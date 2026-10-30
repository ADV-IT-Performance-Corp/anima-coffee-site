#!/usr/bin/env python3
"""Build one blog post (EN + UA) from tools/blog_posts/<name>.json.

Generic replacement for the one-off build_blog_post_*.py scripts. The page shell (head,
schema, nav, sticky CTA, tracking) is copied from TEMPLATE, an existing post, so every post
stays identical in structure. Content comes only from the JSON file; every claim in it must
be in CLAUDE.md / the truth registry. Idempotent. Adds datePublished + dateModified, and
puts the card at the top of both blog indexes.

Usage (repo root):
  python3 tools/build_blog_post.py coffee-machine-free-trial-checklist-kyiv
  python3 tools/gen_sitemap.py --date <date> && python3 tools/gen_content_md.py
  python3 tools/check_blog.py
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = "switch-coffee-supplier-checklist-kyiv.html"
P = 'style="margin:0 0 18px;color:var(--ink-soft);line-height:1.8"'
H2 = 'style="font-size:24px;margin:28px 0 12px"'
CARD = ('<a href="{slug}" style="display:block;border:1px solid var(--line);border-radius:12px;padding:24px 28px;'
        'text-decoration:none;max-width:760px;margin-bottom:16px"><span style="color:var(--accent);font-weight:700;'
        'font-size:20px">{title}</span><p style="margin:8px 0 0;color:var(--ink-soft)">{card}</p></a>')


LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
TH = 'style="text-align:left;padding:10px 12px;border-bottom:2px solid var(--line)"'
TD = 'style="padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top"'


def inline(text):
    """Escape, then **bold** and [text](url). Relative urls are site pages (same path from blog/ and ua/blog/)."""
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

    def a(m):
        url = m.group(2)
        ext = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url}"{ext}>{m.group(1)}</a>'
    return LINK.sub(a, t)


def block_html(b):
    if isinstance(b, str):
        return f"<p {P}>{inline(b)}</p>"
    if "ul" in b:
        return ('<ul style="margin:0 0 18px;padding-left:22px;color:var(--ink-soft);line-height:1.8">'
                + "".join(f"<li>{inline(i)}</li>" for i in b["ul"]) + "</ul>")
    if "table" in b:
        t = b["table"]
        head = "".join(f"<th {TH}>{inline(h)}</th>" for h in t["head"])
        rows = "".join("<tr>" + "".join(f"<td {TD}>{inline(c)}</td>" for c in r) + "</tr>" for r in t["rows"])
        return (f'<div style="overflow-x:auto;margin:0 0 22px"><table style="border-collapse:collapse;width:100%;'
                f'color:var(--ink-soft);font-size:15px;line-height:1.5"><thead><tr>{head}</tr></thead>'
                f"<tbody>{rows}</tbody></table></div>")
    raise ValueError(b)


def body_html(c):
    out = "".join(block_html(b) for b in c["intro"])
    for h, blocks in c["secs"]:
        out += f"<h2 {H2}>{html.escape(h)}</h2>" + "".join(block_html(b) for b in blocks)
    out += f"<h2 {H2}>{html.escape(c['outro_h'])}</h2>" + "".join(block_html(b) for b in c["outro"])
    out += f"<h2 {H2} id=\"sources\">{html.escape(c['sources_h'])}</h2>" + block_html({"ul": c["sources"]})
    return out


def build(lang, post):
    c, slug, date = post[lang], post["slug"], post["date"]
    prefix = "ua/" if lang == "uk" else ""
    src = (ROOT / prefix / "blog" / TEMPLATE).read_text(encoding="utf8")
    old_title = re.search(r"<title>(.*?) \| Anima Volitiva</title>", src).group(1)
    old_desc = re.search(r'<meta name="description" content="(.*?)" />', src).group(1)
    esc = lambda s: html.escape(s, quote=True).replace("&#x27;", "'")
    src = src.replace(old_title, esc(c["title"])).replace(old_desc, esc(c["desc"])).replace(TEMPLATE, slug)
    src = re.sub(r'\s*"datePublished": "[0-9-]+",?', "", src)
    src = re.sub(r'"dateModified": "[0-9-]+"', f'"datePublished": "{date}",\n      "dateModified": "{date}"', src)
    src, n = re.subn(r'(<article class="block"><div class="wrap" style="max-width:800px">).*?(</div></article>)',
                     lambda m: m.group(1) + "\n" + body_html(c) + "\n" + m.group(2), src, flags=re.S)
    assert n == 1, "article block not found in template"
    src, n = re.subn(r'(<section class="cta block" id="cta"><div class="wrap" style="text-align:center">\s*<h2>).*?'
                     r'(</h2>\s*<a class="btn btn-primary" href="../#cta">).*?(</a>)',
                     lambda m: m.group(1) + html.escape(c["cta"]) + m.group(2) + html.escape(c["cta_btn"]) + m.group(3),
                     src, flags=re.S)
    assert n == 1, "CTA block not found in template"
    (ROOT / prefix / "blog" / slug).write_text(src, encoding="utf8")

    idx = ROOT / prefix / "blog" / "index.html"
    t = idx.read_text(encoding="utf8")
    if f'href="{slug}"' not in t:
        first = t.index('<a href="', t.index('<section class="block"><div class="wrap">'))
        t = t[:first] + CARD.format(slug=slug, title=html.escape(c["title"]), card=html.escape(c["card"])) + t[first:]
        idx.write_text(t, encoding="utf8")


if __name__ == "__main__":
    name = sys.argv[1]
    post = json.loads((ROOT / "tools" / "blog_posts" / f"{name}.json").read_text(encoding="utf8"))
    for lg in ("en", "uk"):
        build(lg, post)
    print("built", post["slug"])
