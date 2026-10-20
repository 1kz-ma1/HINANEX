import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { SOURCES, TOPICS, RESEARCH_QUESTIONS, buildComparisonMemo, buildEvidenceComparison } from "../src/decision-lab-model.js";

test("比較ラボは公式一次資料だけを固定HTTPSリンクとして案内する", () => {
  assert.equal(SOURCES.length, 4);
  assert.equal(new Set(SOURCES.map((source) => source.id)).size, SOURCES.length);
  for (const source of SOURCES) {
    const url = new URL(source.url);
    assert.equal(url.protocol, "https:");
    assert.ok(["www.city.edogawa.tokyo.jp", "www.gsi.go.jp"].includes(url.hostname));
    assert.ok(source.scope);
  }
});

test("利用者の目的によって施設・安全判定や公式資料の候補順位を生成しない", () => {
  const a = buildComparisonMemo("wide", []);
  const b = buildComparisonMemo("gsi", []);
  assert.notEqual(a, b);
  for (const source of SOURCES) {
    assert.ok(a.includes(source.url));
    assert.ok(b.includes(source.url));
    assert.ok(a.includes("未確認｜" + source.title));
  }
  assert.match(a, /A\/C正式承認/);
  assert.match(a, /未確認の事項: 個々の施設/);
});

test("個人の原文閲覧チェックはユーザー自身のメモにしか反映しない", () => {
  const memo = buildComparisonMemo("waiting", ["waiting", "gsi", "waiting"]);
  assert.match(memo, /原文を確認した｜江戸川区：水害時待避施設/);
  assert.match(memo, /原文を確認した｜国土地理院：指定緊急避難場所/);
  assert.match(memo, /未確認｜江戸川区：広域避難/);
  assert.throws(() => buildComparisonMemo("unknown", []));
  assert.throws(() => buildComparisonMemo("wide", ["not-a-source"]));
  assert.equal(Object.keys(TOPICS).length, 4);
});

test("操作画面は明示的な試作ラベル・安全上の境界・操作導線を持つ", async () => {
  const html = await readFile(new URL("../decision-lab.html", import.meta.url), "utf8");
  const js = await readFile(new URL("../src/decision-lab.js", import.meta.url), "utf8");
  const css = await readFile(new URL("../decision-lab.css", import.meta.url), "utf8");
  assert.match(html, /操作検証専用・実際の避難判断には使えません/);
  assert.match(html, /施設・安全な経路の推奨/);
  assert.match(html, /name="topic" value="undecided" checked/);
  assert.match(html, /id="sourceCards"/);
  assert.match(html, /id="memo"/);
  assert.match(html, /src="\.\/src\/decision-lab.js"/);
  assert.match(js, /textContent = source\.description/);
  assert.match(js, /sourceCards\.addEventListener\("change", updateMemo\)/);
  assert.match(css, /@media\(max-width:680px\)/);
  assert.doesNotMatch(js, /fetch\(|geolocation|localStorage|sessionStorage/);
});


test("比較は異なる2原本の意味・不足根拠を提示し、順位や安全性を計算しない", () => {
  const comparison = buildEvidenceComparison("meaning", "wide", "waiting");
  assert.equal(comparison.left.title, "江戸川区：広域避難");
  assert.equal(comparison.right.title, "江戸川区：水害時待避施設");
  assert.match(comparison.prompt, /それぞれの対象制度/);
  assert.match(comparison.unresolved, /同じ場所/);
  assert.equal(Object.keys(RESEARCH_QUESTIONS).length, 5);
  assert.throws(() => buildEvidenceComparison("meaning", "wide", "wide"), /異なる2つ/);
  assert.throws(() => buildEvidenceComparison("unknown", "wide", "waiting"), /未定義/);
  assert.throws(() => buildEvidenceComparison("meaning", "wide", "made-up"), /未定義/);
  for (const question of Object.values(RESEARCH_QUESTIONS)) {
    assert.ok(question.title && question.prompt && question.unresolved);
  }
  assert.ok(!Object.hasOwn(comparison, "score"));
  assert.ok(!Object.hasOwn(comparison, "recommendation"));
  assert.ok(!Object.hasOwn(comparison, "route"));
});

test("現時点の開設と安全経路は未検証であり条件選択から結論を生成しない", () => {
  const opening = buildEvidenceComparison("opening", "waiting", "gsi");
  const route = buildEvidenceComparison("route", "wide", "flow");
  const hazard = buildEvidenceComparison("flood", "waiting", "gsi");
  assert.match(opening.unresolved, /現在利用可能とは判断できません/);
  assert.match(route.unresolved, /経路の安全性や所要時間を判断できません/);
  assert.match(hazard.unresolved, /UNKNOWN/);
  assert.match(buildEvidenceComparison("location", "waiting", "flow").unresolved, /A\/C/);
  assert.match(buildComparisonMemo("undecided", ["gsi"], {
    questionId: "opening", leftId: "waiting", rightId: "gsi",
  }), /この画面では未確定: .*現在利用可能とは判断できません/);
  assert.match(buildComparisonMemo("wide", []), /未確認の事項/);
  assert.throws(() => buildComparisonMemo("wide", [], {
    questionId: "opening", leftId: "wide", rightId: "wide",
  }));
});

test("画面は2資料の入力・違い・不明点の表示とモバイルの縦並びを持つ", async () => {
  const html = await readFile(new URL("../decision-lab.html", import.meta.url), "utf8");
  const js = await readFile(new URL("../src/decision-lab.js", import.meta.url), "utf8");
  const css = await readFile(new URL("../decision-lab.css", import.meta.url), "utf8");
  for (const id of ["researchQuestion", "leftSource", "rightSource", "compareWarning", "comparisonRoot"]) {
    assert.ok(html.includes('id="' + id + '"'));
  }
  assert.match(js, /buildEvidenceComparison\(comparison\.questionId, comparison\.leftId, comparison\.rightId\)/);
  assert.match(js, /comparisonRoot\.replaceChildren\(\)/);
  assert.match(js, /textContent = pair\.unresolved/);
  assert.match(js, /link\.rel = "noopener noreferrer"/);
  assert.match(css, /\.compare-columns\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(css, /@media\(max-width:680px\)\{\.compare-fields,\.compare-columns/);
  assert.doesNotMatch(js, /innerHTML|fetch\(|localStorage|sessionStorage|geolocation/);
});
