# Measurement pack — GTM/GA4 import + GSC setup (slice 4, 2026-09-25)

Site is live at https://aeo.animacoffee.com.ua/. GTM container `GTM-MQQNGFTV`
is installed on every page. GA4 is **not** configured inside it on purpose
(`assets/analytics.js` keeps its `GA4_ID` a placeholder to avoid double
counting — see the comment block at the top of that file). This pack closes
that gap without touching any HTML, `analytics.js`, `webmcp.js` or JSON-LD.

No real IDs are in this repo. `docs/measurement/gtm-ga4-import.json` uses the
placeholder `G-XXXXXXXXXX` for the GA4 Measurement ID; you paste the real one
during import (step 2 below).

---

## 1. Create a GA4 property

1. https://analytics.google.com/ → Admin → **Create property** → name it
   `Anima AEO (aeo.animacoffee.com.ua)`, timezone Ukraine, currency UAH.
2. Add a **Web** data stream for `https://aeo.animacoffee.com.ua`.
3. Copy the **Measurement ID** (format `G-XXXXXXXXXX`) shown on the stream
   details page. You'll paste it in step 2.

## 2. Import the GTM pack

1. https://tagmanager.google.com/ → open container `GTM-MQQNGFTV`.
2. **Admin → Import Container** → upload `gtm-ga4-import.json` from this
   folder → Workspace: your current workspace → **Merge**, and choose
   *"Rename conflicting tags, triggers, and variables"* if GTM flags any
   name collision (it should not, on a clean import).
3. Before publishing, open the **GA4 Measurement ID** constant variable
   under *Variables* and replace `G-XXXXXXXXXX` with the real ID from
   step 1.
4. **Preview** the container against the live site, confirm the `GA4
   Configuration` tag fires on page load and the `GA4 Event - lead_accepted`
   tag fires when a test lead is submitted (see step 5 below for the safe
   way to do that).
5. **Submit → Publish**.

What the pack adds:

| Name | Type | Fires on | Notes |
|---|---|---|---|
| `GA4 Configuration` | Google Tag (GA4 config) | All Pages | Standard GA4 page-view + config tag |
| `GA4 Event - lead_accepted` | GA4 event | Custom event `lead_accepted` | Marked as a key event (conversion) — mirrors the toggle in GA4 Admin → Events, set that toggle manually too after the event first fires |
| `GA4 Event - cta_click` | GA4 event | Custom event `cta_click` | Sends the `channel` param (phone / telegram / form). **Pending**: the sticky-CTA slice that pushes this event to `dataLayer` hasn't landed yet — importing this tag now is safe (it just won't fire until that slice ships), so you don't need a second import round trip |
| `GA4 Event - ai_referral` | GA4 event | Page view, gated by a referrer-host check | Sends `ai_source` (the matched host) when `document.referrer` is one of `chatgpt.com`, `chat.openai.com`, `perplexity.ai`, `gemini.google.com`, `copilot.microsoft.com`, `claude.ai` |

Nothing in `analytics.js` changes — `lead_accepted` is already pushed to
`dataLayer` by `window.animaTrackLead()` (with `source_page` and
`lead_origin` params); this pack just adds the GA4-side tag/trigger that
listens for it.

## 3. Search Console

1. https://search.google.com/search-console → **Add property**.
   - Prefer **Domain** property (`animacoffee.com.ua`) if you also own DNS
     for the apex domain — it covers `aeo.` and every other subdomain in one
     go, verified via a DNS TXT record.
   - If you don't want to touch DNS, use a **URL-prefix** property for
     `https://aeo.animacoffee.com.ua/` instead, verified via the HTML-file
     method: GSC gives you a file like `google1234567890abcdef.html` —
     that's the same convention already used for the existing
     `google46d01ca3a8e17a46.html` file at the repo root (see that file for
     the exact format), upload the new one the same way, in a follow-up
     commit (not part of this PR — it needs the real verification code from
     your GSC account).
