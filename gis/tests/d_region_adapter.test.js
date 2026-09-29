const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {};
const adapterPath = path.resolve(__dirname, "../gis/js/d_region_adapter.js");
vm.runInThisContext(fs.readFileSync(adapterPath, "utf8"), { filename: adapterPath });
const adapter = window.HINANEX_D_ADAPTER;

function payload(overrides = {}) {
  const base = {
    region: { code: "13123", name: "東京都江戸川区" },
    datasets: [{
      region_code: "13123",
      region_name: "東京都江戸川区",
      requirement_code: "shelter_location",
      records: [
        {
          id: "test-1",
          name: "TEST FACILITY WITH COORDINATES",
          latitude: 35.0,
          longitude: 139.0,
          address: null,
          administrative_area: null,
          facility_type: "shelter",
          supported_disasters: null,
          accessibility: null,
          capacity: null,
          detail_url: null,
          notes: "synthetic contract-test record"
        },
        {
          id: "test-2",
          name: "TEST FACILITY WITHOUT COORDINATES",
          latitude: null,
          longitude: null,
          address: null,
          administrative_area: null,
          facility_type: null,
          supported_disasters: null,
          accessibility: null,
          capacity: null,
          detail_url: null,
          notes: "synthetic contract-test record"
        }
      ],
      evidence: [{ source_name: "TEST EVIDENCE", publisher: "TEST" }]
    }],
    assessments: [],
    capabilities: [],
    gaps: [],
    recommendations: [],
    meta: {
      schema_version: "0.9",
      generated_at: "2026-09-29T00:00:00Z",
      dataset_count: 1,
      assessment_count: 0,
      capability_count: 0,
      gap_count: 0,
      recommendation_count: 0,
      evidence_count: 1
    }
  };
  return { ...base, ...overrides };
}

{
  const result = adapter.extractShelterLocation(payload(), "13123");
  assert.equal(result.schemaVersion, "0.9");
  assert.equal(result.records.length, 2);
  assert.equal(result.mappableRecords.length, 1);
  assert.equal(result.missingCoordinateRecords.length, 1);
}

assert.throws(
  () => adapter.extractShelterLocation(payload({ region: { code: "15100", name: "新潟県新潟市" } }), "13123"),
  /Region mismatch/
);

{
  const invalid = payload();
  invalid.datasets[0].records[0].longitude = null;
  assert.throws(() => adapter.extractShelterLocation(invalid, "13123"), /coordinates must both/);
}

{
  const invalid = payload();
  invalid.datasets[0].region_code = "15100";
  assert.throws(() => adapter.extractShelterLocation(invalid, "13123"), /region_code mismatch/);
}

{
  const invalid = payload();
  invalid.meta.schema_version = "1.0";
  assert.throws(() => adapter.extractShelterLocation(invalid, "13123"), /Unsupported RegionExport schema_version/);
}

{
  const noShelters = payload();
  noShelters.datasets = [{
    region_code: "13123",
    region_name: "東京都江戸川区",
    requirement_code: "other_requirement",
    records: [],
    evidence: []
  }];
  const result = adapter.extractShelterLocation(noShelters, "13123");
  assert.equal(result.dataset, null);
  assert.equal(result.records.length, 0);
}

console.log("d_region_adapter.test.js: OK");
