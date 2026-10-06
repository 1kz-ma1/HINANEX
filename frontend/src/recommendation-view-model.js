import { list, textOrNull } from "./view-model-utils.js";
import { getSeverityMeta } from "./gap-view-model.js";

const recommendationType = Object.freeze({
  IMPROVE_DATA: { label: "改善候補", tone: "degraded" },
  INVESTIGATE_DATA: { label: "追加調査", tone: "unknown" },
});

function getRecommendationTypeMeta(type) {
  return recommendationType[type] ?? {
    label: `未定義（${type ?? "値なし"}）`,
    tone: "unknown",
  };
}

function buildRecommendationViewModels(exportData) {
  return list(exportData?.recommendations).map((recommendation) => {
    const type = getRecommendationTypeMeta(recommendation.recommendation_type);
    const priority = getSeverityMeta(recommendation.priority);

    return {
      capabilityCode: textOrNull(recommendation.capability_code) ?? "コード情報なし",
      requirementCode: textOrNull(recommendation.requirement_code) ?? "コード情報なし",
      typeCode: recommendation.recommendation_type,
      typeLabel: type.label,
      tone: type.tone,
      priorityCode: recommendation.priority,
      priorityDisplayLabel: "優先度",
      priorityLabel: priority.label,
      priorityTone: priority.tone,
      title: textOrNull(recommendation.title) ?? "提案名なし",
      rationale: textOrNull(recommendation.rationale) ?? "理由は提供されていません。",
      actions: list(recommendation.actions),
    };
  });
}

export { buildRecommendationViewModels, getRecommendationTypeMeta };
