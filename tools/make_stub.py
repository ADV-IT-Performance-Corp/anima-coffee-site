#!/usr/bin/env python3
"""Generate an old-slug redirect stub: meta refresh + canonical + noindex + plain link.

Usage: tools/make_stub.py <path-to-write> <target-relative-url> <link-text> [--title TITLE]

GitHub Pages serves no server-side redirects, so retired URLs become a tiny
static stub instead of a 404: it sends both users and crawlers on to the
replacement page while keeping the old URL resolvable (required for old
inbound links / cached engine citations).
"""
import sys
import argparse


STUB_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8" />
<meta http-equiv="refresh" content="0; url={target}" />
<link rel="canonical" href="{canonical}" />
<meta name="robots" content="noindex, follow" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<link rel="stylesheet" href="{style_path}" />
</head>
<body>
<p>{moved_text} <a href="{target}">{link_text}</a>.</p>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("target", help="relative URL to redirect to, e.g. ../answers/foo.html")
    ap.add_argument("canonical", help="absolute canonical URL of the target page")
    ap.add_argument("link_text")
    ap.add_argument("--title", default=None)
    ap.add_argument("--lang", default="en", choices=["en", "uk"])
    ap.add_argument("--style-path", default="style.css")
    args = ap.parse_args()

    moved_text = "This page has moved to" if args.lang == "en" else "Ця сторінка переміщена на"
    title = args.title or ("Page moved" if args.lang == "en" else "Сторінку переміщено")

    content = STUB_TEMPLATE.format(
        lang=args.lang,
        target=args.target,
        canonical=args.canonical,
        title=title,
        style_path=args.style_path,
        moved_text=moved_text,
        link_text=args.link_text,
    )
    with open(args.path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote stub {args.path} -> {args.target}")


if __name__ == "__main__":
    main()
