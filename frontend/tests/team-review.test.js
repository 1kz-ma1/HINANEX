import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { test } from "node:test";

const page = await readFile(new URL("../team-review.html", import.meta.url), "utf8");
const example = JSON.parse(await readFile(new URL("../mock/team-review-example.json", import.meta.url), "utf8"));
const match = /<script>([\s\S]*?)<\/script>/.exec(page);
assert.ok(match, "self-contained inline script is required");
const context = vm.createContext({
  window: { addEventListener() {} },
  URL, Date, Set, Blob, console,
});
vm.runInContext(match[1], context, { timeout: 2000 });
const check = vm.runInContext("validatePayload", context);
const merge = vm.runInContext("planReviewMerge", context);
const blankReview = () => clone(example.records[0].review);
const reviewed = (note, time="2026-10-22T04:00:00.000Z") => ({
  ...blankReview(), status:"in_progress", reviewer:"班員A", notes:note,
  reviewed_at:time
});


const clone = (x) => JSON.parse(JSON.stringify(x));

test("offline page is one HTML asset with no outbound requests or embed dependency", () => {
  assert.match(page, /connect-src 'none'/);
  assert.match(page, /default-src 'none'/);
  assert.match(page, /id="fileInput"/);
  assert.match(page, /id="exportButton"/);
  assert.match(page, /type="file"/);
  assert.match(page, /URL\.createObjectURL/);
  assert.match(page, /textContent/);
  assert.doesNotMatch(page, /<script[^>]+src=/);
  assert.doesNotMatch(page, /<link[^>]+stylesheet/);
  assert.doesNotMatch(page, /localStorage|sessionStorage|fetch\(|XMLHttpRequest|sendBeacon/);
  assert.doesNotMatch(page, /navigator\.serviceWorker|indexedDB/);
});

test("schema accepts only separate review notes and rejects approval", () => {
  assert.equal(check(clone(example)).records.length, 3);
  const approvals = [
    ["approved_for_map", true],
    ["data_promotion_authorized", true],
    ["official_facility_positions_accepted", 1],
  ];
  for (const [key, value] of approvals) {
    const bad = clone(example);
    bad.safety[key] = value;
    assert.throws(() => check(bad), /安全ゲート/);
  }
  const bad = clone(example);
  bad.records[0].review.status = "approved";
  assert.throws(() => check(bad), /作業状態/);
});

test("strict schema refuses private coordinates, unknown fields and credentials", () => {
  for (const field of ["gsi_reference_latitude", "abr_reference_longitude", "password", "facility_type_confirmed"]) {
    const bad = clone(example);
    bad.records[0][field] = "secret";
    assert.throws(() => check(bad), /施設の形式/);
  }
  const bad = clone(example);
  bad.records[0].sources.push({ title: "foo", url: "javascript:alert(1)" });
  assert.throws(() => check(bad), /HTTPS/);
  const credentialed = clone(example);
  credentialed.records[0].sources.push({title:"bad",url:"https://user:pass@example.com"});
  assert.throws(() => check(credentialed), /HTTPS/);
});

test("review states and zero values round-trip without meaning conversion", () => {
  const data = clone(example);
  data.records[1].review = {
    status: "evidence_found",
    checks: {official_source:true, identity:true, address:false, position_evidence:false},
    reviewer: "班員A", notes: "資料確認。位置承認は未実施。",
    evidence_url: "https://www.city.nagoya.jp/",
    reviewed_at: "2026-10-22T02:30:00.000Z",
  };
  assert.equal(check(data).records[1].review.status, "evidence_found");
  const revived = clone(data);
  assert.equal(check(revived).records[1].review.checks.position_evidence, false);
  assert.equal(revived.safety.official_facility_positions_accepted, 0);
});

test("rejects duplicate facility ids and unknown priority/issue codes", () => {
  const data = clone(example);
  data.records[1].id = data.records[0].id;
  assert.throws(() => check(data), /重複/);
  const badPriority = clone(example);
  badPriority.records[1].priority = "APPROVED";
  assert.throws(() => check(badPriority), /優先度/);
  const badIssue = clone(example);
  badIssue.records[1].issues = ["safe_for_flood"];
  assert.throws(() => check(badIssue), /要確認理由/);
});

test("rejects extra field of dataset and malformed review record", () => {
  const d = clone(example);
  d.dataset.coordinates = {latitude:35.0, longitude:136.9};
  assert.throws(() => check(d), /dataset/);
  const r = clone(example);
  r.records[0].review.site_position_approved = true;
  assert.throws(() => check(r), /review/);
  const t = clone(example);
  t.records[0].review.reviewed_at = "not-a-date";
  assert.throws(() => check(t), /日時/);
});

test("sample is labeled synthetic and has no official location claims", () => {
  assert.match(example.dataset.id, /SYNTHETIC/);
  assert.equal(example.safety.approved_for_map, false);
  assert.ok(example.records.every(r => r.name.includes("架空")));
  assert.ok(example.records.every(r => r.sources.length === 0));
});


test("atomic merge combines independent reviewers without changing safety flags", () => {
  const base = clone(example);
  const a=clone(example), b=clone(example);
  a.records[0].review=reviewed("Aの調査メモ");
  b.records[1].review=reviewed("Bの調査メモ");
  const before=JSON.stringify(base);
  const result=merge(base,[a,b]);
  assert.equal(result.applied,2);
  assert.equal(result.merged.records[0].review.notes,"Aの調査メモ");
  assert.equal(result.merged.records[1].review.notes,"Bの調査メモ");
  assert.equal(result.merged.safety.official_facility_positions_accepted,0);
  assert.equal(JSON.stringify(base),before);
});

test("conflicting same-facility edits abort entire merge without partial updates", () => {
  const base=clone(example), a=clone(example), b=clone(example);
  a.records[0].review=reviewed("Aの判断");
  b.records[0].review=reviewed("Bの判断");
  b.records[2].review=reviewed("他の施設");
  const before=JSON.stringify(base);
  assert.throws(()=>merge(base,[a,b]),/異なるレビュー/);
  assert.equal(JSON.stringify(base),before);
});

test("new source PDF links in base don't prevent merging older approved-shape review JSON", () => {
  const base=clone(example), old=clone(example);
  base.records[0].sources.push({
    title:"区の公式PDF（2026-09-01）",
    url:"https://www.city.nagoya.jp/official-list.pdf"
  });
  old.records[0].review=reviewed("元のJSONを使って確認");
  const result=merge(base,[old]);
  assert.equal(result.applied,1);
  // Incoming source lists are never copied. Newer official source links stay in base.
  assert.equal(result.merged.records[0].sources.length,1);
});

test("wrong fingerprint, changed facility metadata and approval changes fail closed", () => {
  const base=clone(example), wrong=clone(example);
  wrong.dataset.source_fingerprint="a".repeat(64);
  assert.throws(()=>merge(base,[wrong]),/異なるデータセット/);
  const other=clone(example);
  other.records[0].address="異なる住所";
  assert.throws(()=>merge(base,[other]),/施設情報/);
  const unsafe=clone(example);
  unsafe.safety.approved_for_map=true;
  assert.throws(()=>merge(base,[unsafe]),/安全ゲート/);
});

test("duplicate semantic reviews don't create conflicts just because timestamps differ", () => {
  const base=clone(example), incoming=clone(example);
  base.records[0].review=reviewed("同じ確認", "2026-10-22T03:00:00.000Z");
  incoming.records[0].review=reviewed("同じ確認", "2026-10-22T04:00:00.000Z");
  const result=merge(base,[incoming]);
  assert.equal(result.applied,0);
  assert.equal(result.merged.records[0].review.reviewed_at,"2026-10-22T04:00:00.000Z");
});

test("blank unreviewed files don't erase prior human evidence", () => {
  const base=clone(example), blank=clone(example);
  base.records[0].review=reviewed("先に確認済み");
  const result=merge(base,[blank]);
  assert.equal(result.applied,0);
  assert.equal(result.merged.records[0].review.notes,"先に確認済み");
  assert.throws(()=>merge(base,Array.from({length:21},()=>blank)),/1～20/);
});

test("incomplete evidence link is surfaced separately from site approval", () => {
  assert.match(page, /根拠資料URLが未記入/);
  assert.match(page, /参照点が100m以上/);
  assert.match(page, /id="mergeInput"/);
  assert.match(page, /multiple disabled/);
});

test("attention-first filter explicitly treats incomplete reviews as needing human follow-up", () => {
  const needs = vm.runInContext("requiresFollowUp", context);
  const rec = clone(example.records[0]);
  assert.equal(needs(rec),true);
  rec.review.status="evidence_found";
  rec.review.checks={official_source:true,identity:true,address:true,position_evidence:true};
  assert.equal(needs(rec),true);
  rec.review.evidence_url="https://www.city.nagoya.jp/";
  assert.equal(needs(rec),false);
  // This tests work-record completeness ONLY, not independent site acceptance.
  assert.equal(example.safety.approved_for_map,false);
});


test("saved-in-memory but not exported review cannot be overwritten by a new import", () => {
  const data=clone(example);
  context.testData=data;
  try {
    vm.runInContext("documentData=testData; selectedId=null; lastExportedOrImportedJson=JSON.stringify(testData)", context);
    const unexported=vm.runInContext("hasUnexportedReviewChanges", context);
    assert.equal(unexported(),false);
    data.records[0].review.notes="重要な班員の新規メモ";
    assert.equal(unexported(),true);
    assert.throws(
      () => vm.runInContext("importJson(JSON.stringify(testData))",context),
      /未書き出し/
    );
    assert.equal(data.records[0].review.notes,"重要な班員の新規メモ");
  } finally {
    vm.runInContext("documentData=null; selectedId=null; lastExportedOrImportedJson=null",context);
    delete context.testData;
  }
});

test("unsaved form edits are detectable before switching, merging, or exporting", () => {
  const data=clone(example);
  const rec=data.records[0];
  const ui={
    recordEditor:{hidden:false},
    reviewStatus:{value:rec.review.status},
    reviewer:{value:rec.review.reviewer},
    reviewNote:{value:rec.review.notes},
    evidenceUrl:{value:rec.review.evidence_url},
    checklist:{querySelectorAll(){return checks.map(k=>({
      dataset:{check:k}, checked:rec.review.checks[k]
    }));}},
  };
  const checks=["official_source","identity","address","position_evidence"];
  context.document={getElementById(id){return ui[id];}};
  context.testData=data;
  try {
    vm.runInContext("documentData=testData; selectedId=testData.records[0].id",context);
    const changed=vm.runInContext("hasUnappliedEditorChanges",context);
    assert.equal(changed(),false);
    ui.reviewNote.value="保存前のメモ";
    assert.equal(changed(),true);
    ui.reviewNote.value="";
    assert.equal(changed(),false);
    ui.evidenceUrl.value="https://www.city.nagoya.jp/source";
    assert.equal(changed(),true);
    ui.evidenceUrl.value="";
    ui.checklist.querySelectorAll=()=>[{dataset:{check:"identity"},checked:true}];
    assert.equal(changed(),true);
  } finally {
    vm.runInContext("documentData=null; selectedId=null; lastExportedOrImportedJson=null",context);
    delete context.testData;
    delete context.document;
  }
});

test("offline UI has unload protection and no misleading legacy merge language", () => {
  assert.match(page, /beforeunload/);
  assert.match(page, /hasUnexportedReviewChanges/);
  assert.match(page, /rejectUnappliedEditorChanges/);
  assert.doesNotMatch(page, /班員間の結果は自動統合されない/);
  assert.doesNotMatch(page, /\*\*同じ施設への異なる変更/);
});


// Run the actual inline handlers in an isolated mock DOM. Delayed file.text
// is manually released; no sleeps or browser claims.
function operationHarness(data) {
  const ui=new Map();
  const get=id=>{
    if(!ui.has(id)) ui.set(id,{value:"",hidden:false,disabled:false,dataset:{},
      querySelectorAll(){return [];},replaceChildren(){},append(){}});
    return ui.get(id);
  };
  let allowConfirm=false, clickFailure=false;
  const ctx=vm.createContext({URL:class extends URL{
    static createObjectURL(){return "blob:synthetic";}
    static revokeObjectURL(){}
  },Date,Set,Blob,console,setTimeout(){},
    window:{addEventListener(){},confirm(){return allowConfirm;}},
    document:{getElementById:get,body:{append(){}},
      createElement(){return {click(){if(clickFailure)throw Error("synthetic download failure");},remove(){}};}}
  });
  vm.runInContext(match[1],ctx);
  ctx.seed=data;
  vm.runInContext("documentData=seed;selectedId=seed.records[0].id;lastExportedOrImportedJson=JSON.stringify(seed);renderList=()=>{};fillEditor=()=>{};setSourceGroups=()=>{}",ctx);
  const rec=data.records[0];
  for(const [id,value] of [["reviewStatus",rec.review.status],["reviewer",rec.review.reviewer],["reviewNote",rec.review.notes],["evidenceUrl",rec.review.evidence_url]])get(id).value=value;
  get("checklist").querySelectorAll=()=>Object.entries(rec.review.checks).map(([check,checked])=>({dataset:{check},checked}));
  return {ctx,get,run:code=>vm.runInContext(code,ctx),confirm:()=>{allowConfirm=true;},failClick:()=>{clickFailure=true;}};
}
function delayedFile(data) {
  let release;
  const promise=new Promise(resolve=>{release=()=>resolve(JSON.stringify(data));});
  return {file:{size:100,text:()=>promise},release};
}
test("delayed merge refuses later editor input and retains both document and note",async()=>{
  const h=operationHarness(clone(example)), incoming=clone(example);
  incoming.records[1].review=reviewed("incoming");
  const delayed=delayedFile(incoming);h.ctx.files=[delayed.file];
  const before=h.run("JSON.stringify(documentData)");
  const merging=h.run("mergeFiles(files)");
  h.get("reviewNote").value="読込中の未反映メモ";
  delayed.release();await merging;
  assert.equal(h.run("JSON.stringify(documentData)"),before);
  assert.equal(h.get("reviewNote").value,"読込中の未反映メモ");
  assert.match(h.get("feedback").textContent,/現在の作業を保持/);
  assert.equal(h.run("activeFileRead"),null);
});
test("delayed merge rejects a second merge and new baseline read; later applied edits abort first merge",async()=>{
  const h=operationHarness(clone(example)), incoming=clone(example);
  incoming.records[1].review=reviewed("incoming");
  const delayed=delayedFile(incoming);h.ctx.files=[delayed.file];
  const merging=h.run("mergeFiles(files)");
  let reads=0;h.ctx.other={size:100,text:async()=>{reads++;return JSON.stringify(example);}};
  await h.run("mergeFiles([other])");
  assert.match(h.get("feedback").textContent,/進行中/);
  await h.run("loadFile(other)");
  assert.match(h.get("feedback").textContent,/進行中/);
  assert.equal(reads,0);
  h.get("reviewNote").value="読込中に反映";
  h.run("saveSelected()");
  const after=h.run("JSON.stringify(documentData)");
  delayed.release();await merging;
  assert.equal(h.run("JSON.stringify(documentData)"),after);
  assert.equal(h.run("documentData.records[0].review.notes"),"読込中に反映");
  assert.equal(h.run("documentData.records[1].review.notes"),"");
});
test("delayed baseline read cannot erase edits and untouched merge commits",async()=>{
  const h=operationHarness(clone(example)), incoming=clone(example);
  incoming.records[1].review=reviewed("incoming");
  const delayed=delayedFile(incoming);h.ctx.file=delayed.file;
  const reading=h.run("loadFile(file)");
  h.get("reviewNote").value="新メモ";
  delayed.release();await reading;
  assert.equal(h.run("documentData.records[1].review.notes"),"");
  assert.equal(h.get("reviewNote").value,"新メモ");
  h.get("reviewNote").value="";
  h.ctx.files=[{size:100,text:async()=>JSON.stringify(incoming)}];
  await h.run("mergeFiles(files)");
  assert.equal(h.run("documentData.records[1].review.notes"),"incoming");
  assert.equal(h.run("activeFileRead"),null);
});
test("download initiation or cancelled confirmation never clears dirty state; explicit current snapshot confirmation does",()=>{
  const h=operationHarness(clone(example));
  h.get("reviewNote").value="未保存";h.run("saveSelected()");
  h.run("exportJson()");
  assert.equal(h.run("hasUnexportedReviewChanges()"),true);
  h.run("confirmExport()");
  assert.equal(h.run("hasUnexportedReviewChanges()"),true);
  h.confirm();h.run("confirmExport()");
  assert.equal(h.run("hasUnexportedReviewChanges()"),false);
  h.get("reviewNote").value="追加";h.run("saveSelected()");h.run("exportJson()");
  h.get("reviewNote").value="さらに追加";h.run("saveSelected()");h.run("confirmExport()");
  assert.equal(h.run("hasUnexportedReviewChanges()"),true);
  h.failClick();h.run("exportJson()");h.run("confirmExport()");
  assert.equal(h.run("hasUnexportedReviewChanges()"),true);
  assert.equal(h.run("pendingExportJson"),null);
});
