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


/*
 * Search questions describe gaps in THIS prototype's evidence, not what an
 * official publisher does or does not provide. A fixed official page is not
 * a live data feed or confirmation of a particular facility's status.
 */
export const RESEARCH_QUESTIONS = Object.freeze({
  meaning: Object.freeze({
    title: "資料が説明している制度・役割は何か",
    prompt: "両方の一次資料を開き、それぞれの対象制度・表記・適用時点を読み比べる。",
    unresolved: "制度の説明が一致しても、個別施設が同じ場所・同じ用途・同じ有効期間であるとは判断できません。",
  }),
  location: Object.freeze({
    title: "資料にある所在地・施設名は同じ施設を指すか",
    prompt: "名称・住所・掲載元を個別に確認する。別資料の施設IDや座標を自動的に結合しない。",
    unresolved: "現・旧校舎などの物理的な同一性・施設IDの対応・適用時点はA/Cの人間レビューが未完了です。",
  }),
  flood: Object.freeze({
    title: "その施設の洪水時の利用条件は確認できるか",
    prompt: "待避施設とGSIの災害別指定を区別し、元の公式条件・表記を確認する。",
    unresolved: "この画面は個別施設の洪水適合性を検証していません。UNKNOWNを利用可能・利用不能に置き換えません。",
  }),
  opening: Object.freeze({
    title: "今この施設が開設され、利用できるか",
    prompt: "過去・平時の掲載情報と、現在の運用情報を別物として考える。",
    unresolved: "この比較ラボは現在の開設・定員・混雑について検証済みの情報源を接続していません。現在利用可能とは判断できません。",
  }),
  route: Object.freeze({
    title: "現在、安全に移動できる経路があるか",
    prompt: "掲載地点と経路の安全確認は別工程であることを確認する。",
    unresolved: "この比較ラボには最新の交通・浸水・通行可否の根拠がなく、経路の安全性や所要時間を判断できません。",
  }),
});

export function buildEvidenceComparison(questionId, leftId, rightId) {
  const question = RESEARCH_QUESTIONS[questionId];
  const left = SOURCES.find((source) => source.id === leftId);
  const right = SOURCES.find((source) => source.id === rightId);
  if (!question) throw new Error("確認したい問いが未定義です");
  if (!left || !right) throw new Error("比較する資料が未定義です");
  if (leftId === rightId) throw new Error("異なる2つの資料を選んでください");
  return Object.freeze({
    questionId,
    questionTitle: question.title,
    prompt: question.prompt,
    unresolved: question.unresolved,
    left,
    right,
  });
}

export function buildComparisonMemo(topic, reviewedIds = [], comparison = null) {
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
    ...(comparison ? (() => {
      const view = buildEvidenceComparison(comparison.questionId, comparison.leftId, comparison.rightId);
      return [
        "比較したい問い: " + view.questionTitle,
        "比較対象: " + view.left.title + " ／ " + view.right.title,
        "比較に必要な確認: " + view.prompt,
        "この画面では未確定: " + view.unresolved,
      ];
    })() : []),
    "利用者の自己申告による原文確認:",
    ...SOURCES.map((s) => "- " + (confirmed.has(s.id) ? "原文を確認した" : "未確認") + "｜" + s.title + "｜" + s.url),
    "未確認の事項: 個々の施設の同一性・最新の開設状況・収容状況・洪水適合性・移動経路の安全性",
    "このメモは操作検証用です。人間によるA/C正式承認、D投入、避難先推奨には使用できません。",
  ].join("\n");
}
