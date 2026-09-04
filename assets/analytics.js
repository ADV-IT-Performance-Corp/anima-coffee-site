/* Anima Volitiva — analytics (GA4 + Yandex Metrica base).
 * Loaded in <head> on every page. TWO external secrets activate it; until they are
 * set the file no-ops safely (placeholder IDs are detected and skipped).
 *
 *   GA4      — replace G-XXXXXXXXXX below  (Google Analytics 4 Measurement ID)
 *   Metrica  — replace XXXXXXXX  below     (Yandex Metrica counter number)
 *   GTM      — container GTM-MQQNGFTV is loaded inline in every page's <head>
 *              (installed 2026-09-04). Configure GA4 INSIDE GTM; keep GA4_ID a
 *              placeholder here, or page views double-count. lead_accepted is
 *              also pushed to dataLayer so a GTM trigger can consume it.
 *
 * The lead_accepted conversion is fired from assets/lead.js via
 * window.animaTrackLead() — ONLY after the first-party lead API has
 * durably accepted the lead and returned a lead_id (DC-3). It carries no
 * currency/value (a non-revenue event) and no PII — source_page and
 * lead_id only.
 */
(function () {
  // ==== THE TWO SECRETS — paste real IDs on these two lines to activate ==========
  var GA4_ID     = "G-XXXXXXXXXX"; // <-- GA4 Measurement ID (Google Analytics 4)
  var METRICA_ID = "101507598";    // <-- Yandex Metrica counter id (Anima, live)
  // ===============================================================================

  var GA4_LIVE     = !/X{6,}/.test(GA4_ID);        // "G-XXXXXXXXXX" placeholder -> skip
  var METRICA_LIVE = /^\d{5,}$/.test(METRICA_ID);  // only a numeric counter is live

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

  // --- Conversion hook, called by lead.js ONLY after the first-party lead
  // API returns HTTP 200 with a lead_id (never on mailto: open, never
  // speculatively). No currency/value — this is a non-revenue event — and
  // no PII: source_page + lead_id only.
  window.animaTrackLead = function (sourcePage, leadId) {
    var sp = sourcePage || location.pathname;
    try { window.dataLayer = window.dataLayer || []; window.dataLayer.push({ event: "lead_accepted", source_page: sp, lead_id: leadId || "" }); } catch (e) {}
    try { if (GA4_LIVE) gtag("event", "lead_accepted", { source_page: sp, lead_id: leadId || "" }); } catch (e) {}
    try { if (METRICA_LIVE && window.ym) ym(METRICA_ID, "reachGoal", "lead_accepted"); } catch (e) {}
  };
})();
