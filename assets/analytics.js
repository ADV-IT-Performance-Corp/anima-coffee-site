/* Anima Volitiva — analytics (GA4 + Yandex Metrica base).
 * Loaded in <head> on every page. TWO external secrets activate it; until they are
 * set the file no-ops safely (placeholder IDs are detected and skipped).
 *
 *   GA4      — replace G-XXXXXXXXXX below  (Google Analytics 4 Measurement ID)
 *   Metrica  — replace XXXXXXXX  below     (Yandex Metrica counter number)
 *   GTM      — container GTM-MQQNGFTV is loaded inline in every page's <head>
 *              (installed 2026-09-04). GA4 is NOT loaded by this file: leave
 *              GA4_ID a placeholder and add the GA4 tag inside the GTM
 *              container when it is wanted (otherwise page views double-count).
 *              Metrica still loads directly from this file, not via GTM.
 *              lead_accepted is also pushed to dataLayer for GTM triggers.
 *
 * The lead_accepted conversion is fired from assets/lead.js via
 * window.animaTrackLead() — ONLY after the first-party lead API has
 * durably accepted the lead and returned a lead_id (DC-3). It carries no
 * currency/value (a non-revenue event) and no PII — source_page and
 * lead_id only.
 *
 * WebMCP (W1, 2026-09-14): animaTrackLead() takes an optional third
 * argument, `origin` ("human" | "agent"), pushed to dataLayer/GA4 as
 * `lead_origin` so an agent-submitted lead is distinguishable from a
 * human-submitted one in GTM segmentation, without changing the POST
 * payload (the DC-2 backend contract is untouched). Defaults to "human"
 * when omitted. The Yandex Metrica `reachGoal("lead_accepted")` call keeps
 * its existing goal name for BOTH origins — renaming/splitting it would
 * silently stop reporting conversions against the goal already configured
 * in Metrica; `lead_origin` segmentation lives in dataLayer/GA4 only.
 *
 * Honest-delivery fallback (2026-10-31): animaTrackLead() takes a fourth
 * argument, `deliveryStatus` ("confirmed" | "unconfirmed"), pushed to
 * dataLayer/GA4 as `delivery_status` — "confirmed" when a first-party
 * endpoint returned a lead_id, "unconfirmed" when delivery went through
 * Roistat's fire-and-forget reach(). The event name and Metrica goal stay
 * unchanged; only this new param lets analytics tell the two apart.
 *
 * Roistat (W2, 2026-09-14): the counter snippet below is the documented
 * Roistat installation code (help-en.roistat.com/settings/project/
 * tracking_code/installing/), adapted to read the project id/host from the
 * two constants instead of being hardcoded per-page. ROISTAT_PROJECT_ID
 * empty -> the whole block no-ops, same as the two secrets above. Once the
 * counter has loaded it exposes `window.roistatGoal.reach()`, which
 * assets/lead.js uses as its client-side lead-delivery path (see W2 spec) —
 * this file only loads the counter; it never calls reach() itself.
 */
