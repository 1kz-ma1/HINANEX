/**
 * B read-only check of a real Render-equivalent predeploy output bundle.
 * Invocation: node frontend/scripts/check-render-evidence-bundle.mjs
 *   <temporary-deploy-dist> <C-public-educational-json>
 * Does not publish, mutate D output, or change main/Render.
 */
import { readFile, stat } from "node:fs/promises";
import { resolve, sep } from "node:path";
import { parseEvidenceCase } from "../src/evidence-case-view-model.js";

const [bundleArgument, cCaseFile] = process.argv.slice(2);
if (!bundleArgument || !cCaseFile || process.argv.length !== 4) {
  throw new Error("Usage: <Render-equivalent-output-root> <C-public-evidence-json>");
}
const root = resolve(bundleArgument);
const item = (part) => resolve(root, part);
async function required(path) {
  const file = item(path);
  if (!file.startsWith(root + sep)) throw new Error("Invalid static path: " + path);
  try {
    if (!(await stat(file)).isFile()) {
      throw new Error("Missing public staging file: " + path);
    }
    return await readFile(file, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT" || error?.code === "ENOTDIR") {
      throw new Error("Missing public staging file: " + path);
    }
    throw error;
  }
}
function check(ok, error) {
  if (!ok) throw new Error(error);
}
const cCase = JSON.parse(await readFile(cCaseFile, "utf8"));
const view = parseEvidenceCase(cCase);
check(view.currentOpening === "UNKNOWN" && !view.isOperational
  && view.sources.length === 4 && view.stages.length === 3,
  "Unreviewed C source cannot qualify as an active site");

const landing = await required("index.html");
check(landing.includes('href="/frontend/"') && landing.includes('href="/gis/gis/"'),
  "Staging landing lost its B/E navigation");

const frontend = await required("frontend/index.html");
check(frontend.includes('href="./evidence-case.html"'),
  "Published B homepage omitted the evidence-only case link");
const casePage = await required("frontend/evidence-case.html");
check(casePage.includes('src="./src/evidence-case-page.js"')
  && casePage.includes('href="./evidence-case.css"')
  && casePage.includes("発表・教育用の事例です。"),
  "Published standalone educational page lost safety/asset requirements");

const assets = [
  "frontend/styles.css",
  "frontend/evidence-case.css",
  "frontend/src/evidence-case-page.js",
  "frontend/src/evidence-case-view-model.js",
  "frontend/mock/shimokamata-evidence-ui-preview.json",
  "gis/gis/index.html",
];
for (const file of assets) await required(file);
const pageJs = await required("frontend/src/evidence-case-page.js");
check(pageJs.includes("parseEvidenceCase(data)")
  && pageJs.includes("content.hidden = true")
  && !pageJs.includes("innerHTML"), "B C-contract gate or privacy safety missing");
const modelJs = await required("frontend/src/evidence-case-view-model.js");
check(modelJs.includes("C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1")
  && modelJs.includes("may_be_used_as_live_shelter_recommendation"),
  "B source-contract required safety clause missing");

const preview = JSON.parse(await required(
  "frontend/mock/shimokamata-evidence-ui-preview.json"
));
check(parseEvidenceCase(preview).isOperational === false,
  "B preview is not display-only");

const areas = [
  ["edogawa.json", "13123"],
  ["niigata.json", "15100"],
  ["nagoya.json", "23100"],
];
const outputs = [];
for (const [filename, code] of areas) {
  const data = JSON.parse(await required("pipeline/data/output/" + filename));
  check(data.region?.code === code,
    "Staging bundle published wrong municipality: " + filename);
  check(
    ["datasets", "assessments", "capabilities", "gaps", "recommendations"]
      .every((key) => Array.isArray(data[key])) && typeof data.meta === "object",
    "Staging bundle D contract invalid for: " + filename
  );
  outputs.push({ name: filename, region_code: code, status: "PACKAGED_ONLY" });
}
const meta = JSON.parse(await required("_staging.json"));
check(meta.paths?.frontend === "/frontend/"
  && meta.paths?.gis === "/gis/gis/"
  && meta.paths?.region_exports === "/pipeline/data/output/",
  "Staging manifest route base disagrees with Render build");

process.stdout.write(JSON.stringify({
  status: "RENDER_EQUIVALENT_BUNDLE_PREDEPLOY_C_EVIDENCE_PASS",
  package_exists: true,
  published_case_path: "/frontend/evidence-case.html",
  source_v1_parse: "PASS_EDUCATIONAL_ONLY",
  active_current_opening: "UNKNOWN",
  human_C_site_approvals_generated: 0,
  D_status_approval_generated: 0,
  region_exports_read_only: outputs,
  real_render_service_not_deployed: true,
  real_render_staging_browser_not_tested: true,
}, null, 2) + "\n");
