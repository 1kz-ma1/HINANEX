"use strict";
// Offline regression of the actual F01/F06 controllers, not a disaster-data test.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../gis/js");
const hazard = fs.readFileSync(path.join(root, "hazard_information.js"), "utf8");
const links = fs.readFileSync(path.join(root, "official_alert_links.js"), "utf8");
const cities = {
  "13123": ["江戸川区", "https://bosai.city.edogawa.tokyo.jp/"],
  "15100": ["新潟市", "https://www.city.niigata.lg.jp/kurashi/bosai/index.html"],
  "23100": ["名古屋市", "https://www.city.nagoya.jp/bousaiportal/index.html"]
};

function setup() {
  const names = ["hazardGuideOpen", "hazardGuideClose", "hazardGuidePanel",
    "hazardGuideRegion", "hazardGuideFlood", "hazardGuideStatus", "region",
    "officialFlood", "mapRasterBanner", "mapFloodRefreshStatus",
    "externalFloodTileNotice", "officialAlertsOpen", "officialAlertsClose",
    "officialAlertsPanel", "officialAlertsRegionName", "officialAlertsRegionNote",
    "officialAlertsLocalLink", "mapToolHazards", "mapToolHazardsSummary",
    "mapToolScene", "mapToolScenario", "mapToolMarks", "mapEvidencePanel",
    "mapEvidenceClose", "mapTourPanel", "mapTourClose", "mapSharePanel",
    "mapShareClose", "mapSettingsPanel", "mapSettingsClose", "outside"];
  const docHandlers = {};
  const windowHandlers = {};
  const elements = {};
  const document = {
    activeElement: null,
    getElementById(id) { return elements[id] || null; },
    addEventListener(type, handler) { (docHandlers[type] ||= []).push(handler); },
    emit(type, event) { for (const handler of docHandlers[type] || []) handler(event); }
  };
  for (const id of names) {
    const events = {};
    elements[id] = {
      id, events, dataset: {}, attributes: {}, href: "", textContent: "",
      value: id === "region" || id === "hazardGuideRegion" ? "13123" : "",
      checked: id === "officialFlood" || id === "hazardGuideFlood",
      hidden: ["hazardGuidePanel", "officialAlertsPanel", "externalFloodTileNotice",
        "mapEvidencePanel", "mapTourPanel", "mapSharePanel", "mapSettingsPanel"].includes(id),
      open: id === "mapToolHazards", focusCount: 0,
      addEventListener(type, fn) { (events[type] ||= []).push(fn); },
      setAttribute(key, val) { this.attributes[key] = String(val); },
      removeAttribute(key) { delete this.attributes[key]; if (key === "href") this.href = ""; },
      dispatchEvent(ev) { for (const fn of events[ev.type] || []) fn(ev); },
      focus() { this.focusCount++; document.activeElement = this; },
      click() {
        const ev = {type: "click", target: this};
        // Capturing document listeners run before the element click handler.
        document.emit("click", ev);
        this.dispatchEvent(ev);
      },
      contains(target) { return target === this; },
      querySelector(q) { return q === "summary" ? elements.mapToolHazardsSummary : null; }
    };
  }
  const window = {
    addEventListener(type, handler) { (windowHandlers[type] ||= []).push(handler); },
    emit(type) { for (const handler of windowHandlers[type] || []) handler(); }
  };
  // No fetch, GPS, storage, or network objects exist in this context.
  const context = {document, window, Event, console};
  vm.runInNewContext(hazard, context, {filename: "hazard_information.js"});
  vm.runInNewContext(links, context, {filename: "official_alert_links.js"});
  function change(id) { elements[id].dispatchEvent(new Event("change")); }
  function region(code) { elements.region.value = code; change("region"); }
  function esc() {
    let prevented = false;
    document.emit("keydown", {key: "Escape", preventDefault() { prevented = true; }});
    return prevented;
  }
  return {e: elements, document, window, change, region, esc};
}

let passed = 0;
function test(label, fn) {
  fn();
  passed++;
  console.log("PASS F01/F06 edge: " + label);
}

test("three regions switch repeatedly and link/selector always agree", () => {
  const {e, region} = setup();
  for (const code of ["15100", "23100", "13123", "15100", "13123", "23100"]) {
    region(code);
    assert.equal(e.hazardGuideRegion.value, code);
    assert.equal(e.officialAlertsLocalLink.href, cities[code][1]);
    assert.match(e.officialAlertsRegionName.textContent, new RegExp(cities[code][0]));
    assert.equal(e.officialAlertsLocalLink.hidden, false);
  }
});

test("unknown, empty, and prototype-like region codes never reuse an old city link", () => {
  const {e, region} = setup();
  for (const code of ["99999", "", "__proto__", "constructor", "15100x"]) {
    region("23100");
    region(code);
    assert.equal(e.hazardGuideRegion.value, "");
    assert.equal(e.officialAlertsLocalLink.hidden, true);
    assert.equal(e.officialAlertsLocalLink.href, "");
    assert.equal(e.officialAlertsLocalLink.textContent, "");
    assert.match(e.officialAlertsRegionNote.textContent, /未登録.*警報なし/);
  }
  region("13123");
  assert.equal(e.officialAlertsLocalLink.href, cities["13123"][1]);
});

test("F01 own selector reuses existing region change without creating positions", () => {
  const {e, change} = setup();
  let updates = 0;
  e.region.addEventListener("change", () => updates++);
  for (const code of ["15100", "23100", "13123"]) {
    e.hazardGuideRegion.value = code;
    change("hazardGuideRegion");
    assert.equal(e.region.value, code);
    assert.equal(e.officialAlertsLocalLink.href, cities[code][1]);
  }
  assert.equal(updates, 3);
  e.hazardGuideRegion.value = "unexpected";
  change("hazardGuideRegion");
  assert.equal(e.region.value, "13123");
  assert.equal(updates, 3);
});

