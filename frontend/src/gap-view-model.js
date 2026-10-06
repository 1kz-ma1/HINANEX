import { list, textOrNull } from "./view-model-utils.js";

const gapKind = Object.freeze({
  CONFIRMED_IMPROVEMENT: {
    label: "改善候補",
    description: "現在のEvidenceから不足または品質低下を確認できる項目です。",
    tone: "degraded",
  },
  INVESTIGATION: {
    label: "追加調査",
    description: "存在・取得・評価状況の追加確認が必要です。自治体側の不足を断定するものではありません。",
    tone: "unknown",
  },
});

const severity = Object.freeze({
  HIGH: { label: "高", tone: "blocked" },
  MEDIUM: { label: "中", tone: "degraded" },
  LOW: { label: "低", tone: "full" },
});

function getGapKindMeta(kind) {
  return gapKind[kind] ?? {
    label: `未定義（${kind ?? "値なし"}）`,
    description: "Contractで定義されていないGap種別です。",
    tone: "unknown",
  };
}

function getSeverityMeta(value) {
  return severity[value] ?? { label: `未定義（${value ?? "値なし"}）`, tone: "unknown" };
}

function buildGapViewModels(exportData) {
  return list(exportData?.gaps).map((gap) => {
    const kind = getGapKindMeta(gap.kind);
    const priority = getSeverityMeta(gap.severity);

    return {
      capabilityCode: textOrNull(gap.capability_code) ?? "コード情報なし",
      requirementCode: textOrNull(gap.requirement_code) ?? "コード情報なし",
      kindCode: gap.kind,
      kindLabel: kind.label,
      kindDescription: kind.description,
      severityCode: gap.severity,
      severityLabel: priority.label,
      severityTone: priority.tone,
      tone: kind.tone,
      reason: textOrNull(gap.reason) ?? "理由は提供されていません。",
      capabilityStatus: gap.capability_status,
    };
  });
}

export { buildGapViewModels, getGapKindMeta, getSeverityMeta };
