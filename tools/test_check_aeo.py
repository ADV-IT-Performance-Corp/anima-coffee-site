#!/usr/bin/env python3
"""Unit tests for tools/check_aeo.py's structural comparison functions:
new_empty_inline_elements() and new_comma_dash_artifacts().

stdlib only (unittest). Usage: python3 tools/test_check_aeo.py

Uses only synthetic content — no real page copy, no real custdev names.
Where a removed name needs a stand-in, "Supplier" is used (the site's own
placeholder convention, see tools/check_aeo.py's roaster-name check).
"""
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo as ca  # noqa: E402


class EmptyInlineElementTests(unittest.TestCase):
    def test_edit_before_preexisting_empty_element_is_not_flagged(self):
        """An unrelated text edit within the ~40-char context window in
        front of an element that was ALREADY empty on origin/main must not
        be flagged — only the element's own history matters, not nearby
        prose. The current (Step-A) context heuristic ties the element's
        identity to that exact preceding text, so an edit there makes it
        think the element is new. RED at Step A/B."""
        main = "<p>Alpha beta gamma delta <b></b> rest</p>"
        head = "<p>Alpha beta gamma DELTA <b></b> rest</p>"
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_newly_emptied_element_with_common_context_is_flagged(self):
        """A pre-existing empty <b> is kept unchanged, and a genuinely NEW
        second empty <b> is added elsewhere in the same file, reusing the
        same ~40-char preceding text. The current (Step-A) heuristic finds
        that context already present on origin/main (from the unchanged
        first element) and misses the new one too — a false negative. The
        structural check must still flag exactly one net-new empty <b>
        (main has 1 instance of the signature, head has 2). RED at Step A/B."""
        shared_prefix = "the finest fresh roasted coffee beans daily by "
        main = f"<p>{shared_prefix}<b></b> forever.</p>"
        head = (
            f"<p>{shared_prefix}<b></b> forever.</p>"
            f"<p>{shared_prefix}<b></b> newly empty too.</p>"
        )
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)

    def test_exemptions_hold(self):
        """id/name anchor targets, aria-hidden decorative elements, and
        markup inside script/style/template are never flagged regardless
        of history. A class-only span that matches an ALREADY-empty span
        of the same class elsewhere on origin/main is also exempt
        (position-independent, by class) — this sub-case is a Step C
        addition: it fails (is flagged) at Step A/B and passes at Step C."""
        pad = "Completely different unrelated paragraph text padding padding padding here."
        main = (
            '<span class="ico"></span>'
            f"<p>{pad}</p>"
            '<a id="anchor1"></a>'
            '<span aria-hidden="true"></span>'
            '<script>var markup = "<b></b>";</script>'
        )
        head = (
            '<a id="anchor1"></a>'
            '<span aria-hidden="true"></span>'
            f"<p>{pad}</p>"
            '<span class="ico"></span>'
            '<script>var markup = "<b></b>";</script>'
        )
        result = ca.new_empty_inline_elements(head, main)
        # anchor/aria-hidden/script-skip sub-cases: nothing from those should
        # ever appear in the failure list.
        self.assertFalse(any("anchor1" in r for r in result))
        self.assertFalse(any("aria-hidden" in r for r in result))
        self.assertFalse(any("markup" in r for r in result))
        # class-only-span-matches-by-class-on-main exemption (Step C).
        self.assertEqual(result, [])


class OriginMainTextMemoizationTests(unittest.TestCase):
    def test_origin_main_text_is_fetched_once_per_path(self):
        """F7a (agy-independent verifier, tools/check_aeo.py:584/:602):
        check_punctuation_artifacts() and check_empty_inline_elements()
        each call _origin_main_text(p) per file, so every page was fetched
        via `git show` TWICE per run. Memoize per rel-path for the
        duration of one run so a repeated lookup of the same path costs
        one subprocess call."""
        ca._origin_main_text.cache_clear()
        fake = subprocess_result = mock.Mock(returncode=0, stdout="cached content")
        with mock.patch.object(ca.subprocess, "run", return_value=fake) as run_mock:
            p = pathlib.Path("/fake/root/answers/faq.html")
            with mock.patch.object(ca, "ROOT", pathlib.Path("/fake/root")):
                ca._origin_main_text(p)
                ca._origin_main_text(p)
        self.assertEqual(run_mock.call_count, 1)


class NewFileNotScannedTests(unittest.TestCase):
    def test_new_file_is_not_scanned_for_comma_dash(self):
        """A file absent from origin/main has no deletion history, so the
        ', —' rule is out of scope for it — main=None must return []
        (not compare against an empty document)."""
        head = "<p>one, — two, — three</p>"
        self.assertEqual(ca.new_comma_dash_artifacts(head, None), [])

    def test_new_file_is_not_scanned_for_empty_elements(self):
        """A file absent from origin/main has no deletion history, so the
        empty-inline-element rule is out of scope for it — main=None must
        return [] (not compare against an empty document)."""
        head = '<b></b><span class="ico"></span>'
        self.assertEqual(ca.new_empty_inline_elements(head, None), [])


