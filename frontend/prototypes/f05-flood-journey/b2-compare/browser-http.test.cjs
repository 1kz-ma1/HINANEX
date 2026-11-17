"use strict";
// F05/B2: real HTTP + real headless Chrome, but SYNTHETIC fixtures only.
// This does not certify real facilities, official rights, disaster suitability,
// public staging, or iOS/Android/assistive-technology acceptance.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const {spawn, spawnSync} = require("node:child_process");

const prefix = "/frontend/prototypes/f05-flood-journey/b2-compare/";
const paths = new Map([
  [prefix, "index.html"],
  [prefix + "index.html", "index.html"],
  [prefix + "model.js", "model.js"],
  [prefix + "fixtures.js", "fixtures.js"]
]);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function chromeBinary() {
  for (const name of [process.env.B2_BROWSER_BIN, process.env.CHROME_BIN,
    "/usr/bin/google-chrome", "/usr/bin/chromium", "google-chrome", "chromium"].filter(Boolean)) {
    const file = path.isAbsolute(name) || name.includes("/") || name.includes("\\");
    if (file && fs.existsSync(name)) return name;
    if (!file && spawnSync(process.platform === "win32" ? "where" : "which", [name]).status === 0) return name;
  }
  return null;
}

async function localServer() {
  const requests = [];
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, "http://127.0.0.1").pathname;
    requests.push(pathname);
    if (req.method !== "GET") {res.writeHead(405);res.end();return;}
    const file = paths.get(pathname);
    if (!file) {res.writeHead(404);res.end();return;}
    res.writeHead(200, {
      "Content-Type": file.endsWith(".js") ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8",
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"
    });
    fs.createReadStream(path.join(__dirname, file)).pipe(res);
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return {server, requests, base: "http://127.0.0.1:" + server.address().port};
}

function signalTree(child, signal) {
  if (process.platform !== "win32" && Number.isInteger(child.pid)) {
    try {process.kill(-child.pid, signal);return;}
    catch (error) {if (error.code !== "ESRCH") throw error;}
  }
  if (child.exitCode === null && child.signalCode === null) child.kill(signal);
}
async function processExited(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return true;
  return Promise.race([
    new Promise(resolve => child.once("exit", () => resolve(true))),
    delay(timeoutMs).then(() => false)
  ]);
}
async function stopChrome(browser) {
  if (!browser) return;
  const {ws, child, profile} = browser;
  if (ws) {try {ws.close();} catch { /* already disconnected */ }}
  if (child.exitCode === null && child.signalCode === null) {
    signalTree(child, "SIGTERM");
    if (!await processExited(child, 4000)) {
      signalTree(child, "SIGKILL");
      if (!await processExited(child, 4000)) throw Error("Chrome process remained active");
    }
  }
  if (process.platform !== "win32") signalTree(child, "SIGTERM");
  for (let i = 0; i < 15; i++) {
    try {
      await fs.promises.rm(profile, {recursive:true, force:true, maxRetries:3, retryDelay:200});
      if (!fs.existsSync(profile)) return;
    } catch (error) {
      if (!["EBUSY","ENOTEMPTY","EPERM","EACCES"].includes(error.code) || i === 14) throw error;
    }
    await delay(300);
  }
  throw Error("Browser profile cleanup failed: " + profile);
}
async function launchChrome(bin) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "f05-b2-chrome-"));
  const child = spawn(bin, ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--no-first-run", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank"],
  {stdio:["ignore","ignore","pipe"], detached:process.platform !== "win32"});
  let stderr = "";
  child.stderr.on("data", data => {stderr = (stderr + data.toString()).slice(-1500);});
  const browser = {profile, child, ws:null, errors:[], requests:[]};
  try {
    let port = 0;
    for (let i = 0; i < 300; i++) {
      const active = path.join(profile, "DevToolsActivePort");
      if (fs.existsSync(active)) {
        port = Number(fs.readFileSync(active, "utf8").split("\n")[0]);
        break;
      }
      if (child.exitCode !== null) throw Error("Chrome exited: " + stderr);
      await delay(100);
    }
    if (!port) throw Error("Chrome CDP startup timeout: " + stderr);
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list",
      {signal:AbortSignal.timeout(10000)})).json();
    const page = targets.find(item => item.type === "page" && item.webSocketDebuggerUrl);
    if (!page) throw Error("Chrome page target unavailable");
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    browser.ws = ws;
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error("Chrome WebSocket timeout")), 12000);
      ws.addEventListener("open", () => {clearTimeout(timer);resolve();}, {once:true});
      ws.addEventListener("error", () => {clearTimeout(timer);reject(Error("Chrome WebSocket error"));}, {once:true});
    });
    const pending = new Map();
    let id = 0;
    ws.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") {
        browser.errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      }
      if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
        browser.errors.push(message.params.args.map(arg => arg.value || arg.description).join(" "));
      }
      if (message.method === "Network.requestWillBeSent") browser.requests.push(message.params.request.url);
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      message.error ? task.reject(Error(message.error.message)) : task.resolve(message.result);
    });
    ws.addEventListener("close", () => {
      for (const task of pending.values()) task.reject(Error("Chrome CDP disconnected"));
      pending.clear();
    });
    browser.command = (method, params = {}) => new Promise((resolve, reject) => {
      const next = ++id;
      const timer = setTimeout(() => {pending.delete(next);reject(Error("CDP timeout: " + method));}, 15000);
      pending.set(next, {
        resolve(value) {clearTimeout(timer);resolve(value);},
        reject(error) {clearTimeout(timer);reject(error);}
      });
      ws.send(JSON.stringify({id:next, method, params}));
    });
    browser.evaluate = async expression => {
      const result = await browser.command("Runtime.evaluate", {expression, returnByValue:true, awaitPromise:true});
      if (result.exceptionDetails) throw Error("Chrome JS: " + (result.exceptionDetails.exception?.description || result.exceptionDetails.text));
      return result.result.value;
    };
    return browser;
  } catch(error) {
    await stopChrome(browser);
    throw error;
  }
}

