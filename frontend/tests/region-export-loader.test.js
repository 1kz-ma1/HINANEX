import test from "node:test";
import assert from "node:assert/strict";

import {
  MOCK_REGION_OPTIONS,
  getMockRegionExport,
} from "../mock/region-exports.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";

test("江戸川・新潟・名古屋の3地域を選択できる", () => {
  assert.deepEqual(
    MOCK_REGION_OPTIONS.map(({ key, label }) => ({ key, label })),
    [
      { key: "edogawa", label: "東京都江戸川区" },
      { key: "niigata", label: "新潟県新潟市" },
      { key: "nagoya", label: "愛知県名古屋市" },
    ],
  );
});

test("選択地域に応じて地域名・Capability・Gap・Recommendationが切り替わる", () => {
  const actual = MOCK_REGION_OPTIONS.map(({ key }) => {
    const viewModel = buildRegionExportViewModel(getMockRegionExport(key));
    return {
      key,
      regionName: viewModel.regionName,
      capability: viewModel.capabilities[0].statusCode,
      gapCount: viewModel.gaps.length,
      recommendationCount: viewModel.recommendations.length,
      evidenceCount: viewModel.evidence.length,
      isSynthetic: viewModel.isSynthetic,
    };
  });

  assert.deepEqual(actual, [
    {
      key: "edogawa",
      regionName: "東京都江戸川区（UI確認用仮データ）",
      capability: "FULL",
      gapCount: 0,
      recommendationCount: 0,
      evidenceCount: 1,
      isSynthetic: true,
    },
    {
      key: "niigata",
      regionName: "新潟県新潟市（UI確認用仮データ）",
      capability: "FULL",
      gapCount: 0,
      recommendationCount: 0,
      evidenceCount: 1,
      isSynthetic: true,
    },
    {
      key: "nagoya",
      regionName: "愛知県名古屋市（UI確認用仮データ）",
      capability: "BLOCKED",
      gapCount: 1,
      recommendationCount: 1,
      evidenceCount: 1,
      isSynthetic: true,
    },
  ]);
});

test("未定義の地域キーへ暗黙にfallbackしない", () => {
  assert.throws(() => getMockRegionExport("unknown"), RangeError);
});

test("取得したmockを変更しても次の地域選択へ影響しない", () => {
  const first = getMockRegionExport("edogawa");
  first.region.name = "変更済み";

  assert.equal(
    getMockRegionExport("edogawa").region.name,
    "東京都江戸川区（UI確認用仮データ）",
  );
});
