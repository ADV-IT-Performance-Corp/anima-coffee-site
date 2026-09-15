# Testimonials provenance (W3a, 2026-09-14)

Internal record only — not linked from any nav/sitemap. Every quote published
on `index.html`, `ua/index.html`, `about.html`, `ua/about.html`, `llms.txt`
and (optionally) `assets/webmcp.js` must appear verbatim (original-language
text) in this file. See `tools/check_testimonials.py`.

Founder authorization (2026-09-14, verbatim): "по квотам от клиентов - я
давал кастдэвы, я давал ссылку на сайт где их ленд основной мы делали. там
все отзывы реальны и квоты."

No real name of any 2025 custdev interview respondent appears anywhere in
this file or in the rest of this repository. Interview-derived quotes are
attributed by row index only (`R<n>`); see §Secondary source below.

## Primary source — animacoffee.com.ua (client's own live site)

Fetched 2026-09-14 from https://animacoffee.com.ua/ (home page). Five quotes
are rendered as Viber-chat screenshots (`/images/otzivi/1-1.png` through
`5-1.png`); five more are plain-text testimonials in the "Відгуки від 4 типів
клієнтів" grid. Attribution below is exactly what the source page displays —
no name/company/role has been added or altered. Every quote below was
re-transcribed word-for-word against its source image on 2026-09-14 (a prior
pass had introduced two transcription errors — see the `normalized:` /
`corrected:` notes on #1, #3 and #4).

### 1. Марина Джура, М'ята (кав'ярня)
- Source: https://animacoffee.com.ua/ — `/images/otzivi/1-1.png` (Viber
  screenshot)
- Attribution as shown: "Марина Джура М'ята"
- Date collected: 2026-09-14
- Verified against source image: 2026-09-14
- Quote (verbatim, uk): "Хочемо виразити свою вдячність Вашій команді за професіоналізм, компанія «Anima Volitiva» дійсно команда професіоналів, завдяки Вам в нашій кав'ярні завжди смачна, ароматна, якісна кава, дякуємо що завжди на зв'язку, за швидке реагування на наші прохання, за підтримку!! Ми не помилилися в своєму виборі"
- normalized: source image reads "вдячність Вайші команді" — obvious typo
  for "Вашій" (dative of "Ваша"); corrected. Source also has a stray space
  before the comma in "ароматна , якісна" and uses straight quote marks
  around 'Anima Volitiva' where this file uses «guillemets» — both are
  formatting normalizations, not content changes.

### 2. Діана Шевченко
- Source: https://animacoffee.com.ua/ — `/images/otzivi/2-1.png` (Viber
  screenshot)
- Attribution as shown: "Діана Шевченко"
- Date collected: 2026-09-14
- Verified against source image: 2026-09-14
- Quote (verbatim, uk): "Доброго дня. Кава дуже смачна, клієнти задоволені. Набагато смачніше, ніж було раніше. Дякую."

### 3. Діана Самоукіна, LUX CAFE
- Source: https://animacoffee.com.ua/ — `/images/otzivi/3-1.png` (Viber
  screenshot)
- Attribution as shown: "Діана Самоукіна / LUX CAFE"
- Date collected: 2026-09-14
- Verified against source image: 2026-09-14
- Quote (verbatim, uk): "Щиро вдячні компанії за чудову співпрацю! Дуже швидко відреагували на наш запит, допомогли підібрати кавовий апарат і каву, яка ідеально підійшла саме для нашої кав'ярні. Особлива подяка за постійну підтримку: завжди на зв'язку, оперативно реагуєте та приїжджаєте, якщо виникають будь-які питання. Ваша турбота та професійність дуже цінується. Дякуємо!"
- corrected: a prior pass dropped the clause "та приїжджаєте, якщо
  виникають" before "будь-які питання" — not verbatim (flagged in
  pre-merge review of PR #36, 2026-09-14). Re-transcribed from the source
  image and restored on all four site occurrences plus the EN translation.

### 4. Леся, М-н «Продукти»
- Source: https://animacoffee.com.ua/ — `/images/otzivi/4-1.png` (Viber
  screenshot)
- Attribution as shown: "Леся (М-н «Продукти»)"
- Date collected: 2026-09-14
- Verified against source image: 2026-09-14
- Quote (verbatim, uk): "Хочу поділитись своїми враженнями після початку співпраці. Коли ми поставили нові апарати з вашою кавою у нас в кілька разів зріс потік клієнтів на каву. Це було неочікувано навіть для нас. З'явились люди, які відмовились від щоденних поїздок на заправку, куди їздили спеціально випити кави саме такої як там. Та ми й самі із задоволенням зранку п'ємо саме нашу (вашу каву)). Дякуємо за якісне обслуговування та своєчасну доставку інгредієнтів. Чай теж топчик"
- corrected (round 2): a prior pass had "поділитися" — the source image
  reads "поділитись". Both are grammatically valid Ukrainian infinitives,
  but the published quote must match the source image exactly; reverted on
  both site occurrences (index.html, ua/index.html).
