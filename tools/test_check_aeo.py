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
        fake = mock.Mock(returncode=0, stdout="cached content")
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


class ImplicitCloseOnBlockElementTests(unittest.TestCase):
    def test_implicit_p_close_on_div_start(self):
        """Finding 1 (tools/check_aeo.py:317): `<p>Supplier<div>Other</div>`
        deleted down to `<p><div>Other</div>` must still be caught as a
        deletion. Before the fix, opening <div> while <p> was open nested
        the <div> INSIDE the <p> instead of closing it (no
        _IMPLICIT_CLOSE_ON entry for p->div), so "Other" was misattributed
        to the <p> (which then looked non-empty) and the emptied <p> was
        never flagged. After the fix, <div> starting closes the open <p>
        first, exactly like a real browser, so the now-empty <p> is a new
        empty-element signature."""
        main = "<p>Supplier<div>Other</div></p>"
        head = "<p><div>Other</div></p>"
        records = ca._scan_empty_elements(head)
        p_records = [r for r in records if r["tag"] == "p"]
        self.assertEqual(len(p_records), 1)
        self.assertEqual(p_records[0]["key"][2], "")

        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<p>", result[0])

    def test_implicit_p_close_realistic_variant_service_card(self):
        """Realistic variant drawn from the site's own about.html card
        markup (`<p>...</p><div class="go">...</div>` inside an `<a
        class="svc-card">`): a mechanical deletion that removes a card's
        paragraph text along with its own closing tag, leaving the
        following <div> as what implicitly closes it, must still be
        flagged."""
        main = (
            '<a class="svc-card" href="services.html">'
            '<div class="sc-k">All services</div><h3>Six services</h3>'
            '<p>Equipment, beans, people and support.</p>'
            '<div class="go">See services &rarr;</div></a>'
        )
        head = (
            '<a class="svc-card" href="services.html">'
            '<div class="sc-k">All services</div><h3>Six services</h3>'
            '<p><div class="go">See services &rarr;</div></a>'
        )
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<p>", result[0])

    def test_p_does_not_close_on_inline_element_start(self):
        """Only BLOCK elements trigger the implicit close — an inline
        element (e.g. <b>) starting inside an open <p> must still nest
        normally, not close the <p>."""
        head = "<p>text <b>bold</b> more</p>"
        records = ca._scan_empty_elements(head)
        self.assertEqual(records, [])

    def test_li_closes_on_li_not_on_div(self):
        """<li> only closes on another <li> (per _should_implicit_close),
        not on an arbitrary block element — a <div> nested inside an open
        <li> is legal HTML and must stay nested (proven structurally via a
        tracked <b> inside the <div>, since <div> itself isn't a tracked
        empty-element tag)."""
        head = "<ul><li>one<div><b></b></div></li></ul>"
        records = ca._scan_empty_elements(head)
        b_records = [r for r in records if r["tag"] == "b"]
        self.assertEqual(len(b_records), 1)
        self.assertEqual(b_records[0]["key"][2], "ul>li>div")

        head2 = "<ul><li>one<li>two<b></b></ul>"
        records2 = ca._scan_empty_elements(head2)
        b_records2 = [r for r in records2 if r["tag"] == "b"]
        self.assertEqual(len(b_records2), 1)
        self.assertEqual(b_records2[0]["key"][2], "ul>li")

    def test_tr_closes_open_td_and_previous_tr(self):
        """Starting a new <tr> while a <td> (and its enclosing <tr>) are
        still open closes BOTH — a table row can't nest inside the
        previous row's cell — so a later empty element ends up parented
        under the table, not under the stale row/cell."""
        head = "<table><tr><td>one<tr><td><b></b></table>"
        records = ca._scan_empty_elements(head)
        b_records = [r for r in records if r["tag"] == "b"]
        self.assertEqual(len(b_records), 1)
        # Exactly one <tr> and one <td> deep — the stale first row/cell was
        # closed by the implicit-close loop, not left as a phantom ancestor.
        self.assertEqual(b_records[0]["key"][2], "table>tr>td")


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

    def test_self_closed_non_void_element_is_not_closed_immediately(self):
        """Finding 2 (tools/check_aeo.py:356): a self-closed non-void
        element (`<i/>`) must NOT be closed the moment it is encountered —
        browsers ignore the trailing "/" on a non-void tag and leave it
        open exactly like a real `<i>`, so the text that follows belongs
        INSIDE it, not to its parent. `<p><i/> text</p>` must not be
        flagged as an empty <i> — the old immediate-close behaviour was a
        false positive that would have blocked a legitimate PR."""
        main = "<p>t</p>"
        head = "<p>t</p><p><i/> text</p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(result, [])

    def test_self_closed_non_void_element_keeps_following_markup_nested(self):
        """Structural proof for the finding-2 fix: since `<i/>` does not
        close immediately, a `<b></b>` right after it is a CHILD of `<i>`,
        not a sibling — parent_path "i", not "" (flat)."""
        head = "<i/><b></b></i>"
        records = ca._scan_empty_elements(head)
        b_records = [r for r in records if r["tag"] == "b"]
        self.assertEqual(len(b_records), 1)
        self.assertEqual(b_records[0]["key"][2], "i")

    def test_self_closed_void_tag_still_never_pushed(self):
        """A self-closed void element (`<br/>`) must still never be
        pushed onto the stack at all — it must not appear in the parent
        path of a later sibling, and closing it must not double-pop a
        real element. `main` already has the surrounding `<p><br/></p>`
        (itself an empty <p>, since a lone <br/> contributes no text
        either way) so only the new `<b>` is a net-new signature."""
        main = "<p>t</p><p><br/></p>"
        head = "<p>t</p><p><br/><b></b></p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("under p ", result[0])
        self.assertNotIn("br", result[0])


