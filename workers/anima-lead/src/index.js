import { validate } from "./validate.js";
import { deliverOne, sweep } from "./deliver.js";

const MAX_BODY = 16 * 1024;
const RATE_LIMIT = 10;          // POSTs per IP per 10 minutes
const RATE_WINDOW = 600;

const allowed = (env) => new Set((env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean));
const json = (obj, status, extra = {}) => new Response(JSON.stringify(obj), {
  status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...extra } });
function cors(req, env) {
  const o = req.headers.get("Origin");
  return o && allowed(env).has(o) ? { "Access-Control-Allow-Origin": o, "Vary": "Origin" } : { "Vary": "Origin" };
}
async function ipBucket(req, env) {
  const ip = req.headers.get("CF-Connecting-IP") || "unknown";
  const data = new TextEncoder().encode((env.IP_SALT || "anima") + "|" + ip);
  const h = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(h)].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function handle(req, env, ctx, now = Math.floor(Date.now() / 1000)) {
  const url = new URL(req.url);
  if (url.pathname === "/health") return json({ ok: true }, 200);
  if (url.pathname !== "/api/anima/lead") return json({ error: "not_found" }, 404);
  const c = cors(req, env);
  if (req.method === "OPTIONS") {
    const ok = !!c["Access-Control-Allow-Origin"];
    return new Response(null, { status: 204, headers: ok ? { ...c, "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600" } : c });
  }
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405, c);
  const origin = req.headers.get("Origin");
  if (origin && !allowed(env).has(origin)) return json({ error: "origin_not_allowed" }, 403, c);
  const len = Number(req.headers.get("Content-Length") || 0);
  if (len > MAX_BODY) return json({ error: "too_large" }, 413, c);
  const text = await req.text();
  if (text.length > MAX_BODY) return json({ error: "too_large" }, 413, c);
  let body; try { body = JSON.parse(text); } catch { return json({ error: "bad_json" }, 400, c); }
  const v = validate(body);
  if (v.honeypot) return json({ status: "accepted", lead_id: crypto.randomUUID() }, 200, c); // drop silently
  if (v.error) return json({ error: v.error }, v.status || 422, c);

  try {
    const bucket = await ipBucket(req, env);
    const win = Math.floor(now / RATE_WINDOW);
    await env.DB.prepare("INSERT INTO rate(bucket, window, n) VALUES(?,?,1) ON CONFLICT(bucket, window) DO UPDATE SET n=n+1").bind(bucket, win).run();
    const r = await env.DB.prepare("SELECT n FROM rate WHERE bucket=? AND window=?").bind(bucket, win).first();
    if (r && r.n > RATE_LIMIT) return json({ error: "rate_limited" }, 429, { ...c, "Retry-After": "600" });

    const leadId = crypto.randomUUID();
    const p = v.p; delete p.company_url;
    await env.DB.batch([
      env.DB.prepare("INSERT INTO leads(lead_id, idempotency_key, created_at, payload) VALUES(?,?,?,?) ON CONFLICT(idempotency_key) DO NOTHING")
        .bind(leadId, p.idempotency_key, now, JSON.stringify(p)),
      env.DB.prepare("INSERT INTO outbox(lead_id, next_attempt_at) SELECT lead_id, ? FROM leads WHERE lead_id=? ON CONFLICT(lead_id) DO NOTHING").bind(now, leadId),
    ]);
    const stored = await env.DB.prepare("SELECT lead_id FROM leads WHERE idempotency_key=?").bind(p.idempotency_key).first();
    if (!stored) return json({ error: "storage_unavailable" }, 503, c);
    if (stored.lead_id === leadId && ctx && ctx.waitUntil) ctx.waitUntil(deliverOne(env, leadId, now));
    return json({ status: "accepted", lead_id: stored.lead_id }, 200, c); // STORED receipt
  } catch {
    return json({ error: "storage_unavailable" }, 503, c);
  }
}

export default {
  fetch: (req, env, ctx) => handle(req, env, ctx),
  scheduled: (_evt, env, ctx) => ctx.waitUntil(sweep(env)),
};
