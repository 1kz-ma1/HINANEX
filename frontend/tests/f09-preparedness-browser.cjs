// Real Chromium CDP smoke: run explicitly with `node tests/f09-preparedness-browser.cjs`.
// Requires installed Chromium/Chrome; no npm dependency or external network.
const assert = require('node:assert/strict');
const { spawn, spawnSync } = require('node:child_process');
const { createServer } = require('node:http');
const { mkdtempSync, readFileSync, existsSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { once } = require('node:events');
const { setTimeout: sleep } = require('node:timers/promises');

const root = path.resolve(__dirname, '../prototypes/f09-preparedness');
const allow = new Map([['/', 'index.html'], ['/index.html', 'index.html'], ['/styles.css', 'styles.css'], ['/app.js', 'app.js'], ['/model.js', 'model.js']]);
const mime = { html: 'text/html', css: 'text/css', js: 'text/javascript' };

async function main() {
  const server = createServer((request, response) => {
    const filename = allow.get(new URL(request.url, 'http://127.0.0.1').pathname);
    if (!filename) { response.writeHead(404); response.end('Not found'); return; }
    response.writeHead(200, { 'Content-Type': mime[filename.split('.').at(-1)] + '; charset=utf-8', 'Cache-Control': 'no-store' });
    response.end(readFileSync(path.join(root, filename)));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  const browserData = mkdtempSync(path.join(tmpdir(), 'hinanex-f09-chrome-'));
  const candidates = [process.env.F09_BROWSER_BIN, process.env.F02_BROWSER_BIN, process.env.CHROME_BIN, process.env.CHROMIUM_BIN, '/usr/bin/google-chrome', '/usr/bin/chromium', 'google-chrome', 'chromium'].filter(Boolean);
  const binary = candidates.find(name => path.isAbsolute(name) ? existsSync(name) : spawnSync(process.platform === 'win32' ? 'where' : 'which', [name]).status === 0);
  if (!binary) throw new Error('Chromium / Chrome is required for F09 browser acceptance');
  const chrome = spawn(binary, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    '--no-first-run', '--no-default-browser-check', '--no-proxy-server', '--remote-debugging-port=0',
    `--user-data-dir=${browserData}`, 'about:blank',
  ], { stdio: 'ignore' });
  let ws;
  try {
    let port;
    for (let i = 0; i < 100; ++i) {
      const portFile = path.join(browserData, 'DevToolsActivePort');
      if (existsSync(portFile)) { port = Number(readFileSync(portFile, 'utf8').split('\n')[0]); break; }
      if (chrome.exitCode !== null) throw new Error(`Chromium exited: ${chrome.exitCode}`);
      await sleep(80);
    }
    if (!port) throw new Error('Chromium debug port was unavailable');
    const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    const target = tabs.find(tab => tab.type === 'page');
    assert.ok(target, 'headless Chrome page target');
    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });
    let nextId = 0;
    const waiting = new Map();
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (!message.id || !waiting.has(message.id)) return;
      const { resolve, reject } = waiting.get(message.id);
      waiting.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    });
    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = ++nextId;
        waiting.set(id, { resolve, reject });
        ws.send(JSON.stringify({ id, method, params }));
      });
    }
    async function evaluate(expression) {
      const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    }
    async function eventually(expression, predicate = Boolean) {
      for (let i = 0; i < 75; ++i) {
        const result = await evaluate(expression);
        if (predicate(result)) return result;
        await sleep(40);
      }
      throw new Error(`Condition not reached: ${expression}`);
    }
    async function key(key, code, vk) {
      await send('Input.dispatchKeyEvent', { type: key === 'Enter' ? 'keyDown' : 'rawKeyDown', key, code, windowsVirtualKeyCode: vk, ...(key === 'Enter' ? { text: '\r' } : {}) });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode: vk });
    }
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
    let injectedFallback = false;
    async function injectLocalSources() {
      const rawHTML = readFileSync(path.join(root, 'index.html'), 'utf8');
      const css = readFileSync(path.join(root, 'styles.css'), 'utf8');
      const html = rawHTML
        .replace(/<link rel="stylesheet" href="\.\/styles\.css">/, `<style>${css}</style>`)
        .replace(/<script type="module" src="\.\/app\.js"><\/script>/, '');
      const frameId = (await send('Page.getFrameTree')).frameTree.frame.id;
      await send('Page.setDocumentContent', { frameId, html });
      const model = readFileSync(path.join(root, 'model.js'), 'utf8').replace(/\bexport /g, '');
      const app = readFileSync(path.join(root, 'app.js'), 'utf8')
        .replace(/^import .*;\s*/m, '').replace(/\bexport /g, '');
      await evaluate(`(() => { ${model} \n ${app} })()`);
    }
    const navigation = await send('Page.navigate', { url: `http://127.0.0.1:${address.port}/` });
    if (navigation.errorText === 'net::ERR_BLOCKED_BY_ADMINISTRATOR') {
      if (process.env.F09_REQUIRE_HTTP === '1' || process.env.GITHUB_ACTIONS === 'true') throw new Error('Real HTTP browser test BLOCKED by policy; cannot claim HTTP acceptance');
      // Managed Chromium forbids HTTP/file; inject the exact local sources.
      injectedFallback = true;
      await injectLocalSources();
      console.log('BLOCKED HTTP navigation by administrator; continuing real-browser DOM/keyboard tests with exact local sources');
    } else if (navigation.errorText) {
      throw new Error(`Navigation failed: ${navigation.errorText}`);
    }
    await eventually('document.querySelectorAll("#checklist input").length', n => n === 10);
    assert.equal(await evaluate('document.querySelector("#checked-count").textContent'), '0');
    assert.equal(await evaluate('document.querySelector("#progress-percent").textContent'), '0%');
    console.log('PASS initial 0/10, no storage');

    // Native Tab navigation and Space toggling, without synthetic DOM click.
    await evaluate('document.querySelector("[data-item-id=water]").focus()');
    await key('Tab', 'Tab', 9);
    assert.equal(await evaluate('document.activeElement.dataset.itemId'), 'food');
    await evaluate('document.querySelector("[data-item-id=water]").focus()');
    await key(' ', 'Space', 32);
    await eventually('document.querySelector("#checked-count").textContent', x => x === '1');
    assert.equal(await evaluate('document.activeElement.dataset.itemId'), 'water');
    assert.equal(await evaluate('document.querySelector("#progress-percent").textContent'), '10%');
    assert.equal(await evaluate('document.querySelector("[data-item-id=water]").checked'), true);
    await key(' ', 'Space', 32);
    await eventually('document.querySelector("#checked-count").textContent', x => x === '0');
    console.log('PASS Space toggle/untoggle and focus retention');

    await evaluate('document.querySelector("[data-item-id=water]").click()');
    assert.equal(await evaluate('document.querySelector("#checked-count").textContent'), '1');
    await evaluate('document.querySelector("#filter-button").click()');
    assert.equal(await evaluate('document.querySelector("[data-item-id=water]").closest(".item").hidden'), true);
    await evaluate('document.querySelector("#filter-button").click()');
    await evaluate('document.querySelector("#reset-button").focus()');
    await key('Enter', 'Enter', 13);
    await eventually('document.querySelector("#checked-count").textContent', x => x === '0');
    assert.equal(await evaluate('document.querySelector("[data-item-id=water]").checked'), false);
    console.log('PASS filter and keyboard Enter reset');

    for (const width of [320, 390, 1440]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
      await sleep(80);
      const overflow = await evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth');
      assert.ok(overflow <= 1, `Horizontal overflow at ${width}px: ${overflow}`);
      assert.equal(await evaluate('document.querySelector("[data-item-id=water]").getBoundingClientRect().width >= 24'), true);
      console.log(`PASS responsive ${width}px (no horizontal overflow)`);
    }
    await evaluate('document.querySelector("[data-item-id=food]").click()');
    assert.equal(await evaluate('document.querySelector("#checked-count").textContent'), '1');
    if (injectedFallback) {
      await injectLocalSources();
      console.log('BLOCKED HTTP reload; testing browser DOM re-initialization only');
    } else {
      await send('Page.reload', { ignoreCache: true });
    }
    await eventually('document.querySelectorAll("#checklist input").length', x => x === 10);
    await eventually('document.querySelector("#checked-count").textContent', x => x === '0');
    assert.equal(await evaluate('document.querySelectorAll("#checklist input:checked").length'), 0);
    if (!injectedFallback) {
      assert.equal(await evaluate('Object.keys(localStorage).length + Object.keys(sessionStorage).length'), 0);
    } else {
      const source = readFileSync(path.join(root, 'app.js'), 'utf8') + readFileSync(path.join(root, 'model.js'), 'utf8');
      assert.doesNotMatch(source, /localStorage|sessionStorage|indexedDB|document\.cookie|fetch\s*\(|XMLHttpRequest/);
      console.log('BLOCKED storage browser API on policy-restricted origin; static no-storage source check PASS');
    }
    console.log(injectedFallback ? 'PASS new DOM session starts 0/10 (HTTP reload BLOCKED)' : 'PASS HTTP reload resets all to zero; storage remains empty');
    const screenshot = process.env.F09_SCREENSHOT;
    if (screenshot) {
      const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      writeFileSync(screenshot, Buffer.from(shot.data, 'base64'));
    }
  } finally {
    if (ws) ws.close();
    chrome.kill('SIGTERM');
    server.close();
    await sleep(450);
    try { rmSync(browserData, { recursive: true, force: true, maxRetries: 8, retryDelay: 100 }); } catch (error) { console.error('Chrome temp cleanup:', error.message); }
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
