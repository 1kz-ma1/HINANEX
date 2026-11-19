"use strict";
// F02 RegionExport consumer: actual HTTP HTML/CSS/ESM/JSON in headless Chrome.
// CI uses synthetic fixtures. Optional F02_REAL_EXPORT_PATH serves a local generated D JSON.
// Neither mode approves official row identity, shelter suitability, or publication.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const { spawn, spawnSync } = require("node:child_process");
const {waitForDevToolsPort} = require("./helpers/chrome-active-port.cjs");
const root = path.resolve(__dirname, "../..");
const assets = new Set([
  "/frontend/f02.html",
  "/frontend/f02.css",
  "/frontend/src/f02-page.js",
  "/frontend/src/f02-shelter-reference.js",
  "/frontend/src/region-export-loader.js",
  "/frontend/src/region-export-source.js",
]);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function waitForProcessExit(child, timeoutMs) {
  return new Promise(resolve => {
    if (child.exitCode !== null || child.signalCode !== null) { resolve(true); return; }
    let timer;
    const onExit = () => { clearTimeout(timer); resolve(true); };
    timer = setTimeout(() => { child.off("exit", onExit); resolve(false); }, timeoutMs);
    child.once("exit", onExit);
  });
}
function signalChromeTree(child,signal){
  // Chrome's Linux helper processes must be stopped with their isolated group.
  // Windows retains the normal process termination path.
  if(process.platform!=="win32"&&Number.isInteger(child.pid)){
    try{process.kill(-child.pid,signal);return;}
    catch(error){if(error.code!=="ESRCH")throw error;}
  }
  if(child.exitCode===null&&child.signalCode===null)child.kill(signal);
}
async function removeProfileAfterChromeExit(profile){
  // Chrome's helper processes can still flush files after the launcher exits.
  // A failed removal is a test failure, never a reason to claim browser PASS.
  const transient=new Set(["ENOTEMPTY","EBUSY","EPERM","EACCES"]);
  for(let attempt=0;attempt<15;attempt++){
    try{
      await fs.promises.rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:200});
      if(!fs.existsSync(profile))return;
    }catch(error){
      if(!transient.has(error.code)||attempt===14)throw error;
    }
    await wait(300);
  }
  throw Error("Chrome profile remains after bounded cleanup retries: "+profile);
}
async function stopChrome(child,profile,ws=null){
  if(ws){try{ws.close();}catch{/* Chrome may already be terminating. */}}
  if(child.exitCode===null&&child.signalCode===null){
    signalChromeTree(child,"SIGTERM");
    if(!await waitForProcessExit(child,4000)){
      signalChromeTree(child,"SIGKILL");
      if(!await waitForProcessExit(child,4000)){
        throw Error("Chrome did not exit; refusing to remove an active browser profile");
      }
    }
  }
  // The launcher can exit while Chrome helpers still hold the profile/pipe.
  if(process.platform!=="win32")signalChromeTree(child,"SIGTERM");
  if(ws&&ws.readyState!==WebSocket.CLOSED){
    await Promise.race([
      new Promise(resolve=>ws.addEventListener("close",resolve,{once:true})),
      wait(1500),
    ]);
  }
  await removeProfileAfterChromeExit(profile);
}

