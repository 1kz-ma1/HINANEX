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
    return select?.value === expectedCode && chip?.textContent?.includes("D出力読込済");
  }, code, { timeout: 30000 });
  const row = expected.get(code);
  const count = async id => Number((await page.locator(id).innerText()).trim());
  assert.equal(await count("#recordCount"), row.records, code + " record count");
  assert.equal(await count("#mappedCount"), row.mapped, code + " coordinate count");
  assert.equal(await count("#missingCoordinateCount"),
    row.missing_coordinates, code + " missing coords");
  const statusText = await page.locator("#datasetStatus").innerText();
  assert.match(statusText, /RegionExport/, code + " expected D source status");
  assert.equal(await page.locator("#region").inputValue(), code);
  assert.equal(row.mapped + row.missing_coordinates, row.records);
  return row;
};
async function selectRegion(page, code) {
  const layout = page.locator("#gisLayout");
  if (await layout.getAttribute("data-left-panel") !== "open") {
    await page.locator("#toggleLeftPanel").click();
  }
  await page.locator("#region").selectOption(code);
  return waitUntilLoaded(page, code);
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
    assert.match(await page.locator("#facilityListPanel").innerText(), /UNKNOWN/);

    // User can recover from a refused GPS permission through manual coordinates.
    await selectRegion(page, "13123");
    await page.locator("#toggleLeftPanel").click(); // close side sheet
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

    // The external flood tile delivery being unavailable never becomes
    // a claim that no flooding exists.
    if (await page.locator("#mapRasterBanner").isVisible()) {
      assert.match(await page.locator("#mapRasterBanner").innerText(),
        /浸水なしではありません/);
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
