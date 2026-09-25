#!/usr/bin/env python3
"""Idempotently add a sales ContactPoint to every page's Organization JSON-LD
node (the "Organization exposes a sales ContactPoint" scenario in
tools/check_aeo_leads.py's contactpoint_problems()). stdlib only.

Per-page, per-block: JSON-parses each <script type="application/ld+json">
block (never regex-surgery on the payload, matching
tools/add_localbusiness_schema.py's discipline), locates the Organization
node (by @id ending "#organization", falling back to bare @type ==
"Organization" — mirrors check_aeo_leads.find_organization_node()), and
reads that SAME node's own existing `telephone`/`email` fields rather than
assuming one hardcoded pair (verified 2026-09-25: every Organization node
site-wide already carries the identical +380738730145 /
animacoffeeco@gmail.com, but this script does not hardcode that
assumption — it always reads the value from the node it is patching).

Skips a page/block if:
- it has no Organization node,
- that Organization node already has a contactPoint (idempotent — safe to
  re-run),
- that Organization node is missing telephone or email to copy (nothing
  to safely add without inventing a value — would violate the truth
  rule).

Only the JSON-LD <script> block containing the Organization node is
touched; the rest of the page (and any other ld+json block on the same
page, e.g. a sibling Service/FAQPage block) is left byte-for-byte
unchanged. Re-serializes the whole block via json.dumps so structure is
preserved exactly regardless of pre-existing key ordering.

Usage: python3 tools/add_organization_contactpoint.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_aeo as ca  # noqa: E402 — reuse ROOT/all_html_pages/is_indexable

_BLOCK_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def _flatten(data):
    """Same flattening rule as check_aeo_leads._jsonld_nodes(): @graph list,
    bare top-level list, or a single node."""
    if isinstance(data, dict) and isinstance(data.get("@graph"), list):
        return data["@graph"]
    if isinstance(data, list):
        return data
    return [data]


def _find_org(nodes):
    for n in nodes:
        if isinstance(n, dict) and n.get("@type") == "Organization" and str(n.get("@id", "")).endswith("#organization"):
            return n
    for n in nodes:
        if isinstance(n, dict) and n.get("@type") == "Organization":
            return n
    return None


def patch_html(html_src: str):
    """Returns (new_html, notes) where notes is a list of per-block strings
    describing what happened (added / skipped-already-present /
    skipped-no-org / skipped-missing-telephone-or-email)."""
    notes = []

    def repl(m):
        prefix, body, suffix = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except Exception as e:
            notes.append(f"skip block (unparseable: {e})")
            return m.group(0)
        nodes = _flatten(data)
        org = _find_org(nodes)
        if org is None:
            return m.group(0)  # not the Organization block; leave untouched
        if org.get("contactPoint") is not None:
            notes.append("skip (contactPoint already present)")
            return m.group(0)
        telephone = org.get("telephone")
        email = org.get("email")
        if not telephone or not email:
            notes.append("skip (Organization node missing telephone or email to copy)")
            return m.group(0)
        org["contactPoint"] = {
            "@type": "ContactPoint",
            "contactType": "sales",
            "telephone": telephone,
            "email": email,
            "availableLanguage": ["uk", "en"],
            "areaServed": "UA",
        }
        notes.append("added contactPoint")
        new_body = json.dumps(data, ensure_ascii=False, indent=2)
        return prefix + new_body + suffix

    new_html = _BLOCK_RE.sub(repl, html_src)
    return new_html, notes


def main():
    patched = []
    skipped = []
    for p in ca.all_html_pages():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not ca.is_indexable(text):
            continue
        new_text, notes = patch_html(text)
        rel = str(p.relative_to(ROOT))
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            patched.append(rel)
        elif any("skip" in n for n in notes) and "already present" not in " ".join(notes):
            # Only report genuinely interesting skips (missing tel/email);
            # "no Organization node on this page" is silent/expected.
            interesting = [n for n in notes if "already present" not in n]
            if interesting:
                skipped.append((rel, interesting))

    print(f"patched {len(patched)} page(s):")
    for rel in patched:
        print(f"  {rel}")
    if skipped:
        print(f"\nskipped {len(skipped)} page(s) with an Organization node but missing telephone/email:")
        for rel, notes in skipped:
            print(f"  {rel}: {notes}")


if __name__ == "__main__":
    main()
