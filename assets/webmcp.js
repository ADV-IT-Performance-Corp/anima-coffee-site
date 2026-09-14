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
 * Feature-detected (`'modelContext' in document`) — no polyfill is loaded in
 * production; browsers/agents without WebMCP support simply never see the
 * tool. Loaded `defer` on every page via assets/analytics.js.
 */
(function () {
  if (!("modelContext" in document)) return;

  var FACTS = [
    // --- unpublished topics first (more specific keyword sets can overlap
    // with published ones below, e.g. "training" alone vs "training
    // duration") ---
    {
      unpublished: true,
      re: /\b(brand|model)s?\b.*\b(machine|equipment)s?\b|which (machines?|models?) exactly|full (brand|model) list/i
    },
    { unpublished: true, re: /water hardness|hardness of the water|water quality spec/i },
    { unpublished: true, re: /liabilit|insurance|who('?s| is) (liable|responsible) if/i },
    { unpublished: true, re: /contract (length|term|duration)|minimum contract|how long is the contract|commitment period/i },
    { unpublished: true, re: /multi-?location|multiple locations|multi-?site account|chain account|central(ized)? billing/i },
    { unpublished: true, re: /\bpos\b|point of sale|cashless payment|card payment on the machine/i },
    { unpublished: true, re: /maintenance (frequency|schedule) in (days|hours)|how many (visits|technician visits) per (week|month)|exact maintenance (schedule|cadence)/i },
    { unpublished: true, re: /training (duration|curriculum|hours|length)|how long is the training/i },

    // --- published facts (all copied verbatim from live site copy) ---
    {
      re: /\bpackage|start,? pro,? (and )?max|pricing tier/i,
      en: "Anima offers three equipment packages — Start, Pro, Max — matched to the venue format. Pricing is a custom quote per venue; package contents and prices are not published online.",
      uk: "Anima пропонує три пакети обладнання — Start, Pro, Max — під формат вашого об'єкта. Ціна розраховується індивідуально під об'єкт; вміст пакетів і ціни онлайн не публікуються."
    },
    {
      re: /\bprice|cost|how much (does|will) it cost|quote\b/i,
      en: "Pricing is an individual quote per venue based on your volume and number of locations — there is no published price list.",
      uk: "Ціна — індивідуальний розрахунок під об'єкт залежно від обсягу та кількості локацій — опублікованого прайс-листа немає."
    },
    {
      re: /trial|14[- ]day|free trial|test period/i,
      en: "Free 14-day trial with no prepayment.",
      uk: "Безкоштовний 14-денний тест без передоплати."
    },
    {
      re: /support|24\/7|breakdown|sla|response time|replacement machine|technician/i,
      en: "24/7 support line. On breakdown, a technician or a replacement machine is provided within 24 hours.",
      uk: "Лінія підтримки 24/7. У разі поломки технік або підмінний апарат надається протягом 24 годин."
    },
    {
      re: /kyiv oblast|coverage|service area|where do you operate|which (city|cities|region)/i,
      en: "Service area is Kyiv city and Kyiv Oblast.",
      uk: "Зона обслуговування — місто Київ та Київська область."
    },
    {
      re: /since when|how long have you (been|existed)|founded|established|history/i,
      en: "Anima Volitiva has been on the market since 2015.",
      uk: "Anima Volitiva на ринку з 2015 року."
    },
    {
      re: /how many (active )?client|client count|customer count|how many businesses/i,
      en: "1,700+ active B2B clients.",
      uk: "Понад 1 700 активних B2B-клієнтів."
    },
    {
      re: /barista|staff training|do (we|i) need (a )?barista|training included/i,
      en: "Staff training is included with every installation — no dedicated barista hire needed.",
      uk: "Навчання персоналу входить у кожну інсталяцію — окремий бариста не потрібен."
    },
    {
      re: /water filtration|maintenance included|weekly (visit|resupply|service)/i,
      en: "Water filtration and maintenance are included with every machine, plus weekly resupply of beans/consumables and a weekly technician quality visit.",
      uk: "Фільтрація води та обслуговування входять у кожен апарат, а також щотижневе поповнення кави/витратних матеріалів і щотижневий технічний візит."
    },
    {
      re: /phone|contact|email|address|hours|opening hours|call you|reach you/i,
      en: "Phone: +38 (073) 873 01 45. Email: animacoffeeco@gmail.com. Address: Kyiv Oblast, Bila Tserkva, 29a Pavlichenko St. Hours: Mon–Sat 09:00–17:00.",
      uk: "Телефон: +38 (073) 873 01 45. Email: animacoffeeco@gmail.com. Адреса: Київська обл., Біла Церква, вул. Павліченко 29а. Години роботи: Пн–Сб 09:00–17:00."
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

  document.modelContext.registerTool({
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
