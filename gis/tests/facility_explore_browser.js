"use strict";
// Real Chromium/Leaflet E-only smoke on current generated RegionExports.
// This does NOT accept official hazard semantics or shelter coordinates.
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

async function runFacilityExploreBrowser({context,base,out,waitUntilLoaded}) {
  const result = [];
  for(const [width,height,code] of [[1365,900,"13123"],[390,844,"23100"]]){
    const page = await context.newPage();
    const errors=[];
    page.on("pageerror",err=>errors.push(err.message));
    await page.setViewportSize({width,height});
    try {
      const response=await page.goto(base+"/gis/gis/?region="+code,
        {waitUntil:"domcontentloaded"});
      assert.equal(response.status(),200);
      await waitUntilLoaded(page,code);
      await page.locator("#mapToolScene > summary").click();
      await page.locator("#mapFacilityExploreOpen").click();
      assert.equal(await page.locator("#facilityExplorePanel").isVisible(),true);
      assert.match(await page.locator("#facilityExploreCount").innerText(),/未判定 \d+件/);
      assert.match(await page.locator("#facilityExploreStatus").innerText(),/安全性・開設状況は未認定/);
      assert.ok(await page.locator(".facility-explore-item").count() >= 2);
      await page.locator(".facility-explore-item button").nth(0).click();
      await page.locator(".facility-explore-item button").nth(1).click();
      assert.equal(await page.locator("#facilityExploreComparison .facility-explore-card").count(),2);
      assert.equal(await page.locator("#facilityExploreChoice button").count(),2);
      assert.match(await page.locator("#facilityExploreComparison").innerText(),/未判定/);
      assert.equal(await page.locator("#facilityExploreComparison img").count(),0);
      await page.locator("#facilityExploreChoice button").first().click();
      assert.match(await page.locator("#facilityExploreChoice").innerText(),/本人の確認対象/);
      await page.locator("#facilityExploreFilter").selectOption("UNKNOWN");
      assert.equal(await page.locator("#facilityExploreChoice button").count(),0,
        "changing classification clears the user choice");
      await page.locator("#facilityExploreQuery").fill("NO_MATCH_SYNTHETIC_QUERY");
      assert.match(await page.locator("#facilityExploreList").innerText(),/検索一致なし/);
      assert.equal(await page.locator("#facilityExploreComparison .facility-explore-card").count(),0);
      const geometry=await page.locator("#facilityExplorePanel").evaluate(el=>{
        const rect=el.getBoundingClientRect();
        return {left:rect.left,right:rect.right,height:rect.height};
      });
      assert.ok(geometry.left>=-1 && geometry.right<=width+1,
        "facility explorer stays within viewport");
      assert.ok(geometry.height <= height*.78+2,
        "facility explorer must not occupy entire mobile screen");
      await page.locator("#facilityExploreQuery").fill("");
      const screenshot="facility-explore-"+code+"-"+width+".png";
      await page.screenshot({path:path.join(out,screenshot),animations:"disabled"});
      await page.locator("#facilityExploreClose").click();
      assert.equal(await page.locator("#facilityExplorePanel").isVisible(),false);
      assert.deepEqual(errors,[]);
      result.push({width,code,comparedTwo:true,clearedChoice:true,
        actualDScenarioInput:true,sourceSafetyApproved:false,
        renderedUnlocatedRows:code==="23100",screenshot});
    } finally {await page.close();}
  }
  fs.writeFileSync(path.join(out,"facility_explore_browser_audit.json"),
    JSON.stringify({status:"E_FLOOD_FACILITY_EXPLORER_CHROMIUM_PASS",
      current_RegionExports_only:true,official_semantics_approved:false,
      physical_Safari_tested:false,route_safety_tested:false,checks:result},null,2)+"\n","utf8");
  return result;
}
module.exports={runFacilityExploreBrowser};
