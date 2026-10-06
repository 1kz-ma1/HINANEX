import { collectEvidence } from "./evidence-view-model.js";
import { formatDateTime, list, safeHttpUrl, textOrNull } from "./view-model-utils.js";

const capabilityStatus = Object.freeze({
  FULL: {
    label: "利用可能",
    description: "現在取得できるデータで、このCapabilityの条件を満たしています。",
    tone: "full",
  },
  DEGRADED: {
    label: "一部制約あり",
    description: "支援能力は利用できますが、データ条件による制約があります。",
    tone: "degraded",
  },
  BLOCKED: {
    label: "現在利用不可",
    description: "現在取得できるデータでは、この支援能力を実行できません。",
    tone: "blocked",
  },
  UNKNOWN: {
    label: "判定不能",
    description: "評価に必要な情報が不足しているため、状態を判定できません。",
    tone: "unknown",
  },
  NOT_APPLICABLE: {
    label: "対象外",
    description: "この地域または評価条件では対象外です。",
    tone: "not-applicable",
  },
});

const dependencyStatus = Object.freeze({
  READY: { label: "準備完了", tone: "full" },
  DEGRADED: { label: "一部制約あり", tone: "degraded" },
  BLOCKED: { label: "利用不可", tone: "blocked" },
  UNKNOWN: { label: "判定不能", tone: "unknown" },
  NOT_APPLICABLE: { label: "対象外", tone: "not-applicable" },
});

const criticalityLabel = Object.freeze({
  1: "補助的",
  2: "重要",
  3: "必須",
});

function getCapabilityStatusMeta(status) {
  return capabilityStatus[status] ?? {
    label: `未定義の状態（${status ?? "値なし"}）`,
    description: "Contractで定義されていない状態です。データ提供側へ確認してください。",
    tone: "unknown",
  };
}

function getDependencyStatusMeta(status) {
  return dependencyStatus[status] ?? {
    label: `未定義（${status ?? "値なし"}）`,
    tone: "unknown",
  };
}

function capabilityDescription(capability, status) {
  if (capability.capability_code === "shelter_discovery" && capability.status === "FULL") {
    return "施設名称と緯度経度を使った位置ベース探索が可能です。避難所の安全性やリアルタイム利用可否を保証する状態ではありません。";
  }

  return status.description;
}

function capabilityScopeNote(capabilityCode) {
  if (capabilityCode !== "shelter_discovery") return null;

  return "災害別安全性、収容人数、アクセシビリティ、避難経路安全性、リアルタイム利用可否は、このCapability判定の対象外です。";
}

function buildCapabilityViewModel(exportData, capabilityInput = null) {
  if (!exportData || typeof exportData !== "object") {
    throw new TypeError("RegionExportがオブジェクトではありません。");
  }

  const capability = capabilityInput ?? list(exportData.capabilities)[0];
  if (!capability) {
    throw new Error("表示できるCapabilityがありません。");
  }

  const status = getCapabilityStatusMeta(capability.status);
  const dependencies = list(capability.dependency_results).map((dependency) => {
    const dependencyMeta = getDependencyStatusMeta(dependency.status);

    return {
      requirementCode: textOrNull(dependency.requirement_code) ?? "コード情報なし",
      criticality: criticalityLabel[dependency.criticality] ?? "重要度情報なし",
      statusCode: dependency.status,
      statusLabel: dependencyMeta.label,
      tone: dependencyMeta.tone,
      reasons: list(dependency.reasons),
    };
  });

  const requirementCodes = dependencies
    .map((dependency) => dependency.requirementCode)
    .filter((code) => code !== "コード情報なし");

  return {
    regionName: textOrNull(exportData.region?.name) ?? "地域情報なし",
    schemaVersion: textOrNull(exportData.meta?.schema_version) ?? "不明",
    generatedAt: formatDateTime(exportData.meta?.generated_at),
    capabilityCode: textOrNull(capability.capability_code) ?? "コード情報なし",
    capabilityName: textOrNull(capability.capability_name) ?? "名称情報なし",
    statusCode: capability.status,
    statusLabel: status.label,
    statusDescription: capabilityDescription(capability, status),
    scopeNote: capabilityScopeNote(capability.capability_code),
    tone: status.tone,
    reasons: list(capability.reasons),
    dependencies,
    evidence: collectEvidence(exportData, requirementCodes),
    assessedAt: formatDateTime(capability.assessed_at),
    engineVersion: textOrNull(capability.engine_version) ?? "不明",
  };
}

function buildCapabilityViewModels(exportData) {
  return list(exportData?.capabilities).map((capability) =>
    buildCapabilityViewModel(exportData, capability),
  );
}

export {
  buildCapabilityViewModel,
  buildCapabilityViewModels,
  collectEvidence,
  formatDateTime,
  getCapabilityStatusMeta,
  getDependencyStatusMeta,
  safeHttpUrl,
};
