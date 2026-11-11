import { access, readFile } from "node:fs/promises";

const requiredFiles = [
  "index.html",
  "f02.html",
  "f02.css",
  "src/f02-page.js",
  "src/f02-shelter-reference.js",
  "scripts/check-f02-real-export.js",
  "historical-evidence-demo.html",
  "decision-lab.html",
  "decision-lab.css",
  "src/decision-lab.js",
  "src/decision-lab-model.js",
  "historical-evidence-demo.css",
  "src/historical-evidence-demo.js",
  "src/historical-evidence-model.js",
  "styles.css",
  "src/app.js",
  "src/region-export-view-model.js",
  "src/flood-scenario-view-model.js",
  "src/region-export-source.js",
  "src/region-export-loader.js",
  "src/display-labels.js",
  "src/presentation-view-model.js",
  "mock/region-export.json",
];

await Promise.all(requiredFiles.map((path) => access(new URL(`../${path}`, import.meta.url))));

const index = await readFile(new URL("../index.html", import.meta.url), "utf8");
const requiredMarkers = [
  'id="overviewRoot"',
  'href="./historical-evidence-demo.html"',
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
const f02 = await readFile(new URL("../f02.html", import.meta.url), "utf8");
for (const marker of [
  'id="search"', 'id="results"', 'id="detail"', 'id="sources"',
  'id="load-state"', 'id="record-count"', 'id="detail-title"',
  'src="./src/f02-page.js"', 'href="./f02.css"',
]) {
  if (!f02.includes(marker)) {
    throw new Error("f02.html required marker missing: " + marker);
  }
}

console.log("Static build check passed.");
