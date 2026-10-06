import { buildAssessmentViewModels } from "./assessment-view-model.js";
import { buildCapabilityViewModels } from "./capability-view-model.js";
import { collectEvidence } from "./evidence-view-model.js";
import { buildGapViewModels } from "./gap-view-model.js";
import { buildRecommendationViewModels } from "./recommendation-view-model.js";
import { formatDateTime, textOrNull } from "./view-model-utils.js";

function countLabel(value) {
  return Number.isInteger(value) ? value.toLocaleString("ja-JP") : "—";
}

function buildRegionExportViewModel(exportData) {
  if (!exportData || typeof exportData !== "object") {
    throw new TypeError("RegionExportがオブジェクトではありません。");
  }

  const regionCode = textOrNull(exportData.region?.code) ?? "コード情報なし";

  return {
    regionCode,
    regionName: textOrNull(exportData.region?.name) ?? "地域情報なし",
    isSynthetic: regionCode.startsWith("DEMO-"),
    schemaVersion: textOrNull(exportData.meta?.schema_version) ?? "不明",
    generatedAt: formatDateTime(exportData.meta?.generated_at),
    counts: {
      datasets: countLabel(exportData.meta?.dataset_count),
      capabilities: countLabel(exportData.meta?.capability_count),
      gaps: countLabel(exportData.meta?.gap_count),
      recommendations: countLabel(exportData.meta?.recommendation_count),
    },
    capabilities: buildCapabilityViewModels(exportData),
    assessments: buildAssessmentViewModels(exportData),
    gaps: buildGapViewModels(exportData),
    recommendations: buildRecommendationViewModels(exportData),
    evidence: collectEvidence(exportData),
  };
}

export { buildRegionExportViewModel };