(function () {
  // ==== THE THREE SECRETS — paste real IDs on these lines to activate ============
  var GA4_ID     = "G-XXXXXXXXXX"; // <-- GA4 Measurement ID (Google Analytics 4)
  var METRICA_ID = "101507598";    // <-- Yandex Metrica counter id (Anima, live)
  var ROISTAT_PROJECT_ID = "7c0c18bea7088f4a9551779737558ad3"; // <-- Roistat project key (Anima, live)
  var ROISTAT_HOST = "cloud-eu.roistat.com"; // <-- EU mirror (not cloud.roistat.com)
  // ===============================================================================

  var GA4_LIVE     = !/X{6,}/.test(GA4_ID);        // "G-XXXXXXXXXX" placeholder -> skip
  var METRICA_LIVE = /^\d{5,}$/.test(METRICA_ID);  // only a numeric counter is live
  var ROISTAT_LIVE = !!ROISTAT_PROJECT_ID;         // empty string -> skip

  // --- GA4 (gtag.js) ---
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;
  if (GA4_LIVE) {
    var g = document.createElement("script");
    g.async = true;
    g.src = "https://www.googletagmanager.com/gtag/js?id=" + GA4_ID;
    document.head.appendChild(g);
    gtag("js", new Date());
    gtag("config", GA4_ID);
  }

  // --- Yandex Metrica ---
  if (METRICA_LIVE) {
    (function (m, e, t, r, i, k, a) {
      m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
      m[i].l = 1 * new Date();
      k = e.createElement(t); a = e.getElementsByTagName(t)[0];
      k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
    })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
    ym(METRICA_ID, "init", { clickmap: true, trackLinks: true, accurateTrackBounce: true });
  }

  // --- Roistat (visit analytics + client-side lead delivery via
  // roistatGoal.reach(), called from assets/lead.js) ---
  if (ROISTAT_LIVE) {
    // Wrapped in try/catch (Codex fast-follow, 2026-09-14): this IIFE must
    // never be able to throw its way out before window.animaTrackLead is
    // defined below — a Roistat-side failure (malformed cookie, missing
    // <script> anchor, etc.) would otherwise silently take GA4/Metrica
    // conversion tracking down with it.
    try {
      (function (w, d, s, h, id) {
        w.roistatProjectId = id;
        w.roistatHost = h;
        var p = d.location.protocol === "https:" ? "https://" : "http://";
        var u = /^.*roistat_visit=[^;]+(.*)?$/.test(d.cookie)
          ? "/dist/module.js"
          : "/api/site/1.0/" + id + "/init?referrer=" + encodeURIComponent(d.location.href);
        var js = d.createElement(s);
        js.charset = "UTF-8";
        js.async = 1;
        js.src = p + h + u;
        var js2 = d.getElementsByTagName(s)[0];
        js2.parentNode.insertBefore(js, js2);
      })(window, document, "script", ROISTAT_HOST, ROISTAT_PROJECT_ID);
    } catch (e) {}
  }

  // --- AI answer-engine attribution (2026-11-02). Detects, once per session
  // (first touch wins), which AI surface sent the visitor — from the referrer
  // host or from utm_source (ChatGPT appends utm_source=chatgpt.com to links
  // it opens, and often strips the referrer). The label is exposed through
  // window.animaAttribution.aiSource() for assets/lead.js, which sends it to
  // Roistat as the `ai_source` field next to the utm_* values, and is pushed
  // to dataLayer once as `ai_referral_detected` for GTM/GA4. Google AI
  // Overviews / AI Mode clicks arrive as plain google.com organic and cannot
  // be told apart client-side. No PII; values come from a fixed allowlist.
  var AI_HOSTS = {
    "chatgpt.com": "chatgpt", "chat.openai.com": "chatgpt",
    "perplexity.ai": "perplexity", "gemini.google.com": "gemini",
    "copilot.microsoft.com": "copilot", "copilot.com": "copilot",
    "claude.ai": "claude", "grok.com": "grok", "chat.deepseek.com": "deepseek",
    "meta.ai": "meta-ai"
  };
  var AI_UTM = {
    "chatgpt": "chatgpt", "chatgpt.com": "chatgpt", "openai": "chatgpt",
    "perplexity": "perplexity", "perplexity.ai": "perplexity",
    "gemini": "gemini", "gemini.google.com": "gemini",
    "copilot": "copilot", "copilot.microsoft.com": "copilot",
    "claude": "claude", "claude.ai": "claude", "grok": "grok", "deepseek": "deepseek"
  };
  var AI_STORE_KEY = "anima_ai_src_v1";
  function hostLabel(host) {
    host = (host || "").toLowerCase().replace(/^www\./, "");
    if (Object.prototype.hasOwnProperty.call(AI_HOSTS, host)) return AI_HOSTS[host];
    var parts = host.split(".");
    while (parts.length > 2) {
      parts.shift();
      var h = parts.join(".");
      if (Object.prototype.hasOwnProperty.call(AI_HOSTS, h)) return AI_HOSTS[h];
    }
    return "";
  }
  function detectAiSource() {
    var via = "", label = "";
    try {
      var u = new URLSearchParams(location.search).get("utm_source");
      u = (u || "").toLowerCase();
      if (u && Object.prototype.hasOwnProperty.call(AI_UTM, u)) { label = AI_UTM[u]; via = "utm"; }
    } catch (e) {}
    if (!label) {
      try {
        var r = document.referrer ? new URL(document.referrer) : null;
        if (r && r.hostname !== location.hostname) { label = hostLabel(r.hostname); via = label ? "referrer" : ""; }
      } catch (e) {}
    }
    return label ? { label: label, via: via } : null;
  }
  var aiSourceCached = "";
  try { aiSourceCached = sessionStorage.getItem(AI_STORE_KEY) || ""; } catch (e) {}
  if (!aiSourceCached) {
    var hit = detectAiSource();
    if (hit) {
      aiSourceCached = hit.label;
      try { sessionStorage.setItem(AI_STORE_KEY, hit.label); } catch (e) {}
      try { window.dataLayer.push({ event: "ai_referral_detected", ai_source: hit.label, ai_source_via: hit.via, source_page: location.pathname }); } catch (e) {}
    }
  }
  window.animaAttribution = { aiSource: function () { return aiSourceCached; } };

  // --- Conversion hook, called by lead.js ONLY after the first-party lead
  // API returns HTTP 200 with a lead_id (never on mailto: open, never
  // speculatively). No currency/value — this is a non-revenue event — and
  // no PII: source_page + lead_id only.
  window.animaTrackLead = function (sourcePage, leadId, origin, deliveryStatus, extra) {
    var sp = sourcePage || location.pathname;
    var leadOrigin = origin === "agent" || origin === "chatkit" ? origin : "human";
    var ds = deliveryStatus === "confirmed" || deliveryStatus === "unconfirmed" ? deliveryStatus : "";
    // lead_source (form | webmcp | chatkit) and ai_source (chatgpt, ...) are
    // the same labels sent to Roistat; both come from fixed vocabularies.
    var ls = extra && /^(form|webmcp|chatkit)$/.test(extra.lead_source || "") ? extra.lead_source : "";
    var ai = extra && /^[a-z0-9-]{1,20}$/.test(extra.ai_source || "") ? extra.ai_source : "";
    var ev = { source_page: sp, lead_id: leadId || "", lead_origin: leadOrigin, delivery_status: ds, lead_source: ls, ai_source: ai };
    try { window.dataLayer = window.dataLayer || []; var o = { event: "lead_accepted" }; for (var k in ev) o[k] = ev[k]; window.dataLayer.push(o); } catch (e) {}
    try { if (GA4_LIVE) gtag("event", "lead_accepted", ev); } catch (e) {}
    try { if (METRICA_LIVE && window.ym) ym(METRICA_ID, "reachGoal", "lead_accepted"); } catch (e) {}
  };

  // --- Click-to-contact tracking for tel:/Telegram/mailto links anywhere on
  // the page (header, footer, contact blocks). The sticky bar already pushes
  // its own cta_click, so links inside #sticky-cta are skipped to avoid double
  // counting. Same event/param names as assets/sticky-cta.js, plus source_page
  // and ai_source (fixed vocabulary) so phone/Telegram contacts can be tied to
  // AI-referral sessions. No PII: the href is never sent. Never calls
  // preventDefault, so navigation is untouched.
  document.addEventListener("click", function (e) {
    try {
      var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      if (!a || a.closest("#sticky-cta")) return;
      var h = (a.getAttribute("href") || "").toLowerCase();
      var ch = h.indexOf("tel:") === 0 ? "phone"
        : /^https?:\/\/(t\.me|telegram\.me)\//.test(h) ? "telegram"
        : h.indexOf("mailto:") === 0 ? "email" : "";
      if (!ch) return;
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ event: "cta_click", channel: ch, source_page: location.pathname, ai_source: aiSourceCached });
    } catch (err) {}
  }, true);
})();
