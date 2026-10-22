import { access, readFile } from "node:fs/promises";

const requiredFiles = [
  "index.html",
  "team-review.html",
  "mock/team-review-example.json",
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
  'href="./team-review.html"',
];

for (const marker of requiredMarkers) {
  if (!index.includes(marker)) {
    throw new Error(`index.htmlに必要な参照がありません: ${marker}`);
  }
}

JSON.parse(await readFile(new URL("../mock/region-export.json", import.meta.url), "utf8"));
const review = await readFile(new URL("../team-review.html", import.meta.url), "utf8");
if (!review.includes("hinanex.team-review.v1") || review.includes('<script src=')) {
  throw new Error("Offline review HTML must be standalone with explicit versioned JSON");
}
const mockReview = JSON.parse(await readFile(new URL("../mock/team-review-example.json", import.meta.url), "utf8"));
if (mockReview.schema_id !== "hinanex.team-review.v1" || mockReview.safety.approved_for_map !== false) {
  throw new Error("Team review fixture may not approve facility positions");
}
console.log("Static build check passed.");
