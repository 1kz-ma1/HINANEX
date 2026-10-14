"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const script=fs.readFileSync(path.resolve(__dirname,"../gis/js/filter_demo.js"),"utf8");
const html=fs.readFileSync(path.resolve(__dirname,"../gis/index.html"),"utf8");
const css=fs.readFileSync(path.resolve(__dirname,"../gis/css/filter_demo.css"),"utf8");
const flush=()=>new Promise(r=>setImmediate(r));
function mount(result={state:"ready",region:"江戸川区",sourceTotal:152,mapped:152,missing:0,
 classified:0,unknown:152,criterion:"施設名に「小学校」を含む",criterionKind:"name",matches:74}){
 const nodes=new Map(),events=new Map(),timers=new Map(),calls=[];
 let id=0;
 class E{
  constructor(name){this.id=name;this.textContent="";this.hidden=["filterDemoPanel","filterDemoContent","storyPanel","mapEvidenceReplayPanel"].includes(name);this.style={};this.attrs={};this.listeners={};this.disabled=false;this.href="";}
  addEventListener(k,fn){this.listeners[k]=fn;}
  click(){this.listeners.click?.({target:this});}
  focus(){document.activeElement=this;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k];}
  removeAttribute(k){delete this.attrs[k];}
  querySelectorAll(){return [get("filterDemoClose"),get("filterDemoPlay"),get("filterDemoPause")];}
 }
 const get=id=>{if(!nodes.has(id))nodes.set(id,new E(id));return nodes.get(id);};
 get("mapTourOpen").addEventListener("click",()=>{});
 get("mapTourClose").addEventListener("click",()=>{});
 const document={hidden:false,activeElement:null,getElementById:get,addEventListener(k,fn){events.set(k,fn);}};
 const api={
  async begin(){calls.push("begin");return result;},
  apply(){calls.push("apply");return{state:"filtered",matches:result.matches};},
  inspect(){calls.push("inspect");return{state:"inspected",name:"東小学校",criterion:result.criterion,criterionValue:"東小学校",decision:"UNKNOWN",reason:null,sourceTrace:null,sourceUrl:null};},
  halt(){calls.push("halt");},end(restore){calls.push("end:"+restore);}
 };
 const window={HINANEX_FACILITY_PRESENTER:api,
  setInterval(fn,ms){assert.equal(ms,1000);timers.set(++id,fn);return id;},
  clearInterval(k){timers.delete(k);}
 };
 vm.runInNewContext(script,{document,window,console:{warn(){}}},{timeout:1800});
 return{get,calls,timers,events,document,
  async open(){get("mapFilterDemoOpen").click();await flush();await flush();},
  tick(n){for(let i=0;i<n;i++){const fn=timers.values().next().value;assert.ok(fn);fn();}},
  gesture(){get("map").listeners.wheel?.({});}
 };
}
test("primary demo is source-attribute GIS presentation; historical demos remain",()=>{
 assert.match(html,/id="mapFilterDemoOpen" type="button"/);
 assert.match(html,/id="mapStoryOpen" type="button"/);
 assert.match(html,/id="mapHistoricalEvidenceDemo" type="button"/);
 assert.match(html,/js\/filter_demo[.]js[?]v=unified-place-card-20261014-v2/);
 assert.match(css,/@media\(max-width:780px\)/);
 assert.match(html,/表示された施設 ≠ 避難先として適切な施設/);
});
test("52s animation drives actual filter and record inspection; no fake safety claim",async()=>{
 const m=mount();await m.open();
 assert.equal(m.get("filterDemoContent").hidden,false);
 assert.equal(m.get("filterDemoMatched").textContent,"152");
 m.tick(8);
 assert.equal(m.get("filterDemoMatched").textContent,"74");
 assert.ok(m.calls.includes("apply"));
 m.tick(12);
 assert.ok(m.calls.includes("inspect"));
 assert.equal(m.get("filterDemoFacility").textContent,"東小学校");
 assert.equal(m.get("filterDemoEvidenceValue").textContent,"東小学校");
 assert.equal(m.get("filterDemoDecision").textContent,"未判定（UNKNOWN）");
 m.tick(14);assert.match(m.get("filterDemoTitle").textContent,/照合/);
 m.tick(11);assert.equal(m.get("filterDemoFuture").hidden,false);
 m.tick(7);assert.equal(m.timers.size,0);
 assert.equal(m.get("filterDemoProgress").style.width,"100%");
});
test("pause, manual map gesture and close restore filters without undoing user pan",async()=>{
 const m=mount();await m.open();
 m.get("filterDemoPause").click();assert.equal(m.timers.size,0);
 m.get("filterDemoPlay").click();assert.equal(m.timers.size,1);
 m.gesture();assert.equal(m.timers.size,0);
 m.get("filterDemoClose").click();
 assert.ok(m.calls.includes("end:false"));
 assert.equal(m.get("filterDemoPanel").hidden,true);
});
test("missing source or no distinguishing filter never animates invented counts",async()=>{
 for(const result of [{state:"unavailable"},{state:"no-distinguishing-condition",sourceTotal:20,mapped:20,matches:0}]){
  const m=mount(result);await m.open();
  assert.equal(m.get("filterDemoContent").hidden,true);
  assert.equal(m.timers.size,0);
  assert.match(m.get("filterDemoStatus").textContent,/確認できません/);
  m.get("filterDemoClose").click();
 }
});
test("Escape and delayed close do not restart a hidden timer",async()=>{
 const m=mount();await m.open();
 let prevented=false;
 m.events.get("keydown")({key:"Escape",preventDefault(){prevented=true;},stopImmediatePropagation(){}});
 assert.equal(prevented,true);
 assert.equal(m.get("filterDemoPanel").hidden,true);
 assert.equal(m.timers.size,0);
 assert.ok(m.calls.includes("end:true"));
});
