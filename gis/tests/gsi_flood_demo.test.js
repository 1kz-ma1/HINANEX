"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const code=fs.readFileSync(path.resolve(__dirname,"../gis/js/gsi_flood_demo.js"),"utf8");
const html=fs.readFileSync(path.resolve(__dirname,"../gis/index.html"),"utf8");
const flush=()=>new Promise(r=>setImmediate(r));
function mount(reply={state:"ready",source:"GSI_SKHB01_FLOOD",rawDisaster1:1,total:8,shown:5,verifiedTiles:1,requestedTiles:9}){
 const nodes=new Map(),ev=new Map(),timers=new Map(),calls=[];let n=0;
 class Node{constructor(id){this.id=id;this.hidden=["gsiFloodDemoPanel","gsiFloodDemoContent","gsiFloodDemoEvidence","gsiFloodDemoContrast","gsiFloodDemoFuture","gsiFloodDemoOfficial","filterDemoPanel","storyPanel","mapEvidenceReplayPanel"].includes(id);this.textContent="";this.style={};this.disabled=false;this.attrs={};this.listeners={};this.href="";}
 addEventListener(k,f){this.listeners[k]=f;}click(){this.listeners.click?.({});}
 focus(){doc.activeElement=this;}setAttribute(k,v){this.attrs[k]=String(v);}
 removeAttribute(k){delete this.attrs[k];}
 querySelectorAll(){return [get("gsiFloodDemoClose"),get("gsiFloodDemoPlay")];}}
 const get=id=>{if(!nodes.has(id))nodes.set(id,new Node(id));return nodes.get(id);};
 for(const id of ["mapTourClose","mapTourOpen"])get(id).addEventListener("click",()=>{});
 const doc={hidden:false,activeElement:null,getElementById:get,addEventListener(k,f){ev.set(k,f);}};
 const api={async begin(){calls.push("begin");return reply;},
 show(){calls.push("show");return {state:"shown",count:reply.total};},
 inspect(){calls.push("inspect");return {state:"inspected",name:"公式掲載地点",address:"出典の住所",
 sourceTrace:"feature_index=0",sourceUrl:"https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson",
 disaster1Raw:1,tileCount:1,requestedTiles:9};},
 compareD(){calls.push("compare");return {state:"separate-source",mapped:152,unclassified:152};},
 halt(){calls.push("halt");},end(b){calls.push("end:"+b);}};
 const win={HINANEX_GSI_FLOOD_PRESENTER:api,
 setInterval(f,ms){assert.equal(ms,1000);timers.set(++n,f);return n;},
 clearInterval(k){timers.delete(k);}};
 vm.runInNewContext(code,{window:win,document:doc,console:{warn(){}}},{timeout:1800});
 return {get,ev,calls,timers,async open(){get("mapGsiFloodDemoOpen").click();await flush();await flush();},
 tick(count){for(let i=0;i<count;i++){const f=timers.values().next().value;assert.ok(f);f();}},
 pan(){get("map").listeners.wheel?.({});}};
}
test("GSI flood is primary while D filter and 2019 evidence remain",()=>{
 assert.ok(html.indexOf('id="mapGsiFloodDemoOpen"')<html.indexOf('id="mapFilterDemoOpen"'));
 assert.match(html,/gsi_flood_demo[.]js[?]v=verified-gsi-flood-20261014-v1/);
 assert.match(html,/公式掲載 ≠ 現在安全・開設中・避難推奨/);
});
test("50 seconds: verified source layer -> raw flood proof -> distinct D unknown -> future",async()=>{
 const m=mount();await m.open();assert.equal(m.get("gsiFloodDemoContent").hidden,false);
 m.tick(7);assert.ok(m.calls.includes("show"));
 m.tick(12);assert.ok(m.calls.includes("inspect"));
 assert.equal(m.get("gsiFloodDemoName").textContent,"公式掲載地点");
 assert.equal(m.get("gsiFloodDemoTrace").textContent,"feature_index=0");
 assert.match(m.get("gsiFloodDemoOfficial").href,/skhb01/);
 m.tick(12);assert.ok(m.calls.includes("compare"));
 assert.match(m.get("gsiFloodDemoDStatus").textContent,/未判定 152件/);
 m.tick(12);assert.equal(m.get("gsiFloodDemoFuture").hidden,false);
 m.tick(7);assert.equal(m.timers.size,0);
 assert.equal(m.get("gsiFloodDemoProgress").style.width,"100%");
});
test("source absent or incorrect raw value refuses to animate",async()=>{
 for(const r of [{state:"unavailable"},{state:"ready",source:"GSI_SKHB01_FLOOD",rawDisaster1:0,total:2,shown:2}]){
  const m=mount(r);await m.open();
  assert.equal(m.get("gsiFloodDemoContent").hidden,true);
  assert.equal(m.timers.size,0);
  assert.match(m.get("gsiFloodDemoStatus").textContent,/確認できません/);
  m.get("gsiFloodDemoClose").click();
 }
});
test("gesture cancels animation and leaves manually moved map; Esc restores otherwise",async()=>{
 const m=mount();await m.open();m.pan();assert.equal(m.timers.size,0);
 m.get("gsiFloodDemoClose").click();assert.ok(m.calls.includes("end:false"));
 const x=mount();await x.open();let prevented=false;
 x.ev.get("keydown")({key:"Escape",preventDefault(){prevented=true;},stopImmediatePropagation(){}});
 assert.equal(prevented,true);assert.ok(x.calls.includes("end:true"));
 assert.equal(x.timers.size,0);
});
