// Собирает PDF-резюме из cv/index.html через Chrome (печать в PDF с живым текстом — его читают ATS).
// Запуск: node tools/build_cv.mjs  →  assets/Danil_Ulyanov_CV.pdf  (дальше tools/build.py кладёт его на сайт)
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, rmSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const qr = readFileSync(join(root, 'cv/qr.svg'), 'utf8').replace(/<\?xml[^>]*>/, '');
const html = readFileSync(join(root, 'cv/index.html'), 'utf8').replace('<!--QR-->', qr);
const tmpHtml = join(root, 'cv/_render.html');           // рядом с исходником, чтобы работали пути ../assets
writeFileSync(tmpHtml, html);

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
  await send('Page.navigate', { url: 'file://' + tmpHtml });
  // ждём шрифты и все картинки
  for (let i = 0; i < 50; i++) {
    const r = await send('Runtime.evaluate', { expression: `document.readyState === 'complete' && document.fonts.status === 'loaded' && [...document.images].every(i => i.complete)`, returnByValue: true });
    if (r.result?.result?.value) break;
    await sleep(200);
  }
  await sleep(500);
  const pdf = await send('Page.printToPDF', { preferCSSPageSize: true, printBackground: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
  const out = join(root, 'assets/Danil_Ulyanov_CV.pdf');
  writeFileSync(out, Buffer.from(pdf.result.data, 'base64'));
  console.log('assets/Danil_Ulyanov_CV.pdf', Math.round(Buffer.from(pdf.result.data, 'base64').length / 1024), 'KB');
} finally {
  chrome.kill('SIGKILL');
  rmSync(tmpHtml, { force: true });
  rmSync(profile, { recursive: true, force: true });
}
