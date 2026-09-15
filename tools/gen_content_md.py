#!/usr/bin/env python3
"""Generate AI-readable Markdown from the live HTML pages. stdlib only.

Two outputs, both regenerable from the on-disk HTML (source of truth stays
the HTML; these are derived views, never hand-edited):

1. Markdown twins: `<page>.md` next to `<page>.html`, for every indexable
   page that doesn't already have one. Format matches the existing
   answers/*.md twins (H1, Direct answer / lead paragraph, FAQ if present,
   Contact, Source) so tools/check_md_twin_subset.py's strict-subset rule
   still holds for any twin this script writes.
2. llms-full.txt at the repo root: the full body Markdown (all headings,
   paragraphs, list items, FAQ) of every indexable page, concatenated with
   a per-page separator and Source line.

Usage:
  python3 tools/gen_content_md.py --twins-only     # (re)write missing twins
  python3 tools/gen_content_md.py --full-only      # (re)write llms-full.txt
  python3 tools/gen_content_md.py                  # both
"""
import argparse
import html
import pathlib
import re
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"
SKIP_TAGS = {"script", "style", "nav", "footer", "noscript"}
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
BLOCK_TAGS = {"p", "li", "div"}


def is_indexable(path: pathlib.Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if 'http-equiv="refresh"' in src:
        return False  # redirect stub
    return "noindex" not in src.lower()


def collect_indexable_pages():
    pages = []
    for pattern in ("*.html", "answers/*.html", "blog/*.html",
                     "ua/*.html", "ua/answers/*.html", "ua/blog/*.html"):
        for p in sorted(ROOT.glob(pattern)):
            if "ppc/" in p.as_posix():
                continue
            if is_indexable(p):
                pages.append(p)
    return pages


def url_for(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel in ("index.html", "ua/index.html"):
        rel = rel[: -len("index.html")]
    return f"{BASE}/{rel}"


class BodyExtractor(HTMLParser):
    """Walks the body in document order, emitting one Markdown block per
    heading/paragraph/list-item, skipping nav/header/footer/script/style."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.skip_stack = []
        self.cur_tag = None
        self.cur_text = []
        self.blocks = []  # list of (kind, text)
        self.seen_h1 = False

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag in SKIP_TAGS or (tag == "div" and "contact-block" in attrs_d.get("class", "")):
            self.skip_stack.append(tag)
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in HEADING_TAGS or tag in ("p", "li"):
            self.cur_tag = tag
            self.cur_text = []

    def handle_endtag(self, tag):
        if self.skip_stack and tag == self.skip_stack[-1]:
            self.skip_stack.pop()
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == self.cur_tag and tag in HEADING_TAGS | {"p", "li"}:
            text = re.sub(r"\s+", " ", "".join(self.cur_text)).strip()
            if text:
                self.blocks.append((tag, text))
            self.cur_tag = None
            self.cur_text = []

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.cur_tag:
            self.cur_text.append(data)


def extract_blocks(html_src: str):
    body_start = html_src.find("<body")
    body_src = html_src[body_start:] if body_start != -1 else html_src
    parser = BodyExtractor()
    parser.feed(body_src)
    return parser.blocks


def blocks_to_markdown(blocks):
    lines = []
    seen = set()
    for tag, text in blocks:
        key = (tag, text)
        if key in seen:
            continue  # dedupe (Direct-answer paragraphs are often repeated verbatim in a second block)
        seen.add(key)
        if tag == "h1":
            lines.append(f"# {text}")
        elif tag == "h2":
            lines.append(f"## {text}")
        elif tag in ("h3", "h4"):
            lines.append(f"### {text}")
        elif tag == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _visible_text(html_src: str) -> str:
    stripped = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html_src, flags=re.S | re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return html.unescape(stripped)


def contact_line(html_src: str):
    """Reuses the page's own rendered contact-block text verbatim (label
    included: EN pages say 'Call:', UA pages say 'Тел.:') so the line is a
    literal substring of the page, not a re-templated guess."""
    m = re.search(r'class="contact-block"[^>]*>(.*?)</div>', html_src, re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", _visible_text(m.group(1))).strip()


def full_page_markdown(path: pathlib.Path) -> str:
    src = path.read_text(encoding="utf-8")
    blocks = extract_blocks(src)
    body = blocks_to_markdown(blocks)
    url = url_for(path)
    cline = contact_line(src)
    contact = f"\n## Contact\n\n{cline}\n" if cline else ""
    return f"{body}\n{contact}\nSource: {url}\n"


def twin_markdown(path: pathlib.Path) -> str:
    """Minimal H1 + Direct-answer + FAQ + Contact form, matching the
    existing answers/*.md twin convention (strict subset of page text)."""
    src = path.read_text(encoding="utf-8")
    blocks = extract_blocks(src)
    h1 = next((t for tag, t in blocks if tag == "h1"), None)
    if not h1:
        return None
    # Direct answer: first <p> block after the H1 that isn't a nav/tagline
    # fragment (heuristic: longer than 60 chars).
    direct = None
    for tag, t in blocks:
        if tag == "p" and len(t) > 60:
            direct = t
            break
    if not direct:
        direct = h1
    url = url_for(path)
    parts = [f"# {h1}", "", direct, "", "## FAQ", "", f"**Q: {h1}**", "", f"A: {direct}", ""]
    cline = contact_line(src)
    if cline:
        parts += ["## Contact", "", cline, ""]
    parts += [f"Source: {url}", ""]
    return "\n".join(parts)


TWIN_TARGETS = [
    "index.html", "about.html", "services.html", "how-to-rent.html",
    "monthly-contract.html", "barista-training.html", "maintenance.html",
    "premium-coffee-beans.html", "dr-coffee-vs-espresso.html", "blog/index.html",
]


def write_twins():
    written = []
    targets = list(TWIN_TARGETS) + ["ua/" + t for t in TWIN_TARGETS]
    # plus every other currently-indexable page lacking a twin (covers the
    # newly-unlocked item-6 pages and the item-3 renamed slugs)
    for p in collect_indexable_pages():
        rel = p.relative_to(ROOT).as_posix()
        targets.append(rel)
    seen = set()
    for rel in targets:
        if rel in seen:
            continue
        seen.add(rel)
        html_path = ROOT / rel
        if not html_path.exists():
            continue
        md_path = html_path.with_suffix(".md")
        if md_path.exists():
            continue
        md = twin_markdown(html_path)
        if md is None:
            continue
        md_path.write_text(md, encoding="utf-8")
        written.append(md_path.relative_to(ROOT).as_posix())
    return written


def write_llms_full():
    pages = collect_indexable_pages()
    sections = []
    for p in pages:
        sections.append(full_page_markdown(p))
    out = "\n---\n\n".join(sections)
    header = (
        "# Anima Volitiva — Full Site Content (AI-readable)\n\n"
        "Full Markdown body of every indexable page on "
        f"{BASE}, regenerated by tools/gen_content_md.py from the live HTML.\n"
        "Individual page Markdown twins (`.md` next to `.html`) carry the\n"
        "same H1/Direct-answer/FAQ/Contact facts in a shorter form; this file\n"
        "is the full-depth version for agents that want everything in one\n"
        "fetch. See llms.txt for the curated page index.\n\n---\n\n"
    )
    (ROOT / "llms-full.txt").write_text(header + out, encoding="utf-8")
    return len(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twins-only", action="store_true")
    ap.add_argument("--full-only", action="store_true")
    a = ap.parse_args()
    if not a.full_only:
        written = write_twins()
        print(f"wrote {len(written)} new twin(s)")
        for w in written:
            print(f"  {w}")
    if not a.twins_only:
        n = write_llms_full()
        print(f"llms-full.txt: {n} pages")


if __name__ == "__main__":
    main()
