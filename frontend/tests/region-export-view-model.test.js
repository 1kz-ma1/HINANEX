import test from "node:test";
import assert from "node:assert/strict";

import {
  buildAssessmentViewModel,
  buildMetricViewModel,
  buildRecordCountPresentation,
  getDiscoveryStatusMeta,
} from "../src/assessment-view-model.js";
import { buildCapabilityViewModel } from "../src/capability-view-model.js";
import { collectEvidence } from "../src/evidence-view-model.js";
import { buildGapViewModels } from "../src/gap-view-model.js";
import { buildRecommendationViewModels } from "../src/recommendation-view-model.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";
import { metric, regionExport } from "./fixtures.js";

test("MetricScoreの4、0、nullを異なる表示へ変換する", () => {
  const four = buildMetricViewModel("completeness", "完全性", metric(4));
  const zero = buildMetricViewModel("coverage", "網羅性", metric(0));
  const unassessed = buildMetricViewModel("timeliness", "適時性", metric(null, "情報不足"));

  assert.equal(four.scoreLabel, "4 / 4");
  assert.equal(zero.scoreLabel, "0 / 4");
  assert.equal(zero.isUnassessed, false);
  assert.equal(unassessed.score, null);
  assert.equal(unassessed.scoreLabel, "未評価");
  assert.equal(unassessed.reason, "情報不足");
});

test("Data QualityとApplication Readinessを共通Metric構造で保持する", () => {
  const viewModel = buildAssessmentViewModel(regionExport().assessments[0]);

  assert.equal(viewModel.dataQuality.length, 7);
  assert.equal(viewModel.applicationReadiness.length, 8);
  assert.equal(viewModel.dataQuality.find((item) => item.key === "coverage").score, 0);
  assert.equal(
    viewModel.applicationReadiness.find((item) => item.key === "semantic_fitness").score,
    null,
  );
});

test("CapabilityのFULL、BLOCKED、UNKNOWNを再判定せず保持する", () => {
  const statuses = ["FULL", "BLOCKED", "UNKNOWN"];
  const rendered = statuses.map((status) => {
    const payload = regionExport();
    payload.capabilities[0].status = status;
    return buildCapabilityViewModel(payload).statusCode;
  });

  assert.deepEqual(rendered, statuses);
});

test("Shelter Discovery FULLは位置ベース探索に意味を限定する", () => {
  const viewModel = buildCapabilityViewModel(regionExport());

  assert.match(viewModel.statusDescription, /位置ベース探索/);
  assert.match(viewModel.scopeNote, /災害別安全性/);
  assert.match(viewModel.scopeNote, /リアルタイム利用可否/);
});

test("Gapの改善候補と追加調査を区別する", () => {
  const gaps = buildGapViewModels(regionExport());

  assert.equal(gaps[0].kindLabel, "改善候補");
  assert.equal(gaps[1].kindLabel, "追加調査");
  assert.match(gaps[1].kindDescription, /自治体側の不足を断定/);
});

test("GapのseverityとRecommendationのpriorityを別の表示名にする", () => {
  const gap = buildGapViewModels(regionExport())[0];
  const recommendation = buildRecommendationViewModels(regionExport())[0];

  assert.equal(gap.severityDisplayLabel, "重要度");
  assert.equal(recommendation.priorityDisplayLabel, "優先度");
});

test("Recommendationの複数actionsを失わない", () => {
  const recommendations = buildRecommendationViewModels(regionExport());

  assert.deepEqual(recommendations[0].actions, ["action 1", "action 2"]);
  assert.equal(recommendations[0].typeLabel, "追加調査");
});

test("published_at=nullでもEvidenceを表示モデルへ変換できる", () => {
  const evidence = collectEvidence(regionExport());

  assert.equal(evidence.length, 1);
  assert.equal(evidence[0].publishedAt, null);
  assert.equal(evidence[0].notes, "公開日を推測しない表示の確認用です。");
});

test("GapとRecommendationが空でも地域詳細ViewModelを構築できる", () => {
  const viewModel = buildRegionExportViewModel(
    regionExport({
      gaps: [],
      recommendations: [],
      meta: {
        ...regionExport().meta,
        gap_count: 0,
        recommendation_count: 0,
      },
    }),
  );

  assert.deepEqual(viewModel.gaps, []);
  assert.deepEqual(viewModel.recommendations, []);
});

test("NOT_FOUNDを自治体の未公開と断定しない", () => {
  const status = getDiscoveryStatusMeta("NOT_FOUND");

  assert.equal(status.label, "現在の取得経路では未確認");
  assert.match(status.description, /自治体が未公開という意味ではありません/);
});

test("名古屋市のrecord_countを全避難関連施設数として扱わない", () => {
  const viewModel = buildAssessmentViewModel(regionExport().assessments[0]);

  assert.match(viewModel.recordCountLabel, /HINANEXの現在の取得結果/);
  assert.match(viewModel.scopeNote, /16区別の屋内施設/);
  assert.match(viewModel.scopeNote, /屋外施設は含まず/);
});


test("非取得状態のrecord_count=0を実施設0件として表示しない", () => {
  const statuses = [
    "NOT_MACHINE_READABLE",
    "ACCESS_RESTRICTED",
    "NOT_FOUND",
    "UNKNOWN",
  ];

  for (const status of statuses) {
    const presentation = buildRecordCountPresentation(status, 0);
    assert.equal(presentation.label, "件数を確認できません", status);
    assert.match(presentation.note, /実施設が0件という意味ではありません/, status);
    assert.doesNotMatch(presentation.label, /0件/, status);
  }
});

test("対象外と取得済みの件数表示を区別する", () => {
  assert.equal(
    buildRecordCountPresentation("NOT_APPLICABLE", 0).label,
    "件数表示の対象外",
  );
  assert.equal(
    buildRecordCountPresentation("AVAILABLE", 0).label,
    "HINANEXの現在の取得結果：0件",
  );
});
