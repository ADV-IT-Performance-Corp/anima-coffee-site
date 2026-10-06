#!/usr/bin/env python3
"""Add an OfferCatalog ("Coffee equipment rental and service") to the Service
node's JSON-LD on the home pages (EN + UA). Idempotent: re-running replaces
the catalog, never duplicates it. stdlib only; json.loads/json.dumps
discipline (no regex surgery on the JSON payload).

Grounding (truth rule): every Offer lists only what is already published —
the eight equipment brands (llms.txt "Equipment" line, "these eight brands
are the complete lineup") and the Start/Pro/Max packages. Prices are NOT
published, so there is no price / priceSpecification anywhere; the Offers
carry availability and areaServed only (Kyiv and Kyiv Oblast).

Usage: python3 tools/add_offer_catalog.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
_BLOCK_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)

PAGES = {"index.html": "en", "ua/index.html": "uk"}

SUPER = ["Dr. Coffee", "Necta"]
PRO = ["La Spaziale", "Nuova Simonelli", "Rancilio", "Iberital", "Astoria", "Fiorenzato"]
PACKAGES = ["Start", "Pro", "Max"]

AREA = [
    {"@type": "AdministrativeArea", "name": "Kyiv"},
    {"@type": "AdministrativeArea", "name": "Kyiv Oblast"},
]
IN_STOCK = "https://schema.org/InStock"

COPY = {
    "en": {
        "catalog": "Coffee equipment rental and service",
        "super_name": "{b} super-automatic coffee machines (rental with full service)",
        "super_cat": "Super-automatic coffee machine",
        "pro_name": "{b} professional espresso machines (rental with full service)",
        "pro_cat": "Professional espresso machine",
        "pkg_name": "{p} equipment package",
        "pkg_desc": "Equipment package matched to the venue format; custom quote per venue, package contents and prices are not published.",
    },
    "uk": {
        "catalog": "Оренда та сервіс кавового обладнання",
        "super_name": "Суперавтомати {b} (оренда з повним сервісом)",
        "super_cat": "Суперавтомат",
        "pro_name": "Професійні еспресо-машини {b} (оренда з повним сервісом)",
        "pro_cat": "Професійна еспресо-машина",
        "pkg_name": "Пакет обладнання {p}",
        "pkg_desc": "Пакет обладнання під формат об'єкта; індивідуальний розрахунок під об'єкт, вміст пакетів і ціни не публікуються.",
    },
}


def offer(item):
    return {"@type": "Offer", "availability": IN_STOCK, "areaServed": AREA, "itemOffered": item}


def build_catalog(lang):
    c = COPY[lang]
    items = []
    for b in SUPER:
        items.append(offer({
            "@type": "Product", "name": c["super_name"].format(b=b),
            "category": c["super_cat"], "brand": {"@type": "Brand", "name": b}}))
    for b in PRO:
        items.append(offer({
            "@type": "Product", "name": c["pro_name"].format(b=b),
            "category": c["pro_cat"], "brand": {"@type": "Brand", "name": b}}))
    for p in PACKAGES:
        items.append(offer({
            "@type": "Service", "name": c["pkg_name"].format(p=p),
            "description": c["pkg_desc"]}))
    return {"@type": "OfferCatalog", "name": c["catalog"], "itemListElement": items}


def patch(rel, lang):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    done = []

    def sub(m):
        data = json.loads(m.group(2))
        nodes = data.get("@graph", [data])
        hit = False
        for n in nodes:
            if n.get("@type") == "Service":
                n["hasOfferCatalog"] = build_catalog(lang)
                hit = True
        if not hit:
            return m.group(0)
        done.append(1)
        return m.group(1) + json.dumps(data, indent=2, ensure_ascii=False) + m.group(3)

    new = _BLOCK_RE.sub(sub, text)
    if done and new != text:
        path.write_text(new, encoding="utf-8")
    return len(done)


if __name__ == "__main__":
    for rel, lang in PAGES.items():
        print(f"{rel}: {patch(rel, lang)} block(s) patched")
