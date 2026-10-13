/**
 * Browser acceptance smoke for B source-only evidence UI.
 * Real Chromium, run from repository root HTTP server.
 * Must be passed an ACTUAL C-generated public case JSON via argument.
 *
 * Usage: node frontend/scripts/evidence-case-browser-smoke.mjs \
 *   <actual-C-public-evidence.json> <screenshot-output-dir>
 *
 * Playwright is an OPTIONAL CI-only dependency; not bundled in public frontend.
 * Screenshots contain only pinned PUBLIC source text (no private reply content).
 */
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const expectedUrl = "http://127.0.0.1:8765/frontend/evidence-case.html";
const sourceFile = process.argv[2];
const screenshotDir = process.argv[3];
if (!sourceFile || !screenshotDir || process.argv.length !== 4) {
  throw new Error("Usage: browser smoke <C-public-json> <screenshots-dir>");
}
const publicOriginal = await readFile(sourceFile, "utf8");
const actualC = JSON.parse(publicOriginal);
if (
  actualC.consumer_contract !== "C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1"
  || actualC.presentation_only !== true
  || actualC.may_be_used_as_live_shelter_recommendation !== false
  || actualC.human_C_site_pairs_approved !== 0
  || actualC.new_flood_candidate_or_excluded !== 0
) {
  throw new Error("Actual public C case is not an unapproved educational-only fixture");
}

await mkdir(screenshotDir, { recursive: true });
const outputs = [];
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });

async function assert(condition, description) {
  if (!condition) throw new Error(description);
}
async function visible(node) {
  return node.isVisible();
}

try {
  for (const viewport of [
    { name: "desktop", width: 1365, height: 900 },
    { name: "mobile", width: 390, height: 844 },
  ]) {
    const page = await browser.newPage({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
      reducedMotion: "reduce",
      locale: "ja-JP",
    });
    const failures = [];
    page.on("pageerror", (error) => failures.push(error.message));

    const response = await page.goto(expectedUrl, { waitUntil: "networkidle" });
    await assert(response?.status() === 200, viewport.name + " UI HTTP failed");
    await page.waitForFunction(
      () => document.querySelector("#caseSourceStatus")?.dataset.kind === "preview"
    );
    await assert(await visible(page.locator("#caseContent")), "Default preview did not render");
    await assert(
      await page.locator("#caseStages > li").count() === 3,
      "Default preview does not have exactly 3 states"
    );
    await assert(
      (await page.locator("#caseSourceStatus").textContent()).includes("画面確認用サンプル"),
      "B authored preview is not visibly labelled"
    );
    await assert(
      (await page.locator(".case-unknown").textContent()).includes("UNKNOWN"),
      "Current status UNKNOWN must be visibly distinct"
    );

    // Keyboard focusability of the file picker button; avoid hidden-label trap.
    await page.locator("#chooseCaseFile").focus();
    await assert(
      await page.evaluate(() => document.activeElement?.id === "chooseCaseFile"),
      "File selector is not keyboard focusable"
    );

    // Read actual C-produced public JSON using the same control as the user.
    await page.locator("#caseFile").setInputFiles({
      name: "C_public_evidence.json",
      mimeType: "application/json",
      buffer: Buffer.from(publicOriginal, "utf8"),
    });
    await page.waitForFunction(
      () => document.querySelector("#caseSourceStatus")?.dataset.kind === "file"
    );
    await assert(await visible(page.locator("#caseContent")), "Actual C JSON not rendered");
    await assert(await page.locator("#caseStages > li").count() === 3,
      "Real C export did not render exact 3 stages");
    await assert(await page.locator("#caseSources > li").count() === 4,
      "Real C export did not render exact 4 source links");
    await assert(await page.locator("#caseError").isHidden(),
      "Real C export triggered contract error");
    await assert(
      await page.locator(".case-unknown").innerText() === "現況 UNKNOWN",
      "C source accidentally promoted live site status"
    );
    const unsafeAnchors = await page.locator("#caseContent a[href]").evaluateAll((nodes) =>
      nodes.filter((node) =>
        !node.href.startsWith("https://www.city.edogawa.tokyo.jp/")
        && !node.href.startsWith("https://www.gikai.city.edogawa.tokyo.jp/")
      ).map((n) => n.href)
    );
    await assert(unsafeAnchors.length === 0, "Displayed unsafe / non-official source URLs");
    const safeLinkCount = await page.locator("#caseContent a[href]").count();
    await assert(safeLinkCount >= 4, "Expected official source links missing");
    const currentClaim = await page.locator("#caseContent").innerText();
    await assert(
      !currentClaim.includes("現在利用可能") && !currentClaim.includes("避難できます"),
      "Case output has an unsupported safe-shelter claim"
    );
    const pageSize = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }));
    await assert(
      pageSize.scroll <= pageSize.client + 1,
      viewport.name + ": horizontal overflow " + JSON.stringify(pageSize)
    );

    const imagePath = resolve(screenshotDir, "evidence-case-" + viewport.name + ".png");
    await page.screenshot({ path: imagePath, fullPage: true, animations: "disabled" });
    outputs.push({
      viewport, result: "actual_C_public_json_rendered",
      stages: 3, official_public_sources: 4,
      horizontal_overflow: false,
      screenshot: "evidence-case-" + viewport.name + ".png",
    });

    // Replace valid C with forged current opening and private content.
    const forged = structuredClone(actualC);
    forged.demo_states[2].current_operational_status = "OPEN";
    forged.claimed_municipal_reply = "PRIVATE_SECRET_NOT_FOR_BROWSER";
    await page.locator("#caseFile").setInputFiles({
      name: "forged-municipal-case.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(forged), "utf8"),
    });
    await page.waitForFunction(
      () => document.querySelector("#caseSourceStatus")?.dataset.kind === "error"
    );
    await assert(await page.locator("#caseContent").isHidden(),
      "Stale accepted source data remains after invalid JSON");
    await assert(await visible(page.locator("#caseError")),
      "Unsafe source contract not visibly rejected");
    await assert(
      !(await page.locator("body").innerText()).includes("PRIVATE_SECRET_NOT_FOR_BROWSER"),
      "Forged private content leaked into DOM"
    );
    const failureScreenshot = resolve(
      screenshotDir, "evidence-case-invalid-" + viewport.name + ".png"
    );
    await page.screenshot({
      path: failureScreenshot, fullPage: true, animations: "disabled",
    });

    // Recover only via explicit user action; never silently fallback to preview.
    await page.locator("#loadCasePreview").click();
    await page.waitForFunction(
      () => document.querySelector("#caseSourceStatus")?.dataset.kind === "preview"
    );
    await assert(await visible(page.locator("#caseContent")), "Explicit preview reset failed");
    await assert(failures.length === 0,
      viewport.name + ": browser JS error(s): " + failures.join("; "));
    await page.close();
  }
  const manifest = {
    status: "B_BROWSER_SMOKE_PASSED_EDUCATIONAL_ONLY",
    actual_C_generated_fixture: true,
    official_bytes_reverified_during_browser_run: false,
    live_current_opening_validated: false,
    no_hazard_suitability_evaluation: true,
    responsive_viewports: outputs,
  };
  await writeFile(
    resolve(screenshotDir, "browser_smoke_manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n", "utf8"
  );
  process.stdout.write(
    "Real Chromium C->B evidence UI smoke PASS desktop/mobile; 3 stages; 4 official sources; "
    + "invalid contract hides previous view; no GIS/shelter claims.\n"
  );
} finally {
  await browser.close();
}
