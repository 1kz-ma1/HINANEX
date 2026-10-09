import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { buildAnalysisSummary, isSelectedRegion } from "../src/presentation-view-model.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";
import { buildGisRegionUrl } from "../src/region-export-source.js";
import { regionExport } from "./fixtures.js";

test("分析サマリーはRegionExport由来のstatusと件数を再計算せず保持する", () => {
  const payload = regionExport();
  payload.capabilities[0].status = "BLOCKED";
  payload.meta.gap_count = 2;
  payload.meta.recommendation_count = 1;

  const summary = buildAnalysisSummary(buildRegionExportViewModel(payload));

  assert.equal(summary.capabilityStatusCode, "BLOCKED");
  assert.equal(summary.capabilityStatusLabel, "現在利用不可");
  assert.match(summary.recordCountLabel, /12件/);
  assert.equal(summary.gapCount, "2");
  assert.equal(summary.recommendationCount, "1");
  assert.match(summary.scopeNote, /16区別の屋内施設データ/);
});

test("3地域のFrontendからGISへのURLを地域コード付きで生成する", () => {
  assert.equal(buildGisRegionUrl("13123"), "/gis/gis/?region=13123");
  assert.equal(buildGisRegionUrl("15100"), "/gis/gis/?region=15100");
  assert.equal(buildGisRegionUrl("23100"), "/gis/gis/?region=23100");
  assert.throws(() => buildGisRegionUrl("99999"), /未対応の地域コード/);
});

test("地域ボタンのactive判定は選択コードだけをtrueにする", () => {
  assert.equal(isSelectedRegion("15100", "13123"), false);
  assert.equal(isSelectedRegion("15100", "15100"), true);
  assert.equal(isSelectedRegion("15100", "23100"), false);
});

test("通常UIに3地域ボタンと折りたたみ設定を用意する", async () => {
  const index = await readFile(new URL("../index.html", import.meta.url), "utf8");

  assert.match(index, /data-region-code="13123"[^>]*aria-pressed="true"/);
  assert.match(index, /data-region-code="15100"[^>]*aria-pressed="false"/);
  assert.match(index, /data-region-code="23100"[^>]*aria-pressed="false"/);
  assert.match(index, /<details class="developer-settings" id="developerSettings">/);
  assert.match(index, /<div id="summaryRoot"/);
  assert.doesNotMatch(index, /B \/ Frontend/);
});

test("Assessmentは0点と未評価の違いを説明し、2グループをdetailsで生成する", async () => {
  const app = await readFile(new URL("../src/app.js", import.meta.url), "utf8");

  assert.match(app, /0 \/ 4は評価結果として0/);
  assert.match(app, /未評価はscore=null/);
  assert.match(app, /return element\("details", \{/);
  assert.match(app, /"データ品質"/);
  assert.match(app, /"アプリ利用適性"/);
});

test("Flood Scenarioは常設領域でLoading, empty, error, unsupportedを区別する", async () => {
  const [index, app] = await Promise.all([
    readFile(new URL("../index.html", import.meta.url), "utf8"),
    readFile(new URL("../src/app.js", import.meta.url), "utf8"),
  ]);

  assert.match(index, /id="floodScenario" aria-labelledby="floodScenarioTitle">/);
  assert.match(index, /id="floodScenarioRoot"[^>]*aria-live="polite"/);
  assert.match(app, /Scenario結果を読み込み中/);
  assert.match(app, /Scenario結果なし/);
  assert.match(app, /Scenario結果の取得に失敗/);
  assert.match(app, /未対応のScenario Contract/);
  assert.match(app, /候補が0件という意味ではありません/);
});

test("Scenario施設結果はkeyboard対応detailsと日本語statusで根拠を開ける", async () => {
  const app = await readFile(new URL("../src/app.js", import.meta.url), "utf8");

  assert.match(app, /element\("details", \{/);
  assert.match(app, /element\("summary", \{ text: "根拠を見る" \}\)/);
  assert.match(app, /statusBadge\(row\.statusLabel, row\.statusTone\)/);
  assert.match(app, /attributes: \{ type: "button" \}/);
  assert.doesNotMatch(app, /unknownCount/);
  assert.doesNotMatch(app, /candidateCount/);
  assert.doesNotMatch(app, /excludedCount/);
  assert.match(app, /buildGisRegionUrl\(context\.regionCode\)/);
  assert.doesNotMatch(app, /buildGisRegionUrl\([^)]*facility/i);
});

test("Scenario UIはmobileで1列化し長い根拠を折り返す", async () => {
  const styles = await readFile(new URL("../styles.css", import.meta.url), "utf8");

  assert.match(styles, /@media \(max-width: 620px\)/);
  assert.match(styles, /\.scenario-facts \{ grid-template-columns: 1fr; \}/);
  assert.match(styles, /\.scenario-root > \*[\s\S]*min-width: 0;/);
  assert.match(styles, /\.scenario-source-link a,[\s\S]*overflow-wrap: anywhere;/);
  assert.match(styles, /\.scenario-evidence > summary:focus-visible/);
});
