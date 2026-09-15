/* Anima Volitiva — WebMCP read-only buyer-facts tool (D5).
 *
 * Registers ONE imperative, read-only tool so an agent visiting the site can
 * answer questions about Anima's service from facts that are ALREADY
 * VISIBLE on the live site today. It never invents a fact: anything not
 * published (machine brand list, water hardness, liability, contract
 * length, multi-location accounts, POS/cashless, exact maintenance
 * cadence beyond "weekly", staff training curriculum/duration) is answered
 * as "not published" and the agent is told to put the question in the lead
 * request instead.
 *
 * Feature-detected — no polyfill is loaded in production; browsers/agents
 * without WebMCP support simply never see the tool. Loaded `defer` on every
 * page via assets/analytics.js.
 *
 * Context resolution (round 4, 2026-09-14): the current spec puts the API
 * on Document —
 *   partial interface Document { [SecureContext, SameObject] readonly attribute ModelContext modelContext; };
 * (webmachinelearning.github.io/webmcp) — so `document.modelContext` is
 * tried first. `navigator.modelContext` is kept as a fallback only because
 * some early Chrome preview builds and older explainer drafts exposed it
 * there instead; if a visitor's browser (or an injected test harness) only
 * has the navigator form, this still finds it. Neither existing means no
 * WebMCP support: do nothing.
 */
