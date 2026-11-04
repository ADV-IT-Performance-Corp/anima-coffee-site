// Delivery to Roistat (which creates the lead in Anima's Kommo). A 2xx is TRANSPORT
// acceptance by Roistat, not proof a human saw it in Kommo.
const MAX_ATTEMPTS = 8;
// Documented Roistat "proxylead" endpoint (help-en.roistat.com/integrations/additional_settings/proxylead/).
// The page lists only cloud.roistat.com (no EU host); override with ROISTAT_LEAD_URL if the project needs it.
const DEFAULT_URL = "https://cloud.roistat.com/api/proxy/1.0/leads/add";
const cut = (v, n) => String(v || "").slice(0, n);
const backoffSec = (n) => Math.min(6 * 3600, 60 * 2 ** n);

export function roistatRequest(env, lead) {
  const p = lead.payload;
  const comment = [
    p.business && "Бізнес: " + p.business, p.city && "Місто: " + p.city,
    p.machines && "Обладнання: " + p.machines, p.details && "Деталі: " + p.details,
    "Сторінка: " + (p.page_slug || "-"), "Джерело: " + (p.lead_source || "form"),
    p.ai_source && "AI-джерело: " + p.ai_source, "lead_id: " + lead.lead_id,
  ].filter(Boolean).join("\n");
  // `key` is the integration key from the Roistat CRM-integration settings (not a personal API key).
  const q = new URLSearchParams({
    roistat: p.roistat_visit || "nocookie", key: env.ROISTAT_INTEGRATION_KEY,
    title: cut("Заявка з сайту (" + (p.lead_source || "form") + ")", 1024),
    name: cut(p.name, 1024), phone: cut(p.phone, 1024), email: cut(p.email, 1024),
    comment: cut(comment, 4096), sync: "1", "fields[charset]": "UTF-8",
  });
  // Documented as a query string (GET); sync=1 makes the answer carry an error or the new lead id.
  return { url: (env.ROISTAT_LEAD_URL || DEFAULT_URL) + "?" + q.toString(), init: { method: "GET", redirect: "error" } };
}

export async function deliverOne(env, leadId, now = Math.floor(Date.now() / 1000), fetchFn = fetch) {
  if (!env.ROISTAT_INTEGRATION_KEY || (env.ROISTAT_LEAD_URL && !/^https:\/\//.test(env.ROISTAT_LEAD_URL)))
    return "not_configured"; // stays pending; stored data is not lost
  const claim = await env.DB.prepare(
    "UPDATE outbox SET status='sending', claimed_at=? WHERE lead_id=? AND status='pending' AND next_attempt_at<=?"
  ).bind(now, leadId, now).run();
  if (!claim.meta || claim.meta.changes !== 1) return "skipped";
  const row = await env.DB.prepare("SELECT lead_id, payload, (SELECT attempts FROM outbox o WHERE o.lead_id=leads.lead_id) AS attempts FROM leads WHERE lead_id=?").bind(leadId).first();
  const lead = { lead_id: row.lead_id, payload: JSON.parse(row.payload) };
  try {
    const { url, init } = roistatRequest(env, lead);
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 10000);
    const r = await fetchFn(url, { ...init, signal: ctl.signal }).finally(() => clearTimeout(t));
    const text = await r.text().catch(() => "");
    if (r.status >= 200 && r.status < 300 && !/error/i.test(text)) {
      await env.DB.prepare("UPDATE outbox SET status='delivered', delivered_at=?, last_error=NULL WHERE lead_id=?").bind(now, leadId).run();
      return "delivered";
    }
    throw new Error(r.status >= 200 && r.status < 300 ? "roistat_error" : "http_" + r.status);
  } catch (e) {
    const attempts = (row.attempts || 0) + 1;
    const dead = attempts >= MAX_ATTEMPTS;
    await env.DB.prepare("UPDATE outbox SET status=?, attempts=?, next_attempt_at=?, claimed_at=NULL, last_error=? WHERE lead_id=?")
      .bind(dead ? "dead" : "pending", attempts, now + backoffSec(attempts), String(e.message || e).slice(0, 120), leadId).run();
    return dead ? "dead" : "retry";
  }
}

export async function sweep(env, now = Math.floor(Date.now() / 1000), fetchFn = fetch) {
  // Reclaim rows stuck in 'sending' (worker killed mid-request).
  await env.DB.prepare("UPDATE outbox SET status='pending' WHERE status='sending' AND claimed_at<?").bind(now - 300).run();
  const due = await env.DB.prepare("SELECT lead_id FROM outbox WHERE status='pending' AND next_attempt_at<=? ORDER BY next_attempt_at LIMIT 20").bind(now).all();
  const out = [];
  for (const r of due.results || []) out.push(await deliverOne(env, r.lead_id, now, fetchFn));
  return out;
}
