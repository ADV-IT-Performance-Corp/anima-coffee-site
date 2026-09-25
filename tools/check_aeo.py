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
   whitespace in a JSON-LD name/headline/description string; or more
   ", —"/", –" sequences (any whitespace variant, including NBSP) in a
   file's scan text than on `origin/main` — a structural COUNT comparison,
   not a text-context heuristic (plain ", —" is legitimate UA/RU
   punctuation elsewhere on the site, so only a net increase relative to
   origin/main is flagged; see new_comma_dash_artifacts()). A file with no
   `origin/main` version (a new file) has no deletion history, so this
   count-comparison rule is out of scope for it — new_comma_dash_artifacts()
   returns `[]` when `main_text is None`. The never-valid-sequence and
   JSON-LD-whitespace rules above still run on new files.
10. No `.html` file has MORE empty/whitespace-only instances of a given
    (tag, attrs, parent-tag-chain) signature than `origin/main` has of that
    same signature, for the tracked tag set (`b strong i em span a li p
    h1`-`h6 td th dd dt figcaption blockquote`) — a structural count
    comparison via an HTMLParser open-element stack, not a text-context
    heuristic (see new_empty_inline_elements()). Anchor/id/name targets
    (non-empty `id`/`name` value) and `aria-hidden="true"` elements are
    exempt unconditionally; a `span` whose only attribute is `class` is
    exempt when an origin/main span of the same class is already empty
    anywhere in the file. Content inside `script`/`style`/`template` is
    never scanned. A file with no `origin/main` version (a new file) has no
    deletion history, so this rule is out of scope for it —
    new_empty_inline_elements() returns `[]` when `main_html is None`.
11. No file (any HTML page incl. noindex/stubs, any Markdown twin, llms.txt,
    llms-full.txt) contains the brand name "Fiorenzato" in any case or
    script (Latin, Cyrillic "Фіоренцато"/"Фиоренцато") — unconfirmed per the
    monorepo truth registry (`public_claims_registry.yaml`, semantic_key
    equipment_brand: only Dr.Coffee and Necta are approved/publishable) as
    of 2026-09-25; remove this rule only when the owner/registry confirms
    the name.
12. `pricing-model.html` and `ua/pricing-model.html` both exist, each carries
    a `<form class="lead-form"` lead-capture element, neither contains a
    numeric price/currency/discount figure ($, ₴, €, грн, UAH, USD, or a
    price-style %) or a digit-driven team-size -> package mapping (e.g.
    "10-20 people", "до 50 співробітників") per
    claim-anima-pricing-custom-quote's no_numeric_price qualifier, and every
    FAQPage JSON-LD question/answer on each page is reflected verbatim in
    that page's visible text (see check_pricing_model_page_complete()).

Known false negative (both checks 9's ", —" rule and check 10, documented
here rather than "fixed" — see new_comma_dash_artifacts() and
new_empty_inline_elements()): within ONE file, removing an artifact/empty-
element instance of signature K while a DIFFERENT instance of the same K
is newly created elsewhere in the same file nets to zero net change and is
not flagged. Accepted: the mechanical bulk deletions this gate defends
against (a site-wide text/name removal) ADD artifacts, they do not move an
existing one from one spot to another — a same-file net-zero swap is not
the failure mode this gate exists to catch.