class SelfClosedWhileSkippingTests(unittest.TestCase):
    def test_self_closed_skip_tag_inside_skipped_subtree_sticks_documented(self):
        """Finding 2 retires the special-case immediate-close for
        self-closing tags: a self-closing tag is now ALWAYS just a start
        tag, with no carve-out for skip-subtree tags (an earlier round had
        added exactly that carve-out; finding 2 supersedes it). A
        self-closed `<script/>` (or `<template/>`) encountered WHILE
        ALREADY skipping therefore pushes onto `_skip_stack` like any
        nested skip tag and is never popped — no matching end tag for it
        exists in this markup — so the enclosing skip region stays stuck
        open for the rest of the document. Documented, not "fixed": same
        class of accepted limitation as
        test_mismatched_nested_skip_tags_close_by_name_not_by_position
        below — both the head and origin/main copies of a file run through
        this SAME parser, so identical markup at the divergence point
        produces identical (swallowed) output on both sides and never
        surfaces as a false positive. This shape does not occur on the
        real site: 0 self-closing non-void tags site-wide (verified
        2026-09-19)."""
        main = "<template><script/></template>"
        head = "<template><script/></template><b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(result, [])

        main2 = "<template><template/></template>"
        head2 = "<template><template/></template><b></b>"
        result2 = ca.new_empty_inline_elements(head2, main2)
        self.assertEqual(result2, [])

    def test_self_closed_other_tag_inside_skipped_subtree_is_ignored(self):
        """A self-closed NON-skip tag encountered while already skipping
        (e.g. `<b/>` inside `<template>`) must not touch `_skip_stack` at
        all in either handle_starttag (nothing pushed, tag is not a
        skip-subtree tag) or handle_endtag (top of stack is `template`,
        not `b`, so the stray pop is ignored) — the skip region must close
        cleanly on the real `</template>` and elements after it must be
        seen normally."""
        main = "<p>t</p>"
        head = "<template><b/></template><p>t</p><i></i>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<i>", result[0])
        self.assertNotIn("<b>", result[0])

    def test_self_closed_void_tag_while_skipping_is_never_pushed(self):
        """A self-closed VOID tag while skipping (`<br/>` inside
        `<template>`) must never reach handle_endtag at all (void tags are
        excluded from the endtag call regardless of skip state) and must
        leave `_skip_stack` untouched, so the skip region still closes
        cleanly on the real `</template>`."""
        main = "<template><br/></template>"
        head = "<template><br/></template><b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)

    def test_stray_end_tag_for_never_opened_skip_tag_is_ignored(self):
        """An end tag for a skip-subtree tag that was never opened, seen
        while NOT skipping, must be ignored like any other stray end tag
        (no matching entry on `_skip_stack`, which is empty) — it must not
        put the scanner into skip mode or swallow anything that follows."""
        main = ""
        head = "</script><b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<b>", result[0])

    def test_mismatched_nested_skip_tags_close_by_name_not_by_position(self):
        """Malformed markup: `<template><style></template></style><b></b>`
        closes its two skip-subtree tags in the WRONG order. Documented
        behaviour (not "fixed" — this is invalid HTML, not a case worth
        chasing standards-compliant error recovery for): handle_endtag
        matches the _skip_stack TOP by tag name. `</template>` arrives
        while the top is `style`, so it is treated as a stray nested tag
        and ignored; `</style>` then matches and pops, leaving `template`
        stuck on `_skip_stack` forever (no further `</template>` exists).
        The scanner never leaves skip mode, so the trailing `<b></b>` is
        swallowed. Since both the head and origin/main copies of a file go
        through this same parser, identical malformed markup on both sides
        produces identical (empty) output and never surfaces as a false
        positive or false negative in the diff."""
        html = "<template><style></template></style><b></b>"
        records = ca._scan_empty_elements(html)
        self.assertEqual(records, [])

    def test_implicit_close_is_not_confused_by_an_intervening_skip_region(self):
        """A skip-subtree region sitting between two implicitly-closing
        `<p>` tags must not change which element the second `<p>` closes,
        nor where a later empty element's parent path points: `<p>a
        <template>z</template><p>b<b></b>` closes the FIRST `<p>` when the
        second `<p>` opens (per `_IMPLICIT_CLOSE_ON`), so the empty `<b>`'s
        parent path is flat `p` (the second `<p>`), not `p>p` or anything
        involving `template`."""
        main = "<p>a<template>z</template><p>b"
        head = "<p>a<template>z</template><p>b<b></b>"
        records = ca._scan_empty_elements(head)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["key"][2], "p")

        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("under p ", result[0])


