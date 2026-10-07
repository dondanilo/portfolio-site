"""Собирает сайт в dist/ из src/index.html.

- Картинки вида @@assets/... вшиваются как data URI (мелкие: логотипы, портрет, сертификаты).
- Блок мероприятий рендерится из content/events.json на место <!--EVENTS-->.
  Фото мероприятий НЕ вшиваются — копируются в dist/assets/events/ и грузятся файлами.
- Нужна только стандартная библиотека Python — так сборка работает и локально, и в GitHub Actions."""
import base64, html, json, mimetypes, pathlib, re, shutil

root = pathlib.Path(__file__).resolve().parent.parent
dist = root / "dist"
src = (root / "src/index.html").read_text(encoding="utf-8")
mimetypes.add_type("image/webp", ".webp")


def render_events():
    path = root / "content/events.json"
    events = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    out = []
    for n, e in enumerate(events, 1):
        base = f"assets/events/{e['id']}"
        full = json.dumps([f"{base}/{p['file']}.webp" for p in e["photos"]])
        meta = "".join(f"<span>{html.escape(v)}</span>" for v in (e["city"], e["date"], e.get("role"), e.get("scale")) if v)
        logo = f'<img class="event-logo" src="@@{e["logo"]}" alt="">' if e.get("logo") else ""
        text = f'<p class="event-text">{html.escape(e["text"])}</p>' if e.get("text") else ""
        extra = len(e["photos"]) - 5
        tiles = []
        for i, p in enumerate(e["photos"]):
            cls = "ph ph-cover" if i == 0 else "ph"
            more = f'<span class="ph-more">+{extra}<small>фото</small></span>' if i == 4 and extra > 0 else ""
            tiles.append(f'<button class="{cls}" type="button" data-i="{i}" aria-label="Открыть фото {i + 1}">'
                         f'<img src="{base}/{p["file"]}-s.webp" alt="" loading="lazy">{more}</button>')
        out.append(f'''    <article class="event" data-reveal>
      <header class="event-head">
        <span class="event-num">{n:02d}</span>
        <div>
          <h3>{html.escape(e["title"])}</h3>
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


def inline(m):
    path = root / m.group(1)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


# блоки-черновики (<!--draft: …--> … <!--/draft-->) на сайт не попадают — так раздел прячется, но остаётся в исходнике
src = re.sub(r"<!--draft:.*?<!--/draft-->\n?", "", src, flags=re.S)
page = re.sub(r"@@(assets/[\w./-]+)", inline, src.replace("<!--EVENTS-->", render_events()))
shutil.rmtree(dist, ignore_errors=True)
(dist / "assets").mkdir(parents=True)
(dist / "index.html").write_text(page, encoding="utf-8")
shutil.copytree(root / "assets/events", dist / "assets/events")
shutil.copy(root / "assets/og.jpg", dist / "og.jpg")
shutil.copy(root / "assets/Danil_Ulyanov_CV.pdf", dist / "Danil_Ulyanov_CV.pdf")   # PDF-резюме собирает tools/build_cv.mjs
print("dist/index.html", len(page) // 1024, "KB")
