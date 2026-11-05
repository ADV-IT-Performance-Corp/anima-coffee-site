# Anima lead: Workers Free + D1 hardened candidate

Production delivery OFF. Replaces the hosting/storage part of the planned backend, preserving the existing Roistat-to-Kommo integration. Never enable a competing direct-CRM sender. Browser fallback remains unchanged except capturing the original Roistat visit.

## Contract and limits

POST `/api/anima/lead` matches the merged site adapter. Fixed tenant `anima-coffee`, exact site origin, bounded payload, explicit consent. Origin checks are not authentication: non-browser clients can forge them. A required edge limiter uses ephemeral keyed IP identifiers (10 requests/minute per location); no raw IP is retained. Verify namespace 1001 is unused in the Anima account before deploying. Missing binding or trusted CF IP fails closed. Distributed abuse remains possible; the 500-new-leads/day atomic cap is a final circuit breaker, not complete bot protection. Validate abuse controls before activation.

D1 commits AES-GCM encrypted contact data before returning accepted + UUID + receipt: stored. This is not a CRM receipt. A keyed fingerprint detects idempotency-key reuse with changed content. One physical database and Worker per Anima environment. No account IDs, real credentials, IPs or raw bodies in this package or logs. Platform observability disabled by default. Payload key must remain available; rotation needs migration.

Cron processes up to three queued records every five minutes independently of browser visits. Missing delivery configuration leaves them queued. Atomic claim prevents concurrent sends. Original roistat_visit persists through replay. Only the fixed HTTPS Roistat URL is called, with callback disabled and sync=1. No direct Kommo token or alternate CRM path.

Payload retention is seven days; cron erases payloads, keeping opaque key/hash tombstones to reject stale replay. D1 backups/Time Travel may retain historical ciphertext; deletion and key lifecycle require review. Tombstone growth needs monitoring. Free quota exhaustion must reject intake and preserve browser fallback, never trigger a paid upgrade.

Provider response parser accepts an illustrative fixture shape only; verify it against an authorized, redacted response before enabling. Both proxy and CRM IDs are required for kommo_confirmed. Roistat acceptance is separate. HTTP errors, timeout, malformed responses and interrupted claims become unknown: a receiver may have committed. Do not blindly resend. Roistat's contact-based duplicate checks are heuristics, not idempotency. Authenticated automated reconciliation/polling is NOT implemented. Existing unknown/accepted records require authoritative readback before retry/state change. End-to-end automatic recovery is incomplete.

## Local verification

Node 24: `npm test` runs real SQLite on disk with synthetic receivers. `node runtime-test.mjs` exercises local Miniflare/workerd+D1. From repo root: `python tools/test_durable_leads.py` exercises headless browser fallback, with non-local requests blocked. A TEST-labelled enquiry in real CRM is prohibited.

## Deployment gates / next safe operation

1. Verify signed-in Anima account and Workers Free plan. Do not inherit user-global Wrangler credentials, another tenant's CLI identity, or upgrade billing. Official Free D1 limits: 5M reads/day, 100k writes/day, 5GB/account, 500MB/database. Workers request/CPU limits also apply. These are documented quotas, not load-test results.
2. Create Anima-only staging Worker + D1; bind DB and apply schema. Configure a generated PAYLOAD_KEY via approved secret entry, not chat/Git/printed shell. Keep DELIVERY_ENABLED=false. No secret is supplied by this code.
3. Existing Anima Roistat project and Kommo account were identified privately. Install that specific integration key through approved secret reference. Never use public counter hash, foreign/global REST key or direct CRM fallback. No production secret has been retrieved or installed here.
4. Verify response schema and stable-reference mapping with a non-production receiver/account; implement authenticated receipt reconciliation for unknown/accepted records. Test outage, restart, lost response after commit, duplicate requests, tenant mismatch, recovery, quota limits, and read back deployed cron/binding + synthetic storage receipts with real destinations blocked.
5. Independent exact-head review and CI precede activation. Set ROUTING_VERIFIED=true and DELIVERY_ENABLED=true only after those gates. Configure the site's endpoint only after safe server validation. Preserve browser outbox and original UUIDs. A merge/test/accepted HTTP response is not production CRM delivery.

References:
- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/d1/best-practices/local-development/
- https://help-en.roistat.com/integrations/additional_settings/proxylead/
- https://help-en.roistat.com/API/methods/proxy-leads/

Evidence: direct development, not an admitted Anima OpenClaw run or GBrain ingestion. Production deployment URL, D1 binding/cron readback and real Roistat/Kommo receipts remain unobserved. No customer enquiries generated.

## Validation record (2026-11-04)