2. Once verified, **Sitemaps → Add a new sitemap** → submit `sitemap.xml`
   (already live at `/sitemap.xml`). `ppc-sitemap.xml` is deliberately
   **not** submitted to GSC — see the comment at the top of that file: it's
   for paid-traffic landing pages only, `noindex`, not meant to be organic-
   indexed.
3. **Settings → Users and permissions** — add any teammates who need access.

## 4. Bing Webmaster Tools

https://www.bing.com/webmasters → **Import from Google Search Console**
(one-click once GSC in step 3 is verified) — pulls the same verified
property and sitemap without a second verification step.

## 5. Verifying a test lead end to end

The lead form's own test-lead convention already exists in
`assets/lead.js` (`TEST_MARKER_RE` / `isTestLead()`): put the word **тест**
or **test** anywhere in the *Name* or *Details* field (as a standalone word,
e.g. "Тест ліда" or "test submission" — not inside another word like
"testimonial"). The Roistat deal created from that submission is prefixed
`ТЕСТ — ...` so it's obvious to delete afterward.

Full chain to check, in order:

1. Submit the lead form on the live site with a test-marked name/details.
2. **Roistat** (`https://cloud-eu.roistat.com`) → Leads → confirm a new deal
   appears with the `ТЕСТ —` prefix within ~1 minute.
3. **AmoCRM** → confirm the Roistat→AmoCRM integration opened the matching
   deal (same lead name/prefix).
4. **GA4** → Admin → DebugView (or Realtime report) → confirm a
   `lead_accepted` event lands with `source_page` and `lead_origin: human`
   params, within a minute or two of the submit.
5. Delete the test deal in Roistat/AmoCRM once confirmed — do **not** leave
   test leads in the CRM.

If step 4 doesn't show the event: re-check step 2 of this README (constant
variable pasted with the real ID, container published) before assuming the
site is broken — `analytics.js`/`lead.js` are unchanged by this pack and
already proven to push `lead_accepted` correctly.

---

## Українською

Сайт https://aeo.animacoffee.com.ua/ вже працює. GTM-контейнер
`GTM-MQQNGFTV` встановлено на всіх сторінках. GA4 навмисно не налаштовано
всередині нього (`GA4_ID` у `assets/analytics.js` — заглушка, щоб уникнути
подвійного підрахунку переглядів). Цей пакет закриває прогалину без
редагування HTML, `analytics.js`, `webmcp.js` чи JSON-LD.

### 1. Створіть властивість GA4
Analytics → Admin → Create property → веб-потік для
`https://aeo.animacoffee.com.ua` → скопіюйте Measurement ID (`G-XXXXXXXXXX`).

### 2. Імпортуйте пакет GTM
Tag Manager → відкрийте `GTM-MQQNGFTV` → Admin → Import Container →
завантажте `gtm-ga4-import.json` → **Merge** → вставте реальний Measurement
ID у змінну "GA4 Measurement ID" → Preview на живому сайті → Publish.

### 3. Search Console
Додайте властивість (Domain для `animacoffee.com.ua` через DNS TXT, або
URL-prefix для `aeo.animacoffee.com.ua` через HTML-файл — за прикладом уже
наявного `google46d01ca3a8e17a46.html`). Після верифікації надішліть
`sitemap.xml`. `ppc-sitemap.xml` **не** надсилайте — він лише для платного
трафіку.

### 4. Bing Webmaster
Import from Google Search Console — одна кнопка після верифікації GSC.

### 5. Перевірка тестового ліда
Напишіть слово **тест** окремим словом у полі "Ім'я" або "Деталі" форми —
угода в Roistat отримає префікс `ТЕСТ —`. Перевірте послідовність: форма →
Roistat → AmoCRM → подія `lead_accepted` у GA4 DebugView/Realtime. Видаліть
тестову угоду після перевірки.