class NestedSkipSubtreeTests(unittest.TestCase):
    def test_nested_template_does_not_swallow_the_rest_of_the_file(self):
        """agy [HIGH] tools/check_aeo.py:317 (round-1 diff 5a62161..9cb16ef):
        handle_endtag only decrements _skip_depth when the stack top is a
        skip root with the matching tag, so a NESTED <template> inside a
        <template> closes the outer template on the inner end tag and
        leaves the scanner permanently in skip mode for the rest of the
        file. An empty <b></b> placed AFTER a nested template pair must
        still be flagged when main lacks it."""
        main = "<template><template></template></template>"
        head = "<template><template></template></template><b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)

    def test_script_nested_in_template_does_not_swallow_the_rest_of_the_file(self):
        """Second regression shape from the agy finding: a <script> nested
        inside a <template> must not miscount the skip depth either — an
        empty <b></b> after the pair must still be flagged when main lacks
        it."""
        main = "<template><script>x</script></template>"
        head = "<template><script>x</script></template><b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)


class CommaDashScanTextTests(unittest.TestCase):
    def test_comma_dash_scan_text_includes_jsonld_prose(self):
        """F6 hardening after the agy [HIGH] false-positive finding at
        tools/check_aeo.py:588 (main_joined was claimed to be built from
        head's jsonld_pairs; the conductor verified this was NOT actually
        the case at 9cb16ef). To make the misread impossible by
        construction, one helper builds the scan text for BOTH sides. An
        .html string whose ONLY ', —' sits inside a JSON-LD 'description'
        must still appear in the scan text via that one helper."""
        import pathlib as _pathlib
        html_src = (
            '<html><body><p>no dash here</p>'
            '<script type="application/ld+json">'
            '{"description": "Beans, — roasted weekly."}'
            "</script></body></html>"
        )
        scan_text = ca._comma_dash_scan_text(_pathlib.Path("x.html"), html_src)
        self.assertIn(", —", scan_text)

    def test_comma_dash_delta_zero_when_dash_moves_between_scan_units(self):
        """A pair where main has ', —' only inside JSON-LD and head has it
        only in visible text must yield delta 0 through
        new_comma_dash_artifacts() — counts are per file across BOTH scan
        units (visible text + JSON-LD prose), not per unit."""
        import pathlib as _pathlib
        p = _pathlib.Path("x.html")
        main_html = (
            '<html><body><p>Beans roasted weekly.</p>'
            '<script type="application/ld+json">'
            '{"description": "Beans, — a supplier favorite."}'
            "</script></body></html>"
        )
        head_html = (
            '<html><body><p>Beans, — roasted weekly.</p>'
            '<script type="application/ld+json">'
            '{"description": "Beans, a supplier favorite."}'
            "</script></body></html>"
        )
        main_scan = ca._comma_dash_scan_text(p, main_html)
        head_scan = ca._comma_dash_scan_text(p, head_html)
        self.assertEqual(ca.new_comma_dash_artifacts(head_scan, main_scan), [])


class CommaDashArtifactTests(unittest.TestCase):
    def test_preexisting_comma_dash_is_not_flagged(self):
        """A legitimate ', —' aside whose surrounding words merely got
        edited elsewhere in the sentence (not a deletion stranding the
        dash) must not be flagged. The current (Step-A) heuristic ties the
        dash's identity to its exact preceding text, so any nearby edit
        makes it look new — a false positive. RED at Step A/B."""
        main = "<p>Оренда кавомашин, — сказав він.</p>"
        head = "<p>Оренда кавових машин, — сказав він.</p>"
        self.assertEqual(ca.new_comma_dash_artifacts(head, main), [])

    def test_comma_dash_stranded_by_deletion_is_flagged(self):
        """A pre-existing ', —' is kept unchanged, and a genuinely NEW
        second ', —' is added elsewhere in the same file, reusing the same
        ~25-char preceding text. The current (Step-A) heuristic finds that
        context already present on origin/main (from the unchanged first
        occurrence) and misses the new one too — a false negative. The
        count comparison must still flag exactly one net-new ', —' (main
        has 1 occurrence, head has 2). RED at Step A/B."""
        shared_prefix = "the finest fresh roasted coffee beans that we offer today"
        main = f"<p>{shared_prefix}, — always fresh.</p>"
        head = (
            f"<p>{shared_prefix}, — always fresh.</p>"
            f"<p>{shared_prefix}, — even more fresh.</p>"
        )
        result = ca.new_comma_dash_artifacts(head, main)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
