/* Anima Volitiva — lead capture -> first-party API (DC-3, per
 * docs/specs/spec-anima-aeo-client-delivery-cutover-2026-08-21.md §7 in
 * ADV-Strategy-Core).
 *
 * With data-endpoint set to the Anima intake (/api/anima/lead) every channel
 * is mapped to its schema with a stable idempotency key; a validated response
 * confirms server storage, not downstream delivery. Otherwise: POSTs JSON to the URL in the form's data-endpoint attribute. No endpoint
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
 * is used for animaTrackLead/respondWith; (2b) configured
 * (window.roistatProjectId set) but not ready yet -> wait up to ~4s
 * (polling every 100ms) for the async counter script to define
 * roistatGoal, keeping the button disabled / the respondWith promise
 * pending for agents, then deliver via (2) or fall through; (3) else ->
 * today's fallback contact block / not_connected. If the counter is
 * configured but blocked (ad blocker, network failure) window.roistatGoal
 * never appears, so the (2b) wait times out and this falls through to (3)
 * on its own — no explicit "blocked" detection is needed, and success is
 * never claimed without an actual reach() call.
 *
 * Fast-follows (2026-09-14, same day): the agent-path sending guard now
 * stays held until the deferred form.reset() actually runs, so a second
 * executeTool() racing that window can't fire a second reach() for the
 * same submit; and assets/analytics.js wraps the Roistat counter IIFE in
 * try/catch so a failure there can never prevent window.animaTrackLead
 * from being defined.
 *
 * Outbox (PR #87, main): a lead that could not be handed to Roistat is kept
 * in localStorage (anima_lead_outbox_v1, 7-day TTL, cap 3) and re-delivered
 * automatically on a later page view via flushOutbox() once Roistat becomes
 * available. One-tap email + Telegram controls let the visitor send the
 * same details themselves without waiting for that re-delivery.
 *
 * Honest-delivery fallback (2026-10-31, v2 — re-cut on top of the outbox):
 * the one-tap controls are <button> elements whose destination URL lives
 * only in a closure, never in a DOM attribute — assets/analytics.js runs
 * Metrica with trackLinks: true, and privacy.html promises those tools see
 * nothing but the anonymous lead_accepted signal; a real <a href> with the
 * visitor's name/phone/details in the query string would leak that. When
 * Roistat IS configured (window.roistatProjectId set) but delivery could
 * not be attempted (the (2b) wait timed out, or reach() itself threw), the
 * copy is T.deliveryFailed instead of the misleading T.noBackend, and the
 * lead is still kept in the outbox for automatic re-send (saveOutbox is
 * unconditional on every path that reaches here) — never T.sent, never
 * lead_accepted, since nothing was actually delivered yet.
 * window.animaTrackLead() takes a 4th `deliveryStatus` argument
 * ("confirmed" | "unconfirmed") so lead_accepted can tell a first-party
 * POST apart from a fire-and-forget Roistat reach() — including the
 * reach() that flushOutbox() fires on a later page view.
 */
