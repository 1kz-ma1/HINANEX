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

{
  const extended = payload();
  extended.scenarios = [{
    scenario_id: "flood_shelter_selection",
    region_code: "13123",
    status: "UNKNOWN",
    requirement_assessment: { discovery_status: "AVAILABLE" },
    facility_results: [
      {
        facility_id: "test-1",
        status: "UNKNOWN",
        reason: "公式ODSの記号の定義を確認中",
        fact: {
          facility_id: "test-1",
          official_status_raw: "○",
          usable_floor_raw: null,
          hazard_scope_raw: "災害種別_洪水",
          join_status: "DIRECT_SAME_SOURCE",
          source_record_trace: "csv_row=2",
          source_url: "https://example.test/official.csv"
        }
      },
      {
        facility_id: "test-2",
        status: "UNKNOWN",
        reason: "利用階数のrawを保持",
        fact: {
          facility_id: "test-2",
          official_status_raw: "2階以上",
          usable_floor_raw: "2階以上",
          hazard_scope_raw: "災害種別_洪水",
          join_status: "DIRECT_SAME_SOURCE",
          source_record_trace: "csv_row=3",
          source_url: "https://example.test/official.csv"
        }
      }
    ]
  }];
  const result = adapter.extractShelterLocation(extended, "13123");
  assert.equal(result.floodScenario.status, "UNKNOWN");
  assert.equal(result.floodScenario.sourceContractConsistent, true);
  const malformed = structuredClone(extended);
  malformed.scenarios[0].facility_results[0].status = null;
  assert.equal(adapter.extractShelterLocation(malformed, "13123").floodScenario.sourceContractConsistent, false);
  const duplicated = structuredClone(extended);
  duplicated.scenarios.push(structuredClone(duplicated.scenarios[0]));
  assert.equal(adapter.extractShelterLocation(duplicated, "13123").floodScenario.sourceContractConsistent, false);
  assert.equal(result.floodScenario.discoveryStatus, "AVAILABLE");
  assert.equal(result.floodScenario.recordCount, 2);
  assert.equal(result.floodScenario.unknownCount, 2);
  assert.equal(result.floodScenario.byId.get("test-2").usableFloorRaw, "2階以上");
  assert.equal(result.mappableRecords.length, 1);
  assert.equal(result.missingCoordinateRecords.length, 1);

  extended.scenarios[0].facility_results[1].facility_id = "wrong-id";
  assert.throws(
    () => adapter.extractShelterLocation(extended, "13123"),
    /facility ID exact join mismatch/
  );
}

{
  // A valid old RegionExport does not acquire an invented scenario.
  const result = adapter.extractShelterLocation(payload(), "13123");
  assert.equal(result.floodScenario, null);
}


// CI's dedicated E adapter test entrypoint also exercises the exact same
// consumer adapter against synthetic local file inventories (no real D raw).
require("./inspect_local_region_exports.test.js");
