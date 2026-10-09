import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { buildFloodScenarioViewModel } from "../src/flood-scenario-view-model.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";
import { regionExport } from "./fixtures.js";

function facilityResult({
  id,
  name,
  status = "UNKNOWN",
  reason = "現在の取得結果では施設単位の条件を確定できないため",
  scope = "災害種別_洪水",
  semantics = "新潟市の公式CSVにある災害種別_洪水列",
  raw = null,
  floor = null,
  join = "DIRECT_SAME_SOURCE",
  trace = "csv_row=2",
  sourceUrl = "https://example.test/official.csv",
  latitude = null,
  longitude = null,
}) {
  return {
    facility_id: id,
    status,
    reason,
    fact: {
      facility_id: id,
      facility_name: name,
      hazard_scope_raw: scope,
      source_semantics: semantics,
      official_status_raw: raw,
      usable_floor_raw: floor,
      source_url: sourceUrl,
      source_record_trace: trace,
      join_status: join,
      latitude,
      longitude,
    },
  };
}

function withScenario() {
  const payload = regionExport();
  payload.scenarios = [{
    region_code: "DEMO-23100",
    region_name: "名古屋市（UI確認用合成データ）",
    scenario_id: "flood_shelter_selection",
    scenario_name: "洪水時の避難候補探索",
    hazard: "flood",
    status: "UNKNOWN",
    requirement_assessment: {
      requirement_code: "shelter_hazard_applicability",
      discovery_status: "AVAILABLE",
      // Deliberately different from facility_results.length. B must not recalculate them.
      record_count: 99,
      directly_joined_count: 7,
      raw_value_count: 0,
      reason: "Dが公開したScenario-local assessment理由",
    },
    facility_results: [
      facilityResult({
        id: "s1",
        name: "施設A",
        raw: "○",
        latitude: 37.9,
        longitude: 139.0,
      }),
      facilityResult({
        id: "s2",
        name: "施設B",
        raw: "2階以上",
        floor: "2階以上",
        trace: "csv_row=3",
      }),
      facilityResult({
        id: "s3",
        name: "施設C",
        raw: "×",
        trace: "csv_row=4",
        sourceUrl: "javascript:alert(1)",
      }),
    ],
    reasons: ["Dが公開した全体理由"],
    gaps: ["Dが公開した制約"],
    recommendations: ["Dが公開した確認事項"],
    evaluated_at: "2026-10-08T03:00:00Z",
  }];
  return payload;
}

test("legacy RegionExport without scenarios[] is No Scenario Result, not zero candidates", () => {
  const legacy = regionExport();
  delete legacy.scenarios;

  assert.equal(buildFloodScenarioViewModel(legacy).uiState, "empty");
  assert.equal(buildRegionExportViewModel(legacy).floodScenario.uiState, "empty");
  assert.match(buildFloodScenarioViewModel(legacy).message, /Scenario Resultがありません/);
});

test("Scenario Summary keeps D status and all three D counts without record aggregation", () => {
  const view = buildRegionExportViewModel(withScenario()).floodScenario;

  assert.equal(view.uiState, "ready");
  assert.equal(view.statusCode, "UNKNOWN");
  assert.equal(view.statusLabel, "判断不能");
  assert.equal(view.discoveryStatusCode, "AVAILABLE");
  assert.equal(view.discoveryStatusLabel, "公式raw情報を取得済み");
  assert.equal(view.recordCount, 99);
  assert.equal(view.directlyJoinedCount, 7);
  assert.equal(view.rawValueCount, 0);
  assert.equal(view.rows.length, 3);
  assert.equal("candidateCount" in view, false);
  assert.equal("excludedCount" in view, false);
  assert.equal("unknownCount" in view, false);
  assert.equal(view.assessmentReason, "Dが公開したScenario-local assessment理由");
  assert.deepEqual(view.reasons, ["Dが公開した全体理由"]);
});

test("D Schema defaults are applied only when optional Scenario fields are missing", () => {
  const payload = withScenario();
  delete payload.scenarios[0].scenario_id;
  delete payload.scenarios[0].scenario_name;
  delete payload.scenarios[0].hazard;
  delete payload.scenarios[0].requirement_assessment.requirement_code;

  const view = buildFloodScenarioViewModel(payload);

  assert.equal(view.uiState, "ready");
  assert.equal(view.name, "洪水時の避難候補探索");
  assert.equal(view.statusCode, "UNKNOWN");
});

test("explicit invalid Scenario values are not replaced with Schema defaults", () => {
  const emptyName = withScenario();
  emptyName.scenarios[0].scenario_name = "";
  assert.equal(buildFloodScenarioViewModel(emptyName).uiState, "unsupported");

  const otherHazard = withScenario();
  otherHazard.scenarios[0].hazard = "tsunami";
  assert.equal(buildFloodScenarioViewModel(otherHazard).uiState, "unsupported");

  const paddedHazard = withScenario();
  paddedHazard.scenarios[0].hazard = " flood ";
  assert.equal(buildFloodScenarioViewModel(paddedHazard).uiState, "unsupported");

  const otherRequirement = withScenario();
  otherRequirement.scenarios[0].requirement_assessment.requirement_code = "other_requirement";
  assert.equal(buildFloodScenarioViewModel(otherRequirement).uiState, "unsupported");
});

