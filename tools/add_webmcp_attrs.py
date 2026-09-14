#!/usr/bin/env python3
"""W1 — idempotently wire declarative WebMCP onto the lead form (every page
that carries `class="lead-form"`) and load `assets/webmcp.js` on every real
site page (every page that already loads `assets/analytics.js` — the same
site-chrome marker the other site-wide tools scripts use).

Declarative WebMCP (see docs cited in the brief — webmachinelearning/webmcp
declarative-api-explainer.md):
  - `toolname`   on the <form> — one stable ASCII name for the whole site,
    since almost every lead-form page shares the same CTA/offer
    ("Get my custom assessment" / "Отримати індивідуальний аудит"); the small
    number of PPC pages with a different button label are still the same
    underlying quote/assessment request, so the single name still matches
    what the form really is.
  - `tooldescription` on the <form> — in the page's own language.
  - `toolparamdescription` on every *visible* input/textarea (never on the
    hidden `company_url` honeypot).
  - `toolautosubmit` is deliberately never added (human confirms submit).

Safe to re-run: a <form class="lead-form"> that already carries `toolname=`
is left alone; each visible field missing `toolparamdescription` gets one
independently, so a partial prior run still converges. Script-tag injection
skips any page that already references `assets/webmcp.js`.

Usage:
    python3 tools/add_webmcp_attrs.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

TOOLNAME = "request_coffee_service_assessment"

TOOLDESC_EN = (
    "Request a free, no-obligation custom coffee machine rental and service "
    "quote or assessment for a business location in Kyiv or Kyiv Oblast. "
    "Anima Volitiva matches equipment to the venue, quotes individually, and "
    "offers a free 14-day trial with no prepayment."
)
TOOLDESC_UK = (
    "Замовити безкоштовний, без зобов'язань індивідуальний розрахунок або "
    "аудит оренди та сервісу кавомашин для вашого бізнесу в Києві чи "
    "Київській області. Anima Volitiva підбирає обладнання під об'єкт, "
    "розраховує вартість індивідуально та пропонує безкоштовний 14-денний "
    "тест без передоплати."
)

# field name -> (EN toolparamdescription, UK toolparamdescription)
FIELD_DESCRIPTIONS = {
    "name": (
        "Contact person's full name.",
        "Повне ім'я контактної особи.",
    ),
    "business": (
        "Business or venue name.",
        "Назва компанії або закладу.",
    ),
    "city": (
        "City. Service area is Kyiv city and Kyiv Oblast.",
        "Місто. Сервіс доступний у місті Київ та Київській області.",
    ),
    "machines": (
        "Number of coffee machines needed, if known (optional).",
        "Кількість кавомашин, якщо відомо (необов'язково).",
    ),
    "contact": (
        "Email or phone number to reach you.",
        "Email або номер телефону для зв'язку.",
    ),
    # D4 qualification-without-UI-change: everything below is asked inside
    # this one free-text field, never rendered as separate form fields.
    "message": (
        "Optional notes for our team. If known, please include: business "
        "type (office, cafe or restaurant, hotel, retail or gas station, "
        "coworking, or other), approximate headcount, your role at the "
        "company, whether the city is Kyiv city or Kyiv Oblast, which "
        "package interests you (Start, Pro, Max, or not sure yet), and your "
        "preferred contact channel (phone, email, or Telegram).",
        "Додаткові нотатки для нашої команди. Якщо відомо, вкажіть: тип "
        "бізнесу (офіс, кафе чи ресторан, готель, роздрібна торгівля чи "
        "АЗС, коворкінг або інше), приблизну кількість співробітників, вашу "
        "посаду в компанії, чи це місто Київ, чи Київська область, який "
        "пакет вас цікавить (Start, Pro, Max або ще не визначились), і "
        "бажаний канал зв'язку (телефон, email чи Telegram).",
    ),
}
FIELD_DESCRIPTIONS["details"] = FIELD_DESCRIPTIONS["message"]

HONEYPOT_NAME = "company_url"

FORM_OPEN_RE = re.compile(r'<form\b[^>]*class="lead-form"[^>]*>')
FIELD_RE = re.compile(r'<(input|textarea)\b[^>]*>')
NAME_ATTR_RE = re.compile(r'\bname="([^"]+)"')
TYPE_ATTR_RE = re.compile(r'\btype="([^"]+)"')


def is_uk(rel_path: str) -> bool:
    return rel_path == "ua" or rel_path.startswith("ua/")


def add_form_attrs(text: str, rel_path: str) -> tuple[str, bool]:
    changed = False

    def sub(m: re.Match) -> str:
        nonlocal changed
        tag = m.group(0)
        if "toolname=" in tag:
            return tag
        changed = True
        desc = TOOLDESC_UK if is_uk(rel_path) else TOOLDESC_EN
        insert = f' toolname="{TOOLNAME}" tooldescription="{desc}"'
        return tag[:-1] + insert + ">"

    return FORM_OPEN_RE.sub(sub, text), changed


# A handful of PPC pages repurpose the `name="machines"` input for a
# different question entirely (Codex #1 review, W1) — same field name, a
# visibly different <label> just before it. Checked against the preceding
# ~40 chars of the page's own text, in order, before falling back to the
# generic "number of coffee machines" description.
MACHINES_FIELD_OVERRIDES = [
    ("Team size", (
        "Approximate headcount at the venue, if known (optional) — not a machine count on this page.",
        "Приблизна кількість співробітників на об'єкті, якщо відомо (необов'язково) — не кількість апаратів на цій сторінці.",
    )),
    ("Sites", (
        "Number of sites/locations needing coverage, if known (optional) — not a machine count on this page.",
        "Кількість об'єктів/локацій, які потрібно охопити, якщо відомо (необов'язково) — не кількість апаратів на цій сторінці.",
    )),
]


def field_description(name: str, preceding_text: str):
    if name == "machines":
        for label_marker, pair in MACHINES_FIELD_OVERRIDES:
            if preceding_text.endswith(label_marker):
                return pair
    return FIELD_DESCRIPTIONS.get(name)


def add_field_attrs(text: str, rel_path: str) -> tuple[str, bool]:
    changed = False
    out = []
    pos = 0
    for m in FIELD_RE.finditer(text):
        tag = m.group(0)
        out.append(text[pos:m.start()])
        pos = m.end()

        if "toolparamdescription=" in tag:
            out.append(tag)
            continue
        name_m = NAME_ATTR_RE.search(tag)
        if not name_m or name_m.group(1) == HONEYPOT_NAME:
            out.append(tag)
            continue
        type_m = TYPE_ATTR_RE.search(tag)
        if type_m and type_m.group(1) == "hidden":
            out.append(tag)
            continue
        preceding = text[max(0, m.start() - 40):m.start()]
        pair = field_description(name_m.group(1), preceding)
        if not pair:
            out.append(tag)
            continue
        desc = pair[1] if is_uk(rel_path) else pair[0]
        changed = True
        out.append(tag[:-1] + f' toolparamdescription="{desc}"' + ">")
    out.append(text[pos:])
    return "".join(out), changed


def webmcp_script_path(rel_path: str) -> str:
    depth = rel_path.count("/")
    return "../" * depth + "assets/webmcp.js"


def add_script_tag(text: str, rel_path: str) -> tuple[str, bool]:
    if "assets/webmcp.js" in text:
        return text, False
    marker = re.search(r'<script src="[^"]*assets/analytics\.js"[^>]*></script>', text)
    if not marker:
        return text, False
    src = webmcp_script_path(rel_path)
    tag = f'\n<script src="{src}" defer></script>'
    i = marker.end()
    return text[:i] + tag + text[i:], True


def process(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    orig = text
    if 'class="lead-form"' in text:
        text, _ = add_form_attrs(text, rel)
        text, _ = add_field_attrs(text, rel)
    text, _ = add_script_tag(text, rel)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    touched = 0
    for path in sorted(ROOT.rglob("*.html")):
        if ".git" in path.parts:
            continue
        if process(path):
            touched += 1
    print(f"updated {touched} file(s)")


if __name__ == "__main__":
    main()
