"use strict";

// Real Playwright Chromium user-flow smoke for E's reference-only source
// comparison. Sources are test-only INTERCEPTED synthetic fixtures: no A/C
// approval, no external GSI requests, no Render publication, no GPS collection.
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const rawUrl = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson";
const sha = "a".repeat(64);
const fixtureTag = "HINANEX_SYNTHETIC_CI_ONLY";
const names = [
  fixtureTag + " 原文テスト01",
  '<img src=x onerror="window.__comparisonInjected=true">',
  fixtureTag + " 原文テスト03"
];

function feature(index) {
  return {
    source_feature_key: rawUrl + "#feature_index=" + index,
    name_raw: names[index],
    address_raw: index === 1 ? null : fixtureTag + " 住所原文" + index,
    remarks_raw: index === 2 ? "合成の備考。" + "長文確認".repeat(45) : null,
    latitude: 35.7 + index * 0.001,
    longitude: 139.9 + index * 0.001,
    source_url: rawUrl,
    source_record_trace: "feature_index=" + index,
    source_raw_sha256: sha,
    disaster1_raw: 1,
    search_context_region_code: "13123",
    designation_kind: "designated_emergency_evacuation_site",
    hazard_dataset: "GSI_SKHB01_FLOOD"
  };
}
const features = Array.from({ length: 3 }, (_, i) => feature(i));
const fixture = {
  catalog_kind: "flood_designated_emergency_site_reference",
  region_code: "13123",
  hazard: "flood",
  status: "REFERENCE_ONLY",
  source_status: "C_ACCEPTED",
  https_provenance_status: "MATCH",
  https_provenance_checked_at_utc: "2026-10-09T03:00:00Z",
  total_source_records: features.length,
  source_raw_sha256: sha,
  c_audit_reference: "CI_SYNTHETIC_ONLY_NO_SOURCE_APPROVAL",
  sites: features
};

async function installSyntheticTileRoutes(page, mode) {
  await page.route("**/pipeline/data/output/gsi_verified_tiles/**", route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/13123/10-909-403.json") && mode !== "missing") {
      const data = mode === "unverified"
        ? { ...fixture, source_status: "PENDING" } : fixture;
      return route.fulfill({ status: 200, contentType: "application/json",
        body: JSON.stringify(data) });
    }
    return route.fulfill({ status: 404, body: "CI_ONLY_NO_ACCEPTED_TILE" });
  });
  await page.route("**/pipeline/data/output/edogawa_flood_site_catalog.json", route =>
    route.fulfill({ status: 404, body: "CI_ONLY_NO_LEGACY_TILE" }));
}

async function chooseOrigin(page, latitudeLongitude) {
  const menu = page.locator("#mapToolScenario");
  if (!(await menu.evaluate(node => node.open))) {
    await page.locator("#mapToolScenario > summary").click();
  }
  await page.locator("#coordinateSearchInput").fill(latitudeLongitude);
  await page.locator("#coordinateSearchButton").click();
  await page.waitForFunction(() => document.querySelector("#coordinateSearchStatus")
    ?.textContent?.includes("指定座標へ移動しました"));
}

