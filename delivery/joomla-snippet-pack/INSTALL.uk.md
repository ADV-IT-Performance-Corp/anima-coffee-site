# Інструкція для веб-адміністратора — animacoffee.com.ua (Joomla)

Ці зміни стосуються робочого сайту клієнта. Застосовувати лише після письмового погодження клієнтом.

1. Відкрийте файл `jsonld-localbusiness.html` і скопіюйте блок `<script type="application/ld+json"> ... </script>`.
2. Вставте його в `<head>` лише головної сторінки: через плагін «custom code / head» (Extensions > Plugins), поле custom head у шаблоні або `index.php` шаблону перед `</head>`. Наявний контейнер Google Tag Manager GTM-W42FSJWF не видаляйте.
3. Завантажте файл `llms.txt` у корінь сайту (поруч із `index.php`) через файловий менеджер хостингу або FTP.
4. Перевірте: головну сторінку в Google Rich Results Test; команда `curl -I https://animacoffee.com.ua/llms.txt` має показати HTTP 200.
5. Переконайтеся, що сайт виглядає як раніше і GTM працює.

Відкат: видаліть вставлений блок JSON-LD і файл `llms.txt` з кореня сайту.
