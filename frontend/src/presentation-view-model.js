function buildAnalysisSummary(viewModel) {
  const capability = viewModel.capabilities[0] ?? null;
  const assessment = viewModel.assessments[0] ?? null;

  return {
    regionName: viewModel.regionName,
    capabilityName: capability?.capabilityName ?? "情報なし",
    capabilityStatusCode: capability?.statusCode ?? null,
    capabilityStatusLabel: capability?.statusLabel ?? "情報なし",
    capabilityTone: capability?.tone ?? "unknown",
    recordCountLabel: assessment?.recordCountLabel ?? "データ件数：情報なし",
    scopeNote: assessment?.scopeNote ?? null,
    gapCount: viewModel.counts.gaps,
    recommendationCount: viewModel.counts.recommendations,
    generatedAt: viewModel.generatedAt,
  };
}

function isSelectedRegion(selectedRegionCode, buttonRegionCode) {
  return selectedRegionCode === buttonRegionCode;
}

export { buildAnalysisSummary, isSelectedRegion };
