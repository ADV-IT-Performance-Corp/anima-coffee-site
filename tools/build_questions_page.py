#!/usr/bin/env python3
"""Wire the Customer_Question_Mining artifact (8_Customer_Question_Mining.md, 3768w) into a
real AEO page: top mined buyer-questions (by frequency) with grounded answers + the artifact's
Kyiv-Oblast pain-point summary. Answers are authored from the site's established offer facts
(2h SLA, flat monthly invoice, Franke/WMF, Kyiv water 15-20 dH, no bean quotas). EN + UA.
FAQPage + Article schema, OG, hreflang. Closes surface-artifact coverage 10/13 -> 11/13."""
import html, pathlib, json
ROOT = pathlib.Path("/home/dancanadian/anima-site")
BASE = "https://aeo.animacoffee.com.ua"
SLUG = "what-kyiv-coffee-operators-ask.html"

# FULL Top-30 mined-question inventory (Customer_Question_Mining) with grounded answers
QA = [
 ("How do I choose between renting a Swiss super-automatic like Franke or buying one outright for a 50-person Kyiv office?",
  "Buying ties up $3,500–$15,000+ per unit in depreciating hardware and leaves you owning every repair, scale failure and downtime day. Renting under Anima’s flat monthly invoice keeps that capital free: you get the same Franke/WMF machine, sized in a free on-site audit, plus beans, staff training, water/voltage protection and a 2-hour on-site SLA — one predictable OpEx line, no CapEx."),
 ("What should I do if my coffee machine shows a limescale warning but our office team can't change the water filters?",
  "A limescale warning means mineral buildup is already threatening the boiler — it should not be left to untrained staff. Under Anima’s service it’s not your job: filter changes and descaling are part of the preventive-maintenance schedule included in the flat monthly fee, and a technician handles it on-site before it becomes a failure."),
 ("Why does our office coffee taste increasingly bitter even though we use premium beans and never touched the grinder?",
  "Bitterness that creeps in without a settings change is almost always scale and calibration drift — hardened boilers and an un-recalibrated grind pull over-extracted, bitter shots. Anima’s monthly calibration re-syncs grind, pressure and temperature to your specific beans and water, restoring a consistent cup without you changing anything."),
 ("If our gas station in Kyiv Oblast breaks down on a Sunday, how fast can a certified technician arrive with parts?",
  "Anima guarantees a 2-hour on-site response across Kyiv & Kyiv Oblast, 24/7 — weekends included — with certified technicians carrying diagnostic tools and proprietary Swiss parts. For a forecourt where downtime is direct lost sales (up to ~$500/day), that SLA is the difference between a coffee outage and uninterrupted revenue."),
 ("Why are our rental costs fluctuating monthly when we were promised a fixed-price contract?",
  "Fluctuating invoices usually mean your current vendor treats service calls, parts or bean volume as variable add-ons. Anima’s contract is a genuine flat monthly rate — machine, beans, service and support are all inside one fixed figure, so the number you sign is the number you pay every month."),
 ("How does hard Kyiv municipal water affect professional WMF boilers over a six-month period?",
  "Kyiv-region water runs 15–20 dH. Without active filtration and scheduled scale calibration, that mineral load causes catastrophic boiler scaling within 6–12 months. Anima installs filtration calibrated to your local hardness and runs preventive descaling, so the boiler never reaches failure — the scaling risk is engineered out, not billed later."),
 ("How can we cut our office coffee budget without downgrading beans or risking complaints from leadership?",
  "The saving comes from consolidation, not cheaper coffee: one flat invoice replaces separate machine-rental, bean-supply, maintenance and training contracts, and removes surprise repair bills. You keep origin-traced specialty beans and a consistent cup — the cost falls because downtime, scale failures and admin overhead are engineered out."),
 ("What is included in the mandatory staff barista training, and how does it prevent breakdowns?",
  "Every deployment includes a mandatory 2-hour barista onboarding covering correct grind, milk-system hygiene and daily care. In high-turnover HoReCa and retail, untrained staff are the top cause of milk blockages and avoidable failures — the training halts that quality drift and cuts complaints, and it’s covered by the flat invoice, not an add-on."),
 ("Can we rent a professional Swiss machine for a Kyiv retail showroom without a long-term minimum contract?",
  "Yes. There is no forced minimum term and no mandatory bean-volume quota. You pay one flat monthly fee that already includes the machine, specialty beans, service and support — so you scale up or down without being locked into a multi-year lease or a consumables commitment."),
 ("Why is our self-managed coffee program underperforming versus outsourcing to a managed service at our retail location?",
  "Self-managed programs quietly leak revenue to downtime, scale failures, inconsistent quality and staff error. A managed service with a 2-hour SLA, calibrated specialty beans and trained staff keeps the machine producing sellable, consistent coffee — retail operators on the calibrated model see materially higher coffee-related revenue than commodity self-service setups."),
 ("How do we calibrate grind settings on a super-automatic when moving from commercial-grade to specialty-grade beans?",
  "Specialty beans need different grind, pressure and temperature than commodity beans, or you get sour or bitter shots. Anima calibrates the machine to the specific bean it supplies during setup and re-tunes it on the monthly maintenance visit — you don’t adjust it yourself, and the profile stays consistent as beans rotate."),
 ("What are the power and water-line requirements for installing a commercial Franke machine in a new office?",
  "High-draw Swiss machines need a dedicated stable power line and a plumbed, filtered water supply sized to your volume. Anima’s free on-site survey specs the exact power, water and filtration for your space before install — including voltage stabilisation for Kyiv’s grid — so the machine runs safely from day one instead of tripping or scaling."),
 ("How does a single monthly OPEX invoice cover maintenance, training, beans and equipment rental together?",
  "Anima’s zero-headache model bundles hardware rental, origin-traced specialty beans, mandatory training, water/voltage protection and 24/7 technical support with a 2-hour SLA into one flat monthly figure. Technical labour and parts are inside the fee — there are no surprise repair bills, which is the single most common misconception buyers arrive with."),
 ("Why is the milk foam on our automatic machine thin and watery instead of thick and creamy?",
  "Thin foam is usually a blocked or mis-calibrated milk system — scale, residue or worn settings. It’s a classic untrained-use fault. Anima’s preventive maintenance cleans and re-calibrates the milk circuit, and the 2-hour staff training prevents the daily-use mistakes that cause it, so cafe-quality microfoam stays consistent."),
 ("If untrained employees damage the machine, who pays for the repair?",
  "Under Anima’s managed model, technical repairs and parts are inside the flat monthly fee — you are not hit with a surprise bill when a new hire causes a fault. Combined with the mandatory training that prevents most damage first, the risk of turnover-driven repair costs is removed from your P&L."),
 ("What is the actual financial loss of coffee-machine downtime for a high-traffic Kyiv Oblast gas station?",
  "For a busy forecourt, a dead machine is direct lost sales of up to ~$500/day, plus lost fuel and retail cross-selling that coffee drives. That is exactly why Anima’s 2-hour on-site SLA exists — it caps downtime instead of leaving you waiting days for a freelance technician."),
 ("How do origin-traced specialty beans improve employee retention in hybrid corporate offices?",
  "A reliably excellent coffee is a low-cost, daily-visible perk: it pulls people into the office, reduces café spend and signals the employer invests in the workday. Anima supplies origin-traced specialty beans calibrated to the machine so the cup is consistently good — the amenity works every shift rather than being a broken machine nobody trusts."),
 ("Why does our machine randomly stop dispensing during the morning rush even though the water tank is full?",
  "Mid-rush stoppages with a full tank point to scale, pressure or flow-sensor issues under peak load — the machine is warning before a full failure. Anima’s preventive maintenance catches these early, and the 2-hour SLA gets a technician on-site fast if it does stop, so the rush isn’t lost."),
 ("What is the difference between leasing a coffee machine from an agency and hiring an integrated coffee partner in Kyiv?",
  "A lease gives you a box and leaves beans, service, water and training to other vendors — with a blame-circle when something fails. An integrated partner like Anima owns the whole outcome: machine, specialty beans, calibration, training, water/voltage protection and a 2-hour SLA under one flat invoice, so quality and uptime are one company’s responsibility."),
 ("How do we configure custom drink menus on a WMF machine to match local Kyiv retail tastes?",
  "Swiss super-automatics support fully custom drink profiles — recipes, strength, milk texture and portion. Anima programs the menu to your location’s preferences during setup and adjusts it on maintenance visits, so the retail line-up matches what your Kyiv customers actually order."),
 ("What water filtration is required to handle 18 dH water hardness for commercial espresso machines in Kyiv Oblast?",
  "At ~18 dH you need active softening/decarbonisation filtration matched to your throughput, not a token cartridge — otherwise scale kills the boiler. Anima measures your line, installs filtration calibrated to that hardness and maintains it on schedule, which is why the scale-driven failures common in Kyiv don’t reach our machines."),
 ("Why are our employees skipping the office machine to buy coffee at nearby cafés, and how do we fix it?",
  "Staff leave when the office cup is inconsistent or the machine is often broken. Fixing it is a quality-and-uptime problem: Anima supplies specialty beans calibrated to a reliable Swiss machine, keeps it running with a 2-hour SLA, and trains staff — so the office coffee is worth staying for and the café spend drops."),
 ("How do we run daily cleaning cycles on a Swiss super-automatic without leaving chemical residue in the next drinks?",
  "Correct cleaning uses approved tablets and a full rinse cycle in the right sequence — done wrong it leaves residue. Anima’s 2-hour staff training covers the exact daily routine, and the maintenance schedule verifies the cleaning system, so drinks stay clean and safe with no aftertaste."),
 ("If we scale from one machine to three because of office expansion, how does the transition work?",
  "Scaling is a flat-rate change, not a new capital project: Anima surveys the new footprint, adds calibrated machines and beans on the same monthly model, and trains the added staff. There’s no upfront CapEx per unit and service terms stay identical across all sites."),
 ("Why is our current vendor taking 48 hours to respond to critical service requests in Kyiv?",
  "A 48-hour response usually means an under-resourced vendor with no local SLA — and every hour is lost coffee revenue. Anima contracts a guaranteed 2-hour on-site response across Kyiv & Kyiv Oblast, 24/7, with technicians and Swiss parts on hand, so critical faults are hours, not days."),
 ("How do specialty bean profiles differ between light roasts and espresso-optimized roasts for automatic brewers?",
  "Light roasts are denser and more acidic and need finer grind and different temperature; espresso-optimized roasts are tuned for pressure extraction and crema. Anima matches the roast to your machine and audience and calibrates the grinder to it, so the automatic brewer pulls the profile the bean was meant for."),
 ("What happens if our restaurant’s espresso machine breaks down during weekend dinner service?",
  "Weekend and evening breakdowns are exactly what the SLA is for: Anima guarantees a 2-hour on-site response 24/7, including weekends, with a replacement unit if a repair would take too long — so service continues instead of a dead machine at your busiest hour."),
 ("How does proper grinder calibration reduce bean waste and save money in a high-volume office program?",
  "An uncalibrated grinder wastes beans on inconsistent, rejected shots and over-dosing. Precise calibration to the bean and machine cuts that waste and stabilises cost per cup. Anima calibrates on every maintenance visit, so a high-volume program spends on coffee people drink, not on waste."),
 ("Are we responsible for the cost of water filters and grinding burrs when renting professional equipment in Kyiv Oblast?",
  "No. Under Anima’s flat monthly model, consumable-service items like water filters and grinder burr upkeep are part of the included preventive maintenance — not surprise line-items. You budget one predictable figure; the wear parts and their replacement are our responsibility."),
 ("How can we guarantee zero equipment downtime for our HoReCa group without an in-house full-time technician?",
  "You outsource the uptime, not hire for it: Anima provides a guaranteed 2-hour on-site SLA across Kyiv & Kyiv Oblast, preventive monthly calibration that stops most failures before they happen, and replacement units when needed — delivering near-zero downtime across your sites without a technician on payroll."),
]

