const capabilityStatus = Object.freeze({
  FULL: {
    label: "利用可能",
    description: "現在取得できるデータで、この支援能力を実行できます。",
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

function list(value) {
  return Array.isArray(value) ? value : [];
}

function textOrNull(value) {
  return typeof value === "string" && value.trim() ? value : null;
}

function safeHttpUrl(value) {
  const text = textOrNull(value);
  if (!text) return null;

  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

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

function formatDateTime(value) {
  if (!value) return "日時情報なし";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "日時形式を確認してください";

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Tokyo",
  }).format(date);
}

function collectEvidence(exportData, requirementCodes) {
  const targetCodes = new Set(requirementCodes);

  return list(exportData.datasets).flatMap((dataset) => {
    if (!targetCodes.has(dataset.requirement_code)) return [];

    return list(dataset.evidence).map((evidence) => ({
      requirementCode: dataset.requirement_code,
      sourceName: textOrNull(evidence.source_name) ?? "名称情報なし",
      sourceUrl: safeHttpUrl(evidence.source_url),
      publisher: textOrNull(evidence.publisher),
      publishedAt: textOrNull(evidence.published_at),
      fetchedAt: textOrNull(evidence.fetched_at),
      license: textOrNull(evidence.license),
      sourceFormat: textOrNull(evidence.source_format),
      retrievalMethod: textOrNull(evidence.retrieval_method),
      notes: textOrNull(evidence.notes),
    }));
  });
}

function buildCapabilityViewModel(exportData) {
  if (!exportData || typeof exportData !== "object") {
    throw new TypeError("RegionExportがオブジェクトではありません。");
  }

  const capability = list(exportData.capabilities)[0];
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
    statusDescription: status.description,
    tone: status.tone,
    reasons: list(capability.reasons),
    dependencies,
    evidence: collectEvidence(exportData, requirementCodes),
    assessedAt: formatDateTime(capability.assessed_at),
    engineVersion: textOrNull(capability.engine_version) ?? "不明",
  };
}

export {
  buildCapabilityViewModel,
  collectEvidence,
  formatDateTime,
  getCapabilityStatusMeta,
  getDependencyStatusMeta,
  safeHttpUrl,
};
