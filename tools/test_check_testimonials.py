#!/usr/bin/env python3
"""Unit tests for tools/check_testimonials.py (the "no testimonials may be
published" gate, owner decision 2026-11-02).

stdlib only (unittest). Usage: python3 tools/test_check_testimonials.py

Uses only synthetic respondent names ("Тестенко" / "Testenko") - never a
real custdev interviewee name.
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_testimonials as ct  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

SYNTH_NAMES = ["Тестенко", "Testenko"]

CLEAN_PAGE = "<h1>Coffee service</h1><p>24/7 support, free 14-day trial.</p>"


class ScanTextTests(unittest.TestCase):
    def test_clean_page_passes(self):
        self.assertEqual(ct.scan_text("index.html", CLEAN_PAGE), [])

    def test_testimonial_figure_fails(self):
        html = '<figure class="testi"><blockquote lang="uk"><p>Quote.</p></blockquote></figure>'
        errors = ct.scan_text("index.html", html)
        self.assertTrue(any("testimonial" in e for e in errors))

    def test_testimonials_section_id_fails(self):
        errors = ct.scan_text("index.html", '<section id="testimonials"><h2>Reviews</h2></section>')
        self.assertTrue(any('id="testimonials"' in e for e in errors))

    def test_testimonials_anchor_link_fails(self):
        errors = ct.scan_text("index.html", '<a href="#testimonials">Reviews</a>')
        self.assertTrue(any("#testimonials" in e for e in errors))

    def test_customer_testimonials_heading_fails(self):
        errors = ct.scan_text("llms.txt", "## Customer testimonials\n- quote\n")
        self.assertTrue(any("heading" in e for e in errors))

    def test_review_jsonld_fails(self):
        errors = ct.scan_text("index.html", '{"@type":"AggregateRating","ratingValue":"5"}')
        self.assertTrue(any("Review/AggregateRating" in e for e in errors))

    def test_each_named_persona_fails(self):
        for name in ct.NAMED_PERSONAS:
            errors = ct.scan_text("about.html", f"<p>... {name} ...</p>")
            self.assertTrue(any("named persona" in e for e in errors), name)

    def test_unrelated_names_pass(self):
        self.assertEqual(ct.scan_text("about.html", "<p>Oleksandr from the support line.</p>"), [])


class LoadCustdevNamesTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(ct.load_custdev_names(pathlib.Path("/nonexistent/custdev-names.txt")))

    def test_present_file_returns_names(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "names.txt"
            p.write_text("Тестенко\n# comment\n\nTestenko\n", encoding="utf-8")
            self.assertEqual(ct.load_custdev_names(p), ["Тестенко", "Testenko"])


class ScanNamesTests(unittest.TestCase):
    def test_detects_synthetic_respondent_name(self):
        errors = ct.scan_names("delivery/notes.md", "respondent Тестенко said great things", SYNTH_NAMES)
        self.assertTrue(any("custdev respondent" in e for e in errors))

    def test_clean_text_has_no_hits(self):
        self.assertEqual(ct.scan_names("delivery/notes.md", "respondent R1 said great things", SYNTH_NAMES), [])


class RepoStateTests(unittest.TestCase):
    """The real repo must publish no testimonials."""

    def test_repo_is_clean(self):
        bad = []
        for rel in ct.tracked_files(ROOT):
            if rel in ct.SELF_EXEMPT:
                continue
            fpath = ROOT / rel
            if not fpath.exists():
                continue
            try:
                text = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            bad.extend(ct.scan_text(rel, text))
        self.assertEqual(bad, [])

    def test_webmcp_has_no_testimonials_topic(self):
        js = (ROOT / "assets" / "webmcp.js").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"re:\s*/[^/]*testimonial", js))


if __name__ == "__main__":
    unittest.main()
