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

    def test_name_attribute_is_exempt_like_id(self):
        """A non-empty `name` attribute is a real anchor/link target just
        like a non-empty `id`, so an empty <a name="x"></a> introduced in
        head must not be flagged (see _is_id_or_name)."""
        main = "<p>text</p>"
        head = '<p>text</p><a name="x"></a>'
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_template_skips_content_like_script(self):
        """<template> is in _SKIP_SUBTREE_TAGS, so its content is never
        scanned — an empty <b></b> inside a <template> introduced in head
        must not be flagged, exactly like inside <script>."""
        main = "<p>text</p>"
        head = "<p>text</p><template><b></b></template>"
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_style_skips_content_like_script(self):
        """<style> is in _SKIP_SUBTREE_TAGS, so tag-like text inside it
        (e.g. a CSS content string containing literal markup) is never
        scanned, exactly like inside <script>."""
        main = "<p>text</p>"
        head = '<p>text</p><style>b { content: "<b></b>"; }</style>'
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_media_descendant_exempts_element_with_no_text(self):
        """An element with no text but a media-set descendant (img, or
        svg>use) is not empty, even when main lacks the element entirely —
        _mark_media_ancestors marks every open ancestor, not just the
        immediate parent."""
        main = "<p>only text</p>"
        head = (
            "<p>only text</p>"
            '<a href="/x"><img src="a.png" alt=""></a>'
            "<span><svg><use href=\"#i\"/></svg></span>"
        )
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_nested_empty_elements_are_separate_signatures(self):
        """Two DIFFERENT nested empty elements in the same new subtree each
        get their own (tag, attrs, parent_path) signature and are both
        counted: an empty <b> (parent path "p>span") and an empty <span>
        (parent path "p"). The new outer <p> itself carries non-empty text
        ("extra text") so it does not ALSO register as a third empty
        signature — isolating exactly the two nested ones under test."""
        main = "<p>text</p>"
        head = "<p>text</p><p>extra text<span><b></b></span></p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 2)

    def test_parent_path_differs_makes_new_signature(self):
        """The parent-tag-chain is part of the signature key: an empty <b>
        directly under <p> on main and the same empty <b> directly under
        <li> on head are DIFFERENT signatures (documented consequence of
        keying by parent path), so the <li>-parented one is flagged as new
        even though a <b> of this shape already existed on main. Both the
        <p> and <li> wrappers carry their own text so only the <b> itself
        differs, isolating the signature comparison to parent path."""
        main = "<p>text <b></b></p>"
        head = "<ul><li>text <b></b></li></ul>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)


class OriginMainTextMemoizationTests(unittest.TestCase):
    def test_origin_main_text_is_fetched_once_per_path(self):
        """F7a (agy-independent verifier, tools/check_aeo.py:584/:602):
        check_punctuation_artifacts() and check_empty_inline_elements()
        each call _origin_main_text(p) per file, so every page was fetched
        via `git show` TWICE per run. Memoize per rel-path for the
        duration of one run so a repeated lookup of the same path costs
        one subprocess call."""
        ca._origin_main_text_by_rel.cache_clear()
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


class ValueAwareExemptionTests(unittest.TestCase):
    def test_aria_hidden_false_is_flagged(self):
        """F7b (independent verifier, tools/check_aeo.py:363-368):
        _is_aria_hidden() exempted on attribute-KEY presence only, so
        aria-hidden="false" was wrongly exempted like a real
        decorative/hidden element. Measured on the site: 91 aria-hidden
        usages, all "true", so this must not change current-main output."""
        main = "<p>text</p>"
        head = '<p>text</p><span aria-hidden="false"></span>'
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)

    def test_aria_hidden_true_still_exempt(self):
        main = "<p>text</p>"
        head = '<p>text</p><span aria-hidden="true"></span>'
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(result, [])

    def test_empty_id_attribute_is_flagged(self):
        """id="" is not a real anchor target, so it must not exempt an
        otherwise-empty <b>."""
        main = "<p>text</p>"
        head = '<p>text</p><b id=""></b>'
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)


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


class ImplicitCloseTests(unittest.TestCase):
    def test_implicit_p_close_gives_flat_parent_path(self):
        """`<p>one<p>two<b></b>` has no closing </p> tags at all: opening
        the second <p> while a <p> is the innermost open element implicitly
        closes the first (per _IMPLICIT_CLOSE_ON), so the empty <b></b> is a
        child of the SECOND <p>, with parent_path "p" (flat, one level) —
        NOT "p>p" (which would imply the second <p> nested inside the
        first). Verified directly against _scan_empty_elements() output,
        confirming HTMLParser's implicit-close handling here matches the
        real HTML5 parsing rule for this pair."""
        head = "<p>one<p>two<b></b>"
        records = ca._scan_empty_elements(head)
        self.assertEqual(len(records), 1)
        parent_path = records[0]["key"][2]
        self.assertIn("p", parent_path)
        self.assertNotIn("p>p", parent_path)
        self.assertEqual(parent_path, "p")

        main = "<p>one<p>two"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("under p ", result[0])
        self.assertNotIn("under p>p", result[0])


class SelfClosedTagTests(unittest.TestCase):
    def test_self_closed_svg_children_do_not_become_ancestors(self):
        """[HIGH] agy, tools/check_aeo.py:327 (full diff 5a62161..746cd77):
        handle_startendtag overrides HTMLParser.handle_startendtag without
        calling handle_endtag, leaving non-void self-closing elements
        unclosed on self.stack — foreign-content markup like
        `<svg><path/><use/></svg>` pushes `path` and `use` and leaves them
        open until `</svg>` pops everything above it, so every later
        sibling would be wrongly attributed under `path`/`use` instead of
        the real parent. The `<svg>` closes before the `<b>`, so the `<b>`'s
        parent path is `span`, not `span>svg>path>use`."""
        main = "<p>t</p>"
        head = '<p>t</p><span><svg><path d="M0 0"/><use href="#i"/></svg><b></b></span>'
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("under span ", result[0])
        self.assertNotIn("path", result[0])

    def test_self_closed_non_void_element_is_closed_immediately(self):
        """A self-closed non-void element (`<i/>`) must be closed the
        moment it is encountered, exactly like a real `<i></i>` pair —
        the text that follows it belongs to its PARENT, not to the
        (already-closed) `<i>` itself."""
        main = "<p>t</p>"
        head = "<p>t</p><p><i/> text</p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<i>", result[0])

    def test_self_closed_void_tag_still_never_pushed(self):
        """A self-closed void element (`<br/>`) must still never be
        pushed onto the stack at all — it must not appear in the parent
        path of a later sibling, and closing it must not double-pop a
        real element."""
        main = "<p>t</p>"
        head = "<p>t</p><p><br/><b></b></p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("under p ", result[0])
        self.assertNotIn("br", result[0])


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

    def test_comma_dash_added_elsewhere_is_flagged(self):
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

    def test_comma_dash_stranded_by_deletion_is_flagged(self):
        """The word "Supplier" was deleted from between the comma and the
        dash: on main the comma and dash are separated by "Supplier" so
        _DASH_AFTER_COMMA has 0 matches there; on head, with "Supplier"
        gone, the comma and dash are directly adjacent, giving 1 match — a
        net increase of exactly 1 for this file, correctly flagged."""
        main = "<p>Beans, Supplier — roasted weekly.</p><p>Beans are delivered weekly.</p>"
        head = "<p>Beans, — roasted weekly.</p><p>Beans are delivered weekly.</p>"
        result = ca.new_comma_dash_artifacts(head, main)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
