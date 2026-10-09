"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { auditDirectory, loadBrowserAdapter, main } = require("./inspect_local_region_exports");

function row(id, lat, lon) {
  return {
    id, name: "SYNTHETIC " + id, latitude: lat, longitude: lon,
    address: null, administrative_area: null, facility_type: "shelter",
    supported_disasters: null, accessibility: null, capacity: null,
    detail_url: null, notes: "SYNTHETIC ONLY"
  };
}
function fixture(region, coords, includeScenario = false) {
  const records = coords.map(([a,b],i)=>row("test-" + i, a, b));
  return {
    region: { code: region, name: "TEST REGION" },
    datasets: [{
      region_code: region, region_name: "TEST REGION",
      requirement_code: "shelter_location", records,
      evidence: [{ publisher:"TEST", source_name:"SYNTHETIC FIXTURE" }]
    }],
    scenarios: includeScenario ? [{
      scenario_id: "flood_shelter_selection", region_code:region,
      status:"UNKNOWN", requirement_assessment:{ discovery_status:"AVAILABLE" },
      facility_results: records.map(rec=>({
        facility_id:rec.id, status:"UNKNOWN", reason:"uninterpreted TEST",
        fact:{ facility_id:rec.id, official_status_raw:null, hazard_scope_raw:null,
          usable_floor_raw:null, join_status:"DIRECT_SAME_SOURCE",
          source_record_trace:"synthetic-row-1", source_url:"https://example.test/fixture" }
      }))
    }] : [],
    meta:{schema_version:"0.9", generated_at:"2026-10-09T00:00:00Z"}
  };
}

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "hinanex-e-d-audit-"));
try {
  const put=(name,value)=>fs.writeFileSync(path.join(temporary,name),JSON.stringify(value));
  const original=fixture("13123",[[35.7,139.9],[null,null]]);
  put("edogawa.json",original);
  put("niigata.json",fixture("15100",[[37.9,139.0]],true));
  const adapter=loadBrowserAdapter();
  let report=auditDirectory(temporary,adapter);
  assert.equal(report.all_local_contracts_valid,false);
  assert.equal(report.region_exports[0].status,"LOCAL_CONTRACT_OK");
  assert.equal(report.region_exports[0].records,2);
  assert.equal(report.region_exports[0].mapped,1);
  assert.equal(report.region_exports[0].missing_coordinates,1);
  assert.match(report.region_exports[0].raw_file_sha256,/^[0-9a-f]{64}$/);
  assert.ok(report.region_exports[0].limitations.includes("NO_FLOOD_SCENARIO_PRESENT; scenario not inferred"));
  assert.ok(report.region_exports[0].limitations.includes("UNMAPPED_COORDINATES_NOT_GUESSED"));
  assert.equal(report.region_exports[1].status,"LOCAL_CONTRACT_OK");
  assert.equal(report.region_exports[1].scenario_status,"UNKNOWN");
  assert.equal(report.region_exports[1].scenario_unknown,1);
  assert.ok(report.region_exports[1].limitations.includes("FLOOD_SCENARIO_UNKNOWN_PRESERVED"));
  assert.equal(report.region_exports[2].status,"MISSING_FILE");
  assert.equal(report.baseline_accepted,false);
  assert.equal(report.official_source_provenance_checked,false);
  assert.equal(report.live_http_and_browser_checked,false);

  put("nagoya.json",fixture("23100",[[null,null],[null,null]],true));
  report=auditDirectory(temporary,adapter);
  assert.equal(report.all_local_contracts_valid,true);
  assert.equal(report.region_exports[2].records,2);
  assert.equal(report.region_exports[2].mapped,0);
  assert.equal(report.region_exports[2].missing_coordinates,2);
  assert.equal(report.region_exports[2].scenario_unknown,2);
  const digest=crypto.createHash("sha256").update(fs.readFileSync(path.join(temporary,"nagoya.json"))).digest("hex");
  assert.equal(report.region_exports[2].raw_file_sha256,digest);
  assert.equal(main(["--output-dir",temporary,"--json"]),0);
  assert.equal(main(["--output-dir",temporary,"--invalid"]),2);

  const wrong=fixture("15100",[[null,null]],false);
  put("nagoya.json",wrong);
  report=auditDirectory(temporary,adapter);
  assert.equal(report.region_exports[2].status,"INVALID_CONTRACT");
  assert.ok(report.region_exports[2].limitations[0].includes("Region mismatch"));

  put("nagoya.json",fixture("23100",[[null,null],[null,null]]));
  const duplicate=fixture("13123",[[35.7,139.9],[35.7,139.9]]);
  duplicate.datasets[0].records[1].id=duplicate.datasets[0].records[0].id;
  put("edogawa.json",duplicate);
  report=auditDirectory(temporary,adapter);
  assert.equal(report.region_exports[0].status,"DUPLICATE_FACILITY_ID");
  fs.writeFileSync(path.join(temporary,"edogawa.json"),"{invalid json", "utf8");
  report=auditDirectory(temporary,adapter);
  assert.equal(report.region_exports[0].status,"INVALID_JSON");

  // Tools must be observational: never alter D's source files or infer missing
  // official records. The original fixture can be restored byte-for-byte.
  const bytes=JSON.stringify(original);
  put("edogawa.json",original);
  const before=fs.readFileSync(path.join(temporary,"edogawa.json"),"utf8");
  auditDirectory(temporary,adapter);
  assert.equal(fs.readFileSync(path.join(temporary,"edogawa.json"),"utf8"),before);
  assert.equal(before,bytes);
  console.log("inspect_local_region_exports.test.js: OK");
} finally {
  fs.rmSync(temporary,{recursive:true,force:true});
}
