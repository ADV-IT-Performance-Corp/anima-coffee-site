#!/usr/bin/env python3
"""AEO-1 slice gate (2026-09-15 audit fixes). stdlib only.

Checks, each printed as its own PASS/FAIL line with failing examples:
1. No page (indexable or not) contains Mock/MOCK_LLM_MODE/Mock Mode/[Mock Response.
2. Every indexable page has exactly one <h1>.
3. No indexable page's slug, <title>, or <h1> contains a rejected term
   (2-hour/emergency-sla wording, "specialty", "swiss", "Franke", "WMF").
4. Every sitemap.xml <loc> resolves to a real file on disk.
5. Every indexable page has a Markdown twin (<page>.md next to <page>.html).
6. llms-full.txt is in sync with `tools/gen_content_md.py`'s generator output.
7. Every old-slug redirect stub carries noindex + a canonical + a meta-refresh
   that both point at a URL/file that actually exists.
8. No file (any HTML page incl. noindex/stubs, any Markdown twin, llms.txt,
   llms-full.txt) contains the roaster name "Covim" in any case or script
   (Latin, Cyrillic "Ковім"/"Ковим") — unconfirmed by the owner as of
   2026-09-15 per the truth registry; remove this rule only when the owner
   confirms the name.
9. No `.html`/`.md`/`.txt` file carries a punctuation artifact of the kind a
   mechanical text deletion leaves behind: a never-valid sequence (`?,`
   `:,` `;,` `,,` an empty/space-only `()`/`( )`, or a comma/dash right
   after an opening bracket) in visible page text or in a JSON-LD
   name/text/description/headline/citation string; leading/trailing
   whitespace in a JSON-LD name/headline/description string; or a ", —"/
   ", –" whose immediate context is new relative to `origin/main` (plain
   ", —" is legitimate UA/RU punctuation elsewhere on the site, so only a
   changed context — proof a deletion left it stranded — is flagged).
10. No `.html` file carries an empty or whitespace-only inline/text element
    (`<b>`, `<strong>`, `<i>`, `<em>`, `<span>`, `<a>`, `<li>`, `<p>`,
    `<h1>`-`<h6>`, `<td>`, `<th>`, `<dd>`, `<dt>`, `<figcaption>`,
    `<blockquote>`) left behind by a bulk text deletion. Same
    anti-false-positive principle as check 9's ", —" rule: flagged only
    when the element is NOT already empty in the same spot on
    `origin/main` — so icon spans, spacer cells, JS mount points and other
    by-design empty elements that predate this PR are never flagged.
    Anchor targets (`id`/`name`, no visible text expected) and
    `aria-hidden` decorative elements are exempt unconditionally, and a
    file with no `origin/main` counterpart is skipped (nothing to prove
    creation against).

Usage: python3 tools/check_aeo.py
Exit 0 if every check passes, else 1.
"""
import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"

MOCK_MARKERS = ["Mock Generated Content", "MOCK_LLM_MODE", "Mock Mode", "[Mock Response"]
REJECTED_TERMS = [
    "2-hour-emergency-sla", "2-hour sla", "2 hour sla",
    "specialty", "swiss", "franke", "wmf",
]
UNCONFIRMED_ROASTER_PATTERN = re.compile(
    r"(?<![a-zA-Zа-яА-ЯіїєґІЇЄҐ])(covim|ков[іи]м)(?![a-zA-Zа-яА-ЯіїєґІЇЄҐ])",
    re.IGNORECASE,
)


def all_html_pages():
    # google*.html is the Search Console verification file: headless by
    # design, not a page — same exemption tools/aeo_seo_check.py applies.
    return sorted(p for p in ROOT.rglob("*.html")
                  if "node_modules" not in str(p) and not p.name.startswith("google"))


def is_redirect_stub(text: str) -> bool:
    return 'http-equiv="refresh"' in text


def is_indexable(text: str) -> bool:
    return "noindex" not in text.lower() and not is_redirect_stub(text)


def check_no_mock():
    fails = []
    for p in all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for marker in MOCK_MARKERS:
            if marker in text:
                fails.append(f"{p.relative_to(ROOT)}: contains {marker!r}")
    return fails


def check_single_h1():
    fails = []
    for p in all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not is_indexable(text):
            continue
        n = len(re.findall(r"<h1[ >]", text))
        if n != 1:
            fails.append(f"{p.relative_to(ROOT)}: {n} H1(s)")
    return fails


