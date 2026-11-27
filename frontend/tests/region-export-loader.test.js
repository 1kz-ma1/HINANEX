import test from "node:test";
import assert from "node:assert/strict";

import { createRegionExportController } from "../src/region-export-loader.js";

function response(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return structuredClone(payload);
    },
  };
}

function payloadFor(code, name) {
  return { region: { code, name } };
}

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test("江戸川・新潟・名古屋をD runtime URLから順番に取得する", async () => {
  const fixtures = new Map([
    ["../pipeline/data/output/edogawa.json", payloadFor("13123", "東京都江戸川区")],
    ["../pipeline/data/output/niigata.json", payloadFor("15100", "新潟県新潟市")],
    ["../pipeline/data/output/nagoya.json", payloadFor("23100", "愛知県名古屋市")],
  ]);
  const requested = [];
  const rendered = [];
  const controller = createRegionExportController({
    async fetchImpl(url) {
      requested.push(url);
      return response(fixtures.get(url));
    },
    onSuccess(payload) {
      rendered.push(payload.region.code);
    },
  });

  await controller.selectRegion("13123");
  await controller.selectRegion("15100");
  await controller.selectRegion("23100");

  assert.deepEqual(requested, [...fixtures.keys()]);
  assert.deepEqual(rendered, ["13123", "15100", "23100"]);
});

test("後から完了した旧地域の結果で現在表示を上書きしない", async () => {
  const edogawa = deferred();
  const niigata = deferred();
  const rendered = [];
  const controller = createRegionExportController({
    fetchImpl(url) {
      return url.includes("edogawa") ? edogawa.promise : niigata.promise;
    },
    onSuccess(payload) {
      rendered.push(payload.region.code);
    },
  });

  const oldRequest = controller.selectRegion("13123");
  const currentRequest = controller.selectRegion("15100");
  niigata.resolve(response(payloadFor("15100", "新潟県新潟市")));
  await currentRequest;
  edogawa.resolve(response(payloadFor("13123", "東京都江戸川区")));
  const oldResult = await oldRequest;

  assert.deepEqual(rendered, ["15100"]);
  assert.equal(oldResult.status, "stale");
});

test("選択地域と取得JSONのregion.code不一致をerrorにする", async () => {
  let errorMessage = null;
  const controller = createRegionExportController({
    async fetchImpl() {
      return response(payloadFor("15100", "新潟県新潟市"));
    },
    onError(error) {
      errorMessage = error.message;
    },
  });

  const result = await controller.selectRegion("13123");

  assert.equal(result.status, "error");
  assert.match(errorMessage, /一致しません/);
});

test("HTTP error時にerror callbackへ渡す", async () => {
  let errorMessage = null;
  const controller = createRegionExportController({
    async fetchImpl() {
      return response({}, { ok: false, status: 404 });
    },
    onError(error) {
      errorMessage = error.message;
    },
  });

  const result = await controller.selectRegion("23100");

  assert.equal(result.status, "error");
  assert.match(errorMessage, /HTTP 404/);
});

// Run the actual app coordinator and regional controller with controlled
// promises, a transport that ignores abort, and rendering/DOM stubs.
async function appLoads() {
  const {readFile}=await import("node:fs/promises");
  const {assertRegionMatches,getPayloadRegionCode}=await import("../src/region-export-source.js");
  const app=await readFile(new URL("../src/app.js",import.meta.url),"utf8");
  const start=app.indexOf("function setSourceStatus(");
  const end=app.indexOf('closeEvidence.addEventListener("click"',start);
  assert.ok(start>=0 && end>start);
  const requests=[];
  const fetchImpl=url=>{const d=deferred();requests.push({url,...d});return d.promise;};
  const status={textContent:"",dataset:{}}, regionSelect={value:"13123"};
  const regionName={},generatedAt={},schemaVersion={},demoNotice={};
  const state={display:null,active:null,scenario:null};
  const clearRegionContent=()=>{state.display=null;state.scenario=null;};
  const bindings={
    sourceStatus:status,regionSelect,regionName,generatedAt,schemaVersion,demoNotice,
    fetch:fetchImpl,createRegionExportController:opts=>createRegionExportController({...opts,fetchImpl}),
    assertRegionMatches,getPayloadRegionCode,buildRegionExportViewModel:p=>p,
    renderPage:p=>{state.display=p.region.code;state.scenario="ready";},
    renderLoading:source=>{clearRegionContent();state.active=source.code;status.dataset.tone="loading";},
    renderError:(error,source,{isSynthetic=false}={})=>{clearRegionContent();state.scenario=isSynthetic?"demo-error":"error";},
    clearRegionContent,setActiveRegion:code=>{state.active=code;},
    renderFloodScenario:v=>{state.scenario=v.uiState;}
  };
  const api=new Function(...Object.keys(bindings),app.slice(start,end)+
    "\nreturn {loadDemoRegionExport,selectRegion,loadSelectedRegion,loadManualRegionExport};")(...Object.values(bindings));
  const snapshot=()=>JSON.stringify({state,status,regionName,generatedAt,schemaVersion,demoNotice,regionSelect});
  return {api,requests,state,status,snapshot,regionName};
}

