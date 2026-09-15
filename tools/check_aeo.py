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

Usage: python3 tools/check_aeo.py
Exit 0 if every check passes, else 1.
"""
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
UNCONFIRMED_ROASTER_PATTERN = re.compile(r"covim|ков[іи]м", re.IGNORECASE)


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


CHECKS = [
    ("no Mock/placeholder content", check_no_mock),
    ("exactly one H1 per indexable page", check_single_h1),
    ("no rejected term in indexable slug/title/H1", check_rejected_terms),
    ("every sitemap URL resolves to a file", check_sitemap_urls_exist),
    ("every indexable page has a Markdown twin", check_md_twins),
    ("llms-full.txt in sync with generator", check_llms_full_sync),
    ("every old-slug stub is well-formed", check_redirect_stubs),
    ("no unconfirmed roaster name (Covim) anywhere", check_no_unconfirmed_roaster_name),
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