15 Node/SQLite tests passed; 18 isolated Chromium browser tests passed; local workerd+D1 restart/receipt/synthetic downstream round trip passed. The runtime test exposed Workers' unsupported redirect:error setting; changed to manual and non-200 remains unknown. Current Wrangler 4.157.0 uses Miniflare 5.20261103.0-beta; the test pins that exact harness and uses its exported v4 option converter. npm audit reported zero vulnerabilities after removing the old test harness. Local runtime tests do not enforce production CPU/quota limits and are not deployment evidence.

Independent read-only review found the intake abuse gap (required keyed edge limiter added), unverified provider wire/receipt schema (activation remains gated), and missing automated reconciliation (still open). No production Cloudflare resources, billing setting, Roistat or Kommo record was changed. The Anima browser window is minimized and the available UI interface could not restore it; owner was asked only to restore that existing window. No ADV/AMC identity was substituted.

Active sends are excluded from retention cleanup until their bounded lease ends, so cleanup cannot discard an in-flight receipt. Expired unresolved records lose their contact payload under the seven-day policy; opaque IDs/state tombstones remain. The added retention/send race test passes.

## Continuation of merged component

This hardens the existing `workers/anima-lead` from PRs #102/#103. It is the only server intake implementation in this candidate; the temporary parallel prototype has been removed. The provider request retains the documented GET query format from #103, while changing unsupported redirect:error to manual and forbidding arbitrary provider hosts. Disable logging of outbound URLs since the documented API places the integration key in the query.

Schema changes are NOT a migration for an existing deployed database. Deployment has not been verified. If an older D1 already exists, stop before schema application, preserve its data, and supply a reviewed migration to the new tenant/key/encrypted-payload schema. Do not overwrite an existing database or apply CREATE IF NOT EXISTS as if it migrated columns. Existing old outbox records must be reconciled before switching senders.

Prior tests that treated arbitrary 2xx as delivered and blindly retried ambiguous errors are replaced by explicit negative receipt/lost-response tests. The replacement suite covers the same persistence, origin, tenant, consent, contact, body-size, capacity, missing-config and rate-limit paths plus encryption, process restart, concurrency and retention. Historical "success" stub tests are not production proof.

## Local contract repair after #104 (2026-11-05)

The browser emits `anima_<UUID>` idempotency keys; the Worker now accepts that exact existing format and the legacy bare UUID without changing queued keys. Server-generated receipt IDs remain UUIDs. This fixes a real interface mismatch missed by separate browser-stub and server-fixture tests.

Intake serialization now uses the original visit/AI snapshots, including blank or legacy missing values. Only initial enqueue captures missing attribution. Replay never reads a later cookie or AI source, so a lost-response retry keeps identical content and can recover the original D1 receipt. Invalid/nonnumeric cookies remain blank under the existing numeric/32-character reader.

Regression test: from the repository root run `python tools/test_worker_browser_contract.py -v`. It uses an actual Chromium-generated request, the actual Worker bundled into local workerd, and persistent local D1 through a test-only IPC bridge. Every browser request is intercepted: site assets are served from the checkout, intake is handled by the local Worker, all other origins are aborted. Worker outbound fetches are denied, delivery is disabled, and all credentials/contacts are synthetic. It covers first storage, commit-then-lost-response, process restart, changed later visit/AI, legacy missing attribution and invalid cookies. It is not a live provider/deployment test.

`ANIMA_TEST_CHROMIUM` may point to an already installed Chromium binary; no download or sign-in is needed. The existing browser regression suite supports the same optional override.

RED on the merged-source baseline: 4/4 contract tests failed (browser key400; invalid cookie leaked into payload). After the key-only repair, first storage passed while replay and invalid-cookie cases still failed. After attribution repair, 4/4 passed. Existing provider-reconciliation/deployment/CI gates remain unchanged. No endpoint, production flag, billing setting or credential was changed. The hosted-CI billing failure recorded for b6d732d remains an external blocker, not replaced by local PASS. Publication and merge of this repair are separate pending steps.

Local repair verification: 4 browser-to-actual-Worker/D1 tests, 16 Node/SQLite tests, 18 existing browser fallback tests and the local workerd restart fixture passed. Test harnesses disable cf metadata fetching/telemetry and deny downstream traffic; no production provider is used. The IPC helper has bounded read/cleanup waits and is test-only. The existing CI workflow was not changed or rerun in this repair. The new contract test must be included in the publication acceptance packet; future CI integration remains a separate release step.

### CI wiring follow-up (local candidate)

The existing `durable-lead-browser` PR job now installs Node24 and the pinned Workers/D1 harness before its browser checks, then runs `python -m unittest -v tools.test_worker_browser_contract` using the already installed Playwright/Chromium. The existing fallback suite, permissions, event trigger, timeouts and deployment configuration are unchanged. This wires the critical contract regression into the same job; it is not a hosted-CI execution receipt and does not resolve the external billing block. No workflow was dispatched in this local change.
