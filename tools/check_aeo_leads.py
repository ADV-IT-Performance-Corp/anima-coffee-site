#!/usr/bin/env python3
"""AEO leads slice gate (2026-09-25). stdlib only.

Executable checks for the "every buyer-intent page can convert" Gherkin
feature set (see the slice brief). Each check is printed as its own
PASS/FAIL line with failing examples, mirroring tools/check_aeo.py's
CHECKS/main() convention.

Checks:
1. Every in-scope landing page (sitemap.xml + ppc-sitemap.xml, EN and
   /ua/, excluding answers/ and blog/ pages, excluding the explicit
   LEAD_FORM_EXEMPT list) has exactly one class="lead-form" element with
   id="leadForm" and a reference to assets/lead.js (see
   lead_form_problems()).
2. Every indexable page has a sticky CTA bar container (id="sticky-cta")
   that reuses the page's own existing tel: and Telegram links and links
   to a lead form (see sticky_cta_bar_problems()). This is the
   statically-checkable SUBSET of the "sticky contact bar" scenario —
   the dataLayer.push('cta_click', ...) calls and the "never covers the
   submit button at 375px" layout fact both need a real browser and are
   NOT checked here; tools/test_check_aeo_leads.py exercises the logic
   function directly with fixtures instead.
3. Every indexable page that declares an Organization JSON-LD node has a
   `contactPoint` with contactType "sales", the published telephone and
   email, availableLanguage containing both "uk" and "en", and
   areaServed "UA" (see contactpoint_problems()).
4. Every in-scope landing page's JSON-LD has a Service node whose
   provider references the Organization @id (see service_node_problems()).
5. Every in-scope landing page's visible Q&A (the site's own
   <details><summary>...<span class="ico"></span></summary><p>...</p>
   </details> pattern, confirmed against barista-training.html,
   maintenance.html, monthly-contract.html, premium-coffee-beans.html,
   how-to-rent.html) is backed by a matching FAQPage in JSON-LD, and vice
   versa: every FAQPage question text must appear verbatim (whitespace-
   normalized, case-insensitive) somewhere in the page's visible text —
   this is the "no invented FAQ" rule applied in reverse, and it also
   catches pre-existing bad content (see faq_problems()).
6. No indexable page's JSON-LD adds WebSite SearchAction, geo,
   priceRange, AggregateRating, or an @type Review node. Confirmed via
   grep against the unmodified site (2026-09-25): zero existing
   occurrences of any of these, so a blanket ban (not a diff-only rule)
   is correct and simpler — see the module-level FAKE_MARKUP_PATTERNS
   comment.
7. Every JSON-LD block on every indexable page parses as JSON.
8. hreflang/canonical <link> tags are unchanged vs origin/main (a
   regression guard for whoever implements the fixes this gate demands —
   reuses tools/check_aeo.py's own _origin_main_text() memoized git-show
   helper).
9. tools/check_aeo.py itself still exits 0 (shelled out to as a list of
   args, matching tools/check_aeo.py's own subprocess.run pattern in
   check_llms_full_sync() — never shell=True with interpolated strings).

Usage: python3 tools/check_aeo_leads.py
Exit 0 if every check passes, else 1.

This gate is expected to be RED against the unmodified site (a TDD
red commit) — it does not fix the site, only tests it.
"""
import html
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo as ca  # noqa: E402 — reuse ROOT/BASE/all_html_pages/is_indexable/_origin_main_text

ROOT = ca.ROOT
BASE = ca.BASE

# Pages in scope for the lead-form requirement (sitemap.xml + ppc-sitemap.xml,
# non-answer, non-blog, indexable) that intentionally have no lead-form of
# their own. Each entry MUST be verified, not blanket-added — see the
# module docstring's check 1.
LEAD_FORM_EXEMPT = {
    # A one-line Google Search Console ownership token
    # ("google-site-verification: ...") — not a real page, has no <html>
    # structure at all to hang a form on. tools/check_aeo.py's own
    # all_html_pages() already excludes this filename from every other
    # page-shaped check for the same reason.
    "google46d01ca3a8e17a46.html": "Search Console verification stub, not a real page",
}


# --- sitemap / in-scope landing pages -------------------------------------