(function () {
  var uk = (document.documentElement.lang || "en").toLowerCase().indexOf("uk") === 0;
  var T = uk
    ? {
        sending: "Надсилаємо…",
        sent: "Дякуємо! Заявку отримано. Ми зв'яжемося з вами.",
        err: "Не вдалося надіслати через сайт. Скористайтесь контактами нижче — ми відповідаємо швидко.",
        noBackend: "Форма ще не підключена до нашої системи. Зв'яжіться з нами напряму — ми відповідаємо швидко:",
        deliveryFailed: "Не вдалося підтвердити, що заявку надіслано. Напишіть нам напряму, щоб вона не загубилася:",
        oneTap: "Надіслати ці дані в один дотик:",
        pendingFull: "На цьому пристрої вже є три заявки, що очікують надсилання. Скористайтесь прямим контактом нижче:",
        viaEmail: "Email",
        viaTelegram: "Telegram"
      }
    : {
        sending: "Sending…",
        sent: "Thank you! Your request has been received. We'll be in touch.",
        err: "Could not send via the site. Please use the contacts below — we reply fast.",
        noBackend: "This form isn't wired to our system yet. Reach us directly — we reply fast:",
        deliveryFailed: "We couldn't confirm your request went through. Please contact us directly so it doesn't get lost:",
        oneTap: "Send these details in one tap:",
        pendingFull: "There are already three pending requests on this device. Please use a direct contact below:",
        viaEmail: "Email",
        viaTelegram: "Telegram"
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

  // Accepted-lead confirmation (2026-10-25): visitors never saw the old
  // one-line "thank you", which sat at the bottom edge of the viewport under
  // the sticky CTA bar. Render it as a panel and scroll it clear of the bar.
  function showSent(status) {
    setStatus(status, T.sent, "ok");
    scrollStatusIntoView(status);
  }

  // Brings `status` clear of the sticky nav and the sticky CTA bar. Shared
  // by showSent and the fallback/delivery-failed renderers below. An
  // explicit window.scrollBy, because scrollIntoView() did not move the
  // page at all at 375px (measured 2026-10-25).
  function scrollStatusIntoView(status) {
    status.setAttribute("tabindex", "-1");
    try { status.focus({ preventScroll: true }); } catch (e) {}
    var r = status.getBoundingClientRect();
    var bar = document.getElementById("sticky-cta");
    var limit = (bar ? bar.getBoundingClientRect().top : window.innerHeight) - 16;
    // The top edge sits below the sticky nav (and .ppc-nav on PPC pages),
    // which stays pinned over the page while scrolling (codex P2).
    var top = 16;
    Array.prototype.forEach.call(document.querySelectorAll("nav, .ppc-nav"), function (n) {
      var nr = n.getBoundingClientRect();
      if (nr.top <= 0 && nr.bottom > 0) top = Math.max(top, nr.bottom + 16);
    });
    var dy = r.top < top ? r.top - top : (r.bottom > limit ? r.bottom - limit : 0);
    if (dy) window.scrollBy({ top: dy, behavior: "smooth" });
  }

  function highlightContactBlock(block, noScroll) {
    if (!block) return;
    block.classList.add("lf-highlight");
    if (!noScroll) block.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(function () { block.classList.remove("lf-highlight"); }, 2600);
  }

  // Clones the page's own tel/mailto contact links (never hardcoded here)
  // into `status`. Shared by the never-configured and delivery-failed
  // renderers.
  function cloneContactLinks(status, block) {
    var tel = block && block.querySelector('a[href^="tel:"]');
    var mail = block && block.querySelector('a[href^="mailto:"]');
    if (tel) {
      status.appendChild(tel.cloneNode(true));
      if (mail) status.appendChild(document.createTextNode(" · "));
    }
    if (mail) status.appendChild(mail.cloneNode(true));
  }

  function fireAccepted(sourcePage, leadId, origin, deliveryStatus, data) {
    try {
      if (window.animaTrackLead) {
        window.animaTrackLead(sourcePage, leadId, origin, deliveryStatus, {
          lead_source: leadSourceFor(data, origin),
          ai_source: (data && data.ai_source) || ""
        });
      }
    } catch (e) {}
  }

  // End-to-end source label sent to Roistat (and GA4/GTM): which channel the
  // lead came through. chatkit = the on-site chat; webmcp = a browser agent
  // submitted the form, or a WebMCP prefill tool tagged the visit
  // (utm_source=ai-agent / utm_medium=webmcp, see assets/webmcp.js) and the
  // visitor pressed submit; form = the plain form. The traffic origin (which
  // AI answer engine sent the visitor) is the separate ai_source field.
  function leadSourceFor(data, origin) {
    if (origin === "chatkit") return "chatkit";
    if (origin === "agent") return "webmcp";
    if (data && (data.utm_medium === "webmcp" || data.utm_source === "ai-agent")) return "webmcp";
    return "form";
  }

  // AI answer-engine the visit came from (chatgpt, perplexity, gemini, ...),
  // detected once per session by assets/analytics.js from the referrer host or
  // utm_source. "" when unknown. Google AI Overviews clicks arrive as plain
  // google.com organic and cannot be told apart client-side.
  function aiSource() {
    try { return (window.animaAttribution && window.animaAttribution.aiSource()) || ""; } catch (e) { return ""; }
  }

  // Backup lead channel (no server needed). A lead that could not be handed to
  // Roistat is kept in this browser (persist-first, 7 days, max 3) and is
  // (a) offered as one-tap email/Telegram controls so the visitor does not
  // retype it, and (b) re-delivered through Roistat on the next page view
  // where it is available. Never shown as "sent" until Roistat really takes it.
  var OUTBOX_KEY = "anima_lead_outbox_v1";
  var OUTBOX_TTL_MS = 7 * 24 * 3600 * 1000;
  // In-memory mirror so a server-bound item still retries within this page
  // view when localStorage is denied.
  var memoryOutbox = [];
  var outboxStorageFailed = false;
  function readOutbox() {
    var all = memoryOutbox;
    try {
      if (!outboxStorageFailed) all = JSON.parse(localStorage.getItem(OUTBOX_KEY) || "[]");
    } catch (e) { outboxStorageFailed = true; }
    var now = Date.now();
    return Array.isArray(all) ? all.filter(function (x) {
      return x && x.data && Number.isFinite(x.ts) && x.ts <= now && now - x.ts < OUTBOX_TTL_MS;
    }) : [];
  }
  function writeOutbox(list) {
    memoryOutbox = list.slice(-3);
    try {
      if (list.length) localStorage.setItem(OUTBOX_KEY, JSON.stringify(list.slice(-3)));
      else localStorage.removeItem(OUTBOX_KEY);
    } catch (e) { outboxStorageFailed = true; }
  }
  function genOutboxId() {
    return "ob_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8);
  }
  function saveOutbox(data, origin) {
    try {
      if (!data || !data.contact) return null;
      var id = genOutboxId();
      var list = readOutbox();
      list.push({ id: id, ts: Date.now(), origin: origin || "human", data: data });
      writeOutbox(list);
      return id;
    } catch (e) { return null; }
  }
  function removeOutboxEntry(id) {
    if (!id) return;
    try { writeOutbox(readOutbox().filter(function (x) { return x.id !== id; })); } catch (e) {}
  }

  // Re-submit dedupe (v2 round 2, P2): a re-submit from the SAME form/chat
  // instance supersedes that instance's own earlier outbox entry instead of
  // stacking a duplicate -- otherwise a later flushOutbox() page view would
  // send both and fire a second lead_accepted for one visitor action. Scoped
  // to one page-load's WeakMap, so entries from earlier page views (which
  // this instance never tracked) are never touched, and flushOutbox() itself
  // is unchanged. `key` is the DOM form element for lead forms, or the chat
  // widget's own form element for ChatKit.
  var OUTBOX_PENDING = new WeakMap();
  function supersedeOutboxFor(key, data, origin) {
    var prev = OUTBOX_PENDING.get(key);
    if (prev) removeOutboxEntry(prev);
    var id = saveOutbox(data, origin);
    if (id) OUTBOX_PENDING.set(key, id); else OUTBOX_PENDING.delete(key);
  }
  function clearOutboxFor(key) {
    var prev = OUTBOX_PENDING.get(key);
    if (prev) { removeOutboxEntry(prev); OUTBOX_PENDING.delete(key); }
  }
  function leadText(data) {
    var rows = [
      ["Name", data.name], ["Business", data.company], ["City", data.city],
      ["Machines", data.machines], ["Contact", data.contact], ["Details", data.details]
    ];
    return rows.filter(function (r) { return r[1]; })
      .map(function (r) { return r[0] + ": " + r[1]; }).join("\n");
  }
  function flushOutbox() {
    try {
      var list = readOutbox();
      // Purge expired PII even if no delivery channel is configured.
      writeOutbox(list);
      var endpoint = intakeUrl(chatEndpoint());
      if (endpoint) {
        list.filter(function (x) {
          return x.endpoint === endpoint && x.id && x.data.consent === true;
        }).forEach(sendIntake);
        return;
      }
      if (!list.length || !roistatConfigured()) return;
      waitForRoistat().then(function (ready) {
        if (!ready) return;
        var left = [];
        readOutbox().forEach(function (item) {
          // A server-bound item may already be committed: never hand it to
          // Roistat when endpoint config is removed or changes.
          if (item.endpoint) { left.push(item); return; }
          var id = reachRoistat(item.data, item.origin);
          if (id) fireAccepted(item.data.source_page, id, item.origin, "unconfirmed", item.data); else left.push(item);
        });
        writeOutbox(left);
      });
    } catch (e) {}
  }

  // Cuts `str` to at most `maxLen` UTF-16 code units without splitting a
  // surrogate pair -- a naive slice() can leave a lone high surrogate at the
  // cut point, which encodeURIComponent() then throws a URIError on.
  function safeTruncate(str, maxLen) {
    if (maxLen <= 0) return "";
    if (str.length <= maxLen) return str;
    var cut = str.slice(0, maxLen);
    var lastCode = cut.charCodeAt(cut.length - 1);
    if (lastCode >= 0xd800 && lastCode <= 0xdbff) cut = cut.slice(0, -1);
    return cut;
  }

  // Shared bound for both one-tap URLs (mailto has no spec-mandated cap;
  // main's pre-existing Telegram link had no bound at all -- this applies
  // one honest bound to both rather than leave either unbounded).
  var ONE_TAP_MAX_LEN = 1800;

  function mailtoAddress(mailLink) {
    var href = (mailLink.getAttribute("href") || "").replace(/^mailto:/i, "");
    var q = href.indexOf("?");
    return q === -1 ? href : href.slice(0, q);
  }

  // Builds the mailto: or Telegram URL for one channel, bounded to
  // ONE_TAP_MAX_LEN by truncating `details` in 200-char steps (never
  // splitting a surrogate pair -- safeTruncate). Returns null when no URL
  // within bound can be built at all (a lone surrogate anywhere else in the
  // fields makes encodeURIComponent throw, caught here and never left to
  // propagate out of the submit handler; an oversized non-details field can
  // make the bound unreachable even with details truncated to empty).
  function buildChannelUrl(kind, address, data) {
    try {
      var details = data.details || "";
      for (;;) {
        var text = leadText({
          name: data.name, company: data.company, city: data.city,
          machines: data.machines, contact: data.contact, details: details
        });
        var href = kind === "email"
          ? "mailto:" + address + "?subject=" + encodeURIComponent("Заявка з " + location.hostname) + "&body=" + encodeURIComponent(text)
          : address + "?text=" + encodeURIComponent(text);
        if (href.length <= ONE_TAP_MAX_LEN) return href;
        if (!details) return null;
        details = safeTruncate(details, Math.max(0, details.length - 200));
      }
    } catch (e) {
      return null;
    }
  }

  // Builds one <button type="button"> per working channel. The URL lives
  // only in this closure -- never written to href/data-*/title, so no
  // click-tracking listener can read it. On click: mailto via
  // window.location.href; Telegram via window.open(url, "_blank") (NOT
  // "noopener" -- that makes window.open() return null even when the
  // popup opens in spec-compliant browsers, which made the old
  // if-(!w)-fallback always fire and navigate the visitor's own tab away).
  // w.opener is nulled manually once we have the real window reference
  // instead. window.location.href is only the actual blocked-popup
  // fallback (window.open returning null for real). Neither ever
  // auto-opens on render, and neither
  // may submit the form (this is a plain <button>, no form submission is
  // wired to it at all). window.__LEAD_DRAFT_CAPTURE(channel, url) is a
  // harness-only test hook (window.__ROISTAT_TEST_WAIT_MS convention).
  function buildOneTapButton(label, channel, url) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lf-draft-btn";
    btn.textContent = label;
    btn.addEventListener("click", function () {
      if (typeof window.__LEAD_DRAFT_CAPTURE === "function") {
        try { window.__LEAD_DRAFT_CAPTURE(channel, url); } catch (e) {}
      }
      if (channel === "telegram") {
        var w = window.open(url, "_blank");
        if (w) { try { w.opener = null; } catch (e) {} } else { window.location.href = url; }
      } else {
        window.location.href = url;
      }
    });
    return btn;
  }

  // Returns an array of 0-2 one-tap buttons (email, Telegram), each only
  // included when its URL could actually be built within bound.
  function buildOneTapControls(data) {
    var controls = [];
    var block = document.querySelector(".contact-block");
    var mail = block && block.querySelector('a[href^="mailto:"]');
    var address = mail && mailtoAddress(mail);
    if (address) {
      var mailUrl = buildChannelUrl("email", address, data);
      if (mailUrl) controls.push(buildOneTapButton(T.viaEmail, "email", mailUrl));
    }
    var tgUrl = buildChannelUrl("telegram", CONTACT.telegram, data);
    if (tgUrl) controls.push(buildOneTapButton(T.viaTelegram, "telegram", tgUrl));
    return controls;
  }

  // Shared renderer for the never-configured (3) and configured-but-failed
  // (2/2b) cases. `deliveryFailed` picks the copy: T.noBackend (unchanged,
  // case 3) vs T.deliveryFailed (case 2/2b, honest about the outbox) --
  // downgraded to T.err if NEITHER one-tap control could be built, since
  // deliveryFailed's wording promises a path that doesn't exist without at
  // least one working control.
  function renderFallback(status, data, deliveryFailed, override) {
    var controls = buildOneTapControls(data);
    var message = override || (deliveryFailed ? (controls.length ? T.deliveryFailed : T.err) : T.noBackend);
    var block = document.querySelector(".contact-block");
    status.textContent = "";
    status.appendChild(document.createTextNode(message + " "));
    cloneContactLinks(status, block);
    if (controls.length) {
      status.appendChild(document.createTextNode(" "));
      status.appendChild(document.createTextNode(T.oneTap + " "));
      controls.forEach(function (btn, i) {
        if (i) status.appendChild(document.createTextNode(" · "));
        status.appendChild(btn);
      });
    }
    status.className = "lf-status err";
    if (deliveryFailed) {
      // The contact block sits at the page bottom: scrolling to it pushed
      // the one-tap controls off-screen above the viewport on phones
      // (375x667), so keep the status in view instead and only flash the
      // block.
      highlightContactBlock(block, true);
      scrollStatusIntoView(status);
    } else {
      highlightContactBlock(block);
    }
  }

  // No backend configured at all: never fake a conversion, never auto-open
  // a channel. Unchanged copy (T.noBackend); the one-tap controls are the
  // only thing that changed here (safe buttons replace the old real-href
  // anchors).
  function showFallbackContact(status, data) {
    renderFallback(status, data, false);
  }

  // Roistat IS configured but delivery could not be attempted (the (2b)
  // wait timed out, the device went offline, or reach() itself threw).
  // T.noBackend would be false here (a backend IS configured), so this
  // shows the honest deliveryFailed copy, keeps the visitor's typed values
  // (no form.reset()), and the lead stays in the outbox for automatic
  // re-send. Never fires lead_accepted.
  function showDeliveryFailed(status, data, override) {
    renderFallback(status, data, true, override);
  }

  // Double-submit guard: disables the submit button AND marks the form
  // "sending" (checked at the top of the submit handler, since a disabled
  // button can still be re-triggered by a keyboard Enter on some browsers).
  function setSending(form, sending) {
    var btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = sending;
    form.dataset.lfSending = sending ? "1" : "";
  }

  // roistatGoal.reach() is a fire-and-forget beacon call with no delivery
  // confirmation (same as GA4/Metrica elsewhere in this codebase) — a
  // network failure AFTER this check still can't be detected client-side,
  // which is inherent to the no-backend design this slice implements
  // (Codex round-1 review: known, accepted residual risk). The
  // navigator.onLine check below catches the one failure mode that IS
  // detectable up front — an offline device — so at least that case falls
  // through to the honest contact-fallback instead of a false "accepted".
  function roistatReady() {
    if (typeof navigator !== "undefined" && navigator.onLine === false) return false;
    return !!(window.roistatGoal && typeof window.roistatGoal.reach === "function");
  }

  // Fast-agent / slow-connection race (Codex fast-follow, 2026-09-14):
  // ROISTAT_PROJECT_ID is set but the counter script (loaded async by
  // assets/analytics.js) hasn't defined window.roistatGoal yet at submit
  // time. Poll briefly instead of falling straight through to (3) so a
  // submit that arrives a beat before the counter finishes loading still
  // gets delivered. ~4s cap, 100ms interval == ~40 checks.
  // window.__ROISTAT_TEST_WAIT_MS lets the headless test harness shrink
  // the cap so timeout-path tests don't have to burn a real 4s; read once
  // at load (never set outside webmcp/run_headless_check.js).
  var ROISTAT_WAIT_MS = (typeof window !== "undefined" && window.__ROISTAT_TEST_WAIT_MS) || 4000;
  var ROISTAT_POLL_MS = 100;
  function waitForRoistat() {
    if (roistatReady()) return Promise.resolve(true);
    if (typeof navigator !== "undefined" && navigator.onLine === false) return Promise.resolve(false);
    return new Promise(function (resolve) {
      // Codex round-2 fix: measure elapsed wall-clock time via Date.now(),
      // not a fixed-per-tick counter — a backgrounded tab throttles
      // setInterval callbacks (Chrome: as infrequently as ~1/min), so
      // counting "ticks * 100ms" as if each tick were punctual could
      // stretch this well past the intended ~4s cap, leaving the button
      // disabled / the respondWith promise pending far longer than meant.
      var deadline = Date.now() + ROISTAT_WAIT_MS;
      var timer = setInterval(function () {
        if (roistatReady()) {
          clearInterval(timer);
          resolve(true);
        } else if (Date.now() >= deadline) {
          clearInterval(timer);
          resolve(false);
        }
      }, ROISTAT_POLL_MS);
    });
  }

  // window.roistatProjectId is set synchronously by assets/analytics.js's
  // counter-init IIFE as soon as ROISTAT_PROJECT_ID is non-empty — before
  // the counter script itself has finished loading async. That makes it a
  // reliable "Roistat is configured" signal independent of whether
  // window.roistatGoal exists yet, which is what tells waitForRoistat()
  // apart from "never configured, go straight to fallback".
  function roistatConfigured() {
    return typeof window.roistatProjectId !== "undefined" && !!window.roistatProjectId;
  }

  // window.__LEAD_RESET_DELAY_MS lets the headless test harness widen the
  // deferred-reset window below so the duplicate-submit race is reliably
  // exercisable instead of depending on real event-loop timing; read once
  // at load (never set outside webmcp/run_headless_check.js).
  var LEAD_RESET_DELAY_MS = (typeof window !== "undefined" && window.__LEAD_RESET_DELAY_MS) || 0;

  // Agent delivery: calls reach() once and resolves the respondWith result.
  // Keeps the sending guard held until the deferred form.reset() actually
  // runs (Codex fast-follow, 2026-09-14) — releasing it right after
  // respondWith() let a second executeTool() racing that window fire a
  // second reach() for the same submit (double AmoCRM deal).
  function deliverRoistatAgent(form, data, origin) {
    var leadId = reachRoistat(data, origin);
    if (leadId) {
      fireAccepted(data.source_page, leadId, origin, "unconfirmed", data);
      clearOutboxFor(form);
      // Deferred to the next tick: resetting the form synchronously, in the
      // same turn as respondWith(), was observed to break the WebMCP
      // polyfill's resolution of the returned promise (it never delivered
      // the result back to the caller) — see W2 spec. setSending(false)
      // moves here too so the double-submit guard covers this whole window.
      setTimeout(function () {
        form.reset();
        setSending(form, false);
      }, LEAD_RESET_DELAY_MS);
      return { status: "accepted", leadId: leadId };
    }
    // reach() threw (e.g. blocked mid-call) -> never claim success; keep
    // the lead for automatic re-delivery. A re-submit of THIS form
    // supersedes its own earlier outbox entry instead of stacking one.
    setSending(form, false);
    supersedeOutboxFor(form, data, origin);
    return notConnectedResult();
  }

  // Human delivery: calls reach() once and updates the DOM synchronously
  // (no deferred reset needed — there's no respondWith() promise to race).
  function deliverRoistatHuman(form, status, data, origin) {
    var leadId = reachRoistat(data, origin);
    setSending(form, false);
    if (leadId) {
      fireAccepted(data.source_page, leadId, origin, "unconfirmed", data);
      clearOutboxFor(form);
      form.reset();
      showSent(status);
      return;
    }
    // reach() threw mid-call -- Roistat IS configured, so this is the
    // delivery-failed case, not the never-configured one. Supersedes this
    // form's own earlier outbox entry (fix 2).
    supersedeOutboxFor(form, data, origin);
    showDeliveryFailed(status, data);
  }

  // No phone-vs-email validation exists elsewhere in this file (the
  // "contact" field is plain free text) — an "@" is the same minimal
  // heuristic a human would use to tell the two apart.
  function splitContact(contact) {
    return contact.indexOf("@") !== -1 ? { email: contact } : { phone: contact };
  }

  // Roistat has no test mode for goals (see spec) — a "ТЕСТ"/"TEST" marker
  // in the name or details is the owner's own convention for spotting and
  // deleting test deals in the CRM. Bounded by non-letter/start/end on both
  // sides (Codex round-1 fix) so ordinary words that merely CONTAIN the
  // substring — "latest", "contest", "testimonial" — never false-positive;
  // \b is not used because it only recognises ASCII \w, not Cyrillic.
  var TEST_MARKER_RE = /(^|[^a-zа-яіїєґ'])(?:тест|test)(?:[^a-zа-яіїєґ']|$)/i;
  function isTestLead(data) {
    return TEST_MARKER_RE.test(data.name) || TEST_MARKER_RE.test(data.details);
  }

  function buildLeadName(data, origin) {
    var leadName = "Заявка з " + location.hostname;
    if (origin === "agent") leadName += " (AI-агент)";
    if (origin === "chatkit") leadName += " (ChatKit)";
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
    var leadSource = leadSourceFor(data, origin);
    var ai = data.ai_source || "";
    // Attribution also goes into the free-text comment: Roistat custom fields
    // only reach amoCRM when mapped there, the comment always does.
    var attribution = ["lead_source=" + leadSource];
    if (ai) attribution.push("ai_source=" + ai);
    ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid"].forEach(function (k) {
      if (data[k]) attribution.push(k + "=" + data[k]);
    });
    if (data.referrer) attribution.push("referrer=" + data.referrer);
    if (data.source_page) attribution.push("page=" + data.source_page);
    var leadName = buildLeadName(data, origin);
    if (ai) leadName += " [AI: " + ai + "]";
    var payload = {
      leadName: leadName,
      text: (data.details ? data.details + "\n\n" : "") + "[" + attribution.join("; ") + "]",
      name: data.name,
      fields: {
        company: data.company,
        city: data.city,
        machines: data.machines,
        details: data.details,
        source_page: data.source_page,
        lead_origin: origin,
        lead_source: leadSource,
        ai_source: ai,
        utm_source: data.utm_source || "",
        utm_medium: data.utm_medium || "",
        utm_campaign: data.utm_campaign || "",
        utm_term: data.utm_term || "",
        utm_content: data.utm_content || "",
        gclid: data.gclid || "",
        referrer: data.referrer || "",
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

  // Reuse ADV-Strategy-Core's dedicated Anima intake. No CRM URL, token,
  // tenant selector or secondary provider is accepted from browser input.
  function intakeUrl(endpoint) {
    try {
      var u = new URL(endpoint, location.href);
      var local = u.hostname === "127.0.0.1" || u.hostname === "localhost";
      if ((u.protocol !== "https:" && !(local && u.protocol === "http:")) ||
          u.pathname !== "/api/anima/lead" || u.username || u.password || u.search || u.hash) return "";
      return u.href;
    } catch (e) { return ""; }
  }

  function intakePayload(data, id) {
    var contact = splitContact(data.contact || "");
    var p = {
      client_slug: "anima-coffee", idempotency_key: id,
      name: data.name || "", business: data.company || "", city: data.city || "",
      machines: data.machines || "", email: contact.email || "", phone: contact.phone || "",
      details: data.details || "", page_slug: data.source_page || "",
      consent: data.consent === true
    };
    // Referrer query strings may contain personal data; only send origin/path.
    try { var r = new URL(data.referrer); p.referrer = r.origin + r.pathname; } catch (e) { p.referrer = ""; }
    UTM_KEYS.forEach(function (k) { p[k] = data[k] || ""; });
    // End-to-end attribution for the server -> Roistat hop (same labels as the
    // client-side path): channel, AI answer engine and the Roistat visit id,
    // which the server cannot read itself because credentials are omitted.
    p.lead_source = /^(form|webmcp|chatkit)$/.test(data.lead_source || "") ? data.lead_source : leadSourceFor(data, "");
    p.ai_source = aiSource();
    var rv = /(?:^|;\s*)roistat_visit=([A-Za-z0-9_-]{1,64})/.exec(document.cookie || "");
    p.roistat_visit = rv ? rv[1] : "";
    return p;
  }

  var intakePending = {};
  function sendIntake(item) {
    if (intakePending[item.id]) return intakePending[item.id];
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    var promise = fetch(item.endpoint, {
      method: "POST", credentials: "omit", redirect: "error", cache: "no-store",
      referrerPolicy: "no-referrer", signal: controller.signal,
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(intakePayload(item.data, item.id)), keepalive: true
    }).then(function (r) {
      if (r.status !== 200) throw new Error("not_accepted");
      return r.json();
    }).then(function (body) {
      if (!body || body.status !== "accepted" ||
          !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(body.lead_id || "")) {
        throw new Error("invalid_receipt");
      }
      // Remove only this acknowledged item; do not overwrite newer submissions.
      writeOutbox(readOutbox().filter(function (x) { return x.id !== item.id; }));
      // A storage receipt, not a downstream CRM delivery receipt.
      fireAccepted(item.data.source_page, body.lead_id, item.origin, "confirmed", item.data);
      return { status: "accepted", leadId: body.lead_id, receipt: "stored" };
    }).catch(function () {
      // The server may have committed before the response was lost. Retain
      // the SAME key and never race this request with a Roistat beacon.
      return notConnectedResult();
    }).then(function (result) {
      clearTimeout(timer);
      delete intakePending[item.id];
      return result;
    });
    intakePending[item.id] = promise;
    return promise;
  }

  function submitIntake(data, endpoint, origin) {
    var url = intakeUrl(endpoint);
    if (!url || data.consent !== true || !data.contact) return Promise.resolve(notConnectedResult());
    var list = readOutbox();
    var fingerprint = JSON.stringify(intakePayload(data, ""));
    var item = list.find(function (x) {
      return x.endpoint === url && x.id && x.data.consent === true &&
        JSON.stringify(intakePayload(x.data, "")) === fingerprint;
    });
    if (!item) {
      if (list.length >= 3) {
        var full = notConnectedResult();
        full.message = T.pendingFull;
        full.reason = "pending_limit";
        return Promise.resolve(full);
      }
      item = { id: "anima_" + crypto.randomUUID(), ts: Date.now(), origin: origin,
        endpoint: url, data: data };
      list.push(item);
      // Persist BEFORE the request; a reload can recover the same key.
      writeOutbox(list);
    }
    return sendIntake(item);
  }

  function submitLead(form, status, data, endpoint) {
    setStatus(status, T.sending, "");
    submitIntake(data, endpoint, "human").then(function (result) {
      if (result.status === "accepted") { form.reset(); showSent(status); }
      else showDeliveryFailed(status, data, result.reason === "pending_limit" ? result.message : undefined);
      setSending(form, false);
    });
  }

  // Agent path (WebMCP): structured result for e.respondWith().
  function submitLeadAgent(form, data, endpoint) {
    return submitIntake(data, endpoint, "agent").then(function (result) {
      if (result.status === "accepted") form.reset();
      setSending(form, false);
      return result;
    });
  }

  function notConnectedResult() {
    return {
      status: "not_connected",
      // T.noBackend is false when Roistat is configured but delivery failed.
      message: roistatConfigured() ? T.err : T.noBackend,
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
      gclid: utm.gclid || "",
      ai_source: aiSource()
    };
  }

  function handle(form) {
    // Keep the status line directly under the submit button (the markup puts
    // it after the note and consent text), so the result shows where the
    // visitor just clicked.
    var statusEl = form.querySelector(".lf-status");
    var submitBtn = form.querySelector(".lf-submit");
    if (statusEl && submitBtn && submitBtn.nextElementSibling !== statusEl) {
      submitBtn.parentNode.insertBefore(statusEl, submitBtn.nextSibling);
    }

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
      // An agent's tool call still needs a resolution (Codex round-2 fix):
      // leaving executeTool()'s promise unresolved would hang the caller.
      if (form.dataset.lfSending === "1") {
        if (isAgent) { e.respondWith(Promise.resolve({ status: "error", message: T.err })); }
        return;
      }

      var data = collectData(form);
      var endpoint = (form.getAttribute("data-endpoint") || "").trim();
      // The form discloses that submission consents to contact; chat uses
      // its explicit checkbox. Never infer consent for old queued entries.
      data.consent = !!form.querySelector(".lf-consent a[href]");

      // (1) Configured durable intake owns this submission exclusively.
      if (endpoint) {
        setSending(form, true);
        if (isAgent) {
          e.respondWith(submitLeadAgent(form, data, endpoint));
          return;
        }
        submitLead(form, status, data, endpoint);
        return;
      }

      var origin = isAgent ? "agent" : "human";

      // (2) Roistat ready right now -> one reach() call, no POST.
      if (roistatReady()) {
        setSending(form, true);
        if (isAgent) {
          e.respondWith(Promise.resolve(deliverRoistatAgent(form, data, origin)));
        } else {
          deliverRoistatHuman(form, status, data, origin);
        }
        return;
      }

      // (2b) Configured but the async counter hasn't defined
      // window.roistatGoal yet (fast agent / slow connection racing the
      // script load) -> wait briefly instead of dropping straight to the
      // fallback. Never wait when Roistat was never configured at all.
      if (roistatConfigured()) {
        setSending(form, true);
        // Drop any stale previous-attempt controls/text for the duration of
        // the wait, so a re-submit never leaves a prior failure's button
        // visible while a new attempt is in flight.
        if (!isAgent) setStatus(status, T.sending, "");
        if (isAgent) {
          e.respondWith(
            waitForRoistat().then(function (ready) {
              if (ready) return deliverRoistatAgent(form, data, origin);
              setSending(form, false);
              supersedeOutboxFor(form, data, origin);
              return notConnectedResult();
            })
          );
        } else {
          waitForRoistat().then(function (ready) {
            if (ready) {
              deliverRoistatHuman(form, status, data, origin);
            } else {
              setSending(form, false);
              supersedeOutboxFor(form, data, origin);
              showDeliveryFailed(status, data);
            }
          });
        }
        return;
      }

      // (3) fallback — never configured, today's behaviour. Also
      // supersedes this form's own earlier outbox entry (fix 2).
      if (isAgent) { supersedeOutboxFor(form, data, origin); e.respondWith(Promise.resolve(notConnectedResult())); return; }
      supersedeOutboxFor(form, data, origin);
      showFallbackContact(status, data);
    });
  }

  // ChatKit channel (assets/chat.js): the chat widget delivers through the
  // SAME three-way path as the forms (first-party endpoint -> Roistat ->
  // contact fallback), so the Roistat -> AmoCRM integration and the
  // lead_accepted conversion stay identical; only lead_origin/lead_source
  // say "chatkit". Resolves {status: "accepted", leadId} | {status:
  // "not_connected", ...} | {status: "error"}; never claims success
  // without a real accept/reach.
  function chatEndpoint() {
    var f = document.querySelector("form.lead-form[data-endpoint]");
    return ((f && f.getAttribute("data-endpoint")) || "").trim();
  }

  // `formKey` (the chat widget's own <form> element, passed by
  // assets/chat.js) scopes the re-submit supersede (fix 2) to this chat
  // instance -- optional so a caller with no stable key just never
  // supersedes (falls back to saveOutbox's old stacking behaviour).
  function submitChat(data, formKey) {
    var origin = "chatkit";
    var endpoint = chatEndpoint();
    data.lead_origin = origin;
    data.lead_source = origin;
    if (endpoint) return submitIntake(data, endpoint, origin);
    function viaRoistat() {
      var leadId = reachRoistat(data, origin);
      if (!leadId) {
        if (formKey) supersedeOutboxFor(formKey, data, origin); else saveOutbox(data, origin);
        return notConnectedResult();
      }
      fireAccepted(data.source_page, leadId, origin, "unconfirmed", data);
      if (formKey) clearOutboxFor(formKey);
      return { status: "accepted", leadId: leadId };
    }
    if (roistatReady()) return Promise.resolve(viaRoistat());
    if (roistatConfigured()) {
      return waitForRoistat().then(function (ready) {
        if (ready) return viaRoistat();
        if (formKey) supersedeOutboxFor(formKey, data, origin); else saveOutbox(data, origin);
        return notConnectedResult();
      });
    }
    if (formKey) supersedeOutboxFor(formKey, data, origin); else saveOutbox(data, origin);
    return Promise.resolve(notConnectedResult());
  }

  window.animaLead = {
    submitChat: submitChat,
    collectBase: function () {
      var utm = captureUtm();
      return {
        source_page: location.pathname,
        referrer: document.referrer || "",
        utm_source: utm.utm_source || "",
        utm_medium: utm.utm_medium || "",
        utm_campaign: utm.utm_campaign || "",
        utm_term: utm.utm_term || "",
        utm_content: utm.utm_content || "",
        gclid: utm.gclid || "",
        ai_source: aiSource()
      };
    }
  };

  window.addEventListener("online", flushOutbox);

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("form.lead-form"), handle);
    flushOutbox();
  });
})();
