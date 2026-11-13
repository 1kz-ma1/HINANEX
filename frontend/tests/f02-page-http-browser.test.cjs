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
function browserBinary() {
  for (const name of [process.env.F02_BROWSER_BIN, process.env.CHROME_BIN,
    "/usr/bin/google-chrome", "/usr/bin/chromium", "google-chrome", "chromium"].filter(Boolean)) {
    if (name.includes("/") && fs.existsSync(name)) return name;
    if (!name.includes("/") && spawnSync("which", [name]).status === 0) return name;
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
  if (name === "licensed") {
    body.datasets[0].evidence[0].publisher = "東京都江戸川区（合成検証値）";
    body.datasets[0].evidence[0].license = "CC BY 2.1 JP";
  }
  if (name === "custom-license") body.datasets[0].evidence[0].license = "other";
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
    "--user-data-dir=" + profile, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  let diagnostics = "";
  child.stderr.on("data", x => { diagnostics = (diagnostics + x.toString()).slice(-1000); });
  try {
    let port = 0;
    for (let i = 0; i < 300; i++) {
      const active = path.join(profile, "DevToolsActivePort");
      if (fs.existsSync(active)) {
        port = Number(fs.readFileSync(active, "utf8").split("\n")[0]);
        break;
      }
      if (child.exitCode !== null) throw Error("Chrome exited: " + diagnostics);
      await wait(100);
    }
    if (!port) throw Error("Chrome CDP startup timed out: " + diagnostics);
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list")).json();
    const page = targets.find(x => x.type === "page" && x.webSocketDebuggerUrl);
    if (!page) throw Error("Chrome CDP page unavailable");
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener("open", resolve, { once: true });
      ws.addEventListener("error", reject, { once: true });
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
    const command = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
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
    child.kill("SIGKILL");
    fs.rmSync(profile, { recursive: true, force: true });
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

      await navigate("normal", "document.readyState==='complete' && !document.querySelector('#search').disabled && document.querySelector('#record-count').textContent.includes('D記録 2件')");
      for (const asset of assets) assert.ok(requests.includes(asset), "Browser did not fetch asset: " + asset);
      assert.ok(requests.includes("/pipeline/data/output/edogawa.json"));
      assert.ok(await evaluate("document.body.innerText.includes('安全性・災害適合性・開設・経路')"));
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 2);
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
      console.log("F02_A11Y_HTTP: named search/group, live status, Tab/Enter, detail focus, and official live-status separation PASS");
      console.log("F02_CONSUMER_HTTP: real HTTP HTML/CSS/ESM/JSON, safety, evidence and escaping PASS");

      assert.equal(await evaluate("(()=>{const q=document.querySelector('#search');q.value='ｽｽﾞﾗﾝ';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelectorAll('#results .record').length})()"), 1);
      assert.ok(await evaluate("(()=>{document.querySelector('#results .record').click();return document.activeElement?.id==='detail-title' && document.querySelector('#detail').innerText.includes('座標なし・位置未確認') && document.querySelector('#detail').innerText.includes('未確認')})()"));
      assert.ok(await evaluate("(()=>{const q=document.querySelector('#search');q.value='該当なし';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelector('#load-state').innerText.includes('検索に一致する記録はありません') && document.querySelectorAll('#results .record').length===0})()"));
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

      for (const size of [[320, 700], [390, 844], [1440, 900]]) {
        await command("Emulation.setDeviceMetricsOverride",
          { width: size[0], height: size[1], deviceScaleFactor: 1, mobile: false });
        const metric = await evaluate("({width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth})");
        assert.equal(metric.width, size[0]);
        assert.ok(metric.overflow <= 2, "Horizontal overflow at " + size[0] + "px: " + metric.overflow);
      }
      await command("Emulation.clearDeviceMetricsOverride");
      await navigate("empty", "document.querySelector('#load-state')?.innerText.includes('記録は0件です')");
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 0);
      await navigate("missing", "document.querySelector('#load-state')?.innerText.includes('Datasetが収録されていません')");
      assert.equal(await evaluate("document.querySelector('#search').disabled"), true);
      await navigate("bad-region", "document.querySelector('#load-state')?.innerText.includes('RegionExportを表示できません')");
      await navigate("bad-contract", "document.querySelector('#load-state')?.innerText.includes('coordinates')");
      await navigate("http-error", "document.querySelector('#load-state')?.innerText.includes('HTTP 503')");
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
      if (browser) {
        browser.ws.close();
        browser.child.kill("SIGKILL");
        fs.rmSync(browser.profile, { recursive: true, force: true });
      }
      await new Promise(resolve => server.close(resolve));
    }
  });
