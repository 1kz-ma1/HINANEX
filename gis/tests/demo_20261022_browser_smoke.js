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
    assert.equal(gestureConfig.debounce, 135);
    assert.equal(gestureConfig.basemapDuringZoom, false);
    assert.equal(gestureConfig.floodDuringZoom, false);
    // Real Leaflet projection: the destination grid must cover the complete
    // viewport before it can replace a scaled-out old raster. CI parses this
    // script; assembled Chromium execution is a distinct acceptance step.
    const targetCoverage=await page.evaluate(()=>{
      const size=map.getSize(),point=L.point(size.x/2,size.y/2);
      const grid=destinationTileGrid(point,Math.max(map.getMinZoom(),map.getZoom()-1));
      if(!grid)return null;
      return {count:grid.tiles.length,
        left:Math.min(...grid.tiles.map(t=>t.left)),
        right:Math.max(...grid.tiles.map(t=>t.left+t.size)),
        top:Math.min(...grid.tiles.map(t=>t.top)),
        bottom:Math.max(...grid.tiles.map(t=>t.top+t.size)),
        size:{x:size.x,y:size.y},
        accurateSource:grid.tiles.every(t=>t.url.startsWith(
          "https://cyberjapandata.gsi.go.jp/xyz/std/"))};
    });
    assert.ok(targetCoverage,"a normal zoom-out has manageable full coverage");
    assert.ok(targetCoverage.count<=48 && targetCoverage.count>0);
    assert.ok(targetCoverage.left<=0.01);
    assert.ok(targetCoverage.right>=targetCoverage.size.x-0.01);
    assert.ok(targetCoverage.top<=0.01);
    assert.ok(targetCoverage.bottom>=targetCoverage.size.y-0.01);
    assert.equal(targetCoverage.accurateSource,true);
    // The CSS preview updates immediately; the geographic destination/tile
    // switch should start ~70ms after the final wheel event rather than 135ms.
    assert.deepEqual(await page.evaluate(() => [
      WHEEL_GESTURE_IDLE_MS, WHEEL_PREVIEW_TRANSITION_MS,
      TARGET_CENTER_WAIT_MS, TARGET_COVER_WAIT_MS,
      fullCoverHandoff
    ]),[70,40,180,650,false]);
    const centralTarget = await page.evaluate(() => {
      const size=map.getSize(), point=L.point(size.x/2,size.y/2);
      const grid=destinationTileGrid(point,Math.max(map.getMinZoom(),map.getZoom()-1));
      const central=targetCenterTileIndices(grid);
      return {count:grid?.tiles.length||0,central:central.length,
        fullyOfficial:central.every(i=>grid.tiles[i].url.startsWith(
          "https://cyberjapandata.gsi.go.jp/xyz/std/"))};
    });
    assert.ok(centralTarget.count>=centralTarget.central &&
      centralTarget.central>0,"central geographic grid subset is nonempty");
    assert.equal(centralTarget.fullyOfficial,true);
    // Browser-only test marker. Its position comes from Leaflet's existing
    // viewport projection, NOT from a real or inferred shelter record.
    // Disable transition on this probe so pixel geometry can be asserted
    // synchronously before the 70ms wheel-to-commit timer expires.
    const probeBefore = await page.evaluate(() => {
      const point = L.point(map.getSize().x * 0.7, map.getSize().y * 0.34);
      const stylesheet = document.createElement("style");
      stylesheet.id = "hinanex-wheel-geometry-probe-style";
      stylesheet.textContent =
        ".hinanex-wheel-geometry-probe { transition: none !important; }";
      document.head.appendChild(stylesheet);
      window.__wheelGeometryProbe = L.marker(map.containerPointToLatLng(point), {
        pane: "shelterPane",
        icon: L.divIcon({
          className: "hinanex-wheel-geometry-probe",
          iconSize: [24, 24], iconAnchor: [12, 12]
        })
      }).addTo(map);
      const box = window.__wheelGeometryProbe.getElement().getBoundingClientRect();
      return { x: box.left + box.width / 2, y: box.top + box.height / 2,
        width: box.width, height: box.height };
    });
    assert.equal(probeBefore.width, 24);
    assert.equal(probeBefore.height, 24);
    const wheelPreview = await page.evaluate(() => {
      window.__wheelZoomCalls = 0;
      const oldZoomAround = map.setZoomAround.bind(map);
      map.setZoomAround = (...args) => {
        window.__wheelZoomCalls++;
        window.__wheelLastCommitAt=performance.now();
        return oldZoomAround(...args);
      };
      const before = map.getZoom();
      const el = map.getContainer();
      const rect = el.getBoundingClientRect();
      for (let i = 0; i < 3; i++) {
        el.dispatchEvent(new WheelEvent("wheel", {
          bubbles:true, cancelable:true,
          clientX:rect.left+rect.width/2, clientY:rect.top+rect.height/2,
          deltaMode:0, deltaY:-16
        }));
      }
      return {
        before,
        immediateZoom:map.getZoom(),
        cssScale:map.getPane("tilePane").style.scale,
        cursor: { x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2 },
        probe: (() => {
          const el = window.__wheelGeometryProbe.getElement();
          const box = el.getBoundingClientRect();
          return { x: box.left + box.width / 2, y: box.top + box.height / 2,
            width: box.width, height: box.height, translate: el.style.translate };
        })(),
        markerPaneScale:map.getPanes().mapPane.style.scale,
        floodScale:map.getPane("officialFloodPane").style.scale,
        boundaryScale:map.getPane("boundaryPane").style.scale,
        footprintScale:map.getPane("referenceFootprintPane").style.scale,
        markerTranslations:(()=>{
          const markers=[];
          map.eachLayer(layer=>{
            if(layer.getLatLng && layer.getElement) {
              const elem=layer.getElement();
              if (elem?.style && markers.length<8)
                markers.push({translate:elem.style.translate,
                  width:elem.getBoundingClientRect().width,
                  height:elem.getBoundingClientRect().height});
            }
          });
          return markers;
        })(),
        calls:window.__wheelZoomCalls
      };
    });
    assert.equal(wheelPreview.immediateZoom,wheelPreview.before,
      "the geographic map must remain unchanged while old raster is scaled");
    assert.ok(Number(wheelPreview.cssScale)>1,
      "map image preview must respond before wheel idle timer expires");
    assert.equal(wheelPreview.markerPaneScale,"",
      "facility marker parent must never be uniformly enlarged");
    assert.equal(wheelPreview.boundaryScale,wheelPreview.cssScale,
      "official boundary vector geometry must track the raster immediately");
    assert.equal(wheelPreview.footprintScale,wheelPreview.cssScale,
      "source-backed footprints must track the same visible zoom");
    assert.ok(wheelPreview.markerTranslations.length > 0,
      "the marker translation check must not vacuously pass without any markers");
    assert.ok(wheelPreview.markerTranslations.every(item=>
      item.translate!=="" && item.width>0 && item.height>0),
      "existing source point markers should move without scaling their icons");
    // Inspect rendered DOM pixels, not just the inline CSS translate string.
    // For a zoom anchored at the cursor, the source point must move by the
    // same affine projection as the visible official background raster.
    const visualScale = Number(wheelPreview.cssScale);
    const expectedProbeX = wheelPreview.cursor.x +
      (probeBefore.x - wheelPreview.cursor.x) * visualScale;
    const expectedProbeY = wheelPreview.cursor.y +
      (probeBefore.y - wheelPreview.cursor.y) * visualScale;
    assert.ok(Math.abs(wheelPreview.probe.x - expectedProbeX) < 2,
      "visible source marker x-coordinate must track the raster scale");
    assert.ok(Math.abs(wheelPreview.probe.y - expectedProbeY) < 2,
      "visible source marker y-coordinate must track the raster scale");
    assert.equal(wheelPreview.probe.width, 24,
      "preview must preserve the source marker's rendered width");
    assert.equal(wheelPreview.probe.height, 24,
      "preview must preserve the source marker's rendered height");
    assert.notEqual(wheelPreview.probe.translate, "",
      "off-center source marker must receive a temporary geographic translation");
    assert.ok(Number(wheelPreview.floodScale)>1,
      "official flood raster must visually follow map preview scale");
    assert.equal(wheelPreview.calls,0,
      "no Leaflet destination update while previewing");
    // The center-first official GSI handoff may take up to 180ms AFTER
    // the 70ms wheel-idle window. A fixed 250ms sleep races the boundary
    // under loaded CI; wait for the actual single native commit instead.
    await page.waitForFunction(z=>map.getZoom()>z,wheelPreview.before,
      {timeout:3000});
    const afterWheel = await page.evaluate(() => map.getZoom());
    assert.ok(afterWheel>wheelPreview.before,
      "final wheel target must zoom into the map");
    assert.equal(await page.evaluate(() => window.__wheelZoomCalls),1,
      "one wheel burst must produce exactly one Leaflet view commit");
    assert.equal(await page.evaluate(() => map.getPane("tilePane").style.scale),"",
      "temporary image scaling must be fully cleared after commit");
    // After geographic commit, Leaflet should own the exact projected
    // location again. No CSS preview offsets may remain on the marker.
    const probeAfterCommit = await page.evaluate(() => {
      const layer = window.__wheelGeometryProbe;
      const element = layer.getElement();
      const box = element.getBoundingClientRect();
      const viewport = map.getContainer().getBoundingClientRect();
      const projected = map.latLngToContainerPoint(layer.getLatLng());
      return {
        x: box.left + box.width / 2, y: box.top + box.height / 2,
        expectedX: viewport.left + projected.x,
        expectedY: viewport.top + projected.y,
        width: box.width, height: box.height,
        translate: element.style.translate
      };
    });
    assert.ok(Math.abs(probeAfterCommit.x - probeAfterCommit.expectedX) < 2,
      "marker x-anchor must return to Leaflet after the final geographic commit");
    assert.ok(Math.abs(probeAfterCommit.y - probeAfterCommit.expectedY) < 2,
      "marker y-anchor must return to Leaflet after the final geographic commit");
    assert.equal(probeAfterCommit.width, 24);
    assert.equal(probeAfterCommit.height, 24);
    assert.equal(probeAfterCommit.translate, "",
      "no transient marker translation may survive commit");
    // Run the opposite gesture against the SAME Leaflet marker and same
    // raster pane. Offline GSI imagery may be missing: this is precisely the
    // case where the old coverage limiter froze zoom-out until final commit.
    await page.evaluate(z => map.setZoom(z, {animate:false}), wheelPreview.before);
    await page.waitForTimeout(160);
    // External GSI imagery is deliberately blocked by this runner. The DOM
    // must nevertheless have a bounded, geographically projected official
    // underlay; loading of the true pixels is an independent live-network gate.
    const haloBefore = await page.evaluate(() => {
      buildZoomOutHalo();
      const grid=zoomOutHaloGrid(), entry=zoomOutHalo;
      if (!entry || !grid) return null;
      const first=entry.node.querySelector("img");
      const firstTile=grid.tiles[0];
      const pane=map.getPane("tilePane");
      const viewport=map.getContainer().getBoundingClientRect();
      const paneRect=pane.getBoundingClientRect();
      return {
        count:grid.tiles.length,
        sourceZoom:grid.sourceZoom, currentZoom:map.getZoom(),
        urlsValid:grid.tiles.every(t=>t.url.startsWith(
          "https://cyberjapandata.gsi.go.jp/xyz/std/")),
        sourceMatched:first?.src===firstTile.url,
        tilePositionX:parseFloat(entry.node.style.left)+parseFloat(first.style.left),
        tilePositionY:parseFloat(entry.node.style.top)+parseFloat(first.style.top),
        expectedX:viewport.left-paneRect.left+firstTile.left,
        expectedY:viewport.top-paneRect.top+firstTile.top,
        underNormalTiles:pane.firstChild===entry.node,
        idleVisibility:entry.node.style.visibility
      };
    });
    assert.ok(haloBefore && haloBefore.count>0 && haloBefore.count<=24);
    assert.ok(haloBefore.sourceZoom<haloBefore.currentZoom);
    assert.equal(haloBefore.urlsValid,true);
    assert.equal(haloBefore.sourceMatched,true);
    assert.ok(Math.abs(haloBefore.tilePositionX-haloBefore.expectedX)<0.01);
    assert.ok(Math.abs(haloBefore.tilePositionY-haloBefore.expectedY)<0.01);
    assert.equal(haloBefore.underNormalTiles,true);
    assert.equal(haloBefore.idleVisibility,"hidden");
    const zoomOutPreview = await page.evaluate(() => {
      const layer = window.__wheelGeometryProbe;
      const icon = layer.getElement();
      const beforeBox = icon.getBoundingClientRect();
      const el = map.getContainer();
      const rect = el.getBoundingClientRect();
      const cursor = {x:rect.left+rect.width/2,y:rect.top+rect.height/2};
      const before = {
        zoom:map.getZoom(),
        x:beforeBox.left+beforeBox.width/2,
        y:beforeBox.top+beforeBox.height/2
      };
      window.__wheelOutStartAt=performance.now();
      for (let i=0;i<3;i++) {
        el.dispatchEvent(new WheelEvent("wheel", {
          bubbles:true,cancelable:true,
          clientX:cursor.x,clientY:cursor.y,deltaMode:0,deltaY:16
        }));
      }
      const afterBox=icon.getBoundingClientRect();
      window.__oldWheelHaloNode=zoomOutHalo?.node || null;
      return {
        before,cursor,
        nativeZoom:map.getZoom(),
        scale:Number(map.getPane("tilePane").style.scale),
        boundaryScale:Number(map.getPane("boundaryPane").style.scale),
        floodScale:Number(map.getPane("officialFloodPane").style.scale),
        footprintScale:Number(map.getPane("referenceFootprintPane").style.scale),
        expectedScale:Math.pow(2,wheelDestinationZoom()-map.getZoom()),
        iconX:afterBox.left+afterBox.width/2,
        iconY:afterBox.top+afterBox.height/2,
        iconWidth:afterBox.width,iconHeight:afterBox.height,
        wheelCalls:window.__wheelZoomCalls,
        haloVisibility:zoomOutHalo?.node?.style.visibility,
        haloSamePane:zoomOutHalo?.node?.parentElement===
          map.getPane("tilePane")
      };
    });
    assert.equal(zoomOutPreview.haloVisibility,"visible",
      "the preloaded source-accurate halo must show under shrinking old GSI tiles");
    assert.equal(zoomOutPreview.haloSamePane,true,
      "the halo must share the precise source raster affine zoom transform");
    assert.ok(zoomOutPreview.scale>0 && zoomOutPreview.scale<1,
      "zoom-out must visibly shrink old raster BEFORE destination image updates");
    assert.ok(Math.abs(zoomOutPreview.scale-zoomOutPreview.expectedScale)<0.00001,
      "zoom-out must use intended visual zoom, not old tile-coverage clamp");
    assert.equal(zoomOutPreview.nativeZoom,zoomOutPreview.before.zoom,
      "native geographic zoom changes only after existing raster shrinks");
    assert.equal(zoomOutPreview.wheelCalls,1,
      "zoom-out preview must not commit while the wheel is still active");
    assert.equal(zoomOutPreview.boundaryScale,zoomOutPreview.scale);
    assert.equal(zoomOutPreview.floodScale,zoomOutPreview.scale);
    assert.equal(zoomOutPreview.footprintScale,zoomOutPreview.scale);
    assert.ok(Math.abs(zoomOutPreview.iconX-
      (zoomOutPreview.cursor.x+(zoomOutPreview.before.x-zoomOutPreview.cursor.x)*
        zoomOutPreview.scale))<2,
      "zoom-out must keep the source marker's rendered x-coordinate aligned");
    assert.ok(Math.abs(zoomOutPreview.iconY-
      (zoomOutPreview.cursor.y+(zoomOutPreview.before.y-zoomOutPreview.cursor.y)*
        zoomOutPreview.scale))<2,
      "zoom-out must keep the source marker's rendered y-coordinate aligned");
    assert.equal(zoomOutPreview.iconWidth,24);
    assert.equal(zoomOutPreview.iconHeight,24);
    await page.waitForTimeout(850);
    assert.equal(await page.evaluate(() => window.__wheelZoomCalls),2,
      "one additional geographic commit completes the outward gesture");
    assert.ok(await page.evaluate(() => map.getZoom())<zoomOutPreview.before.zoom);
    const commitDelay=await page.evaluate(
      ()=>window.__wheelLastCommitAt-window.__wheelOutStartAt);
    assert.ok(commitDelay>0 && commitDelay<550,
      "with external GSI tiles unavailable, native zoom must commit within "+
      "the short center-first deadline rather than waiting for 650ms atlas");
    assert.equal(await page.evaluate(() => map.getPane("tilePane").style.scale),"");
    const afterHalo = await page.evaluate(() => ({
      oldStillConnected:Boolean(window.__oldWheelHaloNode?.isConnected),
      nextHaloVisibility:zoomOutHalo?.node?.style.visibility || null,
      nextHaloIsOld:zoomOutHalo?.node===window.__oldWheelHaloNode
    }));
    assert.equal(afterHalo.oldStillConnected,false,
      "old geographic halo must be discarded before source coordinates change");
    assert.equal(afterHalo.nextHaloIsOld,false,
      "post-commit cache regeneration must not reuse stale source pixels");
    assert.ok(afterHalo.nextHaloVisibility===null ||
      afterHalo.nextHaloVisibility==="hidden",
      "freshly prepared next-gesture halo must remain invisible at rest");
    assert.equal(await page.evaluate(() =>
      window.__wheelGeometryProbe.getElement().style.translate),"");
    await page.evaluate(() => {
      map.removeLayer(window.__wheelGeometryProbe);
      delete window.__wheelGeometryProbe;
      document.getElementById("hinanex-wheel-geometry-probe-style").remove();
    });
    await page.evaluate(z => map.setZoom(z, {animate:false}), wheelPreview.before);
    await page.waitForTimeout(160);

    // Real-Leaflet regression for the reported user bug: switching OFF the
    // basemap, official flood raster or both must survive instant CSS preview,
    // final native zoom, async tile completion and the next halo warm-up.
    for (const [baseEnabled,floodEnabled] of [
      [false,true],[true,false],[false,false]
    ]) {
      const immediate = await page.evaluate(([showBase,showFlood]) => {
        const set=(id,checked)=>{
          const el=document.getElementById(id);
          el.checked=checked;
          el.dispatchEvent(new Event("change",{bubbles:true}));
        };
        set("basemap",showBase);
        set("officialFlood",showFlood);
        const rect=map.getContainer().getBoundingClientRect();
        map.getContainer().dispatchEvent(new WheelEvent("wheel",{
          bubbles:true,cancelable:true,
          clientX:rect.left+rect.width/2,
          clientY:rect.top+rect.height/2,
          deltaMode:0,deltaY:80
        }));
        return {
          checkedBase:document.getElementById("basemap").checked,
          checkedFlood:document.getElementById("officialFlood").checked,
          mapBase:map.hasLayer(baseMap),
          mapFlood:map.hasLayer(officialFloodLayer),
          previewSourceNames:(wheelPreview?.targets||[]).map(t=>
            t.layer===baseMap ? "basemap" :
            t.layer===officialFloodLayer ? "officialFlood" : "other"),
          basemapRetained:map.getPane("tilePane")
            .querySelectorAll(".hinanex-raster-retained").length,
          floodRetained:map.getPane("officialFloodPane")
            .querySelectorAll(".hinanex-raster-retained").length,
          destinationCover:document.querySelectorAll(".hinanex-target-tile-cover").length,
          halo:document.querySelectorAll(".hinanex-zoom-out-halo").length
        };
      },[baseEnabled,floodEnabled]);
      assert.equal(immediate.checkedBase,baseEnabled);
      assert.equal(immediate.checkedFlood,floodEnabled);
      assert.equal(immediate.mapBase,baseEnabled);
      assert.equal(immediate.mapFlood,floodEnabled);
      assert.equal(immediate.previewSourceNames.includes("basemap"),baseEnabled);
      assert.equal(immediate.previewSourceNames.includes("officialFlood"),floodEnabled);
      if (!baseEnabled) {
        assert.equal(immediate.basemapRetained,0,
          "disabled basemap must never be cloned during wheel preview");
        assert.equal(immediate.destinationCover,0,
          "separate GSI target atlas cannot bypass basemap OFF control");
        assert.equal(immediate.halo,0,
          "preloaded zoom-out halo must respect disabled basemap");
      }
      if (!floodEnabled) {
        assert.equal(immediate.floodRetained,0,
          "disabled official flood must never be cloned during wheel preview");
      }
      await page.waitForTimeout(900);
      const after=await page.evaluate(() => ({
        checkedBase:document.getElementById("basemap").checked,
        checkedFlood:document.getElementById("officialFlood").checked,
        mapBase:map.hasLayer(baseMap),
        mapFlood:map.hasLayer(officialFloodLayer),
        baseGhost:map.getPane("tilePane")
          .querySelectorAll(".hinanex-raster-retained").length,
        floodGhost:map.getPane("officialFloodPane")
          .querySelectorAll(".hinanex-raster-retained").length,
        targetCover:document.querySelectorAll(".hinanex-target-tile-cover").length,
        halo:document.querySelectorAll(".hinanex-zoom-out-halo").length
      }));
      assert.equal(after.checkedBase,baseEnabled);
      assert.equal(after.checkedFlood,floodEnabled);
      assert.equal(after.mapBase,baseEnabled);
      assert.equal(after.mapFlood,floodEnabled);
      if (!baseEnabled) {
        assert.equal(after.baseGhost,0);
        assert.equal(after.targetCover,0,
          "OFF state must persist through post-zoom async atlas loading");
        assert.equal(after.halo,0,
          "OFF state must persist through idle halo refresh");
      }
      if (!floodEnabled) assert.equal(after.floodGhost,0);
    }
    // The independent vector/point layer switches must survive the same
    // geographic zoom and clustering refresh; OFF never means hidden only
    // until the next zoom bucket is computed.
    await page.evaluate(() => {
      for (const id of ["boundary","shelter"]) {
        const el=document.getElementById(id);
        el.checked=false;
        el.dispatchEvent(new Event("change",{bubbles:true}));
      }
      const rect=map.getContainer().getBoundingClientRect();
      map.getContainer().dispatchEvent(new WheelEvent("wheel",{
        bubbles:true,cancelable:true,
        clientX:rect.left+rect.width/2,
        clientY:rect.top+rect.height/2,
        deltaMode:0,deltaY:-90
      }));
    });
    await page.waitForTimeout(950);
    const vectorState=await page.evaluate(() => ({
      boundaryChecked:document.getElementById("boundary").checked,
      shelterChecked:document.getElementById("shelter").checked,
      boundary:map.hasLayer(boundaryGroup),
      shelters:map.hasLayer(shelterGroup),
      viewportD:map.hasLayer(viewportDGroup)
    }));
    assert.equal(vectorState.boundaryChecked,false);
    assert.equal(vectorState.shelterChecked,false);
    assert.equal(vectorState.boundary,false,
      "OFF municipality boundary must not reappear after zoom update");
    assert.equal(vectorState.shelters,false,
      "OFF facility markers must not reappear after zoom bucket update");
    assert.equal(vectorState.viewportD,false,
      "OFF shelter choice must also hide the viewport D overlay");
    await page.evaluate(() => {
      for (const id of ["boundary","shelter"]) {
        const el=document.getElementById(id);
        el.checked=true;
        el.dispatchEvent(new Event("change",{bubbles:true}));
      }
    });

    // Restore user-visible controls for the broader GIS page journey.
    await page.evaluate(() => {
      for (const id of ["basemap","officialFlood"]) {
        const el=document.getElementById(id);
        el.checked=true;
        el.dispatchEvent(new Event("change",{bubbles:true}));
      }
    });
    await page.waitForTimeout(120);

    // Real Chromium shared-link journey: a new audience sees one prominent
    // entry button, no presenter menus, no GPS request or autoplay. The
    // verified skhb01 catalog may be unavailable in an isolated offline
    // environment; preserve its explicit, safe fail-closed fallback.
    const visitor=await context.newPage();
    const visitorErrors=[];
    visitor.on("pageerror",e=>visitorErrors.push(e.message));
    const visitorResponse=await visitor.goto(base+"/gis/gis/?demo=audience",
      {waitUntil:"domcontentloaded"});
    assert.equal(visitorResponse.status(),200);
    await visitor.waitForFunction(()=>!!window.HINANEX_GSI_FLOOD_PRESENTER);
    assert.equal(await visitor.locator("#mapAudienceIntro").isVisible(),true,
      "distribution URL must show the welcome card in a fresh session");
    assert.equal(await visitor.locator("#gsiFloodDemoPanel").isVisible(),false,
      "a shared URL never autoplays a scenario or requests GPS");
    assert.equal(await visitor.locator(".map-tour-other-demos").isVisible(),false,
      "other presenter choices cannot clutter the audience's demo path");
    await visitor.locator("#mapAudienceIntroStart").click();
    assert.equal(await visitor.locator("#mapAudienceIntro").isVisible(),false);
    assert.equal(await visitor.locator("#gsiFloodDemoPanel").isVisible(),true,
      "welcome CTA must launch MAIN GSI DEMO in one action");
    await visitor.waitForFunction(()=>{
      const content=document.getElementById("gsiFloodDemoContent");
      const fallback=document.getElementById("gsiFloodDemoFallback");
      return !content.hidden || !fallback.hidden;
    },null,{timeout:15000});
    let verifiedPinJourney=false;
    if(await visitor.locator("#gsiFloodDemoContent").isVisible()){
      await visitor.locator("#gsiFloodDemoNext").click(); // show verified GSI pins
      await visitor.locator("#gsiFloodDemoNext").click(); // user-selection stage
      assert.equal(await visitor.locator("#gsiFloodDemoPickHint").isVisible(),true);
      assert.equal(await visitor.locator("#gsiFloodDemoNext").isDisabled(),true);
      assert.equal((await visitor.locator("#gsiFloodDemoEvidence").isVisible()),false);
      const proof=await visitor.evaluate(()=>{
        const icon=document.querySelector(".reference-site-marker");
        if(!icon)return {found:false};
        // Exercise the exact verified-marker DOM event/Leaflet click path
        // without scripting the presenter proof (which would bypass trust).
        icon.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));
        return {found:true,
          selected:document.getElementById("gsiFloodDemoName").textContent,
          trace:document.getElementById("gsiFloodDemoTrace").textContent,
          promptHidden:document.getElementById("gsiFloodDemoPickHint").hidden};
      });
      assert.equal(proof.found,true,"ready official catalog must render a real GSI pin");
      assert.equal(proof.promptHidden,true);
      assert.ok(proof.selected.length>0 && proof.trace.length>0);
      assert.equal(await visitor.locator("#gsiFloodDemoEvidence").isVisible(),true);
      verifiedPinJourney=true;
    }else{
      assert.match(await visitor.locator("#gsiFloodDemoFallbackReason").innerText(),
        /未確認|確認できません/);
      assert.equal(await visitor.locator("#gsiFloodDemoFallbackD").isVisible(),false,
        "unavailable GSI must not redirect the visitor to a different demo");
    }
    assert.deepEqual(visitorErrors,[],"shared intro and presenter must not crash Chromium");
    await visitor.close();

    // Targeted CI profile: execute BOTH real-Chromium wheel directions and
    // exact marker pixel assertions, without conflating this gate with the
    // independent full UI/presenter smoke later in this file.
    if (process.env.HINANEX_WHEEL_ONLY === "1") {
      assert.deepEqual(errors, [], "no GIS page errors during real zoom gestures");
      fs.writeFileSync(path.join(out, "wheel_browser_audit.json"),
        JSON.stringify({
          status: "GIS_CHROMIUM_WHEEL_BOTH_DIRECTIONS_PASS",
          browser: "Playwright Chromium / real Leaflet 1.9.4",
          asserted: [
            "ZOOM_IN_CSS_PREVIEW_BEFORE_COMMIT",
            "ZOOM_OUT_CSS_PREVIEW_BEFORE_COMMIT",
            "BOUNDARIES_AND_FLOOD_TRACK_PREVIEW",
            "SOURCE_MARKER_RENDERED_PIXELS_TRACK_RASTER",
            "SOURCE_MARKER_ICON_SIZE_STABLE",
            "NATIVE_LEAFLET_FINAL_COMMIT_AND_CSS_CLEANUP",
            "OFFICIAL_GSI_BOUNDED_HALO_PROJECTED_IN_RASTER_PANE",
            "HALO_VISIBLE_ONLY_DURING_ZOOM_OUT_AND_DISCARDED_AT_COMMIT",
            "AUDIENCE_WELCOME_ONE_CLICK_MAIN_DEMO",
            "SINGLE_PUBLIC_DEMO_WITH_VERIFIED_GSI_PIN_CHOICE_OR_SAFE_FALLBACK"
          ],
          current_D_exports_contract_valid: report.all_local_contracts_valid,
          external_GSI_and_flood_raster_requests_blocked: true,
          full_GIS_UI_and_live_staging_verified: false,
          physical_Safari_trackpad_verified: false,
          actual_shelter_safety_approved: false,
          interactive_verified_GSI_pin_available_offline: verifiedPinJourney
        }, null, 2) + "\n", "utf8");
      process.stdout.write(
        "GIS_CHROMIUM_WHEEL_BOTH_DIRECTIONS_PASS: real DOM geometry, " +
        "not live GSI raster/physical device acceptance.\n");
      await context.close();
      return;
    }

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
    // Leaflet removes/replaces the previous point popup across transition
    // frames. Wait for the NEW boundary popup specifically, rather than
    // counting leftover rows from the previous source-point popup.
    const boundarySpeech = page.locator(".hinanex-place-popup.place-bubble--boundary");
    await boundarySpeech.waitFor({ state: "visible" });
    assert.equal(await boundarySpeech.locator(".place-card-summary .row").count(), 0,
      "boundary fixture must keep technical/source rows behind disclosure");
    assert.match(await boundarySpeech.innerText(), /自治体境界（参考）/);
    assert.equal(await boundarySpeech.locator(".place-card-disclosure").count(), 1);
    await boundarySpeech.locator(".leaflet-popup-close-button").click();
    await boundarySpeech.waitFor({ state: "hidden" });

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
    await page.evaluate(() => document.getElementById("mapTourStart").click());
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("1 / 3"));
    await page.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("元データの座標あり"));
    assert.match(await page.locator("#mapTourDescription").innerText(),
      /推奨施設ではありません/);
    await page.evaluate(() => document.getElementById("mapTourPause").click());
    assert.match(await page.locator("#mapTourProgress").innerText(), /一時停止/);
    await page.evaluate(() => document.getElementById("mapTourNext").click());
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("2 / 3"));
    await page.evaluate(() => document.getElementById("mapTourNext").click());
    await page.waitForFunction(() => document.querySelector("#mapTourProgress")
      ?.textContent?.includes("3 / 3"));
    await page.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("位置は推測しません"));
    assert.match(await page.locator("#mapTourSourceStatus").innerText(),
      /座標確認済み 0件/);
    await screenshot(page, "presenter-short-tour-unlocated-nagoya");
    await page.evaluate(() => document.getElementById("mapTourStop").click());
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
    await offlinePage.evaluate(() => document.getElementById("mapTourStart").click());
    await offlinePage.waitForFunction(() => document.querySelector("#mapTourSourceStatus")
      ?.textContent?.includes("取得・確認できませんでした"));
    assert.match(await offlinePage.locator("#mapTourSourceStatus").innerText(),
      /施設が存在しないという意味ではありません/);
    await screenshot(offlinePage, "missing-d-no-false-zero-tour");
    await offlinePage.evaluate(() => document.getElementById("mapTourStop").click());

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
