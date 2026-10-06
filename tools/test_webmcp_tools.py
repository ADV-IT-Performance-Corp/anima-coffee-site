#!/usr/bin/env python3
"""Tests for assets/webmcp.js (3 WebMCP tools), the OfferCatalog JSON-LD and
llms.txt consistency. stdlib + pytest + node (no browser, no network).

Usage: python3 -m pytest tools/test_webmcp_tools.py -v

The JS is exercised through tools/webmcp_harness.js, which runs the REAL
assets/webmcp.js inside a node vm with DOM stubs.
"""
import json
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "webmcp_harness.js"

EN_BRANDS = {"Dr. Coffee", "Necta", "La Spaziale", "Nuova Simonelli", "Rancilio",
             "Iberital", "Astoria", "Fiorenzato"}
CATALOG_PAGES = ["index.html", "ua/index.html"]


def run(mode, calls=None):
    out = subprocess.run(
        ["node", str(HARNESS), mode, json.dumps(calls or [])],
        capture_output=True, text=True, check=True, cwd=ROOT,
    ).stdout
    return json.loads(out)


def ask(question, language="en"):
    r = run("document", [{"tool": "get_anima_service_info",
                          "args": {"question": question, "language": language}}])
    return r["results"][0]


# --- 1. brands are answerable (EN + UK) -------------------------------------

@pytest.mark.parametrize("q", [
    "Which machine brands do you offer?",
    "What equipment brands are in your lineup?",
    "Do you install Necta machines?",
])
def test_brands_answered_en(q):
    r = ask(q, "en")
    assert r["published"] is True
    for b in EN_BRANDS:
        assert b in r["answer"], b


@pytest.mark.parametrize("q", [
    "Які бренди кавомашин ви пропонуєте?",
    "Які моделі обладнання у вас є?",
])
def test_brands_answered_uk(q):
    r = ask(q, "uk")
    assert r["published"] is True
    for b in EN_BRANDS:
        assert b in r["answer"], b


def test_venue_specific_model_choice_is_deferred_to_quote_not_invented():
    r = ask("Which exact machine brands and models will you install at my office?")
    assert r["published"] is True
    assert "quote" in r["answer"].lower()


# --- unpublished topics stay unpublished ------------------------------------

@pytest.mark.parametrize("q", [
    "What is the water hardness requirement?",
    "Who is liable if a machine floods the kitchen?",
    "How long is the minimum contract term?",
    "Do you support cashless POS payment on the machine?",
])
def test_unpublished_topics_still_not_published(q):
    r = ask(q)
    assert r["published"] is False
    assert "not published" in r["answer"].lower()


def test_price_figure_is_not_invented():
    r = ask("What is the exact monthly price in USD for the Pro package?")
    assert not re.search(r"[$€]\s*\d|\d+\s*(usd|eur|uah|грн)", r["answer"], re.I)


# --- 2. get_anima_products ---------------------------------------------------

def products(args=None):
    r = run("document", [{"tool": "get_anima_products", "args": args or {}}])
    return r["results"][0]


def test_products_tool_registered_readonly():
    r = run("document")
    t = {x["name"]: x for x in r["tools"]}["get_anima_products"]
    assert t["annotations"]["readOnlyHint"] is True


def test_products_full_lineup_only_published_items():
    p = products()
    blob = json.dumps(p, ensure_ascii=False)
    for b in EN_BRANDS:
        assert b in blob
    for name in ("Start", "Pro", "Max"):
        assert name in blob
    assert "14-day" in blob and "prepayment" in blob
    assert "Kyiv" in blob
    assert "request_coffee_service_assessment" in blob
    # no invented money figures or specs
    assert not re.search(r"[$€₴]\s*\d|\d\s*(usd|eur|uah|грн)|\bkg\b|\bbar\b|\bwatt", blob, re.I)


@pytest.mark.parametrize("cat,brands", [
    ("super_automatic", {"Dr. Coffee", "Necta"}),
    ("professional_espresso", EN_BRANDS - {"Dr. Coffee", "Necta"}),
])
def test_products_category_filter(cat, brands):
    blob = json.dumps(products({"category": cat}), ensure_ascii=False)
    for b in brands:
        assert b in blob
    for b in EN_BRANDS - brands:
        assert b not in blob, b


def test_products_packages_have_no_prices():
    blob = json.dumps(products({"category": "packages"}), ensure_ascii=False)
    assert "Start" in blob and "Max" in blob
    assert "custom quote" in blob.lower()


def test_products_coffee_category():
    assert "Bellissima" in json.dumps(products({"category": "coffee"}), ensure_ascii=False)


def test_products_uk_language():
    blob = json.dumps(products({"language": "uk"}), ensure_ascii=False)
    assert re.search(r"[а-яіїє]{4}", blob)
    assert "14" in blob


def test_products_unknown_category_not_invented():
    assert products({"category": "espresso_grinders"})["published"] is False


# --- 3. prepare_coffee_quote_request never submits --------------------------

def prep(args, mode="document"):
    return run(mode, [{"tool": "prepare_coffee_quote_request", "args": args}])


ARGS = {"name": "Test Person", "business": "Test Cafe", "city": "Kyiv",
        "machines": "2", "contact": "test@example.invalid", "message": "TEST ONLY"}


