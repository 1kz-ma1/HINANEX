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


// Fully synthetic facility names and addresses. The municipality PDF URLs
// are only used to simulate exact origin binding, not to claim source facts.
const pdfUrls=[
  "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai16tenpaku0809.pdf",
  "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai13moriyama0809.pdf",
  "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai14midori0806.pdf",
  "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai02higashi0809.pdf",
  "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai05nakamura0804.pdf"
];
// Actual provider ward labels/URLs only; facilities/addresses stay fictional.
const fakeWards=["天白区","天白区","天白区","守山区","守山区","守山区","緑区","東区","中村区"];
const pdfByFacility=[0,0,0,1,1,1,2,3,4];
function makeTriageFixture() {
  const review=clone(example);
  review.dataset.id="nagoya-stage7-P1";
  review.records=fakeWards.map((ward,i)=>{
    const r=clone(example.records[i%example.records.length]);
    r.id="synthetic-"+i;
    r.name="架空検証施設"+i;
    r.address="架空町"+i+"-10";
    r.priority="P1";
    r.sources=[{title:"合成テスト用公式リンク紐付け",url:pdfUrls[pdfByFacility[i]]}];
    return r;
  });
  const report={
    report_kind:"NAGOYA_P1_PDF_ROW_DIFF_CANDIDATES_NOT_OFFICIAL_APPROVAL",
    status:"HUMAN_REVIEW_REQUIRED",
    previous_captured_at_utc:"2026-10-21T01:00:00Z",
    current_captured_at_utc:"2026-10-22T01:00:00Z",
    source_changed_count:1,
    facility_count:9,
    baseline_extract_matched_count:9,
    current_extract_matched_count:9,
    row_changed_candidate_count:0,
    unresolved_extraction_count:0,
    human_review_required_count:3,
    facilities:review.records.map((r,i)=>({
      ward:fakeWards[i], name:r.name,address:r.address,
      source_url:pdfUrls[pdfByFacility[i]],
      source_bytes_changed:i<3,
      classification:i<3
        ?"ROW_TEXT_UNCHANGED_SOURCE_CHANGED_REVIEW_REQUIRED"
        :"SOURCE_BYTES_UNCHANGED_NOT_OFFICIAL_APPROVAL"
    })),
    safety:{approved_for_map:false,data_promotion_authorized:false,
      official_facility_positions_accepted:0},
    warning:"Synthetic PDF row diff report, no source meaning or site approved"
  };
  return {review, report};
}
const checkTriage=vm.runInContext("validateTriageReport",context);
const filterTriage=vm.runInContext("triageMatches",context);
test("real report schema overlays nine P1 records without mutating source reviews", () => {
  const {review,report}=makeTriageFixture();
  const before=JSON.stringify(review);
  const matching=checkTriage(report,review);
  assert.equal(matching.size,9);
  assert.equal(JSON.stringify(review),before);
  assert.equal(report.safety.official_facility_positions_accepted,0);
  const first=matching.get(review.records[0].id);
  const other=matching.get(review.records[3].id);
  assert.equal(filterTriage(first,"review_required"),true);
  assert.equal(filterTriage(first,"source_changed"),true);
  assert.equal(filterTriage(first,"row_changed"),false);
  assert.equal(filterTriage(other,"no_diff"),true);
  assert.equal(filterTriage(other,"review_required"),false);
});
test("actual-style zero-change report keeps all reviews intact; no promotion",()=>{
  const {review,report}=makeTriageFixture();
  report.facilities.forEach(row=>{
    row.source_bytes_changed=false;
    row.classification="SOURCE_BYTES_UNCHANGED_NOT_OFFICIAL_APPROVAL";
  });
  report.status="EXTRACTED_ROW_TEXT_UNCHANGED_NOT_APPROVAL";
  report.source_changed_count=0;
  report.human_review_required_count=0;
  review.records[0].review.status="evidence_found";
  review.records[0].review.notes="架空レビュー：元の記録";
  assert.equal(checkTriage(report,review).size,9);
  assert.equal(review.records[0].review.status,"evidence_found");
  assert.equal(review.records[0].review.notes,"架空レビュー：元の記録");
  assert.equal(review.safety.approved_for_map,false);
});
test("triage rejects approval, extra coordinate, wrong source URL, identity and forged counts",()=>{
  const scenarios=[
    d=>{d.report.safety.approved_for_map=true;},
    d=>{d.report.facilities[0].candidate_coordinates={lat:35,long:136};},
    d=>{d.report.facilities[0].source_url="https://external.example/shelter.pdf";},
    d=>{d.report.facilities[0].source_url="https://www.city.nagoya.jp.evil.example/a.pdf";},
    d=>{d.report.facilities[0].name="異なる施設";},
    d=>{d.report.facilities[1].name=d.report.facilities[0].name;
        d.report.facilities[1].address=d.report.facilities[0].address;},
    d=>{d.report.row_changed_candidate_count=1;},
    d=>{d.report.human_review_required_count=0;},
    d=>{d.report.source_changed_count=0;},
    d=>{d.report.facilities.pop();},
    d=>{d.report.is_safe_for_flood=true;},
    d=>{d.report.current_captured_at_utc="not-a-date";},
    d=>{d.review.dataset.id="edogawa-something";},
    d=>{d.review.records[0].sources=[];},
    d=>{d.report.facilities[0].classification="APPROVED";},
    d=>{d.report.facilities[0].source_bytes_changed=false;},
    d=>{d.report.status="EXTRACTED_ROW_TEXT_UNCHANGED_NOT_APPROVAL";},
  ];
  for(let i=0;i<scenarios.length;i++){
    const d=makeTriageFixture();
    scenarios[i](d);
    assert.throws(()=>checkTriage(d.report,d.review),undefined, "case "+i);
  }
});
test("all five PDF triage statuses retain distinct human review semantics",()=>{
  const {review,report}=makeTriageFixture();
  report.facilities[0].classification="ROW_TEXT_CHANGED_HUMAN_REVIEW_REQUIRED";
  report.row_changed_candidate_count=1;
  assert.equal(checkTriage(report,review).size,9);
  assert.equal(filterTriage(report.facilities[0],"row_changed"),true);
  report.facilities[0].classification="ROW_EXTRACTION_UNRESOLVED_REVIEW_REQUIRED";
  report.row_changed_candidate_count=0;
  report.unresolved_extraction_count=1;
  report.current_extract_matched_count=8;
  assert.equal(checkTriage(report,review).size,9);
  assert.equal(filterTriage(report.facilities[0],"unresolved"),true);
});
test("triage is optional, offline and not part of reviewer JSON export",()=>{
  assert.match(page,/id="triageInput"/);
  assert.match(page,/id="triageFilter" disabled/);
  assert.match(page,/triageReport=null;triageByFacility=new Map/);
  assert.match(page,/const json=JSON\.stringify\(documentData,null,2\)/);
  assert.doesNotMatch(page, /fetch\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage/);
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

test("triage accepts real calendar UTC boundaries and rejects impossible or normalized dates",()=>{
  for(const date of ["2024-02-29T00:00:00Z","2026-12-31T23:59:59Z","2026-01-01T00:00:00Z"]){
    const {review,report}=makeTriageFixture();
    report.previous_captured_at_utc=date;report.current_captured_at_utc=date;
    assert.equal(checkTriage(report,review).size,9);
  }
  for(const date of ["2026-02-29T00:00:00Z","2026-02-30T00:00:00Z","2026-04-31T00:00:00Z","2026-13-01T00:00:00Z","2026-00-01T00:00:00Z","2026-01-00T00:00:00Z","2026-01-01T24:00:00Z","2026-01-01T23:60:00Z","2026-01-01T23:59:60Z","0000-01-01T00:00:00Z"]){
    for(const key of ["previous_captured_at_utc","current_captured_at_utc"]){
      const {review,report}=makeTriageFixture();
      report[key]=date;
      assert.throws(()=>checkTriage(report,review),/日時/,date);
    }
  }
});
test("triage rejects same PDF split into forged wards, swapped provider ward labels, and source count tampering",()=>{
  const {review,report}=makeTriageFixture();
  const split=clone(report);
  split.facilities[1].ward="架空の区";
  split.source_changed_count=2;
  assert.throws(()=>checkTriage(split,review),/区の対応/);
  const swapped=clone(report);
  swapped.facilities.forEach(row=>{if(row.ward==="天白区")row.ward="守山区";else if(row.ward==="守山区")row.ward="天白区";});
  assert.throws(()=>checkTriage(swapped,review),/区の対応/);
  const count=clone(report);count.source_changed_count=2;
  assert.throws(()=>checkTriage(count,review),/集計値/);
});
test("invalid or stale PDF import preserves previous triage, baseline and review data",async()=>{
  const {review,report}=makeTriageFixture(), h=operationHarness(review);
  h.ctx.payload=JSON.stringify(report);
  h.run("importTriageJson(payload)");
  const previous=h.run("triageReport"), priorIndex=h.run("triageByFacility");
  const before=h.run("JSON.stringify(documentData)");
  const bad=clone(report);bad.facilities[1].ward="架空の区";bad.source_changed_count=2;
  h.ctx.invalid=JSON.stringify(bad);
  assert.throws(()=>h.run("importTriageJson(invalid)"),/区の対応/);
  assert.equal(h.run("triageReport"),previous);
  assert.equal(h.run("triageByFacility"),priorIndex);
  const invalidDate=clone(report);invalidDate.current_captured_at_utc="2026-02-30T00:00:00Z";
  h.ctx.invalid=JSON.stringify(invalidDate);
  assert.throws(()=>h.run("importTriageJson(invalid)"),/日時/);
  assert.equal(h.run("triageReport"),previous);
  assert.equal(h.run("triageByFacility"),priorIndex);
  const delayed=delayedFile(report);h.ctx.file=delayed.file;
  const reading=h.run("loadTriageFile(file)");
  h.get("reviewNote").value="遅延中の新しいメモ";
  delayed.release();await reading;
  assert.equal(h.run("triageReport"),previous);
  assert.equal(h.run("triageByFacility"),priorIndex);
  assert.equal(h.run("JSON.stringify(documentData)"),before);
  assert.equal(h.get("reviewNote").value,"遅延中の新しいメモ");
});


// Actual HTTP + Chrome, actual OS temporary JSON files and Blob download.
// Synthetic fixture only; no real facility, private data or external request.
test("team review real HTTP Chrome preserves edits and round-trips an actual downloaded JSON",
  {timeout:120000}, async t => {
    const {default:fs} = await import("node:fs/promises");
    const {default:os} = await import("node:os");
    const {default:path} = await import("node:path");
    const {default:http} = await import("node:http");
    const {default:helper} = await import("./helpers/http-chrome.cjs");
    const bin = helper.browserBinary();
    if (!bin) {
      if (process.env.CI || process.env.TEAM_REVIEW_REQUIRE_CHROME === "1")
        throw Error("Real Chrome required for team review regression");
      t.skip("Chrome unavailable locally; no browser PASS");return;
    }
    const temp=await fs.mkdtemp(path.join(os.tmpdir(),"team-review-http-"));
    let browser,server;
    const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
    try {
      const input=path.join(temp,"baseline.json");
      const downloads=path.join(temp,"downloads");
      await fs.writeFile(input,JSON.stringify(example),"utf8");
      await fs.mkdir(downloads);
      const requests=[];
      server=http.createServer((req,res)=>{
        requests.push(req.url);
        if(req.method==="GET"&&req.url==="/team-review.html"){
          res.writeHead(200,{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"});
          res.end(page);
        }else{res.writeHead(404);res.end();}
      });
      await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"127.0.0.1",resolve);});
      const origin="http://127.0.0.1:"+server.address().port;
      const url=origin+"/team-review.html";
      browser=await helper.launchChrome(bin);
      const {command,evaluate,ws}=browser;
      await command("Page.enable");await command("Runtime.enable");await command("Network.enable");await command("DOM.enable");
      await command("Page.setDownloadBehavior",{behavior:"allow",downloadPath:downloads});
      async function ready(condition,label){
        for(let i=0;i<100;i++){
          if(await evaluate(condition))return;
          await pause(100);
        }
        throw Error("Timed out waiting for "+label);
      }
      async function navigate(){
        const result=await command("Page.navigate",{url});
        assert.ok(!result.errorText,result.errorText);
        // Only retry transient navigation execution-context errors.
        const end=Date.now()+10000;
        while(Date.now()<end){
          try{
            if(await evaluate("location.href==="+JSON.stringify(url)+" && document.readyState==='complete' && document.querySelector('#workArea')?.hidden===true"))return;
          }catch(error){
            if(!/Execution context was destroyed|Cannot find context with specified id|Inspected target navigated/i.test(error.message))throw error;
          }
          await pause(100);
        }
        throw Error("Fresh empty team review document not ready");
      }
      async function choose(file){
        const {root}=await command("DOM.getDocument");
        const {nodeId}=await command("DOM.querySelector",{nodeId:root.nodeId,selector:"#fileInput"});
        assert.ok(nodeId,"real file input");
        await command("DOM.setFileInputFiles",{nodeId,files:[file]});
      }
      async function click(selector){
        const result=await command("Runtime.evaluate",{expression:"document.querySelector("+JSON.stringify(selector)+").click()",userGesture:true,returnByValue:true});
        if(result.exceptionDetails)throw Error("Click failed: "+result.exceptionDetails.text);
      }
      async function confirm(accept){
        let listener,timer;
        const opened=new Promise((resolve,reject)=>{
          listener=event=>{
            const message=JSON.parse(event.data);
            if(message.method==="Page.javascriptDialogOpening")resolve(message.params);
          };
          ws.addEventListener("message",listener);
          timer=setTimeout(()=>reject(Error("Expected actual confirmation dialog")),8000);
        });
        const action=click("#confirmExportButton").then(()=>null,error=>error);
        try{
          const dialog=await opened;
          assert.equal(dialog.type,"confirm");
          await command("Page.handleJavaScriptDialog",{accept});
          const error=await action;if(error)throw error;
        }finally{clearTimeout(timer);ws.removeEventListener("message",listener);}
      }
      await navigate();
      await choose(input);
      await ready("!document.querySelector('#workArea').hidden && document.querySelector('#facilityList').querySelectorAll('button').length===3 && document.querySelector('#fileInput').value===''","baseline import");
      await click("#facilityList button:first-child");
      const note="合成ブラウザ回帰：保存確認前に失わない";
      await evaluate("document.querySelector('#reviewNote').value="+JSON.stringify(note));
      await click("#facilityList button:nth-child(2)");
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),note);
      assert.equal(await evaluate("document.querySelector('#facilityName').textContent"),example.records[0].name);
      assert.equal(await evaluate("document.querySelector('#feedback').dataset.error"),"true");
      await click("#saveRecord");
      await click("#exportButton");
      await ready("!document.querySelector('#confirmExportButton').disabled","download started");
      // A real file in the configured download directory is required, not an
      // intercepted Blob, a mocked a.click(), or a claimed browser save.
      let downloaded;
      for(let i=0;i<100;i++){
        const names=await fs.readdir(downloads);
        const completed=names.filter(name=>name.endsWith(".json"));
        if(completed.length===1&&!names.some(name=>name.endsWith(".crdownload"))){downloaded=path.join(downloads,completed[0]);break;}
        await pause(100);
      }
      assert.ok(downloaded,"actual completed JSON download");
      const saved=JSON.parse(await fs.readFile(downloaded,"utf8"));
      assert.equal(saved.records[0].review.notes,note);
      assert.deepEqual(saved.safety,example.safety);
      await confirm(false);
      assert.equal(await evaluate("document.querySelector('#confirmExportButton').disabled"),false);
      await choose(input);
      await ready("document.querySelector('#feedback').dataset.error==='true' && document.querySelector('#fileInput').value===''","unconfirmed download prevents overwrite");
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),note);
      await confirm(true);
      assert.equal(await evaluate("document.querySelector('#confirmExportButton').disabled"),true);
      assert.match(await evaluate("document.querySelector('#feedback').textContent"),/本人による保存確認/);
      await evaluate("window.__teamReviewOldDocument=true");
      await navigate();
      assert.equal(await evaluate("window.__teamReviewOldDocument===undefined"),true);
      assert.equal(await evaluate("document.querySelector('#exportButton').disabled"),true);
      await choose(downloaded);
      await ready("!document.querySelector('#workArea').hidden && document.querySelector('#fileInput').value===''","actual downloaded file reimport");
      await click("#facilityList button:first-child");
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),note);
      assert.deepEqual(browser.exceptions,[]);
      assert.ok(browser.outbound.every(u=>u===url||u===origin+"/favicon.ico"||u.startsWith("blob:"+origin+"/")),JSON.stringify(browser.outbound));
      assert.ok(requests.every(p=>p==="/team-review.html"||p==="/favicon.ico"),JSON.stringify(requests));
      console.log("TEAM_REVIEW_DOWNLOAD_HTTP: real file input, Blob download bytes, cancel/confirm, fresh document and reimport PASS");
    }finally{
      try{if(browser)await helper.stopChrome(browser.child,browser.profile,browser.ws);}
      finally{
        try{if(server?.listening)await new Promise(resolve=>{server.close(resolve);server.closeAllConnections?.();});}
        finally{await fs.rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:200});}
      }
    }
  });


