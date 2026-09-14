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

    errors.extend(check_webmcp_js())

    for e in errors:
        print(f"FAIL {e}")
    print(f"\nWebMCP check: {pages_checked} lead-form page(s) scanned, {len(errors)} failure(s)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
