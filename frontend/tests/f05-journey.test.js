import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {buildF05Journey, isLocalPreviewOrigin} from "../src/f05-journey-model.js";

test("F05 F01 starts independently and F02 requires an explicit region",()=>{
  const state=buildF05Journey({origin:"http://127.0.0.1:8000"});
  assert.equal(state.f01Href,"/gis/gis/");
  assert.equal(state.status,"REGION_UNSELECTED");
  assert.equal(state.f02Href,null);
  assert.equal(state.routeHref,null);
});
test("Only explicitly chosen Edogawa gets a local F02 link",()=>{
  const state=buildF05Journey({regionCode:"13123",origin:"http://localhost:8000"});
  assert.equal(state.status,"LOCAL_F02_LINK");
  assert.equal(state.f02Href,"/frontend/f02.html");
  assert.equal(state.regionCode,"13123");
  for(const code of [null,"","15100","23100",13123," 13123 ","13123?facility=a"]){
    const wrong=buildF05Journey({regionCode:code,origin:"http://localhost:8000"});
    assert.equal(wrong.f02Href,null);
    assert.equal(wrong.regionCode,null);
  }
});
test("Origin spoofing and nonlocal staging cannot expose F02 link",()=>{
  for(const origin of [null,"", "https://hinanex-staging.onrender.com","http://127.0.0.1.evil.example",
    "http://localhost.evil.example","https://127.0.0.1:8000","javascript:alert(1)"]){
    assert.equal(isLocalPreviewOrigin(origin),false,String(origin));
    assert.equal(buildF05Journey({regionCode:"13123",origin}).f02Href,null);
  }
  for(const origin of ["http://127.0.0.1:8000","http://localhost:8000","http://[::1]:8000"]){
    assert.equal(isLocalPreviewOrigin(origin),true,origin);
  }
});
test("Changing region clears stale selection and never sends hazard or facility IDs",()=>{
  const before=buildF05Journey({regionCode:"13123",origin:"http://localhost:8000"});
  const after=buildF05Journey({regionCode:"",origin:"http://localhost:8000"});
  assert.equal(before.f02Href,"/frontend/f02.html");
  assert.equal(after.f02Href,null);
  const state=buildF05Journey({regionCode:"13123",origin:"http://localhost:8000",
    facilityId:"unsafe",hazardScore:10,latitude:35.5});
  assert.equal(state.facilityId,null);
  assert.equal(state.floodSuitability,null);
  assert.equal(state.currentOpenStatus,null);
  assert.equal(state.routeHref,null);
});
test("Prototype shows safety restrictions, no automatic F02 href, and no storage/network",()=>{
  const html=readFileSync(fileURLToPath(new URL("../prototypes/f05-flood-journey/index.html",import.meta.url)),"utf8");
  assert.match(html,/id="regionSelect"/);
  assert.match(html,/<option value="13123">/);
  assert.match(html,/id="f01Link"[^>]+href="\/gis\/gis\/"/);
  assert.match(html,/id="f02Link"[^>]+hidden/);
  assert.doesNotMatch(html,/id="f02Link"[^>]+href=/);
  assert.match(html,/参考経路は未提供/);
  assert.match(html,/F02の実施設表示は一般公開が未承認/);
  assert.match(html,/aria-live="polite"/);
  assert.match(html,/rel="noopener noreferrer"/);
  assert.doesNotMatch(html,/\bfetch\s*\(|\bgeolocation\b|\bsessionStorage\b|\bsetItem\s*\(/);
});
