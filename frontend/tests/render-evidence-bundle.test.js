import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, copyFile, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const frontend = resolve(fileURLToPath(new URL("..", import.meta.url)));
const checkScript = resolve(frontend, "scripts/check-render-evidence-bundle.mjs");
const publicPreview = resolve(frontend, "mock/shimokamata-evidence-ui-preview.json");
const expected = [
  "frontend/index.html",
  "frontend/evidence-case.html",
  "frontend/styles.css",
  "frontend/evidence-case.css",
  "frontend/src/evidence-case-page.js",
  "frontend/src/evidence-case-view-model.js",
  "frontend/mock/shimokamata-evidence-ui-preview.json",
];
const regions = [["edogawa.json", "13123"], ["niigata.json", "15100"], ["nagoya.json", "23100"]];

async function fakeBundle(destination) {
  for (const rel of expected) {
    const p = resolve(destination, rel);
    await mkdir(dirname(p), { recursive: true });
    await copyFile(resolve(frontend, rel.slice("frontend/".length)), p);
  }
  const landing = resolve(destination, "index.html");
  await writeFile(landing, '<a href="/frontend/">analysis</a><a href="/gis/gis/">GIS</a>');
  const gis = resolve(destination, "gis/gis/index.html");
  await mkdir(dirname(gis), { recursive: true });
  await writeFile(gis, "<html>GIS static page (NOT an evacuation recommendation)</html>");
  const meta = resolve(destination, "_staging.json");
  await writeFile(meta, JSON.stringify({
    paths: {
      frontend: "/frontend/",
      gis: "/gis/gis/",
      region_exports: "/pipeline/data/output/",
    },
  }));
  for (const [name, code] of regions) {
    const path = resolve(destination, "pipeline/data/output", name);
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, JSON.stringify({
      region: { code, name }, datasets: [], assessments: [],
      capabilities: [], gaps: [], recommendations: [], meta: {},
    }));
  }
}

function run(output) {
  return spawnSync(process.execPath, [checkScript, output, publicPreview], {
    encoding: "utf8",
  });
}

test("B staging-bundle validator accepts complete synthetic public-only candidate", async () => {
  const tmp = await mkdtemp(resolve(tmpdir(), "hinanex-render-b-candidate-"));
  try {
    await fakeBundle(tmp);
    const result = run(tmp);
    assert.equal(result.status, 0, result.stderr);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.status, "RENDER_EQUIVALENT_BUNDLE_PREDEPLOY_C_EVIDENCE_PASS");
    assert.equal(summary.real_render_service_not_deployed, true);
    assert.equal(summary.region_exports_read_only.length, 3);
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});

test("B staging-bundle validator fails missing source case asset and wrong D region", async () => {
  const tmp = await mkdtemp(resolve(tmpdir(), "hinanex-render-b-broken-"));
  try {
    await fakeBundle(tmp);
    const page = resolve(tmp, "frontend/evidence-case.html");
    await rm(page);
    const first = run(tmp);
    assert.notEqual(first.status, 0);
    assert.match(first.stderr, /Missing public staging file/);
    await fakeBundle(tmp);
    const edogawa = resolve(tmp, "pipeline/data/output/edogawa.json");
    const data = JSON.parse(await readFile(edogawa, "utf8"));
    data.region.code = "99999";
    await writeFile(edogawa, JSON.stringify(data));
    const second = run(tmp);
    assert.notEqual(second.status, 0);
    assert.match(second.stderr, /wrong municipality/);
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
});
