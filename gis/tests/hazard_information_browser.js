"use strict";
/*
 * F01/H-01 real Chromium acceptance on a temporary static distribution.
 * Official raster requests are blocked by the parent smoke on purpose;
 * this tests the hazard-only UI, not official imagery availability/safety.
 */
const assert = require("node:assert/strict");
const path = require("node:path");

async function runHazardInformationBrowser({context,base,out,waitUntilLoaded}) {
  const browserPage = await context.newPage();
  const checks = [];
  try {
    // The context denies real location permissions. Do not invoke geolocation.
    await browserPage.setViewportSize({width:390,height:844});
    browserPage.on("pageerror",error => {
      // Preserve the original error for a clear failing CI trace.
      throw Error("F01 browser JavaScript error: " + error.message);
    });
    const response=await browserPage.goto(base+"/gis/gis/?region=13123",
      {waitUntil:"domcontentloaded"});
    assert.equal(response.status(),200,"F01 temporary GIS HTTP route");
    await waitUntilLoaded(browserPage,"13123");

    // F01 must be accessible from 災害情報 independently of F02 facility selection.
    await browserPage.locator("#mapToolHazards > summary").click();
    await browserPage.locator("#hazardGuideOpen").click();
    const guide=browserPage.locator("#hazardGuidePanel");
    assert.equal(await guide.isVisible(),true,"F01 guide opens on phone viewport");
    assert.equal(await browserPage.locator("#hazardGuideOpen").getAttribute("aria-expanded"),"true");
    assert.equal(await browserPage.locator("#hazardGuideRegion").inputValue(),"13123");
    assert.equal(await browserPage.locator("#mapToolHazards").evaluate(el=>el.open),false,
      "hazard-only guide closes existing map tools");
    const position=await guide.boundingBox();
    assert.ok(position && position.x>=-2 &&
      position.x+position.width<=392 &&
      position.y>=-2 && position.y+position.height<=846,
      "F01 guide must fit 390x844 viewport");
    assert.match(await guide.innerText(),/施設を選択せずに/);
    assert.match(await guide.innerText(),/想定最大規模/);
    assert.match(await guide.innerText(),/元図面の作成年・改訂日を特定できません/);
    assert.match(await guide.innerText(),/選択した地域の全域にデータが掲載され/);
    assert.match(await guide.innerText(),/最新性は別/);
    assert.equal(await browserPage.locator("#mapEvidencePanel").isVisible(),false);
    await browserPage.screenshot({path:path.join(out,"f01-hazard-mobile-390.png"),
      animations:"disabled",fullPage:false});
    checks.push("F01_MOBILE_HAZARD_ONLY_VISIBLE_WITH_SOURCE_LIMITS");

    // Switch the existing official flood raster; display-off must never be
    // mistaken for an absence of floods. This is not a physical tile inspection.
    await browserPage.locator("#hazardGuideFlood").uncheck();
    assert.equal(await browserPage.locator("#officialFlood").isChecked(),false);
    assert.match(await browserPage.locator("#hazardGuideStatus").innerText(),
      /非表示.*浸水なし/);
    await browserPage.locator("#hazardGuideFlood").check();
    assert.equal(await browserPage.locator("#officialFlood").isChecked(),true);
    checks.push("F01_FLOOD_LAYER_EXPLICIT_TOGGLE_NO_FALSE_SAFE");

    // Manual region selection must remain in sync with the legacy selector.
    await browserPage.locator("#hazardGuideRegion").selectOption("15100");
    await waitUntilLoaded(browserPage,"15100");
    assert.equal(await browserPage.locator("#region").inputValue(),"15100");
    assert.equal(await browserPage.locator("#hazardGuideRegion").inputValue(),"15100");
    assert.equal(await guide.isVisible(),true);
    checks.push("F01_MANUAL_REGION_USES_EXISTING_D_CONTROLLER");

    // Keyboard navigation: Escape closes, restores focus and aria-expanded.
    await browserPage.keyboard.press("Escape");
    assert.equal(await guide.isVisible(),false);
    assert.equal(await browserPage.locator("#hazardGuideOpen").getAttribute("aria-expanded"),"false");
    assert.equal(await browserPage.evaluate(() => {
      const focused=document.activeElement;
      return focused?.tagName==="SUMMARY" && focused?.parentElement?.id==="mapToolHazards";
    }),true,"Escape should restore keyboard focus to visible 災害情報 menu trigger");
    checks.push("F01_ESCAPE_FOCUS_AND_A11Y_STATE");

    // On desktop the entry still fits and remains separate from the source panel.
    await browserPage.setViewportSize({width:1365,height:900});
    await browserPage.locator("#mapToolHazards > summary").click();
    await browserPage.locator("#hazardGuideOpen").click();
    assert.equal(await guide.isVisible(),true);
    const desktop=await guide.boundingBox();
    assert.ok(desktop && desktop.x>=-2 && desktop.x+desktop.width<=1367,
      "F01 desktop guide must remain on screen");
    await browserPage.screenshot({path:path.join(out,"f01-hazard-desktop-1365.png"),
      animations:"disabled",fullPage:false});
    checks.push("F01_DESKTOP_HAZARD_GUIDE_PRESENT");
    return checks;
  } finally {
    await browserPage.close();
  }
}
module.exports={runHazardInformationBrowser};
