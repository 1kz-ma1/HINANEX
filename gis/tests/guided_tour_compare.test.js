"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "gis/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "gis/css/map_first.css"), "utf8");
const script = fs.readFileSync(path.join(root, "gis/js/guided_tour.js"), "utf8");
const codes = ["13123", "15100", "23100"];

function mount(focus = async code => ({
  state: code === "23100" ? "unlocated" : "mapped",
  total: code === "13123" ? 152 : code === "15100" ? 566 : 1602,
  mapped: code === "13123" ? 152 : code === "15100" ? 566 : 0
})) {
  class Element {
    constructor(name) {
      this.name = name;
      this.hidden = name === "mapTourPanel" || name === "mapSettingsPanel";
      this.disabled = false;
      this.textContent = "";
      this.attributes = new Map();
      this.listeners = new Map();
      this.open = false;
    }
    addEventListener(kind, listener) { this.listeners.set(kind, listener); }
    setAttribute(key, value) { this.attributes.set(key, value); }
    getAttribute(key) { return this.attributes.get(key); }
    click() { this.listeners.get("click")?.({ target: this }); }
    fire(type, extra={}) { this.listeners.get(type)?.({ target: this, ...extra }); }
  }
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  const documentListeners = new Map();
  const timers = new Map();
  let nextTimer = 0;
  const calls = { begin: 0, halt: 0, end: [], focus: [] };
  const api = {
    begin() { calls.begin++; },
    halt() { calls.halt++; },
    end(restore) { calls.end.push(restore); },
    focus(code, animate, first) {
      calls.focus.push({ code, animate, first });
      return focus(code);
    }
  };
  const window = {
    HINANEX_PRESENTATION_TOUR: api,
    matchMedia: () => ({ matches: true }),
    setTimeout(fn, delay) {
      assert.equal(delay, 6500);
      const id = ++nextTimer;
      timers.set(id, fn);
      return id;
    },
    clearTimeout(id) { timers.delete(id); }
  };
  vm.runInNewContext(script, {
    document: { getElementById: get, addEventListener(k, f) {documentListeners.set(k, f);} },
    window
  }, { timeout: 2000 });
  return {
    get, calls,
    nextTimer() {
      const entry = timers.entries().next().value;
      assert.ok(entry, "expected scheduled tour advance");
      timers.delete(entry[0]);
      entry[1]();
    },
    timers,
    key(key) {
      let prevented = false;
      documentListeners.get("keydown")?.({ key, preventDefault() {prevented = true;} });
      return prevented;
    }
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test("three distinct labeled cases and safe comparison exist in responsive GIS panel", () => {
  for (const code of codes) {
    assert.match(html, new RegExp('id="mapTourCase' + code + '"'));
    assert.match(html, new RegExp('id="mapTourCompare' + code + '"'));
  }
  assert.match(html, /id="mapTourStart"[^>]*>3地域を連続再生/);
  assert.match(html, /js\/guided_tour[.]js[?]v=interactive-presenter-20261014-v1/);
  assert.match(html, /css\/map_first[.]css[?]v=audience-sticky-cta-20261021-v1/);
  assert.match(html, /未取得は0件ではありません/);
  assert.match(css, /\.map-tour-case button\[aria-pressed="true"\]/);
  assert.match(css, /@media\(max-width:680px\)/);
});

test("one selected case is replayable without filling unrelated results or inventing coordinates", async () => {
  const a = mount();
  a.get("mapTourOpen").click();
  assert.equal(a.get("mapTourPanel").hidden, false);
  a.get("mapTourCase23100").click();
  await flush();
  assert.deepEqual(a.calls.focus.map(x => x.code), ["23100"]);
  assert.equal(a.get("mapTourProgress").textContent, "1 / 1｜再生中");
  assert.match(a.get("mapTourCompare23100").textContent, /取得 1602件.*元座標あり 0件/);
  assert.equal(a.get("mapTourCompare13123").textContent, "未再生");
  assert.equal(a.get("mapTourCompare15100").textContent, "未再生");
  assert.match(a.get("mapTourSourceStatus").textContent, /地図は前の位置のまま/);
  assert.equal(a.get("mapTourNext").disabled, true);
  a.nextTimer();
  assert.equal(a.get("mapTourProgress").textContent, "1 / 1｜完了");
  a.get("mapTourCase23100").click();
  await flush();
  assert.equal(a.calls.focus.length, 2, "individual case can be replayed");
  assert.equal(a.calls.end.length, 1, "camera restored before replay");
});

test("all-case comparison runs in order, preserves real D counts and remains non-safety", async () => {
  const a = mount();
  a.get("mapTourStart").click();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent, "1 / 3｜再生中");
  assert.equal(a.get("mapTourCase13123").getAttribute("aria-pressed"), "true");
  a.nextTimer();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent, "2 / 3｜再生中");
  a.nextTimer();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent, "3 / 3｜再生中");
  a.nextTimer();
  assert.equal(a.get("mapTourProgress").textContent, "3 / 3｜完了");
  assert.deepEqual(a.calls.focus.map(x => x.code), codes);
  assert.match(a.get("mapTourCompare13123").textContent, /152件/);
  assert.match(a.get("mapTourCompare15100").textContent, /566件/);
  assert.match(a.get("mapTourCompare23100").textContent, /1602件/);
  assert.match(a.get("mapTourSourceStatus").textContent, /安全性や開設状況は判定していません/);
  assert.equal(a.timers.size, 0);
});

