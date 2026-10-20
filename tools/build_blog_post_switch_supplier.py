#!/usr/bin/env python3
"""Build the blog post "Switching your coffee-machine supplier: five checks" (EN + UA).

Derives the page shell from the existing CAPEX/OPEX post so header, schema, nav, sticky CTA
and tracking stay identical. Every factual claim comes from the approved set in CLAUDE.md /
the truth registry (24/7 support, technician-or-replacement within 24h, 14-day free trial
without prepayment, individual quote, Start/Pro/Max, onboarding stages, training included).
No numbers, prices, testimonials, customer names or quotes. Idempotent: re-running rewrites
the same output. Run from the repo root, then tools/gen_sitemap.py and tools/gen_content_md.py.
"""
import html, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OLD = "capex-vs-opex-b2b-coffee-kyiv.html"
SLUG = "switch-coffee-supplier-checklist-kyiv.html"
DATE = "2026-10-20"

P = 'style="margin:0 0 18px;color:var(--ink-soft);line-height:1.8"'
H2 = 'style="font-size:24px;margin:28px 0 12px"'

CONTENT = {
    "en": {
        "title": "Switching your coffee-machine supplier: five checks before you sign",
        "desc": "Quality drift, slow service, nobody answering a complaint: how Kyiv businesses can switch coffee-machine suppliers without risk, and the five things to confirm before signing.",
        "intro": [
            "Most businesses do not look for a new coffee supplier because the old one is cheap or expensive. They look because the coffee got worse, a broken machine waited too long for a technician, or a complaint went unanswered. If that sounds familiar, the question is not only who to switch to, but how to switch without taking on a new risk.",
            "Use these five checks with any supplier, including <strong>Anima Volitiva</strong>. We list what we commit to for each one, so you can compare like with like.",
        ],
        "secs": [
            ("1. Who picks up when the machine stops?",
             "Ask for the support hours and the exact promise on a breakdown. Ours: a 24/7 support line, and a technician on site or a replacement machine within 24 hours, same-day where operationally possible. Delivery and installation of new equipment also runs within 24 hours."),
            ("2. Can you test it on your own volume first?",
             "A demo in a showroom does not tell you how a machine copes with your morning queue. We offer a free 14-day trial with no prepayment, so you compare the coffee and the service side by side with your current setup before deciding."),
            ("3. Is one company responsible for machine, coffee and service?",
             "When one vendor rents the machine, another supplies beans and a third repairs it, a breakdown turns into a debate about whose fault it is. With Anima Volitiva the machine, the premium roasted coffee, the weekly resupply and the weekly technician quality visit sit under one agreement and one phone number."),
            ("4. Is the price built for your venue, not a brochure?",
             "A kiosk, an office and a restaurant need different equipment. We quote individually for your venue and volume, with three equipment packages (Start, Pro and Max) matched to the format. There is no flat published price, so ask any supplier what is included before comparing numbers."),
            ("5. Is staff training part of the deal?",
             "A well-set machine still fails when the team does not know the daily routine. Staff training is included in our onboarding, which runs in five stages: planning, setup, training, a first-week quality check and a review after the first month."),
        ],
        "outro_h": "What a managed switch looks like",
        "outro": [
            "You do not have to end your current arrangement to find out. Start the 14-day trial, run both in parallel, and decide on the results. We serve HoReCa, offices and retail across Kyiv and Kyiv Oblast, with equipment from Dr. Coffee and Necta (super-automatics) and La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria and Fiorenzato (professional espresso).",
            "Call +38 (073) 873 01 45 (Mon-Sat 09:00-17:00) or leave a request and we will size a trial to your venue.",
        ],
        "cta": "Request a free trial for your venue",
        "cta_btn": "Get your free assessment",
        "card": "How to switch coffee suppliers without risk: five checks before you sign. What to confirm about support, trial, responsibility, pricing and training.",
    },
    "uk": {
        "title": "Зміна постачальника кавомашин: п’ять перевірок перед підписанням",
        "desc": "Падіння якості, повільний сервіс, скарги без відповіді: як бізнесу в Києві змінити постачальника кавомашин без ризику та що підтвердити до підписання договору.",
        "intro": [
            "Більшість компаній шукають нового постачальника кави не через ціну. Причина інша: кава стала гіршою, зламана машина надто довго чекала на техніка або скарга лишилась без відповіді. Якщо це знайомо, питання не лише в тому, до кого перейти, а й у тому, як змінити постачальника, не отримавши нових ризиків.",
            "Скористайтеся цими п’ятьма перевірками з будь-яким постачальником, зокрема з <strong>Anima Volitiva</strong>. Для кожної ми вказуємо, що саме гарантуємо, щоб ви порівнювали однакове з однаковим.",
        ],
        "secs": [
            ("1. Хто відповість, коли машина зупинилась?",
             "Уточніть години підтримки та точну обіцянку на випадок поломки. Наша: цілодобова підтримка 24/7, а також технік на місці або підмінна машина протягом 24 годин, день у день, де це можливо. Доставка та встановлення нового обладнання теж відбуваються протягом 24 годин."),
            ("2. Чи можна спершу перевірити на власному обсязі?",
             "Демонстрація в шоурумі не покаже, як машина впорається з вашою ранковою чергою. Ми пропонуємо безкоштовний 14-денний тест без передоплати: ви порівнюєте каву та сервіс поруч із поточним рішенням ще до остаточного вибору."),
            ("3. Чи відповідає одна компанія за машину, каву та сервіс?",
             "Коли один вендор здає машину, другий постачає зерно, а третій ремонтує, поломка перетворюється на суперечку, хто винен. В Anima Volitiva машина, преміальна обсмажена кава, щотижневе поповнення та щотижневий візит техніка для перевірки якості входять в одну угоду та один номер телефону."),
            ("4. Чи побудована ціна під ваш заклад, а не під брошуру?",
             "Кіоску, офісу й ресторану потрібне різне обладнання. Ми розраховуємо індивідуально під ваш заклад і обсяг: три пакети обладнання (Start, Pro і Max) відповідно до формату. Фіксованої публічної ціни немає, тому в будь-якого постачальника спершу уточніть, що входить, і лише потім порівнюйте цифри."),
            ("5. Чи входить навчання персоналу?",
             "Навіть добре налаштована машина підводить, якщо команда не знає щоденної рутини. Навчання персоналу входить в наш онбординг із п’яти етапів: планування, встановлення, навчання, перевірка якості на першому тижні та огляд після першого місяця."),
        ],
        "outro_h": "Як виглядає керований перехід",
        "outro": [
            "Не обов’язково одразу завершувати поточну співпрацю, щоб дізнатися різницю. Запустіть 14-денний тест, ведіть обидва варіанти паралельно й вирішуйте за результатами. Ми працюємо з HoReCa, офісами та роздрібом у Києві й Київській області: суперавтомати Dr. Coffee та Necta, професійні еспресо-машини La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria та Fiorenzato.",
            "Телефонуйте +38 (073) 873 01 45 (пн-сб 09:00-17:00) або залиште заявку: підберемо тест під ваш заклад.",
        ],
        "cta": "Замовте безкоштовний тест для вашого закладу",
        "cta_btn": "Отримати безкоштовний аудит",
        "card": "Як змінити постачальника кави без ризику: п’ять перевірок перед підписанням. Що підтвердити щодо підтримки, тесту, відповідальності, ціни та навчання.",
    },
}


