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
        """When the exact same preceding text also precedes an
        ALREADY-empty element elsewhere on origin/main, the current
        (Step-A) heuristic treats a genuinely new empty element as
        'already seen' and misses it — a false negative. RED at Step A/B."""
        shared_prefix = "the finest fresh roasted coffee beans that we offer"
        main = (
            f"<p>{shared_prefix}<b></b> for you.</p>"
            f"<p>{shared_prefix}<b>Supplier</b> for you.</p>"
        )
        head = (
            f"<p>{shared_prefix}<b>Supplier</b> for you.</p>"
            f"<p>{shared_prefix}<b></b> for you.</p>"
        )
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)

    def test_exemptions_hold(self):
        """id/name anchor targets, aria-hidden decorative elements, and
        markup inside script/style/template are never flagged regardless
        of history. A class-only span that matches an ALREADY-empty span
        of the same class elsewhere on origin/main should also be exempt
        (position-independent, by class) — that specific exemption is a
        Step C addition, so it is expected to still fail (be flagged) at
        Step A/B; the other three sub-cases already pass at Step A/B."""
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
        # class-only-span-matches-by-class-on-main exemption: NOT implemented
        # at Step A/B (position-dependent context only) -- documents RED.
        self.assertEqual(result, [], "class-only-span exemption not yet implemented (Step C)")


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
        """When the same preceding text also precedes an
        ALREADY-present ', —' elsewhere on origin/main, the current
        (Step-A) heuristic misses a genuinely new stranded ', —' — a
        false negative. RED at Step A/B."""
        shared_prefix = "the finest fresh roasted coffee beans that we offer"
        main = (
            f"<p>{shared_prefix}, — always fresh.</p>"
            f"<p>{shared_prefix}, Supplier — always fresh.</p>"
        )
        head = (
            f"<p>{shared_prefix}, Supplier — always fresh.</p>"
            f"<p>{shared_prefix}, — always fresh.</p>"
        )
        result = ca.new_comma_dash_artifacts(head, main)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