test("switching cases cancels delayed stale D results and marks interrupted fetch UNKNOWN", async () => {
  let resolveOld;
  const a = mount(code => code === "13123"
    ? new Promise(resolve => { resolveOld = resolve; })
    : Promise.resolve({ state: "unlocated", total: 12, mapped: 0 }));
  a.get("mapTourCase13123").click();
  assert.match(a.get("mapTourCompare13123").textContent, /取得中/);
  a.get("mapTourCase23100").click();
  await flush();
  resolveOld({ state: "mapped", total: 999, mapped: 999 });
  await flush();
  assert.equal(a.get("mapTourCompare13123").textContent, "取得中断・未確認");
  assert.match(a.get("mapTourCompare23100").textContent, /取得 12件/);
  assert.ok(!a.get("mapTourSourceStatus").textContent.includes("999"));
  assert.equal(a.calls.end.length, 1);
});

test("failed D fetch, manual pause, resume and close never infer no facilities", async () => {
  const a = mount(async () => { throw new Error("HTTP 503"); });
  a.get("mapTourOpen").click();
  a.get("mapTourCase15100").click();
  await flush();
  assert.match(a.get("mapTourCompare15100").textContent, /未取得・未確認/);
  assert.match(a.get("mapTourSourceStatus").textContent, /施設が存在しないという意味ではありません/);
  a.get("mapTourPause").click();
  assert.match(a.get("mapTourProgress").textContent, /一時停止/);
  assert.equal(a.timers.size, 0);
  a.get("mapTourPause").click();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent, "1 / 1｜再生中");
  assert.equal(a.key("Escape"), true); // open presenter sheet consumes Escape
  assert.equal(a.get("mapTourPanel").hidden, true);
  assert.equal(a.timers.size, 0);
  assert.equal(a.calls.end.at(-1), true);
});

test("pause while pending cancels stale result, next step is manually selectable", async () => {
  let release;
  const a = mount(code => code === "13123" ?
    new Promise(r => { release = r; }) :
    Promise.resolve({state:"mapped",total:2,mapped:1}));
  a.get("mapTourStart").click();
  a.get("mapTourPause").click();
  assert.equal(a.get("mapTourCompare13123").textContent, "取得中断・未確認");
  release({ state:"mapped",total:700,mapped:700 });
  await flush();
  assert.equal(a.get("mapTourCompare13123").textContent, "取得中断・未確認");
  a.get("mapTourNext").click();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent, "2 / 3｜再生中");
  assert.match(a.get("mapTourCompare15100").textContent, /取得 2件/);
  assert.ok(a.calls.halt >= 2);
});

test("manual pan, wheel and toolbar interaction continue the guided tour", async () => {
  const a=mount();
  a.get("mapTourOpen").click();
  a.get("mapTourStart").click();
  await flush();
  assert.equal(a.timers.size,1);
  a.get("map").fire("wheel");
  a.get("map").fire("pointerdown");
  a.get("mapToolScene").open=true;
  a.get("mapToolScene").fire("toggle");
  assert.equal(a.timers.size,1,"the step's clock keeps running");
  assert.equal(a.get("mapTourPanel").hidden,false);
  assert.equal(a.get("mapTourProgress").textContent,"1 / 3｜再生中");
  a.nextTimer();
  await flush();
  assert.equal(a.get("mapTourProgress").textContent,"2 / 3｜再生中");
  a.get("mapTourStop").click();
  assert.equal(a.calls.end.at(-1),false,
    "manual camera adjustments must not be reverted on stop");
});

test("on-map evidence player replaces cross-tab link without altering three-region preview", () => {
  assert.match(html, /id="mapHistoricalEvidenceDemo" type="button"/);
  assert.match(html, /aria-controls="mapEvidenceReplayPanel"/);
  assert.match(html, /id="mapEvidenceReplayPanel"/);
  assert.match(html, /地図上で3つの検証パターンを再生/);
  assert.match(html, /実災害の予測一致・不一致は未検証/);
  assert.match(html, /補助：従来の3地域データ閲覧ツアー/);
  assert.match(html, /js\/evidence_replay[.]js[?]v=spatial-evidence-20261014-v2/);
  assert.match(html, /css\/evidence_replay[.]css[?]v=spatial-evidence-20261014-v2/);
  assert.match(html, /id="mapTourCase23100"/);
});
