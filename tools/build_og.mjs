// Снимает превью для соцсетей (og:image, 1200×630) с первого экрана собранного сайта — на каждом языке.
// Запуск после python3 tools/build.py:  node tools/build_og.mjs  →  assets/og.jpg, og-en.jpg, og-el.jpg, og-es.jpg
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync, writeFileSync, rmSync, mkdtempSync, existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
const LANGS = { ru: 'og.jpg', en: 'og-en.jpg', el: 'og-el.jpg', es: 'og-es.jpg' };
const TYPES = { '.html': 'text/html; charset=utf-8', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.pdf': 'application/pdf' };

// маленький статический сервер для dist/
const server = createServer((req, res) => {
  let p = join(dist, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[extname(p)] || 'application/octet-stream' });
  res.end(readFileSync(p));
}).listen(0);
const site = `http://127.0.0.1:${server.address().port}/`;

const profile = mkdtempSync(join(tmpdir(), 'og-chrome-'));
const PORT = 9398;
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async e => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;

try {
  for (let i = 0; i < 60 && !ws; i++) {
    try { const p = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(x => x.type === 'page'); if (p) ws = new WebSocket(p.webSocketDebuggerUrl); } catch {}
    if (!ws) await sleep(200);
  }
  await new Promise(r => ws.onopen = r);
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1200, height: 630, deviceScaleFactor: 1, mobile: false });
  // превью всегда в фирменной тёмной теме; меню и подсказку «скролл» прячем
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { localStorage.setItem("theme", "dark"); } catch (e) {}
    addEventListener("DOMContentLoaded", () => { const s = document.createElement("style"); s.textContent = "nav, .scroll-cue { display: none !important; }"; document.head.appendChild(s); });` });
  for (const [lang, file] of Object.entries(LANGS)) {
    await send('Page.navigate', { url: site + (lang === 'ru' ? '' : lang + '/') });
    await sleep(500);
    await ev(`document.fonts.ready.then(() => 1)`);
    await sleep(2200);                                   // ртуть «успокаивается» после стартовых капель
    // первая из меняющихся фраз — без анимации смены
    await ev(`(() => { let t = setTimeout(() => {}); while (t > 0) clearTimeout(t--);    // гасим смену фраз
      [...document.getElementById("slot").children].forEach((el, i) => { el.style.transition = "none"; el.className = i ? "wait" : "in"; });
      return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(1)))); })()`);
    await sleep(150);
    const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 86 });
    writeFileSync(join(root, 'assets', file), Buffer.from(shot.result.data, 'base64'));
    console.log('assets/' + file);
  }
} finally {
  server.close();
  const exited = new Promise(r => chrome.once('exit', r));
  chrome.kill('SIGKILL');
  await Promise.race([exited, sleep(3000)]);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }); } catch {}
}
