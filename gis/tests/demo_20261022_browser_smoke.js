#!/usr/bin/env node
"use strict";
/*
 * E-only nondeploy GIS browser smoke on a Render-equivalent static distribution.
 * Run after python deploy/build_staging.py builds REAL D RegionExports and an
 * HTTP server serves the temporary output at http://127.0.0.1:8765.
 *
 * NODE_PATH=<ephemeral-playwright-node_modules> node gis/tests/demo_20261022_browser_smoke.js
 *   <temporary-static-root> <audit-output-dir>
 *
 * No disaster suitability inference, live Render deployment, GPS collection,
 * geocoding or C source approval. External raster/map imagery is blocked only
 * during this offline-ish CI test, never in HINANEX production.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { auditDirectory } = require("./inspect_local_region_exports.js");

const [distArg, outArg] = process.argv.slice(2);
if (!distArg || !outArg || process.argv.length !== 4) {
  throw new Error("Usage: <temporary-staging-static-root> <public-audit-output-dir>");
}
const dist = path.resolve(distArg);
const out = path.resolve(outArg);
const base = "http://127.0.0.1:8765";
const regions = ["13123", "15100", "23100"];
const report = auditDirectory(path.join(dist, "pipeline/data/output"));
assert.equal(report.all_local_contracts_valid, true,
  "D bundle is not valid for E's existing D consumer contract");
const expected = new Map(report.region_exports.map(item => [item.region_code, item]));
for (const region of regions) {
  const item = expected.get(region);
  assert.equal(item.status, "LOCAL_CONTRACT_OK", region);
  assert.equal(item.scenario_status, "UNKNOWN",
    "E must not treat D's current unknown as suitability: " + region);
  assert.equal(item.scenario_unknown, item.records,
    "Unreviewed scenario would require explicit C/D approval: " + region);
}

fs.mkdirSync(out, { recursive: true });
const screenshots = [];
const errors = [];
let browser;
const waitUntilLoaded = async (page, code) => {
  await page.waitForFunction(expectedCode => {
    const chip = document.querySelector("#datasetChip");
    const select = document.querySelector("#region");
    return select?.value === expectedCode && chip?.textContent?.includes("施設データ読込済");
  }, code, { timeout: 30000 });
  const row = expected.get(code);
  const count = async id => Number((await page.locator(id).innerText()).trim());
  assert.equal(await count("#recordCount"), row.records, code + " record count");
  assert.equal(await count("#mappedCount"), row.mapped, code + " coordinate count");
  assert.equal(await count("#missingCoordinateCount"),
    row.missing_coordinates, code + " missing coords");
  const statusText = await page.locator("#datasetStatus").innerText();
  assert.match(statusText, /施設データ形式/, code + " expected D source status");
  assert.equal(await page.locator("#region").inputValue(), code);
  assert.equal(row.mapped + row.missing_coordinates, row.records);
  return row;
};
async function selectRegion(page, code) {
  // The left-panel toggle is intentionally not visible on the map-first
  // desktop layout. Use the VISIBLE Scene menu's quick-region selector.
  const scene = page.locator("#mapToolScene");
  if (!(await scene.evaluate(el => el.open))) {
    await page.locator("#mapToolScene > summary").click();
  }
  await page.locator("#mapRegionQuickSelect").selectOption(code);
  const region = await waitUntilLoaded(page, code);
  assert.equal(await page.locator("#mapRegionQuickSelect").inputValue(), code,
    "Scene quick-region control did not stay synchronized");
  return region;
}
async function screenshot(page, name) {
  const file = name + ".png";
  await page.screenshot({
    path: path.join(out, file), animations: "disabled", fullPage: false,
  });
  screenshots.push(file);
}
(async () => {
  try {
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const context = await browser.newContext({
      viewport: { width: 1365, height: 900 },
      locale: "ja-JP",
      reducedMotion: "reduce",
      permissions: [], // location permission is denied, never request actual GPS
    });
    // Raster and base imagery are independent third-party network services.
    // Failures do not mean flood absence. Leaflet JS/CSS still load normally.
    await context.route(/https:\/\/(?:cyberjapandata\.gsi\.go\.jp|disaportaldata\.gsi\.go\.jp)\//,
      route => route.abort("blockedbyclient"));
    // Use the exact pinned Leaflet 1.9.4 JS/CSS from CI-only npm assets.
    // This avoids treating third-party CDN uptime as GIS feature validity.
    // It is still the real Leaflet library, not a simulated DOM/map.
    const leaflet = process.env.HINANEX_TEST_LEAFLET_DIST;
    if (!leaflet) throw new Error("Missing HINANEX_TEST_LEAFLET_DIST (Leaflet 1.9.4 test dependency)");
    const cdn = "https://unpkg.com/leaflet@1.9.4/dist/";
    for (const [asset, type] of [
      ["leaflet.js", "application/javascript"],
      ["leaflet.css", "text/css"],
    ]) {
      const local = path.join(path.resolve(leaflet), asset);
      if (!fs.statSync(local).isFile()) throw new Error("Pinned test Leaflet missing: " + asset);
      await context.route(cdn + asset, route => route.fulfill({
        status: 200, path: local, contentType: type,
        headers: { "access-control-allow-origin": "*" },
      }));
    }
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    page.on("pageerror", e => errors.push(e.message));

    const response = await page.goto(base + "/gis/gis/?region=13123",
      { waitUntil: "domcontentloaded" });
    assert.equal(response.status(), 200, "GIS HTTP entrypoint");
    await page.waitForFunction(() => !!window.L && !!window.HINANEX_D_ADAPTER,
      null, { timeout: 30000 });
    await waitUntilLoaded(page, "13123");
    assert.equal(new URL(page.url()).searchParams.get("region"), "13123");

    // Real-browser gesture smoke, distinct from Node's option-level unit test:
    // verify that the new default produces a zoom change without hiding data.
    const gestureConfig = await page.evaluate(() => ({
      settings: window.HINANEX_MAP_GESTURES.getSettings(),
      perLevel: map.options.wheelPxPerZoomLevel,
      debounce: map.options.wheelDebounceTime,
      basemapDuringZoom: baseMap.options.updateWhenZooming,
      floodDuringZoom: officialFloodLayer.options.updateWhenZooming
    }));
    assert.equal(gestureConfig.settings.sensitivity, 3.75);
    assert.equal(gestureConfig.settings.style, "continuous");
    assert.equal(gestureConfig.perLevel, 27);
    assert.equal(gestureConfig.debounce, 80);
    assert.equal(gestureConfig.basemapDuringZoom, true);
    assert.equal(gestureConfig.floodDuringZoom, false);
    const beforeWheel = await page.evaluate(() => map.getZoom());
    await page.locator("#map").hover();
    await page.mouse.wheel(0, -48);
    await page.waitForTimeout(400);
    const afterWheel = await page.evaluate(() => map.getZoom());
    assert.ok(afterWheel > beforeWheel,
      "wheel input must visibly zoom into the map with new default settings");
    await page.evaluate(z => map.setZoom(z, {animate:false}), beforeWheel);
    await page.waitForTimeout(160);

    // Exercise the assembled Leaflet popup with UI-only synthetic content.
    await page.evaluate(() => window.detail("カードUI表示テスト", [
      ["種別", "表示テスト"], ["住所", "住所の推定ではありません"],
      ["洪水対応分類", "未判定"], ["施設ID", "UI_TEST_ONLY"],
      ["緯度", "未確認"], ["経度", "未確認"]
    ], "D: shelter_location / raw facts", {
      anchor: [35.70, 139.88],
      href: "https://example.test/source",
      note: "安全性や開設状況は未確認です。"
    }));
    const speech = page.locator(".hinanex-place-popup");
    assert.equal(await speech.isVisible(), true);
    assert.equal(await page.locator("#details").isVisible(), false);
    const overview = await speech.innerText();
    assert.match(overview, /未判定/);
    assert.match(overview, /安全性・現在の開設状況は確認できていません/);
    assert.equal(await speech.locator(".place-card-disclosure").count(), 1);
    const fold = speech.locator(".place-card-disclosure").first();
    assert.equal(await fold.evaluate(el => el.open), false);
    await fold.locator("summary").click();
    assert.match(await fold.innerText(), /UI_TEST_ONLY/);
    assert.equal(await speech.locator(".detail-link").getAttribute("rel"),
      "noopener noreferrer");
    assert.equal(await speech.locator(".detail-link").getAttribute("href"),
      "https://example.test/source");
    // The same selected place survives map motion and has a point attachment.
    const anchor = await page.evaluate(() => {
      const p = document.querySelector(".hinanex-place-popup");
      return p && !!p.closest(".leaflet-popup-pane");
    });
    assert.equal(anchor, true);
    await screenshot(page, "anchored-white-place-bubble-desktop");
    const midWidth = await speech.evaluate(el => el.getBoundingClientRect().width);
    assert.equal(await speech.evaluate(el => el.classList.contains("place-bubble--mid")), true);
    // The same source-point bubble changes size as the map zoom changes,
    // without dropping its evidence text or requiring a new marker click.
    await page.evaluate(() => map.setZoom(9));
    await page.waitForTimeout(250);
    assert.equal(await speech.evaluate(el => el.classList.contains("place-bubble--far")), true);
    const farWidth = await speech.evaluate(el => el.getBoundingClientRect().width);
    assert.ok(farWidth < midWidth, "far zoom must use a smaller popup");
    await page.evaluate(() => map.setZoom(15));
    await page.waitForTimeout(250);
    assert.equal(await speech.evaluate(el => el.classList.contains("place-bubble--near")), true);
    const nearWidth = await speech.evaluate(el => el.getBoundingClientRect().width);
    assert.ok(nearWidth > midWidth, "near zoom may show a wider popup");
    assert.match(await speech.innerText(), /未判定/);
    // Boundary fixture is condensed, not promoted into a real shelter.
    await page.evaluate(() => window.detail("江戸川区", [
      ["種類", "自治体境界"], ["地域", "東京都江戸川区"],
      ["自治体コード", "13123"], ["データ状態", "表示確認用fixture"]
    ], "境界fixture", {
      anchor: [35.70,139.88],
      note: "表示確認用で、公式の避難施設判定ではありません。"
    }));
    assert.equal(await speech.locator(".place-card-summary .row").count(), 0);
    assert.match(await speech.innerText(), /自治体境界（参考）/);
    assert.equal(await speech.locator(".place-card-disclosure").count(), 1);
    assert.equal(await speech.evaluate(el => el.classList.contains("place-bubble--boundary")), true);
    await speech.locator(".leaflet-popup-close-button").click();
    assert.equal(await speech.isVisible(), false);

    // Prove real D marker/cluster drawing, not merely an HTTP resource check.
    const clusters = page.locator(".d-facility-cluster");
    for (let attempt = 0; attempt < 7 && await clusters.count() === 0; attempt++) {
      await page.locator(".leaflet-control-zoom-out").click();
      await page.waitForTimeout(250);
    }
    assert.ok(await clusters.count() > 0,
      "Edogawa D marker grouping not visible after real Leaflet zoom-out");
    assert.match(await clusters.first().getAttribute("aria-label"),
      /未判定|安全性未判定/, "D grouping must not imply safety");
    await screenshot(page, "edogawa-d-cluster-desktop");

    await selectRegion(page, "15100");
    assert.equal(new URL(page.url()).searchParams.get("region"), "15100",
      "E region select must update deep link");
    await screenshot(page, "niigata-verified-coordinates-desktop");

    const nagoya = await selectRegion(page, "23100");
    assert.ok(nagoya.records > 0 && nagoya.mapped === 0,
      "Nagoya list-only decision requires real zero mapped D records");
    assert.equal(nagoya.missing_coordinates, nagoya.records);
    assert.equal(await page.locator("#facilityListPanel").isVisible(), true);
    assert.equal(await page.locator("#mapUnavailable").isVisible(), true);
    assert.match(await page.locator("#facilityListCount").innerText(),
      new RegExp("取得施設 " + nagoya.records + "件"));
    assert.equal(await page.locator("#selectOrigin").isDisabled(), true,
      "Map-click source selection must not be offered on a covered map");
    assert.equal(await page.locator("#facilityListResults .facility-list-card").count(),
      Math.min(20, nagoya.records), "List paging must preserve unmapped records");
    await screenshot(page, "nagoya-zero-coordinates-list-desktop");
    await page.locator("#facilityListSearch").fill("__NO_MATCH_GIS_ACCEPTANCE__");
    await page.waitForFunction(() => document.querySelector("#facilityListCount")
      ?.textContent?.includes("検索一致 0件"));
    assert.equal(await page.locator("#facilityListResults .facility-list-card").count(), 0);
    await page.locator("#facilityListSearch").fill("");
    await page.waitForFunction(() => document.querySelectorAll(
      "#facilityListResults .facility-list-card").length > 0);
    // The source's original enum remains available only on expanded detail.
    const firstListItem = page.locator("#facilityListResults .facility-list-card").first();
    await firstListItem.locator("summary").click();
    assert.match(await firstListItem.innerText(), /UNKNOWN/,
      "raw source status must remain available in expert details");

    // User can recover from a refused GPS permission through manual coordinates.
    await selectRegion(page, "13123");
    // Dismiss Scene menu without changing the selected municipality.
    if (await page.locator("#mapToolScene").evaluate(el => el.open)) {
      await page.locator("#mapToolScene > summary").click();
    }
    await page.locator("#mapLocateMe").click();
    await page.waitForFunction(() => {
      const el = document.querySelector("#mapGpsFeedback");
      return el && !el.hidden && /拒否|取得できません|利用できません/.test(el.textContent);
    });
    assert.match(await page.locator("#originStatus").innerText(), /手動で探索/);
    await page.locator("#mapToolScenario > summary").click();
    await page.locator("#coordinateSearchInput").fill("35.70, 140.10");
    await page.locator("#coordinateSearchButton").click();
    await page.waitForFunction(() => document.querySelector("#coordinateSearchStatus")
      ?.textContent?.includes("指定座標へ移動しました"));
    assert.match(await page.locator("#originStatus").innerText(),
      /35\.70|公式|照合|確認|探索|取得|地点/, "Manual coordinate origin not updated");
    await screenshot(page, "gps-denied-manual-origin-desktop");

    // This short guided tour is a presentation aid (~6.5s per stop), NOT
    // the independent, human-paced 90-second GIS demonstration in E's runbook.
    // Verify manual presenter control and the source-only no-position case.
    await page.locator("#mapToolScenario > summary").click();
    await page.locator("#mapToolScene > summary").click();
    await page.locator("#mapTourOpen").click();
    assert.equal(await page.locator("#mapTourPanel").isVisible(), true);
    await page.locator("#mapTourStart").click();
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("1 / 3"));
    await page.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("元データの座標あり"));
    assert.match(await page.locator("#mapTourDescription").innerText(),
      /推奨施設ではありません/);
    await page.locator("#mapTourPause").click();
    assert.match(await page.locator("#mapTourProgress").innerText(), /一時停止/);
    await page.locator("#mapTourNext").click();
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("2 / 3"));
    await page.locator("#mapTourNext").click();
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("3 / 3"));
    await page.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("位置は推測しません"));
    assert.match(await page.locator("#mapTourSourceStatus").innerText(),
      /座標確認済み 0件/);
    await screenshot(page, "presenter-short-tour-unlocated-nagoya");
    await page.locator("#mapTourStop").click();
    assert.equal(await page.locator("#mapTourProgress").innerText(), "開始前");
    await page.locator("#mapTourClose").click();

    // Explicit negative case: D HTTP unavailable must remain an unknown
    // source state, not a synthetic fallback or a zero-facility claim.
    const offlinePage = await context.newPage();
    const blockedD = new RegExp("/pipeline/data/output/(?:edogawa|niigata|nagoya)[.]json(?:[?].*)?$");
    await offlinePage.route(blockedD, route => route.fulfill({
      status: 503, body: "E_TEST_ONLY_D_REGIONEXPORT_UNAVAILABLE",
    }));
    await offlinePage.route("**/pipeline/data/output/gsi_verified_tiles/**",
      route => route.fulfill({ status: 404, body: "E_TEST_NO_VERIFIED_SOURCE" }));
    await offlinePage.route("**/pipeline/data/output/edogawa_flood_site_catalog.json",
      route => route.fulfill({ status: 404, body: "E_TEST_NO_VERIFIED_SOURCE" }));
    const offlineResponse = await offlinePage.goto(base + "/gis/gis/?region=13123",
      { waitUntil: "domcontentloaded" });
    assert.equal(offlineResponse.status(), 200);
    await offlinePage.waitForFunction(() => document.querySelector("#datasetStatus")
      ?.textContent?.includes("読み込めませんでした"));
    assert.match(await offlinePage.locator("#datasetStatus").innerText(),
      /JSONを選択|pipeline/);
    assert.equal(await offlinePage.locator("#recordCount").innerText(), "—");
    await offlinePage.locator("#mapToolScene > summary").click();
    await offlinePage.locator("#mapTourOpen").click();
    await offlinePage.locator("#mapTourStart").click();
    await offlinePage.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("取得・確認できませんでした"));
    assert.match(await offlinePage.locator("#mapTourSourceStatus").innerText(),
      /施設が存在しないという意味ではありません/);
    await screenshot(offlinePage, "missing-d-no-false-zero-tour");
    await offlinePage.locator("#mapTourStop").click();

    // Official GSI tile-derived point cannot be drawn if its C-verification
    // export is unavailable; never invent purple reference sites.
    await offlinePage.locator("#mapTourClose").click();
    await offlinePage.locator("#mapToolScenario > summary").click();
    await offlinePage.locator("#coordinateSearchInput").fill("35.70, 140.10");
    await offlinePage.locator("#coordinateSearchButton").click();
    await offlinePage.waitForFunction(() => document.querySelector("#mapOriginShortcutStatus")
      ?.textContent?.includes("未検証"));
    assert.equal(await offlinePage.locator(".reference-site-marker").count(), 0,
      "Missing C-verified GSI export incorrectly produced a reference marker");
    assert.match(await offlinePage.locator("#floodDiscoveryResults").innerText(),
      /未検証|照合|確認/);
    await screenshot(offlinePage, "missing-verified-gsi-abstain");
    await offlinePage.close();

    // The external flood tile delivery being unavailable never becomes
    // a claim that no flooding exists.
    if (await page.locator("#mapRasterBanner").isVisible()) {
      assert.match(await page.locator("#mapRasterBanner").innerText(),
        /浸水なしではありません/);
    }
    // The actual Leaflet point bubble is scrollable at mobile/tablet widths.
    for (const [width, height] of [[390, 844], [780, 800]]) {
      const mobile = await context.newPage();
      await mobile.setViewportSize({ width, height });
      await mobile.goto(base + "/gis/gis/?region=13123",
        { waitUntil: "domcontentloaded" });
      await waitUntilLoaded(mobile, "13123");
      await mobile.evaluate(() => {
        const extra = Array.from({length:20}, (_, i) =>
          ["表示テスト項目" + i, "出典値の模擬表示（避難判定なし）"]);
        window.detail("選択地点の情報（UI表示テスト）",
          [["種別", "表示テスト"], ["洪水対応分類", "未判定"], ...extra],
          "D: shelter_location / raw facts", {
            anchor: [35.70, 139.88],
            note: "安全性と現在の開設状況は確認できていません。"
          });
      });
      const popup = mobile.locator(".hinanex-place-popup");
      assert.equal(await popup.isVisible(), true);
      const metrics = await popup.evaluate(p => {
        const c = p.querySelector(".leaflet-popup-content");
        const rect = p.getBoundingClientRect();
        return {left:rect.left,right:rect.right,
          overflow:c.scrollHeight > c.clientHeight};
      });
      assert.ok(metrics.left >= -2 && metrics.right <= width + 2,
        "anchored bubble must fit mobile width");
      assert.ok(metrics.overflow, "long point details must scroll in speech bubble");
      await screenshot(mobile, "point-bubble-" + width);
      await mobile.locator(".leaflet-popup-close-button").click();
      assert.equal(await popup.isVisible(), false);
      await mobile.close();
    }

    assert.deepEqual(errors, [], "GIS JS page errors");

    const manifest = {
      status: "E_ACTUAL_D_GIS_CHROMIUM_PREDEPLOY_PASS",
      contract: report.schema,
      executed_on_temp_render_equivalent_static_root: true,
      tested_real_render_staging_url: false,
      human_C_or_D_hazard_approval: false,
      e_map_browser_automated_only: true,
      external_tile_services_tested: false,
      external_tile_requests_blocked_in_test_only: true,
      tested_real_user_gps: false,
      physical_edge_safari_voiceover_tested: false,
      gis_source_automatically_generated_shelter_safety: false,
      region_counts_read_from_current_D_payloads: regions.map(code => {
        const row = expected.get(code);
        return {
          region_code: code, records: row.records, mapped: row.mapped,
          missing_coordinates: row.missing_coordinates,
          d_flood_scenario_status: row.scenario_status,
        };
      }),
      checks: [
        "ALL_3_CURRENT_D_EXPORTS_RENDERED_WITH_RAW_COUNTS",
        "EDOGAWA_ACTUAL_LEAFLET_D_CLUSTER",
        "NAGOYA_UNMAPPED_LIST_SEARCH_AND_NO_GEOCODING",
        "REGION_DEEP_LINK_RETAINS_CODE",
        "GPS_DENIAL_MANUAL_COORDINATES",
        "TILE_FAILURE_NOT_FLOOD_ABSENCE",
        "PRESENTER_SHORT_TOUR_MANUAL_PAUSE_NEXT_STOP",
        "MISSING_D_REGION_NO_FABRICATED_ZERO",
        "MISSING_VERIFIED_GSI_NEVER_DRAWS_REFERENCE_SITE",
      ],
      screenshots,
    };
    fs.writeFileSync(path.join(out, "gis_browser_audit.json"),
      JSON.stringify(manifest, null, 2) + "\n", "utf8");
    process.stdout.write(
      "E_GIS_CHROMIUM_PASS: 3 real D regions, cluster, Nagoya list, " +
      "GPS denied/manual recovery. No live shelter suitability approval.\n");
    await context.close();
  } finally {
    if (browser) await browser.close();
  }
})().catch(err => {
  process.stderr.write(String(err.stack || err) + "\n");
  process.exitCode = 1;
});
