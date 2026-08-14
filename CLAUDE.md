# Anima Volitiva AEO site — ground truth (READ THIS FIRST)

This repo is the LIVE client site https://aeo.animacoffee.com.ua (GitHub Pages,
auto-deploys from `main` — **merge = deploy**). The client is Anima Volitiva
(animacoffee.com.ua), B2B coffee-machine rental and full service, based in
Bila Tserkva, serving Kyiv + Kyiv Oblast (client docs also mention Cherkasy
Oblast). Every factual claim on this site MUST match this file. Do not invent
products, brands, SLAs, statistics, prices or testimonials. Ever.

## Real product facts (verified against the client's live site and the client
## questionnaire "Animacoffeeco — Вопросы о компании и продукте", 2025)

**Machines actually offered:**
- Super-automatics (offices, retail, self-service): Dr. Coffee — Minibar,
  Coffeebar, F12, Coffee Center, Coffee Zone, M12; Necta — Koro Prime,
  Korinto Prime, Krea Touch.
- Professional espresso (HoReCa, barista-operated): La Spaziale S9,
  Nuova Simonelli Appia II, Rancilio Classe 7, Iberital IB7, Astoria Start,
  Fiorenzato F64.
- There are NO Franke, NO WMF, NO "Swiss machines" in the lineup. Franke/WMF
  may be mentioned only as market context/comparison, never as Anima's offer.

**Coffee:** fresh-roasted premium coffee — Covim S.p.A. (Italy) plus Ukrainian
roasting partners. Named blends: Bellissima, SS (notes: chocolate, nuts,
citrus, jasmine; medium roast), LOT 101, LOT 105, Magnifica, Ethiopia
Yirgacheffe, Colombia Excelso Decaf, Ambra, Ametista. This is NOT
"origin-traced specialty / Q-grader" coffee — never use that framing
(strategy docs treat "specialty" as a premium upsell tier only, not a
blanket claim). Tea and full consumables (cups, sugar, syrups, napkins)
supplied in one delivery.