def _sitemap_locs():
    locs = []
    for name in ("sitemap.xml", "ppc-sitemap.xml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        locs += re.findall(r"<loc>([^<]+)</loc>", text)
    return locs


def _loc_to_relpath(loc: str) -> str:
    rel = loc[len(BASE):].lstrip("/")
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    return rel


def landing_pages():
    """(rel, path, text) for every in-scope landing page: every
    sitemap.xml/ppc-sitemap.xml entry, minus answers/ and blog/ pages (the
    "non-answer, non-blog" Gherkin filter — checked as a path-segment
    match, so it also covers /ua/answers/... and /ua/blog/...), minus
    non-indexable pages (every current ppc-sitemap.xml page is noindex,
    verified 2026-09-25 — mirrors tools/check_aeo.py's own is_indexable()
    gate and its check_md_twins() convention of treating /ppc/ specially).
    A sitemap entry whose file is missing is skipped here — that is
    tools/check_aeo.py's check_sitemap_urls_exist()'s job, not this gate's."""
    pages = []
    seen = set()
    for loc in _sitemap_locs():
        rel = _loc_to_relpath(loc)
        if rel in seen:
            continue
        seen.add(rel)
        if "answers/" in rel or "blog/" in rel:
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        pages.append((rel, p, text))
    return pages


# --- check 1: canonical lead form ------------------------------------------

_CLASS_ATTR_RE = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*\bclass="([^"]*)"[^>]*>')


def _elements_with_class(html_src: str, cls: str):
    """(tag, full_start_tag) for every start tag carrying `cls` as one of
    its (possibly several) class tokens — not a bare substring match, so
    e.g. class="lead-form-wide" does not count as class="lead-form"."""
    out = []
    for m in _CLASS_ATTR_RE.finditer(html_src):
        tag, classes = m.group(1), m.group(2)
        if cls in classes.split():
            out.append((tag, m.group(0)))
    return out


def lead_form_problems(html_src: str) -> list[str]:
    """Pure function: exactly one class="lead-form" element, carrying
    id="leadForm", plus a reference to assets/lead.js (any relative
    prefix, e.g. "../assets/lead.js" for /ua/ or /ppc/ pages — confirmed
    against ua/coffee-machine-emergency-support.html and
    ppc/free-coffee-assessment.html)."""
    problems = []
    elems = _elements_with_class(html_src, "lead-form")
    if len(elems) != 1:
        problems.append(f'{len(elems)} element(s) with class="lead-form" (want exactly 1)')
        return problems
    _tag, start_tag = elems[0]
    if 'id="leadForm"' not in start_tag:
        problems.append("the lead-form element is missing id=\"leadForm\"")
    if not re.search(r'src="[^"]*assets/lead\.js"', html_src):
        problems.append("page does not reference assets/lead.js (or a relative path to it)")
    return problems


def check_lead_form_on_landing_pages():
    fails = []
    for rel, _p, text in landing_pages():
        if rel in LEAD_FORM_EXEMPT:
            continue
        for msg in lead_form_problems(text):
            fails.append(f"{rel}: {msg}")
    return fails


# --- check 2: sticky CTA bar -----------------------------------------------

STICKY_CTA_ID = "sticky-cta"

_TEL_HREF_RE = re.compile(r'href="(tel:[^"]+)"', re.I)
_TELEGRAM_HREF_RE = re.compile(r'href="(https://t\.me/[^"]+)"', re.I)
_CTA_ANCHOR_RE = re.compile(r'href="[^"]*#cta"')


def _strip_scripts(html_src: str) -> str:
    return re.sub(r"<script\b[^>]*>.*?</script>", " ", html_src, flags=re.S | re.I)


def existing_tel_href(html_src: str):
    m = _TEL_HREF_RE.search(_strip_scripts(html_src))
    return m.group(1) if m else None


def existing_telegram_href(html_src: str):
    m = _TELEGRAM_HREF_RE.search(_strip_scripts(html_src))
    return m.group(1) if m else None


def _find_element_by_id(html_src: str, elem_id: str):
    """(tag, inner_html) for the first element whose start tag carries
    id="elem_id", found via a depth-tracking scan for that one tag name
    (not a full HTML parse — sufficient because we only need one
    identified container's subtree). Returns None if no element with that
    id exists, or if its closing tag can't be found (unterminated)."""
    m = re.search(
        rf'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*\bid="{re.escape(elem_id)}"[^>]*?(/?)>',
        html_src,
    )
    if not m:
        return None
    tag = m.group(1).lower()
    if m.group(2) == "/":  # self-closing start tag: no children at all
        return (tag, "")
    start = m.end()
    open_re = re.compile(rf"<{re.escape(tag)}\b", re.I)
    close_re = re.compile(rf"</{re.escape(tag)}\s*>", re.I)
    depth = 1
    pos = start
    while depth > 0:
        next_close = close_re.search(html_src, pos)
        if not next_close:
            return None  # unterminated element
        next_open = open_re.search(html_src, pos, next_close.start())
        if next_open:
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    return (tag, html_src[start:next_close.start()])


