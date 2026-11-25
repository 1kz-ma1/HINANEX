"use strict";
const assert = require("node:assert/strict");
const path = require("node:path");

// Real Chromium smoke with current D exports and Leaflet. External flood
// imagery is blocked by the parent smoke (no live alert source is queried).
async function runOfficialAlertLinksBrowser({context,base,out,waitUntilLoaded}) {
  const page = await context.newPage();
  const checks = [];
  try {
    await page.setViewportSize({width:390,height:844});
    const response = await page.goto(base+"/gis/gis/?region=13123",
      {waitUntil:"domcontentloaded"});
    assert.equal(response.status(),200);
    await waitUntilLoaded(page,"13123");
    await page.locator("#mapToolHazards > summary").click();
    await page.locator("#officialAlertsOpen").click();
    const panel=page.locator("#officialAlertsPanel");
    assert.equal(await panel.isVisible(),true);
    assert.equal(await page.locator("#officialAlertsOpen").getAttribute("aria-expanded"),"true");
    const b=await panel.boundingBox();
    assert.ok(b && b.x>=-2 && b.x+b.width<=392 && b.y>=-2 && b.y+b.height<=846,
      "F06 must fit within the mobile viewport");
    assert.match(await panel.innerText(),/警報・避難指示の取得/);
    assert.match(await panel.innerText(),/外部サイトで最新の情報を確認/);
    assert.match(await page.locator("#officialAlertsRegionName").innerText(),/江戸川区/);
    assert.equal(await page.locator("#officialAlertsLocalLink").getAttribute("href"),
      "https://bosai.city.edogawa.tokyo.jp/");
    assert.equal(await panel.locator('a[href="https://www.jma.go.jp/bosai/"]').count(),1);
    assert.equal(await panel.locator('a[href="https://www.jma.go.jp/bosai/risk/"]').count(),1);
    await page.screenshot({path:path.join(out,"f06-official-links-mobile.png"),
      animations:"disabled",fullPage:false});
    checks.push("F06_MOBILE_OFFICIAL_SOURCES_VISIBLE");

    // Use the existing region selector, not a new region lookup or inferred location.
    for (const [code,name,url] of [
      ["15100","新潟市","https://www.city.niigata.lg.jp/kurashi/bosai/index.html"],
      ["23100","名古屋市","https://www.city.nagoya.jp/bousaiportal/index.html"]
    ]) {
      await page.evaluate(value=>{
        const node=document.querySelector("#region");
        node.value=value;
        node.dispatchEvent(new Event("change",{bubbles:true}));
      },code);
      await waitUntilLoaded(page,code);
      assert.match(await page.locator("#officialAlertsRegionName").innerText(),new RegExp(name));
      assert.equal(await page.locator("#officialAlertsLocalLink").getAttribute("href"),url);
      assert.equal(await panel.isVisible(),true);
    }
    checks.push("F06_OFFICIAL_LOCAL_DIRECTORY_FOLLOWS_EXISTING_REGION");

    // Unrecognized region must not silently reuse the last valid municipality.
    await page.evaluate(()=>{
      const node=document.querySelector("#region");
      node.value="";
      node.dispatchEvent(new Event("change",{bubbles:true}));
    });
    assert.equal(await page.locator("#officialAlertsLocalLink").isVisible(),false);
    assert.match(await page.locator("#officialAlertsRegionNote").innerText(),/未登録/);
    checks.push("F06_UNKNOWN_REGION_NO_WRONG_MUNICIPAL_LINK");

    await page.keyboard.press("Escape");
    assert.equal(await panel.isVisible(),false);
    assert.equal(await page.locator("#officialAlertsOpen").getAttribute("aria-expanded"),"false");
    assert.equal(await page.evaluate(()=>
      document.activeElement?.tagName==="SUMMARY" &&
      document.activeElement?.parentElement?.id==="mapToolHazards"),true);
    checks.push("F06_ESCAPE_FOCUS_RETURNS_TO_VISIBLE_MENU");

    await page.setViewportSize({width:1365,height:900});
    await page.evaluate(()=>{
      const node=document.querySelector("#region");
      node.value="13123";
      node.dispatchEvent(new Event("change",{bubbles:true}));
    });
    await waitUntilLoaded(page,"13123");
    await page.locator("#mapToolHazards > summary").click();
    await page.locator("#officialAlertsOpen").click();
    assert.equal(await panel.isVisible(),true);
    await page.screenshot({path:path.join(out,"f06-official-links-desktop.png"),
      animations:"disabled",fullPage:false});
    checks.push("F06_DESKTOP_ENTRY_STILL_INDEPENDENT_OF_F01");
    return checks;
  } finally {
    await page.close();
  }
}
module.exports={runOfficialAlertLinksBrowser};