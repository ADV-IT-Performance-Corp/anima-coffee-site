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
  }

  // --- Conversion hook, called by lead.js ONLY after the first-party lead
  // API returns HTTP 200 with a lead_id (never on mailto: open, never
  // speculatively). No currency/value — this is a non-revenue event — and
  // no PII: source_page + lead_id only.
  window.animaTrackLead = function (sourcePage, leadId, origin) {
    var sp = sourcePage || location.pathname;
    var leadOrigin = origin === "agent" ? "agent" : "human";
    try { window.dataLayer = window.dataLayer || []; window.dataLayer.push({ event: "lead_accepted", source_page: sp, lead_id: leadId || "", lead_origin: leadOrigin }); } catch (e) {}
    try { if (GA4_LIVE) gtag("event", "lead_accepted", { source_page: sp, lead_id: leadId || "", lead_origin: leadOrigin }); } catch (e) {}
    try { if (METRICA_LIVE && window.ym) ym(METRICA_ID, "reachGoal", "lead_accepted"); } catch (e) {}
  };
})();
