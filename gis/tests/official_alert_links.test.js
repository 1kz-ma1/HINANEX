"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname, "../gis/index.html"),"utf8");
const js = fs.readFileSync(path.join(__dirname, "../gis/js/official_alert_links.js"),"utf8");
const css = fs.readFileSync(path.join(__dirname, "../gis/css/map_first.css"),"utf8");

for (const id of ["officialAlertsOpen","officialAlertsPanel","officialAlertsClose",
  "officialAlertsRegionName","officialAlertsRegionNote","officialAlertsLocalLink"]) {
  assert.equal((html.match(new RegExp('id="'+id+'"',"g"))||[]).length,1,
    "F06 ID must appear exactly once: "+id);
}
assert.match(html,/js\/official_alert_links\.js\?v=f06-links-20261104-v1/);
assert.match(html,/外部サイトで最新の情報を確認/);
assert.match(html,/気象庁：あなたの街の防災情報/);
assert.match(html,/気象庁：キキクル/);
assert.match(css,/\.official-alerts-panel\[hidden\]\{display:none\}/);
assert.doesNotMatch(js,/fetch\s*\(|XMLHttpRequest|geolocation|localStorage|sessionStorage|navigator\.permissions|setInterval/);
assert.doesNotMatch(js,/\bopen\s*\(/);
const strictUrls = [
  "https://bosai.city.edogawa.tokyo.jp/",
  "https://www.city.niigata.lg.jp/kurashi/bosai/index.html",
  "https://www.city.nagoya.jp/bousaiportal/index.html"
];
for (const u of strictUrls) assert.ok(js.includes(u), "Only official URLs: "+u);
for (const u of ["https://www.jma.go.jp/bosai/","https://www.jma.go.jp/bosai/risk/"])
  assert.ok(html.includes(u),"JMA official destination required: "+u);

function element(id) {
  return {
    id,hidden:id==="officialAlertsPanel",open:id==="mapToolHazards",
    value:id==="region"?"13123":"",href:"",textContent:"",attributes:{},events:{},focused:false,
    addEventListener(t,fn){(this.events[t]??=[]).push(fn);},
    setAttribute(k,v){this.attributes[k]=String(v);},
    removeAttribute(k){delete this.attributes[k];if(k==="href")this.href="";},
    dispatchEvent(e){for(const f of this.events[e.type]||[])f(e);},
    focus(){this.focused=true;},click(){this.dispatchEvent({type:"click",target:this});},
    contains(t){return this===t;},
    querySelector(q){return q==="summary"?elements.mapToolHazardsSummary:null;}
  };
}
const ids=["officialAlertsOpen","officialAlertsPanel","officialAlertsClose",
  "officialAlertsRegionName","officialAlertsRegionNote","officialAlertsLocalLink",
  "region","mapToolHazards","mapToolHazardsSummary","mapToolScene","mapToolScenario",
  "mapToolMarks","hazardGuidePanel","hazardGuideClose","mapEvidencePanel",
  "mapEvidenceClose","mapTourPanel","mapTourClose","mapSharePanel",
  "mapShareClose","mapSettingsPanel","mapSettingsClose"];
const elements=Object.fromEntries(ids.map(id=>[id,element(id)]));
const document={
  events:{},
  getElementById(id){return elements[id]||null;},
  addEventListener(t,fn){(this.events[t]??=[]).push(fn);},
  emit(t,e){for(const f of this.events[t]||[])f(e);}
};
const window={events:{},addEventListener(t,fn){(this.events[t]??=[]).push(fn);}};
vm.runInNewContext(js,{document,window,console},{filename:"official_alert_links.js"});

const e=elements;
assert.equal(e.officialAlertsPanel.hidden,true);
assert.equal(e.officialAlertsLocalLink.href,strictUrls[0]);
assert.match(e.officialAlertsLocalLink.textContent,/江戸川区/);
e.officialAlertsOpen.click();
assert.equal(e.officialAlertsPanel.hidden,false);
assert.equal(e.officialAlertsOpen.attributes["aria-expanded"],"true");
assert.equal(e.mapToolHazards.open,false);
assert.equal(e.officialAlertsClose.focused,true);

// All three links track the existing region selector; no city-specific
// statement about the presence of a current alert is generated.
for(const [regionCode,url,name] of [
  ["15100",strictUrls[1],"新潟市"],["23100",strictUrls[2],"名古屋市"],
  ["13123",strictUrls[0],"江戸川区"]
]){
  e.region.value=regionCode;
  e.region.dispatchEvent({type:"change"});
  assert.equal(e.officialAlertsLocalLink.href,url);
  assert.ok(e.officialAlertsRegionName.textContent.includes(name));
  assert.equal(e.officialAlertsLocalLink.hidden,false);
  assert.match(e.officialAlertsRegionNote.textContent,/外部サイト/);
}
e.region.value="99999";
e.region.dispatchEvent({type:"change"});
assert.equal(e.officialAlertsLocalLink.hidden,true);
assert.equal(e.officialAlertsLocalLink.href,"");
assert.match(e.officialAlertsRegionNote.textContent,/未登録/);
assert.match(e.officialAlertsRegionNote.textContent,/警報なし/);
e.region.value="13123";
e.region.dispatchEvent({type:"change"});

// Opening F06 closes F01, without changing its underlying official raster.
e.officialAlertsClose.click();
e.hazardGuidePanel.hidden=false;
e.hazardGuideClose.events.click=[()=>{e.hazardGuidePanel.hidden=true;}];
e.officialAlertsOpen.click();
assert.equal(e.hazardGuidePanel.hidden,true);
assert.equal(e.officialAlertsPanel.hidden,false);

let prevented=false;
document.emit("keydown",{key:"Escape",preventDefault(){prevented=true;}});
assert.equal(prevented,true);
assert.equal(e.officialAlertsPanel.hidden,true);
assert.equal(e.officialAlertsOpen.attributes["aria-expanded"],"false");
assert.equal(e.mapToolHazardsSummary.focused,true);
console.log("F06 official link directory: 3 regions, unknown state, focus, isolation OK");