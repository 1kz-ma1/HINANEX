"use strict";
const { test }=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const script=fs.readFileSync(path.join(root,"gis/js/presentation_story.js"),"utf8");
const html=fs.readFileSync(path.join(root,"gis/index.html"),"utf8");
const css=fs.readFileSync(path.join(root,"gis/css/presentation_story.css"),"utf8");
const fixture=JSON.parse(fs.readFileSync(path.resolve(root,"../validation/demo/2019_edogawa_evidence_cases.json"),"utf8"));
const flush=()=>new Promise(r=>setImmediate(r));
function mount(load=async()=>({ok:true,json:async()=>structuredClone(fixture)}),mapFocus){
  const nodes=new Map(),handlers=new Map(),clock=new Map(),cam={begin:0,focus:[],halt:0,end:[]};
  let id=0,legacyOpens=0,details=0;
  class Element{
    constructor(name){this.name=name;this.hidden=["storyPanel","storyContent","mapEvidenceReplayPanel"].includes(name);this.disabled=false;this.textContent="";this.dataset={};this.style={};this.attrs=new Map();this.events=new Map();this.href="";}
    addEventListener(k,fn){this.events.set(k,fn);}
    setAttribute(k,v){this.attrs.set(k,v);}
    getAttribute(k){return this.attrs.get(k);}
    click(){this.events.get("click")?.({target:this});}
    focus(){document.activeElement=this;}
    querySelectorAll(){return [get("storyClose"),get("storyPlay"),get("storyPause"),get("storyNext"),get("storyRestart"),get("storyDetailed")];}
  }
  const get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
  get("mapTourClose").addEventListener("click",()=>{});
  get("mapTourOpen").addEventListener("click",()=>legacyOpens++);
  get("mapHistoricalEvidenceDemo").addEventListener("click",()=>details++);
  const document={activeElement:null,hidden:false,baseURI:"https://hinanex-staging.onrender.com/gis/gis/",getElementById:get,addEventListener(k,fn){handlers.set(k,fn);}};
  const window={
    fetch:load,matchMedia:()=>({matches:false}),
    setInterval(fn,ms){assert.equal(ms,1000);const n=++id;clock.set(n,fn);return n;},
    clearInterval(n){clock.delete(n);},
    HINANEX_VALIDATE_EVIDENCE(data){if(data.schema_id!=="hinanex.c.midterm_explanation_cases.v0.1"||data.presentation_only!==true||data.historical_prediction_approved!==false||data.human_c_approved!==false||data.approved_actual_building_pairs!==0||data.historical_replay_executed!==false||data.cases.length!==3||data.cases[1].result!=="NOT_EVALUABLE"||data.cases[2].result!=="SYNTHETIC_INVALID_INPUT_REJECTED")throw new Error("Invalid C truth");return data;},
    HINANEX_PRESENTATION_TOUR:{
      begin(){cam.begin++;},focus(code,animated,first){cam.focus.push({code,animated,first});return mapFocus?mapFocus(code):Promise.resolve({state:"mapped",total:152,mapped:151});},
      halt(){cam.halt++;},end(restore){cam.end.push(restore);}
    }
  };
  vm.runInNewContext(script,{document,window,URL,console:{warn(){}}},{timeout:2000});
  return {get,cam,clock,document,get legacyOpens(){return legacyOpens;},get details(){return details;},
    async open(){get("mapStoryOpen").click();await flush();await flush();},
    tick(n){for(let i=0;i<n;i++){const fn=clock.values().next().value;assert.ok(fn,"timer expected");fn();}},
    gesture(k="pointerdown"){get("map").events.get(k)?.({type:k});},
    hide(){document.hidden=true;handlers.get("visibilitychange")?.();},
    escape(){let value=false;handlers.get("keydown")?.({key:"Escape",preventDefault(){value=true;},stopImmediatePropagation(){}});return value;}
  };
}
test("55-second visual demo is primary and detailed 90s route is retained",()=>{
  assert.match(html,/id="mapStoryOpen" type="button" aria-controls="storyPanel"/);
  assert.match(html,/id="mapHistoricalEvidenceDemo" type="button"/);
  assert.match(html,/id="storyPanel" class="story-panel" role="region"/);
  assert.match(html,/3つの検証を55秒で理解する/);
  assert.match(html,/js\/presentation_story[.]js[?]v=presenter-55s-20261014-v1/);
  assert.match(css,/@media\(max-width:850px\)/);
  assert.match(css,/#map\[data-story-active="true"\]/);
  assert.match(html,/詳細90秒版で根拠を見る/);
});
test("real C deck shows visual 5/13/16/14/7 second sequence and finishes on the 55th tick",async()=>{
  const m=mount();await m.open();
  assert.equal(m.get("storyContent").hidden,false);assert.equal(m.get("storyLoadStatus").hidden,true);
  assert.equal(m.cam.begin,1);assert.deepEqual(m.cam.focus.map(x=>x.code),["13123"]);
  assert.equal(m.cam.focus[0].first,false);
  assert.match(m.get("storyMapStatus").textContent,/取得 152件.*元座標あり 151件.*位置未確認 1件/);
  assert.equal(m.get("storyPanel").dataset.scene,"intro");
  m.tick(5);assert.equal(m.get("storyPanel").dataset.scene,"trace");
  assert.match(m.get("storyNodeValue0").textContent,/66/);
  assert.match(m.get("storyNodeValue1").textContent,/65/);
  m.tick(13);assert.equal(m.get("storyPanel").dataset.scene,"abstain");
  assert.match(m.get("storyNodeValue0").textContent,/205/);
  assert.match(m.get("storyNodeValue1").textContent,/未確定/);
  m.tick(16);assert.equal(m.get("storyPanel").dataset.scene,"negative");
  assert.match(m.get("storyNodeValue2").textContent,/拒否/);
  m.tick(14);assert.equal(m.get("storyPanel").dataset.scene,"summary");
  m.tick(7);assert.equal(m.clock.size,0);
  assert.equal(m.get("storyNext").disabled,true);
  assert.equal(m.get("storyBar").style.width,"100%");
});
test("controls, external C source provenance and handoff to 90s detail work",async()=>{
  const m=mount();await m.open();
  const school=fixture.sources.find(s=>s.id==="school");
  assert.equal(m.get("storyOfficialSource").href,school.official_url);
  assert.equal(m.get("storyMachineAudit").href,school.machine_audit_url);
  m.get("storyPause").click();assert.equal(m.clock.size,0);
  m.get("storyJumpabstain").click();
  assert.equal(m.get("storyPanel").dataset.scene,"abstain");
  assert.equal(m.get("storyJumpabstain").getAttribute("aria-pressed"),"true");
  m.get("storyNext").click();assert.equal(m.get("storyPanel").dataset.scene,"negative");
  m.get("storyRestart").click();assert.equal(m.get("storyPanel").dataset.scene,"intro");
  assert.equal(m.clock.size,1);
  m.hide();assert.equal(m.clock.size,0);
  m.get("storyDetailed").click();assert.equal(m.details,1);assert.equal(m.legacyOpens,1);
  assert.equal(m.get("storyPanel").hidden,true);
  assert.equal(m.cam.end.at(-1),true);
  await m.open();assert.equal(m.escape(),true);
  assert.equal(m.get("storyPanel").hidden,true);
});
test("manual map operation pauses and keeps the viewer's map on close",async()=>{
  const m=mount();await m.open();m.gesture("wheel");
  assert.equal(m.clock.size,0);
  assert.match(m.get("storyMapStatus").textContent,/手動で地図を操作/);
  m.get("storyClose").click();assert.equal(m.cam.end.at(-1),false);
  assert.equal(m.get("map").dataset.storyActive,undefined);
});
test("unknown D locations do not imply missing shelters",async()=>{
  const m=mount(undefined,async()=>({state:"unlocated",total:15,mapped:0}));await m.open();
  assert.match(m.get("storyMapStatus").textContent,/未取得・未確認/);
  assert.doesNotMatch(m.get("storyMapStatus").textContent,/元座標あり 15件/);
});
test("C failures and changed event numbers fail closed before moving the map",async()=>{
  const alternatives=[
    async()=>({ok:false,status:503}),
    async()=>({ok:true,json:async()=>{const v=structuredClone(fixture);v.cases[0].input_text="66明細";return v;}}),
    async()=>({ok:true,json:async()=>{const v=structuredClone(fixture);v.human_c_approved=true;return v;}})
  ];
  for(const fn of alternatives){
    const m=mount(fn);await m.open();
    assert.equal(m.get("storyContent").hidden,true);
    assert.equal(m.get("storyLoadStatus").hidden,false);
    assert.match(m.get("storyLiveStatus").textContent,/停止/);
    assert.equal(m.cam.begin,0);assert.equal(m.clock.size,0);
  }
});
test("closing before C fetch resolves never reopens the visual player",async()=>{
  let release;const m=mount(()=>new Promise(resolve=>{release=resolve;}));
  m.get("mapStoryOpen").click();m.get("storyClose").click();
  release({ok:true,json:async()=>structuredClone(fixture)});
  await flush();await flush();
  assert.equal(m.get("storyPanel").hidden,true);assert.equal(m.cam.begin,0);assert.equal(m.clock.size,0);
});
test("presentation adds no fake points or historical safety verdicts",()=>{
  assert.doesNotMatch(script,/\b(innerHTML|geocode|setView|L\.marker|L\.circleMarker|flyTo)\b/);
  assert.match(script,/camera\.focus\("13123",!reduced,false\)/);
  assert.match(script,/NOT_EVALUABLE|比較不可/);
  assert.match(script,/合成負系テスト/);
  assert.match(script,/人手承認前/);
});
