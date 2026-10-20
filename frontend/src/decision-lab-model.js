/**
 * Product-first, source-first comparison prototype.
 * No facility/hazard/route suitability is inferred here.
 * User confirmations are session-local notes, not A/C human source approval.
 */
export const TOPICS = Object.freeze({
  wide: "区外も含めた早期避難の考え方を確認したい",
  waiting: "区の待避施設の位置づけを確認したい",
  gsi: "GSI掲載地点と区の施設資料の違いを確認したい",
  undecided: "何から調べるべきか整理したい",
});

export const SOURCES = Object.freeze([
  Object.freeze({
    id: "wide",
    title: "江戸川区：広域避難",
    description: "大規模水害時の区外を含む早期避難の考え方を、区の原文で確認する。",
    url: "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/koikihinan.html",
    scope: "避難方針の説明（個別施設の安全判定ではない）",
  }),
  Object.freeze({
    id: "waiting",
    title: "江戸川区：水害時待避施設",
    description: "広域避難が困難な場合などの緊急的な待避施設と利用条件を、区の原文で確認する。",
    url: "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html",
    scope: "自治体の待避施設資料（現在の開設情報ではない）",
  }),
  Object.freeze({
    id: "flow",
    title: "江戸川区：水害時の避難フロー",
    description: "状況に応じた公式の案内を確認する。画面上の選択から避難先を自動決定しない。",
    url: "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/suigaihinan.html",
    scope: "避難行動の一般案内（現在の避難指示を示さない）",
  }),
  Object.freeze({
    id: "gsi",
    title: "国土地理院：指定緊急避難場所",
    description: "GSIに掲載される地点の意味を確認する。区の待避施設一覧とは別の資料として扱う。",
    url: "https://www.gsi.go.jp/bousaichiri/hinanbasho.html",
    scope: "掲載制度の説明（開設・混雑・安全性の証明ではない）",
  }),
]);

export function buildComparisonMemo(topic, reviewedIds = []) {
  if (!Object.hasOwn(TOPICS, topic)) {
    throw new Error("未定義の確認目的です");
  }
  if (!Array.isArray(reviewedIds) || reviewedIds.some((id) => !SOURCES.some((s) => s.id === id))) {
    throw new Error("未定義の資料IDです");
  }
  const confirmed = new Set(reviewedIds);
  return [
    "HINANEX｜根拠比較ラボ・個人用確認メモ",
    "目的: " + TOPICS[topic],
    "利用者の自己申告による原文確認:",
    ...SOURCES.map((s) => "- " + (confirmed.has(s.id) ? "原文を確認した" : "未確認") + "｜" + s.title + "｜" + s.url),
    "未確認の事項: 個々の施設の同一性・最新の開設状況・収容状況・洪水適合性・移動経路の安全性",
    "このメモは操作検証用です。人間によるA/C正式承認、D投入、避難先推奨には使用できません。",
  ].join("\n");
}
