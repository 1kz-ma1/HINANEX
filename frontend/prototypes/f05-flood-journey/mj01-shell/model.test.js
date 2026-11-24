import test from "node:test";
import assert from "node:assert/strict";
import {createJourney,isB2Loopback} from "./model.js";
import {fixedSnapshot} from "./fixtures.js";
const act=(j,type,fields={})=>j.dispatch({type,...fields},j.view().revision);
function reach(j,key="pet"){
  for(const [type,fields] of [["START"],["CONDITION",{key}],["SHOW"],["CONTINUE"]])assert.equal(act(j,type,fields),true);
}
function choose(j){
  assert.equal(act(j,"TOGGLE",{id:"mj01-a"}),true);
  assert.equal(act(j,"TOGGLE",{id:"mj01-b"}),true);
  assert.equal(act(j,"COMPARE"),true);
  assert.equal(act(j,"CHOOSE",{id:"mj01-b"}),true);
}
test("explicit start and condition; no implicit results",()=>{
  const j=createJourney();
  assert.equal(act(j,"SHOW"),false);assert.equal(act(j,"START"),true);
  assert.equal(act(j,"SHOW"),false);assert.equal(act(j,"CONDITION",{key:"__proto__"}),false);
  assert.equal(act(j,"CONDITION",{key:"pet"}),true);
  assert.deepEqual(j.view().rows,[]);assert.equal(act(j,"SHOW"),true);
  assert.equal(j.view().step,"J03");assert.equal(j.view().rows.length,3);
});
test("comparison max two; explicit choice; UNKNOWN unchanged",()=>{
  const j=createJourney();reach(j);
  assert.equal(act(j,"COMPARE"),false);assert.equal(act(j,"CHOOSE",{id:"mj01-a"}),false);
  assert.equal(act(j,"TOGGLE",{id:"mj01-a"}),true);assert.equal(act(j,"TOGGLE",{id:"mj01-b"}),true);
  assert.equal(act(j,"TOGGLE",{id:"mj01-c"}),false);assert.equal(act(j,"COMPARE"),true);
  assert.equal(j.view().complete,false);assert.equal(act(j,"CHOOSE",{id:"mj01-c"}),false);
  assert.equal(act(j,"CHOOSE",{id:"mj01-b"}),true);
  assert.equal(j.view().choice.status,"UNKNOWN");assert.equal(j.view().choice.safetyVerified,false);
  assert.equal(j.view().choice.openStatus,null);assert.equal(j.view().complete,true);
  assert.deepEqual(j.view().choice.unknowns,fixedSnapshot("pet").records[1].unknowns);
});
test("condition change clears all and loads new fixed snapshot",()=>{
  const j=createJourney();reach(j);choose(j);const old=j.view().revision;
  assert.equal(act(j,"CHANGE"),true);assert.deepEqual(j.view().rows,[]);assert.equal(j.view().choice,null);
  assert.equal(j.dispatch({type:"CHOOSE",id:"mj01-b"},old),false);
  act(j,"CONDITION",{key:"step"});act(j,"SHOW");
  assert.equal(j.view().rows[0].status,"UNKNOWN");assert.equal(j.view().rows[1].status,"CANDIDATE");
  assert.deepEqual(j.view().selected,[]);assert.equal(j.view().choice,null);
});
for(const type of ["FAIL","END","BACK"])test(type+" discards old selection; stale action rejected",()=>{
  const j=createJourney();reach(j);choose(j);const old=j.view().revision;
  assert.equal(act(j,type),true);assert.deepEqual(j.view().selected,[]);assert.equal(j.view().choice,null);
  assert.equal(j.view().complete,false);assert.equal(j.dispatch({type:"CHOOSE",id:"mj01-b"},old),false);
  if(type==="BACK"){assert.equal(j.view().step,"J04");assert.equal(j.view().rows.length,3);}
  else {assert.deepEqual(j.view().rows,[]);assert.equal(j.view().condition,null);assert.equal(act(j,"START"),true);assert.deepEqual(j.view().rows,[]);}
});
test("fixed fixture snapshots isolated; invalid key rejected",()=>{
  const a=fixedSnapshot("pet");a.records[1].status="CANDIDATE";
  assert.equal(fixedSnapshot("pet").records[1].status,"UNKNOWN");assert.equal(fixedSnapshot("bogus"),null);
  assert.equal(fixedSnapshot("__proto__"),null);
});
test("loopback allowlist",()=>{
  for(const o of ["http://127.0.0.1:8000","http://localhost:8080","http://[::1]:8000"])assert.equal(isB2Loopback(o),true);
  for(const o of ["https://localhost","http://127.0.0.2","http://example.com","null","http://localhost:8000/path"])assert.equal(isB2Loopback(o),false);
});
