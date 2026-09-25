#!/usr/bin/env python3
"""Generate an OKF (Open Knowledge Format) knowledge bundle under knowledge/
from the JSON-LD @graph already published in index.html.

This does not invent facts: every generated page reflects only the
registry-approved knowledge-graph triples already embedded on the live site
(schema.org nodes inside the <script type="application/ld+json"> block in
index.html). See:
https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing

For each @graph node that carries a `name` (structural nodes with no name,
e.g. BreadcrumbList/FAQPage, are skipped — they have nothing to title a
knowledge page with), this emits one markdown file at
knowledge/<type>-<name-slug>.md with YAML frontmatter (type, title,
description, resource, tags, timestamp) plus a body listing the node's
remaining schema.org properties as `- predicate — value` lines.

Also emits/updates:
  - knowledge/index.md   — links + one-line description per generated page
  - knowledge/log.md     — append-only generation log (one line per run;
                            the one intentional exception to byte-identical
                            output across repeated runs)
  - llms.txt             — adds exactly one bundle link line, idempotently

Output is deterministic across repeated runs against the same index.html:
no wall-clock timestamps in content (a fixed SOURCE_DATE is used), all
dict/list iteration is sorted or preserves source order, no path is written
outside knowledge/ or llms.txt. The only intentional exception is log.md,
which appends one new dated line per run.

Usage: python3 tools/gen_okf_bundle.py [--root PATH]

--root lets callers (tests) point the generator at an isolated copy of the
repo instead of mutating the live working tree; it defaults to the real
repo root so the normal invocation is unchanged.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"

# Fixed source date for generated content — NOT wall-clock time, so the
# fact pages stay byte-identical across repeated runs. log.md is the one
# documented exception (it timestamps the run itself).
SOURCE_DATE = "2026-09-25"

BUNDLE_URL = f"{BASE}/knowledge/index.md"
BUNDLE_LINE = f"- [OKF knowledge bundle]({BUNDLE_URL})"

# Frontmatter/heading fields already surfaced elsewhere in the page; don't
# repeat them in the "- predicate — value" property list.
SKIP_PROPERTY_KEYS = {"@type", "name", "description"}


def slugify(text):
    if isinstance(text, list):
        text = "-".join(str(item) for item in text)
    original = str(text)
    slug = re.sub(r"[^a-z0-9]+", "-", original.lower()).strip("-")
    if not slug:
        # Non-ASCII (e.g. Cyrillic) or otherwise unslugifiable source: fall
        # back to a stable hash of the ORIGINAL text rather than collide on
        # a shared empty string.
        slug = "n-" + hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
    return slug


def type_label(node_type):
    """@type is usually a string but schema.org allows a list (e.g.
    ["Organization", "LocalBusiness"]) — use the first entry as the label."""
    if isinstance(node_type, list):
        return str(node_type[0]) if node_type else "Thing"
    return str(node_type)


def flatten(value):
    """Render an arbitrary JSON-LD value as a single deterministic line."""
    if isinstance(value, dict):
        parts = [f"{k}: {flatten(value[k])}" for k in sorted(value.keys())]
        return "; ".join(parts)
    if isinstance(value, list):
        return ", ".join(flatten(item) for item in value)
    return str(value)


def yaml_str(value):
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def extract_graph(html):
    m = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    if not m:
        raise SystemExit("gen_okf_bundle: no JSON-LD block found in index.html")
    data = json.loads(m.group(1))
    if not isinstance(data, dict) or "@graph" not in data:
        raise SystemExit("gen_okf_bundle: JSON-LD block has no @graph")
    return data["@graph"]


def entity_nodes(graph):
    """Nodes with a `name` — skip pure-structural nodes (BreadcrumbList,
    FAQPage) that have nothing to title a knowledge page with."""
    return [n for n in graph if isinstance(n, dict) and n.get("name")]


def node_description(node):
    desc = node.get("description")
    if desc:
        return desc
    # No description on this node in the source JSON-LD (e.g. WebSite) —
    # describe the entity structurally instead of inventing a fact.
    return (
        f"{node['name']} — a {type_label(node['@type'])} entity from the "
        f"Anima Volitiva knowledge graph published at {BASE}/."
    )


def build_page(node, resource_url):
    node_type = type_label(node["@type"])
    name = node["name"]
    # Slugify type and name independently (not the joined string) so a
    # non-ASCII name that strips to empty still falls back to its own hash
    # instead of colliding with another entity of the same @type.
    slug = f"{slugify(node_type)}-{slugify(name)}"
    description = node_description(node)
    tags = sorted({"okf", "schema.org", slugify(node_type)})

    lines = ["---"]
    lines.append(f"type: {yaml_str(node_type)}")
    lines.append(f"title: {yaml_str(name)}")
    lines.append(f"description: {yaml_str(description)}")
    lines.append(f"resource: {yaml_str(resource_url)}")
    lines.append(f"tags: [{', '.join(tags)}]")
    lines.append(f"timestamp: {yaml_str(SOURCE_DATE)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("")
    lines.append(description)
    lines.append("")

    prop_keys = sorted(k for k in node.keys() if k not in SKIP_PROPERTY_KEYS)
    if prop_keys:
        for key in prop_keys:
            lines.append(f"- {key} — {flatten(node[key])}")
    else:
        lines.append(f"- resource — {resource_url}")
    lines.append("")

    content = "\n".join(lines)
    return slug, content, description


def write_if_changed(path, content):
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def update_llms_txt(llms_txt_path):
    if not llms_txt_path.exists():
        return
    content = llms_txt_path.read_text(encoding="utf-8")
    if BUNDLE_LINE in content:
        return
    marker = "\n## Customer testimonials"
    idx = content.find(marker)
    if idx == -1:
        # Fallback: append at end of file (still exactly one new line).
        new_content = content.rstrip("\n") + "\n" + BUNDLE_LINE + "\n"
    else:
        new_content = content[:idx] + BUNDLE_LINE + "\n" + content[idx:]
    llms_txt_path.write_text(new_content, encoding="utf-8")


def update_log(knowledge_dir, digest, page_count):
    header = (
        "# OKF knowledge bundle — generation log\n\n"
        "One line per run. sha256 digests the generated entity/index page "
        "content (log.md itself excluded); an unchanged digest across runs "
        "confirms the source JSON-LD did not change.\n\n"
    )
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"- {run_ts} sha256={digest} pages={page_count}\n"
    log_path = knowledge_dir / "log.md"
    if not log_path.exists():
        log_path.write_text(header + line, encoding="utf-8")
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)


def main(root=REPO_ROOT):
    root = Path(root)
    knowledge_dir = root / "knowledge"
    index_html = root / "index.html"
    llms_txt = root / "llms.txt"

    knowledge_dir.mkdir(parents=True, exist_ok=True)

    html = index_html.read_text(encoding="utf-8")
    graph = extract_graph(html)
    nodes = entity_nodes(graph)
    if not nodes:
        raise SystemExit("gen_okf_bundle: no named entities found in @graph")

    # All facts here come from the JSON-LD embedded in index.html — that is
    # the resource every generated page traces back to.
    resource_url = f"{BASE}/index.html"

    pages = []  # (slug, content, title, description)
    for node in nodes:
        slug, content, description = build_page(node, resource_url)
        pages.append((slug, content, node["name"], description))

    pages.sort(key=lambda p: p[0])

    written = {}
    for slug, content, _title, _description in pages:
        path = knowledge_dir / f"{slug}.md"
        write_if_changed(path, content)
        written[slug] = content

    index_lines = ["---"]
    index_lines.append(f"type: {yaml_str('Index')}")
    index_lines.append(f"title: {yaml_str('OKF knowledge bundle')}")
    index_lines.append(
        f"description: {yaml_str('Machine-readable knowledge pages for aeo.animacoffee.com.ua, generated from the site’s published schema.org JSON-LD.')}"
    )
    index_lines.append(f"resource: {yaml_str(resource_url)}")
    index_lines.append("tags: [okf, schema.org, index]")
    index_lines.append(f"timestamp: {yaml_str(SOURCE_DATE)}")
    index_lines.append("---")
    index_lines.append("")
    index_lines.append("# OKF knowledge bundle")
    index_lines.append("")
    index_lines.append(
        "Machine-readable knowledge pages for aeo.animacoffee.com.ua, generated "
        "from the site's published schema.org JSON-LD @graph. Each page traces "
        "back to the live page the facts came from via its `resource` field."
    )
    index_lines.append("")
    for slug, _content, title, description in pages:
        index_lines.append(f"- [{title}]({slug}.md) — {description}")
    index_lines.append("")
    index_content = "\n".join(index_lines)

    index_path = knowledge_dir / "index.md"
    write_if_changed(index_path, index_content)

    digest_input = ("index.md:" + index_content + "\n").encode("utf-8")
    for slug, content, _title, _description in pages:
        digest_input += f"{slug}.md:{content}\n".encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()

    update_log(knowledge_dir, digest, len(pages) + 1)
    update_llms_txt(llms_txt)

    print(f"knowledge/: {len(pages)} entity pages + index.md, sha256={digest}")


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root to read index.html/llms.txt from and write knowledge/ into (default: this repo).",
    )
    args = parser.parse_args()
    main(args.root)


if __name__ == "__main__":
    cli()
