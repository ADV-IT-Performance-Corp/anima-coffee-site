#!/usr/bin/env python3
"""Add the ChatKit lead concierge (assets/chat.css + assets/chat.js) to every
indexable page that carries the sticky contact bar. Idempotent; stdlib-only;
same mechanical-patcher convention as tools/add_sticky_cta.py.

Per page:
  - <link rel="stylesheet" href="{depth}assets/chat.css"> before </head>
  - <script src="{depth}assets/lead.js"> (only if the page does not already
    load it — the chat delivers through window.animaLead from lead.js) and
    <script src="{depth}assets/chat.js" defer>, right after the page's
    sticky-cta.js script tag.

Usage:
    python3 tools/add_chat_widget.py
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo as ca  # noqa: E402

ROOT = ca.ROOT
STICKY_JS_RE = re.compile(r'<script src="([^"]*)sticky-cta\.js"></script>')


def process(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not ca.is_indexable(text):
        return f"skip {rel} (not indexable)"
    if "assets/chat.js" in text:
        return f"skip {rel} (already has chat widget)"
    m = STICKY_JS_RE.search(text)
    if m is None or "</head>" not in text:
        return f"skip {rel} (no sticky-cta.js anchor or </head>)"
    prefix = m.group(1)  # "" / "../" — the page's own relative asset prefix
    scripts = ""
    if "assets/lead.js" not in text:
        scripts += f'<script src="{prefix}lead.js"></script>\n'
    scripts += f'<script src="{prefix}chat.js" defer></script>'
    new = text.replace("</head>", f'<link rel="stylesheet" href="{prefix}chat.css" />\n</head>', 1)
    new = new.replace(m.group(0), m.group(0) + "\n" + scripts, 1)
    path.write_text(new, encoding="utf-8")
    return f"patched {rel}"


def main() -> int:
    for p in ca.all_html_pages():
        print(process(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
