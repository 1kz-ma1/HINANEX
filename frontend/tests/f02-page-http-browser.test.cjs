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
// Supervised stress children own all resources, including resources created
// before browser launch finishes. Share the same idempotent cleanup with
// normal finally blocks and cooperative deadline cancellation.
const activeClosers = new Set();
function notifyParent(message) {
  if (process.connected && process.send) process.send(message);
}
function managedCleanup(fn) {
  let pending;
  const close = () => {
    if (!pending) pending = Promise.resolve().then(fn).finally(() => activeClosers.delete(close));
    return pending;
  };
  activeClosers.add(close);
  return close;
}
if (process.env.F02_WP002_REPEAT_CHILD && process.send) {
  let cancelling = false;
  const cancel = async () => {
    if (cancelling) return;
    cancelling = true;
    const results = await Promise.allSettled([...activeClosers].map(close => close()));
    const errors = results.filter(result => result.status === "rejected").map(result => String(result.reason));
    if (process.connected) process.send({type:"cancelled", errors}, () => process.exit(errors.length ? 2 : 1));
    else process.exit(errors.length ? 2 : 1);
  };
  process.on("message", message => { if (message?.type === "cancel") void cancel(); });
  process.on("disconnect", () => { void cancel(); });
  // Keep a normal child from waiting forever for its parent's IPC channel.
  process.channel?.unref();
}
function assertNoPageExceptions(exceptions) {
  assert.equal(exceptions.length, 0, "Unexpected page exceptions: " + exceptions.join(" | "));
}
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
  if (name === "licensed" || name === "wp002-old") {
    body.datasets[0].evidence[0].publisher = "東京都江戸川区（合成検証値）";
    body.datasets[0].evidence[0].license = "CC BY 2.1 JP";
  }
  if (name === "custom-license" || name === "wp002-dom-delay") body.datasets[0].evidence[0].license = "other";
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
  // Associate each data request with its own HTTP document, never the
  // last document that happened to arrive at the server.
  const visits = new Map();
  const held = new Map();
  const heldOnce = new Set();
  function hold(key, res, body) {
    heldOnce.add(key);
    held.set(key, {res, body});
  }
  function release(key) {
    const pending = held.get(key);
    assert.ok(pending, "Missing controlled HTTP response: " + key);
    held.delete(key);
    // Chromium can cancel an old document's pending fetch on navigation.
    if (!pending.res.destroyed) pending.res.end(pending.body);
    return pending.body;
  }
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    const name = url.pathname;
    requests.push(name);
    if (req.method !== "GET") { res.writeHead(405); res.end(); return; }
    if (name === "/frontend/f02.html") {
      const scenario = url.searchParams.get("scenario") || "normal";
      const key = url.pathname + url.search;
      visits.set(key, {scenario, requests: 0});
      if (scenario === "wp002-dom-delay") {
        // Stream the real HTML up to (but not including) the sources DOM.
        // The test releases the tail only after observing the incomplete DOM.
        const html = fs.readFileSync(path.join(root, "frontend/f02.html"), "utf8");
        const split = html.indexOf('<div id="sources">');
        assert.ok(split > 0, "F02 source DOM split point must exist");
        res.writeHead(200, {"Content-Type":"text/html; charset=utf-8",
          "Cache-Control":"no-store", "Referrer-Policy":"same-origin"});
        res.write(html.slice(0, split) + "<!--" + " ".repeat(4096) + "-->");
        hold("dom", res, html.slice(split));
        return;
      }
      if (scenario === "wp002-missing-dom") {
        res.writeHead(200, {"Content-Type":"text/html; charset=utf-8", "Cache-Control":"no-store"});
        res.end("<!doctype html><title>F02 negative DOM fixture</title><p id='search'>incomplete</p>");
        return;
      }
    }
    if (name === "/pipeline/data/output/edogawa.json") {
      // Chrome sends the complete same-origin referrer (including visit).
      // Do not fall back to the most recently requested fixture.
      const referrer = new URL(req.headers.referer || "/", "http://localhost");
      const visit = referrer.origin === "http://127.0.0.1:" + server.address().port
        && referrer.pathname === "/frontend/f02.html"
        ? visits.get(referrer.pathname + referrer.search) : null;
      if (!visit) { res.writeHead(400); res.end("fixture document required"); return; }
      const {scenario} = visit;
      visit.requests += 1;
      if (scenario === "http-error" || (scenario === "http-error-once" && visit.requests === 1)) {
        res.writeHead(503); res.end("not available"); return;
      }
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
      if (scenario === "bad-json") { res.end("{"); return; }
      const body = scenario === "real-data" && realOutput !== null ? realOutput : JSON.stringify(fixtureFor(scenario));
      if (scenario === "wp002-old" && !heldOnce.has("old-export")) {
        res.flushHeaders();
        hold("old-export", res, body);
        return;
      }
      res.end(body);
      return;
    }
    if (!assets.has(name)) { res.writeHead(404); res.end(); return; }
    const file = path.join(root, name.slice(1));
    const mime = name.endsWith(".css") ? "text/css" : name.endsWith(".js") ? "text/javascript" : "text/html";
    res.writeHead(200, { "Content-Type": mime + "; charset=utf-8", "Cache-Control": "no-store", "Referrer-Policy": "same-origin" });
    fs.createReadStream(file).pipe(res);
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const base = "http://127.0.0.1:" + server.address().port;
  const close = managedCleanup(() => new Promise((resolve,reject) => {
    server.close(error => error ? reject(error) : resolve());
    server.closeAllConnections();
  }));
  notifyParent({type:"server", base});
  return { server, requests, held, release, base, close };
}
async function launchChrome(bin) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "f02-consumer-chrome-"));
  const child = spawn(bin, ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--no-first-run", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank"], { stdio: ["ignore", "ignore", "pipe"], detached: process.platform !== "win32" });
  let diagnostics = "";
  child.stderr.on("data", x => { diagnostics = (diagnostics + x.toString()).slice(-1000); });
  let ws = null;
  const close = managedCleanup(() => stopChrome(child, profile, ws));
  notifyParent({type:"chrome", pid:child.pid, profile});
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
    const evaluate = async (expression, {silent = false} = {}) => {
      const result = await command("Runtime.evaluate",
        { expression, returnByValue: true, awaitPromise: true, silent });
      if (result.exceptionDetails) {
        throw Error("Browser JavaScript: " +
          (result.exceptionDetails.exception?.description || result.exceptionDetails.text));
      }
      return result.result.value;
    };
    return { profile, child, ws, command, evaluate, exceptions, outbound, close };
  } catch (error) {
    await close();
    throw error;
  }
}
async function waitUntil(evaluate, expression, description, attempts = 100) {
  for (let i = 0; i < attempts; i++) {
    try {
      if (await evaluate(expression)) return;
    } catch (error) {
      // A navigation can replace the execution context between CDP calls.
      if (!/^(Execution context was destroyed|Cannot find context with specified id)\b/.test(error?.message)) {
        throw error;
      }
    }
    await wait(100);
  }
  throw Error("Timed out waiting for " + description);
}
// Evaluate document identity, DOM readiness and the original assertion in
// one browser execution context. No optional catch around the assertion.
function navigationCondition(url, previousId, condition) {
  return `location.href===${JSON.stringify(url)} &&
    typeof window.__f02TestDocumentId==='string' &&
    window.__f02TestDocumentId!==${JSON.stringify(previousId)} &&
    document.readyState==='complete' &&
    ['search','record-count','load-state','sources','results','retry-load'].every(id=>document.getElementById(id)) &&
    (${condition})`;
}
async function createNavigator(browser, base) {
  const {command, evaluate} = browser;
  // CDP injects this in each new document, even for repeated identical URLs.
  // The marker exists only in this isolated test browser, never product code.
  await command("Page.addScriptToEvaluateOnNewDocument", {
    source: "Object.defineProperty(window,'__f02TestDocumentId',{value:crypto.randomUUID()})"
  });
  let visit = 0;
  async function start(scenario, sameUrl = false) {
    // Referrer-only routing cannot distinguish repeated visits to an identical
    // stateful URL. Only the stateless custom-license fixture may reuse it.
    assert.ok(!sameUrl || scenario === "custom-license",
      "sameUrl is restricted to stateless custom-license");
    const previousId = await evaluate("window.__f02TestDocumentId ?? null");
    const url = base + "/frontend/f02.html?scenario=" + encodeURIComponent(scenario)
      + (sameUrl ? "" : "&visit=" + (++visit));
    const result = await command("Page.navigate", {url});
    assert.ok(!result.errorText, "HTTP document navigation failure: " + result.errorText);
    return {url, previousId, ready: condition => navigationCondition(url, previousId, condition)};
  }
  async function navigate(scenario, condition, sameUrl = false) {
    const next = await start(scenario, sameUrl);
    await waitUntil(evaluate, next.ready(condition), "F02 fresh document " + scenario);
    return next;
  }
  return {start, navigate};
}