test("F01 flood ON/OFF cycles and cross-region operations are deterministic", () => {
  const {e, region, change} = setup();
  let changes = 0;
  e.officialFlood.addEventListener("change", () => changes++);
  for (let i = 0; i < 4; i++) {
    region(i % 2 ? "23100" : "15100");
    e.hazardGuideFlood.checked = false;
    change("hazardGuideFlood");
    assert.equal(e.officialFlood.checked, false);
    assert.match(e.hazardGuideStatus.textContent, /非表示.*浸水なし/);
    e.hazardGuideFlood.checked = true;
    change("hazardGuideFlood");
    assert.equal(e.officialFlood.checked, true);
    assert.match(e.hazardGuideStatus.textContent, /全域取得.*確認済みではありません/);
  }
  assert.equal(changes, 8);
  change("hazardGuideFlood");
  assert.equal(changes, 8, "no redundant official controller events");
});

test("loading, partial and prior-failure states never assert flood safety", () => {
  const {e, change} = setup();
  for (const state of ["loading", "partial", ""] ) {
    e.mapFloodRefreshStatus.dataset.state = state;
    change("officialFlood");
    const msg = e.hazardGuideStatus.textContent;
    assert.match(msg, state === "loading" ? /更新中.*浸水なし/ :
      state === "partial" ? /取得失敗.*浸水なし/ : /全域取得.*確認済みではありません/);
  }
  e.mapRasterBanner.dataset.partial = "true";
  change("officialFlood");
  assert.match(e.hazardGuideStatus.textContent, /取得失敗/);
  e.mapRasterBanner.dataset.partial = "false";
  e.externalFloodTileNotice.hidden = false;
  change("officialFlood");
  assert.match(e.hazardGuideStatus.textContent, /過去の閲覧範囲/);
  e.officialFlood.checked = false;
  change("officialFlood");
  assert.match(e.hazardGuideStatus.textContent, /非表示.*浸水なし/);
});

test("F01 Escape restores visible summary and ARIA state", () => {
  const {e, esc} = setup();
  e.hazardGuideOpen.click();
  assert.equal(e.hazardGuidePanel.hidden, false);
  assert.equal(e.hazardGuideOpen.attributes["aria-expanded"], "true");
  assert.equal(e.hazardGuideRegion.focusCount > 0, true);
  assert.equal(esc(), true);
  assert.equal(e.hazardGuidePanel.hidden, true);
  assert.equal(e.hazardGuideOpen.attributes["aria-expanded"], "false");
  assert.equal(e.mapToolHazardsSummary.focusCount > 0, true);
});

test("F06 Escape restores visible summary and ARIA state", () => {
  const {e, esc} = setup();
  e.officialAlertsOpen.click();
  assert.equal(e.officialAlertsPanel.hidden, false);
  assert.equal(e.officialAlertsOpen.attributes["aria-expanded"], "true");
  assert.equal(e.officialAlertsClose.focusCount > 0, true);
  assert.equal(esc(), true);
  assert.equal(e.officialAlertsPanel.hidden, true);
  assert.equal(e.officialAlertsOpen.attributes["aria-expanded"], "false");
  assert.equal(e.mapToolHazardsSummary.focusCount > 0, true);
});

test("outside click closes both types without altering flood toggle", () => {
  const {e, document} = setup();
  for (const [button, panel] of [["hazardGuideOpen", "hazardGuidePanel"],
    ["officialAlertsOpen", "officialAlertsPanel"]]) {
    e[button].click();
    assert.equal(e[panel].hidden, false);
    document.emit("click", {target: e.outside});
    assert.equal(e[panel].hidden, true);
    assert.equal(e[button].attributes["aria-expanded"], "false");
    assert.equal(e.officialFlood.checked, true);
  }
});

test("F01 to F06 and F06 to F01 never stack in normal click path", () => {
  const {e} = setup();
  for (const pair of [["hazardGuideOpen", "officialAlertsOpen"],
    ["officialAlertsOpen", "hazardGuideOpen"]]) {
    e[pair[0]].click();
    e[pair[1]].click();
    assert.equal(e[pair[0] === "hazardGuideOpen" ? "hazardGuidePanel" : "officialAlertsPanel"].hidden, true);
    assert.equal(e[pair[1] === "hazardGuideOpen" ? "hazardGuidePanel" : "officialAlertsPanel"].hidden, false);
    e[pair[1] === "hazardGuideOpen" ? "hazardGuideClose" : "officialAlertsClose"].click();
  }
});

test("pageshow restores F06 link after history-driven region update", () => {
  const {e, window} = setup();
  e.region.value = "15100";
  window.emit("pageshow");
  assert.equal(e.officialAlertsLocalLink.href, cities["15100"][1]);
  e.region.value = "";
  window.emit("pageshow");
  assert.equal(e.officialAlertsLocalLink.hidden, true);
});

test("F06 uses static HTTPS destinations without network/status inference", () => {
  for (const [code, pair] of Object.entries(cities)) {
    assert.match(pair[1], /^https:\/\//);
    assert.ok(links.includes('"' + code + '"'));
    assert.ok(links.includes(pair[1]));
  }
  assert.doesNotMatch(links, /\bfetch\s*\(|XMLHttpRequest|geolocation|localStorage|setInterval/);
  assert.doesNotMatch(hazard, /\bfetch\s*\(|geolocation|localStorage/);
});

console.log("F01/F06 edge cases: " + passed + " offline scenarios PASS");
