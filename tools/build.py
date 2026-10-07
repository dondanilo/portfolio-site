"""Собирает сайт в dist/ из src/index.html — на четырёх языках.

- Русский — в корне (cmo.getdone.kz), остальные — в папках: /en/, /el/, /es/.
- Переводимые строки в шаблоне размечены {{русская фраза}} (см. tools/i18n_mark.py);
  переводы лежат в content/i18n/<язык>.json: {"русская фраза": "перевод"}.
  Нет перевода — подставится русский текст и сборка предупредит (с флагом --strict — упадёт).
- Служебные метки: {{_lang}}, {{_p}} (префикс пути до корня), {{_cv}}, {{_path}}, {{_oglocale}},
  <!--LANGS--> (переключатель языков), <!--HREFLANG--> (альтернативные версии для поисковиков).
- Картинки вида @@assets/... вшиваются как data URI (мелкие: логотипы, портрет, сертификаты).
- Блок мероприятий рендерится из content/events.json на место <!--EVENTS-->.
  Фото мероприятий НЕ вшиваются — копируются в dist/assets/events/ и грузятся файлами.
- Нужна только стандартная библиотека Python — так сборка работает и локально, и в GitHub Actions."""
import base64, functools, html, json, mimetypes, pathlib, re, shutil, sys

root = pathlib.Path(__file__).resolve().parent.parent
dist = root / "dist"
mimetypes.add_type("image/webp", ".webp")
SITE = "https://cmo.getdone.kz/"

# код, подпись в переключателе, og:locale, имя PDF-резюме
LANGS = [
    ("ru", "RU", "ru_RU", "Danil_Ulyanov_CV.pdf"),
    ("en", "EN", "en_US", "Danil_Ulyanov_CV_EN.pdf"),
    ("el", "EL", "el_GR", "Danil_Ulyanov_CV_EL.pdf"),
    ("es", "ES", "es_ES", "Danil_Ulyanov_CV_ES.pdf"),
]
MONTHS = {
    "ru": "Январь Февраль Март Апрель Май Июнь Июль Август Сентябрь Октябрь Ноябрь Декабрь",
    "en": "January February March April May June July August September October November December",
    "el": "Ιανουάριος Φεβρουάριος Μάρτιος Απρίλιος Μάιος Ιούνιος Ιούλιος Αύγουστος Σεπτέμβριος Οκτώβριος Νοέμβριος Δεκέμβριος",
    "es": "Enero Febrero Marzo Abril Mayo Junio Julio Agosto Septiembre Octubre Noviembre Diciembre",
}
CYR = re.compile("[А-Яа-яЁё]")


def tr_mark(text):
    """Экранирует строку из данных и размечает её для перевода, если она русская."""
    t = html.escape(text)
    return "{{" + t + "}}" if CYR.search(t) else t


def load_dict(lang):
    if lang == "ru":
        return {}
    path = root / f"content/i18n/{lang}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def render_events(lang):
    path = root / "content/events.json"
    events = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    out = []
    for n, e in enumerate(events, 1):
        base = f"assets/events/{e['id']}"
        full = json.dumps([f"{{{{_p}}}}{base}/{p['file']}.webp" for p in e["photos"]])
        if e.get("iso"):                       # дату пишем из iso — месяц на языке страницы
            y, m = e["iso"][:4], int(e["iso"][5:7])
            date = f"{MONTHS[lang].split()[m - 1]} {y}"
        else:
            date = e.get("date", "")
        meta = "".join(f"<span>{v}</span>" for v in
                       (tr_mark(e["city"]), html.escape(date), tr_mark(e.get("role") or ""), tr_mark(e.get("scale") or "")) if v)
        logo = f'<img class="event-logo" src="@@{e["logo"]}" alt="">' if e.get("logo") else ""
        text = f'<p class="event-text">{tr_mark(e["text"])}</p>' if e.get("text") else ""
        extra = len(e["photos"]) - 5
        tiles = []
        for i, p in enumerate(e["photos"]):
            cls = "ph ph-cover" if i == 0 else "ph"
            more = f'<span class="ph-more">+{extra}<small>{{{{фото}}}}</small></span>' if i == 4 and extra > 0 else ""
            tiles.append(f'<button class="{cls}" type="button" data-i="{i}" aria-label="{{{{Открыть фото}}}} {i + 1}">'
                         f'<img src="{{{{_p}}}}{base}/{p["file"]}-s.webp" alt="" loading="lazy">{more}</button>')
        out.append(f'''    <article class="event" data-reveal>
      <header class="event-head">
        <span class="event-num">{n:02d}</span>
        <div>
          <h3>{tr_mark(e["title"])}</h3>
          <p class="event-meta">{meta}</p>
          {text}
        </div>
        {logo}
      </header>
      <div class="album" data-photos='{full}'>
        {"".join(tiles)}
      </div>
    </article>''')
    return "\n".join(out)


