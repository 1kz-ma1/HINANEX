import { access, readFile } from "node:fs/promises";

const requiredFiles = [
  "index.html",
  "styles.css",
  "src/app.js",
  "src/region-export-view-model.js",
  "src/flood-scenario-view-model.js",
  "src/region-export-source.js",
  "src/region-export-loader.js",
  "src/display-labels.js",
  "src/presentation-view-model.js",
  "mock/region-export.json",
  "evidence-case.html",
  "evidence-case.css",
  "src/evidence-case-view-model.js",
  "src/evidence-case-page.js",
  "scripts/check-c-evidence-case.js",
  "mock/shimokamata-evidence-ui-preview.json",
];

await Promise.all(requiredFiles.map((path) => access(new URL(`../${path}`, import.meta.url))));

const index = await readFile(new URL("../index.html", import.meta.url), "utf8");
const requiredMarkers = [
  'id="overviewRoot"',
  'id="summaryRoot"',
  'id="capabilityRoot"',
  'id="floodScenarioRoot"',
  'id="floodScenarioNav"',
  'id="assessmentRoot"',
  'id="gapRoot"',
  'id="recommendationRoot"',
  'id="evidenceRoot"',
  'id="regionSelect"',
  'id="reloadRegionExport"',
  'id="regionExportFile"',
  'id="loadDemoData"',
  'id="sourceStatus"',
  'id="developerSettings"',
  'data-region-code="13123"',
  'data-region-code="15100"',
  'data-region-code="23100"',
  'src="./src/app.js"',
  'href="./styles.css"',
];

for (const marker of requiredMarkers) {
  if (!index.includes(marker)) {
    throw new Error(`index.htmlに必要な参照がありません: ${marker}`);
  }
}

JSON.parse(await readFile(new URL("../mock/region-export.json", import.meta.url), "utf8"));
const evidencePage = await readFile(new URL("../evidence-case.html", import.meta.url), "utf8");
for (const marker of [
  'id="caseFile"', 'id="caseStages"', 'id="caseSources"',
  'id="caseError"', 'id="caseContent"', 'id="caseAddresses"',
  'src="./src/evidence-case-page.js"', 'href="./evidence-case.css"',
]) {
  if (!evidencePage.includes(marker)) {
    throw new Error("教育・根拠事例ページの必須DOMがありません: " + marker);
  }
}
if (!index.includes('href="./evidence-case.html"')) {
  throw new Error("地域分析から教育用根拠事例へのリンクがありません");
}
JSON.parse(await readFile(new URL("../mock/shimokamata-evidence-ui-preview.json", import.meta.url), "utf8"));

console.log("Static build check passed.");
