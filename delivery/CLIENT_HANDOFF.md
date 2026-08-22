# Anima Volitiva — AEO Site Handoff

**Live site:** https://aeo.animacoffee.com.ua/
**Release SHA:** `69dc97658e5439de6678278fd2924308d7473cad`
**Release date:** 2026-08-21 (deployed 2026-08-22, 02:42 UTC)
**Prepared:** 2026-08-22

This document summarizes what has been delivered, what is verified, and what
still needs an owner decision before the site is considered fully closed out.
Every number in this document is pulled directly from the repository or from
a live check against the running site — nothing here is estimated.

---

## 1. What this site is

`aeo.animacoffee.com.ua` is an **AEO (Answer Engine Optimization)** knowledge
site for Anima Volitiva — built to be read correctly by both AI answer
engines (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot) and human
visitors. It is bilingual (English + Ukrainian, full parity) and structured
around the questions a B2B buyer actually asks before renting managed coffee
equipment: pricing model, SLA, service area, machine types, contract terms.

Per the repository's release inventory (`release/release-inventory.yaml`),
the site currently ships **136 routes**, broken down as:

| Class | Count | What it means |
|---|---|---|
| **Indexed** | 54 | In the sitemap and `llms.txt`, discoverable by search engines and AI crawlers — home, about, services, answer pages, blog, comparisons, contracts |
| **Served, not indexed** (`noindex,follow`) | 81 | Real, working pages (PPC landing pages, orphaned solution pages, internal AEO test cases, one legacy-URL alias) — live and linkable but deliberately excluded from the sitemap/AI-crawl surface so they don't compete with the indexed set |
| **Omitted** | 1 | The Google Search Console ownership-verification file — not content |

54 indexed URLs is also the exact count confirmed live: `curl
https://aeo.animacoffee.com.ua/sitemap.xml` returns 54 `<loc>` entries today.

---

## 2. Quality evidence

