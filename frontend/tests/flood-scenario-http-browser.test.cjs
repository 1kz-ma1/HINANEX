"use strict";
// Real application/HTTP/Chrome, with only an explicitly selected synthetic demo.
// No real facility, source approval, disaster safety, or physical-device claim.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const {browserBinary, launchChrome, stopChrome, waitUntil} = require("./helpers/http-chrome.cjs");
const frontend = path.resolve(__dirname, "..");

async function serveDemo() {
  const {regionExport} = await import("./fixtures.js");
  const state = {mode:"ready", requests:[]};
  const assets = new Map([["/frontend/", "index.html"], ["/frontend/styles.css", "styles.css"]]);
  for (const file of fs.readdirSync(path.join(frontend, "src"))) {
    if (file.endsWith(".js")) assets.set("/frontend/src/" + file, "src/" + file);
  }
  function fixture() {
    const payload = regionExport();
    if (state.mode === "legacy") return payload;
    const rows = Array.from({length:state.mode === "empty" ? 0 : 45}, (_, i) => ({
      facility_id:"synthetic-page-" + i, status:"UNKNOWN", reason:"合成記号の意味は判定しません",
      fact:{facility_id:"synthetic-page-" + i, facility_name:"架空の洪水確認施設" + i,
        hazard_scope_raw:"SYNTHETIC_FLOOD", official_status_raw:"○", usable_floor_raw:null,
        join_status:"UNVERIFIED", source_record_trace:"synthetic_row=" + (i + 1),
        source_url:"https://example.invalid/synthetic-flood", latitude:null, longitude:null}
    }));
    if (state.mode === "invalid") rows[0].fact.facility_id = "different-synthetic-id";
    payload.scenarios = [{scenario_id:"flood_shelter_selection", scenario_name:"合成洪水確認",
      region_code:payload.region.code, status:"UNKNOWN",
      requirement_assessment:{discovery_status:"UNKNOWN", raw_value_count:null}, facility_results:rows}];
    return payload;
  }
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    state.requests.push(url.pathname);
    if (req.method !== "GET") {res.writeHead(405);res.end();return;}
    if (url.pathname === "/frontend/mock/region-export.json") {
      if (state.mode === "error") {res.writeHead(503);res.end("synthetic failure");return;}
      res.writeHead(200, {"Content-Type":"application/json; charset=utf-8", "Cache-Control":"no-store"});
      res.end(JSON.stringify(fixture()));return;
    }
    // Initial real-region load deliberately fails; no automatic fixture fallback.
    if (url.pathname.startsWith("/pipeline/data/output/")) {res.writeHead(503);res.end();return;}
    const file = assets.get(url.pathname);
    if (!file) {res.writeHead(404);res.end();return;}
    res.writeHead(200, {"Content-Type":file.endsWith(".js") ? "text/javascript; charset=utf-8" :
      file.endsWith(".css") ? "text/css; charset=utf-8" : "text/html; charset=utf-8", "Cache-Control":"no-store"});
    fs.createReadStream(path.join(frontend, file)).pipe(res);
  });
  await new Promise((resolve, reject) => {server.once("error", reject);server.listen(0, "127.0.0.1", resolve);});
  return {server, state, base:"http://127.0.0.1:" + server.address().port};
}

