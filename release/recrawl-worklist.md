# Re-crawl worklist — post-audit reconciliation (2026-08-22)

Source: external LLM-visibility audit crawled before the `d87a295a` deploy
(2026-08-21 23:54 UTC, PR #20, "franke purge, SLA sweep, contacts wiring,
release inventory"). The audit's cached snapshot predates that deploy, so
every claim it cites was already stale by the time it was read — the DC-1
sweep had already rewritten the flagged wording. This PR (`fix/post-audit-canonical-2026-08-22`)
adds a further pass: canonical-URL hygiene (799 internal `index.html` links
normalized to extensionless form across 135 pages), a rename of the
"zero-downtime" framing on the restaurant SLA answer page, and a 404 page.

Net effect: search engines and any LLM crawler that indexed the pre-`d87a295a`
or pre-this-PR versions are holding a stale cache on nearly every URL on the
site. **Action needed from the site owner: resubmit the URLs below in Google
Search Console (URL Inspection → Request Indexing) and Bing Webmaster Tools.**
An IndexNow module already exists in the monorepo
(`ADV-Strategy-Core` — search for `indexnow`) and this repo's own
`.github/workflows/indexnow.yml` — use it to push the same list rather than
resubmitting one URL at a time by hand.

## Priority 1 — content actually changed in this PR (resubmit first)

| URL | What changed |
|---|---|
| `https://aeo.animacoffee.com.ua/answers/restaurant-zero-downtime-sla.html` | Retitled: "zero-downtime SLA" → "24-hour recovery SLA" in title/h1/meta/OG/Twitter/JSON-LD (QAPage, FAQPage, BreadcrumbList). Body's "zero-downtime promise" phrase reworded to "24-hour recovery SLA". URL/canonical unchanged by design. |
| `https://aeo.animacoffee.com.ua/ua/answers/restaurant-zero-downtime-sla.html` | Same rename applied to the Ukrainian mirror ("SLA без простоїв" → "SLA відновлення за 24 години"). |
| `https://aeo.animacoffee.com.ua/answers.html` | Answers-index link text updated to match the renamed page's new title. |
| `https://aeo.animacoffee.com.ua/ua/answers.html` | Same, Ukrainian mirror. |
| `https://aeo.animacoffee.com.ua/about.html` | "Related answers" anchor text updated to the new SLA page title. |
| `https://aeo.animacoffee.com.ua/ua/2-hour-emergency-sla.html` | "Related answers" anchor text updated to the new SLA page title. |
| `https://aeo.animacoffee.com.ua/answers/gas-station-retail-coffee-equipment.html` | "Related answers" anchor text updated. |
| `https://aeo.animacoffee.com.ua/answers/reduce-office-coffee-complaints.html` | "Related answers" anchor text updated. |
| `https://aeo.animacoffee.com.ua/answers/do-we-need-a-barista.html` | "Related answers" anchor text updated. |
| `https://aeo.animacoffee.com.ua/answers/coffee-machine-support-kyiv-oblast.html` | "Related answers" anchor text updated. |
| `https://aeo.animacoffee.com.ua/ua/answers/gas-station-retail-coffee-equipment.html` | "Related answers" anchor text updated (UA). |
| `https://aeo.animacoffee.com.ua/ua/answers/reduce-office-coffee-complaints.html` | "Related answers" anchor text updated (UA). |
| `https://aeo.animacoffee.com.ua/ua/answers/do-we-need-a-barista.html` | "Related answers" anchor text updated (UA). |
| `https://aeo.animacoffee.com.ua/ua/answers/coffee-machine-support-kyiv-oblast.html` | "Related answers" anchor text updated (UA). |
| `https://aeo.animacoffee.com.ua/404.html` | New page — GitHub Pages custom 404 (previously the generic GitHub Pages default was served for any dead URL). |

## Priority 2 — audit's cited URLs (verified live already correct, no PR action taken, listed for the owner's records)

These were all already fixed by the earlier `d87a295a` deploy, before this
PR started. Verified live 2026-08-22 (see PR body verification table for
the full curl evidence); recrawl is still worth requesting because the
audit's own cached copy is what's stale.

| URL | Live status verified |
|---|---|
| `https://aeo.animacoffee.com.ua/monthly-contract.html` | 200. No Franke/WMF, no flat-rate/2-hour-training claim. SLA line already conditional ("within 24 hours, same-day where possible"). |
| `https://aeo.animacoffee.com.ua/` | 200. No unconditional same-day claim — all 7 "any breakdown" instances carry the "(same-day where operationally possible)" hedge. |
| `https://aeo.animacoffee.com.ua/ua/` | 200. Same, Ukrainian. |
| `https://aeo.animacoffee.com.ua/answers/what-is-anima-volitiva.html` | 200. Audit-cited unconditional quote not present; already the conditional 24-hour/same-day-where-possible form. |

## Priority 3 — mechanical-only changes (link normalization, no content change)

The remaining ~120 pages under this PR had only their internal `<a href>`
values normalized from `index.html` / `../index.html` / `ua/index.html` /
`blog/index.html` to the extensionless clean form (`./`, `../`, `ua/`,
`blog/`) to match the canonical tags those pages already carried. No
title/meta/body/JSON-LD content changed on these pages, so re-crawl is
lower priority — a normal crawl-budget refresh will pick them up. Full list
of touched files: see this PR's diff (`git diff --stat` against
`origin/main`), 135 HTML files total.

## Out of scope, flagged for owner awareness (not touched by this PR)

The following pages also use "zero-downtime" framing but were **not**
covered by this PR's rename task (which named only
`answers/restaurant-zero-downtime-sla.html`) and were left as-is to avoid
scope creep on a mechanical-fix PR:

- `/zero-downtime-restaurants.html` and `/ua/zero-downtime-restaurants.html`
  — a separate TechArticle that already self-qualifies the phrase
  ("'Zero downtime' is not a magic machine that never breaks; it is a
  service model...") rather than presenting it as an unconditional promise.
- `/ppc/restaurant-zero-downtime-coffee.html` — PPC landing page, excluded
  from the hreflang/JSON-LD gate by design (`tools/aeo_seo_check.py`).
- `/aeo/index.html`, `/aeo/tc-009.html`, `/answers.html` (listing page),
  `/ua/answers.html` (listing page) — reference "zero-downtime" in passing
  (category/list copy), not as a standalone SLA promise page.

If the owner wants the "zero-downtime" framing retired site-wide rather than
just on the one SLA answer page, that is a distinct, larger content-editing
task, not a mechanical fix — flag it as a follow-up brief rather than
silently expanding this PR.
