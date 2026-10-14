#!/usr/bin/env node
"use strict";
/*
 * Test-only 2026-10-22 cross-surface presenter handoff.
 * Requires two loopback HTTP servers, NOT live Render:
 * - :8766 hosts exact B offline ZIP presentation and original C T0 HTML.
 * - :8000 hosts the unchanged Render-equivalent D/E static build.
 * NODE_PATH must point to ephemeral Playwright node_modules; the real
 * Leaflet 1.9.4 resources are intercepted from HINANEX_TEST_LEAFLET_DIST.
 * Browser navigation / source coverage tests are NOT a 420s spoken rehearsal.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const { chromium }=require("playwright");

const [presenterArg, auditArg]=process.argv.slice(2);
if(!presenterArg||!auditArg||process.argv.length!==4)throw new Error("Usage: <exact-presenter-assets-dir> <public-screens-dir>");
const dir=path.resolve(presenterArg), out=path.resolve(auditArg);
const manifest=JSON.parse(fs.readFileSync(path.join(dir,"05_C_20261022_evidence_manifest.json"),"utf8"));
assert.equal(manifest.school_operational_groups,65);
assert.equal(manifest.school_occupancy_detail_rows,66);
assert.equal(manifest.approved_actual_building_pairs,0);
assert.equal(manifest.t1_opening_prediction_accuracy,"NOT_EVALUABLE");
assert.equal(manifest.t2_hazard_prediction_accuracy,"NOT_RUN");
assert.equal(manifest.foundation_89_acceptance,"NOT_SIGNED_OFF_BY_THIS_REPORT");

const expectedPresenter="http://127.0.0.1:8766/01_20261022_seven_minute_rehearsal.html";
const expectedGIS="http://127.0.0.1:8000/gis/gis/?region=13123";
const expectedC="http://127.0.0.1:8766/03_C_20261022_offline_evidence.html";
const leaflet=process.env.HINANEX_TEST_LEAFLET_DIST;
if(!leaflet)throw new Error("CI-only HINANEX_TEST_LEAFLET_DIST not provided");
fs.mkdirSync(out,{recursive:true});
const files=[];
let browser;
async function snap(page,name) {
  const file=name+".png";
  await page.screenshot({path:path.join(out,file),fullPage:false,animations:"disabled"});
  files.push(file);
}
(async()=>{
 try{
  browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  const ctx=await browser.newContext({viewport:{width:1365,height:900},locale:"ja-JP",reducedMotion:"reduce",permissions:[]});
  const errors=[];
  ctx.on("page",p=>p.on("pageerror",e=>errors.push(e.message)));
  await ctx.route(/https:\/\/(?:cyberjapandata\.gsi\.go\.jp|disaportaldata\.gsi\.go\.jp)\//,r=>r.abort("blockedbyclient"));
  for(const [asset,mime] of [["leaflet.js","application/javascript"],["leaflet.css","text/css"]]){
    const sourceFile=path.resolve(leaflet,asset);
    assert.ok(fs.existsSync(sourceFile),"Leaflet pinned test resource missing "+asset);
    await ctx.route("https://unpkg.com/leaflet@1.9.4/dist/"+asset,r=>r.fulfill({
      status:200,path:sourceFile,contentType:mime,
      headers:{"access-control-allow-origin":"*"},
    }));
  }
  const presentation=await ctx.newPage();
  presentation.setDefaultTimeout(30000);
  const initial=await presentation.goto(expectedPresenter,{waitUntil:"domcontentloaded"});
  assert.equal(initial.status(),200);
  assert.equal(await presentation.locator("#remaining").innerText(),"00:40");
  assert.equal(await presentation.locator("#elapsed").innerText(),"00:00 / 07:00");
  assert.equal(await presentation.locator("#timeline > button").count(),7);
  await snap(presentation,"presenter-scene-vision");

  // 1:25: open actual adjacent C file, never a synthetic substitute.
  await presentation.locator('#timeline button[data-index="2"]').click();
  assert.equal(await presentation.locator("#elapsed").innerText(),"01:25 / 07:00");
  const cLink=presentation.locator('#resources a[href="./03_C_20261022_offline_evidence.html"]');
  assert.equal(await cLink.count(),1,"Original C local evidence must be an actual presenter launch");
  const cPopupPromise=ctx.waitForEvent("page");
  await cLink.click();
  const cPopup=await cPopupPromise;
  await cPopup.waitForLoadState("domcontentloaded");
  assert.equal(cPopup.url(),expectedC);
  assert.match(await cPopup.locator("body").innerText(),/T0/);
  assert.equal(await cPopup.locator("body").evaluate(el=>el.innerText.includes("NOT_EVALUABLE")||el.innerText.includes("未評価")),true,
    "Offline C must retain T1 NOT_EVALUABLE interpretation");
  await snap(cPopup,"presenter-open-original-c-evidence");
  await cPopup.close();

  // 2:25: open the actual separate GIS HTTP static distribution.
  await presentation.locator('#timeline button[data-index="3"]').click();
  assert.equal(await presentation.locator("#elapsed").innerText(),"02:25 / 07:00");
  const gisLink=presentation.locator('#resources a[href="'+expectedGIS+'"]');
  assert.equal(await gisLink.count(),1);
  const gisPopupPromise=ctx.waitForEvent("page");
  await gisLink.click();
  const gis=await gisPopupPromise;
  gis.setDefaultTimeout(30000);
  await gis.waitForLoadState("domcontentloaded");
  assert.equal(gis.url(),expectedGIS);
  await gis.waitForFunction(()=>document.querySelector("#datasetChip")?.textContent?.includes("D出力読込済"));
  assert.equal(await gis.locator("#region").inputValue(),"13123");
  assert.ok(Number(await gis.locator("#recordCount").innerText())>0);
  // Exercise the same visible controls the 90-second human cue sheet names.
  await gis.locator("#mapToolScenario > summary").click();
  await gis.locator("#coordinateSearchInput").fill("35.70, 140.10");
  await gis.locator("#coordinateSearchButton").click();
  await gis.waitForFunction(()=>document.querySelector("#coordinateSearchStatus")
    ?.textContent?.includes("指定座標へ移動しました"));
  await gis.locator("#mapToolMarks > summary").click();
  await gis.locator("#facilityDisplayMode").selectOption("both");
  assert.equal(await gis.locator("#facilityDisplayMode").inputValue(),"both");
  await gis.locator("#mapToolScene > summary").click();
  await gis.locator("#mapRegionQuickSelect").selectOption("23100");
  await gis.waitForFunction(()=>document.querySelector("#datasetChip")?.textContent?.includes("D出力読込済")&&document.querySelector("#region")?.value==="23100");
  assert.equal(await gis.locator("#mappedCount").innerText(),"0");
  assert.equal(await gis.locator("#facilityListPanel").isVisible(),true);
  assert.match(await gis.locator("#facilityListCount").innerText(),/取得施設/);
  await snap(gis,"presenter-gis-nagoya-list-fallback");

  // 3:55: return to presenter timeline; this is a browser handoff, NOT
  // evidence that narration / manual actions fit inside the 90-second slot.
  await gis.close();
  await presentation.locator('#timeline button[data-index="4"]').click();
  assert.equal(await presentation.locator("#elapsed").innerText(),"03:55 / 07:00");
  await snap(presentation,"presenter-resume-after-gis");

  assert.deepEqual(errors,[],"Unhandled JS page errors");
  fs.writeFileSync(path.join(out,"presenter_handoff_manifest.json"),JSON.stringify({
    status:"B_C_E_PRESENTER_HANDOFF_ACTUAL_CHROMIUM_PASS",
    offline_C_manifest_exact_prior_audit:true,
    presenter_C_relative_link_browser_popup:"PASS",
    presenter_GIS_loopback_link_browser_popup:"PASS",
    GIS_scene_operations:"D_ACTUAL_MAP_AND_NAGOYA_LIST_ROUTED",
    D_GSI_combined_mode_control:"PASS",
    actual_spoken_seven_minute_rehearsal:false,
    actual_spoken_ninety_second_GIS_rehearsal:false,
    actual_approved_current_shelter:false,
    external_GSI_raster_network_tested:false,
    physical_Edge_Safari_VoiceOver_tested:false,
    real_Render_staging_deployed:false,
    source_external_tiles_blocked_in_CI_only:true,
    screenshot_files:files,
  },null,2)+"\n");
  process.stdout.write("PRESENTER_B_C_E_CHROMIUM_HANDOFF_PASS: exact offline C and real local GIS via 1:25/2:25 scene links; not a timed spoken demo.\n");
  await ctx.close();
 }finally{if(browser)await browser.close();}
})().catch(e=>{process.stderr.write(String(e.stack||e)+"\n");process.exitCode=1;});