test("F02 browser polling retries a replaced document context", async () => {
  let attempts = 0;
  await waitUntil(async () => {
    attempts += 1;
    if (attempts === 1) throw Error("Execution context was destroyed.");
    return true;
  }, "true", "new page");
  assert.equal(attempts, 2);
});
test("F02 browser polling retains the original CDP command error", async () => {
  const commandError = Error("CDP command timed out: Runtime.evaluate");
  let attempts = 0;
  await assert.rejects(waitUntil(async () => {
    attempts += 1;
    if (attempts === 1) throw commandError;
    return true;
  }, "true", "new page"), error => error === commandError);
  assert.equal(attempts, 1);
});
test("WP-002 F02 HTTP Chrome: document and fixture readiness reject false positives",
  { timeout: 120000 }, async t => {
    const bin = browserBinary();
    if (!bin) {
      if (process.env.CI || process.env.F02_REAL_EXPORT_PATH) throw Error("Actual Chrome required for WP-002");
      t.skip("Chrome not installed locally"); return;
    }
    const {base, held, release, close:closeServer} = await serve();
    let browser;
    try {
      browser = await launchChrome(bin);
      const {command, evaluate} = browser;
      await command("Page.enable");
      await command("Runtime.enable");
      await command("Network.enable");
      const {start, navigate} = await createNavigator(browser, base);
      if (process.env.F02_WP002_TIMEOUT_PROBE === "1") {
        // Actual HTTP and Chrome are live; leave a CDP command pending until
        // the supervising deadline cancels this child. Never count as PASS.
        await navigate("normal", "document.querySelector('#record-count').textContent.includes('D記録 2件')");
        notifyParent({type:"probe-ready"});
        await command("Runtime.evaluate", {expression:"new Promise(()=>{})", awaitPromise:true});
        assert.fail("Timeout probe unexpectedly completed");
      }
      await assert.rejects(start("http-error-once", true), /sameUrl is restricted/);
      console.log("WP002_SAME_URL_SCOPE_HTTP: stateful same-URL navigation rejected PASS");
      const licensed = "document.querySelector('#sources a.license-link')?.href==='https://creativecommons.org/licenses/by/2.1/jp/'";
      const custom = "document.querySelector('#sources').innerText.includes('利用ライセンス（D記録）: other')";
      await navigate("licensed", licensed);
      const delay = await start("wp002-dom-delay");
      try {
        await waitUntil(evaluate, `location.href===${JSON.stringify(delay.url)} &&
          !!window.__f02TestDocumentId && window.__f02TestDocumentId!==${JSON.stringify(delay.previousId)} &&
          !!document.querySelector('#search') && !document.querySelector('#sources')`, "controlled incomplete real F02 HTML");
        assert.ok(held.has("dom"));
        // Reproduce the original unguarded L427 failure on deliberately
        // incomplete real HTTP HTML. This is not a natural fixed-main rerun.
        assertNoPageExceptions(browser.exceptions);
        // Silent applies only to this intentional evaluation, not page errors
        // or the normal readiness predicate. exceptionDetails still rejects.
        await assert.rejects(waitUntil(expression => evaluate(expression, {silent:true}), custom, "original unsafe condition"), /Browser JavaScript:.*null.*innerText/s);
        assertNoPageExceptions(browser.exceptions);
        assert.equal(await evaluate(delay.ready(custom)), false);
        assert.equal(await evaluate(delay.ready("true")), false);
      } finally {
        if (held.has("dom")) release("dom");
      }
      await waitUntil(evaluate, delay.ready(custom), "released real F02 HTML with original custom-license condition");
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 2);
      assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
      assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('ライセンスURL: 未確認')"));
      console.log("WP002_DOM_HTTP: unsafe null.innerText reproduced; incomplete DOM cannot pass; released real HTML satisfies original custom-license condition PASS");

      const old = await start("wp002-old");
      await waitUntil(async () => held.has("old-export"), "", "old fixture fetch held at server");
      await navigate("custom-license", custom);
      assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
      const oldBody = JSON.parse(release("old-export"));
      assert.equal(oldBody.datasets[0].evidence[0].license, "CC BY 2.1 JP");
      // Probe a late request with the old document's exact referrer after the
      // new document has loaded; it must never receive the new fixture.
      const late = await fetch(base + "/pipeline/data/output/edogawa.json", {
        headers:{referer:old.url}, signal:AbortSignal.timeout(5000)
      });
      assert.equal(late.status, 200);
      assert.equal((await late.json()).datasets[0].evidence[0].license, "CC BY 2.1 JP");
      const unbound = await fetch(base + "/pipeline/data/output/edogawa.json", {signal:AbortSignal.timeout(5000)});
      assert.equal(unbound.status, 400);
      assert.ok(await evaluate(custom));
      assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
      console.log("WP002_FIXTURE_HTTP: held old browser response and late old-referrer request retain old fixture; new document retains custom license PASS");

      // Ten consecutive real HTTP navigation cycles, no retries of a failed
      // cycle. Explicit same-URL navigation must replace the document marker.
      const markers = new Set();
      for (let i = 0; i < 10; i++) {
        await navigate("licensed", licensed);
        const first = await navigate("custom-license", custom, true);
        const id = await evaluate("window.__f02TestDocumentId");
        assert.equal(await evaluate(navigationCondition(first.url, id, "true")), false,
          "Old document must not satisfy readiness even with matching URL and DOM");
        assert.equal(markers.has(id), false); markers.add(id);
        const second = await navigate("custom-license", custom, true);
        const nextId = await evaluate("window.__f02TestDocumentId");
        assert.equal(second.url, first.url);
        assert.notEqual(nextId, id);
        assert.equal(markers.has(nextId), false); markers.add(nextId);
        assert.equal(await evaluate("document.querySelector('#sources a.license-link')"), null);
        assert.ok(await evaluate("document.querySelector('#sources').innerText.includes('ライセンスURL: 未確認')"));
        console.log("WP002_REPEAT_HTTP: cycle " + (i+1) + "/10 PASS");
      }
      assert.equal(markers.size, 20);

      const missing = await start("wp002-missing-dom");
      await waitUntil(evaluate, `location.href===${JSON.stringify(missing.url)} && document.readyState==='complete'`, "missing DOM negative fixture");
      assert.notEqual(await evaluate("window.__f02TestDocumentId"), missing.previousId);
      assert.equal(await evaluate("document.querySelector('#sources')"), null);
      await assert.rejects(waitUntil(evaluate, missing.ready("true"), "required DOM missing", 3),
        /Timed out waiting for required DOM missing/);
      let jsAttempts = 0;
      await assert.rejects(waitUntil(async expression => {jsAttempts++; return evaluate(expression, {silent:true});},
        "(()=>{throw new Error('WP002 deliberate JavaScript error')})()", "real JavaScript negative"),
        /Browser JavaScript:.*WP002 deliberate JavaScript error/s);
      assert.equal(jsAttempts, 1);
      let cdpAttempts = 0;
      await assert.rejects(waitUntil(async () => {cdpAttempts++; return command("WP002.invalidMethod");},
        "true", "real CDP negative"), /WP002\.invalidMethod.*(found|method)/i);
      assert.equal(cdpAttempts, 1);
      // No page exception is allowed during the entire ordinary flow, even
      // if its message resembles the deliberately evaluated TypeError.
      assertNoPageExceptions(browser.exceptions);
      // Separate explicit negative: an uncaught page callback throws the
      // same null.innerText error. It must be rejected by the zero-error gate.
      await evaluate("setTimeout(()=>document.querySelector('#sources').innerText,0); void 0;\n//# sourceURL=wp002-unexpected-page-negative.js");
      await waitUntil(async () => browser.exceptions.length > 0, "", "uncaught page TypeError");
      assert.equal(browser.exceptions.length, 1);
      assert.match(browser.exceptions[0], /null.*innerText/s);
      assert.match(browser.exceptions[0], /wp002-unexpected-page-negative\.js/);
      assert.throws(() => assertNoPageExceptions(browser.exceptions), /Unexpected page exceptions/);
      console.log("WP002_PAGE_EXCEPTION_HTTP: zero ordinary page exceptions; same-type uncaught page exception rejected PASS");
      assert.ok(browser.outbound.every(url => url.startsWith(base + "/") || url === "about:blank" || url.startsWith("data:")),
        "Unexpected browser outbound request");
      // A protocol rejection is not a transport disconnect. Exercise both:
      // close the actual socket while a CDP command is pending, and ensure
      // waitUntil propagates the close error without another polling attempt.
      let disconnectAttempts = 0;
      const disconnected = waitUntil(async () => {
        disconnectAttempts++;
        return command("Runtime.evaluate", {
          expression:"new Promise(()=>{})", awaitPromise:true, returnByValue:true
        });
      }, "true", "actual CDP disconnect");
      const rejected = assert.rejects(disconnected, /^Error: CDP WebSocket closed$/);
      browser.ws.close();
      await rejected;
      assert.equal(disconnectAttempts, 1);
      console.log("WP002_CDP_DISCONNECT_HTTP: pending command rejects on actual WebSocket close without retry PASS");
      console.log("WP002_NEGATIVE_HTTP: missing DOM times out, genuine JS and CDP errors fail immediately PASS");
    } finally {
      try { if (browser) await browser.close(); }
      finally { await closeServer(); }
    }
  });

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
    const { requests, base, close:closeServer } = await serve(realOutput);
    let browser;
    try {
      browser = await launchChrome(bin);
      const { command, evaluate } = browser;
      await command("Page.enable");
      await command("Runtime.enable");
      await command("Network.enable");
      const {navigate} = await createNavigator(browser, base);
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
      assert.equal(await evaluate("document.querySelector('#return-to-detail').hidden"), true);
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
      await evaluate("document.querySelector('#search').focus()");
      await pressKey("Tab");
      assert.equal(await evaluate("document.activeElement.id"), "clear-search");
      assert.ok(await evaluate("document.activeElement.getBoundingClientRect().height>=44"));
      await pressKey("Enter");
      assert.deepEqual(await evaluate("({focus:document.activeElement.id,query:document.querySelector('#search').value,hidden:document.querySelector('#clear-search').hidden,records:document.querySelectorAll('#results .record').length})"),
        {focus:"search",query:"",hidden:true,records:2});
      assert.ok(await evaluate("[...document.querySelectorAll('#results .record')].every(b=>b.getAttribute('aria-pressed')==='false') && document.querySelector('#detail').innerText.includes('施設を選択してください')"),
        "Clearing a zero-match search must not restore stale selected/pressed state");
      console.log("F02_SEARCH_RECOVERY_HTTP: native Tab/Enter clears a zero-match query, restores results and focuses search PASS");
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
        await pressKey("Tab");
        assert.equal(await evaluate("document.activeElement.id"), "return-to-detail");
        assert.ok(await evaluate("document.activeElement.getBoundingClientRect().height>=44"));
        await pressKey("Enter");
        assert.equal(await evaluate("document.activeElement.id"), "detail-title");
        assert.ok(await evaluate("document.querySelector('#detail h3').textContent==='架空の検証施設40'"));
        assert.equal(await evaluate("document.querySelector('#search').value"), "架空");
        assert.equal(await evaluate("document.querySelector('#results [aria-pressed=true]').dataset.recordId"),
          await evaluate("window.__f02ReturnButton.dataset.recordId"));
        await pressKey("Tab");
        assert.equal(await evaluate("document.activeElement.id"), "return-to-record");
      }
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F02_RETURN_HTTP: native Tab/Enter returns to latest selected record, visible at 320/390/1440px, query and details unchanged PASS");
      console.log("F02_SOURCE_NAV_HTTP: native Tab/Enter moves between dataset source and record headings while preserving query and selection PASS");

      await navigate("over-limit", "document.querySelector('#record-count').textContent.includes('D記録 60件')");
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設55';q.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#results .record').click()})()");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), false);
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 50);
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true,
        "Selection beyond the displayed 50 must not retain an unreachable return target");
      assert.equal(await evaluate("document.querySelector('#return-to-detail').hidden"), true);
      assert.ok(await evaluate("document.querySelector('#detail').textContent.includes('施設を選択してください')"));
      await evaluate("(()=>{const q=document.querySelector('#search');q.value='施設55';q.dispatchEvent(new Event('input',{bubbles:true}))})()");
      assert.equal(await evaluate("document.querySelector('#results .record').getAttribute('aria-pressed')"), "false");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true,
        "Narrowing the search again must not restore an old selection");

      await navigate("empty", "document.querySelector('#load-state')?.innerText.includes('記録は0件です')");
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      assert.ok(await evaluate("document.querySelector('#clear-search').hidden"));
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 0);
      await navigate("missing", "document.querySelector('#load-state')?.innerText.includes('Datasetが収録されていません')");
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      assert.ok(await evaluate("document.querySelector('#clear-search').hidden"));
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#search').disabled"), true);
      await navigate("bad-region", "document.querySelector('#load-state')?.innerText.includes('RegionExportを表示できません')");
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      await navigate("bad-contract", "document.querySelector('#load-state')?.innerText.includes('coordinates')");
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      const exportRequests = () => requests.filter(path => path === "/pipeline/data/output/edogawa.json").length;
      await navigate("bad-json", "document.querySelector('#load-state').classList.contains('error')");
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      const beforeTransportError = exportRequests();
      // Block only the data request, so the page and its modules still load.
      await command("Network.setBlockedURLs", {urls: [base + "/pipeline/data/output/edogawa.json"]});
      try {
        await navigate("network-error", "document.querySelector('#load-state').textContent.includes('取得先に接続できませんでした')");
        assert.equal(exportRequests(), beforeTransportError, "Blocked requests must not reach the fixture server");
        assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 0);
        assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), false);
      } finally {
        await command("Network.setBlockedURLs", {urls: []});
      }
      await evaluate("document.querySelector('#load-state').focus()");
      await pressKey("Tab");
      assert.equal(await evaluate("document.activeElement.id"), "retry-load");
      await pressKey("Enter");
      await waitUntil(evaluate, "document.querySelectorAll('#results .record').length===2", "transport retry restores records");
      assert.equal(exportRequests(), beforeTransportError + 1);
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      assert.equal(await evaluate("document.activeElement.id"), "search");
      assert.equal(await evaluate("document.querySelector('#results [aria-pressed=true]')"), null);
      console.log("F02_TRANSPORT_RETRY_HTTP: a blocked data request and malformed JSON are distinct, explicit retry restores records PASS");
      const beforeError = exportRequests();
      await navigate("http-error", "document.querySelector('#load-state')?.innerText.includes('HTTP 503')");
      assert.ok(await evaluate("document.querySelector('#clear-search').hidden"));
      assert.equal(await evaluate("document.querySelector('#return-to-record').hidden"), true);
      assert.equal(await evaluate("document.querySelector('#return-to-detail').hidden"), true);
      assert.equal(exportRequests(), beforeError + 1, "There must be no automatic retry");
      await evaluate("document.querySelector('#load-state').focus()");
      await pressKey("Tab");
      assert.equal(await evaluate("document.activeElement.id"), "retry-load");
      assert.ok(await evaluate("document.activeElement.getBoundingClientRect().height>=44"));
      await pressKey("Enter");
      await waitUntil(evaluate, "document.querySelector('#load-state').textContent.includes('HTTP 503') && !document.querySelector('#retry-load').hasAttribute('aria-disabled')", "explicit retry still fails");
      assert.equal(exportRequests(), beforeError + 2);
      assert.equal(await evaluate("document.activeElement.id"), "retry-load");
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"), 0);
      assert.equal(await evaluate("(()=>{const retry=document.querySelector('#retry-load');retry.click();retry.click();return retry.getAttribute('aria-disabled')})()"), "true");
      await waitUntil(evaluate, "document.querySelector('#load-state').textContent.includes('HTTP 503') && !document.querySelector('#retry-load').hasAttribute('aria-disabled')", "repeat requests while pending");
      assert.equal(exportRequests(), beforeError + 3, "A second activation while loading must not send a request");

      await navigate("http-error-once", "document.querySelector('#load-state')?.innerText.includes('HTTP 503')");
      const beforeRecovery = exportRequests();
      await evaluate("document.querySelector('#load-state').focus()");
      await pressKey("Tab");
      assert.equal(await evaluate("document.activeElement.id"), "retry-load");
      await pressKey("Enter");
      await waitUntil(evaluate, "document.querySelectorAll('#results .record').length===2", "explicit retry restores records");
      assert.equal(exportRequests(), beforeRecovery + 1);
      assert.equal(await evaluate("document.querySelector('#retry-load').hidden"), true);
      assert.equal(await evaluate("document.activeElement.id"), "search");
      assert.equal(await evaluate("document.querySelector('#results [aria-pressed=true]')"), null);
      console.log("F02_RETRY_HTTP: native Tab/Enter retries only on request, retains focus on repeated HTTP error and restores search on success PASS");
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
        if (browser) await browser.close();
      } finally {
        await closeServer();
      }
    }
  });

