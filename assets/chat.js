/* Anima Volitiva — ChatKit lead concierge (assets/chat.js + assets/chat.css).
 *
 * A guided, scripted chat on every indexable page. Zero third-party code, no
 * API key, no LLM call: every answer is a fixed string taken from the
 * approved facts in CLAUDE.md (service promises, commercial terms), so the
 * chat cannot invent a machine, price, SLA or statistic. It takes only button
 * choices, a cups/day number and the visitor's name + contact.
 *
 * Delivery is window.animaLead.submitChat() from assets/lead.js: the SAME
 * path as the forms (first-party endpoint -> Roistat reach() -> AmoCRM, else
 * the honest contact fallback). Leads are tagged lead_origin/lead_source =
 * "chatkit" (Roistat fields, dataLayer lead_accepted) for end-to-end
 * analytics. "Sent" is shown only after a real accept/reach; otherwise the
 * visitor gets the phone / email / Telegram contacts.
 *
 * Consent is an explicit unchecked checkbox, required before submit.
 * To swap in an LLM-backed ChatKit later, replace the FLOW below; the
 * delivery contract above does not change.
 */
(function () {
  if (window.__animaChat) return;
  window.__animaChat = true;
  var uk = (document.documentElement.lang || "en").toLowerCase().indexOf("uk") === 0;

  var T = uk ? {
    open: "Підібрати кавомашину в чаті", title: "Anima Volitiva", sub: "Підбір під ваш заклад", close: "Закрити чат",
    hello: "Вітаю! Допоможу підібрати рішення для вашого закладу та залишити заявку менеджеру. Що у вас за заклад?",
    venues: [["office", "Офіс"], ["horeca", "Кафе / ресторан / готель"], ["retail", "Магазин / АЗС / кіоск"], ["other", "Інше"]],
    cups: "Скільки чашок кави на день приблизно?", cupsPh: "Наприклад, 80",
    city: "Де знаходиться заклад?", cities: [["Київ", "Київ"], ["Київська область", "Київська область"], ["Інше", "Інше місто"]],
    cityOther: "Дякуємо. Зону обслуговування для вашого міста уточнить менеджер.",
    cityOk: "Ми працюємо в Києві та Київській області.",
    more: "Хочете дізнатись ще щось, чи залишимо заявку?",
    qs: [["service", "Що входить у сервіс?"], ["terms", "Умови та ціна"], ["trial", "Пробний період"], ["machines", "Які апарати?"]],
    lead: "Залишити заявку",
    a: {
      service: "Підтримка 24/7. У разі поломки техніка приїздить протягом 24 годин або ми надаємо апарат на заміну. Доставка та встановлення протягом 24 годин, щотижневе поповнення зерна й витратних матеріалів, щотижневий візит техніка, навчання персоналу, онлайн-панель продажів і вода з фільтрацією та обслуговуванням.",
      terms: "Індивідуальний розрахунок під ваш заклад і обсяг. Є три пакети обладнання — Start, Pro, Max — підбираємо під формат закладу. Вартість менеджер називає після розрахунку, фіксованих цін на сайті немає.",
      trial: "Безкоштовний 14-денний тест без передоплати.",
      machines: "Суперавтомати Dr. Coffee та Necta, а також професійні еспресо-машини La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria та Fiorenzato. Конкретну модель менеджер підбере під ваш заклад."
    },
    name: "Ваше імʼя", contact: "Телефон або email", send: "Надіслати заявку", back: "Назад",
    consent: "Погоджуюсь, що Anima Volitiva звʼяжеться зі мною щодо запиту, та з", privacy: "політикою конфіденційності",
    needConsent: "Потрібна згода на звʼязок.", needContact: "Вкажіть коректний телефон (від 6 цифр) або email.",
    sending: "Надсилаємо…", sent: "Дякуємо! Заявку отримано. Менеджер звʼяжеться з вами.",
    nobackend: "Не вдалося передати заявку через сайт. Зв'яжіться з нами напряму:",
    detailsLabel: "Чат-заявка"
  } : {
    open: "Find your coffee machine in chat", title: "Anima Volitiva", sub: "Matched to your venue", close: "Close chat",
    hello: "Hi! I can help match a solution to your venue and pass your request to a manager. What kind of venue do you have?",
    venues: [["office", "Office"], ["horeca", "Cafe / restaurant / hotel"], ["retail", "Shop / petrol station / kiosk"], ["other", "Other"]],
    cups: "Roughly how many cups of coffee per day?", cupsPh: "e.g. 80",
    city: "Where is the venue?", cities: [["Kyiv", "Kyiv"], ["Kyiv Oblast", "Kyiv Oblast"], ["Other", "Another city"]],
    cityOther: "Thanks. A manager will confirm the service area for your city.",
    cityOk: "We serve Kyiv and Kyiv Oblast.",
    more: "Want to know anything else, or shall we take your request?",
    qs: [["service", "What does service include?"], ["terms", "Terms and price"], ["trial", "Free trial"], ["machines", "Which machines?"]],
    lead: "Leave a request",
    a: {
      service: "24/7 support line. On a breakdown a technician arrives within 24 hours or we provide a replacement machine. Delivery and installation within 24 hours, weekly resupply of beans and consumables, a weekly technician visit, staff training, an online sales dashboard, and water filtration with maintenance.",
      terms: "Individual quote for your venue and volume. There are three equipment packages — Start, Pro, Max — matched to the venue format. A manager gives the price after the quote; there are no fixed prices on the site.",
      trial: "A free 14-day trial with no prepayment.",
      machines: "Dr. Coffee and Necta super-automatics, plus professional espresso machines from La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria and Fiorenzato. A manager picks the exact model for your venue."
    },
    name: "Your name", contact: "Phone or email", send: "Send request", back: "Back",
    consent: "I agree that Anima Volitiva may contact me about my request, and to the", privacy: "privacy policy",
    needConsent: "Consent to be contacted is required.", needContact: "Enter a valid phone (6+ digits) or email.",
    sending: "Sending…", sent: "Thank you! Your request has been received. A manager will be in touch.",
    nobackend: "We couldn't pass your request through the site. Please reach us directly:",
    detailsLabel: "Chat request"
  };

  var CONTACT = { phone: "+38 (073) 873 01 45", tel: "tel:+380738730145", email: "animacoffeeco@gmail.com", tg: "https://t.me/Animavolitiva" };
  var EMAIL_RE = /^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z0-9-]{2,24}$/;
  var state = { venue: "", cups: "", city: "", asked: [], started: false, sent: false, sending: false };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function track(name, extra) {
    try {
      window.dataLayer = window.dataLayer || [];
      var o = { event: name, source_page: location.pathname };
      for (var k in extra) o[k] = extra[k];
      window.dataLayer.push(o);
    } catch (e) {}
  }

  var launcher = el("button", "ac-launcher", T.open);
  launcher.type = "button";
  launcher.setAttribute("aria-expanded", "false");
  launcher.setAttribute("aria-controls", "ac-panel");
  var panel = el("div", "ac-panel");
  panel.id = "ac-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", T.title);
  panel.hidden = true;
  var head = el("div", "ac-head");
  var ht = el("div", "ac-ht");
  ht.appendChild(el("strong", "", T.title));
  ht.appendChild(el("span", "", T.sub));
  var x = el("button", "ac-x", "×");
  x.type = "button";
  x.setAttribute("aria-label", T.close);
  head.appendChild(ht); head.appendChild(x);
  var log = el("div", "ac-log");
  log.setAttribute("aria-live", "polite");
  var tray = el("div", "ac-tray");
  panel.appendChild(head); panel.appendChild(log); panel.appendChild(tray);

  function say(text, who) {
    var m = el("div", "ac-msg " + (who || "bot"), text);
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
  }
  function clearTray() { while (tray.firstChild) tray.removeChild(tray.firstChild); }
  function chips(items, onPick) {
    clearTray();
    var row = el("div", "ac-chips");
    items.forEach(function (it) {
      var b = el("button", "ac-chip", it[1]);
      b.type = "button";
      b.addEventListener("click", function () { onPick(it[0], it[1]); });
      row.appendChild(b);
    });
    tray.appendChild(row);
  }

  function stepVenue() {
    chips(T.venues, function (v, label) {
      state.venue = label; say(label, "me"); track("chatkit_step", { step: "venue", value: v }); stepCups();
    });
  }
  function stepCups() {
    say(T.cups);
    clearTray();
    var f = el("form", "ac-row");
    var i = el("input"); i.type = "number"; i.min = "1"; i.max = "100000"; i.inputMode = "numeric"; i.placeholder = T.cupsPh;
    i.setAttribute("aria-label", T.cups);
    var b = el("button", "ac-go", "→"); b.type = "submit";
    f.appendChild(i); f.appendChild(b);
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var n = parseInt(i.value, 10);
      if (!(n > 0)) return;
      state.cups = String(n); say(String(n), "me"); stepCity();
    });
    tray.appendChild(f); i.focus();
  }
  function stepCity() {
    say(T.city);
    chips(T.cities, function (v, label) {
      state.city = v; say(label, "me");
      say(v === T.cities[2][0] ? T.cityOther : T.cityOk);
      stepMenu();
    });
  }
  function stepMenu() {
    say(T.more);
    var items = T.qs.filter(function (q) { return state.asked.indexOf(q[0]) === -1; });
    items.push(["__lead", T.lead]);
    chips(items, function (k, label) {
      say(label, "me");
      if (k === "__lead") { track("chatkit_step", { step: "lead_form" }); return stepForm(); }
      state.asked.push(k); track("chatkit_step", { step: "faq", value: k });
      say(T.a[k]); stepMenu();
    });
  }

  function summary() {
    var parts = [T.detailsLabel + " (ChatKit)"];
    if (state.venue) parts.push((uk ? "Заклад: " : "Venue: ") + state.venue);
    if (state.cups) parts.push((uk ? "Чашок/день: " : "Cups/day: ") + state.cups);
    if (state.city) parts.push((uk ? "Місто: " : "City: ") + state.city);
    return parts.join("; ");
  }

  function stepForm() {
    clearTray();
    var f = el("form", "ac-form");
    f.noValidate = true;
    var name = el("input"); name.type = "text"; name.name = "name"; name.maxLength = 120; name.placeholder = T.name; name.autocomplete = "name";
    name.setAttribute("aria-label", T.name);
    var contact = el("input"); contact.type = "text"; contact.name = "contact"; contact.maxLength = 200; contact.placeholder = T.contact; contact.autocomplete = "tel";
    contact.setAttribute("aria-label", T.contact);
    var hp = el("input", "ac-hp"); hp.type = "text"; hp.name = "company_url"; hp.tabIndex = -1; hp.autocomplete = "off"; hp.setAttribute("aria-hidden", "true");
    var cl = el("label", "ac-consent");
    var cb = el("input"); cb.type = "checkbox";
    cl.appendChild(cb);
    var span = el("span", "", T.consent + " ");
    var a = el("a", "", T.privacy); a.href = uk ? "/ua/privacy.html" : "/privacy.html"; a.target = "_blank"; a.rel = "noopener";
    span.appendChild(a);
    cl.appendChild(span);
    var err = el("div", "ac-err"); err.setAttribute("role", "alert");
    var go = el("button", "ac-send", T.send); go.type = "submit";
    f.appendChild(name); f.appendChild(contact); f.appendChild(hp); f.appendChild(cl); f.appendChild(err); f.appendChild(go);
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      if (state.sending || state.sent) return;
      err.textContent = "";
      var c = contact.value.trim();
      var digits = (c.match(/\d/g) || []).length;
      if (!(EMAIL_RE.test(c) || (c.indexOf("@") === -1 && digits >= 6))) { err.textContent = T.needContact; contact.focus(); return; }
      if (!cb.checked) { err.textContent = T.needConsent; cb.focus(); return; }
      if (hp.value.trim()) { finish(true); return; }
      if (!window.animaLead || !window.animaLead.submitChat) { fallback(); return; }
      state.sending = true; go.disabled = true; err.textContent = T.sending;
      var data = window.animaLead.collectBase();
      data.name = name.value.trim(); data.company = ""; data.city = state.city; data.machines = "";
      data.contact = c; data.details = summary(); data.consent = true;
      window.animaLead.submitChat(data).then(function (r) {
        state.sending = false;
        if (r && r.status === "accepted") { track("chatkit_lead_sent", {}); finish(false); }
        else { go.disabled = false; err.textContent = ""; fallback(); }
      }, function () { state.sending = false; go.disabled = false; fallback(); });
    });
    tray.appendChild(f); name.focus();
  }
  function finish(silent) {
    state.sent = true; clearTray(); say(T.sent);
  }
  function fallback() {
    say(T.nobackend);
    var box = el("div", "ac-msg bot");
    [[CONTACT.phone, CONTACT.tel], [CONTACT.email, "mailto:" + CONTACT.email], ["Telegram", CONTACT.tg]].forEach(function (c) {
      var l = el("a", "ac-contact", c[0]); l.href = c[1]; box.appendChild(l);
    });
    log.appendChild(box); log.scrollTop = log.scrollHeight;
  }

  function setOpen(o) {
    panel.hidden = !o;
    launcher.setAttribute("aria-expanded", o ? "true" : "false");
    launcher.classList.toggle("ac-off", o);
    if (o && !state.started) {
      state.started = true; say(T.hello); stepVenue();
      track("chatkit_open", {});
    }
  }
  launcher.addEventListener("click", function () { setOpen(panel.hidden); });
  x.addEventListener("click", function () { setOpen(false); launcher.focus(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) { setOpen(false); launcher.focus(); } });

  function mount() {
    document.body.appendChild(launcher);
    document.body.appendChild(panel);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
