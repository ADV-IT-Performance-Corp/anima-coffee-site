#!/usr/bin/env node
/* D7 headless check — WebMCP wiring against a REAL rendered page.
 *
 * Serves the worktree over plain HTTP (python http.server), loads index.html
 * in headless Chromium, injects the upstream WebMCP polyfill (webmachine
 * learning/webmcp-tools demos/shared/webmcp-polyfill.js, vendored to
 * /tmp for this run — TEST HARNESS ONLY, never shipped in assets/), then:
 *
 *   1. executeTool('get_anima_service_info', ...) for a published fact and
 *      an explicitly-unpublished topic -> asserts published:true/false.
 *   2. executeTool('request_coffee_service_assessment', {...}) as an agent,
 *      with data-endpoint empty -> asserts status "not_connected" with
 *      phone/email/telegram, and asserts NO network request was made and
 *      no lead_accepted dataLayer push happened.
 *   3. A plain human form submit (no agent flag) with data-endpoint empty
 *      -> asserts the fallback contact block is shown (same code path as
 *      before this change, byte-for-byte).
 *   4. Roistat delivery (W2, 2026-09-14): with data-endpoint still empty and
 *      a stubbed window.roistatGoal.reach installed, a human submit fires
 *      exactly one reach() call with the mapped fields and no POST, an
 *      agent submit gets status "accepted" plus one reach() call with
 *      lead_origin "agent", and a "ТЕСТ"/"TEST" marker in the name prefixes
 *      leadName with "ТЕСТ — ". A separate case sets data-endpoint and
 *      asserts ONLY the POST path runs (no reach() call at all).
 *
 * Every page/context in this file blocks requests to cloud.roistat.com and
 * cloud-eu.roistat.com (route abort) — assets/analytics.js now carries a
 * live ROISTAT_PROJECT_ID, so this is the only thing standing between the
 * harness and calling the real counter. Never remove this blocking.
 *
 * Never points at the live site; this loads the local worktree only, so no
 * real lead can be created.
 *
 * Usage: node webmcp/run_headless_check.js <base_url> <polyfill_path>
 */
const path = require("path");
const { chromium } = require(process.env.PLAYWRIGHT_REQUIRE || "playwright");

const BASE_URL = process.argv[2] || "http://127.0.0.1:8843";
const POLYFILL_PATH = process.argv[3] || "/tmp/webmcp-test/webmcp-polyfill.js";
const fs = require("fs");
const POLYFILL_SRC = fs.readFileSync(POLYFILL_PATH, "utf8");

let failures = 0;
function check(label, cond, detail) {
  if (cond) {
    console.log(`PASS ${label}`);
  } else {
    failures++;
    console.log(`FAIL ${label}${detail ? " — " + detail : ""}`);
  }
}

// Never let a test load the real Roistat counter or reach cloud(-eu).roistat.com.
async function blockRoistat(pg) {
  await pg.route(/roistat\.com/, (route) => route.abort());
}

// Stub window.roistatGoal.reach BEFORE navigation, same as the polyfill init
// script, so assets/lead.js's readiness check (`window.roistatGoal &&
// typeof window.roistatGoal.reach === "function"`) sees it on first submit.
const ROISTAT_STUB_SRC = `(function () {
  window.__roistatCalls = [];
  window.roistatGoal = {
    reach: function (payload) { window.__roistatCalls.push(payload); }
  };
})();`;

// assets/analytics.js carries a live ROISTAT_PROJECT_ID, so on any page
// that doesn't stub window.roistatGoal, assets/lead.js's (2b) wait path
// (fast-follow, 2026-09-14) now polls for up to ~4s before falling back —
// window.roistatGoal never appears here because blockRoistat() aborts the
// real counter request. Shrink that wait for pages whose tests want the
// pre-existing "falls straight to fallback" behaviour, so the suite
// doesn't spend 4 real seconds per such page.
const SHORT_WAIT_SRC = `window.__ROISTAT_TEST_WAIT_MS = 250;`;

