#!/usr/bin/env python3
"""Unit tests for tools/aeo_seo_check.py's per-page hreflang rule.

stdlib only (unittest). Usage: python3 tools/test_aeo_seo_check.py

Covers the EN_ONLY_ANSWER_PAGES exemption: 13 answer pages landed in
PR #43 ("13 EN answer pages from truth-clean staged corpus") with no
Ukrainian counterpart yet, so they cannot carry a real hreflang="uk"
link without pointing at a nonexistent or mismatched page. The gate must
still require hreflang="en" for them, but not fail them for a missing
"uk"/"x-default" alternate that would be a lie. A page NOT on this list
must still fail the normal way — the exemption is a named, closed list,
not a blanket relaxation of the AEO gate.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import aeo_seo_check as gate  # noqa: E402

MINIMAL_EN_ONLY_PAGE = """<!DOCTYPE html>
<html><head>
<title>Barista staff training for office coffee setups</title>
<meta name="description" content="A sufficiently long meta description for AEO gate purposes here.">
<link rel="canonical" href="https://aeo.animacoffee.com.ua/answers/barista-staff-training-for-office-coffee-setups.html" />
<link rel="alternate" hreflang="en" href="https://aeo.animacoffee.com.ua/answers/barista-staff-training-for-office-coffee-setups.html" />
<link rel="alternate" hreflang="x-default" href="https://aeo.animacoffee.com.ua/answers/barista-staff-training-for-office-coffee-setups.html" />
<script type="application/ld+json">{"@context": "https://schema.org", "@type": "FAQPage"}</script>
</head><body><h1>Barista staff training</h1></body></html>
"""

MINIMAL_BILINGUAL_PAGE = MINIMAL_EN_ONLY_PAGE.replace(
    "barista-staff-training-for-office-coffee-setups.html",
    "coffee-machine-breakdown-peak-hours.html",
).replace(
    '<link rel="alternate" hreflang="x-default"',
    '<link rel="alternate" hreflang="uk" href="https://aeo.animacoffee.com.ua/ua/answers/coffee-machine-breakdown-peak-hours.html" />\n'
    '<link rel="alternate" hreflang="x-default"',
)


class EnOnlyAnswerPageExemptionTests(unittest.TestCase):
    def _write(self, tmp, relname, content):
        p = pathlib.Path(tmp) / relname
        p.write_text(content, encoding="utf-8")
        return p

    def test_listed_en_only_page_is_not_flagged_for_missing_uk(self):
        """A page named on EN_ONLY_ANSWER_PAGES must not fail for a missing
        hreflang=uk/x-default — it still needs hreflang=en. Exercises the
        exemption mechanism itself (via monkeypatch) independent of whether
        the live list currently has any entries — see
        test_exemption_list_is_empty_now_all_13_pages_translated below for
        the live-list assertion."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                "barista-staff-training-for-office-coffee-setups.html",
                MINIMAL_EN_ONLY_PAGE,
            )
            original = gate.EN_ONLY_ANSWER_PAGES
            gate.EN_ONLY_ANSWER_PAGES = frozenset(
                {"barista-staff-training-for-office-coffee-setups.html"}
            )
            try:
                errs = gate.check_page(path, all_h1s={})
            finally:
                gate.EN_ONLY_ANSWER_PAGES = original
            self.assertFalse(
                any("hreflang" in e for e in errs),
                f"expected no hreflang failures for an exempted EN-only page, got: {errs}",
            )

    def test_unlisted_page_missing_uk_still_fails(self):
        """A page NOT on the exemption list must still fail normally —
        the exemption is a closed, named list, not a relaxed default."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "some-other-new-answer-page.html", MINIMAL_EN_ONLY_PAGE)
            errs = gate.check_page(path, all_h1s={})
            self.assertTrue(
                any("hreflang=uk" in e for e in errs),
                f"expected a missing hreflang=uk failure for a non-exempted page, got: {errs}",
            )

    def test_bilingual_page_passes_untouched(self):
        """A page that already carries all three hreflang links (the
        normal case) keeps passing regardless of the exemption list."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp, "coffee-machine-breakdown-peak-hours.html", MINIMAL_BILINGUAL_PAGE
            )
            errs = gate.check_page(path, all_h1s={})
            self.assertFalse(any("hreflang" in e for e in errs), errs)

    def test_exemption_list_is_empty_now_all_13_pages_translated(self):
        """The 13 pages named in the 2026-09-24 AEO gap audit each shipped
        a real ua/answers/ translation on 2026-09-25 (fix/aeo-gate-150),
        so the debt list is empty again. Guards against silent list rot in
        either direction: a future EN-only landing should add itself here,
        not accumulate silently, and a shipped translation should be
        removed from here, not left as a stale, unnecessary exemption."""
        self.assertEqual(len(gate.EN_ONLY_ANSWER_PAGES), 0)



# A ppc/ landing page: EN-only, noindex, no hreflang and no JSON-LD by design
# (CLAUDE.md: "ppc/ = 13 noindex landing pages, EN only, stripped nav").
MINIMAL_PPC_PAGE = """<!DOCTYPE html>
<html><head>
<title>Coffee machine rental in Kyiv</title>
<meta name="description" content="A sufficiently long meta description for AEO gate purposes here.">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://aeo.animacoffee.com.ua/ppc/coffee-machine-rental-kyiv.html" />
</head><body><h1>Coffee machine rental in Kyiv</h1></body></html>
"""


class _BackslashPath(type(pathlib.Path())):
    """A real, readable Path whose str() renders with Windows backslashes,
    so the Windows rendering can be reproduced on Linux CI too. File I/O
    goes through __fspath__, which keeps the real separators."""

    def __fspath__(self):
        return super().__str__()

    def __str__(self):
        return super().__str__().replace("/", "\\")


class PpcPathPortabilityTests(unittest.TestCase):
    """The ppc/ exemption must not depend on the OS path separator: on
    native Windows Python str(path) uses backslashes, so a "/ppc/"
    substring match silently stopped exempting all 13 ppc/ pages there
    (150/163 locally vs 163/163 on Linux/WSL)."""

    def _write_ppc(self, tmp, content=MINIMAL_PPC_PAGE):
        d = pathlib.Path(tmp) / "ppc"
        d.mkdir()
        p = d / "coffee-machine-rental-kyiv.html"
        p.write_text(content, encoding="utf-8")
        return p

    def test_ppc_page_exempt_on_native_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            errs = gate.check_page(self._write_ppc(tmp), all_h1s={})
            self.assertEqual(errs, [])

    def test_ppc_page_exempt_when_path_renders_with_backslashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _BackslashPath(self._write_ppc(tmp))
            self.assertIn("\\ppc\\", str(path))  # really Windows-style
            errs = gate.check_page(path, all_h1s={})
            self.assertEqual(errs, [])

    def test_non_ppc_page_still_fails_when_path_renders_with_backslashes(self):
        """The fix must not turn into a blanket exemption: a page outside
        ppc/ with no hreflang still fails, whatever the separator."""
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "some-page.html"
            p.write_text(MINIMAL_PPC_PAGE, encoding="utf-8")
            errs = gate.check_page(_BackslashPath(p), all_h1s={})
            self.assertIn("missing hreflang=uk", errs)
            self.assertIn("missing JSON-LD", errs)


if __name__ == "__main__":
    unittest.main()
