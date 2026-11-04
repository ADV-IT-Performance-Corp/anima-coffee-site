import test from "node:test";
import assert from "node:assert/strict";
import { makeDB } from "./d1shim.js";
import { handle } from "../src/index.js";
import { deliverOne, sweep } from "../src/deliver.js";

const ORIGIN = "https://aeo.animacoffee.com.ua";
const baseEnv = () => ({ DB: makeDB(), ALLOWED_ORIGINS: ORIGIN + ",https://animacoffee.com.ua", IP_SALT: "t" });
const confEnv = () => ({ ...baseEnv(), ROISTAT_API_KEY: "k", ROISTAT_LEAD_URL: "https://roistat.invalid/leads/add" });
const good = (o = {}) => ({ client_slug: "anima-coffee", idempotency_key: "key-12345678", name: "Test", phone: "+380501234567",
  consent: true, page_slug: "/", lead_source: "form", roistat_visit: "123", ...o });
const post = (env, body, headers = {}, now) => handle(new Request("https://w.invalid/api/anima/lead", {
  method: "POST", headers: { "Content-Type": "application/json", Origin: ORIGIN, "CF-Connecting-IP": "1.1.1.1", ...headers },
  body: JSON.stringify(body) }), env, null, now); // no ctx: tests drive delivery explicitly
const rows = (env, t) => env.DB.raw.prepare("SELECT * FROM " + t).all();
const NOW = 1_800_000_000;

test("preflight: Anima origin allowed, foreign origin gets no allow-origin", async () => {
  const env = baseEnv();
  const ok = await handle(new Request("https://w.invalid/api/anima/lead", { method: "OPTIONS", headers: { Origin: ORIGIN } }), env, {});
  assert.equal(ok.status, 204); assert.equal(ok.headers.get("Access-Control-Allow-Origin"), ORIGIN);
  const bad = await handle(new Request("https://w.invalid/api/anima/lead", { method: "OPTIONS", headers: { Origin: "https://evil.example" } }), env, {});
  assert.equal(bad.status, 204); assert.equal(bad.headers.get("Access-Control-Allow-Origin"), null);
});

test("stores lead before answering, returns stored receipt with UUID", async () => {
  const env = baseEnv();
  const r = await post(env, good(), {}, NOW);
  assert.equal(r.status, 200);
  const b = await r.json();
  assert.equal(b.status, "accepted"); assert.match(b.lead_id, /^[0-9a-f-]{36}$/);
  assert.equal(rows(env, "leads").length, 1); assert.equal(rows(env, "outbox")[0].status, "pending");
});

test("same idempotency key returns the same lead_id and creates no duplicate", async () => {
  const env = baseEnv();
  const a = await (await post(env, good(), {}, NOW)).json();
  const b = await (await post(env, good(), {}, NOW)).json();
  assert.equal(a.lead_id, b.lead_id); assert.equal(rows(env, "leads").length, 1); assert.equal(rows(env, "outbox").length, 1);
});

test("rejects foreign origin, other tenant, no consent, no contact, bad key, oversize", async () => {
  const env = baseEnv();
  assert.equal((await post(env, good(), { Origin: "https://evil.example" }, NOW)).status, 403);
  assert.equal((await post(env, good({ client_slug: "adv" }), {}, NOW)).status, 404);
  assert.equal((await post(env, good({ consent: false }), {}, NOW)).status, 422);
  assert.equal((await post(env, good({ phone: "", email: "" }), {}, NOW)).status, 422);
  assert.equal((await post(env, good({ idempotency_key: "x" }), {}, NOW)).status, 422);
  assert.equal((await post(env, good({ details: "x".repeat(20000) }), {}, NOW)).status, 413);
  assert.equal(rows(env, "leads").length, 0);
});

test("honeypot is dropped silently without storing", async () => {
  const env = baseEnv();
  const r = await post(env, good({ company_url: "http://spam" }), {}, NOW);
  assert.equal(r.status, 200); assert.equal(rows(env, "leads").length, 0);
});

test("rate limit: 11th request from one IP in the window is 429", async () => {
  const env = baseEnv(); let last;
  for (let i = 0; i < 11; i++) last = await post(env, good({ idempotency_key: "key-rate-" + i }), {}, NOW);
  assert.equal(last.status, 429);
});

test("storage failure returns 503 (never a fake accepted)", async () => {
  const env = baseEnv(); env.DB.raw.exec("DROP TABLE leads");
  assert.equal((await post(env, good(), {}, NOW)).status, 503);
});

test("delivery not configured: lead stays pending, nothing lost", async () => {
  const env = baseEnv(); const b = await (await post(env, good(), {}, NOW)).json();
  assert.equal(await deliverOne(env, b.lead_id, NOW), "not_configured");
  assert.equal(rows(env, "outbox")[0].status, "pending");
});

test("delivery success posts Roistat form with visit id and marks delivered", async () => {
  const env = confEnv(); const b = await (await post(env, good({ ai_source: "chatgpt" }), {}, NOW)).json();
  let seen;
  const f = async (url, init) => { seen = { url, body: init.body.toString() }; return new Response("{}", { status: 200 }); };
  assert.equal(await deliverOne(env, b.lead_id, NOW, f), "delivered");
  assert.equal(seen.url, "https://roistat.invalid/leads/add");
  assert.match(seen.body, /roistat=123/); assert.match(seen.body, /chatgpt/); assert.match(seen.body, /lead_id/);
  assert.equal(rows(env, "outbox")[0].status, "delivered");
});

test("failure retries with backoff by cron sweep, then dead-letters after 8 attempts", async () => {
  const env = confEnv(); const b = await (await post(env, good(), {}, NOW)).json();
  const fail = async () => new Response("no", { status: 503 });
  assert.equal(await deliverOne(env, b.lead_id, NOW, fail), "retry");
  assert.equal(rows(env, "outbox")[0].attempts, 1);
  assert.deepEqual(await sweep(env, NOW + 10, fail), []);             // not due yet
  let t = NOW; let last;
  for (let i = 0; i < 10; i++) { t += 7 * 3600; const res = await sweep(env, t, fail); if (res.length) last = res[0]; }
  assert.equal(last, "dead"); assert.equal(rows(env, "outbox")[0].status, "dead");
  assert.equal(rows(env, "leads").length, 1);
});

test("sweep recovers after outage without any visitor and reclaims stuck rows", async () => {
  const env = confEnv(); const b = await (await post(env, good(), {}, NOW)).json();
  await deliverOne(env, b.lead_id, NOW, async () => { throw new Error("net"); });
  env.DB.raw.prepare("UPDATE outbox SET status='sending', claimed_at=? WHERE lead_id=?").run(NOW, b.lead_id);
  const res = await sweep(env, NOW + 7200, async () => new Response("{}", { status: 200 }));
  assert.deepEqual(res, ["delivered"]);
});
