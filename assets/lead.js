/* Anima Volitiva — lead capture -> first-party API (DC-3, per
 * docs/specs/spec-anima-aeo-client-delivery-cutover-2026-08-21.md §7 in
 * ADV-Strategy-Core).
 *
 * POSTs JSON to the URL in the form's data-endpoint attribute. No endpoint
 * URL is ever hardcoded here — data-endpoint is set per-deployment once the
 * DC-2 backend exists.
 *
 * The lead_accepted analytics conversion fires ONLY after the API answers
 * HTTP 200 with a lead_id in the body — never on a mailto: click, never
 * speculatively. When data-endpoint is empty (no backend wired yet) the form
 * does NOT fabricate a conversion and does NOT auto-open a mail client: it
 * points the visitor at the direct phone/email contact block already on the
 * page as the fallback CTA.
 *
 * The hidden honeypot field (name="company_url") is injected on every
 * lead-form page by tools/add_lead_honeypot.py. If it's filled in, the
 * submit is silently dropped (spam bots fill every field; real visitors
 * never see this one — it's off-screen via .lf-hp in style.css).
 *
 * WebMCP (W1, 2026-09-14): a browser agent submits this same form with
 * `SubmitEvent.agentInvoked` set. That path runs the SAME validation and
 * SAME submit call as a human, then answers with `e.respondWith(promise)`
 * instead of writing to the DOM — see handleAgent(). Human behaviour above
 * is byte-for-byte unchanged.
 *
 * Roistat delivery (W2, 2026-09-14): exactly one delivery path runs per
 * submit, chosen in this order — (1) data-endpoint set -> the POST path
 * above, unchanged; (2) else Roistat ready (window.roistatGoal.reach is a
 * function, set by assets/analytics.js once its counter script has
 * loaded) -> one roistatGoal.reach() call, whose Roistat->AmoCRM
 * integration opens the CRM deal, no POST, and a client-generated lead_id
 * is used for animaTrackLead/respondWith; (3) else -> today's fallback
 * contact block / not_connected. If the counter is configured but blocked
 * (ad blocker, network failure) window.roistatGoal never appears, so this
 * falls through to (3) on its own — no explicit "blocked" detection is
 * needed, and success is never claimed without an actual reach() call.
 */
