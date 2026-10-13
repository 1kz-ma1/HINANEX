/**
 * B consumer of C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1.
 *
 * This is NOT an independent PDF/municipal statement audit. Every approved
 * display string/URL/digest here is pinned to the reviewed C provider v1
 * draft contract so a hand-edited "UNKNOWN => safe" JSON fails closed.
 * Never convert this data to a facility recommendation or GIS coordinate.
 */
export const CONTRACT = "C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1";
export const EXPORT_STATUS = "PUBLIC_EDUCATIONAL_EVIDENCE_NOT_SHELTER_GUIDANCE";

export const PUBLISHED_SOURCES = Object.freeze({
  "2025_reuse_policy_pdf": Object.freeze({
    title: "2025年4月 ｜ 旧校舎の後利用方針",
    url: "https://www.city.edogawa.tokyo.jp/documents/40376/0704simokamata_1.pdf",
    sha: "a4fee786088052e1bb787f0db0473245d01cc1cae9784c80ef40b3174ed089bf",
    date: "2025-04",
    type: "municipal_postclosure_policy",
    detail: "Planned demolition of the old school buildings including gym; completion not established.",
  }),
  "2026_external_internal_plan_pdf": Object.freeze({
    title: "2026年4月1日時点 ｜ 区地域防災計画",
    url: "https://www.city.edogawa.tokyo.jp/documents/68931/00006.pdf",
    sha: "92e85981c16542e3e28bd80bafc56c8a71f3ded9a8b5e67bcb53919d16e1ebcb",
    date: "2026-04-01",
    type: "dated_municipal_external_inland_water_standby_roster",
    detail: "Old and new Shimokamata schools appear separately in external and inland water tables.",
  }),
  "2026_demolition_bill_pdf": Object.freeze({
    title: "2026年6月12日 ｜ 解体契約議案",
    url: "https://www.gikai.city.edogawa.tokyo.jp/voices/GikaiDoc/attach/Gk/Gk2792_gian64.pdf",
    sha: "aa9051ef17e94da904e7e11fa228239d59a37e3eb256b0bc44f68991e19adc71",
    date: "2026-06-12",
    type: "municipal_assembly_contract_bill",
    detail: "Bill #64 proposes removal of former campus buildings including the gym; not proof of works completed.",
  }),
  "2026_demolition_vote_html": Object.freeze({
    title: "2026年7月1日 ｜ 区議会議決結果",
    url: "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2",
    sha: "83e6d3bac16705d3a842b7129883f8151e40426abd9f2e40c123ff220ec8ab20",
    date: "2026-07-01",
    type: "municipal_council_vote_result",
    detail: "Council bill #64 passed unanimously, not a demolition or current-opening certificate.",
  }),
});

export const DEMO_STAGES = Object.freeze([
  Object.freeze({
    key: "DOCUMENTARY_FACT",
    displayState: "HISTORICAL_SOURCE_FACT",
    title: "公式資料で確認できること",
    message: "2026年4月1日時点の区の資料では旧・新下鎌田小を別施設として掲載。同年7月に旧施設の解体工事契約議案が可決された。",
    sourceKeys: [
      "2025_reuse_policy_pdf",
      "2026_external_internal_plan_pdf",
      "2026_demolition_bill_pdf",
      "2026_demolition_vote_html",
    ],
    proofFlag: "document_dates_not_current_operating_dates",
  }),
  Object.freeze({
    key: "SOURCE_VERSION_RECONCILIATION",
    displayState: "HUMAN_SOURCE_RECONCILIATION_REQUIRED",
    title: "資料間で追加確認が必要なこと",
    message: "水害待避施設一覧と旧校舎の解体計画・契約は対象時点が異なる。新校舎の住所表記にも資料間差があるため、指定先の建物・適用時点を確認する。",
    sourceKeys: [
      "2025_reuse_policy_pdf",
      "2026_external_internal_plan_pdf",
      "2026_demolition_bill_pdf",
    ],
    proofFlag: "not_a_proven_logical_contradiction",
  }),
  Object.freeze({
    key: "CURRENT_OPERATIONS_UNKNOWN",
    displayState: "UNKNOWN_HUMAN_AND_LIVE_SOURCE_REQUIRED",
    title: "現在の状態は未確認",
    message: "旧校舎・体育館の現存、工事による立入制限、外水・内水の指定継続、災害当日の開設状況は未確認。安全・危険、利用可・不可のいずれにも確定しない。",
    sourceKeys: ["2026_external_internal_plan_pdf", "2026_demolition_vote_html"],
    proofFlag: "current_operational_status",
  }),
]);

const EXPECTED_TOP_LEVEL = [
  "status", "presentation_only", "current_site_safety_or_opening_claim",
  "may_be_used_as_live_shelter_recommendation", "consumer_contract",
  "target_case", "source_documents", "demo_states",
  "not_reenacted_historical_disaster_or_predictive_accuracy_result",
  "human_C_site_pairs_approved", "new_flood_candidate_or_excluded",
  "region_export_read_or_mutated", "no_private_reply_text_or_personal_data_included",
];
const EXPECTED_SOURCE_FIELDS = [
  "original_url", "document_date_scope", "source_type", "verified_detail",
  "original_sha256", "originals_checked_in_prior_separate_github_actions",
  "original_bytes_reverified_by_this_public_export", "human_C_physical_site_approval",
];
const EXPECTED_TARGET_FIELDS = [
  "name", "site_address_raw", "separate_current_school_address_raw",
  "new_school_plan_raw_address_2026", "old_new_premises_human_link_approved",
];

