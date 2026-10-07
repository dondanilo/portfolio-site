// Собирает PDF-резюме из cv/index.html через Chrome (печать в PDF с живым текстом — его читают ATS) — на четырёх языках.
// Запуск: node tools/build_cv.mjs [ru en el es]  →  assets/Danil_Ulyanov_CV.pdf, …_CV_EN.pdf, …_CV_EL.pdf, …_CV_ES.pdf
// (дальше tools/build.py кладёт их на сайт). Переводы — content/i18n/<язык>.json, как у сайта: {"русская фраза": "перевод"}.
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, rmSync, mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const qr = readFileSync(join(root, 'cv/qr.svg'), 'utf8').replace(/<\?xml[^>]*>/, '');
const template = readFileSync(join(root, 'cv/index.html'), 'utf8').replace('<!--QR-->', qr);
const tmpHtml = join(root, 'cv/_render.html');           // рядом с исходником, чтобы работали пути ../assets
const FILES = { ru: 'Danil_Ulyanov_CV.pdf', en: 'Danil_Ulyanov_CV_EN.pdf', el: 'Danil_Ulyanov_CV_EL.pdf', es: 'Danil_Ulyanov_CV_ES.pdf' };
const langs = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(FILES);

function render(lang) {
  const path = join(root, `content/i18n/${lang}.json`);
  const dict = lang === 'ru' ? {} : existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
  if (!dict) { console.log(`[${lang}] нет файла переводов — пропускаю`); return null; }
  const missing = new Set();
  const html = template.replace(/\{\{([\s\S]*?)\}\}/g, (_, key) => {
    if (key === '_lang') return lang;
    if (lang !== 'ru' && !(key in dict)) missing.add(key);
    return (lang === 'ru' ? key : dict[key] ?? key).replaceAll(' —', '\u00a0—');   // тире не уезжает в начало строки
  });
  if (missing.size) console.log(`[${lang}] нет перевода для ${missing.size} строк:`, [...missing].slice(0, 8));
  return html;
}

const profile = mkdtempSync(join(tmpdir(), 'cv-chrome-'));
const PORT = 9399;
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

try {
  for (let i = 0; i < 60 && !ws; i++) {
    try { const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(x => x.type === 'page'); if (p) ws = new WebSocket(p.webSocketDebuggerUrl); } catch {}
    if (!ws) await sleep(200);
  }
  await new Promise(r => ws.onopen = r);
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  await send('Page.enable'); await send('Runtime.enable');
  for (const lang of langs) {
    const html = render(lang);
    if (!html) continue;
    writeFileSync(tmpHtml, html);
    await send('Page.navigate', { url: 'file://' + tmpHtml + '?' + lang });
    await sleep(300);
    // ждём шрифты и все картинки
    for (let i = 0; i < 50; i++) {
      const r = await send('Runtime.evaluate', { expression: `document.readyState === 'complete' && document.fonts.status === 'loaded' && [...document.images].every(i => i.complete)`, returnByValue: true });
      if (r.result?.result?.value) break;
      await sleep(200);
    }
    await sleep(500);
    // резюме обязано влезать ровно в 2 страницы — длинный перевод не должен вытолкнуть блок на третью
    const over = await send('Runtime.evaluate', { expression: `[...document.querySelectorAll('.page')].map(p => p.scrollHeight - p.clientHeight).filter(d => d > 1)`, returnByValue: true });
    if (over.result?.result?.value?.length) console.log(`[${lang}] ⚠ страница переполнена на`, over.result.result.value, 'px');
    const pdf = await send('Page.printToPDF', { preferCSSPageSize: true, printBackground: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
    const buf = Buffer.from(pdf.result.data, 'base64');
    writeFileSync(join(root, 'assets', FILES[lang]), buf);
    const pages = (buf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;
    console.log(`assets/${FILES[lang]}`, Math.round(buf.length / 1024), 'KB,', pages, 'стр.');
  }
} finally {
  const exited = new Promise(r => chrome.once('exit', r));
  chrome.kill('SIGKILL');
  await Promise.race([exited, sleep(3000)]);          // Chrome дописывает профиль — ждём, потом чистим
  rmSync(tmpHtml, { force: true });
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }); } catch {}
}
