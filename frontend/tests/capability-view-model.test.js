import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCapabilityViewModel,
  collectEvidence,
  getCapabilityStatusMeta,
  safeHttpUrl,
} from "../src/capability-view-model.js";

function regionExport(overrides = {}) {
  return {
    region: { code: "DEMO-000", name: "UI確認用地域（架空）" },
    datasets: [
      {
        requirement_code: "shelter_location",
        evidence: [
          {
            source_name: "UIテスト用合成データ",
            source_url: null,
            fetched_at: "2026-09-29T00:00:00Z",
          },
        ],
      },
    ],
    capabilities: [
      {
        capability_code: "shelter_discovery",
        capability_name: "Shelter Discovery",
        status: "DEGRADED",
        dependency_results: [
          {
            requirement_code: "shelter_location",
            criticality: 3,
            status: "DEGRADED",
            reasons: ["表示確認用の理由"],
          },
        ],
        reasons: ["表示確認用の理由"],
        assessed_at: "2026-09-29T00:00:00Z",
        engine_version: "0.9",
      },
    ],
    meta: {
      schema_version: "0.9",
      generated_at: "2026-09-29T00:00:00Z",
    },
    ...overrides,
  };
}

test("Capabilityの全状態を異なる表示として扱う", () => {
  const statuses = ["FULL", "DEGRADED", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE"];
  const labels = statuses.map((status) => getCapabilityStatusMeta(status).label);
  const tones = statuses.map((status) => getCapabilityStatusMeta(status).tone);

  assert.equal(new Set(labels).size, statuses.length);
  assert.equal(new Set(tones).size, statuses.length);
  assert.notEqual(getCapabilityStatusMeta("UNKNOWN").label, getCapabilityStatusMeta("BLOCKED").label);
});

test("Capability状態はContractの値を再計算せず表示モデルへ渡す", () => {
  const payload = regionExport();
  payload.capabilities[0].status = "BLOCKED";

  const viewModel = buildCapabilityViewModel(payload);

  assert.equal(viewModel.statusCode, "BLOCKED");
  assert.equal(viewModel.statusLabel, "現在利用不可");
});

test("Evidenceは依存するrequirement_codeでのみ結び付ける", () => {
  const payload = regionExport({
    datasets: [
      ...regionExport().datasets,
      {
        requirement_code: "unrelated_requirement",
        evidence: [{ source_name: "別データ", fetched_at: "2026-09-29T00:00:00Z" }],
      },
    ],
  });

  const evidence = collectEvidence(payload, ["shelter_location"]);

  assert.equal(evidence.length, 1);
  assert.equal(evidence[0].sourceName, "UIテスト用合成データ");
});

test("nullのEvidence属性を架空の値で補完しない", () => {
  const viewModel = buildCapabilityViewModel(regionExport());

  assert.equal(viewModel.evidence[0].sourceUrl, null);
  assert.equal(viewModel.evidence[0].publisher, null);
  assert.equal(viewModel.evidence[0].publishedAt, null);
});

test("Evidenceの参照URLはhttpとhttpsだけを許可する", () => {
  assert.equal(safeHttpUrl("javascript:alert(1)"), null);
  assert.equal(safeHttpUrl("not a url"), null);
  assert.equal(safeHttpUrl("https://example.com/source"), "https://example.com/source");
});

test("CapabilityがないRegionExportは表示エラーにする", () => {
  assert.throws(
    () => buildCapabilityViewModel(regionExport({ capabilities: [] })),
    /表示できるCapabilityがありません/,
  );
});
