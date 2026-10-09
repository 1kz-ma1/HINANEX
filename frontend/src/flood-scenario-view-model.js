// Consumer adapter for D's additive RegionExport.scenarios[] contract.
// It validates the fields B renders, but never re-evaluates facility eligibility.

import { formatDateTime } from "./view-model-utils.js";

const SCENARIO_ID = "flood_shelter_selection";
const SCENARIO_NAME = "洪水時の避難候補探索";
const SCENARIO_HAZARD = "flood";
const REQUIREMENT_CODE = "shelter_hazard_applicability";
const SCENARIO_STATUSES = new Set([
  "FULL",
  "DEGRADED",
  "BLOCKED",
  "UNKNOWN",
  "NOT_APPLICABLE",
]);
const FACILITY_STATUSES = new Set(["CANDIDATE", "EXCLUDED", "UNKNOWN"]);
const JOIN_STATUSES = new Set(["DIRECT_SAME_SOURCE", "UNVERIFIED"]);
const DISCOVERY_STATUSES = new Set([
  "AVAILABLE",
  "PARTIAL",
  "NOT_MACHINE_READABLE",
  "ACCESS_RESTRICTED",
  "NOT_FOUND",
  "UNKNOWN",
  "NOT_APPLICABLE",
]);

const SCENARIO_STATUS_META = Object.freeze({
  FULL: { label: "全施設を判定可能", tone: "candidate" },
  DEGRADED: { label: "一部施設を判定可能", tone: "degraded" },
  BLOCKED: { label: "処理上の前提不足", tone: "blocked" },
  UNKNOWN: { label: "判断不能", tone: "unknown" },
  NOT_APPLICABLE: { label: "対象外", tone: "not-applicable" },
});

const FACILITY_STATUS_META = Object.freeze({
  CANDIDATE: {
    label: "候補",
    mark: "○",
    tone: "candidate",
    help: "DのScenario Resultで候補として出力されています。施設の安全性や開設を保証する表示ではありません。",
  },
  EXCLUDED: {
    label: "候補外",
    mark: "—",
    tone: "excluded",
    help: "DのScenario Resultで候補外として出力されています。危険または利用不可という意味ではありません。",
  },
  UNKNOWN: {
    label: "判断不能",
    mark: "?",
    tone: "unknown",
    help: "現在のD Scenario Resultでは、洪水条件を施設単位で確定できません。",
  },
});

const DISCOVERY_LABELS = Object.freeze({
  AVAILABLE: "公式raw情報を取得済み",
  PARTIAL: "一部取得",
  NOT_MACHINE_READABLE: "機械判読できない",
  ACCESS_RESTRICTED: "取得制限あり",
  NOT_FOUND: "取得結果では確認できず",
  UNKNOWN: "確認不能",
  NOT_APPLICABLE: "対象外",
});

const JOIN_LABELS = Object.freeze({
  DIRECT_SAME_SOURCE: "同じ公式Sourceの施設行で照合済み",
  UNVERIFIED: "施設単位の照合未確定",
});