// A deadline is enforced by the supervisor before the outer node:test
// timeout. Cooperatively close actual HTTP/Chrome resources, then fail the
// child. If it becomes unresponsive, terminate its reported Chrome groups
// and process, and do not treat the result as a successful cleanup.
async function runStressChild(env, timeoutMs, probe = false) {
  const child = spawn(process.execPath, [__filename], {
    env, cwd:root, stdio:["ignore","pipe","pipe","ipc"]
  });
  let output = "", stderr = "", timedOut = false, acknowledgement = null, fallback = false;
  const resources = {profiles:new Set(), pids:new Set(), bases:new Set()};
  let deadline, escalation;
  const cancel = () => {
    if (timedOut) return;
    timedOut = true;
    if (child.connected) child.send({type:"cancel"}, () => {});
    escalation = setTimeout(() => {
      fallback = true;
      for (const pid of resources.pids) {
        if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], {timeout:5000});
        else {
          try { process.kill(-pid, "SIGKILL"); }
          catch(error) { if (error.code !== "ESRCH") stderr += String(error); }
        }
      }
      if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    }, 12000);
  };
  child.stdout.on("data", chunk => { output += chunk; if (output.length > 2*1024*1024) cancel(); });
  child.stderr.on("data", chunk => { stderr = (stderr + chunk).slice(-65536); });
  child.on("message", message => {
    if (message.type === "chrome") {
      resources.profiles.add(message.profile);
      if (Number.isInteger(message.pid)) resources.pids.add(message.pid);
    } else if (message.type === "server") resources.bases.add(message.base);
    else if (message.type === "cancelled") acknowledgement = message;
    else if (message.type === "probe-ready" && probe && !timedOut) {
      clearTimeout(deadline);
      // A short deadline is intentional only in the controlled negative test.
      deadline = setTimeout(cancel, 100);
    }
  });
  const ended = new Promise((resolve,reject) => {
    child.once("error", reject);
    child.once("close", (code,signal) => resolve({code,signal}));
  });
  deadline = setTimeout(cancel, timeoutMs);
  let status;
  try { status = await ended; }
  finally { clearTimeout(deadline); clearTimeout(escalation); }
  if (fallback) {
    for (const profile of resources.profiles) await removeProfileAfterChromeExit(profile);
    throw Error("F02 stress child required forced termination; cleanup not certified: " + stderr);
  }
  if (timedOut) {
    assert.ok(acknowledgement, "Timed-out child did not acknowledge cleanup: " + stderr);
    assert.deepEqual(acknowledgement.errors, []);
    assert.equal(status.code, 1, "Timed-out child must fail");
    for (const profile of resources.profiles) assert.equal(fs.existsSync(profile), false);
    for (const base of resources.bases) {
      await assert.rejects(fetch(base + "/frontend/f02.html", {signal:AbortSignal.timeout(1000)}),
        error => error.cause?.code === "ECONNREFUSED");
    }
    if (probe) {
      assert.ok(resources.pids.size > 0 && resources.profiles.size > 0 && resources.bases.size > 0,
        "Timeout probe must start real Chrome and HTTP");
      console.log("WP002_TIMEOUT_CLEANUP_HTTP: deadline cancelled live child; Chrome profile removed, HTTP closed, exit failure PASS");
      return {stdout:output};
    }
    throw Error("F02 stress child exceeded deadline; cooperative cleanup completed");
  }
  assert.equal(probe, false, "Timeout probe must hit a deadline");
  assert.equal(status.code, 0, "F02 child failed: " + output + stderr);
  return {stdout:output};
}

