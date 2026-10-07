# Сайт-визитка Данила Ульянова

Сопроводительное письмо + презентация + опыт из LinkedIn в одном сайте, с упором на современную анимацию.

## Как устроено

- `src/index.html` — исходник страницы: главный экран (фон — жидкий металл на WebGL), цифры, бренды, путь, кейсы, подход CMO, event-маркетинг, AI, приложения, образование, контакты.
- `content/events.json` — мероприятия для блока event-маркетинга (добавляются через `tools/add_event.py`).
- `assets/` — портрет, логотипы, сертификаты, фото мероприятий, картинка превью ссылки (`og.jpg`).
- `tools/build.py` — собирает сайт в `dist/`: мелкие картинки вшивает в html, фото мероприятий кладёт файлами.
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

## PDF-резюме

`cv/index.html` — резюме на 2 страницы A4 (тексты те же, что на сайте; при правках сайта обновлять и здесь).
Собрать PDF: `node tools/build_cv.mjs` → `assets/Danil_Ulyanov_CV.pdf` (нужен Google Chrome). PDF коммитится,
`tools/build.py` кладёт его в корень сайта — на него ведут все кнопки «CV / Резюме, PDF».

## Новое мероприятие

```sh
venv/bin/python tools/add_event.py --id <slug> --title "…" --date "…" --city "…" [--role "…"] [--scale "…"] [--text "…"] [--logo assets/logos/….png] фото1.jpg фото2.jpg …
python3 tools/build.py
```

Первое фото — обложка. Для add_event.py нужен Pillow.

## Пока сайт в работе

В `src/index.html` стоит `<meta name="robots" content="noindex">` — поисковики сайт не индексируют. Убрать, когда всё будет готово.
