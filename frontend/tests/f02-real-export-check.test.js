import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const cli = fileURLToPath(new URL("../scripts/check-f02-real-export.js", import.meta.url));
const synthetic = () => ({
  meta: {
    schema_version: "0.9", generated_at: "2026-01-01T00:00:00Z",
    dataset_count: 1, assessment_count: 1, evidence_count: 1,
  },
  region: { code: "13123", name: "江戸川区（合成データ）" },
  datasets: [{
    region_code: "13123", region_name: "江戸川区（合成データ）",
    requirement_code: "shelter_location",
    records: [{
      id: "fictional-1", name: "架空施設", latitude: null, longitude: null,
      address: null, facility_type: null, supported_disasters: null,
    }],
    evidence: [{
      source_name: "合成資料", source_url: "https://example.invalid/fake",
      license: "CC BY 2.1 JP", published_at: null, fetched_at: "2026-01-01T00:00:00Z",
    }],
  }],
  assessments: [{ region_code: "13123", requirement_code: "shelter_location", record_count: 1 }],
});

function invoke(value) {
  const folder = mkdtempSync(join(tmpdir(), "f02-accept-check-"));
  try {
    const file = join(folder, "synthetic.json");
    if (value !== undefined) writeFileSync(file, JSON.stringify(value), "utf8");
    return spawnSync(process.execPath, [cli, file], { encoding: "utf8" });
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
}

test("missing generated artifact returns NOT_RUN, not an empty shelter list", () => {
  const run = invoke();
  assert.equal(run.status, 2);
  assert.equal(JSON.parse(run.stderr).status, "NOT_RUN");
});

test("synthetic contract compatibility does not imply row approval or publication", () => {
  const run = invoke(synthetic());
  assert.equal(run.status, 0, run.stderr);
  const report = JSON.parse(run.stdout);
  assert.equal(report.status, "CONSUMER_COMPATIBLE");
  assert.equal(report.dataset_records, 1);
  assert.equal(report.without_coordinates, 1);
  assert.deepEqual(report.recorded_licenses, ["CC BY 2.1 JP"]);
  assert.equal(report.official_row_review, "NOT_RUN");
  assert.equal(report.publication_approval, "NOT_GRANTED");
  assert.equal(report.input_provenance, "NOT_INDEPENDENTLY_VERIFIED");
});

test("inconsistent D assessment record counts fail closed", () => {
  const document = synthetic();
  document.assessments[0].record_count = 0;
  const result = invoke(document);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /assessment record_count mismatch/);
});

test("missing dataset evidence and missing source URLs fail closed", () => {
  const absent = synthetic();
  absent.datasets[0].evidence = [];
  absent.meta.evidence_count = 0;
  assert.equal(invoke(absent).status, 1);
  const noLink = synthetic();
  noLink.datasets[0].evidence[0].source_url = "javascript:alert(1)";
  assert.equal(invoke(noLink).status, 1);
});

test("metadata count mismatch, empty records and wrong region fail closed", () => {
  const meta = synthetic();
  meta.meta.dataset_count = 2;
  assert.equal(invoke(meta).status, 1);
  const empty = synthetic();
  empty.datasets[0].records = [];
  empty.assessments[0].record_count = 0;
  assert.equal(invoke(empty).status, 1);
  const region = synthetic();
  region.region.code = "15100";
  assert.equal(invoke(region).status, 1);
});