// CI-11: independent process per run, no retry, no missing-browser PASS.
// The total supervisor budget leaves cleanup headroom below the existing
// outer test limit. No change to production or shared workflow timeout.
if (!process.env.F02_WP002_REPEAT_CHILD &&
    (process.env.CI || process.env.F02_WP002_REPEAT === "1")) {
  test("WP-002 CI-11 ten consecutive independent F02 test processes",
    {timeout:300000}, async () => {
      const env = {...process.env, CI:"1", F02_WP002_REPEAT_CHILD:"1"};
      delete env.NODE_TEST_CONTEXT;
      delete env.F02_REAL_EXPORT_PATH;
      delete env.F02_WP002_TIMEOUT_PROBE;
      const end = Date.now() + 240000;
      await runStressChild({...env,F02_WP002_TIMEOUT_PROBE:"1"}, 30000, true);
      for (let run=1; run<=10; run++) {
        const remaining = end - Date.now();
        assert.ok(remaining > 0, "F02 stress supervisor budget exhausted");
        const {stdout} = await runStressChild(env, Math.min(remaining, 130000));
        for (const [label,count] of [["tests",4],["pass",4],["fail",0],["skipped",0]]) {
          assert.match(stdout, new RegExp("^# "+label+" "+count+"\\s*$","m"),
            "F02 child "+run+" unexpected TAP summary: "+stdout);
        }
        for (const marker of ["WP002_DOM_HTTP:", "WP002_FIXTURE_HTTP:",
          "WP002_SAME_URL_SCOPE_HTTP:", "WP002_PAGE_EXCEPTION_HTTP:",
          "WP002_CDP_DISCONNECT_HTTP:", "WP002_NEGATIVE_HTTP:",
          "WP002_REPEAT_HTTP: cycle 10/10 PASS", "F02_CREDIT_HTTP:", "F02_RETRY_HTTP:"]) {
          assert.ok(stdout.includes(marker), "F02 child "+run+" missing "+marker);
        }
        console.log("WP002_CI11_PROCESS: "+run+"/10 PASS (4/4 tests, 0 fail, 0 skip)");
      }
    });
}
