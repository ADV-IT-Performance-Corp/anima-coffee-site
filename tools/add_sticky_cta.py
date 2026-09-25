#!/usr/bin/env python3
"""Add the shared sticky contact CTA bar (id="sticky-cta") to every
indexable page — the "a sticky contact bar is present" Gherkin scenario
(see tools/check_aeo_leads.py's sticky_cta_bar_problems()/
check_sticky_cta_bar(), the statically-checkable subset this patcher makes
pass).

Follows the mechanical-patcher convention used elsewhere in this repo (see
tools/add_lead_form.py, tools/add_lead_honeypot.py): stdlib-only, idempotent
(a page that already has id="sticky-cta" is left untouched). Unlike those
patchers this one targets EVERY indexable page (discovered the same way
tools/check_aeo.py's own checks do: all_html_pages() + is_indexable()),
not a small explicit list, because every indexable page needs the bar.

What gets reused, never invented:
  - The phone number: the page's OWN existing tel: href (verified 2026-09-25
    to be the identical "tel:+380738730145" on every one of the 89 indexable
    pages) — read from the page itself, not hardcoded, so a page with a
    different number would still get ITS OWN number in the bar.
  - Telegram: the site has zero real <a href="https://t.me/...."> anchors
    anywhere (confirmed via grep) — only the JSON-LD Organization "sameAs"
    entry "https://t.me/Animavolitiva". This patcher adds the first real,
    visible Telegram anchor using that exact URL.
  - The lead form: pages that carry their own <section id="cta"> (added by
    tools/add_lead_form.py or already present) link to "#cta" on the same
    page. Pages with no lead form of their own (answers/, blog/ index
    pages, services.html) link to the relevant home page's #cta — root
    index.html for EN pages, ua/index.html for /ua/ pages — computed as a
    proper relative path via os.path.relpath so it works from any depth.

Labels are the site's own established vocabulary, not new marketing copy:
  - EN "Call" — from the existing contact-block ("Call: <a href=tel:...>").
  - EN "Get assessment" — from nav-cta / hero-cta anchors to #cta
    (see index.html's <a class="nav-cta" href="./#cta">Get assessment</a>).
  - UK "Телефонуйте" — the site's own imperative "call" verb, used across
    many ua/ pages' contact call-outs (e.g. ua/how-to-rent.html).
  - UK "Отримати аудит" — from ua/index.html's own nav-cta / hero-cta
    anchors to #cta.
  - "Telegram" is kept as-is in both languages (a brand name; the site's
    own EN prose already writes "on Telegram" verbatim).

Insertion points:
  - <link rel="stylesheet" href="{depth}assets/sticky-cta.css"> right
    before </head>.
  - The #sticky-cta markup + <script src="{depth}assets/sticky-cta.js">
    right before the "<!--contact-block-injected-->" marker every
    indexable page carries near </body> (same universal anchor
    tools/add_lead_form.py uses for its own end-of-body insertions;
    confirmed present on all 89 indexable pages).
  - <body> gets a "has-sticky-cta" class so assets/sticky-cta.css can
    reserve bottom padding (see that file's comment) without touching
    every page's own layout CSS.

Usage:
    python3 tools/add_sticky_cta.py
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo as ca  # noqa: E402 — reuse ROOT/all_html_pages/is_indexable

ROOT = ca.ROOT

STICKY_ID = "sticky-cta"
MARKER = "<!--contact-block-injected-->"
TELEGRAM_HREF = "https://t.me/Animavolitiva"

_TEL_HREF_RE = re.compile(r'href="(tel:[^"]+)"')
_BODY_OPEN_RE = re.compile(r"<body(\s[^>]*)?>")


def is_uk(rel: pathlib.PurePosixPath) -> bool:
    return bool(rel.parts) and rel.parts[0] == "ua"


def _labels(uk: bool) -> dict:
    if uk:
        return {"phone": "\U0001F4DE Телефонуйте", "telegram": "Telegram", "form": "\U0001F4DD Отримати аудит"}
    return {"phone": "\U0001F4DE Call", "telegram": "Telegram", "form": "\U0001F4DD Get assessment"}


def _aria_label(uk: bool) -> str:
    return "Контакти" if uk else "Contact"


def _home_cta_href(rel: pathlib.PurePosixPath) -> str:
    """Relative path (from this page's directory) to the appropriate home
    page's "#cta" anchor: ua/index.html for /ua/ pages, root index.html
    otherwise. Works from any directory depth via os.path.relpath."""
    home = ROOT / ("ua/index.html" if is_uk(rel) else "index.html")
    page_dir = ROOT / rel.parent
    rel_home = os.path.relpath(home, start=page_dir)
    return rel_home.replace(os.sep, "/") + "#cta"


def _asset_href(rel: pathlib.PurePosixPath, asset_name: str) -> str:
    asset = ROOT / "assets" / asset_name
    page_dir = ROOT / rel.parent
    rel_asset = os.path.relpath(asset, start=page_dir)
    return rel_asset.replace(os.sep, "/")


def build_bar(rel: pathlib.PurePosixPath, tel_href: str) -> str:
    uk = is_uk(rel)
    lb = _labels(uk)
    form_href = "#cta" if 'id="cta"' in (ROOT / rel).read_text(encoding="utf-8", errors="ignore") else _home_cta_href(rel)
    return (
        f'<div class="sticky-cta" id="{STICKY_ID}" role="navigation" aria-label="{_aria_label(uk)}">\n'
        f'  <a href="{tel_href}" data-cta-channel="phone">{lb["phone"]}</a>\n'
        f'  <a href="{TELEGRAM_HREF}" target="_blank" rel="noopener" data-cta-channel="telegram">{lb["telegram"]}</a>\n'
        f'  <a href="{form_href}" data-cta-channel="form">{lb["form"]}</a>\n'
        f'</div>\n'
    )


def process(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8", errors="ignore")

    if not ca.is_indexable(text):
        return f"skip {rel} (not indexable)"
    if f'id="{STICKY_ID}"' in text:
        return f"skip {rel} (already has sticky bar)"

    tel_m = _TEL_HREF_RE.search(text)
    if tel_m is None:
        return f"skip {rel} (no existing tel: link to reuse)"
    tel_href = tel_m.group(1)

    if "</head>" not in text or MARKER not in text or not _BODY_OPEN_RE.search(text):
        return f"skip {rel} (missing </head>, <body>, or {MARKER} insertion point)"

    css_href = _asset_href(rel, "sticky-cta.css")
    js_href = _asset_href(rel, "sticky-cta.js")
    bar = build_bar(rel, tel_href)

    new_text = text.replace(
        "</head>",
        f'<link rel="stylesheet" href="{css_href}" />\n</head>',
        1,
    )
    new_text = _BODY_OPEN_RE.sub(
        lambda m: f'<body class="has-sticky-cta"{m.group(1) or ""}>',
        new_text,
        count=1,
    )
    new_text = new_text.replace(
        MARKER,
        bar + f'<script src="{js_href}"></script>\n' + MARKER,
        1,
    )

    path.write_text(new_text, encoding="utf-8")
    return f"updated {rel}"


def main() -> None:
    for path in ca.all_html_pages():
        print(process(path))


if __name__ == "__main__":
    main()
