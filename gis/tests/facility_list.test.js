const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const context = { window: {} };
vm.createContext(context);
const source = path.resolve(__dirname, "../gis/js/facility_list.js");
vm.runInContext(fs.readFileSync(source, "utf8"), context, { filename: source });
const { filterFacilityRecords, PAGE_SIZE } = context.window.HINANEX_FACILITY_LIST;

function record(id, name, address, area) {
  return { id, name, address, administrative_area: area, latitude: null, longitude: null };
}

{
  // A source file with 1,602 rows is not a 0-record map. All 1,602 remain
  // browseable in bounded pages without inventing any coordinates.
  const records = Array.from({ length: 1602 }, (_, i) =>
    record(`id-${i}`, `名古屋TEST施設${i}`, `名古屋市中区${i}番地`, "中区")
  );
  const summary = { records, floodScenario: null };
  const first = filterFacilityRecords(summary);
  assert.equal(PAGE_SIZE, 20);
  assert.equal(first.total, 1602);
  assert.equal(first.matched, 1602);
  assert.equal(first.pages, 81);
  assert.equal(first.records.length, 20);
  assert.equal(first.first, 1);
  assert.equal(first.last, 20);
  const last = filterFacilityRecords(summary, "", 80);
  assert.equal(last.first, 1601);
  assert.equal(last.last, 1602);
  assert.equal(last.records.length, 2);
  assert.equal(filterFacilityRecords(summary, "", 999).page, 80);
  assert.equal(filterFacilityRecords(summary, "", -99).page, 0);
}

{
  const records = [
    record("s1", "テスト保育園", "名古屋市中区丸の内", "中区"),
    record("s2", "仮設TEST施設", "名古屋市港区", "港区"),
    record("s3", "別の施設", null, null)
  ];
  const facts = new Map([
    ["s1", {
      officialStatusRaw: "洪水・内水",
      usableFloorRaw: "2階以上",
      sourceRecordTrace: "file=test.xls;sheet=0;excel_row=5"
    }]
  ]);
  const summary = {
    records,
    floodScenario: { byId: facts }
  };
  assert.equal(filterFacilityRecords(summary, "保育園").matched, 1);
  assert.equal(filterFacilityRecords(summary, "丸の内").records[0].id, "s1");
  assert.equal(filterFacilityRecords(summary, "港区").records[0].id, "s2");
  assert.equal(filterFacilityRecords(summary, "中区　２階以上").records[0].id, "s1");
  assert.equal(filterFacilityRecords(summary, "洪水・内水").matched, 1);
  assert.equal(filterFacilityRecords(summary, "excel_row=5").matched, 1);
  assert.equal(filterFacilityRecords(summary, "存在しない").matched, 0);
  assert.equal(filterFacilityRecords(summary, "存在しない").records.length, 0);
  assert.equal(filterFacilityRecords(summary, "存在しない").first, 0);
  assert.equal(filterFacilityRecords(summary, "存在しない").last, 0);
  // Source records are never altered by search normalization.
  assert.equal(records[0].name, "テスト保育園");
  assert.equal(facts.get("s1").usableFloorRaw, "2階以上");
}

console.log("facility_list.test.js: OK");

// Include the new E-only selector regressions in the existing required CI runner.
require("./facility_explore.test.js");
// Pre-event module remains UI-disconnected; synthetic storage regression.
require("./pre_event_preparation.test.js");
