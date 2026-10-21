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