// Cross product of source type, old/new outcome, and completion order.
// A stale completion must not alter either a pending or a settled latest load.
for (const older of ["demo", "region", "file"]) {
  for (const newer of ["demo", "region", "file"]) {
    for (const oldSucceeds of [true, false]) {
      for (const newSucceeds of [true, false]) {
        for (const oldFirst of [true, false]) {
          test("F01 latest intent wins: " + older + " -> " + newer +
            "; old " + (oldSucceeds ? "success" : "failure") +
            "; new " + (newSucceeds ? "success" : "failure") +
            "; " + (oldFirst ? "old completes first" : "new completes first"), async () => {
            const h = await appLoads();
            function start(kind, code) {
              if (kind === "file") {
                const d = deferred();
                const target = {value:"selected.json", files:[{name:code+".json", text:()=>d.promise}]};
                const done = h.api.loadManualRegionExport({target});
                assert.equal(target.value, "", "file picker released synchronously");
                return {done, finish:ok=>d.resolve(ok?JSON.stringify(payloadFor(code,code)):"invalid JSON")};
              }
              const done = kind==="demo" ? h.api.loadDemoRegionExport() : h.api.selectRegion(code);
              const req = h.requests.at(-1);
              return {done, finish:ok=>req.resolve(response(payloadFor(code,code),{ok,status:ok?200:503}))};
            }
            const old = start(older, "13123"), current = start(newer, "15100");
            assert.equal(h.state.display, null);
            assert.equal(h.status.dataset.tone, "loading");
            if (oldFirst) {
              const pending = h.snapshot();
              old.finish(oldSucceeds); await old.done;
              assert.equal(h.snapshot(), pending, "stale completion must preserve latest pending state");
            }
            current.finish(newSucceeds); await current.done;
            assert.equal(h.status.dataset.tone, newSucceeds ? (newer==="demo"?"demo":"success") : "error");
            assert.equal(h.state.display, newSucceeds ? "15100" : null);
            const before = h.snapshot();
            if (!oldFirst) {
              old.finish(oldSucceeds); await old.done;
              assert.equal(h.snapshot(), before, "stale completion must preserve latest settled state");
            }
            assert.equal(h.requests.filter(r=>r.url.includes("/mock/")).length,
              Number(older==="demo")+Number(newer==="demo"), "no automatic demo fallback");
          });
        }
      }
    }
  }
}

test("F01 delayed demo response.json cannot supersede explicit region reload",async()=>{
  const h=await appLoads(),body=deferred(),entered=deferred();
  const old=h.api.loadDemoRegionExport();
  h.requests[0].resolve({ok:true,json(){entered.resolve();return body.promise;}});
  await entered.promise;
  await h.api.loadManualRegionExport({target:{files:[],value:""}});
  const current=h.api.loadSelectedRegion();
  h.requests[1].resolve(response(payloadFor("13123","region")));await current;
  assert.equal(h.status.dataset.tone,"success");
  const before=h.snapshot();
  body.resolve(payloadFor("15100","old demo"));await old;
  assert.equal(h.snapshot(),before);
});

test("F01 cancelled picker keeps demo; current file failure clears previous display",async()=>{
  const h=await appLoads(),demo=h.api.loadDemoRegionExport();
  await h.api.loadManualRegionExport({target:{files:[],value:""}});
  h.requests[0].resolve(response(payloadFor("13123","demo")));await demo;
  assert.equal(h.status.dataset.tone,"demo");
  const file=h.api.loadManualRegionExport({target:{files:[{name:"broken.json",text:async()=>"invalid"}],value:"broken.json"}});
  assert.equal(h.state.display,null);
  assert.equal(h.regionName.textContent,"JSONを読み込み中");
  await file;assert.equal(h.status.dataset.tone,"error");
  assert.equal(h.state.display,null);
});

test("F01 same file can be reselected while its old read is pending; stale rejection cannot clear the picker", async () => {
  const h = await appLoads();
  let rejectOld;
  const pending = new Promise((resolve, reject) => { rejectOld = reject; });
  const target = {value:"same.json", files:[{name:"same.json",text:()=>pending}]};
  const old = h.api.loadManualRegionExport({target});
  assert.equal(target.value, "");
  target.value = "same.json";
  target.files = [{name:"same.json",text:async()=>JSON.stringify(payloadFor("15100","new read"))}];
  await h.api.loadManualRegionExport({target});
  assert.equal(target.value, "");
  assert.equal(h.state.display,"15100");
  assert.equal(h.status.dataset.tone,"success");
  const before = h.snapshot();
  // Model a later picker selection whose change event has not yet been handled.
  target.value = "next.json";
  rejectOld(new Error("old file read failed")); await old;
  assert.equal(h.snapshot(), before);
  assert.equal(target.value, "next.json");
});
