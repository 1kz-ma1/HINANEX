function metric(score, reason = "表示確認用の合成理由") {
  return { score, reason };
}

function regionExport(overrides = {}) {
  const payload = {
    region: { code: "DEMO-23100", name: "名古屋市（UI確認用合成データ）" },
    datasets: [
      {
        region_code: "DEMO-23100",
        region_name: "名古屋市（UI確認用合成データ）",
        requirement_code: "shelter_location",
        records: [],
        evidence: [
          {
            source_name: "UIテスト用合成データ",
            source_url: null,
            publisher: null,
            published_at: null,
            fetched_at: "2026-10-06T01:00:00Z",
            license: null,
            source_format: "XLSX",
            retrieval_method: "fixture",
            notes: "公開日を推測しない表示の確認用です。",
          },
        ],
        normalized_at: "2026-10-06T01:00:00Z",
      },
    ],
    assessments: [
      {
        region_code: "DEMO-23100",
        region_name: "名古屋市（UI確認用合成データ）",
        requirement_code: "shelter_location",
        discovery_status: "AVAILABLE",
        data_quality: {
          completeness: metric(4),
          coverage: metric(0),
          timeliness: metric(null, "未評価の理由"),
          validity: metric(3),
          consistency: metric(2),
          accuracy_confidence: metric(1),
          traceability: metric(4),
        },
        application_readiness: {
          discoverability: metric(4),
          accessibility: metric(3),
          machine_readability: metric(4),
          interoperability: metric(2),
          geospatial_usability: metric(4),
          update_automation: metric(1),
          reusability: metric(3),
          semantic_fitness: metric(null, "未評価の理由"),
        },
        record_count: 12,
        findings: ["合成所見"],
        assessed_at: "2026-10-06T01:05:00Z",
        assessment_version: "0.9",
      },
    ],
    capabilities: [
      {
        region_code: "DEMO-23100",
        region_name: "名古屋市（UI確認用合成データ）",
        capability_code: "shelter_discovery",
        capability_name: "Shelter Discovery",
        status: "FULL",
        dependency_results: [
          {
            requirement_code: "shelter_location",
            criticality: 3,
            status: "READY",
            reasons: ["合成理由"],
          },
        ],
        reasons: ["合成理由"],
        assessed_at: "2026-10-06T01:05:00Z",
        engine_version: "0.9",
      },
    ],
    gaps: [
      {
        capability_code: "shelter_discovery",
        requirement_code: "shelter_location",
        kind: "CONFIRMED_IMPROVEMENT",
        severity: "MEDIUM",
        reason: "合成Gap",
        capability_status: "DEGRADED",
      },
      {
        capability_code: "shelter_discovery",
        requirement_code: "shelter_location",
        kind: "INVESTIGATION",
        severity: "HIGH",
        reason: "合成調査項目",
        capability_status: "UNKNOWN",
      },
    ],
    recommendations: [
      {
        capability_code: "shelter_discovery",
        requirement_code: "shelter_location",
        recommendation_type: "INVESTIGATE_DATA",
        priority: "HIGH",
        title: "合成提案",
        actions: ["action 1", "action 2"],
        rationale: "合成理由",
      },
    ],
    meta: {
      schema_version: "0.9",
      generated_at: "2026-10-06T01:10:00Z",
      dataset_count: 1,
      assessment_count: 1,
      capability_count: 1,
      gap_count: 2,
      recommendation_count: 1,
      evidence_count: 1,
    },
  };

  return { ...payload, ...overrides };
}

export { metric, regionExport };