const object = (o) => o !== null && typeof o === "object" && !Array.isArray(o);
const hasExactKeys = (o, keys) =>
  object(o) && Object.keys(o).length === keys.length &&
  keys.every((k) => Object.prototype.hasOwnProperty.call(o, k));
const equalArray = (a, b) =>
  Array.isArray(a) && a.length === b.length && a.every((x, i) => x === b[i]);

export class EvidenceContractError extends Error {
  constructor(message) {
    super(message);
    this.name = "EvidenceContractError";
  }
}
function requireValue(condition, message) {
  if (!condition) throw new EvidenceContractError(message);
}

/**
 * Fail closed: rejects unknown fields, edited historical claims, changed
 * sources, fabricated approval and any reinterpretation of UNKNOWN.
 * Returned view model uses pinned C-reviewed public copy only.
 */
export function parseEvidenceCase(data) {
  requireValue(hasExactKeys(data, EXPECTED_TOP_LEVEL), "想定外のデータ項目があります");
  requireValue(data.status === EXPORT_STATUS && data.consumer_contract === CONTRACT,
    "C公開用Evidence契約ではありません");
  for (const [name, expected] of Object.entries({
    presentation_only: true,
    current_site_safety_or_opening_claim: false,
    may_be_used_as_live_shelter_recommendation: false,
    not_reenacted_historical_disaster_or_predictive_accuracy_result: true,
    human_C_site_pairs_approved: 0,
    new_flood_candidate_or_excluded: 0,
    region_export_read_or_mutated: false,
    no_private_reply_text_or_personal_data_included: true,
  })) {
    requireValue(typeof data[name] === typeof expected && data[name] === expected,
      "公開用途・安全判定禁止条件を満たしていません: " + name);
  }
  const target = data.target_case;
  requireValue(hasExactKeys(target, EXPECTED_TARGET_FIELDS), "施設情報の契約が不正です");
  for (const [name, expected] of Object.entries({
    name: "旧下鎌田小学校",
    site_address_raw: "東瑞江3丁目11番1号",
    separate_current_school_address_raw: "瑞江4丁目19番10号",
    new_school_plan_raw_address_2026: "瑞江4-19-1",
    old_new_premises_human_link_approved: false,
  })) requireValue(target[name] === expected, "旧新校舎の識別に不一致があります");
  const sources = data.source_documents;
  const sourceKeys = Object.keys(PUBLISHED_SOURCES);
  requireValue(hasExactKeys(sources, sourceKeys), "出典4件の識別子が一致しません");
  for (const key of sourceKeys) {
    const expected = PUBLISHED_SOURCES[key], s = sources[key];
    requireValue(hasExactKeys(s, EXPECTED_SOURCE_FIELDS), "出典形式が一致しません: " + key);
    requireValue(
      s.original_url === expected.url && s.original_sha256 === expected.sha &&
      s.document_date_scope === expected.date && s.source_type === expected.type &&
      s.verified_detail === expected.detail &&
      s.originals_checked_in_prior_separate_github_actions === true &&
      s.original_bytes_reverified_by_this_public_export === false &&
      s.human_C_physical_site_approval === false,
      "出典のURI・原本版・確認範囲が一致しません: " + key
    );
  }
  requireValue(Array.isArray(data.demo_states) &&
    data.demo_states.length === DEMO_STAGES.length, "3状態の数が不正です");
  DEMO_STAGES.forEach((expected, i) => {
    const s = data.demo_states[i];
    const stageKeys = [
      "key", "label", "display_state", "source_keys", "message", expected.proofFlag,
    ];
    requireValue(hasExactKeys(s, stageKeys), "状態の契約が不正です: " + expected.key);
    requireValue(
      s.key === expected.key && s.label === expected.title &&
      s.display_state === expected.displayState &&
      s.message === expected.message &&
      equalArray(s.source_keys, expected.sourceKeys) &&
      s[expected.proofFlag] === (expected.key === "CURRENT_OPERATIONS_UNKNOWN" ? "UNKNOWN" : true),
      "未承認の評価結果を表示できません: " + expected.key
    );
  });
  return {
    status: EXPORT_STATUS,
    title: "旧下鎌田小学校：資料の時点差から考える",
    addresses: {
      old: "東瑞江3丁目11番1号",
      newSchool: "瑞江4丁目19番10号",
      newPlanRaw: "瑞江4-19-1",
    },
    stages: DEMO_STAGES.map((d, i) => ({
      key: d.key,
      number: i + 1,
      label: d.title,
      message: d.message,
      sourceKeys: [...d.sourceKeys],
      isCurrentUnknown: d.key === "CURRENT_OPERATIONS_UNKNOWN",
    })),
    sources: sourceKeys.map((key) => ({
      key, title: PUBLISHED_SOURCES[key].title,
      date: PUBLISHED_SOURCES[key].date,
      url: PUBLISHED_SOURCES[key].url,
      sha256: PUBLISHED_SOURCES[key].sha,
    })),
    isOperational: false,
    isHistoricalReenactment: false,
    currentOpening: "UNKNOWN",
    reverifiedOriginalsInBrowser: false,
  };
}