function browserBinary() {
  for (const name of [process.env.F02_BROWSER_BIN, process.env.CHROME_BIN,
    "/usr/bin/google-chrome", "/usr/bin/chromium", "google-chrome", "chromium"].filter(Boolean)) {
    // Absolute Windows paths use backslashes; a Unix-only slash/which test misses Chrome.
    const filePath = path.isAbsolute(name) || name.includes("/") || name.includes("\\");
    if (filePath && fs.existsSync(name)) return name;
    if (!filePath && spawnSync(process.platform === "win32" ? "where" : "which", [name]).status === 0) return name;
  }
  return null;
}
function syntheticRegionExport() {
  return {
    meta: { schema_version: "0.9" },
    region: { code: "13123", name: "東京都 江戸川区（合成fixture）" },
    datasets: [{
      region_code: "13123", region_name: "東京都 江戸川区（合成fixture）",
      requirement_code: "shelter_location",
      records: [
        { id: "synthetic-1", name: "架空スズラン会館", address: null,
          facility_type: null, supported_disasters: null, latitude: null, longitude: null },
        { id: "synthetic-2", name: "架空青空学園 <script>alert(1)</script>",
          address: "架空町 1-1", facility_type: "Dの元資料値",
          supported_disasters: ["○", "－"], latitude: 35, longitude: 139 },
      ],
      evidence: [{
        source_name: "合成資料", publisher: null, published_at: null,
        fetched_at: "2026-01-01T00:00:00Z",
        source_url: "https://example.invalid/synthetic-f02"
      }]
    }]
  };
}
function fixtureFor(name) {
  const body = syntheticRegionExport();
  if (name === "empty") body.datasets[0].records = [];
  if (name === "missing") body.datasets = [];
  if (name === "bad-region") body.region.code = "15100";
  if (name === "bad-contract") body.datasets[0].records[0].latitude = 35;
  if (name === "long-list" || name === "over-limit") {
    body.datasets[0].records = Array.from({length: name === "over-limit" ? 60 : 50}, (_, i) => ({
      id: "synthetic-scroll-" + i, name: "架空の検証施設" + i,
      address: null, facility_type: null, supported_disasters: null,
      latitude: null, longitude: null
    }));
  }
  if (name === "licensed") {
    body.datasets[0].evidence[0].publisher = "東京都江戸川区（合成検証値）";
    body.datasets[0].evidence[0].license = "CC BY 2.1 JP";
  }
  if (name === "custom-license") body.datasets[0].evidence[0].license = "other";
  if (name === "multiple-sources") {
    body.datasets[0].evidence.push(
      {source_name: "別の合成資料", source_url: "https://example.invalid/second-f02"},
      {source_name: "URL未確認の合成資料", source_url: "http://example.invalid/unverified-f02"}
    );
  }
  return body;
}
async function serve(realOutput = null) {
  const requests = [];
  let scenario = "normal";
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    const name = url.pathname;
    requests.push(name);
    if (req.method !== "GET") { res.writeHead(405); res.end(); return; }
    if (name === "/frontend/f02.html") scenario = url.searchParams.get("scenario") || "normal";
    if (name === "/pipeline/data/output/edogawa.json") {
      if (scenario === "http-error") { res.writeHead(503); res.end("not available"); return; }
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
      res.end(scenario === "real-data" && realOutput !== null ? realOutput : JSON.stringify(fixtureFor(scenario)));
      return;
    }
    if (!assets.has(name)) { res.writeHead(404); res.end(); return; }
    const file = path.join(root, name.slice(1));
    const mime = name.endsWith(".css") ? "text/css" : name.endsWith(".js") ? "text/javascript" : "text/html";
    res.writeHead(200, { "Content-Type": mime + "; charset=utf-8", "Cache-Control": "no-store" });
    fs.createReadStream(file).pipe(res);
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return { server, requests, base: "http://127.0.0.1:" + server.address().port };
}
async function launchChrome(bin) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "f02-consumer-chrome-"));
  const child = spawn(bin, ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--no-first-run", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank"], { stdio: ["ignore", "ignore", "pipe"], detached: process.platform !== "win32" });
  let diagnostics = "";
  child.stderr.on("data", x => { diagnostics = (diagnostics + x.toString()).slice(-1000); });
  let ws = null;
  try {
    const port = await waitForDevToolsPort(profile, child, () => diagnostics);
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list", { signal: AbortSignal.timeout(10000) })).json();
    const page = targets.find(x => x.type === "page" && x.webSocketDebuggerUrl);
    if (!page) throw Error("Chrome CDP page unavailable");
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error("CDP WebSocket open timed out")), 12000);
      ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      ws.addEventListener("error", () => { clearTimeout(timer); reject(Error("CDP WebSocket failed")); }, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    const outbound = [];
    ws.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") {
        exceptions.push(message.params.exceptionDetails.exception?.description ||
          message.params.exceptionDetails.text);
      }
      if (message.method === "Network.requestWillBeSent") outbound.push(message.params.request.url);
      if (!pending.has(message.id)) return;
      const task = pending.get(message.id);
      pending.delete(message.id);
      message.error ? task.reject(Error(message.error.message)) : task.resolve(message.result);
    });
    ws.addEventListener("close", () => {
      for (const task of pending.values()) task.reject(Error("CDP WebSocket closed"));
      pending.clear();
    });
    const command = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(Error("CDP command timed out: " + method));
      }, 15000);
      pending.set(id, {
        resolve: value => { clearTimeout(timer); resolve(value); },
        reject: error => { clearTimeout(timer); reject(error); },
      });
      try { ws.send(JSON.stringify({ id, method, params })); }
      catch (error) { pending.delete(id); clearTimeout(timer); reject(error); }
    });
    const evaluate = async expression => {
      const result = await command("Runtime.evaluate",
        { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) {
        throw Error("Browser JavaScript: " +
          (result.exceptionDetails.exception?.description || result.exceptionDetails.text));
      }
      return result.result.value;
    };
    return { profile, child, ws, command, evaluate, exceptions, outbound };
  } catch (error) {
    await stopChrome(child, profile, ws);
    throw error;
  }
}
async function waitUntil(evaluate, expression, description) {
  for (let i = 0; i < 100; i++) {
    try { if (await evaluate(expression)) return; } catch { /* navigating */ }
    await wait(100);
  }
  throw Error("Timed out waiting for " + description);
}
test("F02 RegionExport consumer works over real HTTP in Chrome with synthetic data",
  { timeout: 120000 }, async t => {
    const bin = browserBinary();
    if (!bin) {
      if (process.env.CI || process.env.F02_REAL_EXPORT_PATH) throw Error("Actual Chrome required for CI or requested real-data acceptance");
      t.skip("Chrome not installed locally");
      return;
    }
    const realOutput = process.env.F02_REAL_EXPORT_PATH ?
      fs.readFileSync(path.resolve(process.env.F02_REAL_EXPORT_PATH), "utf8") : null;
    const expectedRealRecords = realOutput === null ? null :
      JSON.parse(realOutput).datasets.find(item => item?.requirement_code === "shelter_location")?.records.length;
    const { server, requests, base } = await serve(realOutput);
    let browser;
    try {
      browser = await launchChrome(bin);
      const { command, evaluate } = browser;
      await command("Page.enable");
      await command("Runtime.enable");
      await command("Network.enable");
      async function navigate(scenario, condition) {
        const result = await command("Page.navigate", {
          url: base + "/frontend/f02.html?scenario=" + encodeURIComponent(scenario)
        });
        assert.ok(!result.errorText, "HTTP document navigation failure: " + result.errorText);
        await waitUntil(evaluate, condition, "F02 " + scenario);
      }
      async function pressKey(key) {
        const code = key === "Tab" ? 9 : 13;
        await command("Input.dispatchKeyEvent", {
          type: key === "Tab" ? "keyDown" : "rawKeyDown", key, code: key,
          windowsVirtualKeyCode: code, nativeVirtualKeyCode: code
        });
        if (key === "Enter") await command("Input.dispatchKeyEvent", {
          type: "char", text: "\r", unmodifiedText: "\r",
          windowsVirtualKeyCode: code, nativeVirtualKeyCode: code
        });
        await command("Input.dispatchKeyEvent", {
          type: "keyUp", key, code: key,
          windowsVirtualKeyCode: code, nativeVirtualKeyCode: code
        });
      }

      await navigate("normal", "document.readyState==='complete' && !document.querySelector('#search').disabled && document.querySelector('#record-count').textContent.includes('D記録 2件')");
      for (const asset of assets) assert.ok(requests.includes(asset), "Browser did not fetch asset: " + asset);
      assert.ok(requests.includes("/pipeline/data/output/edogawa.json"));
      assert.ok(await evaluate("document.body.innerText.includes('安全性・災害適合性・開設・経路')"));
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 2);
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#sources a')?.href"),
        "https://example.invalid/synthetic-f02");
      assert.equal(await evaluate("document.querySelectorAll('#results script').length"), 0);
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('利用ライセンス（D記録）: 未確認')"));
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('HINANEXが表示用に再構成')"));
      assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('出典：「合成資料」')"));
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('江戸川区がこの画面を作成・承認したものではありません')"));
      assert.ok(await evaluate("document.querySelector('#record-count').textContent.includes('座標なし 1件')"));
      assert.equal(await evaluate("document.querySelector('#search').getAttribute('aria-controls')"), "results");
      assert.equal(await evaluate("document.querySelector('#search').getAttribute('aria-describedby')"), "record-count");
      assert.equal(await evaluate("document.querySelector('#results').getAttribute('role')"), "group");
      assert.ok(await evaluate("document.querySelector('#load-state').getAttribute('aria-live') === 'polite'"));
      assert.equal(await evaluate("document.querySelector('.official-guidance a').href"),
        "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/oshirase/bousaiapuri.html");
      assert.ok(await evaluate("document.querySelector('.official-guidance a').rel.includes('noopener')"));
      assert.ok(await evaluate("document.querySelector('.official-guidance').innerText.includes('最新の開設・混雑状況')"));
      await command("Accessibility.enable");
      const documentNode = (await command("DOM.getDocument")).root.nodeId;
      const countNode = (await command("DOM.querySelector", {nodeId:documentNode, selector:"#record-count"})).nodeId;
      const countAX = (await command("Accessibility.getPartialAXTree", {nodeId:countNode, fetchRelatives:false})).nodes.find(node=>!node.ignored);
      assert.equal(countAX.role?.value, "status", "Search count must be exposed as a status");
      assert.equal(countAX.properties.find(p=>p.name==="live")?.value.value, "polite");
      assert.equal(countAX.properties.find(p=>p.name==="atomic")?.value.value, true);
      await evaluate("(()=>{const q=document.querySelector('#search');q.focus();q.value='ｽｽﾞﾗﾝ';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.ok(await evaluate("document.querySelector('#record-count').textContent.includes('検索一致 1件')"));
      assert.equal(await evaluate("document.activeElement?.id"), "search");
      assert.equal(await evaluate("(()=>{const c=document.querySelector('#record-count'),o=new MutationObserver(()=>{});o.observe(c,{childList:true,characterData:true,subtree:true});const q=document.querySelector('#search');q.value='スズラン';q.dispatchEvent(new Event('input',{bubbles:true}));const n=o.takeRecords().length;o.disconnect();return n})()"), 0,
        "NFKC-equivalent search with equal counts must not rewrite the live region");
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='該当なし';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.ok(await evaluate("document.querySelector('#record-count').textContent.includes('検索一致 0件') && document.querySelector('#load-state').textContent.includes('検索に一致する記録はありません')"));
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.ok(await evaluate("document.querySelector('#record-count').textContent.includes('検索一致 2件')"));
      assert.equal(await evaluate("document.activeElement?.id"), "search");
      console.log("F02_COUNT_HTTP: AX status/polite/atomic, 1/0/2 search counts, stable search focus, no equal-count rewrite PASS");
      const axNodes = (await command("Accessibility.getFullAXTree")).nodes.filter(node => !node.ignored);
      assert.ok(axNodes.some(node => node.role?.value === "searchbox" &&
        node.name?.value === "施設名で検索"), "Search field missing accessible name");
      assert.ok(axNodes.some(node => node.role?.value === "group" &&
        node.name?.value === "施設記録一覧"), "Result group missing accessible name");
      assert.ok(axNodes.some(node => node.role?.value === "link" &&
        node.name?.value?.includes("江戸川区の公式防災アプリ・ポータル案内")),
        "Official live-status link missing accessible name");
      await evaluate("document.querySelector('#search').focus()");
      await command("Input.dispatchKeyEvent", {
        type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9
      });
      await command("Input.dispatchKeyEvent", {
        type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9
      });
      assert.equal(await evaluate("document.activeElement?.matches('#results .record')"), true,
        "Tab did not move from search to first facility");
      await command("Input.dispatchKeyEvent", {
        type: "rawKeyDown", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await command("Input.dispatchKeyEvent", {
        type: "char", text: "\r", unmodifiedText: "\r",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await command("Input.dispatchKeyEvent", {
        type: "keyUp", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await waitUntil(evaluate,
        "document.activeElement?.id==='detail-title' && document.querySelector('#detail').innerText.includes('名称ベース分類')",
        "F02 keyboard facility selection");
      assert.ok(await evaluate("document.querySelector('#detail').innerText.includes('正式指定未確認')"));
      await pressKey("Tab");
      assert.equal(await evaluate("document.activeElement?.id"), "return-to-record",
        "Tab from the detail heading must reach the explicit return action");
      const returnTree = (await command("Accessibility.getFullAXTree")).nodes.filter(node => !node.ignored);
      assert.ok(returnTree.some(node => node.role?.value === "button" &&
        node.name?.value === "選択した施設へ戻る（架空スズラン会館）"));
      await pressKey("Enter");
      assert.deepEqual(await evaluate("({id:document.activeElement?.dataset.recordId,pressed:document.activeElement?.getAttribute('aria-pressed'),query:document.querySelector('#search').value})"),
        {id:"synthetic-1", pressed:"true", query:""}, "Return must preserve selection and search");
      console.log("F02_A11Y_HTTP: named search/group, live status, Tab/Enter, detail focus, and official live-status separation PASS");
      console.log("F02_CONSUMER_HTTP: real HTTP HTML/CSS/ESM/JSON, safety, evidence and escaping PASS");

      assert.equal(await evaluate("(()=>{const q=document.querySelector('#search');q.value='ｽｽﾞﾗﾝ';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelectorAll('#results .record').length})()"), 1);
      assert.ok(await evaluate("(()=>{document.querySelector('#results .record').click();return document.activeElement?.id==='detail-title' && document.querySelector('#detail').innerText.includes('座標なし・位置未確認') && document.querySelector('#detail').innerText.includes('未確認')})()"));
      assert.ok(await evaluate("(()=>{const q=document.querySelector('#search');q.value='該当なし';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelector('#load-state').innerText.includes('検索に一致する記録はありません') && document.querySelectorAll('#results .record').length===0})()"));
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true,
        "Zero matches must remove the stale return action");
      // Regression: a selected facility must not silently reappear as pressed
      // after no-match search clears its details and the query is reset.
      assert.ok(await evaluate("(()=>{const q=document.querySelector('#search');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}));return [...document.querySelectorAll('#results .record')].every(b=>b.getAttribute('aria-pressed')==='false') && document.querySelector('#detail').innerText.includes('施設を選択してください')})()"),
        "Clearing a zero-match search must not restore stale selected/pressed state");
      assert.ok(await evaluate("(()=>{const q=document.querySelector('#search');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}));document.querySelectorAll('#results .record')[1].click();return document.querySelector('#detail').innerText.includes('○ / －') && document.querySelector('#detail').innerText.includes('敷地・入口・指定範囲は未承認')})()"));
      console.log("F02_CONSUMER_HTTP: NFKC search, focus, raw symbols, unknown fields, no-results PASS");

      await navigate("licensed", "document.querySelector('#sources a.license-link') !== null");
      assert.equal(await evaluate("document.querySelector('#sources a.license-link').href"),
        "https://creativecommons.org/licenses/by/2.1/jp/");
      assert.ok(await evaluate("document.querySelector('#sources a.license-link').rel.includes('noopener')"));
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('HINANEXが加工して作成')"));
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('利用ライセンス（D記録）: CC BY 2.1 JP')"));
      await navigate("custom-license", "document.querySelector('#sources').innerText.includes('利用ライセンス（D記録）: other')");
      assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('ライセンスURL: 未確認')"));
      console.log("F02_CREDIT_HTTP: explicit source, adaptation and conditional CC BY 2.1 JP link PASS");
      await navigate("multiple-sources", "document.querySelectorAll('#sources .source').length===3");
      const sourceTree = (await command("Accessibility.getFullAXTree")).nodes.filter(node => !node.ignored);
      for (const name of ["合成資料", "別の合成資料"]) {
        assert.ok(sourceTree.some(node => node.role?.value === "link" &&
          node.name?.value === "資料URLを開く（" + name + "）"));
      }
      assert.deepEqual(await evaluate("[...document.querySelectorAll('#sources a')].map(link=>link.href)"),
        ["https://example.invalid/synthetic-f02", "https://example.invalid/second-f02"]);
      assert.ok(await evaluate("document.querySelector('#sources .source:last-child').textContent.includes('HTTPSの出典URL: 未確認')"));
      console.log("F02_SOURCE_LINK_AX_HTTP: distinct dataset source link names and HTTPS boundaries PASS");

      for (const size of [[320, 700], [390, 844], [1440, 900]]) {
        await command("Emulation.setDeviceMetricsOverride",
          { width: size[0], height: size[1], deviceScaleFactor: 1, mobile: false });
        const metric = await evaluate("({width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth})");
        assert.equal(metric.width, size[0]);
        assert.ok(metric.overflow <= 2, "Horizontal overflow at " + size[0] + "px: " + metric.overflow);
      }
      await command("Emulation.clearDeviceMetricsOverride");
      await command("Emulation.setDeviceMetricsOverride",
        { width: 1440, height: 700, deviceScaleFactor: 1, mobile: false });
      await navigate("long-list", "document.querySelectorAll('#results .record').length===50");
      assert.equal(await evaluate("getComputedStyle(document.querySelector('.columns>.panel:nth-child(2)')).position"),
        "sticky", "Details should remain visible beside a long desktop list");
      const initialScroll = await evaluate("(()=>{const b=document.querySelectorAll('#results .record')[39];b.scrollIntoView({block:'center'});window.__f02ScrollButton=b;return scrollY})()");
      assert.ok(initialScroll > 200, "Long list must actually scroll before testing selection");
      const selected = await evaluate("(()=>{const b=window.__f02ScrollButton;b.click();return {position:scrollY,sameNode:document.querySelectorAll('#results .record')[39]===b,active:document.activeElement?.id,pressed:b.getAttribute('aria-pressed'),detail:document.querySelector('#detail h3')?.innerText}})()");
      assert.ok(Math.abs(selected.position - initialScroll) < 3,
        "Selecting the facility unexpectedly scrolled from " + initialScroll + " to " + selected.position);
      assert.equal(selected.sameNode, true, "Do not replace list buttons when selecting a facility");
      assert.equal(selected.active, "detail-title", "Preserve accessible detail focus without scrolling");
      assert.equal(selected.pressed, "true");
      assert.equal(selected.detail, "架空の検証施設39");
      const nextSelected = await evaluate("(()=>{const b=document.querySelectorAll('#results .record')[40];b.click();return {position:scrollY,pressed:b.getAttribute('aria-pressed'),previous:document.querySelectorAll('#results .record')[39].getAttribute('aria-pressed'),detail:document.querySelector('#detail h3')?.innerText}})()");
      assert.ok(Math.abs(nextSelected.position - initialScroll) < 3,
        "Repeated facility selection unexpectedly scrolled");
      assert.equal(nextSelected.pressed, "true");
      assert.equal(nextSelected.previous, "false");
      assert.equal(nextSelected.detail, "架空の検証施設40");
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F02_SCROLL_HTTP: repeated selection preserves viewport, existing list DOM, detail focus and sticky desktop panel PASS");

      // Explicit return is allowed to scroll, unlike selection's preventScroll.
      // Use a real long list and native Tab/Enter to exercise the focused action.
      for (const [width, height] of [[320,700], [390,844], [1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride",
          {width, height, deviceScaleFactor:1, mobile:false});
        await navigate("long-list", "document.querySelectorAll('#results .record').length===50");
        await evaluate("(()=>{const q=document.querySelector('#search');q.value='架空';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
        for (const index of [39, 40]) {
          await evaluate("(()=>{const b=document.querySelectorAll('#results .record')[" + index + "];window.__f02ReturnButton=b;b.click()})()");
          assert.equal(await evaluate("document.activeElement?.id"), "detail-title");
          await pressKey("Tab");
          assert.equal(await evaluate("document.activeElement?.id"), "return-to-record");
          assert.ok(await evaluate("document.activeElement.getAttribute('aria-label').includes('架空の検証施設" + index + "')"));
          assert.ok(await evaluate("document.activeElement.getBoundingClientRect().height>=44"));
          if (width < 700) assert.ok(await evaluate("window.__f02ReturnButton.getBoundingClientRect().bottom<0"),
            "Mobile return must start with the selected list item off screen");
          await pressKey("Enter");
          const returned = await evaluate("(()=>{const b=document.activeElement,r=b.getBoundingClientRect();return {same:b===window.__f02ReturnButton,id:b.dataset.recordId,pressed:b.getAttribute('aria-pressed'),visible:r.top>=-1&&r.bottom<=innerHeight+1,query:document.querySelector('#search').value,overflow:document.documentElement.scrollWidth-innerWidth}})()");
          assert.equal(returned.same, true, "Restore the original list node at " + width);
          assert.equal(returned.id, "synthetic-scroll-" + index, "Return to latest selection, not first item");
          assert.equal(returned.pressed, "true");
          assert.equal(returned.visible, true, "Return target must be in view at " + width);
          assert.equal(returned.query, "架空");
          assert.ok(returned.overflow <= 2, "Return control must not overflow at " + width);
          assert.ok(await evaluate("document.querySelector('#detail h3').textContent==='架空の検証施設" + index + "'"));
        }
        await evaluate("document.activeElement.click()");
        await pressKey("Tab");
        await pressKey("Tab");
        assert.equal(await evaluate("document.activeElement.textContent"), "データセット全体の出典へ移動");
        await pressKey("Enter");
        assert.equal(await evaluate("document.activeElement.id"), "source-title");
        assert.equal(await evaluate("document.querySelector('#search').value"), "架空");
        assert.equal(await evaluate("document.querySelector('#results [aria-pressed=true]').dataset.recordId"),
          await evaluate("window.__f02ReturnButton.dataset.recordId"));
      }
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F02_RETURN_HTTP: native Tab/Enter returns to latest selected record, visible at 320/390/1440px, query and details unchanged PASS");
      console.log("F02_SOURCE_NAV_HTTP: native Tab/Enter focuses dataset source heading and preserves query and selection PASS");

      await navigate("over-limit", "document.querySelector('#record-count').textContent.includes('D記録 60件')");
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設55';q.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#results .record').click()})()");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), false);
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 50);
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true,
        "Selection beyond the displayed 50 must not retain an unreachable return target");
      assert.ok(await evaluate("document.querySelector('#detail').textContent.includes('施設を選択してください')"));
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設55';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelector('#results .record').getAttribute('aria-pressed')"), "false");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true,
        "Narrowing the search again must not restore an old selection");

      await navigate("empty", "document.querySelector('#load-state')?.innerText.includes('記録は0件です')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 0);
      await navigate("missing", "document.querySelector('#load-state')?.innerText.includes('Datasetが収録されていません')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#search').disabled"), true);
      await navigate("bad-region", "document.querySelector('#load-state')?.innerText.includes('RegionExportを表示できません')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      await navigate("bad-contract", "document.querySelector('#load-state')?.innerText.includes('coordinates')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      await navigate("http-error", "document.querySelector('#load-state')?.innerText.includes('HTTP 503')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      if (realOutput !== null) {
        assert.ok(Number.isInteger(expectedRealRecords) && expectedRealRecords > 0,
          "Real D export must contain at least one shelter_location record");
        await navigate("real-data",
          "document.querySelector(\'#record-count\')?.textContent.includes(\'D記録 " + expectedRealRecords + "件\')");
        assert.equal(await evaluate("document.querySelectorAll(\'#results .record\').length"),
          Math.min(expectedRealRecords, 50));
        assert.ok(await evaluate("document.body.innerText.includes(\'施設単位の\')"));
        console.log("F02_REAL_EXPORT_HTTP: locally supplied D JSON rendered by real HTTP Chrome, structural display PASS; independent C/publication NOT APPROVED");
      }
      assert.ok(browser.exceptions.length === 0,
        "Browser errors: " + browser.exceptions.join(" | "));
      assert.ok(browser.outbound.every(url => url.startsWith(base) ||
        url === "about:blank" || url.startsWith("data:")),
        "Unexpected network request: " + browser.outbound.join("; "));
      console.log("F02_CONSUMER_HTTP: empty/missing/invalid/HTTP-error states, responsive widths and no external requests PASS");
    } finally {
      try {
        if (browser) await stopChrome(browser.child, browser.profile, browser.ws);
      } finally {
        await new Promise((resolve, reject) => {
          server.close(error => error ? reject(error) : resolve());
          server.closeAllConnections();
        });
      }
    }
  });
