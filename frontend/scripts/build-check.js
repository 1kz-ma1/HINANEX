import { access, readFile } from "node:fs/promises";

const requiredFiles = [
  "index.html",
  "styles.css",
  "src/app.js",
  "src/region-export-loader.js",
  "src/region-export-view-model.js",
  "src/region-export-source.js",
  "src/region-export-loader.js",
  "mock/region-export.json",
];

await Promise.all(requiredFiles.map((path) => access(new URL(`../${path}`, import.meta.url))));

const index = await readFile(new URL("../index.html", import.meta.url), "utf8");
const requiredMarkers = [
  'id="overviewRoot"',
  'id="capabilityRoot"',
  'id="assessmentRoot"',
  'id="gapRoot"',
  'id="recommendationRoot"',
  'id="evidenceRoot"',
  'id="regionSelect"',
  'id="reloadRegionExport"',
  'id="regionExportFile"',
  'id="loadDemoData"',
  'id="sourceStatus"',
  'src="./src/app.js"',
  'href="./styles.css"',
];

for (const marker of requiredMarkers) {
  if (!index.includes(marker)) {
    throw new Error(`index.htmlに必要な参照がありません: ${marker}`);
  }
}

JSON.parse(await readFile(new URL("../mock/region-export.json", import.meta.url), "utf8"));
console.log("Static build check passed.");
