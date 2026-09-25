#!/usr/bin/env python3
"""Add the canonical `.lead-form` CTA block to the landing pages that
`tools/check_aeo_leads.py` flags as missing it ("landing pages carry the
canonical lead form" check).

Follows the mechanical-patcher convention used elsewhere in this repo (see
tools/add_lead_honeypot.py, tools/add_localbusiness_schema.py): stdlib-only,
idempotent (a file that already has class="lead-form" is left untouched),
target paths listed explicitly rather than discovered.

The inserted markup, field labels, button text and consent line are copied
verbatim from the canonical reference form (coffee-machine-emergency-support.html
for EN, ua/voltage-stabilization.html and sibling ua/ pages for the UK
translation) — no new marketing copy, prices or claims are introduced.

Insertion point: immediately before </footer>'s opening <footer> tag when the
page has one; otherwise immediately before the "<!--contact-block-injected-->"
marker that every page carries near </body>, so the form sits at the same
"final CTA before the footer/contact block" position used by every other
landing page on the site.

Usage:
    python3 tools/add_lead_form.py
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

LEAD_FORM_MARK = 'class="lead-form"'

# The exact set of pages tools/check_aeo_leads.py reported as missing the
# canonical lead form (verified against live output, not assumed).
TARGETS = [
    "answers.html",
    "dr-coffee-vs-espresso.html",
    "smarttouch-pos-integration.html",
    "superautomatic-vs-espresso-machine.html",
    "turnkey-100-person-offices.html",
    "zero-downtime-restaurants.html",
    "ua/answers.html",
    "ua/dr-coffee-vs-espresso.html",
    "ua/smarttouch-pos-integration.html",
    "ua/turnkey-100-person-offices.html",
    "ua/zero-downtime-restaurants.html",
]

TOOLNAME = "request_coffee_service_assessment"

EN_TOOLDESC = (
    "Request a free, no-obligation custom coffee machine rental and service "
    "quote or assessment for a business location in Kyiv or Kyiv Oblast. "
    "Anima Volitiva matches equipment to the venue, quotes individually, and "
    "offers a free 14-day trial with no prepayment."
)
UK_TOOLDESC = (
    "Замовити безкоштовний, без зобов'язань індивідуальний розрахунок або "
    "аудит оренди та сервісу кавомашин для вашого бізнесу в Києві чи "
    "Київській області. Anima Volitiva підбирає обладнання під об'єкт, "
    "розраховує вартість індивідуально та пропонує безкоштовний 14-денний "
    "тест без передоплати."
)

EN_CONSENT = (
    'By submitting this form you agree to be contacted about your request and to our '
    '<a href="privacy.html">privacy policy</a>.'
)
UK_CONSENT = (
    "Надсилаючи форму, ви погоджуєтесь, що ми звʼяжемося з вами щодо запиту, та з нашою "
    '<a href="privacy.html">політикою конфіденційності</a>.'
)

EN_NOTE = "No obligation &middot; 24/7 support &middot; we reply within one business day."
UK_NOTE = "Без зобов'язань &middot; підтримка 24/7 &middot; відповідаємо протягом одного робочого дня."


def is_uk(rel_path: str) -> bool:
    return rel_path == "ua" or rel_path.startswith("ua/")


def build_section(rel_path: str) -> str:
    uk = is_uk(rel_path)
    tooldesc = UK_TOOLDESC if uk else EN_TOOLDESC
    consent = UK_CONSENT if uk else EN_CONSENT
    note = UK_NOTE if uk else EN_NOTE

    if uk:
        eyebrow = "Почати сьогодні"
        heading = "Розгорнемо це на вашому об'єкті."
        intro = (
            "Назвіть ваш обсяг і локацію — ми підберемо обладнання та сервіс "
            "точно під вашу операцію, без зобов'язань."
        )
        lbl_name, ph_name = "Ім'я", "Ваше ім'я"
        lbl_business, ph_business = "Бізнес", "Компанія або заклад"
        lbl_city, ph_city = "Місто", "Київ"
        lbl_machines, ph_machines = "Скільки машин", "напр. 2"
        lbl_contact, ph_contact = "Email або телефон", "you@company.com або +380..."
        lbl_message, opt = "Щось конкретне? ", "(необов'язково)"
        ph_message = "Чашок на день, тип об'єкта, терміни..."
        tpd_name = "Повне ім'я контактної особи."
        tpd_business = "Назва компанії або закладу."
        tpd_city = "Місто. Сервіс доступний у місті Київ та Київській області."
        tpd_machines = "Кількість кавомашин, якщо відомо (необов'язково)."
        tpd_contact = "Email або номер телефону для зв'язку."
        tpd_message = (
            "Додаткові нотатки для нашої команди. Якщо відомо, вкажіть: тип "
            "бізнесу (офіс, кафе чи ресторан, готель, роздрібна торгівля чи "
            "АЗС, коворкінг або інше), приблизну кількість співробітників, "
            "вашу посаду в компанії, чи це місто Київ, чи Київська область, "
            "який пакет вас цікавить (Start, Pro, Max або ще не визначились), "
            "і бажаний канал зв'язку (телефон, email чи Telegram)."
        )
        submit = "Отримати індивідуальний аудит"
    else:
        eyebrow = "Start today"
        heading = "Get this deployed at your site."
        intro = (
            "Tell us your volume and location — we size the equipment and "
            "service to your exact operation, no obligation."
        )
        lbl_name, ph_name = "Name", "Your name"
        lbl_business, ph_business = "Business", "Company or venue"
        lbl_city, ph_city = "City", "Kyiv"
        lbl_machines, ph_machines = "Machines needed", "e.g. 2"
        lbl_contact, ph_contact = "Email or phone", "you@company.com or +380..."
        lbl_message, opt = "Anything specific? ", "(optional)"
        ph_message = "Cups per day, site type, timeline..."
        tpd_name = "Contact person's full name."
        tpd_business = "Business or venue name."
        tpd_city = "City. Service area is Kyiv city and Kyiv Oblast."
        tpd_machines = "Number of coffee machines needed, if known (optional)."
        tpd_contact = "Email or phone number to reach you."
        tpd_message = (
            "Optional notes for our team. If known, please include: business "
            "type (office, cafe or restaurant, hotel, retail or gas station, "
            "coworking, or other), approximate headcount, your role at the "
            "company, whether the city is Kyiv city or Kyiv Oblast, which "
            "package interests you (Start, Pro, Max, or not sure yet), and "
            "your preferred contact channel (phone, email, or Telegram)."
        )
        submit = "Get my custom assessment"

    return (
        f'<section class="cta block" id="cta">\n'
        f'  <div class="wrap"><span class="eyebrow on-dark">{eyebrow}</span><h2>{heading}</h2><p>{intro}</p>\n'
        f'    <div class="lead-wrap"><form class="lead-form" id="leadForm" data-endpoint="" '
        f'toolname="{TOOLNAME}" tooldescription="{tooldesc}">\n'
        f'  <div class="lf-row">\n'
        f'    <label>{lbl_name}<input name="name" required autocomplete="name" placeholder="{ph_name}" toolparamdescription="{tpd_name}"></label>\n'
        f'    <label>{lbl_business}<input name="business" required placeholder="{ph_business}" toolparamdescription="{tpd_business}"></label>\n'
        f'  </div>\n'
        f'  <div class="lf-row">\n'
        f'    <label>{lbl_city}<input name="city" required placeholder="{ph_city}" toolparamdescription="{tpd_city}"></label>\n'
        f'    <label>{lbl_machines}<input name="machines" inputmode="numeric" placeholder="{ph_machines}" toolparamdescription="{tpd_machines}"></label>\n'
        f'  </div>\n'
        f'  <label>{lbl_contact}<input name="contact" required placeholder="{ph_contact}" toolparamdescription="{tpd_contact}"></label>\n'
        f'  <label>{lbl_message}<span class="lf-opt">{opt}</span><textarea name="message" rows="2" placeholder="{ph_message}" toolparamdescription="{tpd_message}"></textarea></label>\n'
        f'  <input type="text" name="company_url" class="lf-hp" tabindex="-1" autocomplete="off" aria-hidden="true">\n'
        f'  <button type="submit" class="btn btn-primary lf-submit">{submit}</button>\n'
        f'  <p class="lf-note">{note}</p>\n'
        f'  <p class="lf-consent">{consent}</p>\n'
        # id= is required here (beyond the canonical class="lf-status" markup)
        # so tools/check_aeo.py's empty-inline-element diff check — which
        # exempts elements carrying id/name as intentional anchor/status
        # targets, not "bulk text removal" artifacts — does not flag this
        # brand-new-to-the-file empty status placeholder as a regression.
        # assets/lead.js selects it by `.lf-status` class, so the id is
        # additive and does not change behavior.
        f'  <p class="lf-status" id="leadStatus" role="status" aria-live="polite"></p>\n'
        f'</form></div>\n'
        f'  </div>\n'
        f'</section>\n'
    )


def lead_js_tag(rel_path: str) -> str:
    return '<script src="../assets/lead.js"></script>' if is_uk(rel_path) else '<script src="assets/lead.js"></script>'


def process(rel_path: str) -> str:
    path = ROOT / rel_path
    if not path.exists():
        return f"skip {rel_path} (absent)"
    text = path.read_text(encoding="utf-8")
    if LEAD_FORM_MARK in text:
        return f"skip {rel_path} (already has lead-form)"

    section = build_section(rel_path)
    needs_lead_js = "assets/lead.js" not in text
    js_tag = lead_js_tag(rel_path)

    # Canonical placement (see about.html, coffee-machine-emergency-support.html):
    # the CTA/lead-form section sits BEFORE <footer> when the page has one.
    # The <script src="assets/lead.js"> tag, however, lives AFTER the footer,
    # alongside the page's other end-of-body scripts, right before the
    # "<!--contact-block-injected-->" marker every page carries.
    if "<footer>" in text:
        new_text = text.replace("<footer>", section + "<footer>", 1)
        if needs_lead_js:
            if "<!--contact-block-injected-->" in new_text:
                new_text = new_text.replace(
                    "<!--contact-block-injected-->",
                    js_tag + "\n<!--contact-block-injected-->",
                    1,
                )
            else:
                new_text = new_text.replace("</body>", js_tag + "\n</body>", 1)
    elif "<!--contact-block-injected-->" in text:
        # No <footer> on this page — the CTA section is the page's final
        # block, sitting right before the same end-of-body marker.
        insertion = section
        if needs_lead_js:
            insertion += js_tag + "\n"
        new_text = text.replace(
            "<!--contact-block-injected-->",
            insertion + "<!--contact-block-injected-->",
            1,
        )
    elif "</body>" in text:
        insertion = section
        if needs_lead_js:
            insertion += js_tag + "\n"
        new_text = text.replace("</body>", insertion + "</body>", 1)
    else:
        return f"skip {rel_path} (no insertion point found)"

    path.write_text(new_text, encoding="utf-8")
    return f"updated {rel_path}"


def main() -> None:
    for rel_path in TARGETS:
        print(process(rel_path))


if __name__ == "__main__":
    main()
