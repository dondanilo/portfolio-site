"""Чистая вырезка портрета без светлого ореола.
Вход: исходное фото + маска от tools/vision.swift. Выход: RGBA, где краевые пиксели
перекрашены в цвет самого объекта (пиджак/волосы), а не стены за спиной.
Запуск: python clean_cutout.py photo.png mask.png out.png  (нужны numpy и Pillow)"""
import sys
import numpy as np
from PIL import Image, ImageFilter

src, mask_path, out_path = sys.argv[1:4]
I = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
A = np.asarray(Image.open(mask_path).convert("L")).astype(np.float32) / 255

def blur(x, s):
    if x.ndim == 3:
        return np.stack([blur(x[..., c], s) for c in range(3)], -1)
    im = Image.fromarray((x * 255).clip(0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(s))).astype(np.float32) / 255

# уверенная зона объекта, ужатая на 3 px: у края маска Vision иногда цепляет пиксели фона
conf_img = Image.fromarray(((A > 0.97) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(7))
conf = np.asarray(conf_img).astype(np.float32) / 255

# цвет объекта «вытягиваем» наружу из уверенной зоны (нормированная свёртка на нескольких масштабах)
F = I.copy()
filled = conf.copy()
for s in (2, 4, 8, 16):
    den = blur(conf, s)
    ext = blur(I * conf[..., None], s) / np.maximum(den, 1e-4)[..., None]
    need = (filled < 0.5) & (den > 0.02)
    F[need] = ext[need]
    filled = np.maximum(filled, (den > 0.02).astype(np.float32))
rgb = np.where(conf[..., None] > 0.5, I, F)

# маска плотнее и мягче: срезаем полупрозрачную бахрому, ужимаем на 1 px, сглаживаем
a = np.clip((A - 0.25) / (0.9 - 0.25), 0, 1)
a = a * a * (3 - 2 * a)
a_img = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))

out = Image.fromarray((rgb.clip(0, 1) * 255).astype(np.uint8))
out.putalpha(a_img)
out.save(out_path)
print("saved", out_path)