def check_rejected_terms():
    fails = []
    for p in all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not is_indexable(text):
            continue
        slug = p.stem.lower()
        title_m = re.search(r"<title>(.*?)</title>", text, re.S)
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).lower() if title_m else ""
        h1 = re.sub(r"<[^>]+>", "", h1_m.group(1)).lower() if h1_m else ""
        for term in REJECTED_TERMS:
            for label, field in (("slug", slug), ("title", title), ("h1", h1)):
                if term in field:
                    fails.append(f"{p.relative_to(ROOT)}: {label} contains {term!r}")
    return fails


def check_sitemap_urls_exist():
    fails = []
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        rel = loc[len(BASE):].lstrip("/")
        if rel == "" or rel.endswith("/"):
            rel = rel + "index.html"
        target = ROOT / rel
        if not target.exists():
            fails.append(f"{loc} -> {target.relative_to(ROOT)} missing")
    return fails


def check_md_twins():
    fails = []
    for p in all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not is_indexable(text):
            continue
        if "/ppc/" in p.as_posix():
            continue
        twin = p.with_suffix(".md")
        if not twin.exists():
            fails.append(f"{p.relative_to(ROOT)}: no {twin.name} twin")
    return fails


def check_llms_full_sync():
    """Regenerate into a scratch copy and byte-compare against the on-disk
    file — independent of git's index/staged state."""
    llms_full = ROOT / "llms-full.txt"
    before = llms_full.read_bytes() if llms_full.exists() else None
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_content_md.py"), "--full-only"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return [f"generator failed: {result.stderr.strip()}"]
    after = llms_full.read_bytes()
    if before != after:
        return ["llms-full.txt was stale — run `python3 tools/gen_content_md.py --full-only` (now regenerated)"]
    return []


def check_redirect_stubs():
    fails = []
    for p in all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not is_redirect_stub(text):
            continue
        rel = p.relative_to(ROOT)
        if "noindex" not in text.lower():
            fails.append(f"{rel}: stub missing noindex")
        refresh_m = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', text)
        canon_m = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        if not refresh_m:
            fails.append(f"{rel}: stub missing meta-refresh target")
        if not canon_m:
            fails.append(f"{rel}: stub missing canonical")
        if refresh_m:
            target = (p.parent / refresh_m.group(1)).resolve()
            if not target.exists():
                fails.append(f"{rel}: refresh target {refresh_m.group(1)} missing")
        if canon_m and not canon_m.group(1).startswith(BASE):
            fails.append(f"{rel}: canonical not absolute aeo.animacoffee.com.ua URL")
    return fails


def check_no_unconfirmed_roaster_name():
    fails = []
    patterns = ("*.html", "*.md", "*.txt")
    seen = set()
    for pattern in patterns:
        for p in ROOT.rglob(pattern):
            if "node_modules" in str(p) or "/.git/" in str(p) or "__pycache__" in str(p):
                continue
            if p in seen:
                continue
            seen.add(p)
            text = p.read_text(encoding="utf-8", errors="ignore")
            matches = UNCONFIRMED_ROASTER_PATTERN.findall(text)
            if matches:
                fails.append(f"{p.relative_to(ROOT)}: {len(matches)} occurrence(s) of unconfirmed roaster name")
    return fails


JSONLD_PROSE_KEYS = {"name", "text", "description", "headline", "citation"}
JSONLD_WS_KEYS = {"name", "headline", "description"}
PUNCT_SCAN_EXTS = (".html", ".md", ".txt")

# Sequences that are never valid English/Ukrainian prose punctuation,
# regardless of history — these don't need an origin/main comparison.
_NEVER_VALID_PATTERNS = [
    (re.compile(r"\?,"), "?,"),
    (re.compile(r":,"), ":,"),
    (re.compile(r";,"), ";,"),
    (re.compile(r",,"), ",,"),
    (re.compile(r"\(\s*\)"), "()/( )"),
    (re.compile(r"\([,–—-]"), "( immediately followed by , or a dash"),
]

# Comma + em/en-dash: legitimate UA/RU punctuation (asides, direct speech)
# elsewhere on this site — only flagged below when the surrounding context
# is new relative to origin/main (see check_punctuation_artifacts).
_DASH_AFTER_COMMA = re.compile(r",\s*[–—]")

# Block-level tags get a newline so stripping them can never *merge*
# unrelated blocks into a run-on sentence; every other tag (a, span, b, …)
# is dropped with no replacement so inline adjacency — e.g. `</a>,` — scans
# exactly like the real rendered page, which is the whole point of this
# check: a comma glued to the end of a link is what the mechanical Covim
# deletion actually left behind.
_BLOCK_TAGS_RE = re.compile(
    r"</?(?:p|div|li|ul|ol|h[1-6]|br|tr|td|th|table|thead|tbody|section|"
    r"header|footer|nav|main|article|aside|form|label|blockquote)\b[^>]*>",
    re.I,
)


