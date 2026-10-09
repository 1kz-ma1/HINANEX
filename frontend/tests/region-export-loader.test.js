import test from "node:test";
import assert from "node:assert/strict";

import { createRegionExportController } from "../src/region-export-loader.js";

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
  return { region: { code, name } };
}

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test("江戸川・新潟・名古屋をD runtime URLから順番に取得する", async () => {
  const fixtures = new Map([
    ["../pipeline/data/output/edogawa.json", payloadFor("13123", "東京都江戸川区")],
    ["../pipeline/data/output/niigata.json", payloadFor("15100", "新潟県新潟市")],
    ["../pipeline/data/output/nagoya.json", payloadFor("23100", "愛知県名古屋市")],
  ]);
  const requested = [];
  const rendered = [];
  const controller = createRegionExportController({
    async fetchImpl(url) {
      requested.push(url);
      return response(fixtures.get(url));
    },
    onSuccess(payload) {
      rendered.push(payload.region.code);
    },
  });

  await controller.selectRegion("13123");
  await controller.selectRegion("15100");
  await controller.selectRegion("23100");

  assert.deepEqual(requested, [...fixtures.keys()]);
  assert.deepEqual(rendered, ["13123", "15100", "23100"]);
});

test("後から完了した旧地域の結果で現在表示を上書きしない", async () => {
  const edogawa = deferred();
  const niigata = deferred();
  const rendered = [];
  const controller = createRegionExportController({
    fetchImpl(url) {
      return url.includes("edogawa") ? edogawa.promise : niigata.promise;
    },
    onSuccess(payload) {
      rendered.push(payload.region.code);
    },
  });

  const oldRequest = controller.selectRegion("13123");
  const currentRequest = controller.selectRegion("15100");
  niigata.resolve(response(payloadFor("15100", "新潟県新潟市")));
  await currentRequest;
  edogawa.resolve(response(payloadFor("13123", "東京都江戸川区")));
  const oldResult = await oldRequest;

  assert.deepEqual(rendered, ["15100"]);
  assert.equal(oldResult.status, "stale");
});

test("選択地域と取得JSONのregion.code不一致をerrorにする", async () => {
  let errorMessage = null;
  const controller = createRegionExportController({
    async fetchImpl() {
      return response(payloadFor("15100", "新潟県新潟市"));
    },
    onError(error) {
      errorMessage = error.message;
    },
  });

  const result = await controller.selectRegion("13123");

  assert.equal(result.status, "error");
  assert.match(errorMessage, /一致しません/);
});

test("HTTP error時にerror callbackへ渡す", async () => {
  let errorMessage = null;
  const controller = createRegionExportController({
    async fetchImpl() {
      return response({}, { ok: false, status: 404 });
    },
    onError(error) {
      errorMessage = error.message;
    },
  });

  const result = await controller.selectRegion("23100");

  assert.equal(result.status, "error");
  assert.match(errorMessage, /HTTP 404/);
});

test("fetch失敗時はloading callbackで旧Scenario表示を先に消去する", async () => {
  let visibleScenarioRegion = "13123";
  const events = [];
  const controller = createRegionExportController({
    async fetchImpl() {
      return response({}, { ok: false, status: 503 });
    },
    onLoading(source) {
      visibleScenarioRegion = null;
      events.push(`clear:${source.code}`);
    },
    onError(_error, source) {
      events.push(`error:${source.code}`);
    },
  });

  const result = await controller.selectRegion("15100");

  assert.equal(result.status, "error");
  assert.equal(visibleScenarioRegion, null);
  assert.deepEqual(events, ["clear:15100", "error:15100"]);
});