// Honest-delivery v2 (2026-10-31): the one-tap controls are <button>s, not
// <a>s (no visitor data may ever land in a real href attribute an analytics
// click-listener could read). This hook captures {channel, url} on click
// without navigating/opening a real client, following the
// window.__ROISTAT_TEST_WAIT_MS convention.
const DRAFT_CAPTURE_SRC = `window.__capturedDraft = null; window.__LEAD_DRAFT_CAPTURE = function (channel, url) { window.__capturedDraft = { channel: channel, url: url }; };`;
const T_VIA_EMAIL = "Email";
const T_VIA_TELEGRAM = "Telegram";
async function clickOneTapButton(pg, label) {
  await pg.getByRole("button", { name: label }).click();
  return pg.evaluate(() => window.__capturedDraft);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await blockRoistat(page);
  await page.addInitScript({ content: SHORT_WAIT_SRC });

  // Third-party analytics beacons (GA4/GTM/Metrica, all live via real IDs
  // in assets/analytics.js) fire on page load and form interaction
  // regardless of the lead flow — only a POST to something other than one
  // of those hosts would mean lead.js fetched a (non-existent) endpoint.
  var ANALYTICS_HOSTS = ["google-analytics.com", "googletagmanager.com", "mc.yandex.", "yandex.ru"];
  var networkRequests = [];
  page.on("request", (req) => {
    if (req.method() !== "POST") return;
    if (ANALYTICS_HOSTS.some((h) => req.url().includes(h))) return;
    networkRequests.push(req.url());
  });

  // Install the polyfill BEFORE navigation so assets/webmcp.js's own
  // `'modelContext' in document` feature-detection (which runs at page
  // load, same as it would against a native implementation) sees it and
  // registers the imperative tool.
  await page.addInitScript({ content: POLYFILL_SRC });
  await page.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });

  const hasModelContext = await page.evaluate(() => "modelContext" in document);
  check("polyfill installs document.modelContext", hasModelContext);

  const toolNames = await page.evaluate(async () => {
    const tools = await document.modelContext.getTools();
    return tools.map((t) => t.name);
  });
  check(
    "both tools are discoverable via getTools()",
    toolNames.includes("get_anima_service_info") && toolNames.includes("request_coffee_service_assessment"),
    JSON.stringify(toolNames)
  );

  async function callTool(name, args) {
    return page.evaluate(
      async ({ name, args }) => {
        const tools = await document.modelContext.getTools();
        const tool = tools.find((t) => t.name === name);
        if (!tool) return { __missing: true };
        return document.modelContext.executeTool(tool, args);
      },
      { name, args }
    );
  }

  // 1. Read-only tool: published fact
  const trialResult = await callTool("get_anima_service_info", {
    question: "Do you offer a free trial?",
    language: "en"
  });
  check(
    "get_anima_service_info answers the published trial fact",
    trialResult && trialResult.published === true && /14-day/i.test(trialResult.answer || ""),
    JSON.stringify(trialResult)
  );

  // 1b. Read-only tool: explicitly unpublished topic
  const brandResult = await callTool("get_anima_service_info", {
    question: "What exact machine brand and model will you install?",
    language: "en"
  });
  check(
    "get_anima_service_info refuses the unpublished machine-brand question",
    brandResult && brandResult.published === false && /not published/i.test(brandResult.answer || ""),
    JSON.stringify(brandResult)
  );

  // 1c. Codex round-1 fix: Ukrainian-language question about a published fact
  const ukCoverageResult = await callTool("get_anima_service_info", {
    question: "Ви обслуговуєте Київську область?",
    language: "uk"
  });
  check(
    "get_anima_service_info (uk question) answers the published coverage fact",
    ukCoverageResult && ukCoverageResult.published === true && /Київ/i.test(ukCoverageResult.answer || ""),
    JSON.stringify(ukCoverageResult)
  );

  // 1d. Codex round-1 fix: "breaks down" phrasing (not just "breakdown")
  const breaksDownResult = await callTool("get_anima_service_info", {
    question: "What happens if a machine breaks down over a weekend?",
    language: "en"
  });
  check(
    "get_anima_service_info matches 'breaks down' phrasing, not just 'breakdown'",
    breaksDownResult && breaksDownResult.published === true && /24 hours/i.test(breaksDownResult.answer || ""),
    JSON.stringify(breaksDownResult)
  );

  // 1e. Codex round-2 fix: a more specific ask (hours) must win over a
  // broader one (coverage area) mentioned in the same sentence.
  const hoursVsCoverageResult = await callTool("get_anima_service_info", {
    question: "What are your opening hours in Kyiv Oblast?",
    language: "en"
  });
  check(
    "get_anima_service_info resolves 'opening hours in Kyiv Oblast' to contact info, not coverage",
    hoursVsCoverageResult && hoursVsCoverageResult.published === true && /09:00|17:00/.test(hoursVsCoverageResult.answer || ""),
    JSON.stringify(hoursVsCoverageResult)
  );

  // 1f. Codex round-3 fix: "technician" appears in both the weekly-visit
  // fact and the breakdown fact — the more specific weekly-visit ask must
  // win.
  const weeklyVisitResult = await callTool("get_anima_service_info", {
    question: "Do you include a weekly technician quality visit?",
    language: "en"
  });
  check(
    "get_anima_service_info resolves the weekly-visit question to maintenance, not breakdown coverage",
    weeklyVisitResult && weeklyVisitResult.published === true && /weekly/i.test(weeklyVisitResult.answer || ""),
    JSON.stringify(weeklyVisitResult)
  );

  // 1g. Codex round-4 fix: "minimum contract length" stays unpublished,
  // but "do we have to order a minimum volume" is a distinct, published
  // fact (the site's own FAQ: no forced monthly minimum).
  const minVolumeResult = await callTool("get_anima_service_info", {
    question: "Do we have to buy a minimum amount of coffee every month?",
    language: "en"
  });
  check(
    "get_anima_service_info answers the published no-minimum-volume fact",
    minVolumeResult && minVolumeResult.published === true && /no forced minimum/i.test(minVolumeResult.answer || ""),
    JSON.stringify(minVolumeResult)
  );
  const contractLengthResult = await callTool("get_anima_service_info", {
    question: "What is the minimum contract length?",
    language: "en"
  });
  check(
    "get_anima_service_info still refuses the unpublished contract-length question",
    contractLengthResult && contractLengthResult.published === false,
    JSON.stringify(contractLengthResult)
  );

  // 1h. Codex round-4 fix: "support phone number" must resolve to contact
  // info, not the general breakdown/SLA fact.
  const supportPhoneResult = await callTool("get_anima_service_info", {
    question: "What is your support phone number?",
    language: "en"
  });
  check(
    "get_anima_service_info resolves 'support phone number' to contact info, not just the SLA",
    supportPhoneResult && supportPhoneResult.published === true && /\+38/.test(supportPhoneResult.answer || ""),
    JSON.stringify(supportPhoneResult)
  );

  // 2. Agent form submission via the declarative tool, endpoint empty.
  // toolautosubmit is deliberately OFF (D1: human confirms submit), so the
  // polyfill fills the fields and focuses the submit button but does NOT
  // click it — exactly like a real WebMCP agent flow would require a
  // (possibly synthetic, on the agent's behalf) confirm click before
  // e.respondWith() ever resolves. Start the tool call, then perform that
  // confirm click, then read back the resolved result.
  await page.evaluate(async ({ name, args }) => {
    const tools = await document.modelContext.getTools();
    const tool = tools.find((t) => t.name === name);
    window.__agentResultPromise = document.modelContext.executeTool(tool, args);
  }, {
    name: "request_coffee_service_assessment",
    args: {
      name: "Test Agent Buyer",
      business: "Test Co",
      city: "Kyiv",
      machines: "1",
      contact: "buyer@example.com",
      message: "Office, ~10 people, prefers email."
    }
  });
  await page.waitForTimeout(50);
  await page.click('#leadForm button[type="submit"]');
  const agentResult = await page.evaluate(() => window.__agentResultPromise);
  check(
    "agent form submit returns not_connected with contact facts",
    agentResult &&
      agentResult.status === "not_connected" &&
      agentResult.phone === "+38 (073) 873 01 45" &&
      agentResult.email === "animacoffeeco@gmail.com" &&
      agentResult.telegram === "https://t.me/Animavolitiva",
    JSON.stringify(agentResult)
  );
  check("agent submit with empty endpoint made no network POST", networkRequests.length === 0, JSON.stringify(networkRequests));

  const dataLayerAfterAgent = await page.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check("agent not_connected path pushed no lead_accepted event", dataLayerAfterAgent.length === 0, JSON.stringify(dataLayerAfterAgent));

  // 3. Honest-delivery (TDD case: failure with Roistat configured). Roistat
  // IS configured (live ROISTAT_PROJECT_ID) but blockRoistat() means
  // window.roistatGoal never appears, so this runs the (2b) wait path
  // (SHORT_WAIT_SRC caps it at 250ms) then times out. T.noBackend ("isn't
  // wired") would be FALSE here since a backend IS configured -- the honest
  // deliveryFailed message + one-tap email/Telegram controls must show
  // instead, the visitor's values must survive (no reset), the lead must be
  // saved to the outbox, and no lead_accepted may fire.
  await page.evaluate(() => localStorage.removeItem("anima_lead_outbox_v1"));
  await page.evaluate(DRAFT_CAPTURE_SRC);
  const SENTINEL_NAME = "Human Visitor SENTINEL_Q7x";
  await page.fill('#leadForm input[name="name"]', SENTINEL_NAME);
  await page.fill('#leadForm input[name="business"]', "Human Co");
  await page.fill('#leadForm input[name="city"]', "Kyiv");
  await page.fill('#leadForm input[name="contact"]', "human@example.com");
  await page.click('#leadForm button[type="submit"]');
  await page.waitForTimeout(400);
  const statusText = await page.textContent("#leadForm .lf-status");
  check(
    "configured+timeout: shows the honest delivery-failed message, not T.noBackend",
    /couldn't send your request automatically/i.test(statusText || "") && !/isn't wired/i.test(statusText || ""),
    JSON.stringify(statusText)
  );
  const nameFieldAfterTimeout = await page.inputValue('#leadForm input[name="name"]');
  check(
    "configured+timeout: the visitor's form values are kept, not reset",
    nameFieldAfterTimeout === SENTINEL_NAME,
    JSON.stringify(nameFieldAfterTimeout)
  );
  const statusHtmlAfterTimeout = await page.evaluate(() => document.querySelector("#leadForm .lf-status").outerHTML);
  const anchorHrefsAfterTimeout = await page.evaluate(() =>
    Array.prototype.map.call(document.querySelectorAll("#leadForm .lf-status a"), (a) => a.getAttribute("href") || "")
  );
  check(
    "configured+timeout: both one-tap controls are real <button> elements, not <a>, and the sentinel appears in neither the status HTML nor any anchor href",
    /<button[^>]*class="lf-draft-btn"[^>]*>Email<\/button>/.test(statusHtmlAfterTimeout) &&
      /<button[^>]*class="lf-draft-btn"[^>]*>Telegram<\/button>/.test(statusHtmlAfterTimeout) &&
      statusHtmlAfterTimeout.indexOf(SENTINEL_NAME) === -1 &&
      anchorHrefsAfterTimeout.every((h) => h.indexOf(SENTINEL_NAME) === -1 && h.indexOf("?") === -1),
    JSON.stringify({ anchorHrefsAfterTimeout })
  );
  const contactsAfterTimeout = await page.evaluate(() => ({
    tel: !!document.querySelector('#leadForm .lf-status a[href^="tel:"]'),
    mail: !!document.querySelector('#leadForm .lf-status a[href^="mailto:"]')
  }));
  check(
    "configured+timeout: tel and mailto contacts are present alongside both buttons",
    contactsAfterTimeout.tel && contactsAfterTimeout.mail,
    JSON.stringify(contactsAfterTimeout)
  );
  const emailDraft = await clickOneTapButton(page, T_VIA_EMAIL);
  check(
    "configured+timeout: clicking Email yields a mailto draft to the page's own contact address, via the hook",
    emailDraft && emailDraft.channel === "email" && emailDraft.url.indexOf("mailto:animacoffeeco@gmail.com") === 0,
    JSON.stringify(emailDraft)
  );
  const telegramDraft = await clickOneTapButton(page, T_VIA_TELEGRAM);
  check(
    "configured+timeout: clicking Telegram yields a correctly encoded t.me URL, within the ~1800-char bound, via the hook",
    telegramDraft && telegramDraft.channel === "telegram" &&
      telegramDraft.url.indexOf("https://t.me/Animavolitiva?text=") === 0 &&
      telegramDraft.url.length <= 1900,
    JSON.stringify(telegramDraft)
  );
  const dataLayerAfterTimeout = await page.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check("configured+timeout: no lead_accepted event was pushed", dataLayerAfterTimeout.length === 0, JSON.stringify(dataLayerAfterTimeout));
  const outboxAfterTimeout = await page.evaluate(() => JSON.parse(localStorage.getItem("anima_lead_outbox_v1") || "[]"));
  check(
    "configured+timeout: the lead was saved to the outbox for automatic re-delivery",
    Array.isArray(outboxAfterTimeout) && outboxAfterTimeout.length === 1 && outboxAfterTimeout[0].data.name === SENTINEL_NAME,
    JSON.stringify(outboxAfterTimeout)
  );
  check("human submit made no network POST either", networkRequests.length === 0, JSON.stringify(networkRequests));

  // 4. Round-4 fix: navigator.modelContext-only fallback. Some early Chrome
  // preview builds / older explainer drafts exposed the API on navigator
  // instead of Document (spec: `partial interface Document { readonly
  // attribute ModelContext modelContext; }`). A separate page/context is
  // used so this doesn't disturb the document.modelContext assertions
  // above: the polyfill installs its ModelContext instance on
  // document.modelContext as usual, then a second init script relocates
  // that SAME instance onto navigator.modelContext and deletes the
  // document property, before assets/webmcp.js's own feature-detection
  // ever runs (both scripts are addInitScript — guaranteed to run, in
  // this order, before any page script).
  const navPage = await browser.newPage();
  await blockRoistat(navPage);
  await navPage.addInitScript({ content: SHORT_WAIT_SRC });
  await navPage.addInitScript({ content: POLYFILL_SRC });
  await navPage.addInitScript({
    content: `(function () {
      var mc = document.modelContext;
      if (!mc) return;
      delete document.modelContext;
      Object.defineProperty(navigator, "modelContext", { value: mc, writable: false, configurable: true });
    })();`
  });
  await navPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });

  const navOnly = await navPage.evaluate(() => ({
    hasDocument: "modelContext" in document && !!document.modelContext,
    hasNavigator: "modelContext" in navigator && !!navigator.modelContext
  }));
  check(
    "harness fixture actually relocated modelContext to navigator-only",
    !navOnly.hasDocument && navOnly.hasNavigator,
    JSON.stringify(navOnly)
  );

  async function callToolOn(pg, obj, name, args) {
    return pg.evaluate(
      async ({ obj, name, args }) => {
        const mc = obj === "navigator" ? navigator.modelContext : document.modelContext;
        const tools = await mc.getTools();
        const tool = tools.find((t) => t.name === name);
        if (!tool) return { __missing: true };
        return mc.executeTool(tool, args);
      },
      { obj, name, args }
    );
  }

  const navToolNames = await navPage.evaluate(async () => {
    const tools = await navigator.modelContext.getTools();
    return tools.map((t) => t.name);
  });
  check(
    "navigator-only: both tools are still discoverable via getTools()",
    navToolNames.includes("get_anima_service_info") && navToolNames.includes("request_coffee_service_assessment"),
    JSON.stringify(navToolNames)
  );

  const navTrialResult = await callToolOn(navPage, "navigator", "get_anima_service_info", {
    question: "Do you offer a free trial?",
    language: "en"
  });
  check(
    "navigator-only: get_anima_service_info still answers the published trial fact",
    navTrialResult && navTrialResult.published === true && /14-day/i.test(navTrialResult.answer || ""),
    JSON.stringify(navTrialResult)
  );

  await navPage.evaluate(async ({ name, args }) => {
    const tools = await navigator.modelContext.getTools();
    const tool = tools.find((t) => t.name === name);
    window.__navAgentResultPromise = navigator.modelContext.executeTool(tool, args);
  }, {
    name: "request_coffee_service_assessment",
    args: {
      name: "Nav Fallback Buyer",
      business: "Nav Test Co",
      city: "Kyiv",
      machines: "1",
      contact: "navtest@example.com",
      message: "Office, prefers email."
    }
  });
  await navPage.waitForTimeout(50);
  await navPage.click('#leadForm button[type="submit"]');
  const navAgentResult = await navPage.evaluate(() => window.__navAgentResultPromise);
  check(
    "navigator-only: declarative form tool still registers and answers (not_connected)",
    navAgentResult &&
      navAgentResult.status === "not_connected" &&
      navAgentResult.phone === "+38 (073) 873 01 45",
    JSON.stringify(navAgentResult)
  );

  // 5. Roistat delivery (W2): stub window.roistatGoal.reach and re-navigate
  // on a fresh page so lead.js's readiness check finds it. data-endpoint
  // stays empty, so this exercises path (2) of the three-way choice.
  const roistatPage = await browser.newPage();
  await blockRoistat(roistatPage);
  await roistatPage.addInitScript({ content: POLYFILL_SRC });
  await roistatPage.addInitScript({ content: ROISTAT_STUB_SRC });
  var roistatPostRequests = [];
  roistatPage.on("request", (req) => {
    if (req.method() !== "POST") return;
    if (ANALYTICS_HOSTS.some((h) => req.url().includes(h))) return;
    roistatPostRequests.push(req.url());
  });
  await roistatPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });

  await roistatPage.fill('#leadForm input[name="name"]', "Roistat Human");
  await roistatPage.fill('#leadForm input[name="business"]', "Roistat Co");
  await roistatPage.fill('#leadForm input[name="city"]', "Kyiv");
  await roistatPage.fill('#leadForm input[name="contact"]', "roistat-human@example.com");
  await roistatPage.fill('#leadForm textarea[name="message"]', "Office, ~8 people.");
  await roistatPage.click('#leadForm button[type="submit"]');
  await roistatPage.waitForTimeout(100);

  const humanRoistatCalls = await roistatPage.evaluate(() => window.__roistatCalls);
  check(
    "human submit with Roistat ready fires exactly one reach() call",
    Array.isArray(humanRoistatCalls) && humanRoistatCalls.length === 1,
    JSON.stringify(humanRoistatCalls)
  );
  const humanReach = (humanRoistatCalls || [])[0] || {};
  check(
    "human reach() call carries the mapped fields and lead_origin human",
    humanReach.name === "Roistat Human" &&
      humanReach.email === "roistat-human@example.com" &&
      humanReach.fields &&
      humanReach.fields.company === "Roistat Co" &&
      humanReach.fields.city === "Kyiv" &&
      humanReach.fields.lead_origin === "human" &&
      !!humanReach.fields.lead_id,
    JSON.stringify(humanReach)
  );
  check("human Roistat submit makes no POST", roistatPostRequests.length === 0, JSON.stringify(roistatPostRequests));
  const humanRoistatStatus = await roistatPage.textContent("#leadForm .lf-status");
  check(
    "human Roistat submit shows the normal success message, not the fallback",
    /thank you|дякуємо/i.test(humanRoistatStatus || ""),
    JSON.stringify(humanRoistatStatus)
  );
  // 2026-10-25: the success line used to sit under the consent text, so after
  // form.reset() it landed at the viewport's bottom edge, half under the
  // sticky CTA bar, and visitors never saw it. It must sit right under the
  // submit button and end up fully visible above the sticky bar.
  await roistatPage.waitForTimeout(2000);
  const humanRoistatPlacement = await roistatPage.evaluate(() => {
    const st = document.querySelector("#leadForm .lf-status");
    const btn = document.querySelector("#leadForm .lf-submit");
    const bar = document.getElementById("sticky-cta");
    const r = st.getBoundingClientRect();
    const barTop = bar ? bar.getBoundingClientRect().top : window.innerHeight;
    return {
      afterButton: btn.nextElementSibling === st,
      ok: st.classList.contains("ok"),
      top: r.top,
      bottom: r.bottom,
      barTop: barTop
    };
  });
  check(
    "human success message sits directly under the submit button",
    humanRoistatPlacement.afterButton && humanRoistatPlacement.ok,
    JSON.stringify(humanRoistatPlacement)
  );
  check(
    "human success message is fully visible above the sticky CTA bar",
    humanRoistatPlacement.top >= 0 && humanRoistatPlacement.bottom <= humanRoistatPlacement.barTop,
    JSON.stringify(humanRoistatPlacement)
  );
  const humanRoistatDataLayer = await roistatPage.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check("human Roistat submit pushed exactly one lead_accepted event", humanRoistatDataLayer.length === 1, JSON.stringify(humanRoistatDataLayer));

  // Agent submit on the same stubbed page — reset the form's own call log
  // and dataLayer aren't reset, but the count check below only cares about
  // the delta being exactly one for the new call.
  await roistatPage.evaluate(async ({ name, args }) => {
    const tools = await document.modelContext.getTools();
    const tool = tools.find((t) => t.name === name);
    window.__agentReachPromise = document.modelContext.executeTool(tool, args);
  }, {
    name: "request_coffee_service_assessment",
    args: {
      name: "Roistat Agent Buyer",
      business: "Roistat Agent Co",
      city: "Kyiv",
      machines: "2",
      contact: "+380991234567",
      message: "Retail kiosk."
    }
  });
  await roistatPage.waitForTimeout(50);
  await roistatPage.click('#leadForm button[type="submit"]');
  const agentReachResult = await roistatPage.evaluate(() => window.__agentReachPromise);
  check(
    "agent submit with Roistat ready returns accepted with a lead_id",
    agentReachResult && agentReachResult.status === "accepted" && !!agentReachResult.leadId,
    JSON.stringify(agentReachResult)
  );
  const allRoistatCalls = await roistatPage.evaluate(() => window.__roistatCalls);
  const agentReach = (allRoistatCalls || [])[1];
  check(
    "agent submit fired exactly one additional reach() call with lead_origin agent",
    Array.isArray(allRoistatCalls) && allRoistatCalls.length === 2 && agentReach && agentReach.fields.lead_origin === "agent",
    JSON.stringify(allRoistatCalls)
  );
  check("agent Roistat submit made no POST either", roistatPostRequests.length === 0, JSON.stringify(roistatPostRequests));

  // 5b. "ТЕСТ" marker in the name prefixes leadName — fresh page + fresh stub.
  const testMarkerPage = await browser.newPage();
  await blockRoistat(testMarkerPage);
  await testMarkerPage.addInitScript({ content: POLYFILL_SRC });
  await testMarkerPage.addInitScript({ content: ROISTAT_STUB_SRC });
  await testMarkerPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await testMarkerPage.fill('#leadForm input[name="name"]', "ТЕСТ Buyer");
  await testMarkerPage.fill('#leadForm input[name="business"]', "Test Co");
  await testMarkerPage.fill('#leadForm input[name="city"]', "Kyiv");
  await testMarkerPage.fill('#leadForm input[name="contact"]', "test@example.com");
  await testMarkerPage.click('#leadForm button[type="submit"]');
  await testMarkerPage.waitForTimeout(100);
  const testMarkerCalls = await testMarkerPage.evaluate(() => window.__roistatCalls);
  const testMarkerLeadName = ((testMarkerCalls || [])[0] || {}).leadName || "";
  check(
    "'ТЕСТ' in the name prefixes leadName with 'ТЕСТ — '",
    testMarkerLeadName.indexOf("ТЕСТ — ") === 0,
    JSON.stringify(testMarkerLeadName)
  );

  // 5c. data-endpoint set -> POST path only, even with Roistat stubbed and
  // ready; roistatGoal.reach must NOT be called.
  const endpointPage = await browser.newPage();
  await blockRoistat(endpointPage);
  await endpointPage.addInitScript({ content: ROISTAT_STUB_SRC });
  await endpointPage.route("**/fake-lead-endpoint", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ lead_id: "srv_test_1" }) })
  );
  var endpointPostRequests = [];
  endpointPage.on("request", (req) => {
    if (req.method() === "POST" && req.url().includes("fake-lead-endpoint")) endpointPostRequests.push(req.url());
  });
  await endpointPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await endpointPage.evaluate(() => {
    document.getElementById("leadForm").setAttribute("data-endpoint", "/fake-lead-endpoint");
  });
  await endpointPage.fill('#leadForm input[name="name"]', "Endpoint Human");
  await endpointPage.fill('#leadForm input[name="business"]', "Endpoint Co");
  await endpointPage.fill('#leadForm input[name="city"]', "Kyiv");
  await endpointPage.fill('#leadForm input[name="contact"]', "endpoint@example.com");
  await endpointPage.click('#leadForm button[type="submit"]');
  await endpointPage.waitForTimeout(200);
  check("data-endpoint set: exactly one POST is made", endpointPostRequests.length === 1, JSON.stringify(endpointPostRequests));
  const endpointRoistatCalls = await endpointPage.evaluate(() => window.__roistatCalls || []);
  check("data-endpoint set: roistatGoal.reach is never called", endpointRoistatCalls.length === 0, JSON.stringify(endpointRoistatCalls));
  const endpointStatus = await endpointPage.textContent("#leadForm .lf-status");
  check(
    "data-endpoint set: success message shown via the POST path",
    /thank you|дякуємо/i.test(endpointStatus || ""),
    JSON.stringify(endpointStatus)
  );

  // 6. Fast-follow (2026-09-14): window.roistatGoal appears 1.5s AFTER
  // submit (a fast agent, or a human on a slow connection, racing the
  // async counter script) -> the (2b) wait path picks it up inside its
  // cap and delivers exactly once, instead of losing the lead to (3).
  const lateStubPage = await browser.newPage();
  await blockRoistat(lateStubPage);
  await lateStubPage.addInitScript({ content: `window.__roistatCalls = [];` });
  await lateStubPage.addInitScript({ content: POLYFILL_SRC });
  await lateStubPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await lateStubPage.fill('#leadForm input[name="name"]', "Late Roistat Human");
  await lateStubPage.fill('#leadForm input[name="business"]', "Late Co");
  await lateStubPage.fill('#leadForm input[name="city"]', "Kyiv");
  await lateStubPage.fill('#leadForm input[name="contact"]', "late@example.com");
  // Codex round-1 fix: schedule the delayed stub relative to the click
  // itself, not to page load — networkidle can eat an unpredictable slice
  // of any fixed pre-navigation delay, which could let roistatGoal exist
  // before submit and skip the (2b) wait path entirely without the test
  // noticing. Installing it right before the click guarantees this
  // exercises the poll, not a lucky race.
  await lateStubPage.evaluate(() => {
    setTimeout(function () {
      window.roistatGoal = { reach: function (p) { window.__roistatCalls.push(p); } };
    }, 1500);
  });
  await lateStubPage.click('#leadForm button[type="submit"]');
  // Poll past the stub's 1.5s mark with slack for the wait loop's own
  // 100ms interval.
  await lateStubPage.waitForTimeout(2200);
  const lateCalls = await lateStubPage.evaluate(() => window.__roistatCalls);
  check(
    "roistatGoal defined 1.5s after submit: exactly one reach() call, no lead lost",
    Array.isArray(lateCalls) && lateCalls.length === 1,
    JSON.stringify(lateCalls)
  );
  const lateStatus = await lateStubPage.textContent("#leadForm .lf-status");
  check(
    "roistatGoal defined 1.5s after submit: success message shown, not the fallback",
    /thank you|дякуємо/i.test(lateStatus || ""),
    JSON.stringify(lateStatus)
  );

  // 7. Fast-follow: window.roistatGoal never becomes ready (counter
  // permanently blocked) -> falls back only after the wait times out, and
  // still never claims a reach() that didn't happen.
  const neverReadyPage = await browser.newPage();
  await blockRoistat(neverReadyPage);
  await neverReadyPage.addInitScript({ content: SHORT_WAIT_SRC });
  await neverReadyPage.addInitScript({ content: POLYFILL_SRC });
  await neverReadyPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await neverReadyPage.fill('#leadForm input[name="name"]', "Never Ready Human");
  await neverReadyPage.fill('#leadForm input[name="business"]', "Never Co");
  await neverReadyPage.fill('#leadForm input[name="city"]', "Kyiv");
  await neverReadyPage.fill('#leadForm input[name="contact"]', "never@example.com");
  await neverReadyPage.click('#leadForm button[type="submit"]');
  await neverReadyPage.waitForTimeout(500);
  const neverReadyStatus = await neverReadyPage.textContent("#leadForm .lf-status");
  check(
    "roistatGoal never ready: shows the honest delivery-failed message (configured, not T.noBackend)",
    /couldn't send your request automatically/i.test(neverReadyStatus || ""),
    JSON.stringify(neverReadyStatus)
  );
  const neverReadyDataLayer = await neverReadyPage.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check("roistatGoal never ready: no lead_accepted event was pushed", neverReadyDataLayer.length === 0, JSON.stringify(neverReadyDataLayer));

  // 8. Fast-follow: two back-to-back agent submits with the SAME data must
  // produce exactly one reach() call. window.__LEAD_RESET_DELAY_MS widens
  // the deferred-reset window (normally a single macrotask) so the second
  // submit deterministically lands inside it instead of depending on real
  // event-loop timing.
  const dupPage = await browser.newPage();
  await blockRoistat(dupPage);
  await dupPage.addInitScript({ content: `window.__LEAD_RESET_DELAY_MS = 400;` });
  await dupPage.addInitScript({ content: ROISTAT_STUB_SRC });
  await dupPage.addInitScript({ content: POLYFILL_SRC });
  await dupPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });

  // Codex round-1 fix: a real Playwright click() waits for the submit
  // button to become actionable (enabled) before landing, so by the time
  // it fires the guard window has already closed and the "race" never
  // actually happens — it just becomes a normal, later, legitimate
  // submit. form.requestSubmit() (called with no submitter argument)
  // fires the same 'submit' event the polyfill and lead.js listen for,
  // without requiring any particular button to be enabled, so it lands
  // deterministically INSIDE the guarded window instead of waiting it out.
  async function agentSubmit(pg, args) {
    return pg.evaluate(async ({ name, args }) => {
      const tools = await document.modelContext.getTools();
      const tool = tools.find((t) => t.name === name);
      // executeTool()'s Promise executor attaches the form's 'submit'
      // listener synchronously, so requestSubmit() right after this call
      // (no await, no timeout) is guaranteed to be seen by it.
      const resultPromise = document.modelContext.executeTool(tool, args);
      document.getElementById("leadForm").requestSubmit();
      return resultPromise;
    }, { name: "request_coffee_service_assessment", args });
  }

  const dupArgs = {
    name: "Duplicate Guard Buyer",
    business: "Dup Co",
    city: "Kyiv",
    machines: "1",
    contact: "dup@example.com",
    message: "Same submit twice."
  };
  const dupResult1 = await agentSubmit(dupPage, dupArgs);
  check("duplicate guard: first submit accepted", dupResult1 && dupResult1.status === "accepted", JSON.stringify(dupResult1));
  // Second submit fires immediately after the first resolves — well inside
  // the widened (400ms) deferred-reset window — so the sending guard must
  // still be held: this must resolve as an in-flight error, never a
  // second "accepted".
  const dupResult2 = await agentSubmit(dupPage, dupArgs);
  check(
    "duplicate guard: second (racing) submit is rejected in-flight, not delivered",
    dupResult2 && dupResult2.status === "error",
    JSON.stringify(dupResult2)
  );
  await dupPage.waitForTimeout(500);
  const dupCalls = await dupPage.evaluate(() => window.__roistatCalls);
  check(
    "duplicate guard: exactly one reach() call total for the two racing submits",
    Array.isArray(dupCalls) && dupCalls.length === 1,
    JSON.stringify(dupCalls)
  );

  // 9. Fast-follow: a throwing Roistat counter snippet must never prevent
  // window.animaTrackLead from being defined, and must not take GA4/dataLayer
  // or Metrica down with it. Targets the exact insertBefore() call the
  // counter snippet makes (see assets/analytics.js), regardless of call
  // order relative to GTM/Metrica's own script insertions.
  const throwPage = await browser.newPage();
  await blockRoistat(throwPage);
  await throwPage.addInitScript({
    content: `(function () {
      var orig = Node.prototype.insertBefore;
      Node.prototype.insertBefore = function (newNode, refNode) {
        if (newNode && newNode.tagName === "SCRIPT" && typeof newNode.src === "string" && newNode.src.indexOf("roistat.com") !== -1) {
          throw new Error("simulated roistat snippet failure");
        }
        return orig.call(this, newNode, refNode);
      };
    })();`
  });
  await throwPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  const throwPageState = await throwPage.evaluate(() => ({
    hasAnimaTrackLead: typeof window.animaTrackLead === "function",
    hasYm: typeof window.ym === "function",
    hasDataLayer: Array.isArray(window.dataLayer)
  }));
  check(
    "throwing Roistat snippet: window.animaTrackLead is still defined",
    throwPageState.hasAnimaTrackLead,
    JSON.stringify(throwPageState)
  );
  check(
    "throwing Roistat snippet: Metrica (window.ym) is still initialized",
    throwPageState.hasYm,
    JSON.stringify(throwPageState)
  );
  const throwPageTrack = await throwPage.evaluate(() => {
    window.animaTrackLead("/test", "lead_throw_test", "human");
    return (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted" && e.lead_id === "lead_throw_test");
  });
  check(
    "throwing Roistat snippet: animaTrackLead still pushes lead_accepted to dataLayer",
    Array.isArray(throwPageTrack) && throwPageTrack.length === 1,
    JSON.stringify(throwPageTrack)
  );

  // 10. Honest-delivery (TDD case: reach() itself throws, Roistat ready
  // immediately -- no (2b) wait needed). Same honest message, kept values,
  // one-tap controls, outbox saved, no lead_accepted as the timeout case.
  const throwsReachPage = await browser.newPage();
  await blockRoistat(throwsReachPage);
  await throwsReachPage.addInitScript({
    content: `window.__reachCalls = 0; window.roistatGoal = { reach: function () { window.__reachCalls++; throw new Error("blocked"); } };`
  });
  await throwsReachPage.addInitScript({ content: DRAFT_CAPTURE_SRC });
  await throwsReachPage.addInitScript({ content: POLYFILL_SRC });
  await throwsReachPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await throwsReachPage.evaluate(() => localStorage.removeItem("anima_lead_outbox_v1"));
  await throwsReachPage.fill('#leadForm input[name="name"]', "Throws Reach Human");
  await throwsReachPage.fill('#leadForm input[name="business"]', "Throws Co");
  await throwsReachPage.fill('#leadForm input[name="city"]', "Kyiv");
  await throwsReachPage.fill('#leadForm input[name="contact"]', "throws@example.com");
  await throwsReachPage.click('#leadForm button[type="submit"]');
  await throwsReachPage.waitForTimeout(200);
  const throwsStatus = await throwsReachPage.textContent("#leadForm .lf-status");
  check(
    "reach() throws: shows the honest delivery-failed message",
    /couldn't send your request automatically/i.test(throwsStatus || ""),
    JSON.stringify(throwsStatus)
  );
  const throwsOutbox = await throwsReachPage.evaluate(() => JSON.parse(localStorage.getItem("anima_lead_outbox_v1") || "[]"));
  check(
    "reach() throws: the lead was saved to the outbox, and no lead_accepted fired",
    Array.isArray(throwsOutbox) && throwsOutbox.length === 1,
    JSON.stringify(throwsOutbox)
  );
  const throwsDataLayer = await throwsReachPage.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check("reach() throws: no lead_accepted event was pushed", throwsDataLayer.length === 0, JSON.stringify(throwsDataLayer));

  // 11. Honest-delivery (TDD case: lone surrogate). A lone UTF-16 surrogate
  // half in a field must not throw out of the handler -- honest message and
  // contacts still show, and the outbox entry is still saved.
  const loneSurrogatePage = await browser.newPage();
  await blockRoistat(loneSurrogatePage);
  await loneSurrogatePage.addInitScript({ content: `window.roistatGoal = { reach: function () { throw new Error("blocked"); } };` });
  await loneSurrogatePage.addInitScript({ content: DRAFT_CAPTURE_SRC });
  await loneSurrogatePage.addInitScript({ content: POLYFILL_SRC });
  await loneSurrogatePage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await loneSurrogatePage.evaluate(() => localStorage.removeItem("anima_lead_outbox_v1"));
  var lonePageErrored = false;
  loneSurrogatePage.on("pageerror", function () { lonePageErrored = true; });
  await loneSurrogatePage.fill('#leadForm input[name="name"]', "Lone Surrogate Human");
  await loneSurrogatePage.fill('#leadForm input[name="business"]', "Lone Co");
  await loneSurrogatePage.fill('#leadForm input[name="city"]', "Kyiv");
  await loneSurrogatePage.fill('#leadForm input[name="contact"]', "lone@example.com");
  await loneSurrogatePage.evaluate(() => {
    var f = document.querySelector('#leadForm textarea[name="message"]');
    f.value = "before \ud83d lone surrogate";
    f.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await loneSurrogatePage.click('#leadForm button[type="submit"]', { force: true });
  await loneSurrogatePage.waitForTimeout(200);
  check("lone surrogate in a field: no uncaught error out of the handler", lonePageErrored === false, JSON.stringify(lonePageErrored));
  const loneStatus = await loneSurrogatePage.textContent("#leadForm .lf-status");
  check(
    "lone surrogate in a field: the honest delivery-failed message and contacts are still shown",
    /couldn't send your request automatically|could not send via the site/i.test(loneStatus || ""),
    JSON.stringify(loneStatus)
  );
  const loneHasTel = await loneSurrogatePage.evaluate(() => !!document.querySelector('#leadForm .lf-status a[href^="tel:"]'));
  check("lone surrogate in a field: tel contact still present", loneHasTel, JSON.stringify(loneHasTel));
  const loneOutbox = await loneSurrogatePage.evaluate(() => JSON.parse(localStorage.getItem("anima_lead_outbox_v1") || "[]"));
  check("lone surrogate in a field: the outbox entry is still saved", Array.isArray(loneOutbox) && loneOutbox.length === 1, JSON.stringify(loneOutbox));

  // 12. Honest-delivery (TDD case: oversized fields). A non-details field so
  // large the ~1800-char bound can never be met even with details truncated
  // to empty must omit the controls (not throw), and still save the outbox.
  const oversizedPage = await browser.newPage();
  await blockRoistat(oversizedPage);
  await oversizedPage.addInitScript({ content: `window.roistatGoal = { reach: function () { throw new Error("blocked"); } };` });
  await oversizedPage.addInitScript({ content: DRAFT_CAPTURE_SRC });
  await oversizedPage.addInitScript({ content: POLYFILL_SRC });
  await oversizedPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  await oversizedPage.evaluate(() => localStorage.removeItem("anima_lead_outbox_v1"));
  var oversizedErrored = false;
  oversizedPage.on("pageerror", function () { oversizedErrored = true; });
  await oversizedPage.fill('#leadForm input[name="name"]', "Oversized Other Human");
  await oversizedPage.fill('#leadForm input[name="business"]', "y".repeat(3000));
  await oversizedPage.fill('#leadForm input[name="city"]', "Kyiv");
  await oversizedPage.fill('#leadForm input[name="contact"]', "oversized@example.com");
  await oversizedPage.click('#leadForm button[type="submit"]', { force: true });
  await oversizedPage.waitForTimeout(200);
  check("other fields oversized: no throw", oversizedErrored === false, JSON.stringify(oversizedErrored));
  const oversizedBtnCount = await oversizedPage.evaluate(() => document.querySelectorAll("#leadForm .lf-status button.lf-draft-btn").length);
  check("other fields oversized: no one-tap button is shown (bound unreachable)", oversizedBtnCount === 0, JSON.stringify(oversizedBtnCount));
  const oversizedOutbox = await oversizedPage.evaluate(() => JSON.parse(localStorage.getItem("anima_lead_outbox_v1") || "[]"));
  check("other fields oversized: the outbox entry is still saved", Array.isArray(oversizedOutbox) && oversizedOutbox.length === 1, JSON.stringify(oversizedOutbox));

  // 13. Honest-delivery (TDD case: flushOutbox re-delivery). A stale outbox
  // entry from a prior failed submit must be re-sent via reach() once
  // Roistat becomes available on a later page view, fire lead_accepted with
  // delivery_status "unconfirmed", and then be cleared from the outbox.
  const flushPage = await browser.newPage();
  await blockRoistat(flushPage);
  await flushPage.addInitScript({
    content: `window.localStorage.setItem("anima_lead_outbox_v1", JSON.stringify([{ ts: Date.now(), origin: "human", data: { name: "Flush Test Lead", company: "Flush Co", city: "Kyiv", machines: "", contact: "flush@example.com", details: "", source_page: "/index.html" } }]));`
  });
  await flushPage.addInitScript({ content: `window.__roistatCalls = [];` });
  await flushPage.goto(`${BASE_URL}/index.html`, { waitUntil: "networkidle" });
  // Roistat becomes available AFTER the page has loaded (flushOutbox() runs
  // on DOMContentLoaded and, since window.roistatGoal isn't defined yet,
  // waits via waitForRoistat() up to the real ~4s default cap).
  await flushPage.evaluate(() => { window.roistatGoal = { reach: function (p) { window.__roistatCalls.push(p); } }; });
  await flushPage.waitForTimeout(300);
  const flushCalls = await flushPage.evaluate(() => window.__roistatCalls);
  check(
    "flushOutbox: the stale outbox entry is re-sent via exactly one reach() call",
    Array.isArray(flushCalls) && flushCalls.length === 1 && flushCalls[0].name === "Flush Test Lead",
    JSON.stringify(flushCalls)
  );
  const flushDataLayer = await flushPage.evaluate(() => (window.dataLayer || []).filter((e) => e && e.event === "lead_accepted"));
  check(
    "flushOutbox: re-send fires lead_accepted with delivery_status 'unconfirmed'",
    flushDataLayer.length === 1 && flushDataLayer[0].delivery_status === "unconfirmed",
    JSON.stringify(flushDataLayer)
  );
  const flushOutboxAfter = await flushPage.evaluate(() => JSON.parse(localStorage.getItem("anima_lead_outbox_v1") || "[]"));
  check("flushOutbox: the re-sent entry is cleared from the outbox", Array.isArray(flushOutboxAfter) && flushOutboxAfter.length === 0, JSON.stringify(flushOutboxAfter));

  // 14. Pixel positions + viewport safety at 375x667, EN, UA, and the PR #88
  // newer page (pricing-model.html) which gained the sticky CTA bar. Prints
  // real measured top/bottom for each one-tap control and the sticky bar's
  // top, plus innerHeight, and asserts the first control is both in-viewport
  // and not covered by the sticky bar (Playwright's own click actionability
  // check does real hit-testing).
  async function checkViewportAfterDeliveryFailed(url, langLabel) {
    const pg = await browser.newPage({ viewport: { width: 375, height: 667 } });
    await blockRoistat(pg);
    await pg.addInitScript({ content: `window.roistatGoal = { reach: function () { throw new Error("blocked"); } };` });
    await pg.addInitScript({ content: DRAFT_CAPTURE_SRC });
    await pg.addInitScript({ content: POLYFILL_SRC });
    await pg.goto(url, { waitUntil: "networkidle" });
    await pg.evaluate(() => localStorage.removeItem("anima_lead_outbox_v1"));
    await pg.fill('#leadForm input[name="name"]', "Viewport Human");
    await pg.fill('#leadForm input[name="business"]', "Viewport Co");
    await pg.fill('#leadForm input[name="city"]', "Kyiv");
    await pg.fill('#leadForm input[name="contact"]', "viewport@example.com");
    await pg.click('#leadForm button[type="submit"]');
    let settled = false;
    let prevY = await pg.evaluate(() => window.scrollY);
    for (let i = 0; i < 20 && !settled; i++) {
      await pg.waitForTimeout(100);
      const y = await pg.evaluate(() => window.scrollY);
      if (y === prevY) settled = true;
      prevY = y;
    }
    const metrics = await pg.evaluate(() => {
      var btns = document.querySelectorAll("#leadForm .lf-status button.lf-draft-btn");
      var bar = document.getElementById("sticky-cta");
      var barRect = bar ? bar.getBoundingClientRect() : null;
      var out = { innerHeight: window.innerHeight, barTop: barRect ? barRect.top : null, buttons: [] };
      Array.prototype.forEach.call(btns, function (btn) {
        var rects = btn.getClientRects();
        var r = rects[0] || btn.getBoundingClientRect();
        out.buttons.push({ label: btn.textContent, top: r.top, bottom: r.bottom });
      });
      return out;
    });
    console.log(`PIXELS ${langLabel} (${url}): innerHeight=${metrics.innerHeight} stickyBarTop=${metrics.barTop} buttons=${JSON.stringify(metrics.buttons)}`);
    check(
      `${langLabel} 375x667: both one-tap buttons rendered`,
      metrics.buttons.length === 2,
      JSON.stringify(metrics)
    );
    check(
      `${langLabel} 375x667: both one-tap buttons are within the viewport after scroll settles`,
      settled && metrics.buttons.length === 2 && metrics.buttons.every((b) => b.top >= 0 && b.bottom <= metrics.innerHeight),
      JSON.stringify({ settled, metrics })
    );
    let clickOk = false;
    let clickError = null;
    try {
      await pg.click("#leadForm .lf-status button.lf-draft-btn >> nth=0", { timeout: 3000 });
      clickOk = true;
    } catch (e) {
      clickError = String(e).split("\n")[0];
    }
    check(
      `${langLabel} 375x667: the first one-tap button is not covered by the sticky CTA bar (clickable)`,
      clickOk === true,
      JSON.stringify({ clickOk, clickError })
    );
    await pg.close();
  }
  await checkViewportAfterDeliveryFailed(`${BASE_URL}/index.html`, "EN");
  await checkViewportAfterDeliveryFailed(`${BASE_URL}/ua/index.html`, "UA");
  await checkViewportAfterDeliveryFailed(`${BASE_URL}/pricing-model.html`, "EN-pricing-model(PR88-sticky)");

  await browser.close();

  console.log(`\nHeadless WebMCP check: ${failures === 0 ? "ALL PASS" : failures + " FAILURE(S)"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
