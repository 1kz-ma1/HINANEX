const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {};
const adapterPath = path.resolve(__dirname, "../gis/js/d_region_adapter.js");
vm.runInThisContext(fs.readFileSync(adapterPath, "utf8"), { filename: adapterPath });
const adapter = window.HINANEX_D_ADAPTER;

const cases = [
  ["edogawa", "13123", 2, 1, 1],
  ["niigata", "15100", 2, 1, 1],
  ["nagoya", "23100", 2, 0, 2]
];

for (const [key, code, total, mappable, missing] of cases) {
  const fixturePath = path.resolve(__dirname, "fixtures", `${key}.json`);
  const payload = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const result = adapter.extractShelterLocation(payload, code);
  assert.equal(result.schemaVersion, "0.9", `${key}: schema version`);
  assert.equal(result.region.code, code, `${key}: region code`);
  assert.equal(result.records.length, total, `${key}: record count`);
  assert.equal(result.mappableRecords.length, mappable, `${key}: mappable count`);
  assert.equal(result.missingCoordinateRecords.length, missing, `${key}: missing count`);
}

console.log("region_exports.integration.test.js: OK");
