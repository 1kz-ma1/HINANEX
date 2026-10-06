import { formatDateTime, list, textOrNull } from "./view-model-utils.js";

const dataQualityMetrics = Object.freeze([
  ["completeness", "完全性"],
  ["coverage", "網羅性"],
  ["timeliness", "適時性"],
  ["validity", "妥当性"],
  ["consistency", "一貫性"],
  ["accuracy_confidence", "正確性の確信度"],
  ["traceability", "追跡可能性"],
]);

const applicationReadinessMetrics = Object.freeze([
  ["discoverability", "発見可能性"],
  ["accessibility", "アクセス可能性"],
  ["machine_readability", "機械可読性"],
  ["interoperability", "相互運用性"],
  ["geospatial_usability", "地理空間での利用性"],
  ["update_automation", "更新自動化"],
  ["reusability", "再利用性"],
  ["semantic_fitness", "意味的適合性"],
]);

const unconfirmedCountStatuses = new Set([
  "NOT_MACHINE_READABLE",
  "ACCESS_RESTRICTED",
  "NOT_FOUND",
  "UNKNOWN",
]);

const discoveryStatus = Object.freeze({
  AVAILABLE: { label: "取得済み", tone: "full", description: "現在の取得経路で利用可能です。" },
  PARTIAL: { label: "一部取得", tone: "degraded", description: "現在の取得経路では一部のみ利用可能です。" },
  NOT_MACHINE_READABLE: { label: "機械可読ではない", tone: "blocked", description: "取得先は確認できましたが、現在は機械処理できません。" },
  ACCESS_RESTRICTED: { label: "アクセス制限あり", tone: "blocked", description: "現在の取得経路にはアクセス上の制限があります。" },
  NOT_FOUND: { label: "現在の取得経路では未確認", tone: "unknown", description: "HINANEXの現在の取得経路では確認できていません。自治体が未公開という意味ではありません。" },
  UNKNOWN: { label: "確認状況不明", tone: "unknown", description: "取得状況を判断できる情報が不足しています。" },
  NOT_APPLICABLE: { label: "対象外", tone: "not-applicable", description: "この評価では対象外です。" },
});

const unconfirmedCountStatuses = new Set([
  "NOT_MACHINE_READABLE",
  "ACCESS_RESTRICTED",
  "NOT_FOUND",
  "UNKNOWN",
]);

function getDiscoveryStatusMeta(status) {
  return discoveryStatus[status] ?? {
    label: `未定義（${status ?? "値なし"}）`,
    tone: "unknown",
    description: "Contractで定義されていない状態です。",
  };
}

function buildMetricViewModel(key, label, metric) {
  const score = Number.isInteger(metric?.score) ? metric.score : null;
  const isUnassessed = score === null;

  return {
    key,
    label,
    score,
    scoreLabel: isUnassessed ? "未評価" : `${score} / 4`,
    tone: isUnassessed ? "unassessed" : `score-${score}`,
    isUnassessed,
    reason: textOrNull(metric?.reason) ?? "評価理由は提供されていません。",
  };
}

function buildMetricGroup(source, definitions) {
  return definitions.map(([key, label]) => buildMetricViewModel(key, label, source?.[key]));
}

function buildRecordCountPresentation(discoveryCode, recordCount) {
  if (discoveryCode === "NOT_APPLICABLE") {
    return {
      label: "件数表示の対象外",
      note: "この評価ではDataset件数を表示する対象ではありません。",
    };
  }

  if (unconfirmedCountStatuses.has(discoveryCode)) {
    const contractValue = Number.isInteger(recordCount)
      ? `RegionExportのrecord_countは${recordCount.toLocaleString("ja-JP")}ですが、`
      : "";
    return {
      label: "件数を確認できません",
      note: `${contractValue}実施設が0件という意味ではありません。`,
    };
  }

  if (Number.isInteger(recordCount)) {
    return {
      label: `HINANEXの現在の取得結果：${recordCount.toLocaleString("ja-JP")}件`,
      note: "表示件数は現在の取得経路とDataset scopeに基づく結果です。",
    };
  }

  return {
    label: "データ件数：情報なし",
    note: "RegionExportに有効なrecord_countがありません。",
  };
}

function datasetScopeNote(regionName, requirementCode) {
  if (regionName.includes("名古屋市") && requirementCode === "shelter_location") {
    return "現在のDatasetは16区別の屋内施設データが対象です。屋外施設は含まず、件数は名古屋市の全避難関連施設数を意味しません。";
  }

  return "件数は現在のRegionExportに含まれるDataset範囲です。自治体全体の施設総数を意味しません。";
}

function buildAssessmentViewModel(assessment) {
  const regionName = textOrNull(assessment.region_name) ?? "地域情報なし";
  const requirementCode = textOrNull(assessment.requirement_code) ?? "コード情報なし";
  const discovery = getDiscoveryStatusMeta(assessment.discovery_status);
  const recordCount = Number.isInteger(assessment.record_count) ? assessment.record_count : null;
  const recordCountPresentation = buildRecordCountPresentation(
    assessment.discovery_status,
    recordCount,
  );

  return {
    requirementCode,
    discoveryCode: assessment.discovery_status,
    discoveryLabel: discovery.label,
    discoveryDescription: discovery.description,
    tone: discovery.tone,
    recordCount,
    recordCountLabel: recordCountPresentation.label,
    recordCountNote: recordCountPresentation.note,
    scopeNote: datasetScopeNote(regionName, requirementCode),
    findings: list(assessment.findings),
    assessedAt: formatDateTime(assessment.assessed_at),
    assessmentVersion: textOrNull(assessment.assessment_version) ?? "不明",
    dataQuality: buildMetricGroup(assessment.data_quality, dataQualityMetrics),
    applicationReadiness: buildMetricGroup(
      assessment.application_readiness,
      applicationReadinessMetrics,
    ),
  };
}

function buildAssessmentViewModels(exportData) {
  return list(exportData?.assessments).map(buildAssessmentViewModel);
}

export {
  buildAssessmentViewModel,
  buildAssessmentViewModels,
  buildMetricViewModel,
  buildRecordCountPresentation,
  datasetScopeNote,
  getDiscoveryStatusMeta,
};
