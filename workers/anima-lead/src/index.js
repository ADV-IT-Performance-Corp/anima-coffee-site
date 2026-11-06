// Anima only. No provider URL or tenant selection from visitor input.
const TENANT = 'anima-coffee';
const PROVIDER = 'https://cloud.roistat.com/api/proxy/1.0/leads/add';
const ORIGINS = new Set(['https://aeo.animacoffee.com.ua','https://animacoffee.com.ua']);
// Accept existing browser outbox keys verbatim; never rewrite a pending key.
const IDEMPOTENCY_KEY = /^(?:anima_)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const enc = new TextEncoder();
const dec = new TextDecoder();
const sevenDays = 7 * 86400000;
const hex = b => Array.from(new Uint8Array(b), x => x.toString(16).padStart(2, '0')).join('');
const unhex = s => Uint8Array.from(s.match(/../g), x => parseInt(x, 16));
async function key(env) {
  if (!/^[0-9a-f]{64}$/i.test(env.PAYLOAD_KEY || '')) throw new Error('configuration');
  return crypto.subtle.importKey('raw', unhex(env.PAYLOAD_KEY), 'AES-GCM', false, ['encrypt','decrypt']);
}
async function seal(data, id, env) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const bytes = await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:enc.encode(TENANT + ':' + id)}, await key(env), enc.encode(JSON.stringify(data)));
  return hex(iv) + ':' + hex(bytes);
}
async function open(payload, id, env) {
  const [iv, bytes] = payload.split(':');
  return JSON.parse(dec.decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:unhex(iv),additionalData:enc.encode(TENANT + ':' + id)},await key(env),unhex(bytes))));
}
export function validate(raw) {
  if (!raw || raw.company_url || raw.client_slug !== TENANT || raw.consent !== true || !IDEMPOTENCY_KEY.test(raw.idempotency_key || '')) throw new Error('invalid');
  const data = {client_slug:TENANT,consent:true};
  const limits = {name:160,business:240,city:120,machines:80,email:254,phone:40,details:2000,page_slug:300,referrer:500,roistat_visit:32,utm_source:200,utm_medium:200,utm_campaign:200,utm_term:200,utm_content:200,gclid:200,lead_source:20,ai_source:20};
  for (const [field, limit] of Object.entries(limits)) {
    const value = raw[field] ?? '';
    if (typeof value !== 'string' || value.length > limit || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)) throw new Error('invalid');
    data[field] = value.trim();
  }
  if (data.lead_source && !/^(form|webmcp|chatkit)$/.test(data.lead_source)) throw new Error('invalid');
  if (data.ai_source && !/^[a-z0-9-]{1,20}$/.test(data.ai_source)) throw new Error('invalid');
  if (!data.email && !data.phone) throw new Error('invalid');
  if (data.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) throw new Error('invalid');
  if (data.phone && !/^\+?[\d ()-]{7,40}$/.test(data.phone)) throw new Error('invalid');
  if (data.roistat_visit && !/^\d{1,32}$/.test(data.roistat_visit)) throw new Error('invalid');
  if (data.page_slug && (!data.page_slug.startsWith('/') || /[?#]/.test(data.page_slug))) throw new Error('invalid');
  if (data.referrer) {
    try { const u = new URL(data.referrer); data.referrer = /^https?:$/.test(u.protocol) ? u.origin + u.pathname : ''; }
    catch { data.referrer = ''; }
  }
  return data;
}
function json(body, status, origin) {
  return new Response(JSON.stringify(body), {status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...(origin ? {'Access-Control-Allow-Origin':origin,'Vary':'Origin'} : {})}});
}
export async function intake(request, env, now = Date.now()) {
  const origin = request.headers.get('Origin');
  if (!ORIGINS.has(origin)) return json({error:'origin'},403);
  if (request.method === 'OPTIONS') return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'POST','Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'600','Vary':'Origin'}});
  if (request.method !== 'POST') return json({error:'method'},405,origin);
  if (!(request.headers.get('Content-Type') || '').startsWith('application/json')) return json({error:'content_type'},415,origin);
  const ip = request.headers.get('CF-Connecting-IP');
  if (!ip || !env.INTAKE_LIMITER) return json({error:'unavailable'},503,origin);
  // Ephemeral keyed identifier only; never store/log the IP or limiter key.
  const limiterKey = await crypto.subtle.importKey('raw', unhex(env.PAYLOAD_KEY || ''), {name:'HMAC',hash:'SHA-256'}, false, ['sign']);
  const rateId = hex(await crypto.subtle.sign('HMAC',limiterKey,enc.encode('anima-rate:' + ip)));
  if (!(await env.INTAKE_LIMITER.limit({key:rateId})).success) return json({error:'rate_limited'},429,origin);

  // Bound streamed bodies, including requests without Content-Length.
  let bytes = 0, chunks = [], reader = request.body?.getReader();
  if (!reader) return json({error:'invalid'},400,origin);
  for (;;) { const part = await reader.read(); if (part.done) break; bytes += part.value.length;
    if (bytes > 12000) { await reader.cancel(); return json({error:'too_large'},413,origin); } chunks.push(part.value); }
  let raw, data;
  try { const joined = new Uint8Array(bytes); let i = 0; for (const chunk of chunks) {joined.set(chunk,i);i += chunk.length;}
    raw = JSON.parse(dec.decode(joined)); data = validate(raw); }
  catch {return json({error:'invalid'},400,origin);}
  const fingerprintKey = await crypto.subtle.importKey('raw', unhex(env.PAYLOAD_KEY || ''), {name:'HMAC',hash:'SHA-256'}, false, ['sign']);
  const fp = hex(await crypto.subtle.sign('HMAC', fingerprintKey, enc.encode(JSON.stringify(data))));
  const id = crypto.randomUUID();
  const payload = await seal(data,id,env);
  // Quota cap and idempotency are checked in the same SQLite write statement.
  // Existing keys still receive their receipt when capacity is reached.
  await env.DB.prepare(`INSERT OR IGNORE INTO leads(tenant,idem,id,fingerprint,payload,created,expires,next_attempt)
    SELECT ?,?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM leads WHERE created >= ?) < 500`).bind(TENANT,raw.idempotency_key,id,fp,payload,now,now+sevenDays,now,now-86400000).run();
  const saved = await env.DB.prepare('SELECT id,fingerprint,state FROM leads WHERE tenant=? AND idem=?').bind(TENANT,raw.idempotency_key).first();
  if (!saved) return json({error:'capacity'},503,origin);
  if (saved.fingerprint !== fp) return json({error:'key_conflict'},409,origin);
  if (saved.state === 'expired') return json({error:'expired'},410,origin);
  return json({status:'accepted',lead_id:saved.id,receipt:'stored'},200,origin);
}
export function providerForm(data, id, integrationKey) {
  return new URLSearchParams({key:integrationKey,roistat:data.roistat_visit || 'nocookie',
    title:'Website enquiry [' + id + ']',name:data.name,phone:data.phone,email:data.email,
    comment:JSON.stringify({reference:id,lead_source:data.lead_source,ai_source:data.ai_source,business:data.business,city:data.city,machines:data.machines,details:data.details,page:data.page_slug,referrer:data.referrer,utm_source:data.utm_source,utm_medium:data.utm_medium,utm_campaign:data.utm_campaign,utm_term:data.utm_term,utm_content:data.utm_content,gclid:data.gclid}),
    sync:'1',is_need_callback:'0'});
}
// This conservative parser requires fixture verification against an authorized,
// redacted provider response before enabling delivery. HTTP 200 alone is never success.
export function parseReceipt(body) {
  const data = body?.data;
  const id = value => /^(?:[1-9]\d*)$/.test(String(value ?? '')) ? String(value) : null;
  if (body?.status !== 'success' || !id(data?.id)) return {state:'unknown',proxy:null,kommo:null};
  return {state:id(data.order_id) ? 'kommo_confirmed' : 'roistat_accepted',proxy:id(data.id),kommo:id(data.order_id)};
}
export async function sweep(env, transport = fetch, now = Date.now()) {
  if (env.TENANT !== TENANT) throw new Error('tenant');
  // Retention expiry: remove PII; retain opaque key tombstones against replay.
  await env.DB.prepare("UPDATE leads SET payload=NULL,state='expired' WHERE expires<=? AND state NOT IN ('expired','sending')").bind(now).run();
  // A terminated worker might have committed remotely: never automatically resend.
  await env.DB.prepare("UPDATE leads SET state='unknown' WHERE state='sending' AND next_attempt<=?").bind(now).run();
  if (env.DELIVERY_ENABLED !== 'true' || !env.ROISTAT_INTEGRATION_KEY || env.ROUTING_VERIFIED !== 'true') return;
  await key(env);
  const due = await env.DB.prepare("SELECT id FROM leads WHERE tenant=? AND state='queued' AND next_attempt<=? AND expires>? ORDER BY next_attempt LIMIT 3").bind(TENANT,now,now).all();
  for (const candidate of due.results) {
    const lead = await env.DB.prepare("UPDATE leads SET state='sending',attempts=attempts+1,next_attempt=? WHERE id=? AND state='queued' RETURNING *").bind(now+120000,candidate.id).first();
    if (!lead) continue;
    let receipt = {state:'unknown',proxy:null,kommo:null};
    try {
      const data = await open(lead.payload,lead.id,env);
      const response = await transport(PROVIDER + '?' + providerForm(data,lead.id,env.ROISTAT_INTEGRATION_KEY).toString(),{method:'GET',redirect:'manual',signal:AbortSignal.timeout(15000)});
      if (response.status === 200) receipt = parseReceipt(await response.json());
    } catch { /* No raw errors/bodies/credentials in logs. Outcome may be ambiguous. */ }
    await env.DB.prepare("UPDATE leads SET state=?,proxy_id=?,kommo_id=? WHERE id=? AND state='sending'").bind(receipt.state,receipt.proxy,receipt.kommo,lead.id).run();
  }
}
export default {
  async fetch(request,env) {
    if (env.TENANT !== TENANT) return json({error:'configuration'},503);
    const url = new URL(request.url);
    if (url.pathname === '/health' && request.method === 'GET') return json({service:'anima-reserve',delivery_enabled:env.DELIVERY_ENABLED === 'true'},200);
    if (url.pathname !== '/api/anima/lead' || url.search) return json({error:'not_found'},404);
    try { return await intake(request,env); } catch { return json({error:'unavailable'},503,ORIGINS.has(request.headers.get('Origin')) ? request.headers.get('Origin') : null); }
  },
  async scheduled(_event,env) { await sweep(env); }
};
