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
          facility_id: "s1",
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
          facility_id: "s2",
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
          facility_id: "s3",
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
  assert.match(view.caveat, /安全性はこの画面では確定できません/);
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

test("malformed scenarios shape is explicit unsupported, while absence stays legacy", () => {
  const payload = withScenario();
  payload.scenarios = "not-an-array";
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("mismatched facility IDs fail closed instead of displaying plausible rows", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].fact.facility_id = "another-id";
  const view = buildFloodScenarioViewModel(payload);
  assert.equal(view.uiState, "unsupported");
  assert.match(view.message, /表示を停止/);
});

test("unrecognized facility status fails closed", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].status = "SAFE";
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("duplicate facility IDs fail closed", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[1].facility_id = "s1";
  payload.scenarios[0].facility_results[1].fact.facility_id = "s1";
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("scenario region mismatch fails closed", () => {
  const payload = withScenario();
  payload.scenarios[0].region_code = "13123";
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("invalid coordinate value fails closed", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].fact.latitude = "37.9";
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("duplicate flood scenarios fail closed", () => {
  const payload = withScenario();
  payload.scenarios.push(structuredClone(payload.scenarios[0]));
  assert.equal(buildFloodScenarioViewModel(payload).uiState, "unsupported");
});

test("Scenario coverage is not a facility safety or opening guarantee", () => {
  const payload = withScenario();
  payload.scenarios[0].status = "FULL";
  const full = buildFloodScenarioViewModel(payload);
  assert.equal(full.statusDescription, "全施設を判定可能");
  assert.equal(full.discoveryDescription, "公式raw情報を取得済み");
  assert.equal(full.unknownCount, 3);
  assert.match(full.caveat, /安全性はこの画面では確定できません/);
  payload.scenarios[0].status = "DEGRADED";
  assert.equal(buildFloodScenarioViewModel(payload).statusDescription, "一部施設を判定可能");
  payload.scenarios[0].requirement_assessment.discovery_status = "NOT_FOUND";
  assert.match(buildFloodScenarioViewModel(payload).discoveryDescription, /現在の取得経路/);
});

test("valid empty Scenario is ready with zero facility rows, not malformed", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results = [];
  const view = buildFloodScenarioViewModel(payload);
  assert.equal(view.uiState, "ready");
  assert.equal(view.total, 0);
  assert.deepEqual(view.rows, []);
  assert.equal(view.unknownCount, 0);
});
