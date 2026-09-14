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

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await blockRoistat(page);

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

  // 3. Human submit path unchanged: fill + click submit, expect fallback block
  await page.fill('#leadForm input[name="name"]', "Human Visitor");
  await page.fill('#leadForm input[name="business"]', "Human Co");
  await page.fill('#leadForm input[name="city"]', "Kyiv");
  await page.fill('#leadForm input[name="contact"]', "human@example.com");
  await page.click('#leadForm button[type="submit"]');
  await page.waitForTimeout(200);
  const statusText = await page.textContent("#leadForm .lf-status");
  const hasHighlight = await page.evaluate(() => !!document.querySelector(".contact-block.lf-highlight"));
  check(
    "human submit with empty endpoint shows the fallback contact block",
    /isn't wired|reach us directly/i.test(statusText || "") || hasHighlight,
    JSON.stringify({ statusText, hasHighlight })
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

  await browser.close();

  console.log(`\nHeadless WebMCP check: ${failures === 0 ? "ALL PASS" : failures + " FAILURE(S)"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