def sticky_cta_bar_problems(html_src: str) -> list[str]:
    """Pure, unit-tested function for the statically-checkable subset of
    the "a sticky contact bar is present" scenario: a shared container
    (id="sticky-cta") that reuses the page's OWN existing tel:/Telegram
    links (never invents a fresh one) and carries an anchor to a lead
    form ("...#cta", the site's own convention for its CTA/lead-form
    section id — see coffee-machine-emergency-support.html's
    <section class="cta block" id="cta">). Deliberately does NOT
    fake-pass on an unrelated element merely carrying class="sticky-cta"
    elsewhere on the page — only the identified container's own subtree
    is checked (see tools/test_check_aeo_leads.py for the precision
    test). NOT checked here (needs a real browser): the
    dataLayer.push('cta_click', {channel: ...}) calls, the 375px
    never-covers-the-submit-button layout fact, and /ua/ vs EN label
    language — the bar doesn't exist at all yet, so there is nothing to
    read a label off of."""
    problems = []
    tel = existing_tel_href(html_src)
    telegram = existing_telegram_href(html_src)
    if tel is None:
        problems.append("page has no existing tel: link to reuse in the sticky bar")
    if telegram is None:
        problems.append("page has no existing Telegram (t.me) link to reuse in the sticky bar")
    found = _find_element_by_id(html_src, STICKY_CTA_ID)
    if found is None:
        problems.append(f'no sticky CTA bar container found (id="{STICKY_CTA_ID}")')
        return problems
    _tag, inner = found
    if tel is not None and f'href="{tel}"' not in inner:
        problems.append(f"sticky bar does not reuse the page's tel: link ({tel!r})")
    if telegram is not None and f'href="{telegram}"' not in inner:
        problems.append(f"sticky bar does not reuse the page's Telegram link ({telegram!r})")
    if not _CTA_ANCHOR_RE.search(inner):
        problems.append('sticky bar has no anchor to a lead form ("...#cta")')
    return problems


def check_sticky_cta_bar():
    fails = []
    for p in ca.all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        for msg in sticky_cta_bar_problems(text):
            fails.append(f"{p.relative_to(ROOT)}: {msg}")
    return fails


# --- JSON-LD helpers (shared by checks 3-7) --------------------------------

_JSONLD_BLOCK_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _jsonld_blocks(html_src: str):
    return _JSONLD_BLOCK_RE.findall(html_src)


def _jsonld_nodes(html_src: str):
    """Every JSON-LD node (dict) across every ld+json block on the page,
    flattening an @graph array or a bare top-level array. A block that
    fails to parse is skipped, never crashes the gate (matches
    tools/check_aeo.py's _jsonld_prose_strings() tolerance) — check
    check_all_jsonld_parses() is the dedicated check for parse failures."""
    nodes = []
    for block in _jsonld_blocks(html_src):
        try:
            data = json.loads(block)
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            candidates = data["@graph"]
        elif isinstance(data, list):
            candidates = data
        else:
            candidates = [data]
        nodes.extend(n for n in candidates if isinstance(n, dict))
    return nodes


def _has_type(node: dict, type_name: str) -> bool:
    t = node.get("@type")
    return t == type_name or (isinstance(t, list) and type_name in t)


def find_organization_node(nodes):
    for n in nodes:
        if _has_type(n, "Organization") and str(n.get("@id", "")).endswith("#organization"):
            return n
    for n in nodes:
        if _has_type(n, "Organization"):
            return n
    return None


# --- check 3: Organization sales ContactPoint ------------------------------

