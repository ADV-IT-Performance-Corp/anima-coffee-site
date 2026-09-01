#!/usr/bin/env python3
from pathlib import Path
import re, json
ROOT=Path(__file__).resolve().parents[1]
files=[p for p in ROOT.rglob('*') if p.suffix in {'.html','.txt'} and 'node_modules' not in p.parts]
counts={}
def sub(text, pattern, repl, key, flags=re.I):
    text,n=re.subn(pattern,repl,text,flags=flags); counts[key]=counts.get(key,0)+n; return text
for path in files:
    s=path.read_text(encoding='utf-8')
    ua='ua' in path.parts
    new_client='1 700+ активних B2B-клієнтів' if ua else '1,700+ active B2B clients'
    s=sub(s,r'(?<!\d)(?:1,300\+|1 300\+|1300\+|more than 1,300|понад 1 300)(?:\s+(?:B2B[- ]?(?:partners|партнерів)|businesses|бізнесів))?',new_client,'A client-count')
    s=sub(s,r'\s*(?:,|—|;)?\s*(?:with )?retro-?bonuses? up to 5% for (?:regular )?(?:clients|partners|regulars)','', 'E retro-bonus')
    s=sub(s,r'\s*(?:,|—|;)?\s*ретро-?бонусами? до 5% (?:для )?(?:постійних )?(?:клієнтів|партнерів)','', 'E retro-bonus')
    s=sub(s,r'\s*(?:,|—|;)?\s*(?:and )?a free first (?:rental )?month for HoReCa clients?','', 'D free-month')
    s=sub(s,r'\s*(?:,|—|;)?\s*(?:для HoReCa\s*[—–-]\s*)?перший місяць оренди безкоштовно','', 'D free-month')
    s=sub(s,r'Three (?:price|pricing) tiers(?: plus retro-bonuses up to 5% (?:for regular (?:clients|partners)|for regulars))?', 'Three equipment packages — Start, Pro, Max — matched to the venue format (office, HoReCa, retail); pricing is quoted per venue.', 'F packages')
    s=sub(s,r'(?:across |one of |through )three (?:price|pricing) tiers', 'Three equipment packages — Start, Pro, Max — matched to the venue format (office, HoReCa, retail); pricing is quoted per venue', 'F packages')
    s=sub(s,r'(?:трьома|трьох) (?:ціновими рівнями|ціновими рівнями|тарифними пакетами)', 'Три пакети обладнання — Start, Pro, Max — підібрані під формат закладу (офіс, HoReCa, рітейл); ціна розраховується для кожного закладу.', 'F packages')
    s=sub(s,r'по (?:трьох|трьома) тарифах?', 'Три пакети обладнання — Start, Pro, Max — підібрані під формат закладу (офіс, HoReCa, рітейл); ціна розраховується для кожного закладу', 'F packages')
    s=sub(s,r'hello@animacoffee\.com\.ua','animacoffeeco@gmail.com','I email')
    s=sub(s,r'Kyiv, Bila Tserkva','Kyiv Oblast, Bila Tserkva','J address')
    s=sub(s,r'Київ,\s*Біла Церква','Київська обл., Біла Церква','J address')
    s=sub(s,r'24/7 support(?: line)?\s*[—,:;]?\s*(?:a )?technician or (?:a )?replacement machine (?:is provided )?within 24 hours(?:; same-day service is available where operationally possible)?','Support 24/7; a technician or a replacement machine within 24 hours.','H SLA')
    s=sub(s,r'Підтримка 24/7\s*[—,:;]?\s*(?:технік або )?підмінна машина\s*[—:]?\s*протягом 24 годин(?:;[^.]*|\.)?','Підтримка 24/7; технік або підмінна машина протягом 24 годин.','H SLA')
    s=sub(s,r'contract excerpt|as per the contract (?:clause)?','', 'H contract wording')
    s=sub(s,r'акт приймання[^<.]*|acceptance act[^<.]*','', 'N signer placeholders')
    # Catch remaining prose and JSON-LD variants after the primary substitutions.
    s=sub(s,r'(?:over |more than |понад )?1[ ,]300\+?(?:\s+(?:B2B[- ]?(?:partners|партнерів)|businesses|бізнесів))?',new_client,'A client-count residual')
    s=sub(s,r'\s*(?:and |, )?(?:regular clients (?:earn |get )?|і постійні клієнти (?:отримують )?)?retro-?bonuses?(?: of)? up to 5%[^.<>]*[.]?','', 'E retro-bonus residual')
    s=sub(s,r'\s*(?:and |, )?(?:regular clients (?:earn |get )?|і постійні клієнти (?:отримують )?)?ретро-?бонуси?(?: до)? 5%[^.<>]*[.]?','', 'E retro-bonus residual')
    s=sub(s,r'\s*(?:and |, |; )?(?:HoReCa clients get |для (?:закладів |клієнтів )?HoReCa\s*[—–-]\s*)?(?:the |a |безкоштовний )?first (?:rental )?month (?:free|for HoReCa clients?)[^.<>]*[.]?','', 'D free-month residual')
    s=sub(s,r'\s*(?:and |, |; )?(?:для (?:закладів |клієнтів )?HoReCa\s*[—–-]\s*)?(?:безкоштовний )?перший місяць оренди(?: для (?:клієнтів |закладів )?HoReCa)?[^.<>]*[.]?','', 'D free-month residual')
    s=sub(s,r'(?:(?:across |within |over )?(?:three|3) (?:price|pricing|tariff) tiers|(?:three|3) tiers|3 price tiers)', 'Three equipment packages — Start, Pro, Max — matched to the venue format (office, HoReCa, retail); pricing is quoted per venue', 'F packages residual')
    s=sub(s,r'(?:(?:за |у межах )?(?:трьома|трьох|3) (?:ціновими |тарифними )?(?:рівнями|тарифами|пакетами)|3 тарифні рівні)', 'Три пакети обладнання — Start, Pro, Max — підібрані під формат закладу (офіс, HoReCa, рітейл); ціна розраховується для кожного закладу', 'F packages residual')
    s=sub(s,r'\s*on any breakdown, same-day where operationally possible','', 'H SLA residual')
    s=sub(s,r'\s*у разі поломки[^.<>]*','', 'H SLA residual')
    # Literal variants left inside markup/legacy answer blocks.
    s=sub(s,r'1,300|1 300|1300', new_client, 'A literal residual', 0)
    s=sub(s,r'(?:and |, )?retro-?bonus(?:es)?(?: of| up)? to 5%[^.<>]*', '', 'E literal residual')
    s=sub(s,r'(?:і |, )?ретро-?бонус(?:и)?(?: до)? 5%[^.<>]*', '', 'E literal residual')
    s=sub(s,r'(?:a |the )?free first (?:rental )?month[^.<>]*', '', 'D literal residual')
    s=sub(s,r'(?:безкоштовний )?перший місяць оренди[^.<>]*', '', 'D literal residual')
    # Update Organization JSON-LD fields used throughout the static files.
    social='["https://www.facebook.com/anima.volitiva","https://www.instagram.com/animacoffeeco/","https://www.tiktok.com/@animacoffeeco","https://t.me/Animavolitiva"]'
    s=sub(s,r'"sameAs":\[[^\]]*\]', '"sameAs":'+social, 'M sameAs', 0)
    s=sub(s,r'"foundingDate":"2015",(?="sameAs")', '"foundingDate":"2015","openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],"opens":"09:00","closes":"17:00"}],', 'K JSON-LD hours', 0)
    if ua:
        s=sub(s,r'"addressRegion":"Київ","addressLocality":"Біла Церква","streetAddress":"вул\. Павліченко 29а"', '"addressRegion":"Київська обл.","addressLocality":"Біла Церква","streetAddress":"вул. Павліченко 29а"', 'J JSON-LD UA address', 0)
    else:
        s=sub(s,r'"addressRegion":"Київ","addressLocality":"Біла Церква","streetAddress":"вул\. Павліченко 29а"', '"addressRegion":"Kyiv Oblast","addressLocality":"Bila Tserkva","streetAddress":"29a Pavlichenko St."', 'J JSON-LD EN address', 0)
    path.write_text(s,encoding='utf-8')
print(json.dumps(counts,ensure_ascii=False,indent=2))
