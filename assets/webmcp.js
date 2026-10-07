/* Anima Volitiva — WebMCP tools (D5, extended 2026-10-06).
 *
 * Registers THREE imperative tools so an agent visiting the site can answer
 * buyer questions and hand a quote request to the visitor, using ONLY facts
 * already VISIBLE on the live site / llms.txt. It never invents a fact:
 * anything not published (water hardness, liability, contract length,
 * multi-location accounts, POS/cashless, exact maintenance cadence beyond
 * "weekly", staff training curriculum/duration, package contents, prices) is
 * answered as "not published" and the agent is told to put the question in
 * the lead request instead.
 *
 *   get_anima_service_info        read-only  — keyword Q&A over published facts
 *   get_anima_products            read-only  — the published lineup (brands per
 *                                              type, coffee, Start/Pro/Max, trial,
 *                                              service area, how to request a quote)
 *   prepare_coffee_quote_request  NOT read-only, NOT consequential — prefills the
 *                                              existing #leadForm, scrolls/focuses
 *                                              it, and NEVER submits. The visitor
 *                                              reviews and presses the button.
 *
 * Context resolution: the current spec puts the API on Document —
 *   partial interface Document { [SecureContext, SameObject] readonly attribute ModelContext modelContext; };
 * (webmachinelearning.github.io/webmcp) — so `document.modelContext` is
 * tried first. `navigator.modelContext` is kept as a fallback for early
 * Chrome preview builds and older explainer drafts.
 *
 * Polyfill (2026-10-06): when NEITHER context exists (native WebMCP is behind a
 * Chrome flag), a PINNED, SELF-HOSTED copy of the @mcp-b/global polyfill
 * (assets/vendor/mcp-b-global/, MIT, version in VERSION.txt) is injected
 * before registration. No CDN, no @latest. When a native context exists the
 * polyfill is never fetched. Registration happens exactly once per page, even
 * if this file is included twice.
 */
