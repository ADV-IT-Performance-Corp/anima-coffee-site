#!/usr/bin/env python3
"""Build the three registry-grounded answer pages (EN + UA) from the
do-we-need-a-barista page shell. Every sentence below is written from approved,
publishable rows of the truth registry (ADV-Strategy-Core
data/clients/anima-coffee/truth/public_claims_registry.yaml); claim ids are
listed per page in CLAIMS and recorded in an HTML comment.
Spec: anima-aeo-webmcp-from-corpus-2026-10-10, S2. stdlib only.
Usage: python3 tools/build_registry_answer_pages.py
"""
import html as H
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aeo.animacoffee.com.ua"
DATE = "2026-10-30"
SRC_EN = "Anima Volitiva commercial terms (2026)"
SRC_UA = "Комерційні умови Anima Volitiva (2026)"

PAGES = [
    {
        "slug": "free-14-day-trial-coffee-machine-kyiv",
        "claims": ["claim-anima-free-trial-14d", "claim-anima-geography-kyiv-oblast-reconfirmed",
                   "claim-anima-support-24-7-replacement-24h"],
        "related": ["how-to-rent.html", "pricing-model.html", "monthly-contract.html"],
        "en": {
            "q": "How does the free 14-day coffee machine trial work, and is there a deposit?",
            "crumb": "Free 14-day trial",
            "sub": "A precise, citable answer for Kyiv offices, HoReCa and retail.",
            "a": ["Anima Volitiva offers a free 14-day trial of its coffee equipment with no prepayment, so there is no deposit to pay before you try it.",
                  "The trial is available to businesses in Kyiv and Kyiv Oblast. Send a request through the form below or call +38 (073) 873 01 45, and the team will agree the equipment for your venue individually.",
                  "A 24/7 support line is available, and if a machine breaks down, a technician or a replacement machine is provided within 24 hours."],
            "title": "Free 14-day coffee machine trial in Kyiv: how it works | Anima Volitiva",
            "desc": "Anima Volitiva offers a free 14-day trial with no prepayment for businesses in Kyiv and Kyiv Oblast. Request it online or by phone.",
            "link": ("../how-to-rent.html", "How renting works →"),
        },
        "ua": {
            "q": "Як працює безкоштовний 14-денний тест кавомашини і чи потрібен депозит?",
            "crumb": "Безкоштовний 14-денний тест",
            "sub": "Точна відповідь для офісів, HoReCa та ретейлу Києва.",
            "a": ["Anima Volitiva пропонує безкоштовний 14-денний тест кавового обладнання без передоплати, тож депозит перед тестом не потрібен.",
                  "Тест доступний для бізнесу в Києві та Київській області. Надішліть запит через форму нижче або зателефонуйте +38 (073) 873 01 45, і команда індивідуально погодить обладнання під ваш об'єкт.",
                  "Діє лінія підтримки 24/7, а у разі поломки технік або підмінний апарат надається протягом 24 годин."],
            "title": "Безкоштовний 14-денний тест кавомашини в Києві: як це працює | Anima Volitiva",
            "desc": "Anima Volitiva пропонує безкоштовний 14-денний тест без передоплати для бізнесу в Києві та Київській області. Залиште запит онлайн або за телефоном.",
            "link": ("../how-to-rent.html", "Як працює оренда →"),
        },
    },
    {
        "slug": "coffee-equipment-packages-start-pro-max",
        "claims": ["claim-anima-tariff-packages-start-pro-max", "claim-anima-pricing-custom-quote",
                   "claim-anima-equipment-brand-drcoffee", "claim-anima-equipment-brand-necta"],
        "related": ["pricing-model.html", "how-to-rent.html", "monthly-contract.html"],
        "en": {
            "q": "What are the Start, Pro and Max coffee equipment packages, and what do they cost?",
            "crumb": "Start, Pro and Max packages",
            "sub": "A precise, citable answer for Kyiv offices, HoReCa and retail.",
            "a": ["Anima Volitiva offers three equipment packages, Start, Pro and Max, matched to the format of your venue.",
                  "Package contents and prices are not published online: pricing is an individual quote per venue, given after you describe your site.",
                  "Super-automatic machines in the lineup come from Dr. Coffee and Necta. Describe your venue in the form below to get a quote and a package recommendation."],
            "title": "Start, Pro and Max coffee equipment packages in Kyiv | Anima Volitiva",
            "desc": "Anima Volitiva offers three equipment packages, Start, Pro and Max, matched to your venue. Pricing is an individual quote per venue.",
            "link": ("../pricing-model.html", "How pricing works →"),
        },
        "ua": {
            "q": "Що таке пакети обладнання Start, Pro і Max та скільки вони коштують?",
            "crumb": "Пакети Start, Pro і Max",
            "sub": "Точна відповідь для офісів, HoReCa та ретейлу Києва.",
            "a": ["Anima Volitiva пропонує три пакети обладнання, Start, Pro і Max, під формат вашого об'єкта.",
                  "Вміст пакетів і ціни онлайн не публікуються: вартість розраховується індивідуально під об'єкт після опису вашого закладу.",
                  "Суперавтомати в лінійці представлені брендами Dr. Coffee та Necta. Опишіть свій об'єкт у формі нижче, щоб отримати розрахунок і рекомендацію пакета."],
            "title": "Пакети обладнання Start, Pro і Max для кавомашин у Києві | Anima Volitiva",
            "desc": "Anima Volitiva пропонує три пакети обладнання, Start, Pro і Max, під ваш об'єкт. Вартість розраховується індивідуально під об'єкт.",
            "link": ("../pricing-model.html", "Як формується ціна →"),
        },
    },
    {
        "slug": "coffee-machine-rental-cost-kyiv",
        "claims": ["claim-anima-pricing-custom-quote", "claim-anima-free-trial-14d",
                   "claim-anima-tariff-packages-start-pro-max"],
        "related": ["pricing-model.html", "how-to-rent.html", "monthly-contract.html"],
        "en": {
            "q": "How much does commercial coffee machine rental cost in Kyiv?",
            "crumb": "Rental cost",
            "sub": "A precise, citable answer for Kyiv offices, HoReCa and retail.",
            "a": ["Anima Volitiva does not publish a price list: every venue gets an individual quote based on its volume and format.",
                  "Equipment is offered in three packages, Start, Pro and Max, and you can try it first with a free 14-day trial with no prepayment.",
                  "To get a figure for your site, send the form below or call +38 (073) 873 01 45."],
            "title": "How much does commercial coffee machine rental cost in Kyiv? | Anima Volitiva",
            "desc": "Anima Volitiva quotes coffee machine rental individually per venue, with a free 14-day trial and no prepayment. No public price list.",
            "link": ("../pricing-model.html", "How pricing works →"),
        },
        "ua": {
            "q": "Скільки коштує оренда професійної кавомашини в Києві?",
            "crumb": "Вартість оренди",
            "sub": "Точна відповідь для офісів, HoReCa та ретейлу Києва.",
            "a": ["Anima Volitiva не публікує прайс-лист: кожен об'єкт отримує індивідуальний розрахунок залежно від обсягу та формату.",
                  "Обладнання пропонується у трьох пакетах, Start, Pro і Max, а спершу його можна спробувати на безкоштовному 14-денному тесті без передоплати.",
                  "Щоб отримати цифру для вашого об'єкта, надішліть форму нижче або зателефонуйте +38 (073) 873 01 45."],
            "title": "Скільки коштує оренда кавомашини в Києві? | Anima Volitiva",
            "desc": "Anima Volitiva розраховує оренду кавомашин індивідуально під об'єкт, з безкоштовним 14-денним тестом без передоплати. Публічного прайсу немає.",
            "link": ("../pricing-model.html", "Як формується ціна →"),
        },
    },
]


