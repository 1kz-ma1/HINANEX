#!/usr/bin/env node
"use strict";

/*
 * Read-only E / GIS acceptance inventory for locally generated D RegionExport
 * v0.9 files. Uses the SAME consumer adapter as the browser, not another
 * source normalizer. This does not perform A/C provenance or HTTP acceptance.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");

const REPO_ROOT = path.resolve(__dirname, "../..");
const DEFAULT_OUTPUT_DIR = path.join(REPO_ROOT, "pipeline/data/output");
const REGIONS = [
  { code: "13123", name: "東京都 江戸川区", file: "edogawa.json" },
  { code: "15100", name: "新潟県 新潟市", file: "niigata.json" },
  { code: "23100", name: "愛知県 名古屋市", file: "nagoya.json" }
];

function loadBrowserAdapter() {
  const context = { window: {} };
  vm.runInNewContext(
    fs.readFileSync(path.resolve(__dirname, "../gis/js/d_region_adapter.js"), "utf8"),
    context, { filename: "d_region_adapter.js" }
  );
  return context.window.HINANEX_D_ADAPTER;
}

function examineFile(region, dir, adapter) {
  const location = path.join(dir, region.file);
  const result = {
    region_code: region.code,
    region_label: region.name,
    filename: region.file,
    status: "MISSING_FILE",
    schema_version: null,
    records: null,
    mapped: null,
    missing_coordinates: null,
    evidence: null,
    scenario_status: null,
    scenario_unknown: null,
    raw_file_sha256: null,
    limitations: []
  };
  let bytes;
  try {
    bytes = fs.readFileSync(location);
  } catch (error) {
    if (error.code === "ENOENT") {
      result.limitations.push("LOCAL_FILE_NOT_PRESENT; official sources may still exist");
      return result;
    }
    result.status = "READ_FAILED";
    result.limitations.push("READ_ERROR: " + error.code);
    return result;
  }
  result.raw_file_sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
  let doc;
  try {
    doc = JSON.parse(bytes.toString("utf8").replace(/^\uFEFF/, ""));
  } catch (_) {
    result.status = "INVALID_JSON";
    result.limitations.push("JSON_PARSE_FAILED");
    return result;
  }
  let summary;
  try {
    summary = adapter.extractShelterLocation(doc, region.code);
  } catch (error) {
    result.status = "INVALID_CONTRACT";
    result.limitations.push(String(error.message).slice(0, 240));
    return result;
  }
  result.schema_version = summary.schemaVersion;
  if (!summary.dataset) {
    result.status = "MISSING_SHELTER_DATASET";
    result.limitations.push("shelter_location absent; no substitute dataset inferred");
    return result;
  }
  const ids = summary.records.map(record => record.id);
  if (new Set(ids).size !== ids.length) {
    result.status = "DUPLICATE_FACILITY_ID";
    result.limitations.push("duplicate shelter_location record IDs");
    return result;
  }
  result.status = "LOCAL_CONTRACT_OK";
  result.records = summary.records.length;
  result.mapped = summary.mappableRecords.length;
  result.missing_coordinates = summary.missingCoordinateRecords.length;
  result.evidence = summary.evidence.length;
  if (result.records === 0) result.limitations.push("EMPTY_DATASET_NOT_PROOF_OF_NO_SHELTERS");
  if (result.missing_coordinates > 0) {
    result.limitations.push("UNMAPPED_COORDINATES_NOT_GUESSED");
  }
  if (!summary.floodScenario) {
    result.limitations.push("NO_FLOOD_SCENARIO_PRESENT; scenario not inferred");
  } else {
    result.scenario_status = summary.floodScenario.status;
    result.scenario_unknown = summary.floodScenario.unknownCount;
    if (result.scenario_status === "UNKNOWN" || result.scenario_unknown > 0) {
      result.limitations.push("FLOOD_SCENARIO_UNKNOWN_PRESERVED");
    }
  }
  if (!result.evidence) result.limitations.push("NO_EVIDENCE_RECORDS_IN_EXPORT");
  return result;
}

function auditDirectory(outputDir, adapter = loadBrowserAdapter()) {
  const regions = REGIONS.map(region => examineFile(region, outputDir, adapter));
  const allLocalContractsValid = regions.every(region => region.status === "LOCAL_CONTRACT_OK");
  return {
    schema: "HINANEX_E_LOCAL_D_REGIONEXPORT_ACCEPTANCE_V1",
    source: "READ_ONLY_LOCAL_FILES",
    region_exports: regions,
    all_local_contracts_valid: allLocalContractsValid,
    official_source_provenance_checked: false,
    live_http_and_browser_checked: false,
    flood_raster_network_checked: false,
    gps_permission_checked: false,
    baseline_accepted: false,
    interpretation: [
      "LOCAL_CONTRACT_OK only means the existing E RegionExport adapter accepts saved local bytes; not C source or A provenance acceptance.",
      "UNKNOWN, null coordinates, absent scenario, or absent runtime files are never converted to unsafe/safe or zero available shelters.",
      "Browser HTTP fetching, GPS denial, official flood raster and disaster readiness still require separate real acceptance."
    ]
  };
}

function formatSummary(report) {
  const rows = [
    "D RegionExport local acceptance (read-only; no safety judgment)",
    "region   status                   records   mapped   missing_coords   flood_UNKNOWN"
  ];
  for (const r of report.region_exports) {
    rows.push([
      r.region_code.padEnd(8),
      r.status.padEnd(24),
      String(r.records ?? "—").padStart(7),
      String(r.mapped ?? "—").padStart(8),
      String(r.missing_coordinates ?? "—").padStart(16),
      String(r.scenario_unknown ?? "—").padStart(15)
    ].join(" "));
    if (r.limitations.length) rows.push("         limitations: " + r.limitations.join("; "));
  }
  rows.push("All local D contracts valid: " + report.all_local_contracts_valid);
  rows.push("GPS / external flood raster / HTTP browser / source provenance: NOT TESTED");
  rows.push("Overall Phase-1 baseline accepted: false");
  return rows.join("\n");
}

function main(args) {
  let directory = DEFAULT_OUTPUT_DIR;
  let json = false;
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === "--json") json = true;
    else if (args[i] === "--output-dir" && args[i + 1]) directory = path.resolve(args[++i]);
    else if (args[i] === "--help") {
      process.stdout.write("Usage: node gis/tests/inspect_local_region_exports.js [--output-dir PATH] [--json]\n");
      return 0;
    } else {
      process.stderr.write("Invalid argument: " + args[i] + "\n");
      return 2;
    }
  }
  const report = auditDirectory(directory);
  process.stdout.write((json ? JSON.stringify(report, null, 2) : formatSummary(report)) + "\n");
  return report.all_local_contracts_valid ? 0 : 1;
}

module.exports = { auditDirectory, examineFile, formatSummary, loadBrowserAdapter, main };
if (require.main === module) process.exitCode = main(process.argv.slice(2));
