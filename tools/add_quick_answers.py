#!/usr/bin/env python3
"""Add a visible 'Quick answer' block (natural question + concise factual answer
pulled from the page's own body) plus matching QAPage schema to conversion landings
that carry no Q&A schema. Direct-answer blocks are what answer-engines extract/cite;
this completes AEO answer-coverage without fabrication — the answer text is the page's
own definitional paragraph, only the question is curated (buyer-intent, per page).
Idempotent (marker). EN + UA (UA answer pulled from the UA body, UA question curated)."""
import re, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "<!--quick-answer-->"

# curated natural buyer-intent questions (EN, UA) keyed by page stem
Q = {
 "coworking-rfid-billing": ("How does RFID coffee billing work for co-working spaces?",
                            "Як працює RFID-білінг кави для коворкінгів?"),
 "franke-milk-edge-vs-manual": ("Franke automatic milk vs manual frothing — which is better for high volume?",
                            "Franke автоматичне молоко проти ручного — що краще для великих обсягів?"),
 "gas-station-fleet-coffee": ("What is the best coffee-equipment setup for gas-station forecourt chains?",
                            "Яке обладнання для кави найкраще для мереж АЗК?"),
 "multi-site-bakery-standardization": ("How do you standardize coffee quality across multiple bakery locations?",
                            "Як стандартизувати якість кави в мережі пекарень?"),
 "office-billing-slack": ("How does automated corporate coffee billing work?",
                            "Як працює автоматичний корпоративний білінг кави?"),
 "opex-vs-capex": ("Is it better to rent (OpEx) or buy (CapEx) commercial coffee equipment?",
                            "Оренда (OpEx) чи купівля (CapEx) кавового обладнання — що вигідніше?"),
 "preventive-maintenance-super-automatics": ("How does preventive maintenance protect leased super-automatic machines?",
                            "Як профілактика захищає орендовані суперавтомати?"),
 "self-service-tech-office-coffee": ("What is a fully-managed self-service coffee station for tech offices?",
                            "Що таке керована self-service кавова станція для IT-офісів?"),
 "specialty-bean-calibration": ("Why calibrate specialty beans for high-volume coffee machines?",
                            "Навіщо калібрувати спешелті-зерно для високонавантажених машин?"),
 "telemetry-fleet-control": ("How does Anima keep a coffee-machine fleet running?",
                            "Як Anima тримає парк кавомашин у роботі?"),
 "water-decarbonization-bwt": ("How do you protect espresso machines from Kyiv's hard water?",
                            "Як захистити еспресо-машини від жорсткої води Києва?"),
 "zero-downtime-restaurants": ("How do Kyiv restaurants achieve zero-downtime coffee service?",
                            "Як ресторани Києва досягають кавосервісу без простоїв?"),
 "franke-pos-integration": ("How does Franke coffee-machine POS integration work?",
                            "Як працює інтеграція кавомашини Franke з POS?"),
 "generator-ecoflow-compatibility": ("Are professional coffee machines compatible with generators and EcoFlow?",
                            "Чи сумісні професійні кавомашини з генераторами та EcoFlow?"),
 "staff-training-waste-reduction": ("How does barista staff training reduce coffee waste?",
                            "Як навчання персоналу зменшує втрати кави?"),
}

def answer_from(t):
    body = t.split("</header>")[-1]
    for m in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        txt = re.sub(r"<[^>]+>", "", m); txt = re.sub(r"\s+", " ", txt).strip()
        txt = html.unescape(txt)
        if len(txt) >= 140 and not txt.lower().startswith(("get ", "see how", "book", "request", "отрим", "дивіть")):
            return txt
    return ""

def inject(path, question, heading):
    p = ROOT / path
    if not p.exists(): return None
    t = p.read_text(encoding="utf-8")
    if MARK in t or re.search(r'"@type": ?"(FAQPage|QAPage)"', t): return None
    ans = answer_from(t)
    if not ans or len(ans) < 140: return None
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', t)
    url = canon.group(1) if canon else ""
    a_short = (ans[:560].rsplit(" ", 1)[0] + "…") if len(ans) > 560 else ans
    vis = (f'\n{MARK}\n<section class="block" aria-label="Quick answer"><div class="wrap">'
           f'<div style="border-left:3px solid var(--accent);padding:18px 22px;'
           f'background:rgba(0,0,0,.03);border-radius:8px;max-width:820px">'
           f'<p style="font-weight:700;margin:0 0 10px;font-size:19px">{html.escape(question)}</p>'
           f'<p style="margin:0;color:var(--ink-soft);line-height:1.7">{html.escape(a_short)}</p>'
           f'</div></div></section>\n')
    schema = ('\n<script type="application/ld+json">'
              '{"@context":"https://schema.org","@type":"QAPage",'
              f'"@id":"{url}#qa","mainEntity":{{"@type":"Question",'
              f'"name":{html_json(question)},"text":{html_json(question)},"answerCount":1,'
              f'"acceptedAnswer":{{"@type":"Answer","text":{html_json(ans[:1100])}}}}}}}</script>\n')
    # visible block right after </header>; schema before </head>
    hi = t.find("</head>")
    t = t[:hi] + schema + t[hi:]
    m = re.search(r"</header>", t)
    idx = m.end() if m else t.find("<body>") + 6
    t = t[:idx] + vis + t[idx:]
    p.write_text(t, encoding="utf-8")
    return path

import json as _j
def html_json(s): return _j.dumps(s, ensure_ascii=False)

en = sum(1 for k,(qe,qu) in Q.items() if inject(f"{k}.html", qe, "Quick answer"))
ua = sum(1 for k,(qe,qu) in Q.items() if inject(f"ua/{k}.html", qu, "Швидка відповідь"))
print(f"quick-answer + QAPage added: {en} EN + {ua} UA landings")
