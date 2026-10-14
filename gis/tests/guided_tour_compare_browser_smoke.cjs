#!/usr/bin/env node
"use strict";
/**
 * E-only actual Chromium acceptance for the THREE D-data guided-tour patterns.
 * Run on a temporary Render-equivalent distribution with this E feature's
 * gis/gis assets overlaid by the *shared CI* composite verification job.
 * Real D RegionExport payloads only; not staging, not a safety decision.
 */
const assert = require("node:assert/strict");
const { readFileSync, existsSync, mkdirSync, writeFileSync } = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { auditDirectory } = require("./inspect_local_region_exports.js");
const [distArg, auditArg] = process.argv.slice(2);
if (!distArg || !auditArg || process.argv.length !== 4) {
  throw Error("Usage: <actual-Render-equivalent-output> <public-screens-output>");
}
const distRoot = path.resolve(distArg), out = path.resolve(auditArg);
const sourceReport = auditDirectory(path.join(distRoot, "pipeline/data/output"));
assert.equal(sourceReport.all_local_contracts_valid, true);
const expected = new Map(sourceReport.region_exports.map(x => [x.region_code, x]));
const codes = ["13123", "15100", "23100"];
for (const code of codes) assert.equal(expected.get(code).status, "LOCAL_CONTRACT_OK");
const leaflet = process.env.HINANEX_TEST_LEAFLET_DIST;
if (!leaflet) throw Error("Pinned actual Leaflet library missing");
mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const screens = [];
  const errors = [];
  const ctx = await browser.newContext({
    viewport: { width: 1365, height: 900 },
    locale: "ja-J", reducedMotion: "reduce", permissions: []
  });
  try {
    ctx.on("page", page => page.on("pageerror", error => errors.push(error.message)));
    await ctx.route(/https:\/\/(?:cyberjapandata\.gsi\.go\.jp|disaportaldata\.gsi\.go\.jp)\//,
      route => route.abort("blockedbyclient"));
    for (const [name, mime] of [["leaflet.js","application/javascript"],["leaflet.css","text/css"]]) {
      const local = path.join(leaflet, name);
      assert.ok(existsSync(local), "Leaflet test asset missing " + name);
      await ctx.route("https://unpkg.com/leaflet@1.9.4/dist/" + name,
        route => route.fulfill({status: 200, path: local, contentType: mime,
          headers: {"access-control-allow-origin": "*"}}));
    }
    const page = await ctx.newPage();
    page.setDefaultTimeout(30000);
    const response = await page.goto("http://127.0.0.1:8765/gis/gis/?region=13123",
      {waitUntil:"domcontentloaded"});
    assert.equal(response.status(), 200);
    await page.waitForFunction(() => document.querySelector("#datasetChip")
      ?.textContent?.includes("施設データ読込済"));
    await page.locator("#mapToolScene > summary").click();
    await page.locator("#mapTourOpen").click();
    assert.equal(await page.locator("#mapTourPanel").isVisible(), true);
    for (const code of codes) {
      assert.equal((await page.locator("#mapTourCompare" + code).innerText()).trim(), "未再生");
    }
    const replay = async code => {
      await page.locator("#mapTourCase" + code).click();
      await page.waitForFunction(code => {
        const text = document.querySelector("#mapTourCompare"+code)?.textContent || "";
        return text.includes("取得 ") || text.includes("データ未取得");
      }, code);
      const result = await page.locator("#mapTourCompare" + code).innerText();
      const entry = expected.get(code);
      assert.match(result, new RegExp("取得 " + entry.records + "件"));
      assert.match(result, new RegExp("元座標あり " + entry.mapped + "件"));
      assert.equal(await page.locator("#mapTourCase" + code).getAttribute("aria-pressed"), "true");
      return result;
    };
    const niigata = await replay("15100");
    assert.match(niigata, /元座標あり/);
    assert.equal((await page.locator("#mapTourCompare13123").innerText()).trim(), "未再生");
    await replay("13123");
    const before = await page.locator("#mapTourCompare13123").innerText();
    await replay("23100");
    assert.match(await page.locator("#mapTourSourceStatus").innerText(), /位置は推測しません/);
    assert.equal(await page.locator("#mapTourCompare13123").innerText(), before,
      "One-by-one playback must retain other regional comparison facts");
    await page.screenshot({path:path.join(out,"guided-three-individual-cases.png"),
      animations:"disabled"});
    screens.push("guided-three-individual-cases.png");

    await page.locator("#mapTourStop").click();
    await page.locator("#mapTourStart").click();
    for (let i=0; i<codes.length; i++) {
      const code=codes[i];
      await page.waitForFunction(code => {
        const text = document.querySelector("#mapTourCompare"+code)?.textContent || "";
        return text.includes("取得 ") || text.includes("データ未取得");
      }, code);
      assert.match(await page.locator("#mapTourProgress").innerText(),
        new RegExp((i+1)+" / 3"));
      assert.match(await page.locator("#mapTourCompare"+code).innerText(),
        new RegExp("取得 " + expected.get(code).records + "件"));
      if (i<2) await page.locator("#mapTourNext").click();
    }
    assert.match(await page.locator("#mapTourSourceStatus").innerText(), /位置は推測しません/);
    for (const code of codes) {
      assert.match(await page.locator("#mapTourCompare"+code).innerText(), /取得 .*件/);
    }
    await page.screenshot({path:path.join(out,"guided-three-sequential-comparison.png"),
      animations:"disabled"});
    screens.push("guided-three-sequential-comparison.png");

    await page.locator("#mapTourStop").click();
    assert.equal((await page.locator("#mapTourProgress").innerText()).trim(), "開始前");
    await page.locator("#mapTourCase15100").click();
    await page.waitForFunction(() => document.querySelector("#mapTourCompare15100")
      ?.textContent?.includes("取得 "));
    assert.match(await page.locator("#mapTourProgress").innerText(), /1 \/ 1/);
    await page.locator("#mapTourClose").click();
    assert.equal(await page.locator("#mapTourPanel").isVisible(), false);

    const mobile = await ctx.newPage();
    await mobile.setViewportSize({width:390,height:844});
    await mobile.goto("http://127.0.0.1:8765/gis/gis/?region=13123",
      {waitUntil:"domcontentloaded"});
    await mobile.locator("#mapToolScene > summary").click();
    await mobile.locator("#mapTourOpen").click();
    await mobile.locator("#mapTourCase23100").click();
    await mobile.waitForFunction(() => document.querySelector("#mapTourCompare23100")
      ?.textContent?.includes("取得 "));
    await mobile.screenshot({path:path.join(out,"guided-nagoya-mobile.png"),
      animations:"disabled"});
    screens.push("guided-nagoya-mobile.png");

    assert.deepEqual(errors, []);
    writeFileSync(path.join(out,"guided_three_region_comparison_manifest.json"),
      JSON.stringify({
        status:"E_THREE_REGION_GUIDED_PLAYBACK_CHROMIUM_PASS",
        selected_cases:codes,
        source:"Actual D RegionExports from real Render-equivalent pipeline builder",
        source_results: codes.map(code => ({
          code, records:expected.get(code).records, mapped:expected.get(code).mapped,
          missing_coordinates:expected.get(code).missing_coordinates,
          d_scenario_status:expected.get(code).scenario_status
        })),
        individual_selection_and_replay:true,
        sequential_comparison:true,
        mobile_playback_browser:true,
        no_synthetic_coordinates:true,
        external_tiles_tested:false,
        real_Render_staging_deployed:false,
        real_presenter_90s_rehearsal:false,
        signed_off_shelter_suitability:false,
        screenshots:screens
      },null,2)+"\n","utf8");
    process.stdout.write("E_THREE_REGION_GUIDED_PLAYBACK_CHROMIUM_PASS; actual D only, not shelter recommendation.\n");
  } finally {
    await ctx.close();
    await browser.close();
  }
})().catch(err => {process.stderr.write(String(err.stack||err)+"\n");process.exitCode=1;});