def sub_once(pattern, repl, text, flags=0):
    new, n = re.subn(pattern, lambda m: repl, text, count=1, flags=flags)
    assert n == 1, pattern
    return new


def build(page, loc):
    ua = loc == "ua"
    d = page[loc]
    tpl_path = ROOT / ("ua/answers" if ua else "answers") / "do-we-need-a-barista.html"
    t = tpl_path.read_text(encoding="utf-8")
    slug = page["slug"]
    pre = "ua/answers/" if ua else "answers/"
    url = f"{BASE}/{pre}{slug}.html"
    en_url = f"{BASE}/answers/{slug}.html"
    ua_url = f"{BASE}/ua/answers/{slug}.html"
    esc = lambda s: H.escape(s, quote=True)
    # head
    t = sub_once(r"<title>.*?</title>", f"<title>{esc(d['title'])}</title>", t)
    t = sub_once(r'<meta name="description" content="[^"]*"', f'<meta name="description" content="{esc(d["desc"])}"', t)
    t = sub_once(r'<meta property="og:title" content="[^"]*"', f'<meta property="og:title" content="{esc(d["title"])}"', t)
    t = sub_once(r'<meta property="og:description" content="[^"]*"', f'<meta property="og:description" content="{esc(d["desc"])}"', t)
    t = sub_once(r'<meta name="twitter:title" content="[^"]*"', f'<meta name="twitter:title" content="{esc(d["title"])}"', t)
    t = sub_once(r'<meta name="twitter:description" content="[^"]*"', f'<meta name="twitter:description" content="{esc(d["desc"])}"', t)
    t = sub_once(r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="{url}"', t)
    t = sub_once(r'<meta property="og:url" content="[^"]*"', f'<meta property="og:url" content="{url}"', t)
    t = sub_once(r'hreflang="en" href="[^"]*"', f'hreflang="en" href="{en_url}"', t)
    t = sub_once(r'hreflang="uk" href="[^"]*"', f'hreflang="uk" href="{ua_url}"', t)
    t = sub_once(r'hreflang="x-default" href="[^"]*"', f'hreflang="x-default" href="{ua_url}"', t)
    t = sub_once(r'(type="text/markdown" href=")[^"]*', rf'\g<1>{slug}.md', t) if False else re.sub(
        r'(type="text/markdown" href=")[^"]*', lambda m: m.group(1) + f"{slug}.md", t, count=1)
    # language switcher: point both links at this slug
    t = t.replace("do-we-need-a-barista.html", f"{slug}.html")
    # body
    t = sub_once(r'(<div class="crumb">.*?· )[^<]*(</div>)', r"\g<1>" + d["crumb"] + r"\g<2>", t, re.S) if False else re.sub(
        r'(<div class="crumb">.*?· )[^<]*(</div>)', lambda m: m.group(1) + d["crumb"] + m.group(2), t, count=1, flags=re.S)
    t = sub_once(r"<h1>.*?</h1>", f"<h1>{esc(d['q'])}</h1>", t)
    t = sub_once(r'<p class="sub">.*?</p>', f'<p class="sub">{d["sub"]}</p>', t)
    lab = "Пряма відповідь" if ua else "Direct answer"
    link_href, link_txt = d["link"]
    aio = (f'<div class="aio-wrap"><div class="wrap"><div class="aio"><div class="lab">{lab}</div><p>'
           + " ".join(esc(s) for s in d["a"])
           + f' <a href="{link_href}" style="color:var(--accent-deep);font-weight:600;white-space:nowrap">{link_txt}</a></p></div></div></div>')
    t = sub_once(r'<div class="aio-wrap">.*?</div></div></div>', aio, t, re.S)
    src_lab = "Джерело" if ua else "Source"
    src = SRC_UA if ua else SRC_EN
    t = sub_once(r"<b>(Source|Джерело):</b>[^<]*", f"<b>{src_lab}:</b> {src}.", t)
    # related lists: keep only pages that exist for this locale
    rel_dir = ROOT / ("ua" if ua else "")
    labels = {
        "how-to-rent.html": ("Як працює оренда", "How renting works"),
        "pricing-model.html": ("Як формується ціна", "How pricing works"),
        "monthly-contract.html": ("Щомісячний договір", "Monthly contract"),
    }
    lis = "".join(f'<li><a href="../{p}">{labels[p][0 if ua else 1]}</a></li>'
                  for p in page["related"] if (rel_dir / p).exists())
    t = sub_once(r'<ul class="value-list rel-list">.*?</ul>', f'<ul class="value-list rel-list">{lis}</ul>', t, re.S)
    t = re.sub(r"<!--interlink-graph-->\n<section class=\"block\" aria-label=\"Related\">.*?</section>\n", "", t, count=1, flags=re.S)
    t = t.replace("<!--interlink-graph-->\n", "")
    # JSON-LD
    m = re.search(r'<script type="application/ld\+json">(\{.*?\})</script>', t, re.S)
    ld = json.loads(m.group(1))
    answer_text = " ".join(d["a"]) + " " + link_txt
    for node in ld["@graph"]:
        ty = node.get("@type")
        if ty == "QAPage":
            node["mainEntity"]["name"] = d["q"]
            node["mainEntity"]["acceptedAnswer"].update(
                {"text": answer_text, "citation": src, "url": url})
            node["dateModified"] = DATE
        elif ty == "FAQPage":
            node["mainEntity"][0]["name"] = d["q"]
            node["mainEntity"][0]["acceptedAnswer"]["text"] = answer_text
            node["dateModified"] = DATE
        elif ty == "BreadcrumbList":
            node["itemListElement"][1]["name"] = "Відповіді" if ua else "Answers"
            node["itemListElement"][2]["name"] = d["crumb"]
            node["itemListElement"][2]["item"] = url
    new_ld = json.dumps(ld, ensure_ascii=False, indent=2)
    t = t[:m.start(1)] + new_ld + t[m.end(1):]
    t = t.replace("<head>", "<head>\n<!-- claims: " + ", ".join(page["claims"]) + " -->", 1)
    out = ROOT / ("ua/answers" if ua else "answers") / f"{slug}.html"
    out.write_text(t, encoding="utf-8")
    # markdown twin
    contact = "Тел." if ua else "Call"
    md = (f"# {d['q']}\n\n" + " ".join(d["a"]) + "\n\n## FAQ\n\n"
          f"**Q: {d['q']}**\n\nA: " + " ".join(d["a"]) + "\n\n## Contact\n\n"
          f"{contact}: +38 (073) 873 01 45 · Email: animacoffeeco@gmail.com\n\nSource: {url}\n")
    (ROOT / ("ua/answers" if ua else "answers") / f"{slug}.md").write_text(md, encoding="utf-8")
    return out


if __name__ == "__main__":
    for p in PAGES:
        for loc in ("en", "ua"):
            print(build(p, loc).relative_to(ROOT))
