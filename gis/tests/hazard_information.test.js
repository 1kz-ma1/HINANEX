"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../gis/index.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "../gis/css/map_first.css"), "utf8");
const script = fs.readFileSync(path.join(__dirname, "../gis/js/hazard_information.js"), "utf8");
for (const name of ["hazardGuideOpen", "hazardGuideClose", "hazardGuidePanel",
  "hazardGuideRegion", "hazardGuideFlood", "hazardGuideStatus"]) {
  assert.equal((html.match(new RegExp('id="' + name + '"', "g")) || []).length, 1,
    "F01 control must exist exactly once: " + name);
}
assert.match(html, /js\/hazard_information\.js\?v=f01-flood-20261104-v1/);
assert.match(css, /\.hazard-guide-panel\[hidden\]\{display:none\}/);
assert.match(html, /disaportal\.gsi\.go\.jp/);
assert.match(html, /施設を選択せずに/);
assert.match(html, /aria-label="この洪水画像で確認できる情報の範囲"/);
assert.match(html, /元図面の作成年・改訂日を特定できません/);
assert.match(html, /選択した地域の全域にデータが掲載され/);
assert.match(html, /表示設定・通信上の取得状況と、公的データの対象範囲・最新性は別/);

assert.doesNotMatch(script, /geolocation|localStorage|fetch\s*\(/);

function element(name) {
  return {
    id: name, hidden: name === "hazardGuidePanel" || name === "externalFloodTileNotice",
    checked: name === "officialFlood", value: name === "region" ? "13123" : "",
    open: name === "mapToolHazards", textContent: "", dataset: {}, events: {},
    attributes: {}, focusCount: 0, clickCount: 0,
    addEventListener(type, fn) { (this.events[type] ||= []).push(fn); },
    dispatchEvent(event) {
      for (const fn of this.events[event.type] || []) fn(event);
      return true;
    },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    focus() { this.focusCount++; },
    click() {
      this.clickCount++;
      this.dispatchEvent({type: "click", target: this});
    },
    contains(target) { return target === this; }
  };
}
const names = ["hazardGuideOpen", "hazardGuideClose", "hazardGuidePanel",
  "hazardGuideRegion", "hazardGuideFlood", "hazardGuideStatus",
  "region", "officialFlood", "mapRasterBanner", "mapFloodRefreshStatus",
  "externalFloodTileNotice", "mapToolScene", "mapToolScenario",
  "mapToolMarks", "mapToolHazards",
  "mapEvidencePanel", "mapTourPanel", "mapSharePanel", "mapSettingsPanel"];
const nodes = Object.fromEntries(names.map(n => [n, element(n)]));
const document = {
  events: {},
  getElementById(name) { return nodes[name] || null; },
  addEventListener(type, fn) { (this.events[type] ||= []).push(fn); },
  emit(type, event) { for (const fn of this.events[type] || []) fn(event); }
};
const ctx = {document, Event, console};
vm.createContext(ctx);
vm.runInContext(script, ctx, {filename: "hazard_information.js"});

assert.equal(nodes.hazardGuidePanel.hidden, true);
nodes.hazardGuideOpen.click();
assert.equal(nodes.hazardGuidePanel.hidden, false);
assert.equal(nodes.hazardGuideOpen.attributes["aria-expanded"], "true");
assert.equal(nodes.hazardGuideRegion.value, "13123");
assert.equal(nodes.mapToolHazards.open, false);
assert.match(nodes.hazardGuideStatus.textContent, /全域取得/);
assert.equal(nodes.hazardGuideRegion.focusCount, 1);

let selected = [];
nodes.region.addEventListener("change", () => selected.push(nodes.region.value));
nodes.hazardGuideRegion.value = "15100";
nodes.hazardGuideRegion.dispatchEvent({type:"change"});
assert.equal(nodes.region.value, "15100");
assert.deepEqual(selected, ["15100"]);
nodes.region.value = "23100";
nodes.region.dispatchEvent({type:"change"});
assert.equal(nodes.hazardGuideRegion.value, "23100");
assert.equal(nodes.region.value, "23100");

let changedFlood = 0;
nodes.officialFlood.addEventListener("change", () => changedFlood++);
nodes.hazardGuideFlood.checked = false;
nodes.hazardGuideFlood.dispatchEvent({type:"change"});
assert.equal(nodes.officialFlood.checked, false);
assert.equal(changedFlood, 1);
assert.match(nodes.hazardGuideStatus.textContent, /非表示/);
assert.match(nodes.hazardGuideStatus.textContent, /浸水なし/);
nodes.officialFlood.checked = true;
nodes.officialFlood.dispatchEvent({type:"change"});
assert.equal(nodes.hazardGuideFlood.checked, true);
nodes.mapFloodRefreshStatus.dataset.state = "loading";
nodes.officialFlood.dispatchEvent({type:"change"});
assert.match(nodes.hazardGuideStatus.textContent, /更新中/);
nodes.mapFloodRefreshStatus.dataset.state = "partial";
nodes.officialFlood.dispatchEvent({type:"change"});
assert.match(nodes.hazardGuideStatus.textContent, /取得失敗/);
nodes.mapFloodRefreshStatus.dataset.state = "";
nodes.mapRasterBanner.dataset.partial = "true";
nodes.officialFlood.dispatchEvent({type:"change"});
assert.match(nodes.hazardGuideStatus.textContent, /過去の閲覧範囲/);

// An existing evidence sheet is closed before F01 opens; no facility UI is required.
nodes.hazardGuideClose.click();
nodes.mapEvidencePanel.hidden = false;
nodes.mapEvidenceClose = element("mapEvidenceClose");
nodes.mapEvidenceClose.addEventListener("click", () => { nodes.mapEvidencePanel.hidden = true; });
nodes.hazardGuideOpen.click();
assert.equal(nodes.mapEvidencePanel.hidden, true);
assert.equal(nodes.mapEvidenceClose.clickCount, 1);
assert.equal(nodes.hazardGuidePanel.hidden, false);
let prevented = false;
document.emit("keydown", {key:"Escape", preventDefault(){prevented = true;}});
assert.equal(prevented, true);
assert.equal(nodes.hazardGuidePanel.hidden, true);
assert.equal(nodes.hazardGuideOpen.attributes["aria-expanded"], "false");
assert.equal(nodes.hazardGuideOpen.focusCount > 0, true);

// Does not require a matching D/GSI facility or invoke GPS.
console.log("F01 independent flood access: synthetic UI and fail-closed states OK");