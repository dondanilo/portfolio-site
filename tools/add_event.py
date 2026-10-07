"""Добавляет (или пересобирает) мероприятие в блок Event-маркетинг.

Пример:
  venv/bin/python tools/add_event.py --id tokio-launch \
      --title "Официальный запуск бренда Tokio Inkarami" --date "20 мая 2025" --city "Алматы" \
      --iso 2025-05-20 --logo assets/logos/tokio.png \
      --text "Короткое описание" photo1.jpg photo2.jpg ...

Первое фото — обложка (крупная плитка). Для каждого фото делаются две версии:
assets/events/<id>/NN-s.webp (плитка, ~900px) и NN.webp (для просмотра, ~2000px).
Описание мероприятия пишется в content/events.json, страницу собирает tools/build.py.
Нужен Pillow (лежит в venv)."""
import argparse, json, pathlib
from PIL import Image, ImageOps

root = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
for k in ("id", "title", "date", "city"):
    ap.add_argument(f"--{k}", required=True)
ap.add_argument("--role", default="")
ap.add_argument("--scale", default="")
ap.add_argument("--text", default="")
ap.add_argument("--logo", default="")
ap.add_argument("--iso", default="", help="дата ГГГГ-ММ-ДД — по ней мероприятия сортируются, новые сверху")
ap.add_argument("photos", nargs="+")
a = ap.parse_args()

out = root / "assets/events" / a.id
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("*.webp"):
    old.unlink()
photos = []
for i, src in enumerate(a.photos, 1):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")   # учитываем поворот с камеры
    big = im.copy(); big.thumbnail((2000, 2000), Image.LANCZOS)
    big.save(out / f"{i:02d}.webp", "WEBP", quality=80, method=6)
    small = im.copy(); small.thumbnail((900, 900), Image.LANCZOS)
    small.save(out / f"{i:02d}-s.webp", "WEBP", quality=74, method=6)
    photos.append({"file": f"{i:02d}", "w": big.width, "h": big.height})

db_path = root / "content/events.json"
db = json.loads(db_path.read_text(encoding="utf-8")) if db_path.exists() else []
entry = {k: getattr(a, k) for k in ("id", "title", "date", "iso", "city", "role", "scale", "text", "logo")}
entry["photos"] = photos
db = sorted([e for e in db if e["id"] != a.id] + [entry], key=lambda e: e.get("iso", ""), reverse=True)
db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{a.id}: {len(photos)} фото → assets/events/{a.id}/, всего мероприятий: {len(db)}")
