#!/usr/bin/env node
// B-only acceptance gate for a locally generated D RegionExport.
// Structural compatibility is NOT official row-level validation or publication approval.
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildF02ShelterReference } from "../src/f02-shelter-reference.js";

const defaultFile = fileURLToPath(new URL("../../pipeline/data/output/edogawa.json", import.meta.url));
const input = process.argv[2] ? resolve(process.argv[2]) : defaultFile;
const report = {
  feature: "F02 RegionExport consumer",
  region_code: "13123",
  source_file: input,
  input_provenance: "NOT_INDEPENDENTLY_VERIFIED",
  official_row_review: "NOT_RUN",
  publication_approval: "NOT_GRANTED",
};

async function main() {
  let raw;
  try {
    raw = await readFile(input, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      console.error(JSON.stringify({
        ...report, status: "NOT_RUN", reason: "RegionExport file not found; run D pipeline first",
      }, null, 2));
      process.exitCode = 2;
      return;
    }
    throw error;
  }

  try {
    const payload = JSON.parse(raw);
    const reference = buildF02ShelterReference(payload, "13123");
    if (reference.state !== "READY") throw new Error("shelter_location dataset is not available");
    if (reference.records.length === 0) throw new Error("shelter_location dataset is empty");
    if (reference.evidence.length === 0) throw new Error("dataset-level evidence is missing");
    if (reference.evidence.every(source => source.url === null)) {
      throw new Error("no HTTPS dataset-level source URL");
    }
    if (!Array.isArray(payload.assessments)) {
      throw new Error("RegionExport assessments are missing");
    }
    const assessments = payload.assessments.filter(
      x => x?.requirement_code === "shelter_location" && x?.region_code === "13123"
    );
    if (assessments.length !== 1 ||
        assessments[0].record_count !== reference.records.length) {
      throw new Error("shelter_location assessment record_count mismatch");
    }
    const meta = payload.meta;
    if (meta.dataset_count !== payload.datasets.length ||
        meta.assessment_count !== payload.assessments.length ||
        meta.evidence_count !== payload.datasets.reduce(
          (sum, ds) => sum + (Array.isArray(ds?.evidence) ? ds.evidence.length : 0), 0)) {
      throw new Error("RegionExport meta count mismatch");
    }

    console.log(JSON.stringify({
      ...report,
      status: "CONSUMER_COMPATIBLE",
      contract_schema_version: meta.schema_version,
      generated_at: meta.generated_at ?? null,
      dataset_records: reference.records.length,
      without_coordinates: reference.withoutCoordinates,
      evidence_entries: reference.evidence.length,
      evidence_with_https: reference.evidence.filter(x => x.url).length,
      recorded_licenses: [...new Set(reference.evidence.map(x => x.licenseRaw).filter(Boolean))],
      note: "File structure only: original-source bytes, row identity, latestness and publication remain unverified.",
    }, null, 2));
  } catch (error) {
    console.error(JSON.stringify({
      ...report, status: "CONSUMER_REJECTED",
      reason: error?.message ?? String(error),
    }, null, 2));
    process.exitCode = 1;
  }
}

await main();
