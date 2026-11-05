const test = require('node:test');
const assert = require('node:assert/strict');
const m = require('../model.js');
const fixture = require('../fixtures.js');

test('T01: region filters results without auto-merging facilities', () => {
  assert.equal(m.searchRecords(fixture.records,'sample-blue','').length,4);
  assert.equal(m.searchRecords(fixture.records,'sample-amber','').length,1);
  assert.equal(m.searchRecords(fixture.records,'sample-empty','').length,0);
});
test('T02: facility name searching works and normalizes full-width text', () => {
  assert.equal(m.searchRecords(fixture.records,'sample-blue','青空').length,1);
  assert.equal(m.searchRecords(fixture.records,'sample-blue','  ｽｽﾞﾗﾝ ').length,1);
  assert.equal(m.searchRecords(fixture.records,'sample-blue','存在しない').length,0);
});
test('T03: all listed records are fixtures and URLs are invalid', () => {
  assert.ok(fixture.records.every(x=>x.source.url.startsWith('https://example.invalid/')));
  assert.ok(fixture.records.every(x=>x.regionId.startsWith('sample-')));
});
test('T04: unknown fields and coordinates are preserved, not inferred', () => {
  const x=fixture.records.find(x=>x.id==='FA-002');
  assert.equal(x.roleRaw,'UNKNOWN');assert.equal(m.displayRaw(x.roleRaw),'未確認');
  assert.equal(x.position.coordinates,null);assert.equal(m.locationLabel(x),'位置未確認（座標なし）');
});
test('T05: missing source is distinct from missing coordinates',()=>{
  const s=m.getRegionStats(fixture.records,'sample-blue','');
  assert.deepEqual(s,{total:4,matched:4,noCoordinates:2,sourceUnretrieved:1,withCoordinates:2});
  assert.equal(fixture.records.find(x=>x.id==='FA-003').source.retrieved,false);
});
test('T06: 0 records, 0 search hits and load error are distinct states',()=>{
  assert.equal(m.viewState({regionalCount:0,matchedCount:0}),'NO_REGION_RECORDS');
  assert.equal(m.viewState({regionalCount:4,matchedCount:0}),'NO_SEARCH_RESULTS');
  assert.equal(m.viewState({error:true,regionalCount:4,matchedCount:4}),'LOAD_ERROR');
  assert.equal(m.viewState({regionalCount:4,matchedCount:1}),'RESULTS');
});
test('T07: error takes precedence over 0-count fixture',()=>{
  assert.equal(m.viewState({error:true,regionalCount:0,matchedCount:0}),'LOAD_ERROR');
});
test('T08: source publication date UNKNOWN is not treated as latest',()=>{
  const x=fixture.records.find(x=>x.id==='FA-004');
  assert.equal(m.displayRaw(x.source.publishedAt),'未確認');
});
test('T09: no real coordinates are represented',()=>{
  for(const r of fixture.records){
    if(r.position.coordinates)assert.deepEqual(r.position.coordinates,{lat:0,lng:0});
  }
});
test('T10: all required attribute statuses are separately present',()=>{
  for(const r of fixture.records){
    for(const k of ['designation','boundaryEntrance','hazardConditions','operations','designatedArea']){
      assert.ok(r.attributes[k]?.state);assert.ok(r.attributes[k]?.reason);
    }
  }
});
