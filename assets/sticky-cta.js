/* Sticky contact CTA bar click tracking (assets/sticky-cta.js)
 * Paired with assets/sticky-cta.css and the #sticky-cta markup injected by
 * tools/add_sticky_cta.py.
 *
 * Pushes a GTM dataLayer event on each control's click:
 *   dataLayer.push({event: 'cta_click', channel: 'phone'|'telegram'|'form'})
 * GTM (GTM-MQQNGFTV) is already loaded on every page and reads the global
 * window.dataLayer array — no new third-party script is added here.
 *
 * Deliberately does NOT call preventDefault(): the tel:/https://t.me/...
 * /#cta navigation must continue to work exactly as a plain link would.
 */
(function () {
  function trackClick(event) {
    var channel = event.currentTarget.getAttribute("data-cta-channel");
    if (!channel) return;
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: "cta_click", channel: channel });
  }

  function init() {
    var bar = document.getElementById("sticky-cta");
    if (!bar) return;
    var controls = bar.querySelectorAll("[data-cta-channel]");
    for (var i = 0; i < controls.length; i++) {
      controls[i].addEventListener("click", trackClick);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
