/**
 * Cross-engine educational case accessibility acceptance (B only).
 *
 * Run on a GitHub-hosted Ubuntu runner with Playwright Chromium + WebKit and
 * @axe-core/playwright installed as TEST-ONLY packages (not shipped to users).
 *
 * Usage: node frontend/scripts/evidence-case-webkit-a11y-smoke.mjs \
 *  <ACTUAL_C_PUBLIC_JSON> <PUBLIC_SCREENSHOT_DIRECTORY>
 *
 * This tests Linux Playwright WebKit and Chromium engines; WebKit here is NOT
 * native iOS Safari, VoiceOver, or a Render deployed staging integration.
 * Never feed this page into live shelter routing or an availability API.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium, webkit } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import { parseEvidenceCase } from "../src/evidence-case-view-model.js";

const [sourcePath, targetFolder] = process.argv.slice(2);
if (!sourcePath || !targetFolder || process.argv.length !== 4) {
  throw new Error("Usage: <C-public-json> <public-screenshot-dir>");
}
const raw = await readFile(sourcePath, "utf8");
if (raw.length > 256 * 1024) throw new Error("C public case exceeds size limit");
const original = JSON.parse(raw);
const fixed = parseEvidenceCase(original);
if (fixed.currentOpening !== "UNKNOWN" || fixed.isOperational
  || fixed.stages.length !== 3 || fixed.sources.length !== 4) {
  throw new Error("Only source-cited, unapproved, educational C data is accepted");
}

await mkdir(targetFolder, { recursive: true });
const results = [];
const browserEngines = [
  { name: "webkit", launch: webkit },
  { name: "chromium", launch: chromium },
];
const viewports = [
  { name: "desktop", width: 1365, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];
const assertions = (value, message) => {
  if (!value) throw new Error(message);
};

for (const engine of browserEngines) {
  const browser = await engine.launch.launch({ headless: true });
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        locale: "ja-JP",
        reducedMotion: "reduce",
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();
      const browserExceptions = [];
      page.on("pageerror", (err) => browserExceptions.push(err.message));

      const response = await page.goto(
        "http://127.0.0.1:8765/frontend/evidence-case.html",
        { waitUntil: "networkidle" }
      );
      assertions(response?.status() === 200, engine.name + ": UI not HTTP 200");
      await page.waitForFunction(() =>
        document.querySelector("#caseSourceStatus")?.dataset.kind === "preview"
      );

      // Real engine and a separate C-generated JSON, not B's authored mock.
      await page.locator("#caseFile").setInputFiles({
        name: "C_official_source_case.json",
        mimeType: "application/json",
        buffer: Buffer.from(raw, "utf8"),
      });
      await page.waitForFunction(() =>
        document.querySelector("#caseSourceStatus")?.dataset.kind === "file"
      );
      assertions(await page.locator("#caseContent").isVisible(),
        engine.name + ": real C output not visible");
      assertions(await page.locator("#caseStages > li").count() === 3,
        "Expected exactly three evidence stages");
      assertions(await page.locator("#caseSources > li").count() === 4,
        "Expected exactly four source originals");
      assertions(
        (await page.locator(".case-unknown").textContent()).includes("UNKNOWN"),
        "Never show a live shelter decision"
      );

      // Programmatic keyboard focus then actual Tab must reach next visible
      // action, not the offscreen native file input.
      const picker = page.locator("#chooseCaseFile");
      await picker.focus();
      assertions(await page.evaluate(() =>
        document.activeElement?.id === "chooseCaseFile"), "Picker focus failed");
      await page.keyboard.press("Tab");
      const focusedNext = await page.evaluate(() => document.activeElement?.id);
      assertions(focusedNext === "loadCasePreview",
        engine.name + ": hidden input trapped the Tab order: " + focusedNext);
      await picker.focus();
      const focusStyle = await picker.evaluate((node) => {
        const s = getComputedStyle(node);
        return { style: s.outlineStyle, width: s.outlineWidth };
      });
      // Full styling must be visible to keyboard users, not outline:none.
      assertions(focusStyle.style !== "none" && focusStyle.width !== "0px",
        engine.name + ": no visible picker focus indicator");

      const dims = await page.evaluate(() => ({
        screen: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
        all: [...document.querySelectorAll("main section")].every(
          (el) => el.getBoundingClientRect().width > 0
        ),
      }));
      assertions(dims.content <= dims.screen + 1,
        engine.name + "/" + viewport.name + " horizontal overflow: " + JSON.stringify(dims));
      assertions(dims.all, "A main section is collapsed");

      // Only public content is visible. Axe runs on actual rendered UI:
      // headings, landmark structure, controls, links, color contrast.
      const axeResult = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const violations = axeResult.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        target: v.nodes.map((node) => node.target.join(" ")).slice(0, 5),
        description: v.help,
      }));

      const normalShot = "evidence-a11y-" + engine.name + "-" + viewport.name + ".png";
      await page.screenshot({
        path: resolve(targetFolder, normalShot),
        fullPage: true,
        animations: "disabled",
      });
      results.push({
        engine: engine.name,
        viewport,
        source_type: "actual_C_educational_JSON_no_private_replies",
        official_source_refs: 4,
        educational_stages: 3,
        current_site_opening: "UNKNOWN",
        compliant_tags_checked: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
        accessibility_violations: violations,
        keyboard_tab_order: ["chooseCaseFile", "loadCasePreview"],
        focus_visible: true,
        horizontal_overflow: false,
        screenshot: normalShot,
      });

      // Check error announcement role and hard failure on forged opening.
      const forged = structuredClone(original);
      forged.demo_states[2].current_operational_status = "OPEN";
      forged.personal_reply = "PRIVATE_DO_NOT_LEAK_2026";
      await page.locator("#caseFile").setInputFiles({
        name: "fake-open.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(forged)),
      });
      await page.waitForFunction(() =>
        document.querySelector("#caseSourceStatus")?.dataset.kind === "error"
      );
      assertions(await page.locator("#caseContent").isHidden(),
        engine.name + ": previous valid result remains after invalid source");
      assertions(await page.getByRole("alert").isVisible(),
        engine.name + ": accessible alert not visible");
      const visibleBody = await page.locator("body").innerText();
      assertions(!visibleBody.includes("PRIVATE_DO_NOT_LEAK_2026"),
        "Private metadata leaked in accessibility/visual output");

      assertions(browserExceptions.length === 0,
        engine.name + ": browser JS errors: " + browserExceptions.join("; "));
      await context.close();

      if (violations.length) {
        throw new Error(
          "axe WCAG violations in " + engine.name + "/" + viewport.name + ": "
          + JSON.stringify(violations)
        );
      }
    }
  } finally {
    await browser.close();
  }
}

const manifest = {
  status: "B_WEBKIT_AND_CHROMIUM_ACCESSIBILITY_CI_PASS_EDUCATIONAL_ONLY",
  browser_webkit_platform: "Playwright WebKit on Ubuntu, not native iOS Safari",
  assistive_technology_screen_reader_manually_tested: false,
  axe_wcag_automated_audit_not_full_manual_conformance: true,
  actual_C_generated_public_source_case: true,
  official_original_bytes_redownloaded_in_this_test: false,
  hazard_suitability_or_live_opening_verification: false,
  results,
};
await writeFile(
  resolve(targetFolder, "webkit_a11y_manifest.json"),
  JSON.stringify(manifest, null, 2) + "\n"
);
process.stdout.write(
  "WebKit + Chromium educational case PASS: 1365/390px, "
  + "keyboard order, no horizontal overflow, axe WCAG A/AA zero findings, "
  + "real C public JSON, invalid opening rejected.\n"
);
