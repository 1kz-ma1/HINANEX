import test from "node:test";
import assert from "node:assert/strict";

import {
  REGION_SOURCES,
  assertRegionMatches,
  getPayloadRegionCode,
  getRegionSource,
} from "../src/region-export-source.js";

test("3地域のD RegionExport出力先を固定する", () => {
  assert.equal(REGION_SOURCES["13123"].url, "../pipeline/data/output/edogawa.json");
  assert.equal(REGION_SOURCES["15100"].url, "../pipeline/data/output/niigata.json");
  assert.equal(REGION_SOURCES["23100"].url, "../pipeline/data/output/nagoya.json");
});

test("未対応地域は暗黙に別地域へfallbackしない", () => {
  assert.throws(() => getRegionSource("99999"), /未対応の地域コード/);
  assert.throws(
    () => getPayloadRegionCode({ region: { code: "99999" } }),
    /未対応の地域コード/,
  );
});

test("選択地域とRegionExportの不一致を拒否する", () => {
  const payload = { region: { code: "15100" } };
  assert.throws(() => assertRegionMatches(payload, "13123"), /一致しません/);
  assert.equal(assertRegionMatches(payload, "15100"), "15100");
});

test("RegionExport.region.code欠損を推測しない", () => {
  assert.throws(() => getPayloadRegionCode({ region: {} }), /region.code/);
});
