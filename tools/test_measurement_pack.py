#!/usr/bin/env python3
"""Unit tests for the GTM/GA4 measurement pack (slice 4, 2026-09-25).

Verifies docs/measurement/gtm-ga4-import.json:
1. Parses as a GTM container export (exportFormatVersion 2).
2. Contains the required variable, tag and trigger building blocks: a
   `GA4 Measurement ID` constant variable, a Google Tag (GA4 config) firing
   on All Pages, GA4 event tags for `lead_accepted` (marked as a key event)
   and `cta_click` (with a `channel` param sourced from a Data Layer
   Variable), Custom Event triggers for both, and an `ai_referral` trigger +
   tag pair keyed on document.referrer host matching the named AI surfaces.
3. Every GTM-side event name in the pack is actually pushed to dataLayer
   somewhere in this repo's shipped JS (`assets/*.js`) — `lead_accepted`
   must match a live push; `cta_click` is allowed to be pending (another
   slice is landing its dataLayer push separately) as long as the pack
   itself documents it as pending.

stdlib only (unittest + json + re). Usage: python3 tools/test_measurement_pack.py
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACK_PATH = ROOT / "docs" / "measurement" / "gtm-ga4-import.json"
AI_REFERRAL_HOSTS = [
    "chatgpt.com",
    "chat.openai.com",
    "perplexity.ai",
    "gemini.google.com",
    "copilot.microsoft.com",
    "claude.ai",
]


def load_pack():
    with open(PACK_PATH, encoding="utf-8") as f:
        return json.load(f)


def dataLayer_push_events():
    """Every dataLayer.push({event: "..."}) literal found in assets/*.js."""
    events = set()
    pattern = re.compile(r'event:\s*"([a-zA-Z0-9_]+)"')
    for js in (ROOT / "assets").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        events.update(pattern.findall(text))
    return events


class PackStructureTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PACK_PATH.exists(), f"missing {PACK_PATH}")
        self.pack = load_pack()

    def test_export_format_version_2(self):
        self.assertEqual(self.pack.get("exportFormatVersion"), 2)

    def test_container_version_present(self):
        self.assertIn("containerVersion", self.pack)

    def _container(self):
        return self.pack["containerVersion"]

    def test_ga4_measurement_id_constant_variable(self):
        variables = self._container().get("variable", [])
        names = [v.get("name") for v in variables]
        self.assertIn("GA4 Measurement ID", names)
        var = next(v for v in variables if v.get("name") == "GA4 Measurement ID")
        self.assertEqual(var.get("type"), "c")
        param = next(p for p in var.get("parameter", []) if p.get("key") == "value")
        self.assertEqual(param.get("value"), "G-XXXXXXXXXX")

    def test_ga4_config_tag_on_all_pages(self):
        tags = self._container().get("tag", [])
        ga4_config = [t for t in tags if t.get("type") == "gaawc"]
        self.assertTrue(ga4_config, "no Google Tag (GA4 config, type=gaawc) found")
        triggers = self._container().get("trigger", [])
        all_pages = [t for t in triggers if t.get("name") == "All Pages"]
        self.assertTrue(all_pages, "no 'All Pages' trigger found")
        all_pages_id = all_pages[0]["triggerId"]
        self.assertTrue(
            any(all_pages_id in t.get("firingTriggerId", []) for t in ga4_config),
            "GA4 config tag does not fire on the All Pages trigger",
        )

    def _event_tag(self, event_name):
        tags = self._container().get("tag", [])
        matches = [
            t
            for t in tags
            if t.get("type") == "gaawe"
            and any(
                p.get("key") == "eventName" and p.get("value") == event_name
                for p in t.get("parameter", [])
            )
        ]
        self.assertTrue(matches, f"no GA4 event tag for '{event_name}'")
        return matches[0]

    def _custom_event_trigger(self, event_name):
        triggers = self._container().get("trigger", [])
        matches = [
            t
            for t in triggers
            if t.get("type") == "customEvent"
            and any(
                f.get("value") == event_name
                for f in t.get("customEventFilter", [])
                for f in [f.get("parameter", [{}])[0]] if f
            )
        ]
        self.assertTrue(matches, f"no Custom Event trigger for '{event_name}'")
        return matches[0]

    def test_lead_accepted_tag_marked_key_event(self):
        tag = self._event_tag("lead_accepted")
        marked_key_event = any(
            p.get("key") == "markAsConversion" and p.get("value") == "true"
            for p in tag.get("parameter", [])
        )
        self.assertTrue(marked_key_event, "lead_accepted tag not marked as a key event")
        self._custom_event_trigger("lead_accepted")

    def test_cta_click_tag_has_channel_param_from_dlv(self):
        tag = self._event_tag("cta_click")
        event_params = next(
            (p for p in tag.get("parameter", []) if p.get("key") == "eventParameters"),
            None,
        )
        self.assertIsNotNone(event_params, "cta_click tag has no eventParameters")
        channel_params = [
            row
            for row in event_params.get("list", [])
            if any(c.get("key") == "parameter" and c.get("value") == "channel" for c in row.get("map", []))
        ]
        self.assertTrue(channel_params, "cta_click tag has no 'channel' event parameter")
        value_entry = next(c for c in channel_params[0]["map"] if c.get("key") == "parameterValue")
        self.assertTrue(
            value_entry.get("value", "").startswith("{{"),
            "cta_click 'channel' param is not sourced from a variable (Data Layer Variable)",
        )
        self._custom_event_trigger("cta_click")

    def test_ai_referral_trigger_and_tag(self):
        tags = self._container().get("tag", [])
        ai_tags = [
            t
            for t in tags
            if t.get("type") == "gaawe"
            and any(
                p.get("key") == "eventName" and p.get("value") == "ai_referral"
                for p in t.get("parameter", [])
            )
        ]
        self.assertTrue(ai_tags, "no GA4 event tag for 'ai_referral'")
        tag = ai_tags[0]
        event_params = next(
            (p for p in tag.get("parameter", []) if p.get("key") == "eventParameters"),
            None,
        )
        self.assertIsNotNone(event_params, "ai_referral tag has no eventParameters")
        has_ai_source = any(
            any(c.get("key") == "parameter" and c.get("value") == "ai_source" for c in row.get("map", []))
            for row in event_params.get("list", [])
        )
        self.assertTrue(has_ai_source, "ai_referral tag has no 'ai_source' event parameter")

        variables = self._container().get("variable", [])
        referrer_var = [v for v in variables if "ai" in v.get("name", "").lower() and "referr" in v.get("name", "").lower()]
        self.assertTrue(referrer_var, "no referrer-matching variable found for ai_referral")
        found_host = False
        for v in referrer_var:
            blob = json.dumps(v)
            if any(h in blob for h in AI_REFERRAL_HOSTS):
                found_host = True
        self.assertTrue(found_host, "ai_referral variable does not reference the named AI hosts")
        for host in AI_REFERRAL_HOSTS:
            self.assertIn(host, json.dumps(self.pack), f"missing AI referral host {host}")


class EventWiringTests(unittest.TestCase):
    """Every GTM-side event name must be real: either already pushed to
    dataLayer in this repo's JS, or explicitly documented as pending."""

    def setUp(self):
        self.pack = load_pack()
        self.js_events = dataLayer_push_events()

    def test_lead_accepted_is_pushed_in_repo_js(self):
        self.assertIn(
            "lead_accepted",
            self.js_events,
            "lead_accepted is not pushed anywhere in assets/*.js",
        )

    def test_cta_click_pending_or_pushed(self):
        pending = self.pack.get("_metadata", {}).get("pendingEvents", [])
        if "cta_click" not in self.js_events:
            self.assertIn(
                "cta_click",
                pending,
                "cta_click is neither pushed in assets/*.js nor declared pending in the pack",
            )

    def test_ai_referral_is_gtm_native_not_repo_js(self):
        # ai_referral is computed inside GTM from document.referrer — it is
        # never expected to appear as a literal dataLayer.push in repo JS.
        self.assertNotIn("ai_referral", self.js_events)


if __name__ == "__main__":
    unittest.main()
