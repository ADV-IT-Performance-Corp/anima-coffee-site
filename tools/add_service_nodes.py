#!/usr/bin/env python3
"""Add a page-specific Service node to the 11 landing pages that are
missing one, and fix the `provider` field on the 2 smarttouch-pos-
integration.html pages whose existing Service node doesn't reference the
Organization @id correctly (tools/check_aeo_leads.py's
service_node_problems()). stdlib only, json.loads/json.dumps discipline
(no regex surgery on the JSON payload) — same approach as
tools/add_organization_contactpoint.py.

Every `name`/`description` below is hand-authored per page, grounded in
that page's own existing visible copy (title/h1/intro paragraphs) — no
new capabilities, numbers or claims are introduced (truth rule). See the
task report for the source sentence each one was drawn from.

Excluded: google46d01ca3a8e17a46.html is a bare 53-byte Google Search
Console verification token file (no <html>, no Organization node, no
visible content at all) — it cannot support and does not need a Service
node. Left untouched; reported as a BLOCKED item rather than forced.

Usage: python3 tools/add_service_nodes.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_aeo as ca  # noqa: E402

_BLOCK_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
_JSONLD_BLOCKS_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

# Established site-wide shape for a Service node's areaServed (mirrors
# maintenance.html's Service node: {"@type": "Place", "name": "Kyiv &
# Kyiv Oblast"}).
_AREA_SERVED = {"@type": "Place", "name": "Kyiv & Kyiv Oblast"}

# rel path -> (name, description). Each description paraphrases that
# page's own title/h1/intro copy — see the task report for citations.
NEW_SERVICE_NODES = {
    "about.html": (
        "Managed Coffee Equipment Rental and Full-Service Coffee Program",
        "Professional coffee equipment rental and full-service coffee program "
        "for HoReCa, retail and corporate offices across Kyiv and Kyiv Oblast "
        "— Dr. Coffee and Necta super-automatics plus professional espresso "
        "machines, premium roasted coffee, staff training and support, as "
        "detailed in Anima Volitiva's company passport.",
    ),
    "answers.html": (
        "Coffee Machine Rental, Service and Supply Guidance",
        "Straight answers for Kyiv-area offices, restaurants and retail "
        "operators about coffee machine rental, service and supply, with "
        "equipment and service sized to the operator's exact volume and "
        "location.",
    ),
    "dr-coffee-vs-espresso.html": (
        "Coffee Equipment Selection: Super-Automatic vs Professional Espresso Machines",
        "Guidance on choosing between Dr. Coffee/Necta super-automatic "
        "machines and professional espresso machines (La Spaziale, Nuova "
        "Simonelli, Rancilio, Iberital, Astoria, Fiorenzato) — both equipment "
        "classes are in Anima Volitiva's rental lineup with the same managed "
        "service behind them, fitted to staffing, volume pattern and drink "
        "culture.",
    ),
    "superautomatic-vs-espresso-machine.html": (
        "Premium vs Commercial Coffee Machine Comparison and Selection",
        "A look at what Anima Volitiva actually installs across Kyiv and "
        "Kyiv Oblast and how super-automatic (Dr. Coffee, Necta) and "
        "professional espresso equipment classes really differ, to help "
        "operators pick the right fit.",
    ),
    "turnkey-100-person-offices.html": (
        "Turnkey Full-Service Coffee Program for 100+ Person Offices",
        "A single managed rental agreement for offices of 100 or more people "
        "in Kyiv Oblast: super-automatic equipment sized to real consumption, "
        "premium roasted coffee delivered weekly, staff training included, "
        "and a 24/7 support line, with no equipment purchase required.",
    ),
    "zero-downtime-restaurants.html": (
        "24-Hour Recovery Coffee Service for High-Volume Restaurants",
        "A managed coffee rental model for high-volume Kyiv restaurants "
        "built around 24/7 support: on any breakdown, a technician or "
        "replacement machine is provided within 24 hours, same-day where "
        "operationally possible, so a breakdown never turns into days "
        "without coffee.",
    ),
    "ua/about.html": (
        "Оренда кавообладнання та повний спектр кавового сервісу",
        "Оренда професійного кавообладнання та повний спектр кавових рішень "
        "для HoReCa, ретейлу та корпоративних офісів Києва і Київської "
        "області — суперавтомати Dr. Coffee та Necta, професійні "
        "еспресо-машини, преміальна кава, навчання персоналу та підтримка, "
        "як описано в паспорті компанії Anima Volitiva.",
    ),
    "ua/answers.html": (
        "Консультації з оренди, сервісу та постачання кавомашин",
        "Прямі відповіді для офісів, ресторанів та ретейлу Києва й області "
        "про оренду кавомашин, сервіс і постачання, з підбором обладнання та "
        "сервісу під конкретний обсяг і локацію.",
    ),
    "ua/dr-coffee-vs-espresso.html": (
        "Вибір кавообладнання: суперавтомати чи професійні еспресо-машини",
        "Допомога у виборі між суперавтоматами Dr. Coffee/Necta та "
        "професійними еспресо-машинами (La Spaziale, Nuova Simonelli, "
        "Rancilio, Iberital, Astoria, Fiorenzato) — обидва класи обладнання "
        "в орендному парку Anima Volitiva з однаковим повним сервісом, "
        "підібрані під персонал, навантаження та кавову культуру закладу.",
    ),
    "ua/turnkey-100-person-offices.html": (
        "Кавове рішення «під ключ» для офісів на 100+ співробітників",
        "Єдиний договір керованої оренди для офісів від 100 співробітників у "
        "Київській області: суперавтомат, підібраний під реальне споживання, "
        "преміальна кава зі щотижневою доставкою, навчання персоналу та "
        "підтримка 24/7, без купівлі обладнання.",
    ),
    "ua/zero-downtime-restaurants.html": (
        "Кавовий сервіс з відновленням за 24 години для ресторанів з високим навантаженням",
        "Модель керованої оренди кавообладнання для ресторанів Києва з "
        "високим навантаженням, побудована навколо підтримки 24/7: у разі "
        "поломки технік або підмінна машина надаються протягом 24 годин, де "
        "операційно можливо — день у день, щоб поломка ніколи не "
        "перетворювалася на дні без кави.",
    ),
}

# Pages whose existing Service node's `provider` needs to be FIXED to
# reference the Organization @id (not created anew).
FIX_PROVIDER_PAGES = [
    "smarttouch-pos-integration.html",
    "ua/smarttouch-pos-integration.html",
]


def _flatten(data):
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


def _has_service_with_good_provider(nodes):
    for n in nodes:
        if isinstance(n, dict) and n.get("@type") == "Service":
            provider = n.get("provider")
            pid = provider.get("@id") if isinstance(provider, dict) else None
            if pid and str(pid).endswith("#organization"):
                return True
    return False


def add_service_node(rel, html_src, name, description):
    def repl(m):
        prefix, body, suffix = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except Exception:
            return m.group(0)
        nodes = _flatten(data)
        org = _find_org(nodes)
        if org is None:
            return m.group(0)
        if _has_service_with_good_provider(nodes):
            return m.group(0)  # idempotent
        org_id = org.get("@id")
        service = {
            "@type": "Service",
            "provider": {"@id": org_id},
            "name": name,
            "description": description,
            "areaServed": _AREA_SERVED,
        }
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            data["@graph"].append(service)
        elif isinstance(data, list):
            data.append(service)
        else:
            # bare single-node document: promote to a list
            data = [data, service]
        new_body = json.dumps(data, ensure_ascii=False, indent=2)
        return prefix + new_body + suffix

    return _BLOCK_RE.sub(repl, html_src, count=0)


def fix_provider(html_src):
    # The Organization node and the Service node needing a fix can live in
    # DIFFERENT <script> blocks on the same page (confirmed on
    # smarttouch-pos-integration.html: block 1 has TechArticle+Organization,
    # block 2 has Service+FAQPage) — so first find the page-wide
    # Organization @id across every block, then patch whichever block(s)
    # contain a Service node with a bad provider.
    org_id = None
    for block in _JSONLD_BLOCKS_RE.findall(html_src):
        try:
            data = json.loads(block)
        except Exception:
            continue
        org = _find_org(_flatten(data))
        if org is not None and org.get("@id"):
            org_id = org.get("@id")
            break
    if org_id is None:
        return html_src

    def repl(m):
        prefix, body, suffix = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except Exception:
            return m.group(0)
        nodes = _flatten(data)
        changed = False
        for n in nodes:
            if isinstance(n, dict) and n.get("@type") == "Service":
                provider = n.get("provider")
                pid = provider.get("@id") if isinstance(provider, dict) else None
                if not (pid and str(pid).endswith("#organization")):
                    n["provider"] = {"@id": org_id}
                    changed = True
        if not changed:
            return m.group(0)
        new_body = json.dumps(data, ensure_ascii=False, indent=2)
        return prefix + new_body + suffix

    return _BLOCK_RE.sub(repl, html_src, count=0)


def main():
    patched = []

    for rel, (name, description) in NEW_SERVICE_NODES.items():
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        new_text = add_service_node(rel, text, name, description)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            patched.append(f"{rel}: added Service node {name!r}")
        else:
            patched.append(f"{rel}: SKIPPED (no change — already has a good Service node, or no Organization node found)")

    for rel in FIX_PROVIDER_PAGES:
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        new_text = fix_provider(text)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            patched.append(f"{rel}: fixed Service provider @id reference")
        else:
            patched.append(f"{rel}: SKIPPED (no change — provider already correct, or no Organization node found)")

    for line in patched:
        print(line)


if __name__ == "__main__":
    main()
