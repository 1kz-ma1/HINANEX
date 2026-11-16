import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {createB2Session,isB2Loopback} from "./model.js";
import {getB2Fixture} from "./fixtures.js";

test("loopback-only HTTP origin: nonlocal, spoofed and HTTPS rejected",()=>{
  for(const ok of ["http://127.0.0.1:8000","http://localhost:8000","http://[::1]:8000"]){
    assert.equal(isB2Loopback(ok),true,ok);
  }
  for(const blocked of [null,"","https://127.0.0.1:8000","https://hinanex-staging.onrender.com",
    "http://127.0.0.1.evil.test","http://localhost.evil.test","javascript:alert(1)",
    "http://localhost:8000/path","http://user:pass@localhost:8000"]){
    assert.equal(isB2Loopback(blocked),false,String(blocked));
  }
});
test("synthetic fixture stays synthetic and uses only contract status names",()=>{
  const s=createB2Session(getB2Fixture("ready"));
  assert.equal(s.state,"READY");
  assert.equal(s.total,3);
  assert.deepEqual(s.counts,{CANDIDATE:1,EXCLUDED:1,UNKNOWN:1});
  assert.deepEqual(s.rows().map(r=>r.status),["CANDIDATE","UNKNOWN","EXCLUDED"]);
  for(const row of s.rows()){
    assert.equal(row.openStatus,null);
    assert.equal(row.safetyVerified,false);
    assert.match(row.sourceId,/^SYN-B2-/);
    assert.equal(row.address,null);
    assert.match(row.sourceTrace,/^fixture_row=/);
  }
});
test("UNKNOWN is not promoted by a synthetic CANDIDATE or EXCLUDED sibling",()=>{
  const rows=createB2Session(getB2Fixture("ready")).rows();
  assert.equal(rows[1].status,"UNKNOWN");
  assert.equal(rows[1].rawValue,null);
  assert.match(rows[1].reason,/判定不能/);
  assert.deepEqual(rows[1].unknowns,["元の指定条件","利用可能性","現在の開設状況"]);
});
test("distinct two max, explicit personal choice, no ranking or persistence",()=>{
  const s=createB2Session(getB2Fixture("ready"));
  assert.equal(s.choose("fake-a").ok,false);
  assert.equal(s.toggle("fake-a").ok,true);
  assert.equal(s.choose("fake-a").ok,false);
  assert.equal(s.toggle("fake-b").ok,true);
  assert.equal(s.toggle("fake-c").reason,"TWO_MAX");
  assert.deepEqual(s.selected().map(r=>r.id),["fake-a","fake-b"]);
  assert.equal(s.choose("fake-c").ok,false);
  assert.equal(s.choose("fake-b").ok,true);
  assert.equal(s.choice().id,"fake-b");
  assert.equal(s.choice().safetyVerified,false);
});
test("deselecting, clear, and filtering erase stale choice",()=>{
  const s=createB2Session(getB2Fixture("ready"));
  s.toggle("fake-a");s.toggle("fake-b");s.choose("fake-b");
  assert.equal(s.toggle("fake-a").ok,true);
  assert.equal(s.choice(),null);
  s.toggle("fake-a");s.choose("fake-a");
  assert.equal(s.setCriteria("","UNKNOWN").ok,true);
  assert.deepEqual(s.selected(),[]);
  assert.equal(s.choice(),null);
  assert.deepEqual(s.rows().map(r=>r.id),["fake-b"]);
  assert.equal(s.toggle("fake-a").reason,"NOT_VISIBLE");
  s.clear();
  assert.deepEqual(s.selected(),[]);
});
test("changing query clears comparison and NFKC search is display-only",()=>{
  const s=createB2Session(getB2Fixture("ready"));
  s.toggle("fake-a");s.toggle("fake-b");s.choose("fake-a");
  assert.equal(s.setCriteria("施設Ａ","ALL").ok,true);
  assert.deepEqual(s.rows().map(r=>r.id),["fake-a"]);
  assert.deepEqual(s.selected(),[]);
  assert.equal(s.choice(),null);
  assert.equal(s.setCriteria("","INVALID").reason,"INVALID_CRITERIA");
});
test("empty dataset and no query match stay different",()=>{
  const empty=createB2Session(getB2Fixture("empty"));
  assert.equal(empty.state,"EMPTY_DATASET");
  assert.equal(empty.total,0);
  assert.equal(empty.toggle("fake-a").ok,false);
  const active=createB2Session(getB2Fixture("ready"));
  assert.equal(active.setCriteria("架空ではないXYZ","ALL").ok,true);
  assert.equal(active.state,"READY");
  assert.equal(active.total,3);
  assert.equal(active.rows().length,0);
});
test("absence and simulated fetch failure are distinct states",()=>{
  const absent=createB2Session(getB2Fixture("none"));
  const error=createB2Session(getB2Fixture("load-error"));
  assert.equal(absent.state,"NO_SCENARIO");
  assert.equal(error.state,"LOAD_ERROR");
  assert.equal(error.total,0);
  assert.equal(error.toggle("fake-a").ok,false);
  assert.equal(error.choice(),null);
});
test("snapshot replacement creates a fresh session without old selection",()=>{
  const old=createB2Session(getB2Fixture("ready"));
  old.toggle("fake-a");old.toggle("fake-b");old.choose("fake-b");
  const next=createB2Session(getB2Fixture("empty"));
  assert.equal(next.state,"EMPTY_DATASET");
  assert.deepEqual(next.selected(),[]);
  assert.equal(next.choice(),null);
});
test("source mismatch is fail closed, even with otherwise plausible record",()=>{
  const invalid=createB2Session(getB2Fixture("invalid"));
  assert.equal(invalid.state,"INVALID");
  assert.equal(invalid.rows().length,0);
});
test("mismatched hazard or region, and non-synthetic sources, fail closed",()=>{
  for(const mutate of [
    x=>x.hazardScope="flood",
    x=>x.regionCode="13123",
    x=>x.syntheticOnly=false,
    x=>x.sourceId="https://example.test/official",
    x=>x.fixtureId="live-edogawa",
    x=>x.kind="LIVE_EXPORT",
    x=>x.records[0].hazardScope="OTHER",
    x=>x.records[0].sourceId="SYN-B2-OTHER"
  ]){
    const f=getB2Fixture("ready");mutate(f);
    const s=createB2Session(f);
    assert.equal(s.state,"INVALID",JSON.stringify(f).slice(0,100));
    assert.deepEqual(s.selected(),[]);
  }
});
test("duplicate and malformed ID, status, and null semantics fail closed",()=>{
  for(const mutate of [
    x=>x.records[1].id="fake-a",
    x=>x.records[1].id=" ",
    x=>x.records[0].status="SAFE",
    x=>x.records[0].address=42,
    x=>x.records[0].reason="",
    x=>x.records[0].sourceTrace=null,
    x=>x.records[0].openStatus="OPEN",
    x=>x.records[0].safetyVerified=true,
    x=>x.records[0].rawValue=0,
    x=>x.records[1].unknowns=["", "x"],
    x=>x.records="wrong-shape"
  ]){
    const f=getB2Fixture("ready");mutate(f);
    assert.equal(createB2Session(f).state,"INVALID");
  }
});
test("returned display rows cannot mutate source fixture status",()=>{
  const f=getB2Fixture("ready");
  const s=createB2Session(f);
  f.records[1].status="CANDIDATE";
  assert.equal(s.rows()[1].status,"UNKNOWN");
  assert.equal(Object.isFrozen(s.rows()[1]),true);
});
test("HTML uses textContent and native controls, no silent live-data access",()=>{
  const html=readFileSync(fileURLToPath(new URL("./index.html",import.meta.url)),"utf8");
  assert.match(html,/id="safetyNotice"/);
  assert.match(html,/訓練用の完全な合成データ/);
  assert.match(html,/id="choiceMessage"/);
  assert.match(html,/aria-pressed/);
  assert.match(html,/aria-live="polite"/);
  assert.match(html,/textContent/);
  assert.match(html,/isB2Loopback\(window\.location\.origin\)/);
  assert.doesNotMatch(html,/\bfetch\s*\(|\bXMLHttpRequest\b|\blocalStorage\b|\bsessionStorage\b|\bgeolocation\b|\binnerHTML\b|\blocation\.search\b/);
});
test("fixture contains no real facility names, coordinates or official source links",()=>{
  const fixture=readFileSync(fileURLToPath(new URL("./fixtures.js",import.meta.url)),"utf8");
  assert.doesNotMatch(fixture,/https?:\/\/|\blatitude\b|\blongitude\b/);
  const values=getB2Fixture("ready");
  assert.equal(values.regionCode,"TEST_ONLY");
  assert.ok(values.records.every(r=>r.name.startsWith("架空施設")));
  assert.ok(values.records.every(r=>!Object.hasOwn(r,"coordinates")));
});
