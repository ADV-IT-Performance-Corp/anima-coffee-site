#!/usr/bin/env python3
"""D7 — verify WebMCP wiring (declarative form attrs + the imperative
read-only tool file) across the live site.

For every page carrying `class="lead-form"`:
  - the <form> tag has both `toolname=` and `tooldescription=`
  - `toolautosubmit` is NOT present (human confirms submit — a founder-
    flippable switch, not something this checker turns on)
  - every visible input/textarea (i.e. every field except the hidden
    `company_url` honeypot) has `toolparamdescription=`
  - `tooldescription`/`toolparamdescription` text matches the page's own
    locale (Cyrillic on /ua/ pages, none on root pages)
  - the page loads `assets/webmcp.js`

Site-wide:
  - no forbidden-claim signature (data/clients/anima-coffee/truth/
    prohibited_claims.yaml in the ADV-Strategy-Core monorepo) appears in any
    toolname/tooldescription/toolparamdescription attribute value, nor in any
    literal answer string inside assets/webmcp.js.
  - no `toolparam*` attribute exists anywhere outside a
    `<form ... toolname=...>...</form>` span (W2.6 — a stray attribute on an
    unrelated form, e.g. `form.ppc-form`, is a regression).
  - W2: assets/analytics.js defines `ROISTAT_PROJECT_ID` exactly once and
    loads the Roistat counter snippet exactly once; no other file in the
    site redefines that constant.

stdlib only. Usage: python3 tools/check_webmcp.py
Exit 0 if everything passes, else 1 (prints every failure found).
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Mirrors data/clients/anima-coffee/truth/prohibited_claims.yaml (ADV-
# Strategy-Core monorepo) — kept as a literal list here since this repo has
# no dependency on that one. Update both if a new signature is added there.
FORBIDDEN_SIGNATURES = [
    "free first month",
    "first month free",
    "перший місяць оренди безкоштовно",
    "retro-bonus",
    "ретро-бонус",
    "1,300+",
    "1300+",
    "1,500+",
    "94%",
    "2-hour response",
    "2 hour response",
    "реагування 2 години",
    "2-hour sla",
    "2-hour emergency",
    "flat-rate monthly",
    "flat rate monthly",
    "swiss-grade",
    "swiss machines",
]

FORM_RE = re.compile(r'<form\b[^>]*class="lead-form"[^>]*>', re.S)
FIELD_RE = re.compile(r'<(?:input|textarea)\b[^>]*>', re.S)
NAME_ATTR_RE = re.compile(r'\bname="([^"]+)"')
TYPE_ATTR_RE = re.compile(r'\btype="([^"]+)"')
CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
TOOLNAME_FORM_RE = re.compile(r'<form\b[^>]*>.*?</form>', re.S)
TOOLPARAM_ATTR_RE = re.compile(r'\btoolparam\w*=')

HONEYPOT_NAME = "company_url"


def attr(tag: str, name: str):
    m = re.search(name + r'="([^"]*)"', tag)
    return m.group(1) if m else None


def is_uk(rel_path: str) -> bool:
    return rel_path == "ua" or rel_path.startswith("ua/")


def forbidden_hits(text: str):
    low = text.lower()
    return [s for s in FORBIDDEN_SIGNATURES if s.lower() in low]


def check_page(path: pathlib.Path):
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    if 'class="lead-form"' not in text:
        return []

    errors = []
    uk = is_uk(rel)

    form_matches = list(FORM_RE.finditer(text))
    if not form_matches:
        return [f"{rel}: has a lead-form marker but no <form class=\"lead-form\"> tag matched"]

    for form_match in form_matches:
        form_tag = form_match.group(0)
        toolname = attr(form_tag, "toolname")
        tooldesc = attr(form_tag, "tooldescription")
        if not toolname:
            errors.append(f"{rel}: form missing toolname")
        if not tooldesc:
            errors.append(f"{rel}: form missing tooldescription")
        if "toolautosubmit" in form_tag:
            errors.append(f"{rel}: form has toolautosubmit set (must stay off)")
        if tooldesc:
            has_cyr = bool(CYRILLIC_RE.search(tooldesc))
            if uk and not has_cyr:
                errors.append(f"{rel}: tooldescription is not Ukrainian on a /ua/ page")
            if not uk and has_cyr:
                errors.append(f"{rel}: tooldescription is not English on a root page")
            hits = forbidden_hits(tooldesc)
            if hits:
                errors.append(f"{rel}: tooldescription contains forbidden claim(s) {hits}")

        start = form_match.end()
        end = text.find("</form>", start)
        body = text[start:end] if end != -1 else text[start:]

        for field_tag in FIELD_RE.findall(body):
            name_m = NAME_ATTR_RE.search(field_tag)
            if not name_m or name_m.group(1) == HONEYPOT_NAME:
                continue
            type_m = TYPE_ATTR_RE.search(field_tag)
            if type_m and type_m.group(1) == "hidden":
                continue
            pdesc = attr(field_tag, "toolparamdescription")
            if not pdesc:
                errors.append(f"{rel}: field '{name_m.group(1)}' missing toolparamdescription")
                continue
            has_cyr = bool(CYRILLIC_RE.search(pdesc))
            if uk and not has_cyr:
                errors.append(f"{rel}: toolparamdescription for '{name_m.group(1)}' is not Ukrainian")
            if not uk and has_cyr:
                errors.append(f"{rel}: toolparamdescription for '{name_m.group(1)}' is not English")
            hits = forbidden_hits(pdesc)
            if hits:
                errors.append(f"{rel}: toolparamdescription for '{name_m.group(1)}' contains forbidden claim(s) {hits}")

    if "assets/webmcp.js" not in text:
        errors.append(f"{rel}: does not load assets/webmcp.js")

    return errors


def check_toolparam_scope(path: pathlib.Path):
    """W2.6 — no toolparam* attribute may exist outside a form that itself
    carries toolname (catches the class of bug where an unrelated form on
    the same page, e.g. form.ppc-form, picked up a stray attribute)."""
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    if "toolparam" not in text:
        return []

    tool_spans = []
    for m in TOOLNAME_FORM_RE.finditer(text):
        open_tag_end = text.find(">", m.start())
        if open_tag_end != -1 and "toolname=" in text[m.start():open_tag_end]:
            tool_spans.append((m.start(), m.end()))

    errors = []
    for m in TOOLPARAM_ATTR_RE.finditer(text):
        pos = m.start()
        if not any(start <= pos < end for start, end in tool_spans):
            errors.append(f"{rel}: toolparam* attribute at offset {pos} found outside a toolname-bearing form")
    return errors


def check_webmcp_js():
    path = ROOT / "assets" / "webmcp.js"
    errors = []
    if not path.exists():
        return [f"assets/webmcp.js: missing"]
    text = path.read_text(encoding="utf-8")
    hits = forbidden_hits(text)
    if hits:
        errors.append(f"assets/webmcp.js: contains forbidden claim(s) {hits}")
    if "registerTool" not in text:
        errors.append("assets/webmcp.js: does not call modelContext.registerTool")
    if "readOnlyHint" not in text:
        errors.append("assets/webmcp.js: read-only tool(s) missing readOnlyHint annotation")
    if "document.modelContext" not in text:
        errors.append("assets/webmcp.js: missing document.modelContext (spec-primary context)")
    if "navigator.modelContext" not in text:
        errors.append("assets/webmcp.js: missing navigator.modelContext fallback (round 4)")
    return errors


ROISTAT_CONST_RE = re.compile(r'\bROISTAT_PROJECT_ID\s*=')


def check_roistat_wiring():
    """W2.1 — the Roistat counter is defined exactly once, in
    assets/analytics.js, driven by one ROISTAT_PROJECT_ID constant; no
    other file in the site redefines it."""
    errors = []
    analytics_path = ROOT / "assets" / "analytics.js"
    if not analytics_path.exists():
        return ["assets/analytics.js: missing"]
    analytics_text = analytics_path.read_text(encoding="utf-8")

    const_hits = len(ROISTAT_CONST_RE.findall(analytics_text))
    if const_hits != 1:
        errors.append(f"assets/analytics.js: ROISTAT_PROJECT_ID must be defined exactly once, found {const_hits}")
    if "roistatHost" not in analytics_text or "roistatProjectId" not in analytics_text:
        errors.append("assets/analytics.js: missing the Roistat counter snippet (roistatProjectId/roistatHost)")
    if analytics_text.count("roistatProjectId = id") > 1:
        errors.append("assets/analytics.js: Roistat counter snippet appears more than once")

    for path in sorted(ROOT.rglob("*")):
        if path == analytics_path or ".git" in path.parts:
            continue
        if path.suffix not in (".js", ".html"):
            continue
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if ROISTAT_CONST_RE.search(text):
            rel = path.relative_to(ROOT).as_posix()
            errors.append(f"{rel}: redefines ROISTAT_PROJECT_ID outside assets/analytics.js")

    return errors


def main():
    errors = []
    pages_checked = 0
    for path in sorted(ROOT.rglob("*.html")):
        if ".git" in path.parts:
            continue
        page_errors = check_page(path)
        if 'class="lead-form"' in path.read_text(encoding="utf-8"):
            pages_checked += 1
        errors.extend(page_errors)
        errors.extend(check_toolparam_scope(path))

    errors.extend(check_webmcp_js())
    errors.extend(check_roistat_wiring())

    for e in errors:
        print(f"FAIL {e}")
    print(f"\nWebMCP check: {pages_checked} lead-form page(s) scanned, {len(errors)} failure(s)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
