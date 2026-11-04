// Delivery to Roistat (which creates the lead in Anima's Kommo). A 2xx is TRANSPORT
// acceptance by Roistat, not proof a human saw it in Kommo.
const MAX_ATTEMPTS = 8;
const backoffSec = (n) => Math.min(6 * 3600, 60 * 2 ** n);

export function roistatRequest(env, lead) {
  const p = lead.payload;
  const comment = [
    p.business && "Бізнес: " + p.business, p.city && "Місто: " + p.city,
    p.machines && "Обладнання: " + p.machines, p.details && "Деталі: " + p.details,
    "Сторінка: " + (p.page_slug || "-"), "Джерело: " + (p.lead_source || "form"),
    p.ai_source && "AI-джерело: " + p.ai_source, "lead_id: " + lead.lead_id,
  ].filter(Boolean).join("\n");
  const form = new URLSearchParams({
    key: env.ROISTAT_API_KEY, title: "Заявка з сайту (" + (p.lead_source || "form") + ")",
    name: p.name, phone: p.phone, email: p.email, comment,
    roistat: p.roistat_visit || "",
  });
  for (const k of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid"])
    if (p[k]) form.set(k, p[k]);
  return { url: env.ROISTAT_LEAD_URL, init: { method: "POST", body: form, redirect: "error" } };
}

export async function deliverOne(env, leadId, now = Math.floor(Date.now() / 1000), fetchFn = fetch) {
  if (!env.ROISTAT_API_KEY || !env.ROISTAT_LEAD_URL || !/^https:\/\//.test(env.ROISTAT_LEAD_URL))
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
    if (r.status >= 200 && r.status < 300) {
      await env.DB.prepare("UPDATE outbox SET status='delivered', delivered_at=?, last_error=NULL WHERE lead_id=?").bind(now, leadId).run();
      return "delivered";
    }
    throw new Error("http_" + r.status);
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
