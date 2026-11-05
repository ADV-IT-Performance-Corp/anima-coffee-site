#!/usr/bin/env node
/* Lead attribution check (2026-11-02): AI-referrer detection + Roistat fields.
 * Loads the LOCAL worktree only, aborts every Roistat/GTM/Metrica request,
 * stubs window.roistatGoal.reach and never creates a real lead.
 * Usage: node webmcp/run_attribution_check.js <base_url>
 */
const { chromium } = require(process.env.PLAYWRIGHT_REQUIRE || "playwright");
const BASE = process.argv[2] || "http://127.0.0.1:8843";
let fail = 0;
function check(n, ok, d) { console.log((ok ? "PASS " : "FAIL ") + n + (ok ? "" : " :: " + d)); if (!ok) fail++; }

async function run(browser, url, referer, prefillWebmcp) {
  const ctx = await browser.newContext();
  await ctx.route(/roistat\.com|googletagmanager|mc\.yandex|google-analytics/, (r) => r.abort());
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    window.__calls = [];
    Object.defineProperty(window, "roistatGoal", { configurable: true, get() { return { reach: (p) => window.__calls.push(p) }; } });
  });
  await page.goto(url, { referer: referer || undefined, waitUntil: "domcontentloaded" });
  await page.waitForTimeout(300);
  if (prefillWebmcp) await page.evaluate(() => { const s = JSON.parse(sessionStorage.getItem("anima_utm_v1") || "{}"); s.utm_source = "ai-agent"; s.utm_medium = "webmcp"; sessionStorage.setItem("anima_utm_v1", JSON.stringify(s)); });
  await page.fill('#leadForm input[name="name"]', "Attribution Test");
  await page.fill('#leadForm input[name="business"]', "Co");
  await page.fill('#leadForm input[name="city"]', "Kyiv");
  await page.fill('#leadForm input[name="contact"]', "attr@example.com");
  await page.fill('#leadForm textarea[name="message"]', "Office");
  await page.click('#leadForm button[type="submit"]');
  await page.waitForTimeout(300);
  const out = await page.evaluate(() => ({ calls: window.__calls, dl: window.dataLayer.filter((e) => e && (e.event === "lead_accepted" || e.event === "ai_referral_detected")) }));
  await ctx.close();
  return out;
}

async function intake(browser, url, referer, how) {
  const ctx = await browser.newContext();
  await ctx.route(/roistat\.com|googletagmanager|mc\.yandex|google-analytics/, (r) => r.abort());
  const bodies = [];
  await ctx.route("**/api/anima/lead", (r) => { bodies.push(r.request().postDataJSON()); r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", lead_id: "11111111-1111-4111-8111-111111111111" }) }); });
  const page = await ctx.newPage();
  await page.goto(url, { referer: referer || undefined, waitUntil: "domcontentloaded" });
  await page.evaluate((e) => document.querySelector("form.lead-form").setAttribute("data-endpoint", e), BASE + "/api/anima/lead");
  await page.waitForTimeout(200);
  if (how === "chat") {
    await page.evaluate(() => { const d = window.animaLead.collectBase(); Object.assign(d, { name: "Synthetic", contact: "probe@example.invalid", consent: true }); return window.animaLead.submitChat(d); });
  } else {
    for (const [n, v] of [["name", "Synthetic"], ["business", "Co"], ["city", "Kyiv"], ["contact", "probe@example.invalid"]]) await page.fill('#leadForm input[name="' + n + '"]', v);
    if (how === "agent") {
      await page.evaluate(() => new Promise((res) => { const e = new Event("submit", { cancelable: true }); e.agentInvoked = true; e.respondWith = (p) => p.then(res); document.querySelector("#leadForm").dispatchEvent(e); }));
    } else await page.click('#leadForm button[type="submit"]');
  }
  await page.waitForTimeout(300);
  await ctx.close();
  return bodies[0] || {};
}

(async () => {
  const browser = await chromium.launch();
  let r = await run(browser, BASE + "/?utm_source=chatgpt.com", null, false);
  let f = (r.calls[0] || {}).fields || {};
  check("utm_source=chatgpt.com -> ai_source chatgpt in Roistat fields", f.ai_source === "chatgpt" && f.utm_source === "chatgpt.com" && f.lead_source === "form", JSON.stringify(f));
  check("comment carries attribution line", /\[lead_source=form; ai_source=chatgpt; utm_source=chatgpt\.com/.test((r.calls[0] || {}).text || ""), (r.calls[0] || {}).text);
  check("leadName tagged with AI source", /\[AI: chatgpt\]/.test((r.calls[0] || {}).leadName || ""), (r.calls[0] || {}).leadName);
  const acc = r.dl.find((e) => e.event === "lead_accepted") || {};
  check("lead_accepted carries lead_source+ai_source", acc.lead_source === "form" && acc.ai_source === "chatgpt", JSON.stringify(acc));
  check("ai_referral_detected pushed once", r.dl.filter((e) => e.event === "ai_referral_detected").length === 1, JSON.stringify(r.dl));

  r = await run(browser, BASE + "/", "https://www.perplexity.ai/search?q=x", false);
  f = (r.calls[0] || {}).fields || {};
  check("perplexity.ai referrer -> ai_source perplexity", f.ai_source === "perplexity" && /perplexity\.ai/.test(f.referrer), JSON.stringify(f));

  r = await run(browser, BASE + "/", "https://www.google.com/", false);
  f = (r.calls[0] || {}).fields || {};
  check("plain google referrer -> no ai_source", f.ai_source === "" && f.lead_source === "form", JSON.stringify(f));

  r = await run(browser, BASE + "/", "https://gemini.google.com/", true);
  f = (r.calls[0] || {}).fields || {};
  check("WebMCP-tagged visit -> lead_source webmcp, ai_source gemini", f.lead_source === "webmcp" && f.ai_source === "gemini" && f.lead_origin === "human", JSON.stringify(f));

  r = await run(browser, BASE + "/?utm_source=google&utm_medium=cpc&gclid=abc", "https://chatgpt.com/", false);
  f = (r.calls[0] || {}).fields || {};
  check("paid click keeps its utm/gclid", f.utm_source === "google" && f.gclid === "abc", JSON.stringify(f));
  let b = await intake(browser, BASE + "/", "https://chatgpt.com/", "agent");
  check("intake: agent submit -> lead_source webmcp, ai_source chatgpt", b.lead_source === "webmcp" && b.ai_source === "chatgpt", JSON.stringify(b));
  b = await intake(browser, BASE + "/?utm_source=perplexity", null, "chat");
  check("intake: chat -> lead_source chatkit, ai_source perplexity", b.lead_source === "chatkit" && b.ai_source === "perplexity", JSON.stringify(b));
  b = await intake(browser, BASE + "/", "https://www.google.com/", "human");
  check("intake: plain human -> form, no ai_source", b.lead_source === "form" && b.ai_source === "", JSON.stringify(b));
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