def body_html(c):
    out = ""
    for p in c["intro"]:
        out += f"<p {P}>{p}</p>"
    for h, b in c["secs"]:
        out += f"<h2 {H2}>{html.escape(h)}</h2><p {P}>{html.escape(b)}</p>"
    out += f"<h2 {H2}>{html.escape(c['outro_h'])}</h2>"
    for p in c["outro"]:
        out += f"<p {P}>{html.escape(p)}</p>"
    return out


def build(lang):
    c = CONTENT[lang]
    rel = ("ua/" if lang == "uk" else "") + "blog/" + OLD
    src = (ROOT / rel).read_text(encoding="utf8")
    old_title = re.search(r"<title>(.*?) \| Anima Volitiva</title>", src).group(1)
    old_desc = re.search(r'<meta name="description" content="(.*?)" />', src).group(1)
    esc = lambda s: html.escape(s, quote=True)
    # global swaps (title/desc appear in title, og, schema, breadcrumb, h1, sub; slug in canonical/hreflang/lang switch)
    src = src.replace(old_title, esc(c["title"]).replace("&#x27;", "'"))
    src = src.replace(old_desc, esc(c["desc"]).replace("&#x27;", "'"))
    src = src.replace(OLD, SLUG)
    src = re.sub(r'"dateModified": "[0-9-]+"', f'"dateModified": "{DATE}"', src)
    # body
    src, n = re.subn(
        r'(<article class="block"><div class="wrap" style="max-width:800px">).*?(</div></article>)',
        lambda m: m.group(1) + "\n" + body_html(c) + "\n" + m.group(2), src, flags=re.S)
    assert n == 1
    src, n = re.subn(r'(<section class="cta block" id="cta"><div class="wrap" style="text-align:center">\s*<h2>).*?(</h2>\s*<a class="btn btn-primary" href="../#cta">).*?(</a>)',
                     lambda m: m.group(1) + html.escape(c["cta"]) + m.group(2) + html.escape(c["cta_btn"]) + m.group(3), src, flags=re.S)
    assert n == 1
    (ROOT / (("ua/" if lang == "uk" else "") + "blog/" + SLUG)).write_text(src, encoding="utf8")
    # blog index card
    idx = ROOT / (("ua/" if lang == "uk" else "") + "blog/index.html")
    t = idx.read_text(encoding="utf8")
    if SLUG not in t:
        card = (f'<a href="{SLUG}" style="display:block;border:1px solid var(--line);border-radius:12px;padding:24px 28px;'
                f'text-decoration:none;max-width:760px;margin-top:16px"><span style="color:var(--accent);font-weight:700;font-size:20px">'
                f'{html.escape(c["title"])}</span><p style="margin:8px 0 0;color:var(--ink-soft)">{html.escape(c["card"])}</p></a>')
        marker = f'<a href="{OLD}"'
        i = t.index(marker)
        j = t.index("</a>", i) + 4
        t = t[:j] + card + t[j:]
        idx.write_text(t, encoding="utf8")


if __name__ == "__main__":
    for l in ("en", "uk"):
        build(l)
    print("built", SLUG)
