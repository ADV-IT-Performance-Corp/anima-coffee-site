#!/usr/bin/env node
/* Test harness for assets/webmcp.js — no browser, no network, no deps.
 * Loads the real file into a node `vm` context with minimal DOM stubs and
 * prints a JSON report on stdout. Driven by tools/test_webmcp_tools.py.
 *
 *   node tools/webmcp_harness.js <mode> '<json calls>'
 *     mode = document   -> document.modelContext exists
 *            navigator  -> only navigator.modelContext exists
 *            none       -> neither (the polyfill loader path)
 *            nopage     -> document.modelContext exists but no #leadForm
 *
 * It executes the listed calls ([{tool, args}]) and reports results plus
 * every observed side effect (registrations, form events, submit attempts,
 * injected scripts). webmcp.js is loaded TWICE to prove registration is
 * idempotent.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const mode = process.argv[2] || "document";
const calls = JSON.parse(process.argv[3] || "[]");
const src = fs.readFileSync(path.join(__dirname, "..", "assets", "webmcp.js"), "utf8");

const log = { registered: [], submitAttempts: 0, scrolled: 0, focused: [], injectedScripts: [] };

function field(name, required) {
  return {
    name, value: "", required: !!required, tagName: "INPUT",
    focus() { log.focused.push(name); },
    dispatchEvent() { return true; },
  };
}
const fields = {};
["name", "business", "city", "machines", "contact", "message", "company_url"].forEach((n) => {
  fields[n] = field(n, ["name", "business", "city", "contact"].indexOf(n) >= 0);
});
const submitBtn = { tagName: "BUTTON", type: "submit", focus() { log.focused.push("submit"); }, click() { log.submitAttempts++; } };
const form = {
  id: "leadForm",
  querySelector(sel) {
    const m = /\[name="([^"]+)"\]/.exec(sel);
    if (m) return fields[m[1]] || null;
    if (/submit/.test(sel)) return submitBtn;
    return null;
  },
  scrollIntoView() { log.scrolled++; },
  submit() { log.submitAttempts++; },
  requestSubmit() { log.submitAttempts++; },
  dispatchEvent(e) { if (e && e.type === "submit") log.submitAttempts++; return true; },
};

function makeContext() {
  return { registerTool(t) { log.registered.push(t); return Promise.resolve(); } };
}

const doc = {
  currentScript: { src: "https://aeo.animacoffee.com.ua/assets/webmcp.js" },
  head: {
    appendChild(el) {
      log.injectedScripts.push(el.src);
      setImmediate(() => { doc.modelContext = makeContext(); if (el.onload) el.onload(); });
    },
  },
  createElement(tag) { return { tagName: tag.toUpperCase() }; },
  getElementById(id) { return mode === "nopage" ? null : id === "leadForm" ? form : null; },
  querySelector(sel) { return mode === "nopage" ? null : sel === "#leadForm" ? form : null; },
};
const nav = {};
if (mode === "document" || mode === "nopage") doc.modelContext = makeContext();
if (mode === "navigator") nav.modelContext = makeContext();

const sandbox = {
  document: doc, navigator: nav, console, setTimeout, Promise,
  Event: function (type, init) { this.type = type; Object.assign(this, init || {}); },
};
sandbox.window = sandbox;
vm.createContext(sandbox);

(async () => {
  vm.runInContext(src, sandbox, { filename: "webmcp.js" });
  vm.runInContext(src, sandbox, { filename: "webmcp.js" });
  await new Promise((r) => setTimeout(r, 50));
  const results = [];
  for (const c of calls) {
    const t = log.registered.find((x) => x.name === c.tool);
    results.push(t ? await t.execute(c.args || {}) : { __missing: c.tool });
  }
  process.stdout.write(JSON.stringify({
    tools: log.registered.map((t) => ({ name: t.name, annotations: t.annotations })),
    results,
    form: Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, v.value])),
    submitAttempts: log.submitAttempts, scrolled: log.scrolled, focused: log.focused,
    injectedScripts: log.injectedScripts,
  }));
})();