function text(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function schemaDefault(value, defaultValue) {
  return value === undefined ? defaultValue : value;
}

function nullableText(value) {
  return value === null || value === undefined || typeof value === "string";
}

function nonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

function officialHttpsUrl(url) {
  if (typeof url !== "string") return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function stringList(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.some((item) => text(item) === null)) return null;
  return value.map((item) => item.trim());
}

function emptyScenario(message = "このRegionExportには洪水Scenario Resultがありません。") {
  return Object.freeze({ uiState: "empty", message });
}

function unsupportedScenario(message) {
  return Object.freeze({ uiState: "unsupported", message });
}

function validCoordinate(value) {
  return value === null || value === undefined || Number.isFinite(value);
}

function buildFacilityRow(item, index) {
  const fact = item?.fact;
  const facilityId = text(item?.facility_id);
  const factFacilityId = text(fact?.facility_id);
  const statusCode = text(item?.status);
  const joinStatusCode = text(fact?.join_status);

  const valid =
    facilityId !== null &&
    factFacilityId === facilityId &&
    FACILITY_STATUSES.has(statusCode) &&
    text(item?.reason) !== null &&
    text(fact?.facility_name) !== null &&
    text(fact?.hazard_scope_raw) !== null &&
    text(fact?.source_semantics) !== null &&
    nullableText(fact?.official_status_raw) &&
    nullableText(fact?.usable_floor_raw) &&
    text(fact?.source_url) !== null &&
    nullableText(fact?.source_record_trace) &&
    JOIN_STATUSES.has(joinStatusCode) &&
    validCoordinate(fact?.latitude) &&
    validCoordinate(fact?.longitude);

  if (!valid) return null;

  const status = FACILITY_STATUS_META[statusCode];
  return Object.freeze({
    key: `${facilityId}-${index}`,
    facilityId,
    name: fact.facility_name.trim(),
    statusCode,
    statusLabel: status.label,
    statusMark: status.mark,
    statusTone: status.tone,
    statusHelp: status.help,
    reason: item.reason.trim(),
    hazardScopeRaw: fact.hazard_scope_raw.trim(),
    sourceSemantics: fact.source_semantics.trim(),
    rawValue: text(fact.official_status_raw),
    floorRaw: text(fact.usable_floor_raw),
    joinStatusCode,
    joinStatusLabel: JOIN_LABELS[joinStatusCode],
    sourceTrace: text(fact.source_record_trace),
    sourceUrl: officialHttpsUrl(fact.source_url),
    hasCoordinates: Number.isFinite(fact.latitude) && Number.isFinite(fact.longitude),
  });
}

function buildFloodScenarioViewModel(exportData) {
  if (exportData?.scenarios === undefined) return emptyScenario();
  if (!Array.isArray(exportData.scenarios)) {
    return unsupportedScenario("scenarios がD Contractの配列形式ではありません。");
  }

  const scenario = exportData.scenarios.find(
    (item) => schemaDefault(item?.scenario_id, SCENARIO_ID) === SCENARIO_ID,
  );
  if (!scenario) return emptyScenario();

  const assessment = scenario.requirement_assessment;
  const scenarioName = text(schemaDefault(scenario.scenario_name, SCENARIO_NAME));
  const scenarioHazard = schemaDefault(scenario.hazard, SCENARIO_HAZARD);
  const requirementCode = schemaDefault(assessment?.requirement_code, REQUIREMENT_CODE);
  const statusCode = text(scenario.status);
  const reasons = stringList(scenario.reasons);
  const gaps = stringList(scenario.gaps);
  const recommendations = stringList(scenario.recommendations);
  const facilityResults = scenario.facility_results ?? [];
  const evaluatedAt = text(scenario.evaluated_at);
  const exportRegionCode = text(exportData?.region?.code);

  const validHeader =
    text(scenario.region_code) !== null &&
    scenario.region_code.trim() === exportRegionCode &&
    text(scenario.region_name) !== null &&
    scenarioName !== null &&
    scenarioHazard === SCENARIO_HAZARD &&
    SCENARIO_STATUSES.has(statusCode) &&
    requirementCode === REQUIREMENT_CODE &&
    DISCOVERY_STATUSES.has(text(assessment?.discovery_status)) &&
    nonNegativeInteger(assessment?.record_count) &&
    nonNegativeInteger(assessment?.directly_joined_count) &&
    nonNegativeInteger(assessment?.raw_value_count) &&
    text(assessment?.reason) !== null &&
    Array.isArray(facilityResults) &&
    reasons !== null &&
    gaps !== null &&
    recommendations !== null &&
    evaluatedAt !== null &&
    !Number.isNaN(new Date(evaluatedAt).getTime());

  if (!validHeader) {
    return unsupportedScenario(
      "flood_shelter_selection が現在のD Scenario Contractと一致しません。値を推測せず表示を停止しました。",
    );
  }

  const rows = facilityResults.map(buildFacilityRow);
  if (rows.some((row) => row === null)) {
    return unsupportedScenario(
      "施設結果に現在のD Scenario Contractで解釈できない項目があります。値を推測せず表示を停止しました。",
    );
  }

  const scenarioStatus = SCENARIO_STATUS_META[statusCode];
  return Object.freeze({
    uiState: "ready",
    name: scenarioName,
    statusCode,
    statusLabel: scenarioStatus.label,
    statusTone: scenarioStatus.tone,
    discoveryStatusCode: assessment.discovery_status.trim(),
    discoveryStatusLabel:
      DISCOVERY_LABELS[assessment.discovery_status] ?? assessment.discovery_status.trim(),
    recordCount: assessment.record_count,
    directlyJoinedCount: assessment.directly_joined_count,
    rawValueCount: assessment.raw_value_count,
    assessmentReason: assessment.reason.trim(),
    reasons,
    gaps,
    recommendations,
    evaluatedAt: formatDateTime(evaluatedAt),
    rows,
    caveat:
      "表示している候補・候補外・判断不能はDのScenario Resultです。施設の安全性、開設状況、安全な移動経路を保証しません。",
  });
}

export { buildFloodScenarioViewModel };
