# Rendered screenshot pack v1 — corrective release slice, 2026-08-22

Fresh visual proof captured **after** this PR's fixes (release-identity, inventory,
privacy-page copy + link normalization, truth-approval refresh, llms.txt honesty).
Full-page PNGs, 6 key pages x 2 breakpoints = 12 screenshots.

**How captured:** tree served locally (`python3 -m http.server 8899`), rendered via
the on-disk pinned Chromium build resolved by
`ADV-Strategy-Core/scripts/pw_chromium.py` `launch_kwargs()` (never
`playwright install` — see that script's own docstring for why). `wait_until="networkidle"`,
`full_page=True` screenshots.

## Breakpoints

- `mobile-390` — 390x844 viewport (iPhone-class mobile)
- `desktop-1440` — 1440x900 viewport

## Pages

| File prefix | Page | Why this one |
|---|---|---|
| `home-en` | `/` | Primary landing page, EN |
| `home-ua` | `/ua/` | Primary landing page, UA (bilingual parity check) |
| `privacy-en` | `/privacy.html` | This PR's fix: `[PENDING_OWNER ...]` marker removed, internal links normalized to canonical-clean form |
| `privacy-ua` | `/ua/privacy.html` | UA twin of the same fix |
| `services-en` | `/services.html` | Core commercial page |
| `answers-restaurant-sla-en` | `/answers/restaurant-zero-downtime-sla.html` | Subject of the live-parity check in this PR (post-df5e91e3 "24-hour recovery SLA" title + single stats strip) |

## Files

```
home-en--mobile-390.png
home-en--desktop-1440.png
home-ua--mobile-390.png
home-ua--desktop-1440.png
privacy-en--mobile-390.png
privacy-en--desktop-1440.png
privacy-ua--mobile-390.png
privacy-ua--desktop-1440.png
services-en--mobile-390.png
services-en--desktop-1440.png
answers-restaurant-sla-en--mobile-390.png
answers-restaurant-sla-en--desktop-1440.png
```

## What to look for

- `privacy-en` / `privacy-ua`: the "Who this is" section reads as a clean public
  sentence identifying the operator by brand name and published contact —
  no visible placeholder/bracket text.
- `answers-restaurant-sla-en`: hero title reads "24-hour recovery SLA" (not the
  retired "2-hour" claim); no duplicate stats strip.
- All pages: EN/УКР language switcher visible in the top nav, lead-form CTA present.

Verified alongside this pack: `tools/aeo_seo_check.py` — 137/137 pages PASS,
re-run against this branch's tree on 2026-08-22 (see `release.json` at repo root).
