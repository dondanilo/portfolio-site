# Сайт-визитка Данила Ульянова

Сопроводительное письмо + презентация + опыт из LinkedIn в одном сайте, с упором на современную анимацию.

## Как устроено

- `src/index.html` — исходник страницы: главный экран (фон — жидкий металл на WebGL), цифры, бренды, путь, кейсы, подход CMO, event-маркетинг, AI, приложения, образование, контакты.
- `content/events.json` — мероприятия для блока event-маркетинга (добавляются через `tools/add_event.py`).
- `assets/` — портрет, логотипы, сертификаты, фото мероприятий, картинка превью ссылки (`og.jpg`).
- `tools/build.py` — собирает сайт в `dist/`: мелкие картинки вшивает в html, фото мероприятий кладёт файлами.
- `content/i18n/{en,el,es}.json` — переводы: `{"русская фраза": "перевод"}` (см. «Языки»).
- `src/archive/` — прошлые варианты главного экрана.
- `tools/vision.swift`, `tools/landmarks.swift`, `tools/clean_cutout.py` — вырезка портрета без светлой обводки (macOS Vision, локально).

## Публикация

Каждый push в `main` → GitHub Actions собирает сайт и выкладывает его на GitHub Pages (`.github/workflows/deploy.yml`).

Адрес: **https://cmo.getdone.kz** — CNAME `cmo` → `dondanilo.github.io` в DNS getdone.kz (Hoster.kz), домен прописан в настройках Pages.

Локально посмотреть:

```sh
python3 tools/build.py
open dist/index.html
```

## Языки и тема

Сайт на четырёх языках: русский — `cmo.getdone.kz`, английский — `/en/`, греческий — `/el/`, испанский — `/es/`.
Переключатель RU · EN · EL · ES и кнопка светлой/тёмной темы — в меню (тема по умолчанию — как в системе, выбор запоминается).

- В `src/index.html` и `cv/index.html` переводимые строки размечены `{{русская фраза}}`. Новый русский текст можно
  разметить автоматически: `python3 tools/i18n_mark.py src/index.html` (фразы с `<br>`/`<em>` внутри — оборачивать целиком руками).
- Перевод — в `content/i18n/<язык>.json` с ключом-русской фразой. Изменили русскую фразу — поменяйте и ключ в трёх словарях.
- `python3 tools/build.py` предупреждает о строках без перевода (там остаётся русский); `--strict` — падает.
- Тексты мероприятий из `content/events.json` тоже переводятся через словари; месяц в дате пишется из поля `iso` сам.
- Превью ссылок (`og.jpg`, `og-en.jpg`, …) снимаются с первого экрана: `python3 tools/build.py && node tools/build_og.mjs`.

## PDF-резюме

`cv/index.html` — резюме на 2 страницы A4 (тексты те же, что на сайте; при правках сайта обновлять и здесь).
Собрать PDF: `node tools/build_cv.mjs` → `assets/Danil_Ulyanov_CV.pdf`, `…_CV_EN.pdf`, `…_CV_EL.pdf`, `…_CV_ES.pdf`
(нужен Google Chrome; можно один язык: `node tools/build_cv.mjs en`). Скрипт предупреждает, если перевод не влез в 2 страницы.
PDF коммитятся, `tools/build.py` кладёт их в корень сайта — кнопки «CV / Резюме» на каждой языковой версии ведут на свой PDF.

## Новое мероприятие

```sh
venv/bin/python tools/add_event.py --id <slug> --title "…" --date "…" --city "…" [--role "…"] [--scale "…"] [--text "…"] [--logo assets/logos/….png] фото1.jpg фото2.jpg …
python3 tools/build.py
```

Первое фото — обложка. Для add_event.py нужен Pillow.

## Пока сайт в работе

В `src/index.html` стоит `<meta name="robots" content="noindex">` — поисковики сайт не индексируют. Убрать, когда всё будет готово.
