"""Browser-to-stub tests. All traffic except the local fixture is blocked."""
import functools
import http.server
import json
import os
from pathlib import Path
import threading
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = "anima_lead_outbox_v1"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

class DurableLeads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path=os.environ.get("ANIMA_TEST_CHROMIUM"))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context()
        self.context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.base + "/") else r.abort())
        self.page = self.context.new_page()
        self.page.add_init_script("window.__ROISTAT_TEST_WAIT_MS = 20;")
        self.endpoint = self.base + "/api/anima/lead"
        self.requests = []
        self.hanging = []
        self.mode = "accepted"
        self.committed = set()
        def api(route):
            self.requests.append(route.request.post_data_json)
            if self.mode == "lost":
                self.committed.add(route.request.post_data_json.get('idempotency_key'))
                route.abort()
            elif self.mode == "hang":
                self.hanging.append(route)
                return
            elif self.mode == "unavailable":
                route.fulfill(status=503, body="{}")
            elif self.mode == "malformed":
                route.fulfill(status=200, content_type="application/json", body='{"lead_id":"fake"}')
            else:
                self.committed.add(route.request.post_data_json.get('idempotency_key'))
                route.fulfill(status=200, content_type="application/json", body='{"status":"accepted","lead_id":"11111111-1111-4111-8111-111111111111"}')
        self.context.route("**/api/anima/lead", api)
        self.page.goto(self.base + "/")
        self.page.evaluate("e => document.querySelector('form.lead-form').setAttribute('data-endpoint', e)", self.endpoint)

    def tearDown(self):
        self.context.close()

    def submit(self, consent=True):
        return self.page.evaluate("""consent => animaLead.submitChat({name:'Synthetic', company:'Fixture', city:'Kyiv', machines:'1', contact:'probe@example.invalid', details:'Offline fixture', source_page:'/', consent})""", consent)

    def outbox(self):
        return self.page.evaluate("k => JSON.parse(localStorage.getItem(k) || '[]')", KEY)

    def test_server_contract(self):
        self.assertEqual(self.submit()['status'], 'accepted')
        p = self.requests[0]
        self.assertEqual(p['client_slug'], 'anima-coffee')
        self.assertEqual(p['email'], 'probe@example.invalid')
        self.assertEqual(p['business'], 'Fixture')
        self.assertEqual(p['page_slug'], '/')
        self.assertTrue(p['consent'])
        self.assertGreaterEqual(len(p['idempotency_key']), 8)
        self.assertNotIn('contact', p)
        self.assertEqual(self.outbox(), [])

    def test_outage_retry_same_id(self):
        self.mode = 'unavailable'
        self.assertNotEqual(self.submit()['status'], 'accepted')
        self.assertEqual(len(self.outbox()), 1)
        first = self.requests[0]['idempotency_key']
        self.mode = 'accepted'
        self.assertEqual(self.submit()['status'], 'accepted')
        self.assertEqual(self.requests[1]['idempotency_key'], first)
        self.assertEqual(self.outbox(), [])

    def test_lost_response_reload_replays_without_roistat(self):
        self.mode = 'lost'
        self.submit()
        first = self.requests[0]['idempotency_key']
        self.mode = 'accepted'
        # This fixture has no deployment endpoint in HTML; set it before
        # DOMContentLoaded, as deployment would do in the page source.
        self.page.route(self.base + '/', lambda r: r.fulfill(content_type='text/html', body=(ROOT/'index.html').read_text(encoding='utf-8').replace('data-endpoint=""', 'data-endpoint="'+self.endpoint+'"')))
        self.page.reload()
        self.page.wait_for_function("k => !localStorage.getItem(k)", arg=KEY)
        self.assertEqual(self.requests[1]['idempotency_key'], first)
        self.assertEqual(len(self.committed), 1)

    def test_malformed_receipt_keeps_pending(self):
        self.mode = 'malformed'
        self.assertNotEqual(self.submit()['status'], 'accepted')
        self.assertEqual(len(self.outbox()), 1)

    def test_consent_required(self):
        self.assertNotEqual(self.submit(False)['status'], 'accepted')
        self.assertEqual(self.requests, [])
        self.assertEqual(self.outbox(), [])

    def test_no_roistat_after_uncertain_server_result(self):
        self.mode = 'lost'
        self.page.evaluate("window.__calls=[]; window.roistatGoal={reach:p=>__calls.push(p)}")
        self.submit()
        self.assertEqual(self.page.evaluate('__calls.length'), 0)

    def test_legacy_fallback_survives(self):
        self.page.evaluate("document.querySelector('form.lead-form').dataset.endpoint=''")
        self.assertEqual(self.submit()['status'], 'not_connected')
        self.assertEqual(len(self.outbox()), 1)
        self.assertEqual(self.requests, [])

    def test_endpoint_change_does_not_leak_pending(self):
        self.mode = 'lost'
        self.submit()
        self.page.evaluate("document.querySelector('form.lead-form').dataset.endpoint='https://other.example.invalid/api/anima/lead'; window.dispatchEvent(new Event('online'))")
        self.page.wait_for_timeout(150)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.outbox()), 1)

    def test_rollback_does_not_send_server_item_via_roistat(self):
        self.mode = 'lost'
        self.submit()
        self.page.evaluate("document.querySelector('form.lead-form').dataset.endpoint=''; window.__calls=[]; window.roistatGoal={reach:p=>__calls.push(p)}; window.dispatchEvent(new Event('online'))")
        self.page.wait_for_timeout(150)
        self.assertEqual(self.page.evaluate('__calls.length'), 0)
        self.assertEqual(len(self.outbox()), 1)

    def test_expiry_is_physically_purged(self):
        self.mode = 'lost'
        self.submit()
        self.page.evaluate("k => { let q=JSON.parse(localStorage.getItem(k)); q[0].ts=Date.now()-8*86400000; localStorage.setItem(k,JSON.stringify(q)); window.dispatchEvent(new Event('online')); }", KEY)
        self.assertEqual(self.outbox(), [])
        self.assertEqual(len(self.requests), 1)

    def test_unsafe_endpoint_refused(self):
        self.page.evaluate("document.querySelector('form.lead-form').dataset.endpoint='https://example.invalid/api/lead/v2'")
        self.assertNotEqual(self.submit()['status'], 'accepted')
        self.assertEqual(self.requests, [])
        self.assertEqual(self.outbox(), [])

    def test_human_form_contract(self):
        self.page.locator('form.lead-form input[name=name]').fill('Synthetic')
        self.page.locator('form.lead-form input[name=business]').fill('Fixture')
        self.page.locator('form.lead-form input[name=city]').fill('Kyiv')
        self.page.locator('form.lead-form input[name=contact]').fill('probe@example.invalid')
        self.page.locator('form.lead-form').evaluate("f => f.dispatchEvent(new Event('submit', {cancelable:true}))")
        self.page.wait_for_function("document.querySelector('.lf-status').classList.contains('ok')")
        self.assertEqual(self.requests[0]['client_slug'], 'anima-coffee')
        self.assertTrue(self.requests[0]['consent'])

    def test_agent_form_contract(self):
        self.page.locator('form.lead-form input[name=name]').fill('Synthetic')
        self.page.locator('form.lead-form input[name=business]').fill('Fixture')
        self.page.locator('form.lead-form input[name=city]').fill('Kyiv')
        self.page.locator('form.lead-form input[name=contact]').fill('probe@example.invalid')
        result = self.page.evaluate("""() => new Promise(resolve => {
            let e=new Event('submit', {cancelable:true});
            e.agentInvoked=true; e.respondWith=p=>p.then(resolve);
            document.querySelector('form.lead-form').dispatchEvent(e);
        })""")
        self.assertEqual(result['receipt'], 'stored')
        self.assertEqual(self.requests[0]['client_slug'], 'anima-coffee')

    def test_interrupted_page_replays_in_new_tab(self):
        self.mode = 'lost'
        self.submit()
        first = self.requests[0]['idempotency_key']
        self.page.close()
        self.mode = 'accepted'
        html = (ROOT/'index.html').read_text(encoding='utf-8').replace('data-endpoint=""', 'data-endpoint="'+self.endpoint+'"')
        self.context.route(self.base + '/', lambda r: r.fulfill(content_type='text/html', body=html))
        self.page = self.context.new_page()
        self.page.goto(self.base + '/')
        self.page.wait_for_function("k => !localStorage.getItem(k)", arg=KEY)
        self.assertEqual(self.requests[1]['idempotency_key'], first)
        self.assertEqual(len(self.committed), 1)

    def test_visit_survives_outage_and_later_cookie_change(self):
        self.context.add_cookies([{'name':'roistat_visit','value':'123456','url':self.base}])
        self.mode = 'lost'
        self.submit()
        self.assertEqual(self.requests[0]['roistat_visit'], '123456')
        self.context.add_cookies([{'name':'roistat_visit','value':'987654','url':self.base}])
        self.mode = 'accepted'
        self.page.route(self.base + '/', lambda r: r.fulfill(content_type='text/html', body=(ROOT/'index.html').read_text(encoding='utf-8').replace('data-endpoint=""', 'data-endpoint="'+self.endpoint+'"')))
        self.page.reload()
        self.page.wait_for_function("k => !localStorage.getItem(k)", arg=KEY)
        self.assertEqual(self.requests[1]['roistat_visit'], '123456')
        self.assertEqual(self.requests[0]['idempotency_key'], self.requests[1]['idempotency_key'])

    def test_timeout_preserves_pending(self):
        self.mode = 'hang'
        self.assertNotEqual(self.submit()['status'], 'accepted')
        self.assertEqual(len(self.outbox()), 1)
        self.hanging[0].abort()
        self.page.wait_for_timeout(50)

    def test_storage_denial_reuses_key_within_page(self):
        self.page.evaluate("""k => {
          let get=Storage.prototype.getItem, set=Storage.prototype.setItem;
          Storage.prototype.getItem=function(key){if(key===k)throw new Error('denied'); return get.call(this,key)};
          Storage.prototype.setItem=function(key,v){if(key===k)throw new Error('denied'); return set.call(this,key,v)};
        }""", KEY)
        self.mode = 'lost'
        self.submit()
        first = self.requests[0]['idempotency_key']
        self.mode = 'accepted'
        self.assertEqual(self.submit()['status'], 'accepted')
        self.assertEqual(self.requests[1]['idempotency_key'], first)

    def test_capacity_does_not_evict_pending_server_items(self):
        self.mode = 'lost'
        for i in range(3):
            self.page.evaluate("i => animaLead.submitChat({name:'Synthetic '+i, contact:'probe@example.invalid', consent:true, source_page:'/'})", i)
        before = self.outbox()
        result = self.submit()
        self.assertEqual(result['reason'], 'pending_limit')
        self.assertEqual(self.outbox(), before)
        self.assertEqual(len(self.requests), 3)

if __name__ == '__main__':
    unittest.main()
