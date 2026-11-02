# Anima server intake integration â€” 2026-10-31

## Current evidence and scope

Observed via read-only HTTPS GET on 2026-10-31: `/` returns HTTP 200,
`Server: GitHub.com`, one empty `data-endpoint`, and no `anima-chat-ws` meta.
`/assets/lead.js` returns 200 and includes the browser outbox.
This proves the inspected homepage uses the browser/Roistat path, not delivery
into Roistat or amoCRM. No customer enquiry or live probe was submitted.

Source baseline: anima-coffee-site main `f0f72637892256ee35b1ce3ab1b7f31d38ef27ae`
(PR #89). Existing author/session pointers are in PR #87 and PR #89; readable
Claude links are not a resumed executor session. This work is a separate direct
Codex candidate, not an OpenClaw execution or a resumed Claude session.
GStack investigate/review instructions were read and applied; this host lacks
`gstack-skill-start`. No verified Anima GBrain connection is exposed here, and
no AMC runtime, memory, credentials or gateway was used for Anima.

## Reuse decision

Reuse ADV-Strategy-Core's dedicated `POST /api/anima/lead`, not `/api/lead`
or `/api/lead/v2` (those routes must not route Anima into ADV destinations).
Canonical source inspected via GitHub on 2026-10-31:

- [Anima intake](https://github.com/ADV-IT-Performance-Corp/ADV-Strategy-Core/blob/main/deep_research/api/routers/anima_lead.py):
  schema, fixed Anima tenant, transaction before response, 503 on storage failure.
- [Store](https://github.com/ADV-IT-Performance-Corp/ADV-Strategy-Core/blob/main/deep_research/api/anima_lead/store.py):
  lead/event/outbox transaction and tenant + idempotency-key uniqueness.
- [Notifiers](https://github.com/ADV-IT-Performance-Corp/ADV-Strategy-Core/blob/main/deep_research/api/anima_lead/notifiers.py):
  Anima-only amoCRM webhook and optional email. This adapter explicitly does
  not write to Roistat. A webhook 2xx is transport acceptance; its optional
  provider ID does not by itself establish a CRM record or human receipt.
- [Anima hosting runbook](https://github.com/ADV-IT-Performance-Corp/ADV-Strategy-Core/blob/main/docs/runbooks/anima-chatkit-gemini-cloud-run-2026-10-30.md):
  Anima-owned GCP service and secrets, never ADV's default project.

These are implementation evidence, not evidence that this service is deployed,
configured durably or currently delivering. PR #89 adds static Cloudflare Pages
publishing only; it provisions no database, queue, API or retry worker. Cloudflare
credential presence and deployment success were not observed. No infrastructure
or secrets were changed or read.

## Candidate behavior

No production endpoint is enabled by this change. Existing empty-endpoint
Roistat behavior and contact alternatives remain. Once an approved deployment
sets each form's `data-endpoint` to its HTTPS Anima service `/api/anima/lead`:

1. Human, WebMCP and scripted chat share one first-party intake; no parallel
   Roistat beacon is sent, even after timeout or malformed response.
2. The adapter maps contact to email/phone, company to business, source_page to
   page_slug, fixed `client_slug: anima-coffee`, consent and attribution.
   Form consent follows its displayed submit disclosure; chat requires its
   explicit checkbox. Legacy queued entries are not assigned consent retroactively.
3. Persist a random idempotency key before sending, then reuse it on an identical
   pending request, reload or online event. Endpoint-bound entries are sent only
   to the same currently configured endpoint, never a changed host or Roistat.
4. Accept only HTTP 200 + `status: accepted` + UUID `lead_id`. This is a **stored**
   receipt. Downstream delivery receipts remain in the server outbox/attempt log.
5. Omit credentials and referrer, refuse redirects, bound request time to ten
   seconds. Strip referrer query/fragment in the JSON attribution. No PII logs.
6. Pending browser data stays bounded to three entries/seven days; expired copies
   are physically removed on next load/reconnect. Browser clearing/quota failure,
   extended offline use or closing before the server commits can still lose data.
   This change does not claim lossless browser storage or exactly-once providers.

Old browser-only pending entries stay intact during activation, without automatic
migration to the server. They have no server key or verifiable consent provenance.
Review their migration separately rather than risking duplicates or invented consent.

## Precise activation dependencies

The owner/admin must supply or confirm the **public URL of an already authorized
Anima-owned service** implementing this intake. No public deployment URL or
Anima GCP deployment grant has been established in this session. The repo requires
approval for Anima GCP operations; do not use ADV's project as a substitute.
Do not send secrets in chat. Have the Anima admin configure these privately:

- `ANIMA_LEAD_DATABASE_URL` to durable Postgres; reject the SQLite development
  fallback on Cloud Run. Confirm schema migrations, access control, backups,
  encryption, retention/deletion policy and a restart/scale-to-zero readback.
- `ANIMA_LEAD_AMOCRM_WEBHOOK_URL` and/or the existing Anima SMTP destination.
  Verify the recipient is Anima, mapping, a real downstream record ID and
  receiving-side idempotency on tenant + lead/idempotency key. Provider timeout
  after commit can otherwise duplicate a deal despite intake deduplication.
- Decide how the existing Roistat -> amoCRM route is preserved: use an established
  Roistat server adapter if one exists, or explicitly approve the Anima webhook
  route and attribution mapping. None was verified here. Do not enable both
  intake/CRM writers for a single submission.
- Configure origin/CORS handling for both Anima domains; verify preflight and
  rejection of other origins at the deployed edge. CORS alone is not abuse
  protection; validate rate/capture limits and payload bounds.
- Confirm retries execute without browser returns and without request CPU:
  request-driven Cloud Run/background threads alone are insufficient. Use the
  established scheduler/worker for this service; verify dead-letter alerting,
  retry expiry and provider receipts. The shared v2 sweep route must not be
  assumed to include Anima (it is excluded from v2).

Only after those checks set all form endpoints consistently. Keep Cloudflare
migration separate; a cross-origin Anima API can serve GitHub Pages as well.
Do not embed CRM webhooks or secrets in HTML, assets or Cloudflare static output.

## Verification and release gates

`python -m unittest tools.test_durable_leads` runs real headless Chromium against
local pages and a stub intake. Install the Python Playwright package/browser in
the test environment. Every request outside the loopback fixture is blocked.
The fake receiver is not a real database/CRM and these tests are not production
proof. They cover outages, lost responses, same-key replay, malformed receipts,
consent, human/agent/chat mapping, endpoint changes and rollback isolation.

Before activation run the existing backend tests against an isolated durable DB,
with Anima-only stub receivers: commit -> terminate browser and service -> restart
-> recover outbox -> retry without any page visit -> receiver receipt. Inject
503/429, timeout after receiver commit, duplicate/concurrent keys, expired claims,
and tenant mismatches. Do not use a test label to send a real CRM enquiry.
Require a non-public test tenant/destination in the SAME transport and deploy
configuration, exact-head independent review, and owner authorization for Anima
GCP changes. A normal production enquiry need not be manufactured to test this.

Record separately: source/head, tests, independent review, PR/merged head, CI,
deployed revision/configuration, durable storage readback, downstream provider
receipt and business acceptance. Unknown stages stay unknown. No merge or stub
result can be promoted into production delivery.

Rollback: remove the configured form endpoint to restore the old path for new
submissions. Server-bound pending items will not be replayed through Roistat.
Keep the server worker/database available to complete previously accepted items;
never delete accepted data or reset keys as part of rollback.

## Local validation record

2026-10-31: the original browser contract test failed with `KeyError: client_slug`
on baseline (the old endpoint path posted the incompatible raw form shape).
After implementation, 16 Chromium tests passed using Python Playwright 1.50.0.
The CI job pins that tested harness. AEO, SEO (181 pages), WebMCP (127 forms),
testimonials, blog and Markdown subset (68 twins) checks passed locally.
The existing Node/polyfill suite's endpoint fixture now matches the real API
path and receipt schema; its full polyfill run has not been reproduced here.
An early Windows run of the content checker encountered host cp1252 decoding
errors; rerunning with `PYTHONUTF8=1` passed. Restricted Playwright startup
stalled creating Python's loopback socket pair; the permitted local-network
run completed. Neither is production delivery evidence.

## Review and handoff

PR: https://github.com/ADV-IT-Performance-Corp/anima-coffee-site/pull/90
Owner: this Codex chat, source branch `claude/anima-durable-intake-20261031`.
Initial independent read-only review covered `4bbe2d5`: the capacity finding
was addressed by refusing a fourth server-bound submission rather than silently
evicting an unacknowledged item. Identical pending payloads intentionally reuse
the same key until acceptance is acknowledged: this is the visitor's retry of
an uncertain request. After acknowledgement a new submission gets a fresh key.
Changed payloads also get fresh keys. No long-term person deduplication.

Hosted CI on `4bbe2d5` did not start either job: GitHub reports an account lock
caused by billing. This is an external account dependency, not a test failure
or permission to bypass CI. No billing setting was changed.
The optional AEO-leads check initially failed only its nested llms-full byte
comparison: the Windows generator writes CRLF while Git stores LF. The normalized
content has no diff. Preserve this failed observation separately from later runs.

Open. Obtain the authorized Anima-owned intake URL and deployment access; verify
Postgres and downstream receipts before endpoint activation. (code read)
Open. Resolve the GitHub account lock, then run hosted CI on the final PR head.
Open. Verify receiver-side deduplication, Roistat routing and autonomous retry
using isolated destinations and restart recovery. (code read)
Open. Run full Node/polyfill suite using `webmcp/run_headless_check.js`. (path read)
No release, deployment or business acceptance has been observed. The existing
browser fallback remains active in production. No OpenClaw run/session UUID,
Anima GBrain checkpoint ingestion or remote resume receipt is available here.
