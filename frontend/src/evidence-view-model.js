import { list, safeHttpUrl, textOrNull } from "./view-model-utils.js";

function collectEvidence(exportData, requirementCodes = null) {
  const targetCodes = requirementCodes ? new Set(requirementCodes) : null;

  return list(exportData?.datasets).flatMap((dataset) => {
    if (targetCodes && !targetCodes.has(dataset.requirement_code)) return [];

    return list(dataset.evidence).map((evidence) => ({
      requirementCode: textOrNull(dataset.requirement_code) ?? "コード情報なし",
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

export { collectEvidence };