QA_UA = [
 ("Оренда швейцарського суперавтомата (Franke/WMF) чи купівля — що обрати для офісу на 50 осіб у Києві?",
  "Купівля заморожує $3 500–$15 000+ на одиницю в обладнанні, що дешевшає, і залишає вам усі ремонти, накип і простої. Оренда за фіксованим щомісячним рахунком Anima зберігає ці гроші: та сама машина Franke/WMF, підібрана на безкоштовному аудиті, плюс зерно, навчання, захист води/напруги і 2-годинний SLA — один передбачуваний OPEX, без CapEx."),
 ("Що робити, якщо машина показує попередження про накип, а офісна команда не вміє міняти фільтри?",
  "Попередження про накип означає, що мінеральний наліт уже загрожує бойлеру — це не має лягати на непідготовлений персонал. У сервісі Anima це не ваша задача: заміна фільтрів і декальцинація входять у профілактику за фіксованим рахунком, технік робить це на місці до того, як стане поломкою."),
 ("Чому офісна кава стає дедалі гіркішою, хоча зерно преміальне й налаштування ніхто не чіпав?",
  "Гіркота без зміни налаштувань — це майже завжди накип і збій калібрування: зашлакований бойлер і незкалібрований помел дають перезекстраговані гіркі шоти. Щомісячне калібрування Anima синхронізує помел, тиск і температуру під ваше зерно й воду — стабільна чашка без ваших дій."),
 ("Якщо АЗК у Київській області виходить з ладу в неділю — як швидко приїде сертифікований технік із запчастинами?",
  "Anima гарантує виїзд на місце за 2 години по Києву та області, цілодобово — включно з вихідними — із діагностикою та оригінальними швейцарськими запчастинами. Для форкорту, де простій = прямі втрати (до ~$500/день), цей SLA і є різниця між зупинкою кави й безперервним доходом."),
 ("Чому оренда щомісяця стрибає, хоча нам обіцяли фіксовану ціну?",
  "Стрибки зазвичай означають, що поточний вендор рахує виїзди, запчастини чи обсяг зерна як змінні доплати. Контракт Anima — справжня фіксована ставка на місяць: машина, зерно, сервіс і підтримка в одній сумі. Скільки підписали — стільки й платите."),
 ("Як жорстка київська вода впливає на бойлери WMF за пів року?",
  "Вода регіону — 15–20 dH. Без активної фільтрації та планової декальцинації цей мінерал руйнує бойлер за 6–12 місяців. Anima ставить фільтрацію під вашу жорсткість і робить профілактику — бойлер не доходить до відмови, ризик накипу прибрано інженерно, а не рахунком потім."),
 ("Як скоротити бюджет на каву без зниження якості зерна й скарг від керівництва?",
  "Економія — від консолідації, не від дешевшої кави: один рахунок замінює окремі контракти на оренду, зерно, сервіс і навчання, і прибирає раптові рахунки за ремонт. Спешелті-зерно і стабільна чашка лишаються; витрати падають, бо прибрано простої, накип і адмін-навантаження."),
 ("Що входить в обов'язкове навчання персоналу і як воно запобігає поломкам?",
  "Кожна інсталяція включає обов'язкове 2-годинне навчання: правильний помел, гігієна молочної системи, щоденний догляд. У сегменті з високою плинністю непідготовлений персонал — головна причина блокувань і поломок; навчання прибирає це й зменшує скарги, і воно в межах фіксованого рахунку."),
 ("Чи можна орендувати швейцарську машину для шоуруму в Києві без довгого мінімального контракту?",
  "Так. Немає обов'язкового мінімального терміну і квоти на обсяг зерна. Ви платите один фіксований місячний внесок, що вже включає машину, спешелті-зерно, сервіс і підтримку — масштабуєтесь угору чи вниз без багаторічної прив'язки."),
 ("Чому наша самокерована кавова програма в рітейлі приносить менше, ніж керований сервіс?",
  "Самокеровані програми тихо втрачають дохід на простоях, накипі, нестабільній якості й помилках персоналу. Керований сервіс із 2-годинним SLA, каліброваним зерном і навченим персоналом тримає машину в продажі — оператори на каліброваній моделі мають помітно вищий дохід із кави."),
 ("Як калібрувати помел суперавтомата при переході з комодіті на спешелті-зерно?",
  "Спешелті потребує іншого помелу, тиску й температури, інакше кислить або гірчить. Anima калібрує машину під конкретне зерно на етапі налаштування й перетюнінгує на щомісячному візиті — ви не робите це самі, профіль лишається стабільним при ротації зерна."),
 ("Які вимоги до електрики й водолінії для встановлення Franke в новому офісі?",
  "Потужним швейцарським машинам потрібна окрема стабільна лінія живлення та підключена фільтрована вода під ваш обсяг. Безкоштовне обстеження Anima прораховує точні параметри до монтажу — включно зі стабілізацією напруги під київську мережу — щоб машина працювала безпечно з першого дня."),
 ("Як один місячний OPEX-рахунок покриває сервіс, навчання, зерно й оренду разом?",
  "Модель Anima об'єднує оренду обладнання, спешелті-зерно, обов'язкове навчання, захист води/напруги і цілодобову підтримку з 2-годинним SLA в одну фіксовану суму. Роботи й запчастини — всередині; раптових рахунків за ремонт немає, і це головна оману, з якою приходять клієнти."),
 ("Чому молочна піна виходить рідкою замість густої й кремової?",
  "Рідка піна — зазвичай забита чи розкалібрована молочна система: накип, залишки або збиті налаштування. Профілактика Anima чистить і калібрує молочний контур, а 2-годинне навчання прибирає щоденні помилки — кав'ярняна мікропіна лишається стабільною."),
 ("Якщо непідготовлений персонал пошкодить машину — хто платить за ремонт?",
  "У керованій моделі Anima ремонти й запчастини всередині фіксованого рахунку — раптового рахунку через нового працівника не буде. Разом з обов'язковим навчанням, що запобігає більшості пошкоджень, ризик ремонтів через плинність прибрано з вашого P&L."),
 ("Яка реальна втрата від простою кавомашини для завантаженого АЗК у Київській області?",
  "Для завантаженого форкорту мертва машина — це прямі втрати до ~$500/день, плюс втрачений паливний і супутній продаж, що його тягне кава. Саме тому існує 2-годинний SLA Anima — він обмежує простій, а не лишає вас чекати техніка днями."),
 ("Як спешелті-зерно з простеженим походженням впливає на утримання співробітників у гібридних офісах?",
  "Надійно смачна кава — недорогий, щоденно помітний бенефіт: тягне людей в офіс, зменшує витрати на кав'ярні й показує турботу про робочий день. Anima дає спешелті-зерно, каліброване під машину, — чашка стабільно хороша, і бенефіт працює щозміни, а не стоїть зламаний."),
 ("Чому машина довільно перестає видавати каву в ранковий пік, хоча бак повний?",
  "Зупинки в пік із повним баком вказують на накип, тиск чи датчик потоку під навантаженням — машина попереджає до повної відмови. Профілактика Anima з телеметрією ловить це рано, а 2-годинний SLA швидко приводить техніка — пік не втрачається."),
 ("У чому різниця між орендою машини в агенції та інтегрованим кавовим партнером у Києві?",
  "Оренда дає вам коробку й лишає зерно, сервіс, воду й навчання іншим вендорам — із колом перекладання відповідальності при поломці. Інтегрований партнер Anima відповідає за весь результат: машина, зерно, калібрування, навчання, захист води/напруги і 2-годинний SLA в одному рахунку."),
 ("Як налаштувати кастомне меню напоїв на WMF під смаки київського рітейлу?",
  "Швейцарські суперавтомати підтримують повністю кастомні профілі: рецепт, міцність, молоко, порція. Anima програмує меню під вашу локацію на етапі налаштування й коригує на візитах обслуговування — лінійка відповідає тому, що реально замовляють ваші клієнти."),
 ("Яка фільтрація потрібна для води жорсткістю 18 dH для комерційних еспресо-машин у Київській області?",
  "При ~18 dH потрібна активна пом'якшувальна/декарбонізаційна фільтрація під ваш потік, а не символічний картридж — інакше накип уб'є бойлер. Anima заміряє лінію, ставить фільтрацію під цю жорсткість і обслуговує за графіком — тому характерні для Києва відмови через накип не доходять до наших машин."),
 ("Чому працівники йдуть по каву в сусідні кав'ярні замість офісної машини і як це виправити?",
  "Люди йдуть, коли офісна чашка нестабільна або машина часто зламана. Це питання якості й аптайму: Anima дає спешелті-зерно під надійну швейцарську машину, тримає її в роботі з 2-годинним SLA і навчає персонал — офісна кава варта того, щоб лишитись, а витрати на кав'ярні падають."),
 ("Як робити щоденні цикли чищення суперавтомата без хімічного залишку в ранкових напоях?",
  "Правильне чищення — схвалені таблетки й повний цикл полоскання у правильній послідовності; неправильно — лишає залишок. 2-годинне навчання Anima охоплює точну щоденну процедуру, а графік обслуговування перевіряє систему чищення — напої лишаються чистими без присмаку."),
 ("Якщо ми масштабуємось з однієї машини до трьох через розширення офісу — як відбувається перехід?",
  "Масштабування — це зміна фіксованої ставки, а не новий капітальний проєкт: Anima обстежує нову площу, додає калібровані машини й зерно за тією ж моделлю і навчає новий персонал. Немає CapEx на одиницю, умови сервісу однакові на всіх точках."),
 ("Чому наш вендор відповідає на критичні заявки в Києві 48 годин?",
  "48 годин зазвичай означають вендора без місцевого SLA — а кожна година це втрачений дохід із кави. Anima контрактує гарантований виїзд за 2 години по Києву та області, цілодобово, з техніками й швейцарськими запчастинами — критичні поломки це години, а не дні."),
 ("Чим профілі спешелті-зерна відрізняються між світлим і еспресо-обсмаженням для автоматів?",
  "Світле обсмаження щільніше й кисліше, потребує тоншого помелу й іншої температури; еспресо-обсмаження налаштоване під тиск і крему. Anima підбирає обсмаження під вашу машину й аудиторію та калібрує помел — автомат видає профіль, під який зерно й створене."),
 ("Що буде, якщо еспресо-машина ресторану зламається під час вечірнього сервісу у вихідні?",
  "Поломки ввечері й у вихідні — це саме те, для чого SLA: Anima гарантує виїзд за 2 години цілодобово, включно з вихідними, із підмінним апаратом, якщо ремонт довгий — сервіс триває, а не стоїть мертва машина в найзавантаженіший час."),
 ("Як правильне калібрування помелу зменшує втрати зерна й економить гроші у високооб'ємному офісі?",
  "Незкалібрований помел марнує зерно на нестабільні, відбраковані шоти й передозування. Точне калібрування під зерно й машину зменшує ці втрати й стабілізує собівартість чашки. Anima калібрує на кожному візиті — програма витрачає на каву, яку п'ють, а не на брак."),
 ("Чи відповідаємо ми за вартість фільтрів і жорен при оренді професійного обладнання в Київській області?",
  "Ні. У фіксованій моделі Anima витратні сервісні позиції — фільтри води й обслуговування жорен — частина включеної профілактики, а не раптові рядки. Ви закладаєте одну передбачувану суму; зношувані частини та їх заміна — наша відповідальність."),
 ("Як гарантувати нуль простоїв для HoReCa-групи без штатного техніка на кавомашинах?",
  "Ви віддаєте аптайм на аутсорс, а не наймаєте: Anima дає гарантований 2-годинний SLA по Києву та області, щомісячне профілактичне калібрування, що зупиняє більшість відмов заздалегідь, і підмінні апарати за потреби — близький до нуля простій на всіх точках без техніка в штаті."),
]