test("FULL and DEGRADED describe D coverage, not the presence of candidates", () => {
  const payload = withScenario();

  payload.scenarios[0].status = "FULL";
  payload.scenarios[0].facility_results.forEach((item) => {
    item.status = "EXCLUDED";
  });
  assert.equal(buildFloodScenarioViewModel(payload).statusLabel, "全施設を判定可能");

  payload.scenarios[0].status = "DEGRADED";
  assert.equal(buildFloodScenarioViewModel(payload).statusLabel, "一部施設を判定可能");
});

test("CANDIDATE, EXCLUDED, UNKNOWN are distinct D statuses with safe Japanese labels", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].status = "CANDIDATE";
  payload.scenarios[0].facility_results[1].status = "EXCLUDED";
  const view = buildFloodScenarioViewModel(payload);

  assert.deepEqual(view.rows.map((item) => item.statusCode), [
    "CANDIDATE",
    "EXCLUDED",
    "UNKNOWN",
  ]);
  assert.deepEqual(view.rows.map((item) => item.statusLabel), ["候補", "候補外", "判断不能"]);
  assert.match(view.rows[0].statusHelp, /安全性や開設を保証/);
  assert.match(view.rows[1].statusHelp, /危険または利用不可という意味ではありません/);
  assert.match(view.rows[2].statusHelp, /確定できません/);
});

test("facility reason, evidence and raw municipality semantics remain verbatim", () => {
  const view = buildFloodScenarioViewModel(withScenario());

  assert.equal(view.rows[0].reason, "現在の取得結果では施設単位の条件を確定できないため");
  assert.equal(view.rows[0].hazardScopeRaw, "災害種別_洪水");
  assert.equal(view.rows[0].sourceSemantics, "新潟市の公式CSVにある災害種別_洪水列");
  assert.deepEqual(view.rows.map((item) => item.rawValue), ["○", "2階以上", "×"]);
  assert.equal(view.rows[1].floorRaw, "2階以上");
  assert.equal(view.rows[1].joinStatusLabel, "同じ公式Sourceの施設行で照合済み");
  assert.equal(view.rows[1].sourceTrace, "csv_row=3");
  assert.equal(view.rows[1].hasCoordinates, false);
});

test("江戸川の水害、名古屋の洪水・内水をflood-onlyへ書き換えない", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results = [
    facilityResult({
      id: "edo-1",
      name: "江戸川施設",
      scope: "水害",
      semantics: "水害時の待避施設・使用可能階数。洪水単独指定ではない。",
      join: "UNVERIFIED",
      trace: null,
    }),
    facilityResult({
      id: "nagoya-1",
      name: "名古屋施設",
      scope: "洪水・内水",
      semantics: "16区別の屋内施設データにある洪水・内水の複合列",
      raw: "－",
    }),
  ];
  const view = buildFloodScenarioViewModel(payload);

  assert.equal(view.rows[0].hazardScopeRaw, "水害");
  assert.match(view.rows[0].sourceSemantics, /洪水単独指定ではない/);
  assert.equal(view.rows[0].joinStatusCode, "UNVERIFIED");
  assert.equal(view.rows[1].hazardScopeRaw, "洪水・内水");
  assert.match(view.rows[1].sourceSemantics, /16区別の屋内施設データ/);
  assert.equal(view.rows[1].statusCode, "UNKNOWN");
});

test("official links are HTTPS only and untrusted values remain text", () => {
  const view = buildFloodScenarioViewModel(withScenario());

  assert.equal(view.rows[0].sourceUrl, "https://example.test/official.csv");
  assert.equal(view.rows[2].sourceUrl, null);
  assert.equal(view.rows[0].name, "施設A");
});

test("unknown or malformed D contract stops as unsupported without guessed fields", () => {
  const payload = withScenario();
  payload.scenarios[0].facility_results[0].status = "SAFE";
  const view = buildFloodScenarioViewModel(payload);

  assert.equal(view.uiState, "unsupported");
  assert.match(view.message, /値を推測せず表示を停止/);
  assert.equal("rows" in view, false);
});

test("unknown scenario IDs do not override the flood UI", () => {
  const payload = withScenario();
  payload.scenarios[0].scenario_id = "unrelated_scenario";

  assert.equal(buildFloodScenarioViewModel(payload).uiState, "empty");
});

test("Scenario付きmockは合成デモ識別を保ち実RegionExportに偽装しない", async () => {
  const payload = JSON.parse(
    await readFile(new URL("../mock/region-export.json", import.meta.url), "utf8"),
  );
  const view = buildRegionExportViewModel(payload);

  assert.equal(view.isSynthetic, true);
  assert.equal(view.regionCode, "DEMO-23100");
  assert.equal(view.floodScenario.uiState, "ready");
  assert.deepEqual(view.floodScenario.rows.map((row) => row.statusLabel), [
    "候補",
    "候補外",
    "判断不能",
  ]);
});