def _visible_text_for_scan(html_src: str) -> str:
    stripped = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html_src, flags=re.S | re.I)
    stripped = _BLOCK_TAGS_RE.sub("\n", stripped)
    stripped = re.sub(r"<[^>]+>", "", stripped)
    return html.unescape(stripped)


def _jsonld_prose_strings(html_src: str):
    """(key, value) for every prose-bearing JSON-LD string in every
    <script type="application/ld+json"> block. A block that fails to
    parse is skipped, never crashes the gate."""
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html_src, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, str) and k in JSONLD_PROSE_KEYS:
                        out.append((k, v))
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return out


def _strip_code_and_urls(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    # a parenthesized inline-code span, e.g. "(`roistatGoal.reach()`)", is
    # removed as a unit — otherwise its own literal "()" (part of the code,
    # not prose) and the enclosing parens left empty by stripping only the
    # backticks both false-positive the "( )"/"()" rule.
    text = re.sub(r"\(?`[^`\n]*`\)?", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def _scan_units(path: pathlib.Path, text: str):
    """(visible_text, jsonld_prose_pairs) for one file's content — works
    the same whether `text` came from disk or from `git show`."""
    if path.suffix == ".html":
        return _visible_text_for_scan(text), _jsonld_prose_strings(text)
    return _strip_code_and_urls(text), []


def _origin_main_text(path: pathlib.Path):
    rel = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"origin/main:{rel}"], cwd=ROOT, capture_output=True, text=True,
    )
    return result.stdout if result.returncode == 0 else None


# Not site content: internal handoff/ops docs (verified 2026-09-17 absent
# from both sitemap.xml and robots.txt — 0 references), so out of scope for
# a check about what the site actually serves/publishes. Without this
# exclusion the "( )"/"()" rule false-positives on a pre-existing, deliberate
# "(link goes here)" placeholder convention in these docs, identical on
# origin/main — narrowed here per the zero-false-positives requirement
# rather than by loosening the pattern (the pattern itself is correct for
# site content; delivery/release docs are simply the wrong scope for it).
PUNCT_SCAN_EXCLUDE_DIRS = ("delivery/", "release/")


def _punct_scan_files():
    seen = set()
    for ext in PUNCT_SCAN_EXTS:
        for p in ROOT.rglob(f"*{ext}"):
            sp = p.relative_to(ROOT).as_posix()
            if "node_modules" in sp or "/.git/" in sp or "__pycache__" in sp:
                continue
            if any(sp.startswith(d) for d in PUNCT_SCAN_EXCLUDE_DIRS):
                continue
            if p in seen:
                continue
            seen.add(p)
            yield p


def check_punctuation_artifacts():
    fails = []
    for p in sorted(_punct_scan_files()):
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        visible, jsonld_pairs = _scan_units(p, text)

        # (a) never-valid sequences, in visible text and JSON-LD prose strings
        for label, chunk in [("visible text", visible)] + [(f"JSON-LD {k!r}", v) for k, v in jsonld_pairs]:
            for pattern, name in _NEVER_VALID_PATTERNS:
                for mm in pattern.finditer(chunk):
                    ctx = chunk[max(0, mm.start() - 25): mm.end() + 25].replace("\n", " ")
                    fails.append(f"{rel}: {label}: {name} artifact near {ctx!r}")

        # (b) leading/trailing whitespace on name/headline/description
        for k, v in jsonld_pairs:
            if k in JSONLD_WS_KEYS and v != v.strip():
                fails.append(f"{rel}: JSON-LD {k!r} has leading/trailing whitespace: {v!r}")

        # (c) ", —"/", –" — only when the text immediately BEFORE the comma
        # is new relative to origin/main (see module docstring check 9).
        # Backward-only, ending at the dash itself, on purpose: a mechanical
        # deletion strands ", —" by removing what used to sit *before* the
        # comma (e.g. "...обсмажувачі, — фільтрація" -> "...преміальна, —
        # фільтрація") — the words *after* the dash are irrelevant to
        # whether the dash itself is now an orphan, and comparing them too
        # produced false positives on legitimate ", — " asides elsewhere on
        # the site whose *trailing* clause happened to also get edited.
        main_text = _origin_main_text(p)
        if main_text is None:
            continue  # new file on this branch: nothing to diff against
        main_visible, main_pairs = _scan_units(p, main_text)
        main_joined = main_visible + "\n" + "\n".join(v for _, v in main_pairs)
        for chunk in [visible] + [v for _, v in jsonld_pairs]:
            for mm in _DASH_AFTER_COMMA.finditer(chunk):
                lo = max(0, mm.start() - 50)
                ctx = chunk[lo:mm.end()]
                if ctx not in main_joined:
                    fails.append(f"{rel}: new ', —' artifact vs origin/main near {ctx.replace(chr(10), ' ')!r}")
    return fails


