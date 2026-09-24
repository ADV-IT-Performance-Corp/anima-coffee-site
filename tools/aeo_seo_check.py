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

# 13 EN answer pages landed by PR #43 ("13 EN answer pages from truth-clean
# staged corpus") with no Ukrainian counterpart yet (measured 2026-09-24 AEO
# gap audit). A real hreflang="uk" link needs a real UA page to point at —
# faking one would be a worse AEO signal than omitting it. This is a named,
# closed debt list, not a blanket relaxation: each page still needs
# hreflang="en", and any answer page NOT on this list still fails normally.
# Remove an entry here only when its matching ua/answers/ page ships.
EN_ONLY_ANSWER_PAGES = frozenset({
    "barista-staff-training-for-office-coffee-setups.html",
    "coffee-bean-supply-for-offices-and-horeca.html",
    "coffee-equipment-for-gas-station-retail-chains.html",
    "coffee-machine-maintenance-and-24-7-support-in-kyiv-oblast.html",
    "espresso-machine-calibration-at-installation-what-s-included.html",
    "frequently-asked-questions-about-anima-coffee-service.html",
    "how-to-reduce-coffee-complaints-in-a-50-person-office.html",
    "how-to-rent-a-professional-coffee-machine-in-kyiv.html",
    "monthly-coffee-service-contract-what-s-included.html",
    "no-upfront-investment-coffee-equipment-rental-model.html",
    "premium-coffee-for-corporate-offices-complete-guide.html",
    "restaurant-coffee-program-24-hour-replacement-sla-explained.html",
    "super-automatic-vs-traditional-espresso-machines.html",
})

def find_pages():
    pages = sorted(SITE.rglob("*.html"))
    # google*.html is the Search Console verification file — headless by
    # design and must never be edited, so it is not a page to check.
    # 404.html is the GitHub Pages custom error page: noindex by design,
    # served for arbitrary unmatched URLs, so canonical/hreflang/JSON-LD
    # (which all assert "this URL is the authoritative version of X") do
    # not apply to it — same exemption class as the verification file.
    def _is_redirect_stub(p):
        # Old-slug stubs (tools/make_stub.py): meta-refresh + canonical +
        # noindex to the page's new URL. Same exemption class as 404.html —
        # deliberately not the authoritative version of anything, so
        # canonical/hreflang/JSON-LD/H1 assertions about "this page" don't
        # apply.
        try:
            return 'http-equiv="refresh"' in p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False

    return [p for p in pages
            if "node_modules" not in str(p)
            and not p.name.startswith("google")
            and p.name != "404.html"
            and not _is_redirect_stub(p)]

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
        required_hreflangs = ("en",) if path.name in EN_ONLY_ANSWER_PAGES else ("en", "uk", "x-default")
        for hl in required_hreflangs:
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
