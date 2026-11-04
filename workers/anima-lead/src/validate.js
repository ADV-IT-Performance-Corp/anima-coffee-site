// Mirrors the field rules of ADV-Strategy-Core anima_lead.py (AnimaLeadIn), no secrets.
const MAX = { name: 200, business: 200, city: 200, machines: 200, email: 255, phone: 64,
  details: 4000, page_slug: 200, referrer: 500, utm_source: 200, utm_medium: 200,
  utm_campaign: 200, utm_term: 200, utm_content: 200, gclid: 200, company_url: 500,
  roistat_visit: 64, lead_source: 20, ai_source: 20 };
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const KEY_RE = /^[A-Za-z0-9._:-]{8,128}$/;

export function validate(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return { error: "bad_body" };
  const p = {};
  for (const [k, max] of Object.entries(MAX)) {
    const v = body[k] == null ? "" : body[k];
    if (typeof v !== "string") return { error: "bad_field:" + k };
    if (v.length > max) return { error: "too_long:" + k };
    p[k] = v.trim();
  }
  if (body.client_slug !== undefined && body.client_slug !== "anima-coffee") return { error: "unknown_tenant", status: 404 };
  if (typeof body.idempotency_key !== "string" || !KEY_RE.test(body.idempotency_key)) return { error: "bad_idempotency_key" };
  p.idempotency_key = body.idempotency_key;
  p.consent = body.consent === true;
  if (p.lead_source && !/^(form|webmcp|chatkit)$/.test(p.lead_source)) p.lead_source = "";
  if (p.ai_source && !/^[a-z0-9-]{1,20}$/.test(p.ai_source)) p.ai_source = "";
  if (p.roistat_visit && !/^[A-Za-z0-9_-]{1,64}$/.test(p.roistat_visit)) p.roistat_visit = "";
  if (p.company_url) return { honeypot: true, p };
  const emailOk = EMAIL_RE.test(p.email);
  const digits = (p.phone.match(/\d/g) || []).length;
  if (!emailOk && digits < 7) return { error: "contact_required" };
  if (!p.consent) return { error: "consent_required" };
  return { p };
}
