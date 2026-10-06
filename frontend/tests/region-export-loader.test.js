import test from "node:test";
import assert from "node:assert/strict";

import {
  createRegionExportController,
  getRegionExportConfig,
} from "../src/region-export-loader.js";
import { buildRegionExportViewModel } from "../src/region-export-view-model.js";
import { regionExport } from "./fixtures.js";

function response(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return structuredClone(payload);
    },
  };
}

function payloadFor(code, name) {
  const payload = regionExport();
  payload.region = { code, name };
  for (const assessment of payload.assessments) {
    assessment.region_code = code;
    assessment.region_name = name;
  }
  for (const capability of payload.capabilities) {
    capability.region_code = code;
    capability.region_name = name;
  }
  return payload;
}

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test("3地域をpipeline/data/outputの固定URLへ対応付ける", () => {
  assert.equal(getRegionExportConfig("edogawa").url, "../pipeline/data/output/edogawa.json");
  assert.equal(getRegionExportConfig("niigata").url, "../pipeline/data/output/niigata.json");
  assert.equal(getRegionExportConfig("nagoya").url, "../pipeline/data/output/nagoya.json");
  assert.throws(() => getRegionExportConfig("unknown"), RangeError);
});

test("江戸川区から新潟市、名古屋市へ順番に切り替えられる", async () => {
  const fixtures = new Map([
    ["../pipeline/data/output/edogawa.json", payloadFor("13123", "東京都江戸川区")],
    ["../pipeline/data/output/niigata.json", payloadFor("15100", "新潟県新潟市")],
    ["../pipeline/data/output/nagoya.json", payloadFor("23100", "愛知県名古屋市")],
  ]);
  const requestedUrls = [];
  const renderedNames = [];
  const controller = createRegionExportController({
    async fetchImpl(url) {
      requestedUrls.push(url);
      return response(fixtures.get(url));
    },
    onSuccess(payload) {
      renderedNames.push(buildRegionExportViewModel(payload).regionName);
    },
  });

  await controller.selectRegion("edogawa");
  await controller.selectRegion("niigata");
  await controller.selectRegion("nagoya");

  assert.deepEqual(requestedUrls, [...fixtures.keys()]);
  assert.deepEqual(renderedNames, ["東京都江戸川区", "新潟県新潟市", "愛知県名古屋市"]);
});

test("後から完了した旧地域の結果で現在の表示を上書きしない", async () => {
  const edogawa = deferred();
  const niigata = deferred();
  const renderedNames = [];
  const controller = createRegionExportController({
    fetchImpl(url) {
      return url.includes("edogawa") ? edogawa.promise : niigata.promise;
    },
    onSuccess(payload) {
      renderedNames.push(payload.region.name);
    },
  });

  const oldRequest = controller.selectRegion("edogawa");
  const currentRequest = controller.selectRegion("niigata");
  niigata.resolve(response(payloadFor("15100", "新潟県新潟市")));
  await currentRequest;
  edogawa.resolve(response(payloadFor("13123", "東京都江戸川区")));
  const oldResult = await oldRequest;

  assert.deepEqual(renderedNames, ["新潟県新潟市"]);
  assert.equal(oldResult.status, "stale");
});

test("読み込み開始と失敗時に旧地域の表示を残さない", async () => {
  let visibleRegion = "東京都江戸川区";
  let errorMessage = null;
  const controller = createRegionExportController({
    async fetchImpl() {
      return response({}, { ok: false, status: 404 });
    },
    onLoading() {
      visibleRegion = null;
      errorMessage = null;
    },
    onError(error) {
      visibleRegion = null;
      errorMessage = error.message;
    },
  });

  const result = await controller.selectRegion("niigata");

  assert.equal(result.status, "error");
  assert.equal(visibleRegion, null);
  assert.match(errorMessage, /HTTP 404/);
});
