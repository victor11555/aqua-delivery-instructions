---
source: https://howto.aqua-delivery.com/%D0%A3%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B0-pop-up%D0%B0-%D0%BD%D0%B0-%D1%81%D0%B2%D0%BE%D0%B9-%D1%81%D0%B0%D0%B9%D1%82
---

# Установка Pop-up’а на свой сайт — База знаний Aqua Delivery

#### Запрос Pop-up’а

Для получения pop-up’а необходимо обратиться в службу поддержки Aqua Delivery с соответствующим вопросом. После подготовки pop-up’а вам предоставят html и css файл для встраивания. Для работы pop-up’а на сайте необходима библиотека jquery. Подключить ее можно добавив запись

`<script type="text/javascript" language="javascript" src="https://code.jquery.com/jquery-3.3.1.min.js"></script>`

в шаблон сайта, либо к страницам внутри тега `<head></head>.`

#### Установка на сайт

Содержимое html файла необходимо добавить в шаблон сайта, либо к страницам внутри тега `<body></body>` без родительских элементов.

Также нужно добавить эту строку

`<link rel="stylesheet" href="https://stock.app11.ru/company/css/popup/style.css">`

внутри тега `<head></head>` в шаблон сайта, либо к необходимым страницам.

В виде альтернативы можно добавить css к стилям на сайте.