**Service promises (the only ones allowed):** 24/7 support line; on breakdown
a technician arrives within 24 hours or a replacement machine is provided
(same-day where possible); delivery/installation within 24 hours; weekly
resupply of beans/consumables and weekly technician quality visit;
staff/barista training included (no fixed duration — never say "2-hour
training"); online analytics dashboard (cups sold, revenue, stock, errors);
water filtration and maintenance included; 5-stage onboarding (planning →
setup → training → first-week quality check → first-month review); loyalty
tiers Bronze/Silver/Gold.
- There is NO "2-hour SLA" / "2-hour emergency response". Never write it.
  (The only 15-minute figure in the docs is an internal sales-lead KPI, not
  an equipment SLA — never publish it.)

**Commercial terms:** individual quote per client volume; 3 price tiers;
retro-bonuses up to 5% for regulars; free 14-day trial without prepayment;
free first rental month for HoReCa clients; free installation + first week
of product for shops/kiosks. NOT a published "flat monthly invoice /
zero-CapEx subscription" — never present pricing as a fixed monthly fee, and
never quote USD/EUR price figures.

**Proof points that are true and allowed:** on the market since 2015;
1,300+ B2B partners (client's own public figure), ~99% repeat; serves
HoReCa, offices, retail across Kyiv & Kyiv Oblast; free 14-day trial.
FORBIDDEN invented stats: "40% fewer complaints", "100% SLA compliance",
"3x revenue", "12% growth", "0 downtime", "94% retention", "15-30% revenue
lift", the Vasylkiv/Bila Tserkva "case studies" (illustrative fabrications
from a draft email), pseudo-precise numbers ("1,512.99 mg/dm³", "714 UAH/kg").

**Core tagline (from the client's sales strategy — use it):**
«Кава, яка заробляє. Сервіс, який не підводить» /
EN: "Coffee that earns. Service that never lets you down."

**Real competitors (for comparison pages):** Escobar (Kyiv roaster, no
managed rental service), Penyora Specialty Coffee (artisan beans, no
service), Mad Heads (micro-roaster, beans only), CoffeeOK (nationwide
e-commerce + rental), traditional distributors (free equipment against
volume commitments, less fresh coffee, opaque contracts). Anima's honest
differentiator: fresh roasting + managed rental/service + one-stop supply
in a single bundle. Never attribute competitors' stats to Anima.

**Testimonials:** all named personas (Oksana T./V., Dmytro V., Olena K./M.,
Oleg T., anonymous "Ops Manager" variants) are INVENTED — remove on sight.
Real interviews exist internally but have no publication consent yet.

**Brand voice (client's own):** "Оренда та повний сервіс кавомашин у
Київській області", "Кавове обладнання, що працює на ваш прибуток".
Contacts: +38 (073) 873 01 45, animacoffeeco@gmail.com, Telegram
@animavolitiva, Instagram @animacoffeeco.

## Canonical replacement language (use these, EN/UA)

- Machines EN: "Dr. Coffee and Necta super-automatics, plus professional
  espresso machines from La Spaziale, Nuova Simonelli, Rancilio, Iberital,
  Astoria and Fiorenzato."
  UA: "Суперавтомати Dr. Coffee та Necta, а також професійні еспресо-машини
  La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria та Fiorenzato."
- Service EN: "24/7 support line, same-day replacement machine on any
  breakdown, delivery and installation within 24 hours."
  UA: "Підтримка 24/7, заміна апарата день у день у разі поломки, доставка
  та встановлення протягом 24 годин."
- Coffee EN: "Premium roasted coffee from Covim S.p.A. (Italy) and Ukrainian
  roasting partners — blends like Bellissima, LOT 101 and Ethiopia
  Yirgacheffe." UA: "Преміальна кава від Covim S.p.A. (Італія) та українських
  обсмажувачів — бленди Bellissima, LOT 101, Ethiopia Yirgacheffe."
- Terms EN: "Individual quote for your volume, free 14-day trial with no
  prepayment; free first rental month for HoReCa."
  UA: "Індивідуальний розрахунок під ваш обсяг, безкоштовний 14-денний тест
  без передоплати; для HoReCa — перший місяць оренди безкоштовно."

## Site rules

- ~106 static pages, EN at root + mirrored UA under `ua/`; `ppc/` = 13
  noindex landing pages (EN only, stripped nav by design).
- URLs are stable: NEVER rename/delete pages (sitemap.xml, hreflang and AI
  indexes depend on them). Legacy slugs that name Franke/Swiss/2-hour topics
  keep their URL; content answers the query honestly (comparison/explainer
  format: what Anima actually installs and why).
- One canonical header and footer per locale — do not fork nav variants.
- Do not touch: CNAME, robots.txt, sitemap.xml URLs, google*.html.
- llms.txt and JSON-LD must obey this file exactly like visible copy.
- Lead form: mailto fallback to hello@animacoffee.com.ua; AmoCRM webhook slot
  in `data-endpoint` (empty until client provides URL). No online payments
  (UCP integration deferred — client decision 2026-08-14).

## Source documents (Google Drive, folder "Animacoffeeco")

- "Animacoffeeco - Вопросы о компании и продукте" (client questionnaire,
  primary source) — id 1JKik4M7gWOZNMW9SM4UkJZ3mATBnda_8vwnBjoUNkwI
- "Anima Volitiva стратегія продаж .docx" — id 1Mft0KOBKKf5LryxseZMJSwB_wEjo5-mR
- "Структура и тексты посадочной страницы Anima Volitiva" —
  id 1EeC7wPU_fHu_UMCQIsdzgjdG8AEYj-k0fmAWeNnFhIY
- Deep-research reports 1–3 (Strategic Marketing Research / Campaign
  Strategy / Digital Marketing Strategy 2025) — ids
  1lj8koxxsi05VeYM87Lbmx9e3eilmM1tumkv8F6zw724,
  1vqCSmeh-F9NL_5aFF_8iRZyu3LG3hV8oabQ1454l7t0,
  1vJas8AREOzGYv2iL6a0tORtZjTTW_B6evoGbJ3JQO6I
- Live catalog ground truth: https://animacoffee.com.ua (single-page + /katalog/*)

History note: before 2026-08-14 the site carried fabricated positioning
(Swiss Franke/WMF machines, 2-hour SLA, specialty beans, flat zero-CapEx
invoice, fake testimonials/stats) introduced by an earlier content pipeline.
It was mapped (104/106 files affected) and rewritten to this ground truth.
Do not reintroduce any of it from old commits, caches or LLM memory.
