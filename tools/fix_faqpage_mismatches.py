#!/usr/bin/env python3
"""Fix check_aeo_leads.py's "visible Q&A and FAQPage JSON-LD match" check.

Two DIFFERENT fixes were needed (see the task report for the full
rationale):

1. how-to-rent.html / ua/how-to-rent.html: every mismatched FAQPage
   question WAS covered by real visible content (a <details><summary>
   entry), just phrased slightly differently than the JSON-LD `name`.
   Each of those 11 mismatches (6 EN + 5 UA) needed its OWN bespoke
   per-question judgment call to pick the exact matching visible phrasing
   — that is not a mechanical transform, so it was done by hand with the
   Edit tool directly on the two files, not by this script.

2. smarttouch-pos-integration.html / ua/smarttouch-pos-integration.html:
   verified zero <details> elements exist anywhere on either page (grep
   count == 0) — there is no visible Q&A markup at all, so the entire
   FAQPage node is invented structured data with nothing to fix it
   against. Per the truth rule ("pages without visible Q&A never get an
   invented FAQ" — and inventing visible copy to match it would violate
   the rule even harder), this script REMOVES the FAQPage node entirely
   from both pages' JSON-LD @graph. This part IS mechanical (a
   json.loads/dumps node removal), so it lives here.

stdlib only; json.loads/json.dumps discipline, no regex surgery on the
JSON payload itself.

Usage: python3 tools/fix_faqpage_mismatches.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

_BLOCK_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)

REMOVE_FAQPAGE_PAGES = [
    "smarttouch-pos-integration.html",
    "ua/smarttouch-pos-integration.html",
]


def remove_faqpage(html_src: str):
    removed = [False]

    def repl(m):
        prefix, body, suffix = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except Exception:
            return m.group(0)
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            before = len(data["@graph"])
            data["@graph"] = [n for n in data["@graph"]
                               if not (isinstance(n, dict) and n.get("@type") == "FAQPage")]
            if len(data["@graph"]) == before:
                return m.group(0)
        elif isinstance(data, list):
            before = len(data)
            data = [n for n in data
                    if not (isinstance(n, dict) and n.get("@type") == "FAQPage")]
            if len(data) == before:
                return m.group(0)
        elif isinstance(data, dict) and data.get("@type") == "FAQPage":
            removed[0] = True
            return ""  # drop the whole script block
        else:
            return m.group(0)
        removed[0] = True
        new_body = json.dumps(data, ensure_ascii=False, indent=2)
        return prefix + new_body + suffix

    new_html = _BLOCK_RE.sub(repl, html_src)
    return new_html, removed[0]


def main():
    for rel in REMOVE_FAQPAGE_PAGES:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        # Verify the premise before touching anything: zero visible
        # <details> Q&A markup on the page.
        details_count = len(re.findall(r"<details\b", text))
        if details_count != 0:
            print(f"{rel}: ABORTED — page has {details_count} <details> element(s), "
                  f"premise (\"zero visible Q&A markup\") does not hold; not removing FAQPage")
            continue
        new_text, removed = remove_faqpage(text)
        if removed:
            p.write_text(new_text, encoding="utf-8")
            print(f"{rel}: removed FAQPage node (verified 0 <details> elements on page)")
        else:
            print(f"{rel}: SKIPPED (no change — no FAQPage node found, already removed)")


if __name__ == "__main__":
    main()