Usage: python3 tools/check_aeo.py
Exit 0 if every check passes, else 1.
"""
import functools
import html
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser

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
UNCONFIRMED_BRAND_FIORENZATO_PATTERN = re.compile(
    r"(?<![a-zA-Zа-яА-ЯіїєґІЇЄҐ])(fiorenzato|ф[іи]оренцато)(?![a-zA-Zа-яА-ЯіїєґІЇЄҐ])",
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


def check_no_unconfirmed_fiorenzato_brand():
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
            matches = UNCONFIRMED_BRAND_FIORENZATO_PATTERN.findall(text)
            if matches:
                fails.append(f"{p.relative_to(ROOT)}: {len(matches)} occurrence(s) of unconfirmed brand name Fiorenzato")
    return fails


# check_pricing_model_page_complete(): the "pricing-model" answer page pair
# (EN pricing-model.html + UA ua/pricing-model.html) must exist, carry the
# lead form, expose FAQ JSON-LD that is actually reflected in visible copy,
# and never state a numeric price, currency amount, or a price/discount
# percentage — per claim-anima-pricing-custom-quote's no_numeric_price
# qualifier in the monorepo public_claims_registry.yaml (Offer.price is
# forbidden on this page, price:0 included). It also must not carry a
# digit-driven team-size -> package mapping (e.g. "10-20 people", "до 50
# співробітників") — the approved claim is only that three packages exist
# (Start/Pro/Max) matched to venue *format*, never to a headcount number.
PRICE_FIGURE_PATTERN = re.compile(r"[$₴€]|\bгрн\b|\bUAH\b|\bUSD\b|%", re.IGNORECASE)
TEAM_SIZE_MAPPING_PATTERN = re.compile(
    r"(?:\d+\s*[-–—]\s*\d+|\bдо\s*\d+|\bup to\s*\d+)\s*"
    r"(?:people|staff|employees|person|persons|headcount|workers|"
    r"осіб|співробітник\w*|людей|чолов[іi]к\w*|працівник\w*)",
    re.IGNORECASE,
)


def _faq_qa_pairs(html_src: str):
    """(question, answer) pairs from every FAQPage node's mainEntity across
    all JSON-LD <script> blocks on the page. A block that fails to parse is
    skipped, never crashes the check."""
    pairs = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html_src, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        if not isinstance(nodes, list):
            nodes = [nodes]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "FAQPage":
                for q in node.get("mainEntity", []) or []:
                    if not isinstance(q, dict):
                        continue
                    name = q.get("name", "") or ""
                    answer = ((q.get("acceptedAnswer") or {}).get("text", "")) or ""
                    pairs.append((name, answer))
    return pairs


def check_pricing_model_page_complete():
    fails = []
    pages = [ROOT / "pricing-model.html", ROOT / "ua" / "pricing-model.html"]
    missing = [p for p in pages if not p.exists()]
    for p in missing:
        fails.append(f"{p.relative_to(ROOT)}: page does not exist")
    if missing:
        return fails  # nothing else to check until both pages exist

    for p in pages:
        rel = p.relative_to(ROOT)
        text = p.read_text(encoding="utf-8", errors="ignore")

        if '<form class="lead-form"' not in text:
            fails.append(f"{rel}: missing <form class=\"lead-form\"> element")

        for mm in PRICE_FIGURE_PATTERN.finditer(text):
            ctx = text[max(0, mm.start() - 30): mm.end() + 30].replace("\n", " ")
            fails.append(f"{rel}: forbidden price/currency/percentage figure near {ctx!r}")

        for mm in TEAM_SIZE_MAPPING_PATTERN.finditer(text):
            ctx = text[max(0, mm.start() - 30): mm.end() + 30].replace("\n", " ")
            fails.append(f"{rel}: forbidden team-size -> package mapping near {ctx!r}")

        visible_norm = re.sub(r"\s+", " ", _visible_text_for_scan(text)).strip()
        pairs = _faq_qa_pairs(text)
        if not pairs:
            fails.append(f"{rel}: no FAQPage JSON-LD mainEntity found")
        for name, answer in pairs:
            ans_norm = re.sub(r"\s+", " ", answer).strip()
            if ans_norm and ans_norm not in visible_norm:
                fails.append(
                    f"{rel}: FAQ JSON-LD answer not reflected verbatim in visible page text: {ans_norm[:70]!r}"
                )
            name_norm = re.sub(r"\s+", " ", name).strip()
            if name_norm and name_norm not in visible_norm:
                fails.append(
                    f"{rel}: FAQ JSON-LD question not reflected verbatim in visible page text: {name_norm[:70]!r}"
                )

    # The .md twins carry the same facts as prose (no JSON-LD/lead-form to
    # check there), but they must be held to the same no-price/no-team-size
    # bar as the HTML pages — a hand-edit could otherwise introduce a
    # forbidden figure into the twin without tripping the HTML-only scan
    # above.
    for p in (ROOT / "pricing-model.md", ROOT / "ua" / "pricing-model.md"):
        if not p.exists():
            fails.append(f"{p.relative_to(ROOT)}: markdown twin does not exist")
            continue
        rel = p.relative_to(ROOT)
        text = p.read_text(encoding="utf-8", errors="ignore")
        for mm in PRICE_FIGURE_PATTERN.finditer(text):
            ctx = text[max(0, mm.start() - 30): mm.end() + 30].replace("\n", " ")
            fails.append(f"{rel}: forbidden price/currency/percentage figure near {ctx!r}")
        for mm in TEAM_SIZE_MAPPING_PATTERN.finditer(text):
            ctx = text[max(0, mm.start() - 30): mm.end() + 30].replace("\n", " ")
            fails.append(f"{rel}: forbidden team-size -> package mapping near {ctx!r}")
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

EMPTY_ELEMENT_TAGS = frozenset((
    "b", "strong", "i", "em", "span", "a", "li", "p",
    "h1", "h2", "h3", "h4", "h5", "h6", "td", "th",
    "dd", "dt", "figcaption", "blockquote",
))
_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
))
_MEDIA_DESCENDANT_TAGS = frozenset((
    "img", "svg", "picture", "video", "audio", "iframe", "input",
    "select", "textarea", "button", "canvas", "object", "embed", "use",
))
_SKIP_SUBTREE_TAGS = frozenset(("script", "style", "template"))
# HTML5's "P element" rule: starting almost any block-level element while a
# <p> is the innermost open element implicitly closes that <p> first (a <p>
# can never legally contain another block element, so the browser closes it
# rather than nest). This is also the trigger set for li/dd/dt/td/th/tr
# below via _should_implicit_close() — those tags close only on a narrower
# set of siblings, per HTML5's own optional-end-tag rules for each.
_P_CLOSING_TAGS = frozenset((
    "address", "article", "aside", "blockquote", "details", "div", "dl",
    "fieldset", "figcaption", "figure", "footer", "form",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "menu",
    "nav", "ol", "p", "pre", "section", "table", "ul",
    "li", "dd", "dt", "td", "th", "tr",
))


def _should_implicit_close(open_tag: str, new_tag: str) -> bool:
    """True when starting `new_tag` implicitly closes an innermost-open
    `open_tag` per HTML5's optional-end-tag rules, for the element set this
    gate tracks (p, li, dd, dt, td, th, tr — finding 1). A <p> closes on any
    block-level start (see _P_CLOSING_TAGS; this is the finding-1 fix: a
    <div> starting inside an open <p> used to nest instead of closing it,
    misattributing the <div>'s content to the <p> and hiding a deletion
    artifact). <li> closes only on another <li>. <dt>/<dd> close on either.
    <td>/<th> close on another cell or on a new <tr> (a new row can't nest
    inside the previous row's cell). <tr> closes only on another <tr>."""
    if open_tag == "p":
        return new_tag in _P_CLOSING_TAGS
    if open_tag == "li":
        return new_tag == "li"
    if open_tag in ("dt", "dd"):
        return new_tag in ("dt", "dd")
    if open_tag in ("td", "th"):
        return new_tag in ("td", "th", "tr")
    if open_tag == "tr":
        return new_tag == "tr"
    return False


class _EmptyElementScanner(HTMLParser):
    """Open-element-stack HTML parser producing one record per CLOSED
    tracked element whose subtree has no non-whitespace text and no
    media-set descendant. Void elements are never pushed; a stray end tag
    with no matching open element is ignored; an end tag pops everything
    above (and including) its match; script/style/template subtrees are
    skipped entirely, including for the surrounding ancestors' text
    accumulation — a skip-subtree tag nested inside another (e.g.
    <template><script>...) pushes onto `_skip_stack` rather than the main
    element stack, so the skip region only ends once every nested
    skip-subtree tag has been closed, matching the tag that opened it; a
    naive depth counter that doesn't track WHICH tag opened each nested
    level can desync when an inner tag's end tag is mistaken for the
    outer's. Both the head and the origin/main version of a file go
    through this SAME parser, so any parsing quirk it has is applied
    identically to both sides and cancels out of the comparison. An
    element still open at EOF (missing end tag) is flushed and evaluated
    in `close()` (finding 3) exactly like a properly closed element, so a
    deletion that leaves a page ending unclosed (e.g. `<p>Supplier` ->
    `<p>`) is still compared instead of silently dropped on both sides.

    Invariants (state-machine read-through, round 5): a void tag is NEVER
    pushed onto `self.stack`, under any skip state or event type.
    `_skip_stack` is the single source of truth for "currently skipping" —
    every other method checks it, never a separate flag or depth counter.
    A self-closing tag (`handle_startendtag`) is just a start tag — it
    never self-closes (finding 2). Every node pushed onto `self.stack` (and
    every skip-subtree tag pushed onto `_skip_stack`) is eventually popped
    by exactly one of: the matching real end tag, an ancestor's end tag
    closing everything above it, an implicit close from
    `_should_implicit_close()`, or the end-of-document flush in `close()`
    (finding 3) — nothing else ever mutates either stack.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.records = []
        self._skip_stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._skip_stack:
            if tag in _SKIP_SUBTREE_TAGS:
                self._skip_stack.append(tag)
            return
        while self.stack and _should_implicit_close(self.stack[-1]["tag"], tag):
            self._close_top()
        if tag in _MEDIA_DESCENDANT_TAGS:
            self._mark_media_ancestors()
        if tag in _VOID_TAGS:
            return  # never pushed
        node = {
            "tag": tag,
            "attrs": tuple(sorted(attrs)),
            "has_text": False,
            "has_media": False,
            "line": self.getpos()[0],
            "skip_root": tag in _SKIP_SUBTREE_TAGS,
        }
        if node["skip_root"]:
            self._skip_stack.append(tag)
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        # HTML parsing (finding 2): a trailing "/" on a non-void element's
        # start tag (`<i/>`, `<path/>`) is not a real self-close — browsers
        # ignore it and leave the element open exactly as `<i>` would, so
        # the markup/text that follows becomes its CHILD, not its sibling.
        # Only `_VOID_TAGS` (already never pushed by handle_starttag) are
        # actually "closed" by a self-closing tag. So a self-closing tag is
        # simply a start tag; nothing here ever calls handle_endtag.
        # Previously this method force-closed every non-void self-closed
        # tag immediately, which is why `<p><i/> text</p>` was falsely
        # flagged as an empty `<i>` — the text belongs inside `<i>` in real
        # browsers, so `<i>` is not empty at all.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._skip_stack:
            if self._skip_stack[-1] == tag:
                self._skip_stack.pop()
                if not self._skip_stack:
                    self._close_top()  # closes the skip root pushed in handle_starttag
            return  # nested/stray tag inside a skipped subtree: ignored
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                idx = i
                break
        if idx is None:
            return  # stray end tag with no matching open element: ignored
        while len(self.stack) > idx:
            self._close_top()

    def close(self):
        # HTML parsing (finding 3): an element with no closing tag at all
        # is still valid HTML for tags with an optional end tag (a page can
        # legally end in `<p>Supplier`), and even for a genuinely malformed
        # document a real browser still materializes whatever is left open
        # when input ends. Previously anything still on `self.stack` at EOF
        # was silently dropped, so a page ending `<p>Supplier` -> `<p>`
        # (the text mechanically deleted) produced zero records on EITHER
        # side and the deletion went uncompared. Flushing the stack through
        # the normal `_close_top()` path here means each survivor is
        # evaluated for emptiness exactly like a properly closed element,
        # innermost first (list order).
        super().close()
        while self.stack:
            self._close_top()

    def handle_data(self, data):
        if self._skip_stack:
            return
        if data.replace("\xa0", " ").strip():
            for node in self.stack:
                node["has_text"] = True

    def _mark_media_ancestors(self):
        for node in self.stack:
            node["has_media"] = True

    def _close_top(self):
        node = self.stack.pop()
        if node["skip_root"] or node["tag"] not in EMPTY_ELEMENT_TAGS:
            return
        if node["has_text"] or node["has_media"]:
            return
        parent_path = ">".join(n["tag"] for n in self.stack)
        self.records.append({
            "tag": node["tag"],
            "attrs": node["attrs"],
            "key": (node["tag"], node["attrs"], parent_path),
            "line": node["line"],
        })


def _scan_empty_elements(html_src: str):
    parser = _EmptyElementScanner()
    parser.feed(html_src)
    parser.close()
    return parser.records


def _is_id_or_name(attrs) -> bool:
    """A real anchor/link target needs a non-empty id/name — id="" or
    name="" is not a usable target and must not exempt an empty element."""
    return any(k in ("id", "name") and v and v.strip() for k, v in attrs)


def _is_aria_hidden(attrs) -> bool:
    """Only aria-hidden="true" (case-insensitive, after strip) is actually
    hidden from assistive tech — aria-hidden="false" is explicitly visible
    and must not be exempted."""
    return any(k == "aria-hidden" and (v or "").strip().lower() == "true" for k, v in attrs)


def _format_attrs(attrs) -> str:
    parts = []
    for k, v in attrs:
        parts.append(f' {k}="{v}"' if v is not None else f" {k}")
    return "".join(parts)

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


@functools.lru_cache(maxsize=None)
def _origin_main_text_by_rel(rel: str):
    result = subprocess.run(
        ["git", "show", f"origin/main:{rel}"], cwd=ROOT, capture_output=True, text=True,
    )
    return result.stdout if result.returncode == 0 else None


def _origin_main_text(path: pathlib.Path):
    """Memoized per rel-path for the duration of one run (F7a) — every
    check that needs a file's origin/main version shares the single `git
    show` call site in _origin_main_text_by_rel()."""
    return _origin_main_text_by_rel(path.relative_to(ROOT).as_posix())


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


def _join_scan_units(visible: str, jsonld_pairs) -> str:
    """Visible text + JSON-LD prose strings joined into one scan text, for
    the ', —' count comparison — the ONE join used by both the head and
    the origin/main side, so no local variable from one side can leak
    into the other's join (see the module docstring check 9 and F6)."""
    return visible + "\n" + "\n".join(v for _, v in jsonld_pairs)


def _comma_dash_scan_text(path: pathlib.Path, text: str, scan_units=None) -> str:
    """Wraps _join_scan_units() with the (visible, jsonld_pairs) lookup —
    pass an already-computed `scan_units` pair (e.g. the one
    check_punctuation_artifacts() already has for the head side) to avoid
    recomputing it; omit it (as every test and the origin/main side do) to
    have this call _scan_units() itself."""
    visible, jsonld_pairs = scan_units if scan_units is not None else _scan_units(path, text)
    return _join_scan_units(visible, jsonld_pairs)


def new_comma_dash_artifacts(head_text: str, main_text: str | None) -> list[str]:
    """Structural COUNT comparison (Step C): flags a net increase of comma
    plus em/en-dash occurrences (any whitespace between, including NBSP —
    see _DASH_AFTER_COMMA) in `head_text` vs `main_text`, not a text-context
    match. `main_text=None` means the file has no origin/main version (a
    new file) — a new file has no deletion history, so this rule is out of
    scope for it and this returns `[]` unconditionally. Returns one
    "scan-line {line}: {context!r}" string per occurrence in the delta (so
    len(result) == the net increase; "scan-line" because `line` counts
    newlines in the joined scan text, not the original HTML file's line
    numbers), taken from the first `delta` matches in head. Known false
    negative: a same-file swap (one pre-existing occurrence removed, a
    different one created elsewhere) nets to zero and is not flagged — see
    the module docstring.
    """
    if main_text is None:
        return []
    head_matches = list(_DASH_AFTER_COMMA.finditer(head_text))
    main_n = len(list(_DASH_AFTER_COMMA.finditer(main_text)))
    delta = len(head_matches) - main_n
    if delta <= 0:
        return []
    fails = []
    for mm in head_matches[:delta]:
        line = head_text.count("\n", 0, mm.start()) + 1
        lo, hi = max(0, mm.start() - 25), min(len(head_text), mm.end() + 25)
        ctx = head_text[lo:hi].replace("\n", " ")
        fails.append(f"scan-line {line}: {ctx!r}")
    return fails


def new_empty_inline_elements(head_html: str, main_html: str | None) -> list[str]:
    """Structural COUNT comparison (Step C) via _EmptyElementScanner: for
    each (tag, attrs, parent-tag-chain) signature, flags a net increase of
    empty-element instances in `head_html` vs `main_html`, not a
    text-context match. `main_html=None` means the file has no origin/main
    version (a new file) — a new file has no deletion history, so this rule
    is out of scope for it and this returns `[]` unconditionally.

    Exemptions (unconditional, applied before counting): an element with an
    `id`/`name` attribute (anchor/link target) or `aria-hidden` (decorative
    by design); a `span` whose ONLY attribute is `class`, when a span of the
    same class is ALREADY empty anywhere in main_html (position-independent
    — an icon-span convention re-templated in a different spot is not a new
    artifact).

    Returns one "{line}: {delta} new empty <tag[ attrs]> under
    {parent_path} (main {main_n}, head {head_n})" string per signature with
    a net increase, ordered by first occurrence in head. Known false
    negative: a same-file swap (one pre-existing empty element of signature
    K removed, a different one of the same K created elsewhere) nets to
    zero and is not flagged — see the module docstring.
    """
    if main_html is None:
        return []
    head_records = _scan_empty_elements(head_html)
    main_records = _scan_empty_elements(main_html)

    main_class_only_spans = {
        dict(r["attrs"])["class"]
        for r in main_records
        if r["tag"] == "span" and len(r["attrs"]) == 1 and r["attrs"][0][0] == "class"
    }

    main_counter = Counter(
        r["key"] for r in main_records
        if not _is_id_or_name(r["attrs"]) and not _is_aria_hidden(r["attrs"])
    )

    head_counter = Counter()
    head_first_pos = {}
    for r in head_records:
        if _is_id_or_name(r["attrs"]) or _is_aria_hidden(r["attrs"]):
            continue
        if (r["tag"] == "span" and len(r["attrs"]) == 1 and r["attrs"][0][0] == "class"
                and dict(r["attrs"])["class"] in main_class_only_spans):
            continue
        head_counter[r["key"]] += 1
        head_first_pos.setdefault(r["key"], r["line"])

    fails = []
    for key in sorted(head_counter, key=lambda k: head_first_pos[k]):
        head_n = head_counter[key]
        main_n = main_counter.get(key, 0)
        if head_n <= main_n:
            continue
        tag, attrs, parent_path = key
        line = head_first_pos[key]
        fails.append(
            f"{line}: {head_n - main_n} new empty <{tag}{_format_attrs(attrs)}> "
            f"under {parent_path} (main {main_n}, head {head_n})"
        )
    return fails


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

        # (c) ", —"/", –" — a structural count comparison against
        # origin/main, per file (see module docstring check 9).
        main_text = _origin_main_text(p)
        head_joined = _comma_dash_scan_text(p, text, scan_units=(visible, jsonld_pairs))
        main_joined = _comma_dash_scan_text(p, main_text) if main_text is not None else None
        for msg in new_comma_dash_artifacts(head_joined, main_joined):
            fails.append(f"{rel}: new ', —' artifact vs origin/main {msg}")
    return fails


def check_empty_inline_elements():
    fails = []
    for p in sorted(_punct_scan_files()):
        if p.suffix != ".html":
            continue
        rel = p.relative_to(ROOT).as_posix()
        head_html = p.read_text(encoding="utf-8", errors="ignore")
        main_html = _origin_main_text(p)
        for msg in new_empty_inline_elements(head_html, main_html):
            fails.append(f"{rel}:{msg}")
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
    ("no unconfirmed brand name (Fiorenzato) anywhere", check_no_unconfirmed_fiorenzato_brand),
    ("pricing-model page pair exists, has lead form, no price figures, FAQ matches visible copy", check_pricing_model_page_complete),
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
