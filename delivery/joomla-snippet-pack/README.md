# Joomla snippet pack — animacoffee.com.ua

Install pack for the client's own main site, https://animacoffee.com.ua/ (Joomla). Nothing here is published by us. The live site currently has no JSON-LD and `/llms.txt` returns 404.

IMPORTANT: these changes affect the client's live site. The client must approve before anything is applied.

## Files

| File | What it is |
|---|---|
| `jsonld-localbusiness.html` | One schema.org JSON-LD block (LocalBusiness / ProfessionalService) with a leading comment on where to paste it. |
| `llms.txt` | Plain-text file for the web root, served at `https://animacoffee.com.ua/llms.txt`. Ukrainian first, short English parts. |
| `INSTALL.uk.md` | Short install guide in Ukrainian for the client's web admin. |

## Source-approved facts

Only these facts are used: brand "Anima Volitiva"; B2B coffee-machine rental and full service for HoReCa, offices and retail; Kyiv and Kyiv Oblast; Bila Tserkva, 29a Pavlichenko St.; phone +38 (073) 873 01 45; animacoffeeco@gmail.com; Mon-Sat 09:00-17:00, closed Sunday; founded 2015; 1,700+ active B2B clients; support 24/7 with technician or replacement machine within 24 hours; delivery and installation within 24 hours; free 14-day trial without prepayment; individual quote with packages Start/Pro/Max and no published prices; staff training included; Dr. Coffee and Necta super-automatics plus La Spaziale, Nuova Simonelli, Rancilio, Iberital, Astoria, Fiorenzato espresso machines; premium roasted coffee; the listed social profiles. Do not add other claims or numbers.

## Install (Joomla)

1. Get written approval from the client.
2. Paste the `<script type="application/ld+json">` block from `jsonld-localbusiness.html` into the `<head>` of the home page only, using a "custom code / head" plugin or the template's custom head field, or the template `index.php` before `</head>`. Do not remove the existing GTM-W42FSJWF container.
3. Upload `llms.txt` to the web root (next to `index.php`) via the hosting file manager or FTP.
4. Verify: run the home page URL through Google Rich Results Test, and run `curl -I https://animacoffee.com.ua/llms.txt` (expect HTTP 200 and a text content type).
5. Confirm GTM still fires and the page renders unchanged; tell the delivering team the result.

## Rollback

Remove the pasted JSON-LD block and delete `llms.txt` from the web root; the site returns to its previous state.