(function () {
  var uk = (document.documentElement.lang || "en").toLowerCase().indexOf("uk") === 0;
  var T = uk
    ? {
        sending: "Надсилаємо…",
        sent: "Дякуємо! Ми зв'яжемося з вами протягом одного робочого дня.",
        err: "Не вдалося надіслати через сайт. Скористайтесь контактами нижче — ми відповідаємо швидко.",
        noBackend: "Форма ще не підключена до нашої системи. Зв'яжіться з нами напряму — ми відповідаємо швидко:"
      }
    : {
        sending: "Sending…",
        sent: "Thank you. We'll reply within one business day.",
        err: "Could not send via the site. Please use the contacts below — we reply fast.",
        noBackend: "This form isn't wired to our system yet. Reach us directly — we reply fast:"
      };

  // Published contact facts (CLAUDE.md "Contacts & business info", canonical
  // — mirrored here as constants rather than scraped from the DOM so the
  // agent-facing not_connected result is a stable, machine-readable
  // contract independent of page layout).
  var CONTACT = {
    phone: "+38 (073) 873 01 45",
    email: "animacoffeeco@gmail.com",
    telegram: "https://t.me/Animavolitiva"
  };

  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid"];
  var UTM_STORE_KEY = "anima_utm_v1";

  // Merge UTM/gclid seen on any page this session with whatever is on the
  // current URL, so attribution survives a click-through to a second page
  // before the visitor actually submits the form.
  function captureUtm() {
    var out = {};
    try {
      var stored = JSON.parse(sessionStorage.getItem(UTM_STORE_KEY) || "{}");
      for (var k in stored) { if (Object.prototype.hasOwnProperty.call(stored, k)) out[k] = stored[k]; }
    } catch (e) {}
    try {
      var params = new URLSearchParams(location.search);
      var any = false;
      UTM_KEYS.forEach(function (k) {
        var v = params.get(k);
        if (v) { out[k] = v; any = true; }
      });
      if (any) sessionStorage.setItem(UTM_STORE_KEY, JSON.stringify(out));
    } catch (e) {}
    return out;
  }

  function setStatus(el, msg, cls) {
    el.textContent = msg;
    el.className = "lf-status" + (cls ? " " + cls : "");
  }

  // No backend configured: never fake a conversion, never auto-navigate to
  // mailto. Surface the site's own contact block (tel/mailto links, already
  // rendered in the page footer) as the fallback CTA.
  function showFallbackContact(status) {
    var block = document.querySelector(".contact-block");
    var tel = block && block.querySelector('a[href^="tel:"]');
    var mail = block && block.querySelector('a[href^="mailto:"]');

    status.textContent = "";
    status.appendChild(document.createTextNode(T.noBackend + " "));
    if (tel) {
      status.appendChild(tel.cloneNode(true));
      if (mail) status.appendChild(document.createTextNode(" · "));
    }
    if (mail) status.appendChild(mail.cloneNode(true));
    status.className = "lf-status err";

    if (block) {
      block.classList.add("lf-highlight");
      block.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(function () { block.classList.remove("lf-highlight"); }, 2600);
    }
  }

  function fireAccepted(sourcePage, leadId, origin) {
    try { if (window.animaTrackLead) window.animaTrackLead(sourcePage, leadId, origin); } catch (e) {}
  }

  // Double-submit guard: disables the submit button AND marks the form
  // "sending" (checked at the top of the submit handler, since a disabled
  // button can still be re-triggered by a keyboard Enter on some browsers).
  function setSending(form, sending) {
    var btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = sending;
    form.dataset.lfSending = sending ? "1" : "";
  }

  function roistatReady() {
    return !!(window.roistatGoal && typeof window.roistatGoal.reach === "function");
  }

  // No phone-vs-email validation exists elsewhere in this file (the
  // "contact" field is plain free text) — an "@" is the same minimal
  // heuristic a human would use to tell the two apart.
  function splitContact(contact) {
    return contact.indexOf("@") !== -1 ? { email: contact } : { phone: contact };
  }

  // Roistat has no test mode for goals (see spec) — a "ТЕСТ"/"TEST" marker
  // in the name or details is the owner's own convention for spotting and
  // deleting test deals in the CRM.
  var TEST_MARKER_RE = /ТЕСТ|TEST/i;
  function isTestLead(data) {
    return TEST_MARKER_RE.test(data.name) || TEST_MARKER_RE.test(data.details);
  }

  function buildLeadName(data, origin) {
    var leadName = "Заявка з " + location.hostname;
    if (origin === "agent") leadName += " (AI-агент)";
    if (isTestLead(data)) leadName = "ТЕСТ — " + leadName;
    return leadName;
  }

  function genLeadId() {
    return "rst_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 10);
  }

  // Calls roistatGoal.reach() exactly once and returns the client-generated
  // lead_id, or null if reach() itself threw (never claim success without a
  // real reach call — caller falls through to the fallback path on null).
  function reachRoistat(data, origin) {
    var leadId = genLeadId();
    var payload = {
      leadName: buildLeadName(data, origin),
      text: data.details,
      name: data.name,
      fields: {
        company: data.company,
        city: data.city,
        machines: data.machines,
        details: data.details,
        source_page: data.source_page,
        lead_origin: origin,
        lead_id: leadId
      }
    };
    var contact = splitContact(data.contact);
    if (contact.email) { payload.email = contact.email; } else { payload.phone = contact.phone; }
    try {
      window.roistatGoal.reach(payload);
    } catch (e) {
      return null;
    }
    return leadId;
  }

  function submitLead(form, status, data, endpoint) {
    setStatus(status, T.sending, "");
    fetch(endpoint, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      if (r.status !== 200) { throw new Error("lead_not_accepted"); }
      return r.json();
    }).then(function (body) {
      if (!body || !body.lead_id) { throw new Error("no_lead_id"); }
      fireAccepted(data.source_page, body.lead_id, "human");
      form.reset();
      setStatus(status, T.sent, "ok");
    }).catch(function () {
      setStatus(status, T.err, "err");
    }).then(function () {
      setSending(form, false);
    });
  }

  // Agent path (WebMCP): same POST as submitLead, but resolves a structured
  // result for e.respondWith() instead of writing to the DOM.
  function submitLeadAgent(form, data, endpoint) {
    return fetch(endpoint, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      if (r.status !== 200) { throw new Error("lead_not_accepted"); }
      return r.json();
    }).then(function (body) {
      if (!body || !body.lead_id) { throw new Error("no_lead_id"); }
      fireAccepted(data.source_page, body.lead_id, "agent");
      form.reset();
      return { status: "accepted", leadId: body.lead_id };
    }).catch(function () {
      return { status: "error", message: T.err };
    }).then(function (result) {
      setSending(form, false);
      return result;
    });
  }

  function notConnectedResult() {
    return {
      status: "not_connected",
      message: T.noBackend,
      phone: CONTACT.phone,
      email: CONTACT.email,
      telegram: CONTACT.telegram
    };
  }

  function invalidResult(form) {
    var fields = [];
    Array.prototype.forEach.call(form.querySelectorAll(":invalid"), function (f) {
      if (f.name && f.name !== "company_url") fields.push(f.name);
    });
    return { status: "invalid", message: T.err, fields: fields };
  }

  function collectData(form) {
    var raw = {};
    Array.prototype.forEach.call(form.querySelectorAll("input,textarea"), function (f) {
      if (f.name && f.name !== "company_url") raw[f.name] = (f.value || "").trim();
    });
    var utm = captureUtm();
    return {
      name: raw.name || "",
      company: raw.business || "",
      city: raw.city || "",
      machines: raw.machines || "",
      contact: raw.contact || "",
      details: raw.details || raw.message || "",
      source_page: location.pathname,
      referrer: document.referrer || "",
      utm_source: utm.utm_source || "",
      utm_medium: utm.utm_medium || "",
      utm_campaign: utm.utm_campaign || "",
      utm_term: utm.utm_term || "",
      utm_content: utm.utm_content || "",
      gclid: utm.gclid || ""
    };
  }

  function handle(form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var isAgent = !!e.agentInvoked;

      if (!form.checkValidity()) {
        if (isAgent) { e.respondWith(Promise.resolve(invalidResult(form))); return; }
        form.reportValidity();
        return;
      }

      var status = form.querySelector(".lf-status");
      var hp = form.querySelector('input[name="company_url"]');
      if (hp && (hp.value || "").trim()) {
        // Honeypot tripped — silently drop, don't tell the bot anything useful
        // (a real agent never sees or fills this hidden field).
        form.reset();
        if (isAgent) { e.respondWith(Promise.resolve({ status: "error", message: T.err })); return; }
        setStatus(status, T.sent, "ok");
        return;
      }

      // Double-submit guard: a submit already in flight (button disabled by
      // a prior submit of THIS form) is ignored outright — covers a
      // keyboard Enter re-submit racing a disabled-but-still-focused button.
      if (form.dataset.lfSending === "1") { return; }

      var data = collectData(form);
      var endpoint = (form.getAttribute("data-endpoint") || "").trim();

      // (1) data-endpoint set -> POST path, unchanged.
      if (endpoint) {
        setSending(form, true);
        if (isAgent) {
          e.respondWith(submitLeadAgent(form, data, endpoint));
          return;
        }
        submitLead(form, status, data, endpoint);
        return;
      }

      // (2) else Roistat ready -> one reach() call, no POST.
      if (roistatReady()) {
        setSending(form, true);
        var origin = isAgent ? "agent" : "human";
        var leadId = reachRoistat(data, origin);
        setSending(form, false);
        if (leadId) {
          fireAccepted(data.source_page, leadId, origin);
          if (isAgent) {
            e.respondWith(Promise.resolve({ status: "accepted", leadId: leadId }));
            // Deferred to the next tick: resetting the form synchronously,
            // in the same turn as respondWith(), was observed to break the
            // WebMCP polyfill's resolution of the returned promise (it
            // never delivered the result back to the caller) — see W2 spec.
            setTimeout(function () { form.reset(); }, 0);
            return;
          }
          form.reset();
          setStatus(status, T.sent, "ok");
          return;
        }
        // reach() threw (e.g. blocked mid-call) -> fall through to (3),
        // never claim success without a real reach call.
      }

      // (3) fallback — today's behaviour.
      if (isAgent) { e.respondWith(Promise.resolve(notConnectedResult())); return; }
      showFallbackContact(status);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("form.lead-form"), handle);
  });
})();
