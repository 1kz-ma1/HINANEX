import test from "node:test";
import assert from "node:assert/strict";
import { buildFloodScenarioViewModel } from "../src/flood-scenario-view-model.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";
import { regionExport } from "./fixtures.js";

function withScenario() {
  const payload = regionExport();
  payload.scenarios = [{
    scenario_id: "flood_shelter_selection",
    scenario_name: "洪水時の避難候補探索",
    status: "UNKNOWN",
    requirement_assessment: {
      discovery_status: "AVAILABLE",
      record_count: 3,
      raw_value_count: 3,
    },
    facility_results: [
      {
        facility_id: "s1",
        status: "UNKNOWN",
        reason: "公式対応表が未確認",
        fact: {
          facility_name: "施設A",
          hazard_scope_raw: "災害種別_洪水",
          official_status_raw: "○",
          usable_floor_raw: null,
          join_status: "DIRECT_SAME_SOURCE",
          source_record_trace: "csv_row=2",
          source_url: "https://example.test/official.csv",
          latitude: 37.9,
          longitude: 139.0,
        },
      },
      {
        facility_id: "s2",
        status: "UNKNOWN",
        reason: "条件の意味が未確定",
        fact: {
          facility_name: "施設B",
          hazard_scope_raw: "災害種別_洪水",
          official_status_raw: "2階以上",
          usable_floor_raw: "2階以上",
          join_status: "DIRECT_SAME_SOURCE",
          source_record_trace: "csv_row=3",
          source_url: "https://example.test/official.csv",
          latitude: null,
          longitude: null,
        },
      },
      {
        facility_id: "s3",
        status: "UNKNOWN",
        reason: "元の記号だけ保持",
        fact: {
          facility_name: "施設C",
          hazard_scope_raw: "災害種別_洪水",
          official_status_raw: "×",
          usable_floor_raw: null,
          join_status: "DIRECT_SAME_SOURCE",
          source_record_trace: "csv_row=4",
          source_url: "javascript:alert(1)",
          latitude: null,
          longitude: null,
        },
      },
    ],
  }];
  return payload;
}

test("legacy RegionExport without scenarios[] does not invent a scenario", () => {
  const legacy = regionExport();
  delete legacy.scenarios;
  assert.equal(buildFloodScenarioViewModel(legacy), null);
  assert.equal(buildRegionExportViewModel(legacy).floodScenario, null);
});

test("C/D UNKNOWN status and municipality markers remain original text, not safety labels", () => {
  const view = buildRegionExportViewModel(withScenario()).floodScenario;
  assert.equal(view.statusCode, "UNKNOWN");
  assert.equal(view.discoveryStatus, "AVAILABLE");
  assert.equal(view.total, 3);
  assert.equal(view.unknownCount, 3);
  assert.equal(view.rawValueCount, 3);
  assert.equal(view.rawFloorCount, 1);
  assert.deepEqual(view.rows.map((item) => item.statusCode), ["UNKNOWN", "UNKNOWN", "UNKNOWN"]);
  assert.deepEqual(view.rows.map((item) => item.rawValue), ["○", "2階以上", "×"]);
  assert.equal(view.rows[1].floorRaw, "2階以上");
  assert.equal(view.rows[1].hasCoordinates, false);
  assert.match(view.caveat, /安全・開設を保証/);
});

test("link targets are HTTPS only and untrusted display values stay text", () => {
  const view = buildFloodScenarioViewModel(withScenario());
  assert.equal(view.rows[0].sourceUrl, "https://example.test/official.csv");
  assert.equal(view.rows[2].sourceUrl, null);
  assert.equal(view.rows[0].name, "施設A");
});

test("older provisional statuses are displayed as D source values without inferred safe eligibility", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].status = "CANDIDATE";
  payload.scenarios[0].facility_results[2].status = "EXCLUDED";
  const view = buildFloodScenarioViewModel(payload);
  assert.deepEqual(view.rows.map((item) => item.statusCode), ["CANDIDATE", "UNKNOWN", "EXCLUDED"]);
  assert.equal(view.unknownCount, 1);
  assert.match(view.interpretationNotice, /CANDIDATE\/EXCLUDED/);
});

test("unknown scenario IDs do not override flood UI", () => {
  const payload = withScenario();
  payload.scenarios[0].scenario_id = "unrelated_scenario";
  assert.equal(buildFloodScenarioViewModel(payload), null);
});