def contactpoint_problems(org_node: dict) -> list[str]:
    """Pure function: given an Organization JSON-LD node (dict), return
    problems with its `contactPoint` per the "Organization exposes a
    sales ContactPoint" scenario. `contactPoint` may be a single object
    or an array containing one."""
    cp = org_node.get("contactPoint")
    if cp is None:
        return ["Organization node has no contactPoint"]
    candidates = cp if isinstance(cp, list) else [cp]
    sales = [c for c in candidates if isinstance(c, dict) and c.get("contactType") == "sales"]
    if not sales:
        return ['contactPoint has no entry with contactType "sales"']
    c = sales[0]
    problems = []
    if c.get("@type") != "ContactPoint":
        problems.append(f'sales contactPoint @type is {c.get("@type")!r}, want "ContactPoint"')
    if not c.get("telephone"):
        problems.append("sales contactPoint missing telephone")
    if not c.get("email"):
        problems.append("sales contactPoint missing email")
    langs = c.get("availableLanguage")
    langs_list = langs if isinstance(langs, list) else ([langs] if langs else [])
    if not ({"uk", "en"} <= set(langs_list)):
        problems.append(f'sales contactPoint availableLanguage is {langs!r}, want to include "uk" and "en"')
    if c.get("areaServed") != "UA":
        problems.append(f'sales contactPoint areaServed is {c.get("areaServed")!r}, want "UA"')
    return problems


def check_contactpoint_on_organization():
    fails = []
    for p in ca.all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        org = find_organization_node(_jsonld_nodes(text))
        if org is None:
            continue
        for msg in contactpoint_problems(org):
            fails.append(f"{p.relative_to(ROOT)}: {msg}")
    return fails


# --- check 4: Service node --------------------------------------------------

def service_node_problems(nodes) -> list[str]:
    service_nodes = [n for n in nodes if _has_type(n, "Service")]
    if not service_nodes:
        return ["no Service node in JSON-LD"]
    for n in service_nodes:
        provider = n.get("provider")
        pid = provider.get("@id") if isinstance(provider, dict) else None
        if pid and str(pid).endswith("#organization"):
            return []
    return ['Service node(s) found but none has provider @id ending "#organization"']


def check_service_node_on_landing_pages():
    fails = []
    for rel, _p, text in landing_pages():
        for msg in service_node_problems(_jsonld_nodes(text)):
            fails.append(f"{rel}: {msg}")
    return fails


# --- check 5: FAQPage matches visible Q&A -----------------------------------

# The site's own repeating visible-Q&A markup pattern, confirmed against
# barista-training.html, maintenance.html, monthly-contract.html,
# premium-coffee-beans.html and how-to-rent.html (all use the identical
# <details><summary>Q<span class="ico"></span></summary><p>A</p></details>
# shape inside a <div class="faq">).
_VISIBLE_FAQ_RE = re.compile(
    r'<details[^>]*>\s*<summary>(.*?)<span class="ico"></span></summary>\s*<p>(.*?)</p>\s*</details>',
    re.S,
)