(function () {
  if (typeof window !== "undefined" && window.__animaWebmcpState) return;
  if (typeof window !== "undefined") window.__animaWebmcpState = "pending";

  function resolveContext() {
    return (
      (typeof document !== "undefined" && document.modelContext) ||
      (typeof navigator !== "undefined" && navigator.modelContext) ||
      null
    );
  }

  // ------------------------------------------------------------------ data
  var NOT_PUBLISHED = {
    en: "That detail is not published on the site. Please include this question in your assessment request and our team will answer it directly.",
    uk: "Ця деталь не опублікована на сайті. Будь ласка, додайте це питання до запиту на аудит — наша команда відповість напряму."
  };

  // Published lineup (llms.txt "Equipment" line; model names from the
  // dr-coffee-vs-espresso page). "These eight brands are the complete lineup."
  var BRANDS_SUPER = ["Dr. Coffee", "Necta"];
  var BRANDS_PRO = ["La Spaziale", "Nuova Simonelli", "Rancilio", "Iberital", "Astoria", "Fiorenzato"];
  var MODELS_SUPER = {
    "Dr. Coffee": ["Minibar", "Coffeebar", "F12", "Coffee Center", "Coffee Zone", "M12"],
    "Necta": ["Koro Prime", "Korinto Prime", "Krea Touch"]
  };
  var BLENDS = ["Bellissima", "LOT 101", "LOT 105", "Ethiopia Yirgacheffe"];
  var PACKAGES = ["Start", "Pro", "Max"];

  var T = {
    en: {
      brands:
        "Equipment: super-automatics from Dr. Coffee (Minibar, Coffeebar, F12, Coffee Center, Coffee Zone, M12) and Necta (Koro Prime, Korinto Prime, Krea Touch); professional espresso machines from La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria and Fiorenzato. These eight brands are the complete lineup. Which machine is matched to your venue is agreed in the individual quote.",
      area: "Service area is Kyiv city and Kyiv Oblast.",
      trial: "Free 14-day trial with no prepayment.",
      packages:
        "Three equipment packages — Start, Pro, Max — matched to the venue format. Pricing is a custom quote per venue; package contents and prices are not published online.",
      coffee:
        "Premium roasted coffee, not a forced quota — named blends including Bellissima, LOT 101, LOT 105 and Ethiopia Yirgacheffe.",
      next: "visitor reviews and presses Get my custom assessment",
      quote:
        "To request a quote, use the request_coffee_service_assessment form on the page, or call prepare_coffee_quote_request to prefill it for the visitor to review and send."
    },
    uk: {
      brands:
        "Обладнання: суперавтомати Dr. Coffee (Minibar, Coffeebar, F12, Coffee Center, Coffee Zone, M12) та Necta (Koro Prime, Korinto Prime, Krea Touch); професійні еспресо-машини La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria та Fiorenzato. Ці вісім брендів — повна лінійка. Яку саме машину підібрано під ваш об'єкт, узгоджується в індивідуальному розрахунку.",
      area: "Зона обслуговування — місто Київ та Київська область.",
      trial: "Безкоштовний 14-денний тест без передоплати.",
      packages:
        "Три пакети обладнання — Start, Pro, Max — під формат об'єкта. Ціна розраховується індивідуально під об'єкт; вміст пакетів і ціни онлайн не публікуються.",
      coffee:
        "Преміальна обсмажена кава без примусових квот — зокрема бленди Bellissima, LOT 101, LOT 105 та Ethiopia Yirgacheffe.",
      next: "відвідувач перевіряє дані та натискає «Get my custom assessment»",
      quote:
        "Щоб отримати розрахунок, скористайтеся формою request_coffee_service_assessment на сторінці або викличте prepare_coffee_quote_request, щоб заповнити її для перегляду й відправки відвідувачем."
    }
  };

  // Matchers run against the question regardless of the requested answer
  // language — every entry carries both EN and UK keyword patterns.
  var FACTS = [
    // --- unpublished topics first ---
    { unpublished: true, re: /water hardness|hardness of the water|water quality spec|жорсткість води/i },
    { unpublished: true, re: /liabilit|insurance|who('?s| is) (liable|responsible) if|відповідальніст|страхуванн/i },
    { unpublished: true, re: /contract (length|term|duration)|minimum contract (length|term|duration|period)|how long is the contract|commitment period|термін контракту|тривалість контракту/i },
    { unpublished: true, re: /multi-?location|multiple locations|multi-?site account|chain account|central(ized)? billing|мереж[аеу] закладів|кілька локацій/i },
    { unpublished: true, re: /\bpos\b|point of sale|cashless payment|card payment on the machine|безготівков|термінал/i },
    { unpublished: true, re: /maintenance (frequency|schedule) in (days|hours)|how many (visits|technician visits) per (week|month)|exact maintenance (schedule|cadence)|точний графік обслуговування/i },
    { unpublished: true, re: /training (duration|curriculum|hours|length)|how long is the training|тривалість навчання|скільки триває навчання/i },

    // --- published facts ---
    {
      re: /\bpackage|start,? pro,? (and )?max|pricing tier|пакет/i,
      en: "Anima offers three equipment packages — Start, Pro, Max — matched to the venue format. Pricing is a custom quote per venue; package contents and prices are not published online.",
      uk: "Anima пропонує три пакети обладнання — Start, Pro, Max — під формат вашого об'єкта. Ціна розраховується індивідуально під об'єкт; вміст пакетів і ціни онлайн не публікуються."
    },
    {
      re: /\bprice|cost|how much (does|will) it cost|quote\b|ціна|вартість|скільки коштує/i,
      en: "Pricing is an individual quote per venue based on your volume and number of locations — there is no published price list.",
      uk: "Ціна — індивідуальний розрахунок під об'єкт залежно від обсягу та кількості локацій — опублікованого прайс-листа немає."
    },
    {
      re: /trial|14[- ]day|free trial|test period|тест|14.?денн/i,
      en: "Free 14-day trial with no prepayment.",
      uk: "Безкоштовний 14-денний тест без передоплати."
    },
    {
      re: /minimum (volume|order|amount|quantity)|forced (minimum|quota)|monthly minimum|do (we|i) have to (buy|order)|мінімальн(ий|у) обсяг|обов'?язков(ий|а) мінімум/i,
      en: "No forced minimum. Your quote is based on your real volume, across one of the three equipment packages, with no minimum monthly amount to hit.",
      uk: "Без обов'язкового мінімуму. Розрахунок базується на вашому реальному обсязі в межах одного з трьох пакетів обладнання, без мінімальної щомісячної кількості."
    },
    {
      re: /water filtration|maintenance included|weekly (visit|resupply|service|technician)|фільтрація води|щотижнев/i,
      en: "Water filtration and maintenance are included with every machine, plus weekly resupply of beans/consumables and a weekly technician quality visit.",
      uk: "Фільтрація води та обслуговування входять у кожен апарат, а також щотижневе поповнення кави/витратних матеріалів і щотижневий технічний візит."
    },
    // Brands / models / equipment lineup — published in llms.txt and on the
    // site. Checked before the generic support/technician matcher.
    {
      re: /\bbrands?\b|\bmodels?\b|equipment|lineup|line-up|what machines|which machines|machines? (do you|you) (offer|install|have|rent)|do you (install|offer|rent|have)\b.*\b(machine|\bnecta\b|dr\.? ?coffee|spaziale|simonelli|rancilio|iberital|astoria|fiorenzato)|\bnecta\b|dr\.? ?coffee|spaziale|simonelli|rancilio|iberital|astoria|fiorenzato|бренд|модел[ьіїю]|обладнанн|які (кава)?машини|кавомашин/i,
      en: T.en.brands,
      uk: T.uk.brands
    },
    {
      re: /phone number|contact (info|details|you)|email address|\baddress\b|opening hours|business hours|what (time|hours)|call you|reach you|телефон|адреса|пошта|години роботи|график роботи|зв'?язатися/i,
      en: "Phone: +38 (073) 873 01 45. Email: animacoffeeco@gmail.com. Address: Kyiv Oblast, Bila Tserkva, 29a Pavlichenko St. Hours: Mon–Sat 09:00–17:00.",
      uk: "Телефон: +38 (073) 873 01 45. Email: animacoffeeco@gmail.com. Адреса: Київська обл., Біла Церква, вул. Павліченко 29а. Години роботи: Пн–Сб 09:00–17:00."
    },
    {
      re: /support|24\/7|break(s|ing)? ?down|breakdown|\bsla\b|response time|replacement machine|technician|поломк|підтримк|ремонт/i,
      en: "24/7 support line. On breakdown, a technician or a replacement machine is provided within 24 hours.",
      uk: "Лінія підтримки 24/7. У разі поломки технік або підмінний апарат надається протягом 24 годин."
    },
    {
      re: /coverage|service area|where do you operate|which (city|cities|region)|do you (cover|serve|operate in)|де ви (працюєте|обслуговуєте)|обслуговуєте|яку територію/i,
      en: "Service area is Kyiv city and Kyiv Oblast.",
      uk: "Зона обслуговування — місто Київ та Київська область."
    },
    {
      re: /since when|how long have you (been|existed)|founded|established|(company|business) history|з якого року|скільки років на ринку/i,
      en: "Anima Volitiva has been on the market since 2015.",
      uk: "Anima Volitiva на ринку з 2015 року."
    },
    {
      re: /how many (active )?client|client count|customer count|how many businesses|скільки клієнтів|кількість клієнтів/i,
      en: "1,700+ active B2B clients.",
      uk: "Понад 1 700 активних B2B-клієнтів."
    },
    {
      re: /barista|staff training|do (we|i) need (a )?barista|training included|бариста|навчання персоналу/i,
      en: "Staff training is included with every installation — no dedicated barista hire needed.",
      uk: "Навчання персоналу входить у кожну інсталяцію — окремий бариста не потрібен."
    },
    {
      re: /testimonial|review|feedback|what (do|are) (customers?|clients?) sa(y|ying)|відгук|клієнти кажуть|відгуки клієнтів/i,
      en: "Real customer quotes: \"We're sincerely grateful for the wonderful cooperation! ... Your care and professionalism are truly valued.\" — Diana Samoukina, LUX CAFE. \"We're very happy with the coffee and the service ... it's worth every penny!\" — Oleksii, grocery store owner. \"Now I focus on growing the business, not on repairs. Guests noticed the difference — and started coming back.\" — Coffee shop owner. Full list with sources: https://aeo.animacoffee.com.ua/#testimonials",
      uk: "Реальні відгуки клієнтів: «Щиро вдячні компанії за чудову співпрацю! ... Ваша турбота та професійність дуже цінується.» — Діана Самоукіна, LUX CAFE. «Кавою і обслуговуванням дуже задоволені. ... Вартує своїх коштів!» — Олексій, власники продуктового магазину. «Тепер я фокусуюсь на розвитку, а не на ремонтах. Гості відчули різницю - і стали повертатись.» — Власник кав'ярні. Повний список із джерелами: https://aeo.animacoffee.com.ua/ua/#testimonials"
    }
  ];

  function answer(question, language) {
    var uk = language === "uk";
    var q = String(question || "");
    for (var i = 0; i < FACTS.length; i++) {
      var f = FACTS[i];
      if (f.re.test(q)) {
        if (f.unpublished) {
          return { published: false, answer: uk ? NOT_PUBLISHED.uk : NOT_PUBLISHED.en };
        }
        return { published: true, answer: uk ? f.uk : f.en };
      }
    }
    return { published: false, answer: uk ? NOT_PUBLISHED.uk : NOT_PUBLISHED.en };
  }

  // ------------------------------------------------------------- products
  var CATEGORIES = ["super_automatic", "professional_espresso", "coffee", "packages"];

  function products(category, language) {
    var lang = language === "uk" ? "uk" : "en";
    var t = T[lang];
    if (category && CATEGORIES.indexOf(category) < 0) {
      return {
        published: false,
        answer: lang === "uk" ? NOT_PUBLISHED.uk : NOT_PUBLISHED.en,
        valid_categories: CATEGORIES.slice()
      };
    }
    var out = { published: true, language: lang, category: category || "all" };
    var all = !category;
    if (all || category === "super_automatic") {
      out.super_automatic = { brands: BRANDS_SUPER.slice(), models: MODELS_SUPER };
    }
    if (all || category === "professional_espresso") {
      out.professional_espresso = { brands: BRANDS_PRO.slice() };
    }
    if (all || category === "coffee") {
      out.coffee = { summary: t.coffee, named_blends: BLENDS.slice() };
    }
    if (all || category === "packages") {
      out.packages = { names: PACKAGES.slice(), summary: t.packages };
    }
    if (all) {
      out.brands_note = t.brands;
      out.free_trial = t.trial;
      out.service_area = t.area;
      out.pricing = lang === "uk"
        ? "Індивідуальний розрахунок під об'єкт; ціни онлайн не публікуються."
        : "Custom quote per venue; prices are not published online.";
    }
    out.how_to_request_quote = t.quote;
    out.request_tool = "request_coffee_service_assessment";
    out.prefill_tool = "prepare_coffee_quote_request";
    return out;
  }

  // ------------------------------------------------------- quote prefill
  var QUOTE_FIELDS = ["name", "business", "city", "machines", "contact", "message"];

  function prepareQuote(input, language) {
    var t = T[language === "uk" ? "uk" : "en"];
    var form = document.getElementById("leadForm");
    if (!form) {
      return {
        prefilled: false,
        submitted: false,
        error: "lead form not found on this page",
        next: language === "uk"
          ? "відкрийте головну сторінку сайту та повторіть виклик"
          : "open the site's home page and call this tool again"
      };
    }
    var filled = [];
    var first = null;
    QUOTE_FIELDS.forEach(function (name) {
      var v = input && input[name];
      if (typeof v !== "string" && typeof v !== "number") return;
      v = String(v).trim().slice(0, 1000);
      if (!v) return;
      var el = form.querySelector('[name="' + name + '"]');
      if (!el) return;
      el.value = v;
      try {
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      } catch (e) { /* events are a nicety; the value is already set */ }
      filled.push(name);
    });
    try { form.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) { /* ignore */ }
    // Focus the first required field still empty, else the submit button.
    // Focusing never submits; this tool never calls submit()/click().
    for (var i = 0; i < QUOTE_FIELDS.length && !first; i++) {
      var el2 = form.querySelector('[name="' + QUOTE_FIELDS[i] + '"]');
      if (el2 && el2.required && !el2.value) first = el2;
    }
    if (!first) first = form.querySelector('[type="submit"]');
    try { if (first && first.focus) first.focus(); } catch (e) { /* ignore */ }
    return { prefilled: true, submitted: false, filled_fields: filled, next: t.next };
  }

  // -------------------------------------------------------- registration
  function register(ctx) {
    if (window.__animaWebmcpState === "registered") return;
    window.__animaWebmcpState = "registered";

    function reg(tool) {
      try {
        var r = ctx.registerTool(tool);
        if (r && typeof r.catch === "function") r.catch(function () {});
      } catch (e) { /* a failed registration must never break the page */ }
    }

    reg({
      name: "get_anima_service_info",
      title: "Anima Volitiva service facts",
      description:
        "Answer a buyer's question about Anima Volitiva's B2B coffee machine rental and service (equipment brands, packages, trial, support/SLA, coverage area, company history, client count, contacts/hours) using only facts already published on this site. Anything not published on the site is reported as not published, never invented.",
      inputSchema: {
        type: "object",
        properties: {
          question: { type: "string", description: "The visitor's question about Anima's coffee machine rental/service, in their own words." },
          language: { type: "string", enum: ["en", "uk"], description: "Language to answer in." }
        },
        required: ["question"]
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: function (input) {
        var lang = input && input.language === "uk" ? "uk" : "en";
        return Promise.resolve(answer(input && input.question, lang));
      }
    });

    reg({
      name: "get_anima_products",
      title: "Anima Volitiva published lineup",
      description:
        "Return the lineup Anima publishes: machine brands per type (super-automatic, professional espresso), premium roasted coffee, the Start/Pro/Max packages (custom quote, prices not published), the free 14-day trial with no prepayment, the service area, and how to request a quote. Optional category filter. Read-only; returns only published items.",
      inputSchema: {
        type: "object",
        properties: {
          category: { type: "string", enum: CATEGORIES, description: "Optional: limit to one product category." },
          language: { type: "string", enum: ["en", "uk"], description: "Language to answer in." }
        }
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: function (input) {
        return Promise.resolve(products(input && input.category, input && input.language));
      }
    });

    reg({
      name: "prepare_coffee_quote_request",
      title: "Prefill the coffee service quote request",
      description:
        "Prefill the on-page quote request form (name, business, city, machines, contact, message) from details the visitor gave you, scroll to it and focus it. It NEVER submits: the visitor reviews the fields and presses 'Get my custom assessment' themselves. Only pass details the visitor actually provided.",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Contact person's full name." },
          business: { type: "string", description: "Business or venue name." },
          city: { type: "string", description: "City. Service area is Kyiv city and Kyiv Oblast." },
          machines: { type: "string", description: "Number of coffee machines needed, if known." },
          contact: { type: "string", description: "Email or phone number to reach the visitor." },
          message: { type: "string", description: "Optional notes for the Anima team." },
          language: { type: "string", enum: ["en", "uk"], description: "Language of the returned instructions." }
        }
      },
      annotations: { readOnlyHint: false, consequentialHint: false, untrustedContentHint: false },
      execute: function (input) {
        return Promise.resolve(prepareQuote(input || {}, input && input.language === "uk" ? "uk" : "en"));
      }
    });
  }

  // ------------------------------------------------- polyfill call shim
  // Root cause of the "executeTool hangs / never returns" report (2026-10-06):
  // WebMCP's ModelContext.executeTool takes a RegisteredTool DESCRIPTOR (from
  // `await getTools()`) plus the input as a JSON string
  // (webmachinelearning.github.io/webmcp: executeTool(RegisteredTool tool,
  // optional object inputObject) -> Promise<DOMString>; @mcp-b/global 5.1.0
  // additionally JSON.parses the input and answers "Failed to parse input
  // arguments" for a plain object). Agents and test drivers call it by tool
  // NAME instead, which the polyfill rejects with a TypeError that a CDP
  // driver can swallow and wait on forever. When the polyfill is in use we
  // accept the by-name form (args as an object, a JSON string, or omitted)
  // and always settle: a bad call rejects, it never waits. Native Chrome
  // contexts are never touched (this runs only on the injected polyfill).
  function installCallShim(ctx) {
    if (!ctx || ctx.__animaCallShim || typeof ctx.executeTool !== "function") return;
    var orig = ctx.executeTool;
    function toJson(input) {
      if (typeof input === "string") return input;
      return JSON.stringify(input === undefined || input === null ? {} : input);
    }
    try {
      ctx.executeTool = function (tool, input, options) {
        if (typeof tool === "string") {
          return Promise.resolve(ctx.getTools()).then(function (tools) {
            var found = null;
            tools = Array.prototype.slice.call(tools || []);
            for (var i = 0; i < tools.length; i++) {
              if (tools[i] && tools[i].name === tool) { found = tools[i]; break; }
            }
            if (!found) throw new Error("Tool not found: " + tool);
            return orig.call(ctx, found, toJson(input), options);
          });
        }
        return orig.call(ctx, tool, input === undefined ? input : toJson(input), options);
      };
      ctx.__animaCallShim = true;
    } catch (e) { /* frozen context: leave the polyfill API as shipped */ }
  }

  // ------------------------------------------------------------- bootstrap
  var ctx = resolveContext();
  if (ctx) {
    register(ctx);
    return;
  }

  // No native WebMCP: load the pinned, self-hosted polyfill, then register.
  var base = "/assets/";
  try {
    var cs = document.currentScript && document.currentScript.src;
    if (cs) base = cs.replace(/webmcp\.js(\?.*)?$/, "");
  } catch (e) { /* keep default */ }
  var s = document.createElement("script");
  s.src = base + "vendor/mcp-b-global/index.iife.js";
  s.async = true;
  s.onload = function () {
    var c = resolveContext();
    if (c) { installCallShim(c); register(c); }
  };
  s.onerror = function () { /* no WebMCP available; the page works as normal */ };
  (document.head || document.documentElement).appendChild(s);
})();
