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

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

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

  await browser.close();

  console.log(`\nHeadless WebMCP check: ${failures === 0 ? "ALL PASS" : failures + " FAILURE(S)"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