def _strip_tags(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def visible_qa_pairs(html_src: str):
    pairs = []
    for q, a in _VISIBLE_FAQ_RE.findall(html_src):
        q_text = _strip_tags(q).strip()
        a_text = _strip_tags(a).strip()
        if q_text:
            pairs.append((q_text, a_text))
    return pairs


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def faq_problems(html_src: str, nodes) -> list[str]:
    """Pure function: (1) visible Q&A with no FAQPage in JSON-LD is
    flagged ("Given a landing page whose JSON-LD lacks Service ... if the
    page shows visible Q&A, it also carries FAQPage"); (2) a FAQPage
    whose question text does NOT appear verbatim (whitespace-normalized,
    case-insensitive) anywhere in the page's visible text is flagged —
    the "no invented FAQ" rule, applied against the WHOLE page's visible
    text (not just a .faq block), so a question answered in prose
    elsewhere on the page still counts as backed."""
    visible = visible_qa_pairs(html_src)
    faq_nodes = [n for n in nodes if _has_type(n, "FAQPage")]
    problems = []
    if visible and not faq_nodes:
        problems.append(f"page has {len(visible)} visible Q&A pair(s) but no FAQPage in JSON-LD")
    if faq_nodes:
        page_visible_norm = _normalize_ws(_strip_tags(re.sub(
            r"<script\b[^>]*>.*?</script>", " ", html_src, flags=re.S | re.I)))
        for n in faq_nodes:
            main_entity = n.get("mainEntity")
            questions = main_entity if isinstance(main_entity, list) else ([main_entity] if main_entity else [])
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qname = q.get("name", "")
                qname_norm = _normalize_ws(html.unescape(str(qname)))
                if qname_norm and qname_norm not in page_visible_norm:
                    problems.append(f"FAQPage question not found verbatim in visible page text: {qname!r}")
    return problems


def check_faq_matches_visible_qa():
    fails = []
    for rel, _p, text in landing_pages():
        for msg in faq_problems(text, _jsonld_nodes(text)):
            fails.append(f"{rel}: {msg}")
    return fails


# --- check 6: no fake markup -------------------------------------------------

# Confirmed via grep against the unmodified site (2026-09-25): zero
# existing occurrences of SearchAction/geo/priceRange/AggregateRating/
# Review anywhere in JSON-LD, so a blanket ban is correct (not just a
# diff-only "no NEW occurrence" rule like tools/check_aeo.py's
# punctuation-artifact checks need, since those already have legitimate
# pre-existing instances to protect).
FAKE_MARKUP_PATTERNS = [
    (re.compile(r"SearchAction"), "WebSite SearchAction (no site search exists)"),
    (re.compile(r'"geo"\s*:'), 'a "geo" property'),
    (re.compile(r'"priceRange"\s*:'), 'a "priceRange" property'),
    (re.compile(r"AggregateRating"), "AggregateRating"),
]


def check_no_fake_markup():
    fails = []
    for p in ca.all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        for block in _jsonld_blocks(text):
            for pattern, label in FAKE_MARKUP_PATTERNS:
                if pattern.search(block):
                    fails.append(f"{p.relative_to(ROOT)}: JSON-LD contains {label}")
            try:
                data = json.loads(block)
            except Exception:
                continue
            if isinstance(data, dict) and isinstance(data.get("@graph"), list):
                candidates = data["@graph"]
            elif isinstance(data, list):
                candidates = data
            else:
                candidates = [data]
            for n in candidates:
                if isinstance(n, dict) and _has_type(n, "Review"):
                    fails.append(f"{p.relative_to(ROOT)}: JSON-LD contains an @type Review node")
    return fails


# --- check 7: every JSON-LD block parses ------------------------------------

def check_all_jsonld_parses():
    fails = []
    for p in ca.all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        for i, block in enumerate(_jsonld_blocks(text), start=1):
            try:
                json.loads(block)
            except Exception as e:
                fails.append(f"{p.relative_to(ROOT)}: JSON-LD block #{i} fails to parse: {e}")
    return fails


# --- check 8: hreflang/canonical unchanged vs origin/main -------------------

_CANONICAL_RE = re.compile(r'<link rel="canonical"[^>]*>')
_HREFLANG_RE = re.compile(r'<link rel="alternate" hreflang="[^"]*"[^>]*>')


def _hreflang_canonical_tags(text: str):
    return sorted(_CANONICAL_RE.findall(text)) + sorted(_HREFLANG_RE.findall(text))


def check_hreflang_canonical_unchanged():
    """Regression guard (the "nothing regresses" scenario) for whoever
    implements the fixes this gate demands: reuses
    tools/check_aeo.py's own _origin_main_text() memoized `git show`
    helper, same as its check_punctuation_artifacts()/
    check_empty_inline_elements(). A file with no origin/main version (a
    new file) has nothing to regress against and is skipped, matching
    that module's own new-file convention."""
    fails = []
    for p in ca.all_html_pages():
        main_text = ca._origin_main_text(p)
        if main_text is None:
            continue
        head_text = p.read_text(encoding="utf-8", errors="ignore")
        if _hreflang_canonical_tags(head_text) != _hreflang_canonical_tags(main_text):
            fails.append(f"{p.relative_to(ROOT)}: hreflang/canonical tags changed vs origin/main")
    return fails


# --- check 9: existing gate still passes ------------------------------------

def check_existing_gate_still_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_aeo.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        tail = "\n".join(result.stdout.strip().splitlines()[-15:])
        return [f"tools/check_aeo.py exited {result.returncode}:\n    " + tail.replace("\n", "\n    ")]
    return []


CHECKS = [
    ("landing pages carry the canonical lead form", check_lead_form_on_landing_pages),
    ("a sticky contact bar is present (statically-checkable subset)", check_sticky_cta_bar),
    ("Organization exposes a sales ContactPoint", check_contactpoint_on_organization),
    ("landing pages carry a Service node", check_service_node_on_landing_pages),
    ("visible Q&A and FAQPage JSON-LD match", check_faq_matches_visible_qa),
    ("no fake markup (SearchAction/geo/priceRange/AggregateRating/Review)", check_no_fake_markup),
    ("every JSON-LD block parses", check_all_jsonld_parses),
    ("hreflang/canonical tags unchanged vs origin/main", check_hreflang_canonical_unchanged),
    ("existing tools/check_aeo.py gate still passes", check_existing_gate_still_passes),
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
    print("AEO-leads gate: " + ("ALL GREEN" if ok else "FAILURES ABOVE"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