**Entity integrity gate** (checks that every fact rendered on the site — SLA
wording, contact details, service area, JSON-LD — traces back to one
approved source of truth and is consistent site-wide): **status = passed,
0 blocking findings, 2 warnings, composite score 96/100** (recorded run,
checked 2026-08-21; the release-inventory file this is recorded in is the
one governing the current live deploy). The 2 open warnings are not defects
— they are the client-stated growth metrics ("1,300+ partners", "~99%
repeat rate") correctly flagged as first-party claims with no third-party
corroboration yet (see §5).

**AEO/SEO structural gate** (`tools/aeo_seo_check.py` — checks every
indexable page has exactly one H1, a title, a meta description, a canonical
tag, EN/UA/x-default hreflang, valid JSON-LD, and zero broken internal
links): **137/137 pages pass**, verified by re-running the script against
the exact release commit above.

**Rendered-page screenshot pack:** a full visual QA pass (desktop/tablet/
mobile breakpoints, EN + UA, lead-form states) is on file in the ADV-Strategy-Core
repository at `deliverables/anima-dc5-rendered-pack-2026-08-21/` — available
on request.

---

## 3. Contacts published on the site

Pulled from the site's own JSON-LD / contact blocks, matching the live
`animacoffee.com.ua` primary site as of the 2026-08-22 check:

- **Phone:** +380 73 873 01 45
- **Email:** animacoffeeco@gmail.com *(see §6 — a second address is used
  internally by the lead-form backend; needs to be reconciled to one)*
- **Address:** Kyiv / Bila Tserkva, vul. Pavlichenko 29a
- **Social (`sameAs`):** Facebook, Instagram (`@animacoffeeco`), Telegram
  (`@animavolitiva`), Viber

**Canonical SLA wording**, quoted verbatim as it appears site-wide and as
recorded as the single approved formula in `release/truth-approval.yaml`:

> **EN:** "24/7 support. A technician or replacement machine is provided
> within 24 hours; same-day service is available where operationally
> possible."
>
> **UA:** "Підтримка 24/7. Технік або підмінна машина надається протягом
> 24 годин; того ж дня — коли це операційно можливо."

This replaced an earlier, inconsistent mix of unconditional "same-day" and
"2-hour" claims across the site (62 UA + 17 EN occurrences rewritten in the
DC-1 sweep, PR #20) — this is now the only SLA claim live anywhere on the
site.

---

## 4. Lead form — current behavior

The lead form (present on the homepage and services page) **POSTs JSON to a
configurable endpoint** set per page via a `data-endpoint` HTML attribute.
No endpoint is hardcoded in the form's code.

- **Right now, `data-endpoint` is empty on every page.** When a visitor
  submits, the form does **not** fail silently and does **not** fabricate a
  success message — it shows a "not yet connected, contact us directly"
  message and highlights the page's own phone/email contact block.
- **A conversion is counted only when the backend answers HTTP 200 with a
  real `lead_id`** in the response body. There is no click-based or
  speculative conversion tracking anywhere in the form's code — a visitor
  who only sees the fallback contact block does not register as a
  conversion.
- A hidden honeypot field and in-browser UTM/`gclid` capture are already
  wired, so once an endpoint is set, spam filtering and paid-traffic
  attribution work immediately with no further site changes.

**Two ways to activate the form, owner's choice:**

1. **Route it to Roistat**, the same system the primary `animacoffee.com.ua`
   site already uses. This is the owner's stated preference. It requires
   the owner (or whoever manages Roistat) to supply the endpoint URL and
   any required auth, which then gets set as the `data-endpoint` value.
2. **Use the first-party lead backend already built and merged** in the
   `ADV-Strategy-Core` repository (`POST /api/anima/lead` — transactional
   storage, honeypot, rate limiting, CORS pinned to the two Anima domains,
   idempotent, fails closed with a 503 rather than a fake success). This
   endpoint is fully implemented and tested but sits inert until the owner
   sets its `ANIMA_LEAD_*` environment variables (AmoCRM webhook URL and/or
   SMTP credentials for lead notification, plus a rate-limit override if
   the default of 12/minute needs changing). No code work is required to
   turn this on — only supplying the credentials.

Either path is a configuration step, not a development task — the site-side
code does not need to change either way.

---

## 5. Known open items (honest status)

These are flagged, not hidden, and none of them block the site being live
and functioning:

- **Growth metrics need one owner-approved definition.** The site currently
  states "1,300+ B2B partners" and "~99% repeat rate" (client-stated,
  unverified by any third party). The primary `animacoffee.com.ua` site
  states a different figure in the same spirit — a live check on
  2026-08-22 found: *"94% клієнтів залишаються з нами понад рік"* ("94% of
  clients remain with us for over a year"). These are two different metrics
  (a partner-repeat-rate vs. a one-year-retention rate) that could both be
  true, or could be the same claim measured two ways — the definitions have
  never been reconciled. A prior audit also flagged a further "1,500+"
  variant reported on the Instagram profile; this session could not
  independently verify Instagram (blocked by network policy from this
  environment) and flags it for the owner to check directly. Until defined,
  treat every partner-count/repeat-rate figure on any Anima surface as
  **directional, not audited**.
- **Sales email canonicalization pending.** The visible contact copy
  site-wide uses `animacoffeeco@gmail.com`. The (currently inert) first-party
  lead backend's notification config is separately keyed off
  `ANIMA_LEAD_NOTIFY_EMAIL_TO`, and the historical `hello@animacoffee.com.ua`
  address has also been used as an inbox destination in earlier drafts of
  the form. Pick **one** canonical sales address before wiring any lead
  notification path, so a submitted lead and a "call us" contact click don't
  point to two different inboxes.
- **Search-cache refresh in progress.** A post-audit pass (PR #22, merged
  2026-08-22 01:48 UTC) normalized ~800 internal links and retitled one SLA
  answer page; the recrawl worklist is at `release/recrawl-worklist.md`
  (priority-ordered, ~15 URLs need a fresh crawl first). IndexNow has
  already auto-fired on every push to `main` that touches HTML — most
  recently a manual run on 2026-08-22 at 02:43 UTC, all runs succeeded
  (`gh run list --workflow=indexnow-submit`). Google Search Console /
  Bing Webmaster "Request Indexing" on the priority-1 URLs is the one
  remaining owner action to speed up re-crawl beyond what IndexNow already
  covers.
- **Primary-domain sync recommendation.** `animacoffee.com.ua` (the main
  business site) and `aeo.animacoffee.com.ua` (this AEO site) are not yet
  cross-referenced as the same entity in each site's own JSON-LD, and
  `animacoffee.com.ua` does not link to this site. Adding a `sameAs`
  reference and a visible cross-link on the primary site would strengthen
  both sites' AI-crawler and search signal — this is a recommendation, not
  a defect on either site.

---

## 6. Rollback

The site deploys via **GitHub Pages** directly from the default branch of
`ADV-IT-Performance-Corp/anima-coffee-site` (that default branch is the
one this release was published from). To roll back to any earlier state:

1. Identify the commit SHA to restore (`git log` on the repository).
2. Revert or reset the default branch to that SHA in a normal commit.
3. Publish that commit to the repository's default branch the same way
   every other release in this document was published.

GitHub Pages redeploys automatically once the default branch updates —
typically live within 1-2 minutes. There is no separate rollback console or
manual deploy step. **Contact:** the repository owner (ADV IT Performance
Corp GitHub org) for any rollback or access request.

---

## 7. Acceptance

See `delivery/CLIENT_ACCEPTANCE.md` for the sign-off template.
