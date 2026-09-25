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
        """A page on EN_ONLY_ANSWER_PAGES must not fail for a missing
        hreflang=uk/x-default — it still needs hreflang=en. RED before the
        exemption list exists (every non-ppc page requires all three)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                "barista-staff-training-for-office-coffee-setups.html",
                MINIMAL_EN_ONLY_PAGE,
            )
            errs = gate.check_page(path, all_h1s={})
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

    def test_exemption_list_matches_known_debt_count(self):
        """Guards against silent list rot: exactly the 13 pages named in
        the 2026-09-24 AEO gap audit are on the list, no more, no fewer."""
        self.assertEqual(len(gate.EN_ONLY_ANSWER_PAGES), 13)


if __name__ == "__main__":
    unittest.main()
