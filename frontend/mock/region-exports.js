const dataQualityKeys = [
  "completeness",
  "coverage",
  "timeliness",
  "validity",
  "consistency",
  "accuracy_confidence",
  "traceability",
];

const applicationReadinessKeys = [
  "discoverability",
  "accessibility",
  "machine_readability",
  "interoperability",
  "geospatial_usability",
  "update_automation",
  "reusability",
  "semantic_fitness",
];

const fullDataQualityScores = [4, 3, null, 3, 4, null, 4];
const fullApplicationReadinessScores = [4, 4, 4, 3, 4, 2, 3, 3];
const blockedDataQualityScores = [0, null, null, null, 4, null, 4];
const blockedApplicationReadinessScores = [4, 4, 0, 0, 0, 0, 0, null];

const MOCK_REGION_OPTIONS = Object.freeze([
  Object.freeze({ key: "edogawa", label: "東京都江戸川区" }),
  Object.freeze({ key: "niigata", label: "新潟県新潟市" }),
  Object.freeze({ key: "nagoya", label: "愛知県名古屋市" }),
]);

function buildMetrics(keys, scores, regionLabel) {
  return Object.fromEntries(
    keys.map((key, index) => [
      key,
      {
        score: scores[index],
        reason: `${regionLabel}のUI表示を確認するための仮スコアです。実際の評価ではありません。`,
      },
    ]),
  );
}

function createMockRegionExport({ key, code, label, capabilityStatus, recordCount }) {
  const isBlocked = capabilityStatus === "BLOCKED";
  const regionCode = `DEMO-${code}`;
  const regionName = `${label}（UI確認用仮データ）`;
  const generatedAt = `2026-10-06T0${MOCK_REGION_OPTIONS.findIndex((item) => item.key === key)}:15:00Z`;
  const gaps = isBlocked
    ? [
        {
          capability_code: "shelter_discovery",
          requirement_code: "shelter_location",
          kind: "INVESTIGATION",
          severity: "HIGH",
          reason: "追加調査カードを確認するための仮Gapです。自治体側の不足を示しません。",
          capability_status: "BLOCKED",
        },
      ]
    : [];
  const recommendations = isBlocked
    ? [
        {
          capability_code: "shelter_discovery",
          requirement_code: "shelter_location",
          recommendation_type: "INVESTIGATE_DATA",
          priority: "HIGH",
          title: "取得・変換経路の追加調査を表示する",
          actions: ["取得経路を確認する仮action", "列構造を確認する仮action"],
          rationale: "複数actionを持つRecommendation表示を確認するための仮データです。",
        },
      ]
    : [];

  return {
    region: { code: regionCode, name: regionName },
    datasets: [
      {
        region_code: regionCode,
        region_name: regionName,
        requirement_code: "shelter_location",
        records: [],
        evidence: [
          {
            source_name: `${label} UI確認用仮Evidence`,
            source_url: null,
            publisher: null,
            published_at: null,
            fetched_at: generatedAt,
            license: null,
            source_format: "UI_FIXTURE",
            retrieval_method: "frontend mock module",
            notes: "画面表示の確認専用です。実在する施設・公開状況・評価結果を表しません。",
          },
        ],
        normalized_at: generatedAt,
      },
    ],
    assessments: [
      {
        region_code: regionCode,
        region_name: regionName,
        requirement_code: "shelter_location",
        discovery_status: isBlocked ? "NOT_MACHINE_READABLE" : "AVAILABLE",
        data_quality: buildMetrics(
          dataQualityKeys,
          isBlocked ? blockedDataQualityScores : fullDataQualityScores,
          label,
        ),
        application_readiness: buildMetrics(
          applicationReadinessKeys,
          isBlocked ? blockedApplicationReadinessScores : fullApplicationReadinessScores,
          label,
        ),
        record_count: recordCount,
        findings: [
          `${label}のSC02表示を確認するための仮所見です。`,
          "実在地域についての不足・未公開・安全性を示す情報ではありません。",
        ],
        assessed_at: generatedAt,
        assessment_version: "0.9",
      },
    ],
    capabilities: [
      {
        region_code: regionCode,
        region_name: regionName,
        capability_code: "shelter_discovery",
        capability_name: "Shelter Discovery",
        status: capabilityStatus,
        dependency_results: [
          {
            requirement_code: "shelter_location",
            criticality: 3,
            status: isBlocked ? "BLOCKED" : "READY",
            reasons: ["UI表示確認用に固定した仮状態です。実際の判定結果ではありません。"],
          },
        ],
        reasons: [
          `${capabilityStatus}カードを確認するための仮データです。`,
          "実際の自治体評価や防災判断には使用できません。",
        ],
        assessed_at: generatedAt,
        engine_version: "0.9",
      },
    ],
    gaps,
    recommendations,
    meta: {
      schema_version: "0.9",
      generated_at: generatedAt,
      dataset_count: 1,
      assessment_count: 1,
      capability_count: 1,
      gap_count: gaps.length,
      recommendation_count: recommendations.length,
      evidence_count: 1,
    },
  };
}

const MOCK_REGION_EXPORTS = Object.freeze({
  edogawa: createMockRegionExport({
    key: "edogawa",
    code: "13123",
    label: "東京都江戸川区",
    capabilityStatus: "FULL",
    recordCount: 3,
  }),
  niigata: createMockRegionExport({
    key: "niigata",
    code: "15100",
    label: "新潟県新潟市",
    capabilityStatus: "FULL",
    recordCount: 5,
  }),
  nagoya: createMockRegionExport({
    key: "nagoya",
    code: "23100",
    label: "愛知県名古屋市",
    capabilityStatus: "BLOCKED",
    recordCount: 0,
  }),
});

function getMockRegionExport(regionKey) {
  const payload = MOCK_REGION_EXPORTS[regionKey];
  if (!payload) {
    throw new RangeError(`未定義のUI確認用地域キーです: ${regionKey ?? "値なし"}`);
  }
  return structuredClone(payload);
}

export { MOCK_REGION_EXPORTS, MOCK_REGION_OPTIONS, getMockRegionExport };
