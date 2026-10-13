/**
 * Cross-role deterministic Contract smoke (B only).
 * Usage: node scripts/check-c-evidence-case.js /path/to/C_public_case.json
 *
 * Only public C case JSON is accepted; this command neither fetches
 * private office replies nor reads D/GIS. It never prints source JSON.
 */
import { readFile, stat } from "node:fs/promises";
import { parseEvidenceCase } from "../src/evidence-case-view-model.js";

const path = process.argv[2];
if (!path || process.argv.length !== 3) {
  process.stderr.write("Usage: node scripts/check-c-evidence-case.js <C_public_json_path>\n");
  process.exitCode = 2;
} else {
  try {
    const info = await stat(path);
    if (!info.isFile() || info.size > 256 * 1024) {
      throw new Error("C public case file missing or too large");
    }
    const data = JSON.parse(await readFile(path, "utf8"));
    const result = parseEvidenceCase(data);
    if (result.currentOpening !== "UNKNOWN" || result.isOperational ||
        result.isHistoricalReenactment || result.stages.length !== 3 ||
        result.sources.length !== 4) {
      throw new Error("Unexpected live result in educational case");
    }
    process.stdout.write(
      "C→B educational contract PASS; sources=4; stages=3; opening=UNKNOWN; "
      + "no RegionExport or GIS eligibility.\n"
    );
  } catch (e) {
    process.stderr.write(
      "C→B educational contract REJECTED (no source data printed): "
      + (e.name === "EvidenceContractError" ? e.message : "invalid public case") + "\n"
    );
    process.exitCode = 1;
  }
}
