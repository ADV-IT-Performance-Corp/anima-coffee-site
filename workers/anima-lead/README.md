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
npx wrangler secret put ROISTAT_API_KEY                 # values typed on the PC, never in chat/git
npx wrangler secret put ROISTAT_LEAD_URL                # Roistat "add lead" proxy API URL for the EU project
npx wrangler secret put IP_SALT
npx wrangler deploy                                     # prints https://anima-lead.<sub>.workers.dev
```
Until `ROISTAT_*` are set the Worker still stores every lead (status `pending`) and delivers once they appear.
`ROISTAT_LEAD_URL` / field names are NOT verified against Roistat's live API here: confirm with one
Roistat-side test lead (marked TEST, deleted in Kommo) before relying on it.

## Activation (after deploy and a manual OPTIONS/health check, no real leads)
1. Add the Worker origin to `connect-src` in `_headers` and the meta CSP.
2. Set every form's `data-endpoint` to `https://<worker-host>/api/anima/lead` (and optionally a custom domain).
3. Rollback: empty `data-endpoint`; stored rows stay and the cron keeps delivering them.

## Local tests (no network, no wrangler): `cd workers/anima-lead && npm test` (Node >= 22, uses node:sqlite).