test("F01 real HTTP Chrome: explicit error recovery and synthetic Scenario paging retain keyboard access",
  {timeout:120000}, async t => {
    const bin = browserBinary();
    if (!bin) {
      if (process.env.CI || process.env.F01_REQUIRE_CHROME === "1") throw Error("Real Chrome required for F01 regression");
      t.skip("Chrome unavailable locally; no browser PASS");return;
    }
    const {server, state, base} = await serveDemo();
    let browser;
    try {
      browser = await launchChrome(bin);
      const {command, evaluate} = browser;
      await command("Page.enable");await command("Runtime.enable");await command("Network.enable");
      const navigation = await command("Page.navigate", {url:base + "/frontend/"});
      assert.ok(!navigation.errorText, navigation.errorText);
      await waitUntil(evaluate, "document.querySelector('#sourceStatus')?.dataset.tone==='error'", "initial HTTP failure");
      assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 0);
      assert.ok(!state.requests.includes("/frontend/mock/region-export.json"), "Must not silently fall back to synthetic demo");
      async function load(mode, condition) {
        state.mode = mode;
        await evaluate("(()=>{document.querySelector('#developerSettings').open=true;const b=document.querySelector('#loadDemoData');b.focus({preventScroll:true});b.click()})()");
        await waitUntil(evaluate, condition, "synthetic demo " + mode);
        assert.equal(await evaluate("document.activeElement?.id"), "loadDemoData", "Loading must not steal focus");
      }
      async function enter() {
        await command("Input.dispatchKeyEvent", {type:"rawKeyDown",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
        await command("Input.dispatchKeyEvent", {type:"char",text:"\r",unmodifiedText:"\r",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
        await command("Input.dispatchKeyEvent", {type:"keyUp",key:"Enter",code:"Enter",windowsVirtualKeyCode:13,nativeVirtualKeyCode:13});
      }
      const dataRequests = () => state.requests.filter(x=>x.startsWith("/pipeline/data/output/") || x==="/frontend/mock/region-export.json").length;
      for (const [width, height] of [[320,700], [390,844], [1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride", {width,height,deviceScaleFactor:1,mobile:false});
        await evaluate("document.querySelector('#developerSettings').open=false;document.querySelector('.error-card button').focus()");
        assert.equal(await evaluate("document.querySelector('.error-card button').textContent"), "読み込み設定を開く");
        assert.ok(await evaluate("document.querySelector('.error-card button').getBoundingClientRect().height>=44"));
        const beforeOpen = dataRequests();
        await enter();
        await evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
        assert.ok(await evaluate("document.querySelector('#developerSettings').open && document.activeElement===document.querySelector('#developerSettings > summary')"));
        assert.equal(dataRequests(), beforeOpen, "Opening settings must not fetch data or silently load demo");
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 0);
        assert.ok(await evaluate("document.querySelector('.scenario-feedback--error').textContent.includes('表示できません')"));
        for (let i=0; i<2; i++) {
          await command("Input.dispatchKeyEvent", {type:"keyDown",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
          await command("Input.dispatchKeyEvent", {type:"keyUp",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
        }
        assert.equal(await evaluate("document.activeElement?.id"), "reloadRegionExport");
        await enter();
        await waitUntil(evaluate, "document.querySelector('#sourceStatus').dataset.tone==='error'", "explicit retry failure");
        assert.equal(dataRequests(), beforeOpen+1, "Only explicit reload may retry the same-origin JSON");
        assert.ok(!state.requests.includes("/frontend/mock/region-export.json"));
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 0);
        assert.ok(await evaluate("document.querySelector('.error-card').scrollWidth-document.querySelector('.error-card').clientWidth<=2"));
      }
      console.log("F01_ERROR_RECOVERY_HTTP: native Enter opens settings/focus without fetch, Tab/Enter explicitly retries, HTTP503 stays empty, 320/390/1440px PASS");
      // Isolate paging from the settings focus/Tab smooth-scroll animation.
      // A fresh document preserves the existing nonzero-scroll assertion.
      const previousTimeOrigin = await evaluate("performance.timeOrigin");
      const reset = await command("Page.navigate", {url:base + "/frontend/"});
      assert.ok(!reset.errorText, reset.errorText);
      await waitUntil(evaluate, "performance.timeOrigin!==" + previousTimeOrigin + " && document.readyState==='complete' && document.querySelector('#sourceStatus')?.dataset.tone==='error'", "fresh paging document");
      const ready = "document.querySelectorAll('.scenario-facility').length===20 && document.querySelector('.scenario-pagination')?.textContent.includes('1/3ページ')";
      for (const [width, height] of [[320,700], [390,844], [1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride", {width,height,deviceScaleFactor:1,mobile:false});
        await load("ready", ready);
        assert.equal(await evaluate("document.querySelector('#demoNotice').hidden"), false);
        // This button is below the viewport. Restoring focus must not scroll to it.
        const baseline = await evaluate("(()=>{scrollTo({top:72,behavior:'instant'});const b=document.querySelector('.scenario-pagination button:last-child');b.focus({preventScroll:true});return {y:scrollY,top:b.getBoundingClientRect().top,height:innerHeight}})()");
        assert.ok(baseline.y>60 && baseline.top>baseline.height, "Nonzero scroll and offscreen paging control required: " + JSON.stringify(baseline));
        await enter();
        await waitUntil(evaluate, "document.querySelector('.scenario-pagination')?.textContent.includes('2/3ページ')", "page 2");
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination button:last-child')"), true,
          "Next page must retain focus on the recreated next control at " + width);
        assert.equal(await evaluate("scrollY"), baseline.y, "Focus restoration must prevent a scroll jump");
        assert.equal(await evaluate("document.querySelector('.scenario-facility h3').textContent"), "架空の洪水確認施設20");
        await enter();
        await waitUntil(evaluate, "document.querySelector('.scenario-pagination')?.textContent.includes('3/3ページ')", "last page");
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination > span')"), true,
          "Disabled next control must transfer focus to the page count, not body or reverse action");
        assert.equal(await evaluate("document.querySelector('.scenario-pagination button:last-child').disabled"), true);
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 5);
        const lastText = await evaluate("document.querySelector('.scenario-pagination').textContent");
        await enter();
        assert.equal(await evaluate("document.querySelector('.scenario-pagination').textContent"), lastText,
          "Enter on page count must not reverse the user's paging direction");
        await evaluate("document.querySelector('.scenario-pagination button:first-child').focus({preventScroll:true})");
        await enter();
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination button:first-child')"), true);
        await enter();
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination > span')"), true);
        assert.equal(await evaluate("document.querySelector('.scenario-pagination button:first-child').disabled"), true);
        assert.ok(await evaluate("document.querySelector('.scenario-pagination').textContent.includes('1/3ページ')"));
        assert.ok(await evaluate("[...document.querySelectorAll('.scenario-facility .status-badge')].every(x=>x.textContent==='D判定：UNKNOWN')"));
        const axNodes = (await command("Accessibility.getFullAXTree")).nodes.filter(node => !node.ignored);
        for (const index of [0, 1]) {
          const name = "公式記録と出典を確認（架空の洪水確認施設" + index + "）";
          assert.ok(axNodes.some(node => node.name?.value === name &&
            node.properties?.some(property => property.name === "expanded" && property.value.value === false)),
          "A collapsed disclosure must expose the visible label and its own facility name");
        }
        await evaluate("document.querySelector('.scenario-trace > summary').focus({preventScroll:true})");
        await enter();
        assert.ok(await evaluate("document.querySelector('.scenario-trace').open && document.querySelectorAll('.scenario-trace[open]').length===1 && document.activeElement===document.querySelector('.scenario-trace > summary')"));
        assert.ok(await evaluate("document.querySelector('.scenario-trace').textContent.includes('synthetic_row=1') && document.querySelector('.scenario-trace').textContent.includes('○')"));
        assert.ok(await evaluate("document.querySelector('.scenario-alert').textContent.includes('安全・開設を保証する情報ではありません')"));
        assert.ok(await evaluate("document.querySelector('#floodScenario').scrollWidth-document.querySelector('#floodScenario').clientWidth<=2"));
      }
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F01_PAGING_HTTP: native Enter, repeated paging, boundary count focus, nonzero scroll, 320/390/1440px, UNKNOWN and trace retained PASS");
      console.log("F01_TRACE_AX_HTTP: named facility disclosures and native Enter open behavior PASS");
      for (const [mode, condition] of [
        ["empty", "document.querySelector('.scenario-feedback--empty')!==null"],
        ["invalid", "document.querySelector('.scenario-feedback--unsupported')!==null"],
        ["legacy", "document.querySelector('#floodScenario').hidden"],
        ["error", "document.querySelector('.scenario-feedback--error')!==null"]
      ]) {
        await load(mode, condition);
        assert.equal(await evaluate("document.querySelector('.scenario-pagination')"), null, mode);
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 0, mode);
      }
      await load("ready", ready);
      assert.ok(await evaluate("document.querySelector('#sourceStatus').dataset.tone==='demo'"));
      assert.equal(await evaluate("localStorage.length+sessionStorage.length"), 0);
      assert.deepEqual(browser.exceptions, []);
      assert.ok(browser.outbound.every(url=>url.startsWith(base + "/") || url==="about:blank" || url.startsWith("data:")), "Unexpected outbound request");
      console.log("F01_PAGING_HTTP: no implicit demo fallback, empty/invalid/legacy/HTTP503 reset, fresh first page, no external requests/storage PASS");
    } finally {
      try {if (browser) await stopChrome(browser.child, browser.profile, browser.ws);}
      finally {await new Promise((resolve,reject)=>{server.close(e=>e?reject(e):resolve());server.closeAllConnections();});}
    }
  });
