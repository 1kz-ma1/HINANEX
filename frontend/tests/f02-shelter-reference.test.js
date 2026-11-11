import test from "node:test";
import assert from "node:assert/strict";
import { buildF02ShelterReference, searchF02Facilities, httpsSourceUrl } from "../src/f02-shelter-reference.js";

function regionExport() {
  return {
    meta: { schema_version: "0.9" },
    region: { code: "13123", name: "東京都 江戸川区" },
    datasets: [{
      region_code: "13123", region_name: "東京都 江戸川区",
      requirement_code: "shelter_location",
      records: [
        { id: "a", name: "架空スズラン会館", address: null, facility_type: null,
          supported_disasters: null, latitude: null, longitude: null },
        { id: "b", name: "架空青空学園", address: "架空町 1-1", facility_type: "元資料の種別",
          supported_disasters: ["○", "－"], latitude: 35.0, longitude: 139.0 }
      ],
      evidence: [{source_name: "テスト資料", publisher: null, license: "CC BY 2.1 JP", published_at: null,
        fetched_at: "2026-01-01T00:00:00Z", source_url: "https://example.invalid/test"}]
    }]
  };
}

test("F02 reads one D shelter_location dataset without hazard interpretation", () => {
  const model = buildF02ShelterReference(regionExport());
  assert.equal(model.state, "READY");
  assert.equal(model.records.length, 2);
  assert.equal(model.withoutCoordinates, 1);
  assert.equal(model.records[0].addressRaw, null);
  assert.deepEqual(model.records[1].disasterValues, ["○", "－"]);
  assert.equal(model.evidence[0].publishedAt, null);
  assert.equal(model.evidence[0].licenseRaw, "CC BY 2.1 JP");
  assert.equal(model.evidence[0].url, "https://example.invalid/test");
});

test("NFKC region-free name search preserves unknown-coordinate facilities", () => {
  const rows = buildF02ShelterReference(regionExport()).records;
  assert.equal(searchF02Facilities(rows, " ｽｽﾞﾗﾝ ").length, 1);
  assert.equal(searchF02Facilities(rows, "見つからない").length, 0);
  assert.equal(searchF02Facilities(rows, "").length, 2);
});

test("No dataset is different from an empty dataset", () => {
  const missing = regionExport();
  missing.datasets = [];
  assert.equal(buildF02ShelterReference(missing).state, "NO_DATASET");
  const empty = regionExport();
  empty.datasets[0].records = [];
  const model = buildF02ShelterReference(empty);
  assert.equal(model.state, "READY");
  assert.equal(model.records.length, 0);
});

test("Invalid region and unknown schema fail closed", () => {
  const wrongRegion = regionExport();
  wrongRegion.region.code = "15100";
  assert.throws(() => buildF02ShelterReference(wrongRegion), /region mismatch/);
  const newer = regionExport();
  newer.meta.schema_version = "1.0";
  assert.throws(() => buildF02ShelterReference(newer), /schema version/);
});

test("Dataset mismatch, missing records and duplicate datasets fail closed", () => {
  const mismatch = regionExport();
  mismatch.datasets[0].region_code = "15100";
  assert.throws(() => buildF02ShelterReference(mismatch), /dataset contract/);
  const duplicate = regionExport();
  duplicate.datasets.push(structuredClone(duplicate.datasets[0]));
  assert.throws(() => buildF02ShelterReference(duplicate), /Duplicate/);
});

test("Duplicate records, malformed values and half coordinate pairs fail closed", () => {
  const duplicate = regionExport();
  duplicate.datasets[0].records[1].id = "a";
  assert.throws(() => buildF02ShelterReference(duplicate), /duplicate/);
  const brokenPair = regionExport();
  brokenPair.datasets[0].records[0].latitude = 35;
  assert.throws(() => buildF02ShelterReference(brokenPair), /coordinates/);
  const outOfRange = regionExport();
  outOfRange.datasets[0].records[1].latitude = 100;
  assert.throws(() => buildF02ShelterReference(outOfRange), /coordinates/);
  const brokenField = regionExport();
  brokenField.datasets[0].records[0].address = {text: "maybe"};
  assert.throws(() => buildF02ShelterReference(brokenField), /address/);
  const bogusDisaster = regionExport();
  bogusDisaster.datasets[0].records[0].supported_disasters = "flood";
  assert.throws(() => buildF02ShelterReference(bogusDisaster), /supported_disasters/);
});

test("Invalid evidence and unsafe URLs are not treated as source links", () => {
  const doc = regionExport();
  doc.datasets[0].evidence[0].source_url = "javascript:alert(1)";
  assert.equal(buildF02ShelterReference(doc).evidence[0].url, null);
  assert.equal(httpsSourceUrl("http://example.test"), null);
  const bad = regionExport();
  bad.datasets[0].evidence[0].source_name = null;
  assert.throws(() => buildF02ShelterReference(bad), /evidence/);
});

test("Scenario is not used to reclassify facility data", () => {
  const doc = regionExport();
  doc.scenarios = [{ scenario_id: "flood_shelter_selection", facility_results:
    [{facility_id:"a",status:"CANDIDATE"}] }];
  const model = buildF02ShelterReference(doc);
  assert.equal(model.records[0].id, "a");
  assert.equal(Object.hasOwn(model.records[0], "status"), false);
});

test("F02 preserves absent license as unknown and rejects malformed metadata", () => {
  const missing = regionExport();
  delete missing.datasets[0].evidence[0].license;
  assert.equal(buildF02ShelterReference(missing).evidence[0].licenseRaw, null);
  const invalid = regionExport();
  invalid.datasets[0].evidence[0].license = { guessed: "CC" };
  assert.throws(() => buildF02ShelterReference(invalid), /evidence.license/);
});