// Actual HTTP Chrome, synthetic nine-site review and separate PDF report.
// No real PDF retrieval or facility approval. Keep this existing private path.
test("PDF triage real HTTP Chrome imports separate files, filters, rejects tampering and exports only review",
  {timeout:120000},async t=>{
    const {default:fs}=await import("node:fs/promises");
    const {default:os}=await import("node:os");
    const {default:path}=await import("node:path");
    const {default:http}=await import("node:http");
    const {default:helper}=await import("./helpers/http-chrome.cjs");
    const bin=helper.browserBinary();
    if(!bin){
      if(process.env.CI||process.env.TEAM_REVIEW_REQUIRE_CHROME==="1")throw Error("Chrome required for PDF triage");
      t.skip("Chrome unavailable locally");return;
    }
    const {review,report}=makeTriageFixture();
    review.records[0].review={...review.records[0].review,status:"evidence_found",
      checks:{official_source:true,identity:true,address:true,position_evidence:true},
      reviewer:"合成班員",notes:"架空の確認記録を維持",evidence_url:"https://example.invalid/evidence",
      reviewed_at:"2026-10-22T02:30:00.000Z"};
    check(review);checkTriage(report,review);
    const temp=await fs.mkdtemp(path.join(os.tmpdir(),"pdf-triage-http-"));
    let browser,server;
    const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
    try{
      const input=path.join(temp,"review.json"),diff=path.join(temp,"triage.json"),bad=path.join(temp,"tampered.json");
      const downloads=path.join(temp,"downloads");
      const tampered=clone(report);tampered.safety.approved_for_map=true;
      await fs.mkdir(downloads);
      await Promise.all([[input,review],[diff,report],[bad,tampered]].map(([file,obj])=>fs.writeFile(file,JSON.stringify(obj),"utf8")));
      const requests=[];
      server=http.createServer((req,res)=>{
        requests.push(req.url);
        if(req.method==="GET"&&req.url==="/team-review.html"){
          res.writeHead(200,{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"});res.end(page);
        }else{res.writeHead(404);res.end();}
      });
      await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"127.0.0.1",resolve);});
      const origin="http://127.0.0.1:"+server.address().port,url=origin+"/team-review.html";
      browser=await helper.launchChrome(bin);
      const {command,evaluate}=browser;
      await command("Page.enable");await command("Runtime.enable");await command("Network.enable");await command("DOM.enable");
      await command("Page.setDownloadBehavior",{behavior:"allow",downloadPath:downloads});
      async function ready(expr,label){
        for(let i=0;i<100;i++){if(await evaluate(expr))return;await pause(100);}
        throw Error("Timed out: "+label);
      }
      async function choose(selector,file){
        const {root}=await command("DOM.getDocument");
        const {nodeId}=await command("DOM.querySelector",{nodeId:root.nodeId,selector});
        assert.ok(nodeId,selector);
        await command("DOM.setFileInputFiles",{nodeId,files:[file]});
      }
      const nav=await command("Page.navigate",{url});assert.ok(!nav.errorText);
      await helper.waitUntil(evaluate,"location.href==="+JSON.stringify(url)+" && document.readyState==='complete' && document.querySelector('#triageInput')?.disabled","initial PDF triage");
      await choose("#fileInput",input);
      await ready("!document.querySelector('#workArea').hidden && !document.querySelector('#triageInput').disabled && document.querySelector('#fileInput').value===''","review import");
      assert.equal(await evaluate("document.querySelector('#triageSummary').hidden"),true);
      await choose("#triageInput",diff);
      await ready("!document.querySelector('#triageSummary').hidden && document.querySelector('#triageInput').value==='' && document.querySelector('#feedback').dataset.error==='false'","valid PDF import");
      const summary=await evaluate("document.querySelector('#triageSummary').textContent");
      assert.match(summary,/再確認 3件/);assert.match(summary,/承認にはなりません/);
      await evaluate("{const e=document.querySelector('#triageFilter');e.value='review_required';e.dispatchEvent(new Event('change',{bubbles:true}))}");
      assert.deepEqual(await evaluate("[...document.querySelectorAll('#facilityList button strong')].map(x=>x.textContent)"),review.records.slice(0,3).map(r=>r.name));
      await evaluate("document.querySelector('#facilityList button').click()");
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),review.records[0].review.notes);
      assert.equal(await evaluate("document.querySelector('#reviewStatus').value"),"evidence_found");
      assert.match(await evaluate("document.querySelector('#triageCue').textContent"),/PDF更新：あり/);
      // Invalid replacement must not erase the current filter, report or review.
      await choose("#triageInput",bad);
      await ready("document.querySelector('#triageInput').value==='' && document.querySelector('#feedback').dataset.error==='true'","tampered PDF rejection");
      assert.equal(await evaluate("document.querySelector('#triageSummary').textContent"),summary);
      assert.equal(await evaluate("document.querySelector('#triageFilter').value"),"review_required");
      assert.equal(await evaluate("document.querySelectorAll('#facilityList button').length"),3);
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),review.records[0].review.notes);
      // Unapplied editor changes must survive attempted re-import.
      await evaluate("document.querySelector('#reviewNote').value='未反映の合成メモ'");
      await choose("#triageInput",diff);
      await ready("document.querySelector('#triageInput').value==='' && document.querySelector('#feedback').dataset.error==='true'","unapplied edit rejection");
      assert.equal(await evaluate("document.querySelector('#reviewNote').value"),"未反映の合成メモ");
      assert.equal(await evaluate("document.querySelector('#triageSummary').textContent"),summary);
      await evaluate("document.querySelector('#reviewNote').value="+JSON.stringify(review.records[0].review.notes));
      await evaluate("{const e=document.querySelector('#triageFilter');e.value='no_diff';e.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#needsActionOnly').checked=false;document.querySelector('#needsActionOnly').dispatchEvent(new Event('change',{bubbles:true}))}");
      assert.deepEqual(await evaluate("[...document.querySelectorAll('#facilityList button strong')].map(x=>x.textContent)"),review.records.slice(3).map(r=>r.name));
      const click=await command("Runtime.evaluate",{expression:"document.querySelector('#exportButton').click()",userGesture:true,returnByValue:true});
      assert.ok(!click.exceptionDetails,"export invocation");
      let saved;
      for(let i=0;i<100;i++){
        const names=await fs.readdir(downloads);
        const json=names.filter(n=>n.endsWith(".json"));
        if(json.length===1&&!names.some(n=>n.endsWith(".crdownload"))){saved=JSON.parse(await fs.readFile(path.join(downloads,json[0]),"utf8"));break;}
        await pause(100);
      }
      assert.ok(saved,"actual saved file");
      assert.deepEqual(saved,review,"PDF overlay must not change or join saved review");
      assert.deepEqual(browser.exceptions,[]);
      assert.ok(browser.outbound.every(u=>u===url||u===origin+"/favicon.ico"||u.startsWith("blob:"+origin+"/")),JSON.stringify(browser.outbound));
      assert.ok(requests.every(p=>p==="/team-review.html"||p==="/favicon.ico"),JSON.stringify(requests));
      console.log("TEAM_REVIEW_PDF_TRIAGE_HTTP: actual file imports, completed-review inclusion, filters, tamper/unapplied rejection, unchanged download PASS");
    }finally{
      try{if(browser)await helper.stopChrome(browser.child,browser.profile,browser.ws);}
      finally{
        try{if(server?.listening)await new Promise(resolve=>{server.close(resolve);server.closeAllConnections?.();});}
        finally{await fs.rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:200});}
      }
    }
  });
