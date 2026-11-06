"""Real browser payload -> actual local workerd/D1, no external network or live receiver."""
import json
import mimetypes
import os
import queue
from pathlib import Path
import subprocess
import threading
import unittest
from urllib.parse import urlsplit, unquote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://aeo.animacoffee.com.ua"
KEY = "anima_lead_outbox_v1"

class WorkerBrowserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        options = {"timeout": 15000}
        if os.environ.get("ANIMA_TEST_CHROMIUM"):
            options["executable_path"] = os.environ["ANIMA_TEST_CHROMIUM"]
        cls.browser = cls.pw.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def read_message(self):
        result = queue.Queue(maxsize=1)
        threading.Thread(target=lambda: result.put(self.receiver.stdout.readline()), daemon=True).start()
        try:
            line = result.get(timeout=20)
        except queue.Empty:
            self.fail("Local Worker IPC timed out")
        self.assertTrue(line, "Local Worker closed its IPC channel")
        return json.loads(line)

    def ipc(self, value):
        self.receiver.stdin.write(json.dumps(value) + "\n")
        self.receiver.stdin.flush()
        return self.read_message()

    def stop_receiver(self):
        self.receiver.stdin.close()
        try:
            self.receiver.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.receiver.terminate()
            self.receiver.wait(timeout=5)
        finally:
            self.receiver.stdout.close()
            self.receiver.stderr.close()

    def setUp(self):
        self.receiver = subprocess.Popen(["node", "test/browser-receiver.mjs"], cwd=ROOT / "workers/anima-lead",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.addCleanup(self.stop_receiver)
        self.assertTrue(self.read_message()["ready"])
        self.context = self.browser.new_context()
        self.addCleanup(self.context.close)
        self.requests, self.receipts = [], []
        self.lose_response = False
        self.blocked = []
        def route(r):
            u = urlsplit(r.request.url)
            # The production-looking origin is virtual: every request is intercepted.
            if u.scheme + "://" + u.netloc != ORIGIN:
                self.blocked.append(r.request.url)
                return r.abort()
            if u.path == "/api/anima/lead":
                if r.request.method != "POST":
                    return r.fulfill(status=405, body="{}")
                body = r.request.post_data_json
                self.requests.append(body)
                result = self.ipc({"payload": body})
                self.receipts.append(result)
                if self.lose_response:
                    self.lose_response = False
                    return r.abort()
                return r.fulfill(status=result["status"], content_type="application/json", body=json.dumps(result["body"]))
            path = (ROOT / (unquote(u.path).lstrip("/") or "index.html")).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                return r.fulfill(status=404, body="")
            data = path.read_bytes()
            if path.suffix == ".html":
                data = data.replace(b'data-endpoint=""', b'data-endpoint="https://aeo.animacoffee.com.ua/api/anima/lead"')
            return r.fulfill(status=200, content_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream", body=data)
        self.context.route("**/*", route)
        self.page = self.context.new_page()
        self.page.goto(ORIGIN + "/", wait_until="domcontentloaded")

    def submit(self):
        return self.page.evaluate("""() => animaLead.submitChat(Object.assign(animaLead.collectBase(), {
            name:'Synthetic',contact:'fixture@example.invalid',consent:true
        }))""")

    def test_browser_generated_key_commits_once(self):
        result = self.submit()
        self.assertRegex(self.requests[0]["idempotency_key"], r"^anima_[0-9a-f-]{36}$")
        self.assertEqual(self.receipts[0]["status"], 200)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(self.ipc({"op":"count"})["count"], 1)

    def replay_after_loss(self, legacy_missing=False):
        self.lose_response = True
        self.submit()
        self.assertEqual(self.receipts[0]["status"], 200)
        self.assertEqual(self.requests[0]["roistat_visit"], "")
        self.assertEqual(self.requests[0]["ai_source"], "")
        if legacy_missing:
            self.page.evaluate("""key => {const rows=JSON.parse(localStorage.getItem(key));
                delete rows[0].data.roistat_visit; delete rows[0].data.ai_source;
                localStorage.setItem(key,JSON.stringify(rows));} """, KEY)
        self.assertTrue(self.ipc({"op":"restart"})["ready"])
        self.context.add_cookies([{"name":"roistat_visit","value":"987654","url":ORIGIN}])
        self.page.close()
        self.page = self.context.new_page()
        self.page.goto(ORIGIN + "/?utm_source=chatgpt.com", wait_until="domcontentloaded")
        try:
            self.page.wait_for_function("key => !localStorage.getItem(key)", arg=KEY, timeout=5000)
        except PlaywrightTimeoutError:
            self.fail("Stored receipt not recovered; Worker HTTP sequence: " + str([r["status"] for r in self.receipts]))
        self.assertEqual(self.requests[0], self.requests[1])
        self.assertEqual(self.receipts[0]["body"]["lead_id"], self.receipts[1]["body"]["lead_id"])
        self.assertEqual(self.ipc({"op":"count"})["count"], 1)

    def test_empty_attribution_survives_restart_and_later_visit(self):
        self.replay_after_loss()

    def test_legacy_missing_attribution_does_not_acquire_later_visit(self):
        self.replay_after_loss(legacy_missing=True)

    def test_invalid_cookie_cannot_poison_intake(self):
        self.context.add_cookies([{"name":"roistat_visit","value":"not-a-visit","url":ORIGIN}])
        self.submit()
        self.assertEqual(self.requests[0]["roistat_visit"], "")
        self.assertEqual(self.receipts[0]["status"], 200)

if __name__ == "__main__":
    unittest.main()
