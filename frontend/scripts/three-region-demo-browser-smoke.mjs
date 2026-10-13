/**
 * B-owned browser acceptance on the exact, temporary Render-equivalent distribution.
 * Usage: node frontend/scripts/three-region-demo-browser-smoke.mjs
 *   <temporary-static-root> <public-only-audit-dir>
 *
 * Requires test-only Playwright Chromium installed by a shared CI workflow.
 * No live staging URL, external hazard tile, or current shelter suitability checks.
 */
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const [distArg, auditArg] = process.argv.slice(2);
if (!distArg || !auditArg || process.argv.length !== 4) {
  throw new Error("Usage: <Render-equivalent-static-root> <public-audit-dir>");
}
const distRoot = resolve(distArg);
const auditRoot = resolve(auditArg);
const baseUrl = "http://127.0.0.1:8765";
const regions = [
  { code: "13123", filename: "edogawa.json" },
  { code: "15100", filename: "niigata.json" },
  { code: "23100", filename: "nagoya.json" },
];
const payloads = new Map();

for (const region of regions) {
  const path = resolve(distRoot, "pipeline/data/output", region.filename);
  const payload = JSON.parse(await readFile(path, "utf8"));
  if (payload.region?.code !== region.code) {
    throw new Error("D regional export code mismatch: " + region.filename);
  }
  const scenario = payload.scenarios?.filter((v) =>
    v.scenario_id === "flood_shelter_selection"
  );
  if (
    scenario?.length !== 1
    || scenario[0].status !== "UNKNOWN"
    || !Array.isArray(scenario[0].facility_results)
    || scenario[0].facility_results.some((r) => r.status !== "UNKNOWN")
  ) {
    throw new Error("D flood statuses changed; require independent C/D review: " + region.code);
  }
  payloads.set(region.code, payload);
}

await mkdir(auditRoot, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const checks = [];
const errors = [];
function assert(value, message) {
  if (!value) throw new Error(message);
}

try {
  const page = await browser.newPage({
    viewport: { width: 1365, height: 900 },
    locale: "ja-JP",
    reducedMotion: "reduce",
  });
  page.setDefaultTimeout(20000);
  page.on("pageerror", (error) => errors.push(error.message));

  const response = await page.goto(baseUrl + "/frontend/", { waitUntil: "domcontentloaded" });
  assert(response?.status() === 200, "B homepage HTTP request failed");

  for (const region of regions) {
    if (region.code !== "13123") {
      await page.locator('[data-region-code="' + region.code + '"]').click();
    }
    await page.waitForFunction((code) => {
      const status = document.querySelector("#sourceStatus");
      const selected = document.querySelector("#regionSelect");
      const overview = document.querySelector("#overviewRoot");
      return status?.dataset.tone === "success"
        && selected?.value === code
        && overview?.textContent?.includes(code);
    }, region.code);

    const active = await page.locator('.region-button[aria-pressed="true"]')
      .evaluateAll((items) => items.map((item) => item.dataset.regionCode));
    assert(active.length === 1 && active[0] === region.code,
      "Wrong selected region button: " + region.code);
    assert(await page.locator("#demoNotice").isHidden(),
      "Synthetic demo banner appeared during actual D data display");
    assert(await page.locator("#mapBackLink").getAttribute("href")
      === "/gis/gis/?region=" + region.code,
    "B to E region link mismatch: " + region.code);
    assert(await page.locator("#floodScenario").isVisible(),
      "Actual D flood UNKNOWN panel absent: " + region.code);
    const flood = await page.locator("#floodScenarioRoot").innerText();
    assert(flood.includes("UNKNOWN") && flood.includes("安全・開設を保証する情報ではありません"),
      "D UNKNOWN/disclaimer not visible: " + region.code);
    assert(await page.locator("#summaryRoot").innerText() !== "",
      "B regional summary empty: " + region.code);
    const size = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }));
    assert(size.scroll <= size.client + 1,
      "Horizontal overflow for region " + region.code);

    // Verify only HTTP routing to E; E GIS functional acceptance is independent.
    const gisResponse = await page.request.get(baseUrl + "/gis/gis/?region=" + region.code);
    assert(gisResponse.status() === 200 && (await gisResponse.text()).includes("<html"),
      "E GIS route unavailable: " + region.code);

    const file = "region-" + region.code + "-desktop.png";
    await page.screenshot({
      path: resolve(auditRoot, file),
      fullPage: false,
      animations: "disabled",
    });
    checks.push({
      region_code: region.code,
      d_region_json_loaded: true,
      d_flood_status: "UNKNOWN",
      d_facility_statuses_all_unknown: true,
      b_region_switch_and_summary: "PASS",
      b_gis_region_link_and_http_route: "PASS_ROUTE_ONLY",
      viewport: "1365x900",
      screenshot: file,
    });
  }

  // A mismatched D response must clear previous region content, never silently
  // show the prior municipality or synthetic data under another code.
  const routePattern = "**/pipeline/data/output/niigata.json";
  await page.route(routePattern, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(payloads.get("13123")),
  }));
  await page.locator('[data-region-code="15100"]').click();
  await page.waitForFunction(() => document.querySelector("#sourceStatus")?.dataset.tone === "error");
  assert(await page.locator("#summaryRoot .error-card").isVisible(),
    "Mismatched region did not fail visibly");
  assert((await page.locator("#overviewRoot").innerText()).trim() === "",
    "Stale previous region remains visible after mismatched D data");
  assert(await page.locator("#demoNotice").isHidden(),
    "Mismatched D response silently fell back to synthetic data");
  await page.unroute(routePattern);
  await page.locator('[data-region-code="15100"]').click();
  await page.waitForFunction(() => document.querySelector("#sourceStatus")?.dataset.tone === "success");
  assert((await page.locator("#overviewRoot").innerText()).includes("15100"),
    "B view did not recover from rejected D response");
  assert(errors.length === 0, "B JavaScript page errors: " + errors.join("; "));

  const manifest = {
    status: "B_THREE_REGION_ACTUAL_BUNDLE_BROWSER_PASS",
    test_only_local_render_equivalent_distribution: true,
    live_render_staging_deployed: false,
    real_device_safari_voiceover_tested: false,
    c_human_approval: false,
    e_gis_behavior_certified: false,
    unsupported_region_payload_fail_closed: true,
    controls_restored_after_invalid_payload: true,
    checks,
  };
  await writeFile(resolve(auditRoot, "three_region_browser_manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n", "utf8");
  process.stdout.write("B real D bundle Chromium regions PASS; GIS routes only; " +
    "mismatched D JSON clears stale region and recovery PASS. No live safety approval.\n");
  await page.close();
} finally {
  await browser.close();
}