@functools.lru_cache(maxsize=None)
def data_uri(rel):
    path = root / rel
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def translate(page, lang, values, missing):
    """{{_служебное}} → значение, {{фраза}} → перевод (русский — как есть)."""
    d = load_dict(lang)

    def sub(m):
        key = m.group(1)
        if key.startswith("_"):
            return values[key]
        if lang != "ru" and key not in d:
            missing.setdefault(lang, []).append(key)
        text = key if lang == "ru" else d.get(key, key)
        return text.replace(" —", "\u00a0—")      # тире не уезжает в начало новой строки
    return re.sub(r"\{\{(.*?)\}\}", sub, page, flags=re.S)


def build_page(src, lang, missing):
    code, label, oglocale, cv = next(l for l in LANGS if l[0] == lang)
    prefix = "" if lang == "ru" else "../"
    path = "" if lang == "ru" else f"{lang}/"
    current = ' aria-current="page"'
    switch = "".join(
        f'<a href="{prefix + ("" if c == "ru" else c + "/") or "./"}" hreflang="{c}" lang="{c}"{current if c == lang else ""}>{lab}</a>'
        for c, lab, _, _ in LANGS)
    hreflang = "\n".join(f'<link rel="alternate" hreflang="{c}" href="{SITE}{"" if c == "ru" else c + "/"}">' for c, *_ in LANGS)
    hreflang += f'\n<link rel="alternate" hreflang="x-default" href="{SITE}">'
    page = src.replace("<!--EVENTS-->", render_events(lang)).replace("<!--LANGS-->", switch).replace("<!--HREFLANG-->", hreflang)
    og = "og.jpg" if lang == "ru" else f"og-{lang}.jpg"
    page = translate(page, lang, {"_lang": code, "_p": prefix, "_cv": cv, "_path": path, "_oglocale": oglocale, "_og": og}, missing)
    return re.sub(r"@@(assets/[\w./-]+)", lambda m: data_uri(m.group(1)), page)


def main():
    src = (root / "src/index.html").read_text(encoding="utf-8")
    # блоки-черновики (<!--draft: …--> … <!--/draft-->) на сайт не попадают — так раздел прячется, но остаётся в исходнике
    src = re.sub(r"<!--draft:.*?<!--/draft-->\n?", "", src, flags=re.S)
    shutil.rmtree(dist, ignore_errors=True)
    (dist / "assets").mkdir(parents=True)
    missing = {}
    for code, *_ in LANGS:
        out = dist / ("index.html" if code == "ru" else f"{code}/index.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        page = build_page(src, code, missing)
        out.write_text(page, encoding="utf-8")
        print(out.relative_to(root), len(page) // 1024, "KB")
    shutil.copytree(root / "assets/events", dist / "assets/events")
    for og in root.glob("assets/og*.jpg"):    # превью для соцсетей; собирает tools/build_og.mjs
        shutil.copy(og, dist / og.name)
    for *_, cv in LANGS:                     # PDF-резюме собирает tools/build_cv.mjs
        if (root / "assets" / cv).exists():
            shutil.copy(root / "assets" / cv, dist / cv)
        else:
            print("нет файла резюме:", cv)
    for lang, keys in missing.items():
        uniq = list(dict.fromkeys(keys))
        print(f"[{lang}] нет перевода для {len(uniq)} строк — оставлен русский текст:")
        for k in uniq[:15]:
            print("   ", k[:90])
    if missing and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
