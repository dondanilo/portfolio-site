"""Размечает переводимые строки в HTML-шаблоне: кириллический текст и атрибуты (alt/title/aria-label/content)
оборачиваются в {{…}} — ключом перевода служит сама русская фраза. Запускать один раз при добавлении новых текстов:
    python3 tools/i18n_mark.py src/index.html
Уже размеченное, <style>, <script>, комментарии и черновики не трогает."""
import re, sys, pathlib

CYR = "[А-Яа-яЁё]"
SKIP = r"<style>.*?</style>|<script>.*?</script>|<!--draft:.*?<!--/draft-->|<!--.*?-->|\{\{.*?\}\}"


def mark(s):
    protect = []

    def keep(m):
        protect.append(m.group(0))
        return f"\x00{len(protect) - 1}\x00"

    s = re.sub(SKIP, keep, s, flags=re.S)

    def text(m):
        t = m.group(1)
        if not re.search(CYR, t):
            return m.group(0)
        core = re.sub(r"\s*\n\s*", " ", t.strip())
        return ">" + t[:len(t) - len(t.lstrip())] + "{{" + core + "}}" + t[len(t.rstrip()):] + "<"

    s = re.sub(r">([^<>\x00]+)<", text, s)
    s = re.sub(r'\b(alt|title|aria-label|content)="([^"{}\x00]*)"',
               lambda m: f'{m.group(1)}="{{{{{m.group(2)}}}}}"' if re.search(CYR, m.group(2)) else m.group(0), s)
    for _ in range(3):
        s = re.sub("\x00(\\d+)\x00", lambda m: protect[int(m.group(1))], s)
    return s


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = pathlib.Path(f)
        p.write_text(mark(p.read_text(encoding="utf-8")), encoding="utf-8")
        left = re.findall(r".{0,30}" + CYR + r".{0,30}", re.sub(SKIP, "", p.read_text(encoding="utf-8"), flags=re.S))
        print(f, "— без разметки осталось:", left or "ничего")