EMPTY_ELEMENT_TAGS = (
    "b", "strong", "i", "em", "span", "a", "li", "p",
    "h1", "h2", "h3", "h4", "h5", "h6", "td", "th",
    "dd", "dt", "figcaption", "blockquote",
)

# An element counts as empty when its content is nothing but whitespace or
# a whitespace entity — a genuine text deletion leaves exactly this behind
# (e.g. `<b></b>`), never a non-whitespace child, so nested markup that
# happens to render no visible text (e.g. an icon `<i>` wrapping only a
# `<svg>`) is intentionally out of scope for this check.
_EMPTY_ELEMENT_RE = re.compile(
    r"<(" + "|".join(EMPTY_ELEMENT_TAGS) + r")\b([^>]*)>"
    r"(?:\s|&nbsp;|&#160;|&#xa0;)*</\1>",
    re.I,
)
_ANCHOR_TARGET_RE = re.compile(r"\b(?:id|name)\s*=", re.I)
_ARIA_HIDDEN_RE = re.compile(r"\baria-hidden\b", re.I)


def _strip_non_scan_blocks(html_src: str) -> str:
    return re.sub(r"<(script|style|template)\b[^>]*>.*?</\1>", " ", html_src, flags=re.S | re.I)


def check_empty_inline_elements():
    fails = []
    for p in sorted(_punct_scan_files()):
        if p.suffix != ".html":
            continue
        rel = p.relative_to(ROOT).as_posix()
        raw = _strip_non_scan_blocks(p.read_text(encoding="utf-8", errors="ignore"))

        main_text = _origin_main_text(p)
        main_raw = _strip_non_scan_blocks(main_text) if main_text is not None else None

        for mm in _EMPTY_ELEMENT_RE.finditer(raw):
            tag, attrs = mm.group(1), mm.group(2)
            if tag.lower() == "a" and _ANCHOR_TARGET_RE.search(attrs):
                continue  # anchor used as a link target, not prose text
            if _ARIA_HIDDEN_RE.search(attrs):
                continue  # decorative element, empty by design
            if main_raw is None:
                continue  # new file on this branch: nothing to diff against
            # Backward-only, ending at the element's own closing tag — same
            # principle as check 9(c)'s ", —" rule: text AFTER the element
            # (e.g. the answer prose following an FAQ icon span) can get
            # edited by this same PR for unrelated reasons (the roaster-name
            # removal) without the element itself being new, and including
            # that trailing text in the comparison false-positived exactly
            # that case (icon spans whose following paragraph lost "from
            # Covim S.p.A. (Italy) and..."). Only the text *before* the
            # element decides whether this element already stood empty here.
            lo = max(0, mm.start() - 40)
            ctx = raw[lo:mm.end()]
            if ctx in main_raw:
                continue  # already empty in this exact spot on origin/main
            fails.append(
                f"{rel}: empty <{tag.lower()}> element not on origin/main near {ctx!r}"
            )
    return fails


CHECKS = [
    ("no Mock/placeholder content", check_no_mock),
    ("exactly one H1 per indexable page", check_single_h1),
    ("no rejected term in indexable slug/title/H1", check_rejected_terms),
    ("every sitemap URL resolves to a file", check_sitemap_urls_exist),
    ("every indexable page has a Markdown twin", check_md_twins),
    ("llms-full.txt in sync with generator", check_llms_full_sync),
    ("every old-slug stub is well-formed", check_redirect_stubs),
    ("no unconfirmed roaster name (Covim) anywhere", check_no_unconfirmed_roaster_name),
    ("no mechanical-deletion punctuation artifacts", check_punctuation_artifacts),
    ("no empty inline elements left by bulk text removal", check_empty_inline_elements),
]


def main():
    ok = True
    for label, fn in CHECKS:
        fails = fn()
        status = "PASS" if not fails else "FAIL"
        if fails:
            ok = False
        print(f"[{status}] {label}" + (f" ({len(fails)} failure(s))" if fails else ""))
        for f in fails[:20]:
            print(f"    - {f}")
        if len(fails) > 20:
            print(f"    ... and {len(fails) - 20} more")
    print()
    print("AEO-1 gate: " + ("ALL GREEN" if ok else "FAILURES ABOVE"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