(function () {
  var modelContext =
    (typeof document !== "undefined" && document.modelContext) ||
    (typeof navigator !== "undefined" && navigator.modelContext) ||
    null;
  if (!modelContext) return;

  // Matchers run against the question regardless of the requested answer
  // language (a buyer can ask in English and request a Ukrainian answer, or
  // vice versa) — every entry below carries both an EN and a UK keyword
  // pattern so language of the QUESTION never gates whether a PUBLISHED fact
  // is found.
  var FACTS = [
    // --- unpublished topics first (more specific keyword sets can overlap
    // with published ones below, e.g. "training" alone vs "training
    // duration") ---
    {
      unpublished: true,
      re: /\b(brand|model)s?\b.*\b(machine|equipment)s?\b|which (machines?|models?) exactly|full (brand|model) list|бренд|модел[ьіїю]/i
    },
    { unpublished: true, re: /water hardness|hardness of the water|water quality spec|жорсткість води/i },
    { unpublished: true, re: /liabilit|insurance|who('?s| is) (liable|responsible) if|відповідальніст|страхуванн/i },
    { unpublished: true, re: /contract (length|term|duration)|minimum contract (length|term|duration|period)|how long is the contract|commitment period|термін контракту|тривалість контракту/i },
    { unpublished: true, re: /multi-?location|multiple locations|multi-?site account|chain account|central(ized)? billing|мереж[аеу] закладів|кілька локацій/i },
    { unpublished: true, re: /\bpos\b|point of sale|cashless payment|card payment on the machine|безготівков|термінал/i },
    { unpublished: true, re: /maintenance (frequency|schedule) in (days|hours)|how many (visits|technician visits) per (week|month)|exact maintenance (schedule|cadence)|точний графік обслуговування/i },
    { unpublished: true, re: /training (duration|curriculum|hours|length)|how long is the training|тривалість навчання|скільки триває навчання/i },

    // --- published facts (all copied verbatim from live site copy) ---
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
    // Codex round-4 fix: "minimum contract [length/term]" stays unpublished
    // above, but a DIFFERENT, published fact — no forced minimum coffee
    // volume/order per month — is what the site's own FAQ answers. Checked
    // here, before it could ever fall through to the unpublished catch-all.
    {
      re: /minimum (volume|order|amount|quantity)|forced (minimum|quota)|monthly minimum|do (we|i) have to (buy|order)|мінімальн(ий|у) обсяг|обов'?язков(ий|а) мінімум/i,
      en: "No forced minimum. Your quote is based on your real volume, across one of the three equipment packages, with no minimum monthly amount to hit.",
      uk: "Без обов'язкового мінімуму. Розрахунок базується на вашому реальному обсязі в межах одного з трьох пакетів обладнання, без мінімальної щомісячної кількості."
    },
    // Checked BEFORE the general support/breakdown matcher below: "weekly
    // visit"/"maintenance included" are a more specific ask than the bare
    // word "technician", which also appears in the breakdown fact — a
    // question like "Do you include a weekly technician quality visit?"
    // must resolve to the maintenance fact, not emergency breakdown
    // coverage (Codex #3 review, W1 round 3).
    {
      re: /water filtration|maintenance included|weekly (visit|resupply|service|technician)|фільтрація води|щотижнев/i,
      en: "Water filtration and maintenance are included with every machine, plus weekly resupply of beans/consumables and a weekly technician quality visit.",
      uk: "Фільтрація води та обслуговування входять у кожен апарат, а також щотижневе поповнення кави/витратних матеріалів і щотижневий технічний візит."
    },
    // Checked BEFORE the general support/breakdown matcher below, same as
    // the round-2 hours/coverage fix: "phone number"/"contact"/"address"
    // are a more specific ask than the bare word "support", which also
    // appears in the breakdown fact — "What is your support phone number?"
    // must resolve to contact info, not just the breakdown SLA (Codex
    // round 4).
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
    // W3a — verbatim customer quotes, copied from the attribution already
    // shown on the client's own site (animacoffee.com.ua) or, for the one
    // anonymized survey quote, exactly as published in delivery/
    // testimonials-provenance.md. No name/company was added or invented.
    {
      re: /testimonial|review|feedback|what (do|are) (customers?|clients?) sa(y|ying)|відгук|клієнти кажуть|відгуки клієнтів/i,
      en: "Real customer quotes: \"We're sincerely grateful for the wonderful cooperation! ... Your care and professionalism are truly valued.\" — Diana Samoukina, LUX CAFE. \"We're very happy with the coffee and the service ... it's worth every penny!\" — Oleksii, grocery store owner. \"Now I focus on growing the business, not on repairs. Guests noticed the difference — and started coming back.\" — Coffee shop owner. Full list with sources: https://aeo.animacoffee.com.ua/#testimonials",
      uk: "Реальні відгуки клієнтів: «Щиро вдячні компанії за чудову співпрацю! ... Ваша турбота та професійність дуже цінується.» — Діана Самоукіна, LUX CAFE. «Кавою і обслуговуванням дуже задоволені. ... Вартує своїх коштів!» — Олексій, власники продуктового магазину. «Тепер я фокусуюсь на розвитку, а не на ремонтах. Гості відчули різницю - і стали повертатись.» — Власник кав'ярні. Повний список із джерелами: https://aeo.animacoffee.com.ua/ua/#testimonials"
    }
  ];

  var NOT_PUBLISHED = {
    en: "That detail is not published on the site. Please include this question in your assessment request and our team will answer it directly.",
    uk: "Ця деталь не опублікована на сайті. Будь ласка, додайте це питання до запиту на аудит — наша команда відповість напряму."
  };

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

  modelContext.registerTool({
    name: "get_anima_service_info",
    title: "Anima Volitiva service facts",
    description:
      "Answer a buyer's question about Anima Volitiva's B2B coffee machine rental and service (packages, trial, support/SLA, coverage area, company history, client count, contacts/hours) using only facts already published on this site. Anything not published on the site is reported as not published, never invented.",
    inputSchema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The visitor's question about Anima's coffee machine rental/service, in their own words."
        },
        language: {
          type: "string",
          enum: ["en", "uk"],
          description: "Language to answer in."
        }
      },
      required: ["question"]
    },
    annotations: { readOnlyHint: true, untrustedContentHint: false },
    execute: function (input) {
      var lang = input && input.language === "uk" ? "uk" : "en";
      return Promise.resolve(answer(input && input.question, lang));
    }
  });
})();
