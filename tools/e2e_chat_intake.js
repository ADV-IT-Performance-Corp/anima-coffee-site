// Headless check: ChatKit lead -> first-party intake (Cloudflare Worker contract), MOCKED. No real leads.
// Run: node tools/e2e_chat_intake.js   (needs playwright; serves repo on a local port)
const { chromium } = require("playwright");
const http = require("http"), fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "..");
const srv = http.createServer((q, s) => {
  let p = decodeURIComponent(q.url.split("?")[0]); if (p.endsWith("/")) p += "index.html";
  const f = path.join(root, p);
  if (!f.startsWith(root) || !fs.existsSync(f)) { s.statusCode = 404; return s.end(); }
  const t = { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" }[path.extname(f)] || "application/octet-stream";
  s.setHeader("Content-Type", t); s.end(fs.readFileSync(f));
});
(async () => {
  await new Promise(r => srv.listen(0, "127.0.0.1", r));
  const port = srv.address().port, base = `http://127.0.0.1:${port}`;
  const b = await chromium.launch();
  const results = [];
  for (const mode of ["ok", "fail"]) {
    const pg = await b.newPage();
    const hits = [];
    await pg.route("**/api/anima/lead", r => {
      if (r.request().method() === "OPTIONS") return r.fulfill({ status: 204 });
      hits.push(JSON.parse(r.request().postData()));
      if (mode === "ok") r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "accepted", lead_id: "11111111-2222-4333-8444-555555555555" }) });
      else r.fulfill({ status: 503, body: "{}" });
    });
    await pg.addInitScript(() => localStorage.clear());
    await pg.goto(base + "/index.html");
    await pg.evaluate(() => document.querySelectorAll("form.lead-form").forEach(f => f.setAttribute("data-endpoint", "http://127.0.0.1:" + location.port + "/api/anima/lead")));
    await pg.click(".ac-launcher");
    await pg.click(".ac-chip"); await pg.waitForSelector(".ac-row input");
    await pg.fill(".ac-row input", "150"); await pg.press(".ac-row input", "Enter");
    await pg.waitForSelector(".ac-chip"); await pg.click(".ac-chip");
    await pg.waitForSelector(".ac-chip:last-child"); await pg.click(".ac-chips .ac-chip:last-child");
    await pg.waitForSelector(".ac-form", { timeout: 5000 });
    await pg.fill(".ac-form input[name=contact]", "+380731234567");
    await pg.check(".ac-form input[type=checkbox]");
    await pg.click(".ac-send"); await pg.waitForTimeout(800);
    const log = await pg.innerText(".ac-log");
    results.push({ mode, hits: hits.length, p: hits[0] && { src: hits[0].lead_source, consent: hits[0].consent, key: /^anima_/.test(hits[0].idempotency_key), slug: hits[0].client_slug, phone: hits[0].phone }, log: log.slice(-140) });
    await pg.close();
  }
  await b.close(); srv.close();
  console.log(JSON.stringify(results, null, 1));
  const ok = results[0].hits === 1 && results[0].p.src === "chatkit" && results[0].p.consent === true && results[0].p.key &&
    results[1].hits >= 1 && /380|animacoffeeco|Telegram/i.test(results[1].log);
  console.log(ok ? "E2E OK" : "E2E FAIL"); process.exit(ok ? 0 : 1);
})();
