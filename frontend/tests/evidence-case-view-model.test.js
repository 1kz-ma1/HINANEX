import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  CONTRACT, EvidenceContractError, EXPORT_STATUS,
  parseEvidenceCase, PUBLISHED_SOURCES,
} from "../src/evidence-case-view-model.js";

const fixturePath = new URL("../mock/shimokamata-evidence-ui-preview.json", import.meta.url);
const load = async () => JSON.parse(await readFile(fixturePath, "utf-8"));
const reject = (data) => assert.throws(() => parseEvidenceCase(data), EvidenceContractError);

test("C-public fixture renders only three documentary states and UNKNOWN", async () => {
  const m = parseEvidenceCase(await load());
  assert.equal(m.status, EXPORT_STATUS);
  assert.deepEqual(m.stages.map((s) => s.key), [
    "DOCUMENTARY_FACT", "SOURCE_VERSION_RECONCILIATION", "CURRENT_OPERATIONS_UNKNOWN",
  ]);
  assert.equal(m.currentOpening, "UNKNOWN");
  assert.equal(m.isOperational, false);
  assert.equal(m.isHistoricalReenactment, false);
  assert.equal(m.reverifiedOriginalsInBrowser, false);
  assert.equal(m.sources.length, 4);
  assert.equal(m.stages[2].isCurrentUnknown, true);
});

test("C contract version and explicit NOT-shelter-use fields are required", async () => {
  const original = await load();
  for (const [field, value] of [
    ["consumer_contract", "C_REAL_TIME_EVACUATION"],
    ["status", "SAFE_SHELTER_RECOMMENDATION"],
    ["presentation_only", false],
    ["may_be_used_as_live_shelter_recommendation", true],
    ["current_site_safety_or_opening_claim", true],
    ["region_export_read_or_mutated", true],
    ["not_reenacted_historical_disaster_or_predictive_accuracy_result", false],
    ["no_private_reply_text_or_personal_data_included", false],
    ["new_flood_candidate_or_excluded", 1],
    ["human_C_site_pairs_approved", 1],
  ]) {
    const a = structuredClone(original);
    a[field] = value;
    reject(a);
  }
  const extra = structuredClone(original);
  extra.private_municipal_reply = "do not publish";
  reject(extra);
  assert.equal(CONTRACT, "C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1");
});

test("old site and new campus/address source version cannot be merged or silently corrected", async () => {
  const original = await load();
  for (const [field, val] of [
    ["site_address_raw", "瑞江4丁目19番10号"],
    ["separate_current_school_address_raw", "東瑞江3丁目11番1号"],
    ["new_school_plan_raw_address_2026", "瑞江4-19-10"],
    ["old_new_premises_human_link_approved", true],
  ]) {
    const a = structuredClone(original);
    a.target_case[field] = val;
    reject(a);
  }
});

test("official document URL, SHA, as-of and publisher category are pinned", async () => {
  const orig = await load();
  for (const key of Object.keys(PUBLISHED_SOURCES)) {
    const expected = PUBLISHED_SOURCES[key];
    for (const [field, bad] of [
      ["original_url", "javascript:alert(1)"],
      ["original_sha256", "f".repeat(64)],
      ["document_date_scope", "2026-10-13"],
      ["source_type", "current_live_site_opening"],
      ["originals_checked_in_prior_separate_github_actions", false],
      ["original_bytes_reverified_by_this_public_export", true],
      ["human_C_physical_site_approval", true],
      ["verified_detail", "Officially safe and open."],
    ]) {
      const a = structuredClone(orig);
      a.source_documents[key][field] = bad;
      reject(a);
    }
    assert.ok(expected.url.startsWith("https://"));
    assert.match(expected.sha, /^[0-9a-f]{64}$/);
  }
  const added = structuredClone(orig);
  added.source_documents.unsanctioned_source = { original_url: "https://evil.example" };
  reject(added);
});

test("all three stage labels, order, messages and source sets fail closed on edit", async () => {
  const orig = await load();
  for (let i = 0; i < 3; i++) {
    for (const [field, bad] of [
      ["key", "SAFE_CURRENT_SITE"],
      ["label", "避難可能です"],
      ["display_state", "OPEN"],
      ["message", "解体済み、安全ではありません"],
      ["source_keys", ["unapproved"]],
    ]) {
      const a = structuredClone(orig);
      a.demo_states[i][field] = bad;
      reject(a);
    }
  }
  const fake = structuredClone(orig);
  fake.demo_states[2].current_operational_status = "OPEN";
  reject(fake);
  const extra = structuredClone(orig);
  extra.demo_states[1].live_hazard_score = 100;
  reject(extra);
});

test("public view model excludes private reply artifacts even with a forged extra field", async () => {
  const a = await load();
  a.source_documents["2026_demolition_vote_html"].private_original_reply_file = "secret.eml";
  reject(a);
  const safe = parseEvidenceCase(await load());
  const text = JSON.stringify(safe);
  assert.doesNotMatch(text, /original_municipal_reply|gmail|telephone_memo|phone|personal/);
  assert.equal(safe.addresses.old, "東瑞江3丁目11番1号");
});

test("page is isolated from RegionExport and GIS navigation and has source-only upload", async () => {
  const html = await readFile(new URL("../evidence-case.html", import.meta.url), "utf8");
  const source = await readFile(new URL("../src/evidence-case-page.js", import.meta.url), "utf8");
  const index = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /発表・教育用の事例です/);
  assert.match(html, /id="caseFile"/);
  assert.match(html, /id="caseStages"/);
  assert.match(html, /id="caseSources"/);
  assert.match(html, /id="caseError"/);
  assert.match(index, /href="\.\/evidence-case\.html"/);
  assert.doesNotMatch(html, /<iframe|mapbox|leaflet/i);
  assert.match(source, /parseEvidenceCase\(data\)/);
  assert.match(source, /content\.hidden = true/);
  assert.match(source, /target = "_blank"/);
  assert.match(source, /rel = "noopener noreferrer"/);
  assert.doesNotMatch(source, /innerHTML|eval\(|fetch\(["\x27]\/pipeline|\/gis\/gis\/\?/);
});

test("broken source and C-less empty cases must never be displayed", () => {
  for (const payload of [null, undefined, [], {}, "", 42]) {
    reject(payload);
  }
});