async function runReferenceSiteCompareBrowser({ context, base, out, waitUntilLoaded }) {
  const results = [];
  for (const [width, height] of [[1365, 900], [390, 844]]) {
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewportSize({ width, height });
    await installSyntheticTileRoutes(page, "accepted");
    try {
      const response = await page.goto(base + "/gis/gis/?region=13123",
        { waitUntil: "domcontentloaded" });
      assert.equal(response.status(), 200);
      await waitUntilLoaded(page, "13123");
      // A correctly wired compare script may be ready before any data arrives.
      assert.equal(await page.locator("#referenceCompareOpen").isVisible(), false);
      await chooseOrigin(page, "35.70, 139.90");
      await page.waitForFunction(() => {
        const button = document.querySelector("#referenceCompareOpen");
        return button && !button.hidden && !button.disabled;
      }, null, { timeout: 20000 });
      assert.equal(await page.locator(".reference-site-marker").count(), 3);
      assert.equal(await page.locator("#referenceCompareOpen").isVisible(), true);
      // User must explicitly open the comparison; never steal map pixels.
      assert.equal(await page.locator("#referenceComparePanel").isVisible(), false);
      await page.locator("#referenceCompareOpen").click();
      assert.equal(await page.locator("#referenceComparePanel").isVisible(), true);
      assert.equal(await page.locator(".reference-compare-choice").count(), 3);
      assert.match(await page.locator("#referenceCompareStatus").innerText(),
        /検証済み 1\/9タイル/);
      await page.locator(".reference-compare-choice").nth(0).click();
      await page.locator(".reference-compare-choice").nth(1).click();
      assert.equal(await page.locator(".reference-compare-site").count(), 2);
      assert.equal(await page.locator(".reference-compare-choice").nth(2).isDisabled(), true);
      const text = await page.locator("#referenceCompareResult").innerText();
      assert.match(text, /直線距離/);
      assert.match(text, /経路ではありません/);
      assert.match(text, /元データで未確認/);
      assert.match(text, /feature_index=0/);
      assert.match(text, /feature_index=1/);
      assert.match(text, /<img src=x onerror/);
      assert.equal(await page.locator("#referenceCompareResult img").count(), 0,
        "official source text must be rendered as text, not executable markup");
      assert.equal(await page.evaluate(() => window.__comparisonInjected === true), false);
      const link = page.locator(".reference-compare-site a").first();
      assert.equal(await link.getAttribute("href"), rawUrl);
      assert.match(await link.getAttribute("rel"), /noopener noreferrer/);
      const geometry = await page.locator("#referenceComparePanel").evaluate(panel => {
        const rect = panel.getBoundingClientRect();
        const mapRect = document.querySelector("#map").getBoundingClientRect();
        const columns = panel.querySelector(".reference-compare-columns");
        const css = getComputedStyle(columns);
        return {
          left: rect.left, right: rect.right, height: rect.height,
          mapHeight: mapRect.height,
          columns: css.gridTemplateColumns.split(" ").length,
          scrollable: panel.scrollHeight > panel.clientHeight,
          closeHeight: panel.querySelector("#referenceCompareClose")
            .getBoundingClientRect().height
        };
      });
      assert.ok(geometry.left >= -1 && geometry.right <= width + 1,
        "comparison must fit the desktop/mobile viewport");
      assert.ok(geometry.closeHeight >= 44);
      if (width <= 680) {
        assert.ok(geometry.height <= geometry.mapHeight * .54 + 3,
          "mobile comparison must not cover most of the map");
        assert.equal(geometry.columns, 1, "mobile comparison must stack sites vertically");
      } else {
        assert.ok(geometry.columns >= 2, "desktop comparison must use two columns");
      }
      // Replace one selected site; the third must become available again.
      await page.locator(".reference-compare-choice").nth(1).click();
      assert.equal(await page.locator(".reference-compare-site").count(), 0);
      await page.locator(".reference-compare-choice").nth(2).click();
      assert.equal(await page.locator(".reference-compare-site").count(), 2);
      assert.match(await page.locator("#referenceCompareResult").innerText(),
        new RegExp(fixtureTag + " 住所原文0"));
      assert.match(await page.locator("#referenceCompareResult").innerText(), /長文確認/);
      // The dialog should close without resetting a user's explicit choices.
      await page.locator("#referenceCompareClose").click();
      assert.equal(await page.locator("#referenceComparePanel").isVisible(), false);
      await page.locator("#referenceCompareOpen").click();
      assert.equal(await page.locator(".reference-compare-site").count(), 2);
      const screenshotName = "gsi-comparison-ci-fixture-" + width + ".png";
      await page.screenshot({ path: path.join(out, screenshotName), animations: "disabled" });
      await page.locator("#referenceCompareClose").click();
      // A new origin outside the verified tile must discard prior selections.
      await chooseOrigin(page, "35.70, 140.10");
      await page.waitForFunction(() => document.querySelector("#floodDiscoveryResults")
        ?.textContent?.includes("未配信"));
      assert.equal(await page.locator("#referenceCompareOpen").isVisible(), false);
      assert.equal(await page.locator("#referenceComparePanel").isVisible(), false);
      assert.equal(await page.locator(".reference-site-marker").count(), 0);
      assert.deepEqual(errors, [], "real page JavaScript errors");
      results.push({ viewport: width, height, selectedTwo: true,
        discardedAfterUnknownSource: true, screenshot: screenshotName,
        usedActualOfficialSiteData: false });
    } finally {
      await page.close();
    }
  }

  // Negative: a forged C status and a missing source must NEVER unlock UI.
  for (const mode of ["missing", "unverified"]) {
    const page = await context.newPage();
    await installSyntheticTileRoutes(page, mode);
    try {
      await page.goto(base + "/gis/gis/?region=13123", { waitUntil: "domcontentloaded" });
      await waitUntilLoaded(page, "13123");
      await chooseOrigin(page, "35.70, 139.90");
      await page.waitForFunction(() => document.querySelector("#floodDiscoveryResults")
        ?.textContent?.includes("未検証"));
      assert.equal(await page.locator("#referenceCompareOpen").isVisible(), false);
      assert.equal(await page.locator(".reference-site-marker").count(), 0);
      results.push({ negativeFixture: mode, failClosed: true });
    } finally {
      await page.close();
    }
  }
  assert.equal(results.length, 4);
  fs.writeFileSync(path.join(out, "reference_site_compare_browser_audit.json"), JSON.stringify({
    status: "E_GSI_REFERENCE_COMPARISON_CHROMIUM_FIXTURE_PASS",
    checks: results,
    browser: "real Chromium / real Leaflet; C-accepted SHAPE mocked by CI route only",
    synthetic_fixture_only: true,
    live_GSI_or_municipality_source_approved_by_this_test: false,
    actual_iPhone_Safari_tested: false,
    actual_Render_deployment_tested: false,
    verified_GSI_tile_service_reachability_tested: false,
    actual_route_or_shelter_safety_tested: false
  }, null, 2) + "\n", "utf8");
  return results;
}
module.exports = { runReferenceSiteCompareBrowser };
