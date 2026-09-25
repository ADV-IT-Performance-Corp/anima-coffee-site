#!/usr/bin/env python3
"""RED before fix/aeo-gate-150-ua-alternates-2026-09-25: every EN answers/
page must carry a real hreflang="uk" alternate pointing at a UA page that
exists on disk, and that UA page must carry a reciprocal hreflang="en" link
back to the EN page. This closes the 13-page EN-only debt list in
tools/aeo_seo_check.py.EN_ONLY_ANSWER_PAGES for real (a shipped translation,
not a checker exemption) — see PR #44 for the interim exemption this
supersedes.

stdlib only (unittest). Usage: python3 tools/test_reciprocal_hreflang_2026_09_25.py
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANSWERS = ROOT / "answers"


def _is_redirect_stub(p):
    # Same exemption class as tools/aeo_seo_check.py's find_pages(): a
    # legacy-slug meta-refresh stub is deliberately not the authoritative
    # version of anything, so an alternate-language assertion about "this
    # page" doesn't apply to it either.
    try:
        return 'http-equiv="refresh"' in p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _en_answer_pages():
    return sorted(p for p in ANSWERS.glob("*.html") if not _is_redirect_stub(p))


class ReciprocalHreflangTests(unittest.TestCase):
    def test_every_en_answer_page_has_a_real_uk_alternate(self):
        missing = []
        for p in _en_answer_pages():
            html = p.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'hreflang="uk" href="([^"]+)"', html)
            if not m:
                missing.append(p.name)
                continue
            ua_url = m.group(1)
            ua_path = ROOT / ua_url.replace("https://aeo.animacoffee.com.ua/", "")
            if not ua_path.exists():
                missing.append(p.name + " -> " + ua_url + " (file does not exist)")
        self.assertEqual(
            missing, [],
            f"EN answer pages missing a real hreflang=uk alternate: {missing}",
        )

    def test_every_uk_alternate_points_back_at_the_en_page(self):
        mismatched = []
        for p in _en_answer_pages():
            html = p.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'hreflang="uk" href="([^"]+)"', html)
            if not m:
                continue  # covered by the previous test
            ua_url = m.group(1)
            ua_path = ROOT / ua_url.replace("https://aeo.animacoffee.com.ua/", "")
            if not ua_path.exists():
                continue  # covered by the previous test
            ua_html = ua_path.read_text(encoding="utf-8", errors="ignore")
            en_url = "https://aeo.animacoffee.com.ua/answers/" + p.name
            if f'hreflang="en" href="{en_url}"' not in ua_html:
                mismatched.append(p.name)
        self.assertEqual(
            mismatched, [],
            f"UA pages missing a reciprocal hreflang=en back to the EN page: {mismatched}",
        )


if __name__ == "__main__":
    unittest.main()