async function until(evaluate, expression, label) {
  for (let i = 0; i < 100; i++) {
    try {if (await evaluate(expression)) return;} catch { /* navigation in flight */ }
    await delay(100);
  }
  throw Error("Timeout waiting for " + label);
}

test("F05/B2 real HTTP Chrome: synthetic comparison, reset, errors, keyboard, privacy and widths",
  {timeout:120000}, async t => {
    const bin = chromeBinary();
    if (!bin) {
      if (process.env.CI || process.env.B2_REQUIRE_CHROME === "1") throw Error("B2 real Chrome required in CI");
      t.skip("Chrome unavailable on local machine");
      return;
    }
    const {server, requests, base} = await localServer();
    let browser;
    try {
      browser = await launchChrome(bin);
      const {command, evaluate} = browser;
      await command("Page.enable");
      await command("Runtime.enable");
      await command("Network.enable");
      const navigation = await command("Page.navigate", {url:base + prefix});
      assert.ok(!navigation.errorText, "HTTP navigation failed: " + navigation.errorText);
      await until(evaluate, "document.readyState==='complete' && !document.querySelector('#prototype').hidden && document.querySelectorAll('#recordList button').length===3", "B2 synthetic page");
      assert.ok(requests.includes(prefix), "index over HTTP not requested");
      assert.ok(requests.includes(prefix + "model.js"), "model ESM not requested");
      assert.ok(requests.includes(prefix + "fixtures.js"), "fixture ESM not requested");
      assert.equal(await evaluate("document.querySelector('#onlyLocal').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#safetyNotice').textContent.includes('訓練用の完全な合成データ')"), true);
      assert.ok(await evaluate("document.querySelector('#stats').textContent.includes('合成総数 3件')"));
      assert.ok(await evaluate("document.querySelector('#recordList').textContent.includes('UNKNOWN')"));

      // Two distinct records, unpromoted UNKNOWN, evidence trace and explicit choice.
      await evaluate("document.querySelectorAll('#recordList button')[0].click()");
      await evaluate("document.querySelectorAll('#recordList button')[1].click()");
      assert.equal(await evaluate("document.querySelectorAll('#recordList button[aria-pressed=true]').length"), 2);
      assert.equal(await evaluate("document.querySelectorAll('#recordList button')[2].disabled"), true);
      assert.equal(await evaluate("document.querySelectorAll('#compareArea article').length"), 2);
      assert.ok(await evaluate("document.querySelector('#compareArea').textContent.includes('合成区分：UNKNOWN')"));
      assert.ok(await evaluate("document.querySelector('#compareArea').textContent.includes('fixture_row=2')"));
      assert.ok(await evaluate("document.querySelector('#compareArea').textContent.includes('安全性') && document.querySelector('#compareArea').textContent.includes('未認定')"));
      await evaluate("document.querySelectorAll('#choiceArea button')[1].click()");
      assert.ok(await evaluate("document.querySelector('#choiceMessage').textContent.includes('架空施設B')"));
      assert.equal(await evaluate("document.querySelectorAll('#choiceArea button[aria-pressed=true]').length"), 1);

      // Changing filter, search, or fixture must erase prior personal selection.
      await evaluate("(()=>{const x=document.querySelector('#filter');x.value='UNKNOWN';x.dispatchEvent(new Event('change',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#recordList button').length"), 1);
      assert.equal(await evaluate("document.querySelectorAll('#compareArea article').length"), 0);
      assert.ok(await evaluate("document.querySelector('#choiceMessage').textContent.includes('なし')"));
      await evaluate("(()=>{const x=document.querySelector('#filter');x.value='ALL';x.dispatchEvent(new Event('change',{bubbles:true}))})()");
      await evaluate("(()=>{const x=document.querySelector('#query');x.value='該当なし';x.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#recordList button').length"), 0);
      assert.ok(await evaluate("document.querySelector('#emptyMessage').textContent.includes('検索一致0件')"));
      await evaluate("(()=>{const x=document.querySelector('#query');x.value='';x.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#recordList button').length"), 3);
      assert.equal(await evaluate("document.querySelectorAll('#recordList button[aria-pressed=true]').length"), 0);

      for (const [mode, expected] of [
        ["empty","0件"], ["none","未選択"], ["load-error","取得失敗"], ["invalid","整合"]
      ]) {
        await evaluate("(()=>{const x=document.querySelector('#fixture');x.value=" + JSON.stringify(mode) + ";x.dispatchEvent(new Event('change',{bubbles:true}))})()");
        assert.ok(await evaluate("document.querySelector('#state').textContent.includes(" + JSON.stringify(expected) + ")"), mode);
        assert.equal(await evaluate("document.querySelectorAll('#recordList button').length"), 0, mode);
        assert.equal(await evaluate("document.querySelectorAll('#choiceArea button').length"), 0, mode);
        assert.equal(await evaluate("document.querySelector('#query').disabled"), true, mode);
      }
      await evaluate("(()=>{const x=document.querySelector('#fixture');x.value='ready';x.dispatchEvent(new Event('change',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#recordList button[aria-pressed=true]').length"), 0);

      // Emulated viewport ≠ physical device acceptance.
      for (const [width,height] of [[320,700],[390,844],[1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride",
          {width,height,deviceScaleFactor:1,mobile:false});
        const metrics = await evaluate("({width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth,minTarget:Math.min(...[...document.querySelectorAll('button,select,input')].map(e=>e.getBoundingClientRect().height))})");
        assert.equal(metrics.width, width, "viewport " + width);
        assert.ok(metrics.overflow <= 2, "horizontal overflow at " + width + ": " + metrics.overflow);
        assert.ok(metrics.minTarget >= 44, "touch target below 44px at " + width);
      }
      await command("Emulation.clearDeviceMetricsOverride");

      // Native keyboard: Tab moves from the fixture select to filter;
      // Enter activates a focused record button (not only programmatic click).
      await evaluate("document.querySelector('#fixture').focus()");
      await command("Input.dispatchKeyEvent", {type:"keyDown",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
      await command("Input.dispatchKeyEvent", {type:"keyUp",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
      assert.equal(await evaluate("document.activeElement?.id"), "filter");
      await evaluate("document.querySelectorAll('#recordList button')[0].focus()");
      await command("Input.dispatchKeyEvent", {type:"rawKeyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
      await command("Input.dispatchKeyEvent", {type:"char",text:"\r",unmodifiedText:"\r",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
      await command("Input.dispatchKeyEvent", {type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
      await until(evaluate, "document.querySelectorAll('#recordList button[aria-pressed=true]').length===1", "native Enter selection");

      // No outbound data, storage or runtime exceptions.
      assert.equal(await evaluate("localStorage.length+sessionStorage.length"), 0);
      assert.deepEqual(browser.errors, [], "browser JS/console errors");
      assert.ok(browser.requests.every(url => url.startsWith(base + "/") || url === "about:blank" || url.startsWith("data:")),
        "unexpected network destinations: " + browser.requests.join(" | "));
      console.log("F05_B2_CHROME_HTTP: synthetic-only UI, two-record comparison, UNKNOWN, choice reset, errors, native keyboard, responsive widths, no external requests/storage PASS");
    } finally {
      try {await stopChrome(browser);}
      finally {
        await new Promise((resolve,reject) => {
          server.close(error => error ? reject(error) : resolve());
          server.closeAllConnections();
        });
      }
    }
  });
