"use strict";
// MJ-01: local HTTP Chrome harness adapted from existing B2 browser test; fixed synthetic only.
// This does not certify real facilities, official rights, disaster suitability,
// public staging, or iOS/Android/assistive-technology acceptance.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const {spawn, spawnSync} = require("node:child_process");

const prefix = "/frontend/prototypes/f05-flood-journey/mj01-shell/";
const b2Path = "/frontend/prototypes/f05-flood-journey/b2-compare/model.js";
const paths = new Map([
  [prefix, "index.html"],
  [prefix + "index.html", "index.html"],
  [prefix + "model.js", "model.js"],
  [prefix + "fixtures.js", "fixtures.js"],
  [prefix + "app.js", "app.js"],
  [b2Path, "../b2-compare/model.js"]
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

async function localServer(host="127.0.0.1") {
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
    server.listen(0, host, resolve);
  });
  return {server, requests, base: "http://" + host + ":" + server.address().port};
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
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "mj01-chrome-"));
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


test("MJ01 actual HTTP Chrome: steps, fixed evidence, max two, UNKNOWN, reset, keyboard and privacy", {timeout:120000}, async t=>{
  const bin=chromeBinary();
  if(!bin){if(process.env.CI||process.env.B2_REQUIRE_CHROME==="1")throw Error("MJ01 Chrome required");t.skip("Chrome unavailable locally");return;}
  const {server,requests,base}=await localServer();
  let browser,denied;
  try{
    browser=await launchChrome(bin);
    const {command,evaluate}=browser;
    await command("Page.enable");await command("Runtime.enable");await command("Network.enable");
    const click=id=>evaluate("document.getElementById("+JSON.stringify(id)+").click()");
    const key=async(name,code)=>{
      await command("Input.dispatchKeyEvent",{type:"rawKeyDown",key:name,code:name,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});
      if(name==="Enter")await command("Input.dispatchKeyEvent",{type:"char",text:"\r",unmodifiedText:"\r",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
      await command("Input.dispatchKeyEvent",{type:"keyUp",key:name,code:name,windowsVirtualKeyCode:code,nativeVirtualKeyCode:code});
    };
    const ready=async()=>{
      const n=await command("Page.navigate",{url:base+prefix});assert.ok(!n.errorText);
      await until(evaluate,"document.readyState==='complete' && !document.querySelector('#prototype').hidden && !!document.querySelector('#start')","MJ01 ready");
    };
    const noOverflow=async()=>assert.ok(await evaluate("document.documentElement.scrollWidth<=innerWidth"),"horizontal overflow");
    const noRows=async()=>assert.equal(await evaluate("document.querySelectorAll('[data-record]').length"),0);
    for(const width of [320,390,1440]){
      await command("Emulation.setDeviceMetricsOverride",{width,height:800,deviceScaleFactor:1,mobile:false});
      await ready();await noOverflow();await noRows();
      assert.ok(await evaluate("document.querySelector('#notice').textContent.includes('実S1出力')"));
      await evaluate("document.querySelector('#start').focus()");
      await key("Enter",13);
      assert.equal(await evaluate("document.activeElement.id"),"heading");
      await key("Tab",9);assert.equal(await evaluate("document.activeElement.id"),"condition-pet");
      await key("Enter",13);
      assert.equal(await evaluate("document.activeElement.id"),"condition-pet");
      assert.equal(await evaluate("document.querySelector('#condition-pet').getAttribute('aria-pressed')"),"true");
      await click("show");await noOverflow();
      assert.equal(await evaluate("document.querySelectorAll('[data-record]').length"),3);
      assert.ok(await evaluate("document.querySelector('#content').textContent.includes('MJ01-PET-2') && document.querySelector('#content').textContent.includes('UNKNOWN')"));
      await click("continue");
      const toggleAX = async pressed => {
        const {nodes}=await command("Accessibility.getFullAXTree");
        const toggle=nodes.find(node=>!node.ignored&&node.name?.value==="架空施設Aを比較対象にする");
        assert.ok(toggle,"stable compare control name in Chrome accessibility tree");
        assert.equal(String(toggle.properties?.find(property=>property.name==="pressed")?.value.value),String(pressed));
      };
      await toggleAX(false);
      await key("Tab",9);assert.equal(await evaluate("document.activeElement.id"),"toggle-mj01-a");
      await key("Enter",13);
      assert.equal(await evaluate("document.activeElement.id"),"toggle-mj01-a");
      await toggleAX(true);
      await click("toggle-mj01-b");await noOverflow();
      assert.equal(await evaluate("document.activeElement.id"),"toggle-mj01-b");
      assert.equal(await evaluate("document.querySelector('#toggle-mj01-c').disabled"),true);
      await click("compare");await noOverflow();
      assert.equal(await evaluate("document.querySelectorAll('[data-record]').length"),2);
      assert.ok(await evaluate("!document.querySelector('#status').textContent.includes('完了')"));
      await click("choose-mj01-b");
      assert.ok(await evaluate("document.querySelector('#status').textContent.includes('架空施設B') && document.querySelector('#status').textContent.includes('完了')"));
      assert.equal(await evaluate("document.querySelector('#choose-mj01-b').getAttribute('aria-pressed')"),"true");
      assert.ok(await evaluate("document.querySelector('[data-record=mj01-b]').textContent.includes('UNKNOWN') && document.querySelector('[data-record=mj01-b]').textContent.includes('未認定')"));
      const ax=await command("Accessibility.getFullAXTree");
      assert.ok(ax.nodes.some(x=>!x.ignored&&x.role?.value==="status"));
      assert.ok(ax.nodes.some(x=>!x.ignored&&x.role?.value==="listitem"&&x.name?.value!==undefined));
      await click("change");await noRows();
      assert.equal(await evaluate("document.querySelector('#show').disabled"),true);
      assert.ok(await evaluate("!document.querySelector('#status').textContent.includes('架空施設B')"));
      await click("condition-step");await click("show");
      assert.ok(await evaluate("document.querySelector('[data-record=mj01-a]').textContent.includes('UNKNOWN') && !document.querySelector('#content').textContent.includes('MJ01-PET-')"));
      await click("continue");await click("toggle-mj01-a");await click("toggle-mj01-b");await click("compare");await click("choose-mj01-a");
      await click("fail");await noRows();
      assert.ok(await evaluate("document.querySelector('#status').textContent.includes('取得失敗')"));
      await click("start");await noRows();await click("end");await noRows();
      await click("start");await click("condition-pet");await click("show");
      // Synthetic lifecycle regression. Independent real navigation/tab QA
      // supplies the evidence for visibility changes and BFCache.
      await evaluate("document.querySelector('#end').focus();window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))");
      await noRows();assert.ok(await evaluate("!!document.querySelector('#start')"));
      await evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))");
      assert.equal(await evaluate("document.activeElement.id"),"start");
      await click("start");await click("condition-step");await click("show");
      await evaluate("document.querySelector('#end').focus();window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));document.querySelector('#heading').focus();window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))");
      await noRows();
      assert.equal(await evaluate("document.activeElement.id"),"heading");
      assert.deepEqual(await evaluate("({local:localStorage.length,session:sessionStorage.length,cookie:document.cookie})"),{local:0,session:0,cookie:""});
      assert.deepEqual(await evaluate("Promise.all([indexedDB.databases(),caches.keys()])"),[[],[]]);
      console.log("MJ01_HTTP_WIDTH "+width+" PASS");
    }
    assert.ok(requests.includes(prefix+"app.js")&&requests.includes(prefix+"model.js")&&requests.includes(prefix+"fixtures.js")&&requests.includes(b2Path));
    assert.deepEqual(browser.requests.filter(u=>!u.startsWith(base+"/")&&!u.startsWith("data:")),[]);
    assert.deepEqual(browser.errors,[]);
    denied=await localServer("127.0.0.2");
    const n=await command("Page.navigate",{url:denied.base+prefix});assert.ok(!n.errorText);
    await until(evaluate,"document.readyState==='complete' && document.querySelector('#prototype')?.hidden","nonallowlisted host");
    assert.equal(await evaluate("document.querySelector('#prototype').hidden"),true);
    assert.equal(await evaluate("!!document.querySelector('#start')"),false);
    console.log("MJ01_HTTP_CHROME PASS");
  }finally{
    try{await stopChrome(browser);}finally{
      await new Promise(resolve=>server.close(resolve));
      if(denied)await new Promise(resolve=>denied.server.close(resolve));
    }
  }
});
