"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "gis/js/evidence_replay.js"), "utf8");
const html = fs.readFileSync(path.join(root, "gis/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "gis/css/evidence_replay.css"), "utf8");
const fixture = JSON.parse(fs.readFileSync(path.resolve(root,"../validation/demo/2019_edogawa_evidence_cases.json"),"utf8"));
const flush = () => new Promise(resolve => setImmediate(resolve));

function mount(fetchImpl = async () => ({ ok: true, json: async () => structuredClone(fixture) })) {
  const nodes = new Map();
  const docListeners = new Map();
  const intervals = new Map();
  let intervalId = 0, tourCloses = 0, tourOpens = 0;
  class Element {
    constructor(id) {
      this.id = id;
      this.hidden = id === "mapEvidenceReplayPanel" || id === "mapEvidenceReplayContent";
      this.disabled = false;
      this.textContent = "";
      this.attrs = new Map();
      this.events = new Map();
      this.dataset = {};
      this.style = {};
      this.children = [];
      this.href = "";
    }
    addEventListener(name, listener) { this.events.set(name, listener); }
    setAttribute(name, value) { this.attrs.set(name, value); }
    getAttribute(name) { return this.attrs.get(name); }
    click() { this.events.get("click")?.({ type:"click", target:this }); }
    focus() { document.activeElement = this; }
    replaceChildren(...items) { this.children = [...items]; }
    append(item) { this.children.push(item); }
    querySelectorAll(selector) {
      if (selector === "[data-evidence-case]") return tabNames.map(id => tabs[id]);
      if (selector === "[data-replay-stage]") return Array.from({length:4},(_,i) => steps[i]);
      if (selector === 'button:not([disabled]),a[href]') return [get("mapEvidenceReplayClose"),...tabNames.map(id=>tabs[id]),get("mapEvidenceReplayPlay"),get("mapEvidenceReplayPause"),get("mapEvidenceReplayNext")].filter(node=>!node.disabled);
      return [];
    }
  }
  const get = id => {
    if (!nodes.has(id)) nodes.set(id,new Element(id));
    return nodes.get(id);
  };
  const tabNames = ["trace","abstain","negative"], tabs = {}, steps = [];
  for (const id of tabNames) {
    tabs[id] = new Element("tab-"+id);
    tabs[id].dataset.evidenceCase = id;
    tabs[id].disabled = true;
  }
  for(let i=0;i<4;i++){const n=new Element("stage-"+i);n.dataset.replayStage=String(i);steps.push(n);}
  const document = {
    baseURI:"https://hinanex-staging.onrender.com/gis/gis/",
    hidden:false,activeElement:null,getElementById:get,
    createElement(tag) { return new Element(tag); },
    addEventListener(kind, fn) { docListeners.set(kind,fn); }
  };
  get("mapTourClose").addEventListener("click",()=>{ tourCloses++; get("mapTourPanel").hidden=true; });
  get("mapTourOpen").addEventListener("click",()=>{ tourOpens++; get("mapTourPanel").hidden=false; });
  const window = {
    fetch:fetchImpl,
    setInterval(fn,ms){ assert.equal(ms,1000);const n=++intervalId;intervals.set(n,fn);return n; },
    clearInterval(n){ intervals.delete(n); }
  };
  vm.runInNewContext(source,{document,window,URL,console:{error() {}}},{timeout:2000});
  return {get,tabs,steps,document,intervals,
    get tourCloses(){return tourCloses;},get tourOpens(){return tourOpens;},
    async open(){ get("mapHistoricalEvidenceDemo").click(); await flush(); await flush(); },
    tick(count=1){for(let j=0;j<count;j++){const f=intervals.values().next().value;assert.ok(f,"expected active interval");f();}},
    key(key){const fn=docListeners.get("keydown");let stopped=false;fn?.({key,shiftKey:false,preventDefault(){stopped=true;},stopImmediatePropagation(){}});return stopped;},
    visibility(isHidden){document.hidden=isHidden;docListeners.get("visibilitychange")?.();}
  };
}
test("inline modal is in the real map DOM with status, controls and no navigation",()=>{
  assert.match(html,/id="mapEvidenceReplayPanel"[^>]*role="dialog"/);
  assert.match(html,/id="mapHistoricalEvidenceDemo" type="button"/);
  assert.doesNotMatch(html,/id="mapHistoricalEvidenceDemo" href=/);
  for(const id of ["mapEvidenceReplayClose","mapEvidenceReplayPlay","mapEvidenceReplayPause",
    "mapEvidenceReplayPrev","mapEvidenceReplayNext","mapEvidenceReplayRestart","mapEvidenceReplaySources"]){
    assert.ok(html.includes('id="'+id+'"'));
  }
  assert.match(css,/\.evidence-replay\[hidden\]/);
  assert.match(css,/@media\(max-width:680px\)/);
  assert.match(html,/詳しい検証資料を見る/);
});
test("real C deck drives 15s intro + three 25s cases through four animated stages",async()=>{
  const m=mount();await m.open();
  assert.equal(m.tourCloses,1);
  assert.equal(m.get("mapEvidenceReplayPanel").hidden,false);
  assert.equal(m.get("mapEvidenceReplayContent").hidden,false);
  assert.equal(m.get("mapEvidenceReplayTrack").textContent.startsWith("T0"),true);
  assert.match(m.get("mapEvidenceReplayStageLabel").textContent,/INTRO/);
  assert.equal(m.intervals.size,1);
  m.tick(15);
  assert.equal(m.steps[0].dataset.state,"active");
  assert.match(m.get("mapEvidenceReplayStageText").textContent,/65/);
  m.tick(6);assert.equal(m.steps[1].dataset.state,"active");
  assert.match(m.get("mapEvidenceReplayStageText").textContent,/66/);
  m.tick(6);assert.equal(m.steps[2].dataset.state,"active");
  m.tick(6);assert.equal(m.steps[3].dataset.state,"active");
  assert.match(m.get("mapEvidenceReplayFinding").textContent,/T0/);
  m.tick(7);assert.match(m.get("mapEvidenceReplayTrack").textContent,/T1/);
  m.tick(25);assert.match(m.get("mapEvidenceReplayTrack").textContent,/合成負系/);
  m.tick(25);assert.equal(m.intervals.size,0);
  assert.match(m.get("mapEvidenceReplayStatus").textContent,/MATCH\/MISMATCHは未検証/);
  assert.equal(m.get("mapEvidenceReplayNext").disabled,true);
});
test("case selection and pause/next/previous/restart preserve exact UNVERIFIED and synthetic labels",async()=>{
  const m=mount();await m.open();
  m.tabs.abstain.click();
  assert.equal(m.intervals.size,0);
  assert.match(m.get("mapEvidenceReplayTrack").textContent,/T1/);
  assert.match(m.get("mapEvidenceReplayStageText").textContent,/205人/);
  m.get("mapEvidenceReplayNext").click();
  assert.match(m.get("mapEvidenceReplayStageText").textContent,/null/);
  m.get("mapEvidenceReplayPrev").click();
  assert.match(m.get("mapEvidenceReplayStageText").textContent,/11人/);
  m.tabs.negative.click();
  assert.match(m.get("mapEvidenceReplayTrack").textContent,/合成負系/);
  m.get("mapEvidenceReplayPlay").click();
  assert.equal(m.intervals.size,1);
  m.get("mapEvidenceReplayPause").click();
  assert.equal(m.intervals.size,0);
  m.get("mapEvidenceReplayRestart").click();
  assert.equal(m.intervals.size,1);
  assert.match(m.get("mapEvidenceReplayStageLabel").textContent,/INTRO/);
  m.visibility(true);
  assert.equal(m.intervals.size,0);
});
test("failure to load or falsely approved evidence never renders a scenario",async()=>{
  for(const malformed of [
    null,
    (()=>{const x=structuredClone(fixture);x.historical_prediction_approved=true;return x;})(),
    (()=>{const x=structuredClone(fixture);x.cases[2].result="MISMATCH";return x;})(),
    (()=>{const x=structuredClone(fixture);x.approved_actual_building_pairs=1;return x;})(),
    (()=>{const x=structuredClone(fixture);x.sources[0].official_url="https://evil.example/";return x;})()
  ]){
    const fn=malformed===null ? async()=>({ok:false,status:503}) :
      async()=>({ok:true,json:async()=>malformed});
    const m=mount(fn);await m.open();
    assert.equal(m.get("mapEvidenceReplayContent").hidden,true);
    assert.match(m.get("mapEvidenceReplayStatus").textContent,/確認できません/);
    assert.equal(m.intervals.size,0);
  }
});
test("close/Escape and stale HTTP responses cannot restart a hidden player",async()=>{
  let resolve;
  const m=mount(()=>new Promise(r=>{resolve=r;}));
  m.get("mapHistoricalEvidenceDemo").click();
  assert.equal(m.get("mapEvidenceReplayPanel").hidden,false);
  assert.equal(m.key("Escape"),true);
  assert.equal(m.get("mapEvidenceReplayPanel").hidden,true);
  assert.equal(m.tourOpens,1);
  resolve({ok:true,json:async()=>structuredClone(fixture)});
  await flush();await flush();
  assert.equal(m.intervals.size,0);
  assert.equal(m.get("mapEvidenceReplayContent").hidden,true);
});
test("browser client never changes RegionExport, map view or C evidence",()=>{
  assert.doesNotMatch(source,/\b(flyTo|setView|setZoom|setRegion|geocode|innerHTML)\b/);
  assert.match(source,/textContent/);
  assert.match(source,/cache: "no-store"/);
  assert.match(source,/NOT_EVALUABLE/);
  assert.match(source,/SYNTHETIC_NEGATIVE_TEST_NOT_REAL_MISMATCH/);
});