- normalized: source image renders "З'явились люди. Які відмовились" as two
  sentences (capital "Які") — normalized to one sentence with a lowercase
  "які" for readability; same for the missing comma before "куди їздили".
- corrected: the word after "із задоволенням" is "зранку" (in the morning)
  in the source image, not "заходу" as a prior pass had it — that was a
  transcription error, not a normalization; fixed on both site occurrences.
- Note: "в кілька разів зріс потік клієнтів" is the customer's own qualitative
  claim (not a specific percentage/figure) — kept as-is; not one of the
  registry's forbidden invented-stat strings ("40% fewer complaints", "3x
  revenue", "12% growth", etc. are exact phrases, this is neither).

### 5. Олексій, власники продуктового магазину
- Source: https://animacoffee.com.ua/ — `/images/otzivi/5-1.png` (Viber
  screenshot)
- Attribution as shown: "Олексій" (contact name), business context from the
  message body: "власники продуктового магазину" (grocery store owners)
- Date collected: 2026-09-14
- Verified against source image: 2026-09-14
- Quote (verbatim, uk): "Ми власники продуктового магазину, почали працювати з кавою Anima Volitiva. Кавою і обслуговуванням дуже задоволені. Любителі кави також оцінили смак та ціну! Вартує своїх коштів! Окремо хочемо подякувати Стасу за ввічливість, оперативність і професіоналізм у своїй сфері."
- normalized: source image reads "вічливість" — a typo missing the "в"
  prefix of "ввічливість" (politeness); corrected to the standard spelling
  on publication.
- Note: "оцінили ... ціну" / "Вартує своїх коштів" is the customer's own
  general value comment — no price figure, tier name or "flat monthly
  price" claim is stated, so it does not smuggle in a rejected commercial
  claim.

### 6. Власник кав'ярні (role-only attribution, as published)
- Source: https://animacoffee.com.ua/ — "Відгуки від 4 типів клієнтів" text
  grid (no image, no personal name shown on the source page — role only)
- Attribution as shown: "Власник кав'ярні" (segment tag: "Кав'ярня")
- Date collected: 2026-09-14
- Verified against source page text: 2026-09-14
- Quote (verbatim, uk): "Тепер я фокусуюсь на розвитку, а не на ремонтах. Гості відчули різницю - і стали повертатись."

## Secondary source — 2025 customer-development interviews

Source file: `~/work/anima-corpus-drive-2025/09-customer-survey-responses.md`
(excerpt of Google Sheet `1l9XJbc9uHf7B-EJdgu0T7KcFzu25LtwdjDQhdKPoiug`, owned
by animacoffeeco@gmail.com — the client's own field research; full survey
lives in the client's Google Drive, private, not part of this repo). Per the
brief, attribution is ANONYMOUS only (role + business type + city) — no
interviewee's personal name is published, and none appears in this file. Rows
are numbered `R1`–`R9` here in the order they appear in the source excerpt's
"Selected verbatim responses" section (source-file row order, not a sheet row
number); the real name behind each `R<n>` lives only in the private,
untracked source file and, when present, in `$ANIMA_CUSTDEV_NAMES_FILE` (see
`tools/check_testimonials.py`).

### 7. Business owner, Bohuslav, Kyiv Oblast (2025 customer survey, anonymized)
- Source: custdev 2025, Drive doc 09, respondent R6
- Original respondent name withheld per brief §Sources.2 (interview quotes
  are anonymous-only)
- Date collected (interview): March 2025. Date published: 2026-09-14
- Quote (verbatim, uk): "Підхід до клієнта, я не вірив, що таке буває. Ваша віддача вражає, швидкість реакція — вау."

### Excluded custdev quotes and why

Every other respondent row in the excerpt was screened and excluded from
publication:
- Most rows are feature requests, objections or switch-trigger answers, not
  testimonial-toned quotes (e.g. respondent R7/barcode scanners, respondent
  R8/objection pattern, respondent R3/wants published prices).
- Respondent R1 (Біла Церква): value quote names "лічильники" (pay-per-cup
  metering) — flagged `[NEEDS-OWNER]` in the source file as not yet on the
  truth registry; excluded to avoid publishing an unvetted feature claim.
- Respondents R5, R8, R9: name a competitor (Bianchi / "Фабрика кави") —
  excluded per brief §Sources.2 ("no competitors by name").
- Respondent R2: switch-trigger mentions price ("ціна нижча") — excluded
  (price-adjacent, negative/churn framing).
- No row mentions Franke/WMF/Swiss machines, a 2-hour SLA, a flat monthly
  price, free-first-month, retro-bonus, specialty beans, "1,300 partners"
  or "94% retention" (confirmed clean by the source file's own contamination
  scan).

## Excluded primary-site content

- `/images/sld/1.jpg`–`10.jpg` ("фото 4"–"фото 10"): site/product photos in
  the same slider block, not reviews — excluded, not testimonials.
- Four of the five text-grid personas (Адміністратор HoReCa, Власник
  торгової точки, Менеджер магазину/Продавець, Офіс-менеджер) were read and
  screened clean (no forbidden claims) but not all were used on every
  page — see each page's own testimonial selection; none were altered or
  excluded for a truth-registry reason.
