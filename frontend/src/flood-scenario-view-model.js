// D RegionExport.scenarios[] is optional. This is a display adapter only:
// never infer flood safety/eligibility from the municipality's raw markers.
// See HINANEX Issue #48 and pipeline/docs/FLOOD_SCENARIO_CONTRACT.md.

function readable(value, fallback = "未確認") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
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

function buildFloodScenarioViewModel(exportData) {
  const scenario = Array.isArray(exportData?.scenarios)
    ? exportData.scenarios.find((item) => item?.scenario_id === "flood_shelter_selection")
    : null;

  // Old v0.9 RegionExport payloads legitimately omit this extension.
  if (!scenario) return null;

  const results = Array.isArray(scenario.facility_results)
    ? scenario.facility_results
    : [];
  const rows = results.map((item, index) => {
    const fact = item?.fact ?? {};
    return {
      key: readable(item?.facility_id, `row-${index + 1}`),
      name: readable(fact.facility_name, "施設名未確認"),
      // Do not convert CANDIDATE/EXCLUDED or source ○/× into a safety claim.
      statusCode: readable(item?.status, "UNKNOWN"),
      rawValue: readable(fact.official_status_raw),
      floorRaw: readable(fact.usable_floor_raw, "条件の記録なし"),
      hazardScopeRaw: readable(fact.hazard_scope_raw),
      joinStatus: readable(fact.join_status),
      sourceTrace: readable(fact.source_record_trace, "施設単位の照合未確定"),
      sourceUrl: officialHttpsUrl(fact.source_url),
      reason: readable(item?.reason, "判定理由未確認"),
      hasCoordinates:
        Number.isFinite(fact.latitude) && Number.isFinite(fact.longitude),
    };
  });
  return {
    name: readable(scenario.scenario_name, "洪水時の避難候補探索"),
    statusCode: readable(scenario.status, "UNKNOWN"),
    discoveryStatus: readable(scenario.requirement_assessment?.discovery_status),
    rawValueCount: Number.isInteger(scenario.requirement_assessment?.raw_value_count)
      ? scenario.requirement_assessment.raw_value_count
      : null,
    total: rows.length,
    unknownCount: rows.filter((item) => item.statusCode === "UNKNOWN").length,
    rawFloorCount: rows.filter((item) => item.floorRaw !== "条件の記録なし").length,
    rows,
    caveat:
      "これは公式Sourceの記録・追跡状況です。UNKNOWNは危険・利用不可の意味ではありません。" +
      "記号の意味・開設状況・建物や経路の安全性はこの画面では確定できません。",
    interpretationNotice:
      "新潟市ODSの○・×・－と階数記号は自治体固有の公式対応表を確認中です。" +
      "既存のRegionExportにCANDIDATE/EXCLUDEDが含まれても、ここから安全性や利用可否を推測しません。",
  };
}

export { buildFloodScenarioViewModel };
