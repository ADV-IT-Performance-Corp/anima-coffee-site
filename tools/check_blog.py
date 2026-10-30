#!/usr/bin/env python3
"""Blog publication gate (EN + UA). Complements check_aeo.py / aeo_seo_check.py, which already
scan every page for forbidden entities and broken links; this adds blog-specific rules.

Per post: Article JSON-LD with datePublished; canonical + reciprocal EN/UA twin on disk;
Markdown twin; listed in sitemap.xml and in both blog indexes; a lead-form CTA; no price or
percentage figures and no quoted testimonials (CLAUDE.md: invented stats/prices are banned);
minimum length; at least 3 internal links, an external source link and a Sources section. Exit 0 if all pass.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"
MIN_WORDS = 350
BAD = [
    (r"[$€£]\s?\d|\d\s?(?:USD|EUR|UAH|грн|₴|€|\$)", "price figure"),
    (r"(?<!9)(?<!~)\d\s?%|\b(?!99)\d{1,3}\s?%", "percentage claim (only the owner-stated ~99% repeat rate is tolerated)"),
    (r"\b2[- ]hour|2[- ]годин", "retracted 2-hour SLA"),
    (r"\bspecialty\b|спешелті", "banned specialty framing"),
    (r"retro-?bonus|ретро-?бонус|free first (?:rental )?month|перший місяць оренди безкоштовно", "retracted offer"),
]
fails = []


def fail(page, msg):
    fails.append(f"{page}: {msg}")


sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf8")
posts = [p for loc in ("blog", "ua/blog") for p in sorted((ROOT / loc).glob("*.html")) if p.name != "index.html"]
for p in posts:
    rel = p.relative_to(ROOT).as_posix()
    src = p.read_text(encoding="utf8")
    if '"@type": "Article"' not in src:
        fail(rel, "no Article JSON-LD")
    if not re.search(r'"datePublished": "\d{4}-\d{2}-\d{2}"', src):
        fail(rel, "Article lacks datePublished")
    if f'rel="canonical" href="{BASE}/{rel}"' not in src:
        fail(rel, "canonical missing or wrong")
    twin = ROOT / (rel[3:] if rel.startswith("ua/") else "ua/" + rel)
    if not twin.exists():
        fail(rel, f"missing language twin {twin.relative_to(ROOT)}")
    if not p.with_suffix(".md").exists():
        fail(rel, "missing .md twin (run tools/gen_content_md.py)")
    if f"<loc>{BASE}/{rel}</loc>" not in sitemap:
        fail(rel, "not in sitemap.xml (run tools/gen_sitemap.py)")
    idx = (p.parent / "index.html").read_text(encoding="utf8")
    if f'href="{p.name}"' not in idx:
        fail(rel, "not linked from its blog index")
    if 'id="cta"' not in src or "../#cta" not in src:
        fail(rel, "no lead CTA")
    m = re.search(r"<article.*?</article>", src, re.S)
    text = re.sub(r"<[^>]+>", " ", m.group(0)) if m else ""
    if len(text.split()) < MIN_WORDS:
        fail(rel, f"only {len(text.split())} words (< {MIN_WORDS})")
    art = m.group(0) if m else ""
    if len(re.findall(r'href="\.\./[^"]+\.html', art)) < 3:
        fail(rel, "fewer than 3 internal links in the article")
    if not re.search(r'href="https://(?:animacoffee\.com\.ua|www\.(?:instagram|facebook)\.com|t\.me)', art):
        fail(rel, "no external source link (company site or channel)")
    if 'id="sources"' not in art:
        fail(rel, "no Sources section")
    for rx, label in BAD:
        if re.search(rx, text, re.I):
            fail(rel, f"{label}: /{rx}/")
    if re.search(r"[«\"“][^»\"”]{20,}[»\"”]\s*[—–-]\s*[A-ZА-ЯІЇЄ]", text):
        fail(rel, "looks like a quoted testimonial")

print(f"Blog gate: {len(posts)} posts, {len(fails)} failure(s)")
for f in fails:
    print(" FAIL", f)
sys.exit(1 if fails else 0)
