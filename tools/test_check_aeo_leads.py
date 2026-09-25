#!/usr/bin/env python3
"""Unit tests for tools/check_aeo_leads.py's pure logic functions.

stdlib + pytest. Usage: python3 -m pytest tools/test_check_aeo_leads.py -v

Uses only synthetic fixture HTML — no real page copy. These tests exist
because the "sticky contact bar" Gherkin scenario is mostly NOT statically
checkable from raw HTML (dataLayer.push is JS runtime behavior, 375px is a
rendering fact) — this file makes the logic function itself meaningfully
red-then-green without needing a real browser, per the slice brief.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo_leads as cl  # noqa: E402


# --- sticky_cta_bar_problems() ----------------------------------------------

class TestStickyCtaBarProblems:
    def test_no_bar_at_all_is_flagged(self):
        """The bar doesn't exist anywhere on the unmodified site yet — the
        baseline RED case."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '</body></html>'
        )
        problems = cl.sticky_cta_bar_problems(html_src)
        assert any("sticky-cta" in p for p in problems)

    def test_unrelated_element_merely_carrying_the_class_does_not_fake_pass(self):
        """Precision requirement from the slice brief: a page must not
        pass just because SOME element somewhere carries class="sticky-cta"
        with unrelated content — only an element identified by
        id="sticky-cta" counts, and its own subtree must carry the real
        tel:/Telegram/#cta links, not just live near a similarly-named
        class."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div class="sticky-cta">unrelated decorative banner, no links here</div>'
            '</body></html>'
        )
        problems = cl.sticky_cta_bar_problems(html_src)
        # no id="sticky-cta" container -> still flagged as missing
        assert any('id="sticky-cta"' in p for p in problems)

    def test_complete_bar_passes(self):
        """A correctly-built bar: reuses the page's own tel:/Telegram
        links (does not invent new ones) and links to the lead form."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div id="sticky-cta" class="sticky-cta">'
            '  <a href="tel:+380738730145" data-cta-channel="phone">Call</a>'
            '  <a href="https://t.me/Animavolitiva" data-cta-channel="telegram">Telegram</a>'
            '  <a href="#cta" data-cta-channel="form">Get a quote</a>'
            '</div>'
            '</body></html>'
        )
        assert cl.sticky_cta_bar_problems(html_src) == []

    def test_bar_present_but_invents_a_different_phone_number_is_flagged(self):
        """The bar must REUSE the page's existing tel: link, not a fresh
        one — a mismatched number is a distinct failure from a missing
        bar."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div id="sticky-cta" class="sticky-cta">'
            '  <a href="tel:+380000000000">Call</a>'
            '  <a href="https://t.me/Animavolitiva">Telegram</a>'
            '  <a href="#cta">Get a quote</a>'
            '</div>'
            '</body></html>'
        )
        problems = cl.sticky_cta_bar_problems(html_src)
        assert any("tel:" in p and "reuse" in p for p in problems)

    def test_bar_missing_telegram_link_is_flagged(self):
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div id="sticky-cta" class="sticky-cta">'
            '  <a href="tel:+380738730145">Call</a>'
            '  <a href="#cta">Get a quote</a>'
            '</div>'
            '</body></html>'
        )
        problems = cl.sticky_cta_bar_problems(html_src)
        assert any("Telegram" in p and "reuse" in p for p in problems)

    def test_bar_missing_form_anchor_is_flagged(self):
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div id="sticky-cta" class="sticky-cta">'
            '  <a href="tel:+380738730145">Call</a>'
            '  <a href="https://t.me/Animavolitiva">Telegram</a>'
            '</div>'
            '</body></html>'
        )
        problems = cl.sticky_cta_bar_problems(html_src)
        assert any("lead form" in p for p in problems)

    def test_page_with_no_reusable_links_at_all_is_flagged_before_bar_check(self):
        """A page with no tel:/Telegram link anywhere has nothing to
        reuse — both problems are reported even before the missing-bar
        problem, since they're independently true."""
        html_src = "<html><body><p>no contact links here</p></body></html>"
        problems = cl.sticky_cta_bar_problems(html_src)
        assert any("tel:" in p and "no existing" in p for p in problems)
        assert any("Telegram" in p and "no existing" in p for p in problems)
        assert any("sticky-cta" in p for p in problems)

    def test_nested_divs_inside_bar_do_not_truncate_extraction(self):
        """The container-extraction helper tracks nesting depth for the
        SAME tag name — a nested <div> inside the bar must not make the
        scanner stop at the first </div> it sees and miss content (like
        the #cta anchor) that comes after it."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<a href="https://t.me/Animavolitiva">Telegram</a>'
            '<div id="sticky-cta" class="sticky-cta">'
            '  <div class="sticky-cta-inner">'
            '    <a href="tel:+380738730145">Call</a>'
            '    <a href="https://t.me/Animavolitiva">Telegram</a>'
            '  </div>'
            '  <a href="#cta">Get a quote</a>'
            '</div>'
            '</body></html>'
        )
        assert cl.sticky_cta_bar_problems(html_src) == []

    def test_telegram_link_inside_script_is_not_counted_as_existing(self):
        """A t.me URL that only appears inside a <script>/JSON-LD block
        (e.g. Organization sameAs) is not a real, clickable page link —
        confirmed against the real site: zero actual <a href="t.me/...">
        anchors exist anywhere, only JSON-LD sameAs mentions."""
        html_src = (
            '<html><body>'
            '<a href="tel:+380738730145">Call</a>'
            '<script type="application/ld+json">'
            '{"sameAs": ["https://t.me/Animavolitiva"]}'
            '</script>'
            '</body></html>'
        )
        assert cl.existing_telegram_href(html_src) is None


# --- lead_form_problems() ---------------------------------------------------

class TestLeadFormProblems:
    def test_missing_lead_form_is_flagged(self):
        html_src = '<html><body><p>no form here</p></body></html>'
        problems = cl.lead_form_problems(html_src)
        assert any("0 element" in p for p in problems)

    def test_two_lead_forms_is_flagged(self):
        """Matches the real site's ppc/ pages, which currently ship TWO
        <form class="lead-form"> elements, neither carrying id="leadForm"."""
        html_src = (
            '<html><body>'
            '<form class="lead-form"></form>'
            '<form class="lead-form"></form>'
            '</body></html>'
        )
        problems = cl.lead_form_problems(html_src)
        assert any("2 element" in p for p in problems)

    def test_complete_form_passes(self):
        html_src = (
            '<html><body>'
            '<form class="lead-form" id="leadForm"></form>'
            '<script src="assets/lead.js"></script>'
            '</body></html>'
        )
        assert cl.lead_form_problems(html_src) == []

    def test_relative_lead_js_path_is_accepted(self):
        """/ua/ and /ppc/ pages reference "../assets/lead.js" — any prefix
        before "assets/lead.js" must be accepted."""
        html_src = (
            '<html><body>'
            '<form class="lead-form" id="leadForm"></form>'
            '<script src="../assets/lead.js"></script>'
            '</body></html>'
        )
        assert cl.lead_form_problems(html_src) == []

    def test_missing_id_is_flagged_separately_from_missing_script(self):
        html_src = '<html><body><form class="lead-form"></form></body></html>'
        problems = cl.lead_form_problems(html_src)
        assert any("leadForm" in p for p in problems)
        assert any("lead.js" in p for p in problems)

    def test_class_token_must_match_exactly_not_substring(self):
        """class="lead-form-wide" must not count as class="lead-form"."""
        html_src = '<html><body><form class="lead-form-wide" id="leadForm"></form></body></html>'
        problems = cl.lead_form_problems(html_src)
        assert any("0 element" in p for p in problems)


# --- contactpoint_problems() -------------------------------------------------

class TestContactpointProblems:
    def test_missing_contactpoint_is_flagged(self):
        org = {"@type": "Organization", "telephone": "+380738730145"}
        problems = cl.contactpoint_problems(org)
        assert any("no contactPoint" in p for p in problems)

    def test_complete_sales_contactpoint_passes(self):
        org = {
            "@type": "Organization",
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "sales",
                "telephone": "+380738730145",
                "email": "animacoffeeco@gmail.com",
                "availableLanguage": ["uk", "en"],
                "areaServed": "UA",
            },
        }
        assert cl.contactpoint_problems(org) == []

    def test_contactpoint_as_array_is_accepted(self):
        org = {
            "@type": "Organization",
            "contactPoint": [
                {
                    "@type": "ContactPoint",
                    "contactType": "support",
                    "telephone": "+380738730145",
                },
                {
                    "@type": "ContactPoint",
                    "contactType": "sales",
                    "telephone": "+380738730145",
                    "email": "animacoffeeco@gmail.com",
                    "availableLanguage": ["uk", "en"],
                    "areaServed": "UA",
                },
            ],
        }
        assert cl.contactpoint_problems(org) == []

    def test_missing_available_language_uk_is_flagged(self):
        org = {
            "@type": "Organization",
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "sales",
                "telephone": "+380738730145",
                "email": "animacoffeeco@gmail.com",
                "availableLanguage": ["en"],
                "areaServed": "UA",
            },
        }
        problems = cl.contactpoint_problems(org)
        assert any("availableLanguage" in p for p in problems)

    def test_wrong_area_served_is_flagged(self):
        org = {
            "@type": "Organization",
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "sales",
                "telephone": "+380738730145",
                "email": "animacoffeeco@gmail.com",
                "availableLanguage": ["uk", "en"],
                "areaServed": "Kyiv Oblast",
            },
        }
        problems = cl.contactpoint_problems(org)
        assert any("areaServed" in p for p in problems)


# --- service_node_problems() -------------------------------------------------

class TestServiceNodeProblems:
    def test_no_service_node_is_flagged(self):
        nodes = [{"@type": "Organization", "@id": "https://x/#organization"}]
        problems = cl.service_node_problems(nodes)
        assert any("no Service node" in p for p in problems)

    def test_service_with_correct_provider_passes(self):
        nodes = [
            {"@type": "Organization", "@id": "https://x/#organization"},
            {"@type": "Service", "provider": {"@id": "https://x/#organization"}},
        ]
        assert cl.service_node_problems(nodes) == []

    def test_service_with_wrong_provider_is_flagged(self):
        nodes = [
            {"@type": "Service", "provider": {"@id": "https://x/#something-else"}},
        ]
        problems = cl.service_node_problems(nodes)
        assert any("provider" in p for p in problems)


# --- faq_problems() ----------------------------------------------------------

class TestFaqProblems:
    def test_visible_qa_without_faqpage_is_flagged(self):
        html_src = (
            '<div class="faq">'
            '<details><summary>What is X?<span class="ico"></span></summary>'
            '<p>X is Y.</p></details>'
            '</div>'
        )
        problems = cl.faq_problems(html_src, nodes=[])
        assert any("no FAQPage" in p for p in problems)

    def test_matching_visible_qa_and_faqpage_passes(self):
        html_src = (
            '<div class="faq">'
            '<details><summary>What is X?<span class="ico"></span></summary>'
            '<p>X is Y.</p></details>'
            '</div>'
        )
        nodes = [{
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": "What is X?",
                             "acceptedAnswer": {"@type": "Answer", "text": "X is Y."}}],
        }]
        assert cl.faq_problems(html_src, nodes) == []

    def test_invented_faqpage_question_not_in_visible_text_is_flagged(self):
        """The reverse "no invented FAQ" check — matches the real site's
        smarttouch-pos-integration.html, which ships a 6-question FAQPage
        whose text appears NOWHERE in the visible page body."""
        html_src = '<html><body><p>Completely unrelated page content.</p></body></html>'
        nodes = [{
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": "Does it integrate with SmartTouch POS?"}],
        }]
        problems = cl.faq_problems(html_src, nodes)
        assert any("not found verbatim" in p for p in problems)

    def test_question_answered_in_prose_outside_faq_block_still_counts(self):
        """The verbatim check runs against the WHOLE page's visible text,
        not just a .faq block — a question echoed in an H2 elsewhere
        still counts as backed."""
        html_src = '<html><body><h2>What is X?</h2><p>Some prose.</p></body></html>'
        nodes = [{
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": "What is X?"}],
        }]
        assert cl.faq_problems(html_src, nodes) == []

    def test_whitespace_and_case_are_normalized(self):
        html_src = '<html><body><p>WHAT   is   X?</p></body></html>'
        nodes = [{
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": "what is x?"}],
        }]
        assert cl.faq_problems(html_src, nodes) == []

    def test_page_with_no_visible_qa_and_no_faqpage_is_not_flagged(self):
        html_src = '<html><body><p>Just prose, no Q&A pattern.</p></body></html>'
        assert cl.faq_problems(html_src, nodes=[]) == []


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
