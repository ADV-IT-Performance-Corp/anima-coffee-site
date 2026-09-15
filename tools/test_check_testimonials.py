#!/usr/bin/env python3
"""Unit tests for tools/check_testimonials.py's scan_page() and the
private-list-driven name check.

stdlib only (unittest). Usage: python3 tools/test_check_testimonials.py

Uses only synthetic respondent names ("Тестенко" / "Testenko") — never a
real custdev interviewee name.
"""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_testimonials as ct  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

PROVENANCE = "Some quote text. Верифіковано тут.\n"

# Synthetic stand-in for the real, private custdev-names list.
SYNTH_NAMES = ["Тестенко", "Testenko"]

GOOD_UA_FIGURE = (
    '<figure class="testi"><blockquote lang="uk"><p>Some quote text.</p>'
    '</blockquote><figcaption><b>Name</b>, Business</figcaption></figure>'
)

GOOD_EN_FIGURE = (
    '<figure class="testi">'
    '<blockquote lang="en"><p>English translation.</p></blockquote>'
    '<figcaption><b>Name</b>, Business</figcaption>'
    '<details class="t-orig"><summary>Original</summary>'
    '<blockquote lang="uk"><p>Some quote text.</p></blockquote></details>'
    '</figure>'
)


class ScanPageTests(unittest.TestCase):
    def test_valid_ua_figure_passes(self):
        errors, count = ct.scan_page("index.html", GOOD_UA_FIGURE, PROVENANCE)
        self.assertEqual(errors, [])
        self.assertEqual(count, 1)

    def test_valid_en_figure_with_original_passes(self):
        errors, count = ct.scan_page("index.html", GOOD_EN_FIGURE, PROVENANCE)
        self.assertEqual(errors, [])
        self.assertEqual(count, 1)

    def test_no_testimonials_on_page_fails(self):
        errors, count = ct.scan_page("index.html", "<p>no testimonials here</p>", PROVENANCE)
        self.assertEqual(count, 0)
        self.assertTrue(any("no <figure" in e for e in errors))

    def test_quote_not_in_provenance_fails(self):
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Invented quote never approved.</p>'
            '</blockquote><figcaption>Name</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE)
        self.assertTrue(any("not found verbatim" in e for e in errors))

    def test_empty_ukrainian_quote_fails(self):
        """codex MEDIUM: a blank/whitespace-only original-language quote
        must fail, not silently pass as "found verbatim" (empty string is
        trivially "in" any provenance text)."""
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>   </p>'
            '</blockquote><figcaption>Name</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE)
        self.assertTrue(any("empty Ukrainian quote" in e for e in errors))

    def test_empty_english_quote_fails(self):
        fig = (
            '<figure class="testi">'
            '<blockquote lang="en"><p></p></blockquote>'
            '<figcaption>Name</figcaption>'
            '<details class="t-orig"><summary>Original</summary>'
            '<blockquote lang="uk"><p>Some quote text.</p></blockquote></details>'
            '</figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE)
        self.assertTrue(any("empty English quote" in e for e in errors))

    def test_forbidden_claim_in_quote_fails(self):
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Дякуємо за retro-bonus щомісяця.</p>'
            '</blockquote><figcaption>Name</figcaption></figure>'
        )
        prov = "Дякуємо за retro-bonus щомісяця.\n"
        errors, _ = ct.scan_page("index.html", fig, prov)
        self.assertTrue(any("forbidden claim" in e for e in errors))

    def test_forbidden_claim_in_en_translation_fails(self):
        fig = (
            '<figure class="testi">'
            '<blockquote lang="en"><p>Thanks for the free first month.</p></blockquote>'
            '<figcaption>Name</figcaption>'
            '<details class="t-orig"><summary>Original</summary>'
            '<blockquote lang="uk"><p>Some quote text.</p></blockquote></details>'
            '</figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE)
        self.assertTrue(any("EN translation contains forbidden claim" in e for e in errors))

    def test_interview_quote_with_synthetic_surname_fails(self):
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Some quote text.</p>'
            '</blockquote><figcaption>Тестенко, Богуслав (2025 customer survey)</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE, SYNTH_NAMES)
        self.assertTrue(any("real interviewee name" in e for e in errors))

    def test_interview_quote_with_transliterated_surname_fails(self):
        """codex round-1 MEDIUM: a Latin transliteration must be caught too,
        not just the Cyrillic spelling."""
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Some quote text.</p>'
            '</blockquote><figcaption>Testenko, Bohuslav (2025 customer survey)</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE, SYNTH_NAMES)
        self.assertTrue(any("real interviewee name" in e for e in errors))

    def test_anonymous_interview_quote_passes(self):
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Some quote text.</p>'
            '</blockquote><figcaption>Business owner, Bohuslav (2025 customer survey)</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE, SYNTH_NAMES)
        self.assertEqual(errors, [])

    def test_interview_name_check_skipped_without_private_list(self):
        """When no private list is loaded (custdev_names=None), the
        interview-name check must not run at all (not silently pass a real
        name through — it simply isn't attempted, matching main()'s SKIP
        behavior when $ANIMA_CUSTDEV_NAMES_FILE is absent)."""
        fig = (
            '<figure class="testi"><blockquote lang="uk"><p>Some quote text.</p>'
            '</blockquote><figcaption>Тестенко, Богуслав (2025 customer survey)</figcaption></figure>'
        )
        errors, _ = ct.scan_page("index.html", fig, PROVENANCE, None)
        self.assertEqual(errors, [])

    def test_missing_testimonials_is_per_page_not_global(self):
        """codex round-1 MEDIUM: a page with zero figures must fail even if
        other pages in the same run have plenty."""
        errors_bad, count_bad = ct.scan_page("about.html", "<p>nothing</p>", PROVENANCE)
        errors_good, count_good = ct.scan_page("index.html", GOOD_UA_FIGURE, PROVENANCE)
        self.assertTrue(any("about.html" in e and "no <figure" in e for e in errors_bad))
        self.assertEqual(errors_good, [])
        self.assertEqual(count_bad, 0)
        self.assertEqual(count_good, 1)


class LoadCustdevNamesTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(ct.load_custdev_names(pathlib.Path("/nonexistent/custdev-names.txt")))

    def test_present_file_returns_names(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "names.txt"
            p.write_text("Тестенко\n# comment\n\nTestenko\n", encoding="utf-8")
            names = ct.load_custdev_names(p)
            self.assertEqual(names, ["Тестенко", "Testenko"])


class ScanRepoForNamesTests(unittest.TestCase):
    def test_detects_name_in_tracked_pattern_file(self):
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "delivery").mkdir()
            leaky = root / "delivery" / "notes.md"
            leaky.write_text("respondent Тестенко said great things", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            errors = ct.scan_repo_for_names(root, SYNTH_NAMES)
            self.assertTrue(any("delivery/notes.md" in e for e in errors))

    def test_clean_repo_has_no_hits(self):
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "delivery").mkdir()
            clean = root / "delivery" / "notes.md"
            clean.write_text("respondent R1 said great things", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            errors = ct.scan_repo_for_names(root, SYNTH_NAMES)
            self.assertEqual(errors, [])


class WebmcpTestimonialsTopicTests(unittest.TestCase):
    """Codex MEDIUM: the 'testimonials' topic in assets/webmcp.js must
    exist, match the expected trigger keywords, and carry no forbidden
    claim or real interviewee name in its canned answers."""

    def setUp(self):
        self.webmcp_js = (ROOT / "assets" / "webmcp.js").read_text(encoding="utf-8")

    def _testimonials_block(self):
        m = re.search(
            r're:\s*/([^/]*testimonial[^/]*)/i,\s*en:\s*"((?:[^"\\]|\\.)*)",\s*uk:\s*"((?:[^"\\]|\\.)*)"',
            self.webmcp_js,
        )
        self.assertIsNotNone(m, "no 'testimonials' topic block found in assets/webmcp.js")
        return m

    def test_topic_regex_matches_uk_and_en_trigger_words(self):
        m = self._testimonials_block()
        pattern = re.compile(m.group(1), re.I)
        self.assertTrue(pattern.search("testimonial"))
        self.assertTrue(pattern.search("Що кажуть клієнти? Відгуки клієнтів"))

    def test_topic_answers_are_non_empty_and_clean(self):
        m = self._testimonials_block()
        en, uk = m.group(2), m.group(3)
        self.assertTrue(en.strip())
        self.assertTrue(uk.strip())
        self.assertEqual(ct.forbidden_hits(en), [])
        self.assertEqual(ct.forbidden_hits(uk), [])


if __name__ == "__main__":
    unittest.main()
