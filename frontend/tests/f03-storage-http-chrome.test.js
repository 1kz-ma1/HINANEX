/**
 * HINANEX F03/P-02 #356 — REAL HTTP / Google Chrome / Chrome DevTools Protocol.
 * Zero npm dependencies: runs with the GitHub ubuntu-latest bundled Chrome.
 * No fake localStorage, no DOM insertion, no external requests.
 *
 * Locally:
 *   cd frontend && node --test tests/f03-storage-http-chrome.test.js
 * Chrome may reject localhost by administrator policy; report as BLOCKED, never PASS.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, extname, basename, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'prototypes', 'f03-storage-contract-qa');
const KEY = 'hinanex.preparedness.demo.v1';
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' };
const failures = [];

class CDP {
  constructor(url) {
    this.seq = 0; this.pending = new Map(); this.events = new Map(); this.closed = false;
    this.ws = new WebSocket(url);
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', e => {
      let message;
      try { message = JSON.parse(e.data); } catch { return; }
      if (message.id) {
        const waiter = this.pending.get(message.id);
        if (waiter) {
          this.pending.delete(message.id);
          if (message.error) waiter.reject(new Error(message.error.message));
          else waiter.resolve(message.result ?? {});
        }
      } else {
        for (const handler of this.events.get(message.method) ?? []) handler(message.params ?? {});
      }
    });
    this.ws.addEventListener('close', () => {
      this.closed = true;
      for (const item of this.pending.values()) item.reject(new Error('CDP websocket closed'));
      this.pending.clear();
    });
  }
  on(method, handler) {
    const list = this.events.get(method) ?? [];
    list.push(handler); this.events.set(method, list);
  }
  async send(method, params = {}, sessionId = undefined) {
    await this.ready;
    if (this.closed) throw new Error('CDP websocket closed');
    const id = ++this.seq;
    const promise = new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
    this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    return Promise.race([promise, delay(15000).then(() => { throw new Error('CDP timeout: ' + method); })]);
  }
  close() { this.ws.close(); }
}

async function chromiumPath() {
  for (const name of [process.env.F03_CHROME_BIN, 'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'].filter(Boolean)) {
    if (isAbsolute(name) || name.startsWith('.')) return name;
    const found = spawnSync('which', [name], { encoding: 'utf8' });
    if (found.status === 0) return found.stdout.trim();
  }
  throw new Error('NOT_RUN: Chrome binary unavailable; no browser PASS claimed');
}
async function launchChrome(dir) {
  const bin = await chromiumPath();
  // Never connect to the previous browser's endpoint during profile reuse.
  await rm(join(dir, 'DevToolsActivePort'), { force: true, maxRetries: 8, retryDelay: 100 });
  const child = spawn(bin, [
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
    '--no-first-run', '--no-default-browser-check', '--disable-extensions',
    '--remote-debugging-port=0', '--remote-allow-origins=*', `--user-data-dir=${dir}`,
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  child.stderr.setEncoding('utf8');
  child.stderr.on('data', d => { stderr += d; });
  for (let i = 0; i < 100; i++) {
    if (child.exitCode !== null) throw new Error('Chrome failed: ' + stderr.slice(-1500));
    try {
      const [port, path] = (await readFile(join(dir, 'DevToolsActivePort'), 'utf8')).trim().split('\n');
      const cdp = new CDP(`ws://127.0.0.1:${port}${path}`);
      await cdp.ready;
      return { child, cdp };
    } catch { await delay(100); }
  }
  child.kill('SIGTERM');
  throw new Error('Chrome startup timeout: ' + stderr.slice(-1500));
}
async function stopChrome(chrome) {
  if (chrome.child.exitCode !== null || chrome.child.signalCode !== null) {
    chrome.cdp.close();
    return;
  }
  const stopped = new Promise(resolve => chrome.child.once('exit', resolve));
  // Graceful shutdown flushes real localStorage and releases the profile on Windows.
  try { await chrome.cdp.send('Browser.close'); } catch { /* browser closed the socket */ }
  const exited = await Promise.race([stopped.then(() => true), delay(5000).then(() => false)]);
  if (!exited) { chrome.child.kill('SIGTERM'); await stopped; }
  chrome.cdp.close();
}
async function openTab(cdp, url) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Runtime.enable', {}, sessionId);
  await cdp.send('Network.enable', {}, sessionId);
  const requests = [];
  const jsErrors = [];
  cdp.on('Network.requestWillBeSent', ({ request }) => {
    if (request?.url) requests.push(request.url);
  });
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }) => {
    jsErrors.push(exceptionDetails?.text ?? 'unknown JS exception');
  });
  const tab = {
    requests, jsErrors, sessionId,
    async eval(expression) {
      const response = await cdp.send('Runtime.evaluate', {
        expression, returnByValue: true, awaitPromise: true, userGesture: true,
      }, sessionId);
      if (response.exceptionDetails) throw new Error('Browser JS error: ' + (response.exceptionDetails.text ?? JSON.stringify(response.exceptionDetails)));
      return response.result?.value;
    },
    async navigate(next = url) {
      await cdp.send('Page.navigate', { url: next }, sessionId);
      // CDP navigate is asynchronous; do not accidentally observe the old document.
      await delay(250);
      for (let i = 0; i < 100; i++) {
        try {
          const ok = await tab.eval(`document.readyState === 'complete' && !!document.querySelector('#save-btn')`);
          if (ok) return;
        } catch { /* document not ready yet */ }
        await delay(60);
      }
      throw new Error('HTTP document/navigation did not load in Chrome');
    },
    async click(selector) {
      await tab.eval(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) throw new Error('missing ${selector}'); e.click(); return true; })()`);
    },
    async text(selector) {
      return tab.eval(`document.querySelector(${JSON.stringify(selector)})?.textContent ?? null`);
    },
    async select(code) {
      await tab.eval(`(() => { const e = document.querySelector('input[value=${JSON.stringify(code)}]'); if(!e) throw Error('missing region'); e.checked = true; e.dispatchEvent(new Event('change',{bubbles:true})); return true; })()`);
    },
  };
  await tab.navigate();
  return tab;
}

async function runCase(id, title, check) {
  try { await check(); console.log(`F03_REAL_HTTP: ${id} PASS ${title}`); }
  catch (e) { failures.push(`${id}: ${title}: ${e.message}`); console.log(`F03_REAL_HTTP: ${id} FAIL ${title}: ${e.message}`); }
}

test('F03 Issue #356 genuine HTTP Chrome persistence, integrity, consent and privacy', { timeout: 120000 }, async () => {
  let server;
  let chrome;
  let profile;
  try {
    server = createServer(async (req, res) => {
      const pathname = new URL(req.url, 'http://127.0.0.1').pathname;
      const name = pathname === '/' ? 'index.html' : basename(pathname);
      if (!['index.html', 'styles.css', 'app.js'].includes(name) || pathname !== '/' && pathname !== '/' + name) {
        res.writeHead(404); res.end(); return;
      }
      try {
        const body = await readFile(join(DIR, name));
        res.writeHead(200, { 'Content-Type': MIME[extname(name)], 'Cache-Control': 'no-store' });
        res.end(body);
      } catch { res.writeHead(500); res.end(); }
    });
    await new Promise((ok, fail) => server.once('error', fail).listen(0, '127.0.0.1', ok));
    const url = `http://127.0.0.1:${server.address().port}/index.html`;
    profile = await mkdtemp(join(tmpdir(), 'hinanex-f03-chrome-'));
    chrome = await launchChrome(profile);
    let tab = await openTab(chrome.cdp, url);

    await runCase('C01', 'no localStorage touch before explicit action', async () => {
      // Pre-seed through isolated CDP only, then navigate again and verify no startup read.
      const seeded = JSON.stringify({ schema_version: 1, selected_region: '13123' });
      await tab.eval(`localStorage.setItem(${JSON.stringify(KEY)},${JSON.stringify(seeded)})`);
      await chrome.cdp.send('Page.addScriptToEvaluateOnNewDocument', { source: `
        (()=>{ const get=Storage.prototype.getItem, set=Storage.prototype.setItem, remove=Storage.prototype.removeItem;
        window.__f03Traffic={read:0,write:0,remove:0};
        Storage.prototype.getItem=function(...a){window.__f03Traffic.read++;return get.apply(this,a)};
        Storage.prototype.setItem=function(...a){window.__f03Traffic.write++;return set.apply(this,a)};
        Storage.prototype.removeItem=function(...a){window.__f03Traffic.remove++;return remove.apply(this,a)};
        })();` }, tab.sessionId);
      await tab.navigate();
      assert.deepEqual(await tab.eval('window.__f03Traffic'), { read: 0, write: 0, remove: 0 });
      assert.match(await tab.text('#saved-region-display'), /未設定/);
    });
    await runCase('C02', 'explicit read and saved plaintext is visible to same-origin JS', async () => {
      await tab.click('#load-btn');
      assert.match(await tab.text('#saved-region-display'), /江戸川区/);
      const raw = await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`);
      assert.equal(JSON.parse(raw).selected_region, '13123');
      assert(!raw.includes('gps') && !raw.includes('address'));
    });
    await runCase('C03', 'explicit save then reload and explicit recovery', async () => {
      await tab.select('15100'); await tab.click('#save-btn');
      assert.match(await tab.text('#save-feedback'), /保存しました/);
      assert.equal(JSON.parse(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`)).selected_region, '15100');
      await tab.navigate();
      assert.match(await tab.text('#saved-region-display'), /未設定/);
      await tab.click('#load-btn');
      assert.match(await tab.text('#saved-region-display'), /新潟市/);
    });
    await runCase('C04', 'explicit update and persisted region change', async () => {
      await tab.select('23100'); await tab.click('#save-btn');
      assert.match(await tab.text('#saved-region-display'), /名古屋市/);
      assert.equal(JSON.parse(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`)).selected_region, '23100');
    });
    await runCase('C05', 'reject quota exception without overwriting old region', async () => {
      await tab.eval(`window.__f03SavedSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError')}`);
      await tab.select('13123'); await tab.click('#save-btn');
      assert.match(await tab.text('#save-feedback'), /更新に失敗/);
      assert.match(await tab.text('#saved-region-display'), /名古屋市/);
      await tab.eval('Storage.prototype.setItem=window.__f03SavedSet');
      assert.equal(JSON.parse(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`)).selected_region, '23100');
    });
    await runCase('C06', 'setItem silently not persisted cannot show saved success', async () => {
      await tab.eval(`window.__f03SavedSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){}`);
      await tab.select('13123'); await tab.click('#save-btn');
      assert.match(await tab.text('#save-feedback'), /更新に失敗/);
      await tab.eval('Storage.prototype.setItem=window.__f03SavedSet');
      assert.equal(JSON.parse(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`)).selected_region, '23100');
    });
    await runCase('C07', 'deletion unconfirmed must not show success', async () => {
      await tab.eval(`window.__f03SavedRemove=Storage.prototype.removeItem;Storage.prototype.removeItem=function(){}`);
      await tab.click('#clear-btn');
      assert.match(await tab.text('#save-feedback'), /削除を確認できません/);
      assert.match(await tab.text('#saved-region-display'), /名古屋市/);
      await tab.eval('Storage.prototype.removeItem=window.__f03SavedRemove');
    });
    await runCase('C08', 'delete and reload no saved region', async () => {
      await tab.click('#clear-btn');
      assert.match(await tab.text('#save-feedback'), /削除しました/);
      assert.equal(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`), null);
      await tab.navigate(); await tab.click('#load-btn');
      assert.match(await tab.text('#saved-region-display'), /未設定/);
    });
    await runCase('C09', 'corrupt JSON and invalid schema do not restore region', async () => {
      for (const raw of ['{bad', JSON.stringify({ schema_version: 999, selected_region: '13123' }), JSON.stringify({ schema_version: 1, selected_region: '13123', gps: 35 })]) {
        await tab.eval(`localStorage.setItem(${JSON.stringify(KEY)},${JSON.stringify(raw)})`);
        await tab.navigate(); await tab.click('#load-btn');
        assert.match(await tab.text('#save-feedback'), /読み込めません/);
        assert.match(await tab.text('#saved-region-display'), /未設定/);
      }
    });
    await runCase('C10', 'no background network and saved code never placed in URLs', async () => {
      await tab.navigate();
      assert(tab.requests.every(u => u.startsWith(`http://127.0.0.1:${server.address().port}/`) || u === 'about:blank'), JSON.stringify(tab.requests));
      const href = await tab.eval('location.href');
      assert(!href.includes('13123') && !href.includes('23100'));
      const links = await tab.eval('[...document.querySelectorAll("a[href]")].map(e=>e.getAttribute("href"))');
      assert(!links.some(x => /13123|23100|15100/.test(x)));
    });
    await runCase('C11', 'restart browser with same profile restores only after explicit read', async () => {
      await tab.eval(`localStorage.setItem(${JSON.stringify(KEY)}, JSON.stringify({schema_version:1,selected_region:'15100'}))`);
      await stopChrome(chrome);
      chrome = await launchChrome(profile);
      tab = await openTab(chrome.cdp, url);
      assert.match(await tab.text('#saved-region-display'), /未設定/);
      await tab.click('#load-btn');
      assert.match(await tab.text('#saved-region-display'), /新潟市/);
    });
    await runCase('C12', 'UI disclosure and runtime exceptions', async () => {
      const p = await tab.text('.privacy-note');
      assert.match(p, /共用端末/); assert.match(p, /同一オリジン/);
      assert.match(p, /バックアップ/); assert.match(p, /自動期限/);
      assert.deepEqual(tab.jsErrors, []);
    });
    await runCase('C13', 'real Chrome 320/375/390/430px mobile action hit targets and overflow', async () => {
      for (const width of [320, 375, 390, 430]) {
        await chrome.cdp.send('Emulation.setDeviceMetricsOverride', {
          width, height: 844, deviceScaleFactor: 1, mobile: true,
        }, tab.sessionId);
        await delay(80);
        const sizes = await tab.eval(`(() => ({
          viewport: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          buttons: [...document.querySelectorAll('.action-area button')].map(b => {
            const r = b.getBoundingClientRect();
            return { id:b.id, width:r.width, height:r.height, scroll:b.scrollWidth, client:b.clientWidth };
          })
        }))()`);
        assert.equal(sizes.viewport, width, JSON.stringify(sizes));
        assert(sizes.scrollWidth <= sizes.viewport, JSON.stringify(sizes));
        for (const b of sizes.buttons) {
          assert(b.width >= 200 && b.height >= 44 && b.scroll <= b.client + 1, JSON.stringify({ width, b }));
        }
        console.log(`F03_REAL_HTTP MOBILE ${width}px ${JSON.stringify(sizes.buttons)}`);
        if (process.env.F03_EVIDENCE_DIR) {
          await mkdir(process.env.F03_EVIDENCE_DIR, { recursive: true });
          const { cssContentSize } = await chrome.cdp.send('Page.getLayoutMetrics', {}, tab.sessionId);
          const { data } = await chrome.cdp.send('Page.captureScreenshot', {
            format: 'png', captureBeyondViewport: true,
            clip: { x: 0, y: 0, width, height: Math.ceil(cssContentSize.height), scale: 1 },
          }, tab.sessionId);
          const bytes = Buffer.from(data, 'base64');
          await writeFile(join(process.env.F03_EVIDENCE_DIR, `real-http-chrome-${width}.png`), bytes);
          console.log(`F03_REAL_HTTP_SCREENSHOT_${width}_PNG_SHA256 ${createHash('sha256').update(bytes).digest('hex')}`);
        }
        if (width === 390) {
          const { data } = await chrome.cdp.send('Page.captureScreenshot', {
            format: 'jpeg', quality: 25, fromSurface: true,
          }, tab.sessionId);
          const hash = createHash('sha256').update(Buffer.from(data, 'base64')).digest('hex');
          console.log(`F03_REAL_HTTP_SCREENSHOT_390_SHA256 ${hash}`);
          // Small real HTTP Chrome screenshot for review, kept in CI logs as a base64 JPEG.
          console.log(`F03_REAL_HTTP_SCREENSHOT_390_B64 ${data}`);
        }
      }
      await chrome.cdp.send('Emulation.clearDeviceMetricsOverride', {}, tab.sessionId);
    });
    await runCase('C14', 'write accepted but read-back denied must not retain a confirmed saved badge', async () => {
      await tab.select('23100');
      await tab.eval(`window.__f03SavedGet=Storage.prototype.getItem;Storage.prototype.getItem=function(){throw new DOMException('denied','SecurityError')}`);
      try {
        await tab.click('#save-btn');
        assert.doesNotMatch(await tab.text('#save-state-display'), /✓|保存済み/);
        assert.match(await tab.text('#save-feedback'), /確認できません/);
      } finally { await tab.eval('Storage.prototype.getItem=window.__f03SavedGet'); }
      assert.equal(JSON.parse(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`)).selected_region, '23100');
    });
    await runCase('C15', 'delete accepted but read-back denied must not claim old data remains saved', async () => {
      await tab.click('#load-btn');
      await tab.eval(`window.__f03SavedGet=Storage.prototype.getItem;Storage.prototype.getItem=function(){throw new DOMException('denied','SecurityError')}`);
      try {
        await tab.click('#clear-btn');
        assert.doesNotMatch(await tab.text('#save-state-display'), /✓|保存済み/);
        assert.doesNotMatch(await tab.text('#save-feedback'), /削除しました/);
      } finally { await tab.eval('Storage.prototype.getItem=window.__f03SavedGet'); }
      assert.equal(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`), null);
    });
    await runCase('C16', 'invalid saved data can be explicitly deleted without selecting or saving a region', async () => {
      for (const raw of ['{bad', JSON.stringify({ schema_version: 999, selected_region: '13123' })]) {
        await tab.eval(`localStorage.setItem(${JSON.stringify(KEY)},${JSON.stringify(raw)})`);
        await tab.navigate(); await tab.click('#load-btn');
        assert.equal(await tab.eval(`document.querySelector('#clear-btn').disabled`), false);
        await tab.click('#clear-btn');
        assert.equal(await tab.eval(`localStorage.getItem(${JSON.stringify(KEY)})`), null);
        assert.match(await tab.text('#save-feedback'), /削除しました/);
      }
    });
    console.log(`F03_REAL_HTTP SUMMARY ${16 - failures.length} PASS / ${failures.length} FAIL / 0 NOT_RUN (actual Chrome; http://127.0.0.1)`);
    assert.deepEqual(failures, [], failures.join('\n'));
  } finally {
    if (chrome) {
      await stopChrome(chrome);
    }
    if (server) await new Promise(resolve => server.close(resolve));
    if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 8, retryDelay: 350 });
  }
});