class EofOpenElementTests(unittest.TestCase):
    def test_element_still_open_at_eof_is_recorded(self):
        """Finding 3 (tools/check_aeo.py:291): a page ending `<p>Supplier`
        (perfectly valid HTML — `<p>` has an optional end tag) mechanically
        deleted down to a page ending just `<p>` must still be caught.
        Before the fix, an element still open when the document ends was
        silently discarded and never evaluated for emptiness on either
        side."""
        main = "<p>Supplier"
        head = "<p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<p>", result[0])

    def test_inline_element_still_open_at_eof_is_recorded(self):
        """Not only optional-end-tag block elements — ANY element left
        open at EOF (e.g. a missing `</b>`) must be recorded too."""
        main = "<b>Supplier"
        head = "<b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<b>", result[0])

    def test_element_open_at_eof_unchanged_both_sides_is_not_flagged(self):
        """A page that has ALWAYS ended unclosed (no deletion happened)
        must not be flagged just because the EOF-open element is now
        evaluated — both sides produce the same (empty) record and net to
        zero."""
        main = "<p>"
        head = "<p>"
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_unterminated_skip_subtree_at_eof_does_not_crash(self):
        """An unterminated `<script>` at EOF must not crash the scanner
        and must never itself produce a record (script is never a tracked
        empty-element tag and its skip-root is exempt in `_close_top`),
        even though the EOF flush now walks the whole remaining stack."""
        main = "<script>var x = 1;"
        head = "<script>var x = 1;<b></b>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(result, [])


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

    def test_comma_dash_message_is_labelled_as_scan_line(self):
        """G4 (LOW, coverage — round-2 independent verifier): the failure
        message format is 'scan-line {line}: {ctx!r}' (see
        new_comma_dash_artifacts()'s docstring), not a bare '{line}:'
        implying an original HTML file line number. `line` counts
        newlines in the JOINED scan text (visible text + JSON-LD prose),
        not the source HTML's line numbers — which is why it comes out
        as 5 here even though the dash is on the second visible line of
        the source: _visible_text_for_scan() emits a newline for EACH
        block-tag occurrence (both the opening and closing <p>), so
        '<p>a</p>\\n<p>Beans, — roasted</p>' becomes
        '\\na\\n\\n\\nBeans, — roasted\\n' before the final join appends
        one more trailing newline for the (empty) JSON-LD join — 4
        newlines precede the match, giving line 5. Verified directly
        against _comma_dash_scan_text()'s actual output, not assumed."""
        import pathlib as _pathlib
        p = _pathlib.Path("x.html")
        head_html = "<p>a</p>\n<p>Beans, — roasted</p>"
        main_html = "<p>a</p>\n<p>Beans roasted</p>"
        head_scan = ca._comma_dash_scan_text(p, head_html)
        main_scan = ca._comma_dash_scan_text(p, main_html)
        result = ca.new_comma_dash_artifacts(head_scan, main_scan)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith("scan-line 5: "))
        self.assertIn(", —", result[0])

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


