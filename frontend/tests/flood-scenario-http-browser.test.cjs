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
    const rowCount = {empty:0, single:5, singleBoundary:20, multiBoundary:21}[state.mode] ?? 45;
    const rows = Array.from({length:rowCount}, (_, i) => ({
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
      async function tab() {
        await command("Input.dispatchKeyEvent", {type:"keyDown",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
        await command("Input.dispatchKeyEvent", {type:"keyUp",key:"Tab",code:"Tab",windowsVirtualKeyCode:9});
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
        assert.equal(await evaluate("document.querySelector('#floodScenarioTitle').textContent"), "洪水シナリオ（合成デモ）");
        assert.equal(await evaluate("document.querySelector('#floodScenarioNav').textContent"), "洪水Scenario（合成デモ）");
        assert.ok(await evaluate("document.querySelector('.scenario-metrics').textContent.includes('合成raw値の件数') && document.querySelector('.scenario-alert small').textContent.includes('合成データ上の取得状態') && !document.querySelector('.scenario-alert').textContent.includes('新潟市ODS')"));
        // This button is below the viewport. Restoring focus must not scroll to it.
        const baseline = await evaluate("(()=>{scrollTo({top:72,behavior:'instant'});const b=document.querySelector('.scenario-pagination button:last-child');b.focus({preventScroll:true});return {y:scrollY,top:b.getBoundingClientRect().top,height:innerHeight}})()");
        assert.ok(baseline.y>60 && baseline.top>baseline.height, "Nonzero scroll and offscreen paging control required: " + JSON.stringify(baseline));
        await enter();
        await waitUntil(evaluate, "document.querySelector('.scenario-pagination')?.textContent.includes('2/3ページ')", "page 2");
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination button:last-child')"), true,
          "Next page must retain focus on the recreated next control at " + width);
        assert.equal(await evaluate("scrollY"), baseline.y, "Focus restoration must prevent a scroll jump");
        assert.equal(await evaluate("document.querySelector('.scenario-facility h3').textContent"), "架空の洪水確認施設20");
        assert.equal(await evaluate("document.querySelector('#floodScenarioTitle').textContent"), "洪水シナリオ（合成デモ）");
        assert.equal(await evaluate("document.querySelector('.scenario-trace > summary').textContent"), "合成記録と出典を確認");
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
          const name = "合成記録と出典を確認（架空の洪水確認施設" + index + "）";
          assert.ok(axNodes.some(node => node.name?.value === name &&
            node.properties?.some(property => property.name === "expanded" && property.value.value === false)),
          "A collapsed disclosure must expose the visible label and its own facility name");
        }
        await evaluate("document.querySelector('.scenario-trace > summary').focus({preventScroll:true})");
        await enter();
        assert.ok(await evaluate("document.querySelector('.scenario-trace').open && document.querySelectorAll('.scenario-trace[open]').length===1 && document.activeElement===document.querySelector('.scenario-trace > summary')"));
        assert.ok(await evaluate("document.querySelector('.scenario-trace').textContent.includes('synthetic_row=1') && document.querySelector('.scenario-trace').textContent.includes('○')"));
        assert.equal(await evaluate("document.querySelector('.scenario-trace a').textContent"), "合成データの出典URLを開く");
        assert.ok(await evaluate("[...document.querySelectorAll('.scenario-trace dt')].some(dt => dt.textContent === '合成セルの値' && dt.nextElementSibling.textContent === '○')"));
        assert.ok(await evaluate("document.querySelector('.scenario-alert').textContent.includes('安全・開設を保証する情報ではありません')"));
        assert.ok(await evaluate("document.querySelector('#floodScenario').scrollWidth-document.querySelector('#floodScenario').clientWidth<=2"));
      }
      // Exercise deliberate scrolling after the nonzero scroll-preservation assertions.
      for (const [width, height] of [[320,700], [390,844], [1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride", {width,height,deviceScaleFactor:1,mobile:false});
        await load("ready", ready);
        await evaluate("document.querySelector('.scenario-pagination button:last-child').focus({preventScroll:true})");
        await enter();
        await enter();
        assert.equal(await evaluate("document.activeElement===document.querySelector('.scenario-pagination > span')"), true);
        const lastText = await evaluate("document.querySelector('.scenario-pagination').textContent");
        assert.ok(lastText.includes("3/3ページ"));
        const beforeJump = dataRequests();
        const hashBeforeJump = await evaluate("location.hash");
        await tab();
        assert.equal(await evaluate("document.activeElement.textContent"), "このページの施設一覧の先頭へ");
        assert.ok(await evaluate("document.activeElement.getBoundingClientRect().height>=44"));
        const firstResultPosition = `(() => {
          const result = document.querySelector('#floodScenarioFirstResult').getBoundingClientRect();
          const header = document.querySelector('.site-header').getBoundingClientRect();
          return {top:result.top, bottom:result.bottom, headerBottom:header.bottom, viewportHeight:innerHeight};
        })()`;
        await evaluate("document.activeElement.scrollIntoView({block:'start',behavior:'instant'})");
        const before = await evaluate(firstResultPosition);
        if (width < 600) assert.ok(before.bottom < before.headerBottom, "First result must start above the visible area at " + width);
        await enter();
        assert.deepEqual(await evaluate("({active:document.activeElement.id, name:document.activeElement.textContent})"),
          {active:"floodScenarioFirstResult", name:"架空の洪水確認施設40"});
        const after = await evaluate(firstResultPosition);
        assert.ok(after.top >= after.headerBottom && after.bottom <= after.viewportHeight,
          "First result must be immediately visible below the sticky header at " + width + ": " + JSON.stringify(after));
        await tab();
        assert.ok(await evaluate("document.activeElement===document.querySelector('.scenario-trace > summary')"));
        assert.equal(await evaluate("document.querySelector('.scenario-pagination').textContent"), lastText);
        assert.equal(await evaluate("location.hash"), hashBeforeJump);
        assert.equal(dataRequests(), beforeJump, "In-page jump must not load data again");
      }
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F01_PAGING_HTTP: native Enter, repeated paging, boundary count focus, nonzero scroll, 320/390/1440px, UNKNOWN and trace retained PASS");
      console.log("F01_FIRST_RESULT_HTTP: native Tab/Enter reaches the current page's first result and evidence without data reload PASS");
      console.log("F01_TRACE_AX_HTTP: named facility disclosures and native Enter open behavior PASS");
      console.log("F01_SYNTHETIC_TRACE_HTTP: synthetic labels retained across paging, AX and raw evidence display PASS");
      for (const [mode, condition] of [
        ["empty", "document.querySelector('.scenario-feedback--empty')!==null"],
        ["invalid", "document.querySelector('.scenario-feedback--unsupported')!==null"],
        ["legacy", "document.querySelector('#floodScenario').hidden"],
        ["error", "document.querySelector('.scenario-feedback--error')!==null"]
      ]) {
        await load(mode, condition);
        assert.equal(await evaluate("document.querySelector('.scenario-pagination')"), null, mode);
        assert.equal(await evaluate("document.querySelector('.scenario-result-count')"), null, mode);
        assert.equal(await evaluate("document.querySelector('.scenario-first-result-jump')"), null, mode);
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 0, mode);
        if (mode === "error") {
          assert.equal(await evaluate("document.querySelector('#floodScenarioTitle').textContent"), "洪水シナリオ（合成デモ）");
          assert.ok(await evaluate("document.querySelector('.scenario-feedback--error').textContent.includes('合成デモを読み込めませんでした')"));
        }
      }
      await load("single", "document.querySelectorAll('.scenario-facility').length===5 && document.querySelector('.scenario-result-count')?.textContent==='全5件を表示'");
      assert.equal(await evaluate("document.querySelector('.scenario-pagination')"), null);
      assert.equal(await evaluate("document.querySelector('.scenario-first-result-jump')"), null);
      // Verify the exact 20-row page-size boundary, including reloading while
      // the second page is selected. Keep the existing 5/45/0/error cases.
      for (const [width, height] of [[320,700], [390,844], [1440,900]]) {
        await command("Emulation.setDeviceMetricsOverride", {width,height,deviceScaleFactor:1,mobile:false});
        const onePage = "document.querySelectorAll('.scenario-facility').length===20 && document.querySelector('.scenario-result-count')?.textContent==='全20件を表示'";
        const twoPages = "document.querySelectorAll('.scenario-facility').length===20 && document.querySelector('.scenario-pagination')?.textContent.includes('21件中 1〜20件（1/2ページ）')";
        await load("singleBoundary", onePage);
        assert.equal(await evaluate("document.querySelector('.scenario-pagination')"), null);
        assert.equal(await evaluate("document.querySelector('.scenario-first-result-jump')"), null);
        await load("multiBoundary", twoPages);
        assert.equal(await evaluate("document.querySelector('.scenario-result-count')"), null);
        assert.ok(await evaluate("document.querySelector('.scenario-pagination button:first-child').disabled && !document.querySelector('.scenario-pagination button:last-child').disabled"));
        assert.ok(await evaluate("document.querySelector('.scenario-first-result-jump') !== null"));
        await evaluate("document.querySelector('.scenario-pagination button:last-child').focus({preventScroll:true})");
        await enter();
        await waitUntil(evaluate, "document.querySelector('.scenario-pagination')?.textContent.includes('21件中 21〜21件（2/2ページ）')", "21-row last page at " + width);
        assert.equal(await evaluate("document.querySelectorAll('.scenario-facility').length"), 1);
        assert.equal(await evaluate("document.querySelector('.scenario-facility h3').textContent"), "架空の洪水確認施設20");
        assert.ok(await evaluate("document.activeElement===document.querySelector('.scenario-pagination > span')"));
        await evaluate("document.querySelector('.scenario-pagination button:first-child').focus({preventScroll:true})");
        await enter();
        await waitUntil(evaluate, twoPages, "21-row first page at " + width);
        assert.ok(await evaluate("document.activeElement===document.querySelector('.scenario-pagination > span')"));
        await evaluate("document.querySelector('.scenario-pagination button:last-child').focus({preventScroll:true})");
        await enter();
        await waitUntil(evaluate, "document.querySelector('.scenario-pagination')?.textContent.includes('2/2ページ')", "21-row second page before reload");
        await load("singleBoundary", onePage);
        assert.equal(await evaluate("document.querySelector('.scenario-facility h3').textContent"), "架空の洪水確認施設0");
        assert.equal(await evaluate("document.querySelector('.scenario-pagination')"), null);
        assert.equal(await evaluate("document.querySelector('.scenario-first-result-jump')"), null);
        assert.ok(await evaluate("document.querySelector('#floodScenario').scrollWidth-document.querySelector('#floodScenario').clientWidth<=2"));
      }
      await command("Emulation.clearDeviceMetricsOverride");
      console.log("F01_PAGE_SIZE_BOUNDARY_HTTP: 20/21 rows, native Enter, last-page reload, 320/390/1440px PASS");
      await load("ready", ready);
      assert.equal(await evaluate("document.querySelector('.scenario-result-count')"), null);
      assert.ok(await evaluate("document.querySelector('#sourceStatus').dataset.tone==='demo'"));
      await evaluate("document.querySelector('#reloadRegionExport').click()");
      await waitUntil(evaluate, "document.querySelector('#sourceStatus').dataset.tone==='error'", "explicit regional retry after demo");
      assert.equal(await evaluate("document.querySelector('#floodScenarioTitle').textContent"), "洪水に関する公式情報");
      assert.ok(await evaluate("document.querySelector('#demoNotice').hidden && document.querySelectorAll('.scenario-facility').length===0"));
      console.log("F01_SYNTHETIC_SUMMARY_HTTP: labels across demo, paging and failures with no stale rows PASS");
      assert.equal(await evaluate("localStorage.length+sessionStorage.length"), 0);
      assert.deepEqual(browser.exceptions, []);
      assert.ok(browser.outbound.every(url=>url.startsWith(base + "/") || url==="about:blank" || url.startsWith("data:")), "Unexpected outbound request");
      console.log("F01_PAGING_HTTP: no implicit demo fallback, empty/invalid/legacy/HTTP503 reset, fresh first page, no external requests/storage PASS");
    } finally {
      try {if (browser) await stopChrome(browser.child, browser.profile, browser.ws);}
      finally {await new Promise((resolve,reject)=>{server.close(e=>e?reject(e):resolve());server.closeAllConnections();});}
    }
  });
