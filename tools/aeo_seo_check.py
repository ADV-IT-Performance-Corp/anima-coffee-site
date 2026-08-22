#!/usr/bin/env python3
"""AEO/SEO finalize-and-verify gate — runs across every indexable HTML page.

Checks per page: unique H1, title present, meta description present, canonical
present, hreflang en/uk/x-default present (core+answers pages), valid JSON-LD,
0 broken internal links (relative hrefs/srcs resolve to a real file on disk).

Usage: python3 tools/aeo_seo_check.py
Exit 0 if every page passes every check, else 1. Prints an X/N summary and a
per-page failure list.
"""
import json, pathlib, re, sys

SITE = pathlib.Path(__file__).resolve().parent.parent

def find_pages():
    pages = sorted(SITE.rglob("*.html"))
    # google*.html is the Search Console verification file — headless by
    # design and must never be edited, so it is not a page to check.
    # 404.html is the GitHub Pages custom error page: noindex by design,
    # served for arbitrary unmatched URLs, so canonical/hreflang/JSON-LD
    # (which all assert "this URL is the authoritative version of X") do
    # not apply to it — same exemption class as the verification file.
    return [p for p in pages
            if "node_modules" not in str(p)
            and not p.name.startswith("google")
            and p.name != "404.html"]

def check_page(path, all_h1s):
    html = path.read_text(encoding="utf-8", errors="ignore")
    errs = []

    h1s = re.findall(r"<h1[ >]", html)
    if len(h1s) != 1:
        errs.append(f"h1 count = {len(h1s)} (want 1)")

    if not re.search(r"<title>[^<]{5,}</title>", html):
        errs.append("missing/short <title>")

    if not re.search(r'<meta name="description" content="[^"]{20,}"', html):
        errs.append("missing/short meta description")

    if not re.search(r'<link rel="canonical" href="https://', html):
        errs.append("missing canonical")

    is_ppc = "/ppc/" in str(path)
    if not is_ppc:
        for hl in ("en", "uk", "x-default"):
            if not re.search(rf'hreflang="{hl}"', html):
                errs.append(f"missing hreflang={hl}")

    ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if not ld_blocks:
        if not is_ppc:
            errs.append("missing JSON-LD")
    else:
        for block in ld_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                errs.append(f"invalid JSON-LD: {e}")

    # internal link/asset resolution (relative, non-anchor, non-external)
    refs = re.findall(r'(?:href|src)="([^"]+)"', html)
    base_dir = path.parent
    for ref in refs:
        if ref.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
            continue
        clean = ref.split("#")[0]
        if not clean:
            continue
        target = (base_dir / clean).resolve()
        if not target.exists():
            errs.append(f"broken internal link: {ref}")

    return errs

def main():
    pages = find_pages()
    total = len(pages)
    passed = 0
    failures = {}
    for p in pages:
        errs = check_page(p, None)
        if errs:
            failures[str(p.relative_to(SITE))] = errs
        else:
            passed += 1

    print(f"AEO/SEO gate: {passed}/{total} pages PASS\n")
    if failures:
        print("Failures:")
        for page, errs in failures.items():
            print(f"  {page}")
            for e in errs:
                print(f"    - {e}")
    sys.exit(0 if not failures else 1)

if __name__ == "__main__":
    main()