def test_prepare_prefills_and_never_submits():
    r = prep(ARGS)
    res = r["results"][0]
    assert res["prefilled"] is True
    assert res["submitted"] is False
    assert res["next"] == "visitor reviews and presses Get my custom assessment"
    assert r["submitAttempts"] == 0
    assert r["scrolled"] >= 1 and r["focused"]
    for k in ("name", "business", "city", "machines", "contact", "message"):
        assert r["form"][k] == ARGS[k]
    assert r["form"]["company_url"] == ""  # honeypot untouched


def test_prepare_annotations():
    r = run("document")
    t = {x["name"]: x for x in r["tools"]}["prepare_coffee_quote_request"]
    assert t["annotations"]["consequentialHint"] is False
    assert t["annotations"]["readOnlyHint"] is False


def test_prepare_without_form_reports_not_prefilled():
    res = prep(ARGS, "nopage")["results"][0]
    assert res["prefilled"] is False and res["submitted"] is False


def test_prepare_ignores_unknown_and_nonstring_args():
    r = prep({"name": {"x": 1}, "company_url": "spam", "city": "Kyiv"})
    assert r["form"]["company_url"] == ""
    assert r["form"]["name"] == ""
    assert r["form"]["city"] == "Kyiv"
    assert r["submitAttempts"] == 0


# --- registration: exactly once, both contexts, polyfill path ----------------

@pytest.mark.parametrize("mode", ["document", "navigator"])
def test_three_tools_registered_exactly_once(mode):
    r = run(mode)  # harness loads webmcp.js TWICE
    names = sorted(t["name"] for t in r["tools"])
    assert names == ["get_anima_products", "get_anima_service_info",
                     "prepare_coffee_quote_request"]


def test_polyfill_not_loaded_when_native_exists():
    for mode in ("document", "navigator"):
        assert run(mode)["injectedScripts"] == []


def test_polyfill_loaded_once_from_self_hosted_pinned_path_when_missing():
    r = run("none")
    assert len(r["injectedScripts"]) == 1
    url = r["injectedScripts"][0]
    assert url.startswith("https://aeo.animacoffee.com.ua/assets/vendor/")
    assert "@latest" not in url and "cdn" not in url and "unpkg" not in url
    assert len(r["tools"]) == 3  # registered after the polyfill came up


def test_vendored_polyfill_pinned_with_license():
    d = ROOT / "assets" / "vendor" / "mcp-b-global"
    assert (d / "LICENSE").read_text().startswith("MIT License")
    meta = (d / "VERSION.txt").read_text()
    assert "@mcp-b/global" in meta and re.search(r"\b5\.1\.0\b", meta)
    assert re.search(r"sha256:\s*[0-9a-f]{64}", meta)
    assert (d / "index.iife.js").stat().st_size > 10000


# --- 4. JSON-LD OfferCatalog -------------------------------------------------

LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def graph_nodes(rel):
    nodes = []
    for m in LD_RE.finditer((ROOT / rel).read_text(encoding="utf-8")):
        d = json.loads(m.group(1))  # must parse
        nodes.extend(d.get("@graph", [d]))
    return nodes


def catalog_of(rel):
    for n in graph_nodes(rel):
        c = n.get("hasOfferCatalog")
        if n.get("@type") == "Service" and c:
            return c
    return None


@pytest.mark.parametrize("rel", CATALOG_PAGES)
def test_offer_catalog_present_and_valid(rel):
    c = catalog_of(rel)
    assert c and c["@type"] == "OfferCatalog"
    items = c["itemListElement"]
    assert items and all(i["@type"] == "Offer" for i in items)
    blob = json.dumps(c, ensure_ascii=False)
    assert "priceSpecification" not in blob and '"price"' not in blob
    assert "Kyiv" in blob or "Київ" in blob


@pytest.mark.parametrize("rel", CATALOG_PAGES)
def test_offer_catalog_brands_match_llms_txt(rel):
    c = catalog_of(rel)
    brands = set()
    for i in c["itemListElement"]:
        b = (i.get("itemOffered") or {}).get("brand")
        if b:
            brands.add(b["name"])
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    line = next(l for l in llms.splitlines() if l.startswith("- Equipment:"))
    assert {b for b in EN_BRANDS if b in line} == EN_BRANDS
    assert brands == EN_BRANDS
    names = " ".join(i["itemOffered"]["name"] for i in c["itemListElement"])
    for p in ("Start", "Pro", "Max"):
        assert p in names


# --- 6. llms.txt lists the three tools --------------------------------------

def test_llms_txt_lists_three_tools():
    t = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for n in ("get_anima_service_info", "get_anima_products",
              "prepare_coffee_quote_request", "request_coffee_service_assessment"):
        assert n in t
    assert "exact machine brand list" not in t  # the old contradiction


# --- review round 1 (codex unavailable; gstack-review fallback) -------------

def test_maintenance_question_mentioning_equipment_is_not_hijacked_by_brands():
    r = ask("Is maintenance included for the equipment?")
    assert r["published"] is True
    assert "filtration" in r["answer"].lower()
    assert "Necta" not in r["answer"]


def test_necta_keyword_is_word_bounded():
    r = ask("Is the nectar syrup included?")
    assert "Necta" not in r["answer"]
