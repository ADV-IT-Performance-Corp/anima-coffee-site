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

  function fireAccepted(sourcePage, leadId) {
    try { if (window.animaTrackLead) window.animaTrackLead(sourcePage, leadId); } catch (e) {}
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
      fireAccepted(data.source_page, body.lead_id);
      form.reset();
      setStatus(status, T.sent, "ok");
    }).catch(function () {
      setStatus(status, T.err, "err");
    });
  }

  function handle(form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }

      var status = form.querySelector(".lf-status");
      var hp = form.querySelector('input[name="company_url"]');
      if (hp && (hp.value || "").trim()) {
        // Honeypot tripped — silently drop, don't tell the bot anything useful.
        form.reset();
        setStatus(status, T.sent, "ok");
        return;
      }

      var raw = {};
      Array.prototype.forEach.call(form.querySelectorAll("input,textarea"), function (f) {
        if (f.name && f.name !== "company_url") raw[f.name] = (f.value || "").trim();
      });
      var utm = captureUtm();
      var data = {
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

      var endpoint = (form.getAttribute("data-endpoint") || "").trim();
      if (!endpoint) { showFallbackContact(status); return; }

      submitLead(form, status, data, endpoint);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("form.lead-form"), handle);
  });
})();
