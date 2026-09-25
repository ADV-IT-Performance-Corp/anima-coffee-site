#!/usr/bin/env python3
"""Every EN answers/*.html page must have a reciprocal UA hreflang alternate:
a real ua/answers/<slug>.html file must exist, the EN page must declare
hreflang="uk" pointing at it, and the UA page must declare hreflang="en"
pointing back at the EN page. This is the regression test for the 13-page
AEO gate failure (2026-09-25): PR #44 tried to exempt these pages from
tools/aeo_seo_check.py instead of fixing them — this test asserts the fix
is real content, not a checker carve-out.

Redirect stubs (meta http-equiv="refresh") are excluded — same exemption
class tools/aeo_seo_check.py already applies to them.

stdlib only (unittest). Usage: python3 tools/test_reciprocal_hreflang.py
"""
import pathlib
import re
import sys
import unittest

SITE = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"


def is_redirect_stub(path):
    try:
        return 'http-equiv="refresh"' in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def en_answer_pages():
    return sorted(
        p for p in (SITE / "answers").glob("*.html")
        if not is_redirect_stub(p)
    )


class ReciprocalHreflangTests(unittest.TestCase):
    def test_every_en_answer_page_has_a_ua_twin_with_reciprocal_hreflang(self):
        missing_twin = []
        missing_en_uk_link = []
        missing_ua_en_link = []

        for en_path in en_answer_pages():
            slug = en_path.name
            ua_path = SITE / "ua" / "answers" / slug
            if not ua_path.exists():
                missing_twin.append(slug)
                continue

            en_html = en_path.read_text(encoding="utf-8", errors="ignore")
            ua_url = f"{BASE}/ua/answers/{slug}"
            if not re.search(
                rf'<link rel="alternate" hreflang="uk" href="{re.escape(ua_url)}"\s*/?>',
                en_html,
            ):
                missing_en_uk_link.append(slug)

            ua_html = ua_path.read_text(encoding="utf-8", errors="ignore")
            en_url = f"{BASE}/answers/{slug}"
            if not re.search(
                rf'<link rel="alternate" hreflang="en" href="{re.escape(en_url)}"\s*/?>',
                ua_html,
            ):
                missing_ua_en_link.append(slug)

        self.assertEqual(missing_twin, [], f"EN pages with no ua/answers/ twin: {missing_twin}")
        self.assertEqual(
            missing_en_uk_link, [],
            f"EN pages missing a hreflang=uk link to their UA twin: {missing_en_uk_link}",
        )
        self.assertEqual(
            missing_ua_en_link, [],
            f"UA twins missing a hreflang=en link back to the EN page: {missing_ua_en_link}",
        )


if __name__ == "__main__":
    unittest.main()
