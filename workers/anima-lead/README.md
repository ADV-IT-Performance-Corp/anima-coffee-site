# anima-lead — server-side lead backup on Cloudflare Workers + D1 (Anima's account)

Free-tier replacement for the Cloud SQL plan. Everything lives in **Anima's** Cloudflare account;
nothing of Anima's runs in ADV's GCP. Contract is the one `assets/lead.js` already speaks:
`POST /api/anima/lead` -> `200 {"status":"accepted","lead_id":"<uuid>"}` (a **stored** receipt),
`503` when storage fails, same idempotency key -> same `lead_id`.

Flow: browser -> Worker (validate, honeypot, per-IP rate limit, origin allowlist) -> **D1 commit** -> answer ->
Roistat server request (creates the lead in Anima's Kommo) -> on failure retry with backoff from a
**cron trigger every 5 min** (no visitor needed), dead-letter after 8 attempts (row kept, never deleted).
A Roistat 2xx is transport acceptance, not proof a manager saw it in Kommo.

## One-time setup (needs ONE login on the PC: `npx wrangler login`, Anima's Cloudflare account)
```
cd workers/anima-lead
npx wrangler d1 create anima-leads                      # copy database_id into wrangler.toml
npx wrangler d1 execute anima-leads --remote --file=schema.sql
npx wrangler secret put ROISTAT_INTEGRATION_KEY         # Roistat CRM-integration key, typed on the PC, never in chat/git
# optional: npx wrangler secret put ROISTAT_LEAD_URL     # defaults to https://cloud.roistat.com/api/proxy/1.0/leads/add
npx wrangler secret put IP_SALT
npx wrangler deploy                                     # prints https://anima-lead.<sub>.workers.dev
```
Until `ROISTAT_INTEGRATION_KEY` is set the Worker still stores every lead (status `pending`) and delivers once they appear.
Request format follows Roistat's documented proxylead API (GET `/api/proxy/1.0/leads/add`: `roistat` visit id, `key`, `title`, `name`, `phone`, `email`, `comment`, `sync=1`); the docs name only `cloud.roistat.com`, no EU host. Not exercised against the live Roistat: no test leads are sent from the live site, so the first real enquiry is the first live proof; watch the outbox `last_error`.

## Activation (after deploy and a manual OPTIONS/health check, no real leads)
1. Add the Worker origin to `connect-src` in `_headers` and the meta CSP.
2. Set every form's `data-endpoint` to `https://<worker-host>/api/anima/lead` (and optionally a custom domain).
3. Rollback: empty `data-endpoint`; stored rows stay and the cron keeps delivering them.

## Local tests (no network, no wrangler): `cd workers/anima-lead && npm test` (Node >= 22, uses node:sqlite).