class CommentAndEntityTests(unittest.TestCase):
    """Event-by-state table coverage for the two events _EmptyElementScanner
    never overrides a handler for: comment and entity. `handle_comment` has
    no override (HTMLParser's default is a no-op — a comment never opens,
    closes, or marks text on anything), and the parser is constructed with
    `convert_charrefs=True`, so entities are converted to their character
    and folded into `handle_data` BEFORE handle_data is ever called —
    `handle_entityref`/`handle_charref` are never invoked at all. Both
    behaviours are state-independent (true regardless of what's open), so
    one test per event, exercising it inside an open element, a skip
    region, and at top level, is representative of every state column."""

    def test_comment_is_a_no_op_everywhere(self):
        head = (
            "<!-- top level --><p><!-- inside p -->text</p>"
            "<script><!-- inside script -->x</script>"
            "<template><!-- inside template --><b></b></template>"
        )
        main = "<p>text</p><script>x</script><template><b></b></template>"
        # A comment contributes no text and opens/closes nothing, so its
        # presence or absence changes nothing structurally.
        self.assertEqual(ca.new_empty_inline_elements(head, main), [])

    def test_entity_folds_into_data_everywhere(self):
        main = "<p>&mdash;</p><i>&amp;</i>"
        head = "<p>&mdash;</p><i>&amp;</i><b>&nbsp;</b>"
        # &nbsp; decodes to U+00A0, which handle_data's own
        # `.replace("\xa0", " ").strip()` correctly treats as whitespace-
        # only, so <b> is still empty and gets flagged like any other
        # empty element — entities are not exempt from the whitespace rule.
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<b>", result[0])

    def test_named_entity_counts_as_real_text(self):
        """A genuine (non-whitespace) named entity, e.g. &mdash;, must mark
        its element as non-empty exactly like literal text — proven by
        comparing against a head where the entity was deleted."""
        main = "<p>&mdash;</p>"
        head = "<p></p>"
        result = ca.new_empty_inline_elements(head, main)
        self.assertEqual(len(result), 1)
        self.assertIn("<p>", result[0])


if __name__ == "__main__":
    unittest.main()
