const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = { window: {}, URL };
vm.createContext(ctx);
const file = path.resolve(__dirname, "../gis/js/facility_explore.js");
vm.runInContext(fs.readFileSync(file, "utf8"), ctx, { filename: file });
const { createSession } = ctx.window.HINANEX_FACILITY_EXPLORE;
assert.equal(ctx.window.HINANEX_FACILITY_EXPLORE.apiVersion, "flood-facility-explore-20261023-v1");

function fixture() {
  const records = [
    { id: "c", name: "合成C", address: null, hasCoordinates: false },
    { id: "a", name: "<img src=x onerror=alert(1)>", address: "東京都テスト", hasCoordinates: true },
    { id: "b", name: "合成B", address: "テスト中央", hasCoordinates: false }
  ];
  const byId = new Map([
    ["a", {status:"CANDIDATE",reason:"synthetic fact",joinStatus:"DIRECT_SAME_SOURCE",
      hazardScopeRaw:"災害種別_洪水",officialStatusRaw:"○",sourceRecordTrace:"row=1",
      sourceUrl:"https://example.test/a.csv"}],
    ["b", {status:"EXCLUDED",reason:"synthetic fact",joinStatus:"DIRECT_SAME_SOURCE",
      hazardScopeRaw:"災害種別_洪水",officialStatusRaw:"×",sourceRecordTrace:"row=2",
      sourceUrl:"https://example.test/b.csv"}],
    ["c", {status:"UNKNOWN",reason:"未確認",joinStatus:"UNVERIFIED",
      hazardScopeRaw:"洪水・内水",officialStatusRaw:"－",sourceRecordTrace:null,sourceUrl:null}]
  ]);
  return {dataset:{},region:{code:"13123",name:"合成地域"},
    records,floodScenario:{byId}};
}
{
  const s=createSession(fixture());
  assert.equal(s.state,"READY");
  assert.equal(s.total,3);
  assert.equal(s.counts.UNKNOWN,1);
  assert.equal(s.counts.CANDIDATE,1);
  assert.equal(s.counts.EXCLUDED,1);
  assert.equal(s.page().state,"HAS_ROWS");
  assert.deepEqual(Array.from(s.page().records,x=>x.id),["a","b","c"]);
  assert.equal(s.page().records[2].hasCoordinates,false);
  assert.equal(s.officialSourceTimeVerified,false);
  assert.equal(s.toggle("a").ok,true);
  assert.equal(s.choose("a").ok,false);
  assert.equal(s.toggle("b").ok,true);
  assert.equal(s.toggle("c").reason,"TWO_ONLY");
  assert.equal(s.choose("b").ok,true);
  assert.equal(s.choice().status,"EXCLUDED");
  s.setCriteria("合成","all");
  assert.equal(s.choice(),null);
  assert.equal(s.selected().length,0);
  assert.equal(s.page().matched,2);
  assert.equal(s.toggle("a").reason,"NOT_IN_RESULT");
  s.setCriteria("該当なし","UNKNOWN");
  assert.equal(s.page().state,"NO_MATCH");
  s.setCriteria("","UNKNOWN");
  assert.equal(s.page().matched,1);
  assert.equal(s.page().records[0].status,"UNKNOWN");
  assert.equal(s.setCriteria("","SAFE").ok,false);
}
{
  const data=fixture();
  data.records=[];
  data.floodScenario.byId=new Map();
  const s=createSession(data);
  assert.equal(s.state,"READY");
  assert.equal(s.page().state,"NO_DATA");
  assert.equal(s.total,0);
}
{
  assert.equal(createSession(null).state,"NO_DATASET");
  const data=fixture();
  data.floodScenario=null;
  assert.equal(createSession(data).state,"NO_SCENARIO");
}
{
  const alterations=[
    d=>d.records.push({...d.records[0]}),
    d=>d.records.pop(),
    d=>d.floodScenario.byId.get("a").status="SAFE",
    d=>d.floodScenario.byId.get("a").sourceUrl="javascript:alert(1)",
    d=>d.floodScenario.byId.get("a").sourceUrl="https://user@example.test/test",
    d=>d.floodScenario.byId.get("a").joinStatus="UNVERIFIED",
    d=>d.floodScenario.byId.get("a").hazardScopeRaw="洪水・内水",
    d=>d.floodScenario.byId.get("a").officialStatusRaw=null,
    d=>d.floodScenario.byId.get("a").sourceRecordTrace=null,
    d=>d.floodScenario.byId.get("a").sourceUrl=null,
    d=>d.floodScenario.byId.delete("a"),
    d=>d.floodScenario.byId.get("b").reason=null
  ];
  for (const alter of alterations) {
    const data=fixture();alter(data);
    assert.equal(createSession(data).state,"INVALID");
  }
}
{
  // UNKNOWN must remain visible even with no coordinates or approved hazard interpretation.
  const data=fixture();
  data.floodScenario.byId.get("c").sourceUrl="https://example.test/c.csv";
  const s=createSession(data);
  assert.equal(s.state,"READY");
  assert.equal(s.page().records[2].status,"UNKNOWN");
}
{
  // Rendering uses inert text, and never treats a user pick as safe.
  const html=fs.readFileSync(path.resolve(__dirname,"../gis/index.html"),"utf8");
  const ui=fs.readFileSync(path.resolve(__dirname,"../gis/js/facility_explore_ui.js"),"utf8");
  const map=fs.readFileSync(path.resolve(__dirname,"../gis/js/map.js"),"utf8");
  assert.match(html,/id="mapFacilityExploreOpen"/);
  assert.match(html,/id="facilityExplorePanel"/);
  assert.match(html,/id="facilityExploreChoice"/);
  assert.match(html,/js\/facility_explore\.js/);
  assert.match(html,/js\/facility_explore_ui\.js/);
  assert.ok(html.indexOf('js/facility_explore.js')<html.indexOf('js/facility_explore_ui.js'));
  assert.match(ui,/textContent/);
  assert.doesNotMatch(ui,/innerHTML/);
  assert.match(map,/HINANEX_FACILITY_EXPLORE_UI\?\.setSummary\(summary\)/);
  assert.match(map,/HINANEX_FACILITY_EXPLORE_UI\?\.setSummary\(null\)/);
}
console.log("facility_explore.test.js: OK");
