#!/usr/bin/env python3
"""Real-browser test: every WebMCP tool answers through the vendored
@mcp-b/global polyfill within 5 seconds.

Usage: python3 -m pytest tools/test_webmcp_polyfill_browser.py -v

Serves the repo with a local static server and drives headless Chromium via
Playwright (no network, nothing is submitted, nothing live is touched).
Skips (never silently passes) when Playwright or a Chromium build is missing.

Why this exists: the node harness (tools/webmcp_harness.js) calls `execute`
directly and never goes through the polyfill, so it could not see that
`executeTool('<name>', ...)` on the polyfill context failed. In the polyfill
(and the spec) executeTool takes a RegisteredTool descriptor, not a name.
"""
import functools
import glob
import http.server
import json
import os
import pathlib
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = {
    "get_anima_service_info": {"question": "Do you have a free trial?", "language": "en"},
    "get_anima_products": {"category": "super_automatic", "language": "en"},
    "prepare_coffee_quote_request": {"name": "Test", "business": "Cafe", "city": "Kyiv", "language": "en"},
}
TIMEOUT_MS = 5000

# Calls the context the way the task / an agent would: by tool NAME, with args
# given as a JSON string, an object, or omitted. Always bounded by a timer so a
# hang is reported as a failure, never as a stuck test run.
CALL_JS = """async ([name, args, mode]) => {
  const c = document.modelContext || navigator.modelContext;
  const t0 = performance.now();
  const call = () => {
    if (mode === 'json') return c.executeTool(name, JSON.stringify(args));
    if (mode === 'object') return c.executeTool(name, args);
    return Promise.resolve(c.getTools()).then(ts => {
      const d = Array.from(ts).find(t => t.name === name);
      return c.executeTool(d, JSON.stringify(args));
    });
  };
  const guard = new Promise(r => setTimeout(() => r({ timeout: true }), %d));
  const run = Promise.resolve().then(call).then(
    v => ({ ok: v, ms: Math.round(performance.now() - t0) }),
    e => ({ err: String(e), ms: Math.round(performance.now() - t0) }));
  return Promise.race([run, guard]);
}""" % TIMEOUT_MS


def _chromium_exe():
    pats = [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"),
    ]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    return None


@pytest.fixture(scope="module")
def page():
    sync_api = pytest.importorskip("playwright.sync_api")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            exe = _chromium_exe()
            if not exe:
                httpd.shutdown()
                pytest.skip("no Chromium available for Playwright")
            browser = p.chromium.launch(executable_path=exe)
        pg = browser.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/index.html")
        pg.wait_for_function("window.__animaWebmcpState === 'registered'", timeout=8000)
        pg.js_errors = errors
        yield pg
        browser.close()
    httpd.shutdown()


def test_polyfill_was_injected_and_tools_listed(page):
    info = page.evaluate("""() => {
      const c = document.modelContext || navigator.modelContext;
      return { names: c.listTools().map(t => t.name), testing: typeof navigator.modelContextTesting };
    }""")
    for n in TOOLS:
        assert n in info["names"], info
    assert "request_coffee_service_assessment" in info["names"]
    assert info["names"].count("get_anima_products") == 1  # registered exactly once


@pytest.mark.parametrize("mode", ["json", "object", "descriptor"])
@pytest.mark.parametrize("name", sorted(TOOLS))
def test_every_tool_answers_within_5s(page, name, mode):
    r = page.evaluate(CALL_JS, [name, TOOLS[name], mode])
    print(f"BROWSER-CALL {mode:10s} {name:30s} -> {json.dumps(r)[:240]}")
    assert "timeout" not in r, f"{name} did not return within {TIMEOUT_MS}ms"
    assert "err" not in r, r["err"]
    assert r["ms"] < TIMEOUT_MS
    out = json.loads(r["ok"]) if isinstance(r["ok"], str) else r["ok"]
    assert isinstance(out, dict)
    if name == "get_anima_service_info":
        assert out["published"] is True and "14-day" in out["answer"]
    elif name == "get_anima_products":
        assert out["super_automatic"]["brands"] == ["Dr. Coffee", "Necta"]
    else:
        assert out["prefilled"] is True and out["submitted"] is False


def test_prepare_quote_never_submits(page):
    r = page.evaluate("""() => {
      const f = document.getElementById('leadForm');
      return { name: f.querySelector('[name=name]').value, url: location.pathname };
    }""")
    assert r["name"] == "Test"           # prefilled by the calls above
    assert r["url"].endswith("index.html") or r["url"] == "/index.html"


def test_unknown_tool_rejects_fast(page):
    r = page.evaluate(CALL_JS, ["no_such_tool", {}, "json"])
    assert "timeout" not in r
    assert "err" in r


def test_no_page_errors(page):
    assert page.js_errors == []