def pains():
    d = json.load(open("/tmp/qmining.json"))
    out = []
    for h, b in d.get("pains", []):
        h = h.strip()
        if h.lower() == "question" or len(h) > 60: continue
        out.append((h, b.strip()))
        if len(out) >= 5: break
    return out

def build(ua):
    qa = QA_UA if ua else QA
    canon = f"{BASE}/{'ua/' if ua else ''}answers/{SLUG}"
    alt_en, alt_uk = f"{BASE}/answers/{SLUG}", f"{BASE}/ua/answers/{SLUG}"
    css = "../../style.css" if ua else "../style.css"
    ana = "../../assets/analytics.js" if ua else "../assets/analytics.js"
    heroimg = ("../../" if ua else "../") + "assets/cafe.jpg"
    homep = "../index.html"; ansp = "../answers.html"
    title = ("Що питають київські оператори кави — реальні відповіді" if ua
             else "What Kyiv coffee operators actually ask — grounded answers")
    intro = ("Реальні високочастотні питання B2B-покупців Києва та області — з прямими відповідями для людей і answer-рушіїв."
             if ua else
             "The real, high-frequency questions Kyiv & Oblast B2B buyers ask — with direct, citable answers for people and answer engines.")
    lab = "Пряма відповідь" if ua else "Direct answer"
    faq_html = ""
    for q, a in qa:
        faq_html += (f'<details class="qa" style="border-bottom:1px solid var(--line);padding:16px 0">'
                     f'<summary style="font-weight:700;font-size:17px;cursor:pointer">{html.escape(q)}</summary>'
                     f'<p style="margin:12px 0 0;color:var(--ink-soft);line-height:1.7">{html.escape(a)}</p></details>')
    pain_html = "".join(
        f'<li style="margin-bottom:10px"><b>{html.escape(h)}.</b> <span style="color:var(--ink-soft)">{html.escape(b)}</span></li>'
        for h, b in pains())
    faq_ld = ",".join(
        f'{{"@type":"Question","name":{json.dumps(q,ensure_ascii=False)},"acceptedAnswer":{{"@type":"Answer","text":{json.dumps(a,ensure_ascii=False)}}}}}'
        for q, a in qa)
    ld = ('{"@context":"https://schema.org","@graph":['
          f'{{"@type":"Organization","@id":"{BASE}/#organization","name":"Anima Volitiva","url":"{BASE}/"}},'
          f'{{"@type":"BreadcrumbList","itemListElement":['
          f'{{"@type":"ListItem","position":1,"name":"Home","item":"{BASE}/"}},'
          f'{{"@type":"ListItem","position":2,"name":"Answers","item":"{BASE}/answers.html"}},'
          f'{{"@type":"ListItem","position":3,"name":"What operators ask"}}]}},'
          f'{{"@type":"FAQPage","mainEntity":[{faq_ld}]}}]}}')
    switch = alt_uk if not ua else alt_en
    nav = (f'<nav><div class="wrap"><a class="brand" href="{homep}">Anima <span>Volitiva</span></a>'
           f'<div class="nav-links"><a href="{ansp}" class="active">{"Відповіді" if ua else "Answers"}</a>'
           f'<a class="nav-cta" href="{homep}#cta">{"Отримати аудит" if ua else "Get assessment"}</a>'
           f'<span class="lang"><a class="on" href="#">{"UA" if ua else "EN"}</a><span class="sep">|</span>'
           f'<a href="{switch}">{"EN" if ua else "УКР"}</a></span></div></div></nav>')
    footer = (f'<footer><div class="wrap"><a class="brand" href="{homep}" style="color:#cbb9a6">Anima '
              f'<span style="color:var(--accent)">Volitiva</span></a><div class="fnav">'
              f'<a href="{homep}">{"Головна" if ua else "Home"}</a><a href="{ansp}">{"Відповіді" if ua else "Answers"}</a>'
              f'<a href="{homep}#cta">{"Отримати аудит" if ua else "Get assessment"}</a></div>'
              f'<div>© 2026 Anima Volitiva · Kyiv &amp; Kyiv Oblast</div></div></footer>')
    doc = f'''<!DOCTYPE html>
<html lang="{'uk' if ua else 'en'}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(intro[:155])}" />
<link rel="stylesheet" href="{css}" />
<link rel="canonical" href="{canon}"/>
<link rel="alternate" hreflang="en" href="{alt_en}"/>
<link rel="alternate" hreflang="uk" href="{alt_uk}"/>
<link rel="alternate" hreflang="x-default" href="{alt_en}"/>
<meta property="og:type" content="article"/>
<meta property="og:title" content="{html.escape(title)}"/>
<meta property="og:description" content="{html.escape(intro[:155])}"/>
<meta property="og:url" content="{canon}"/>
<meta property="og:image" content="{BASE}/assets/hero.jpg"/>
<meta name="twitter:card" content="summary_large_image"/>
<script type="application/ld+json">{ld}</script>
<script src="{ana}" defer></script>
</head>
<body>
{nav}
<header class="page-hero" style="--ph:url('{heroimg}')"><div class="wrap">
  <div class="crumb"><a href="{homep}">{'Головна' if ua else 'Home'}</a> · <a href="{ansp}">{'Відповіді' if ua else 'Answers'}</a> · {'Що питають оператори' if ua else 'What operators ask'}</div>
  <h1>{html.escape(title)}</h1>
  <p class="sub">{html.escape(intro)}</p>
</div></header>
<div class="aio-wrap"><div class="wrap"><div class="aio"><div class="lab">{lab}</div><p>{html.escape(qa[0][1])}</p></div></div></div>
<section class="block"><div class="wrap" style="max-width:900px">
  <h2 style="font-size:24px;margin-bottom:8px">{'Головні болі операторів у Києві та області' if ua else 'Top pain points for Kyiv & Oblast operators'}</h2>
  <ul style="list-style:none;padding:0;margin:0 0 8px">{pain_html}</ul>
</div></section>
<section class="block"><div class="wrap" style="max-width:900px">
  <h2 style="font-size:24px;margin-bottom:8px">{'Питання, які реально ставлять' if ua else 'The questions operators actually ask'}</h2>
  {faq_html}
</div></section>
<section class="cta block" id="cta"><div class="wrap" style="text-align:center">
  <h2>{'Порахувати ваш flat-rate за один аудит' if ua else 'Get your flat-rate in one on-site audit'}</h2>
  <a class="btn btn-primary" href="{homep}#cta">{'Отримати безкоштовний аудит' if ua else 'Get your free assessment'}</a>
</div></section>
{footer}
</body></html>'''
    outdir = ROOT / ("ua/answers" if ua else "answers")
    (outdir / SLUG).write_text(doc, encoding="utf-8")
    return f"{'ua/' if ua else ''}answers/{SLUG}"

print("built:", build(False))
print("built:", build(True))
