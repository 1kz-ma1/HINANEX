"""C-owned independent acceptance of generated D flood Scenario exports.

Run from repository root, after D's full workflow:
  python validation/validation/verify_flood_scenario_acceptance.py

This checker does not import D's evaluator, status mapping or schema models.
It independently inspects the RegionExport JSON and the official raw archive.
Passing it does NOT certify the municipality's raw marker semantics or safety.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
PIPE = ROOT / "pipeline"
EXPECTED_REGIONS = {
    "edogawa": ("13123", "FULL"),
    "niigata": ("15100", "FULL"),
    "nagoya": ("23100", "BLOCKED"),
}
NIIGATA_RAW = PIPE / "data/raw/niigata/niigata_evacuation_space.csv"
NAGOYA_RAW = PIPE / "data/raw/nagoya/nagoya_indoor_shelters_bundle.zip"
ALLOWED_STATUS = {"CANDIDATE", "EXCLUDED", "UNKNOWN"}
KNOWN_POSITIVE = {"1", "○", "〇", "true", "yes", "可", "有"}
KNOWN_NEGATIVE = {"0", "×", "false"}


class AcceptanceFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceFailure(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_official_niigata_rows(raw: bytes):
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            text = raw.decode(encoding)
            reader = csv.DictReader(io.StringIO(text, newline=""))
            rows = []
            for row in reader:
                # Physical line number at record end, not the pandas row index.
                rows.append((reader.line_num, row))
            return rows
        except UnicodeDecodeError as exc:
            last_error = exc
    raise AcceptanceFailure(f"Niigata CSV encoding unsupported: {last_error}")


def check_niigata(scenario: dict, locations: dict):
    rows = read_official_niigata_rows(NIIGATA_RAW.read_bytes())
    results = scenario["facility_results"]
    require(len(rows) == len(results), "Niigata raw CSV/result row count mismatch")
    raw_histogram = Counter()
    for result, (physical_line, row) in zip(results, rows):
        fact = result["fact"]
        require(fact["join_status"] == "DIRECT_SAME_SOURCE",
                "Niigata should be direct same-source join")
        require(fact["hazard_scope_raw"] == "災害種別_洪水",
                "Niigata flood raw column was relabeled")
        require("災害種別_洪水" in row, "Niigata official CSV has no flood column")
        raw = (row["災害種別_洪水"] or "").strip()
        recorded = fact.get("official_status_raw")
        require((recorded or "").strip() == raw,
                f"Niigata CSV raw marker mismatch near physical line {physical_line}: "
                f"{recorded!r} vs {raw!r}")
        require(fact["facility_name"] == (row.get("名称") or "").strip(),
                f"Niigata facility name mismatch near line {physical_line}")
        raw_histogram[raw if raw else "<BLANK>"] += 1
        source_trace = fact.get("source_record_trace") or ""
        # D advertises csv_row; verify the advertised row against physical
        # CSV line. Multiline CSV fields require a richer trace convention.
        require(source_trace == f"csv_row={physical_line}",
                f"Niigata physical raw-row trace mismatch: {source_trace!r} "
                f"vs line {physical_line}")
        require(fact["source_url"] == locations["evidence"][0]["source_url"],
                "Niigata Scenario source URL differs from location Evidence")
        status = result["status"]
        require(status in ALLOWED_STATUS, "Niigata Scenario status invalid")
        marker = raw.lower()
        if status == "CANDIDATE":
            require(marker in KNOWN_POSITIVE, "Candidate lacks documented positive marker")
            require(fact["latitude"] is not None and fact["longitude"] is not None,
                    "Candidate lacks official location coordinates")
        if status == "EXCLUDED":
            require(marker in KNOWN_NEGATIVE, "Excluded lacks documented negative marker")
        if status == "UNKNOWN":
            require(marker not in KNOWN_NEGATIVE or fact["join_status"] != "DIRECT_SAME_SOURCE",
                    "Known negative marker was unexpectedly UNKNOWN")
    print("Niigata original raw-value histogram:", dict(sorted(raw_histogram.items())))
    print("Niigata status breakdown:", dict(Counter(x["status"] for x in results)))
    print("NOTE: raw markers are audited; official marker meaning still requires A/C source verification.")


def _cell(value):
    import pandas as pd
    if pd.isna(value):
        return ""
    return str(value).strip()


def check_nagoya(scenario: dict, locations: dict):
    try:
        import pandas as pd
    except ImportError as exc:
        raise AcceptanceFailure("Nagoya raw audit needs pandas/openpyxl/xlrd from pipeline/requirements.txt") from exc

    results = scenario["facility_results"]
    with ZipFile(NAGOYA_RAW) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        require(len(manifest) == 16, "Nagoya D scope must be 16 indoor ward files")
        entries = {entry["filename"]: entry for entry in manifest}
        tables = {}
        for filename in entries:
            engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"
            table = pd.read_excel(io.BytesIO(archive.read(filename)), sheet_name=0,
                                  header=None, dtype=object, engine=engine)
            header_index = None
            for i in range(min(30, len(table))):
                row_text = "".join(_cell(x) for x in table.iloc[i])
                if "施設名称" in row_text and "所在地" in row_text:
                    header_index = i
                    break
            require(header_index is not None, f"{filename}: facility header missing")
            flood_column = None
            for col in range(table.shape[1]):
                label = "".join(_cell(table.iat[r, col]) for r in range(
                    header_index, min(header_index + 3, len(table))))
                label = re.sub(r"\s+", "", label)
                if any(x in label for x in ("洪水内水", "洪水・内水")):
                    flood_column = col
                    break
            require(flood_column is not None, f"{filename}: combined flood/inland column missing")
            tables[filename] = (table, flood_column)
        for item in results:
            fact = item["fact"]
            require(item["status"] == "UNKNOWN", "Nagoya combined column classified as flood-only")
            require(fact["hazard_scope_raw"] == "洪水・内水",
                    "Nagoya combined scope was split or relabeled")
            require(fact["join_status"] == "DIRECT_SAME_SOURCE",
                    "Nagoya original-file same-source join lost")
            trace = fact.get("source_record_trace") or ""
            match = re.fullmatch(r"file=([^;]+);sheet=0;excel_row=(\d+)", trace)
            require(match is not None, f"Nagoya raw-row trace invalid: {trace!r}")
            filename, rownumber = match.group(1), int(match.group(2))
            require(filename in tables, f"Nagoya archive missing {filename}")
            table, col = tables[filename]
            require(1 <= rownumber <= len(table), f"{filename}: row {rownumber} out of range")
            original = _cell(table.iat[rownumber - 1, col])
            require((fact.get("official_status_raw") or "").strip() == original,
                    f"{filename}:{rownumber} flood/inland raw marker mismatch")
            require(fact["source_url"] == entries[filename]["url"],
                    "Nagoya Scenario source URL differs from file manifest")
    print("Nagoya indoor workbooks independently traced:", len(entries))
    print("Nagoya status breakdown:", dict(Counter(x["status"] for x in results)))


def check_edogawa(scenario: dict):
    require(all(item["status"] == "UNKNOWN" for item in scenario["facility_results"]),
            "Edogawa unverified join produced candidate/excluded")
    require(all(item["fact"]["join_status"] == "UNVERIFIED" for item in scenario["facility_results"]),
            "Edogawa joined without a verified source key")
    require(all(item["fact"]["official_status_raw"] is None for item in scenario["facility_results"]),
            "Edogawa has unverified claimed per-facility official facts")
    print("Edogawa: unverified join and UNKNOWN boundary confirmed.")
    print("NOTE: facility-level water-disaster official HTML was NOT ingested; Source→fact audit incomplete.")


def check_export(name: str, export: dict):
    code, legacy_status = EXPECTED_REGIONS[name]
    require(export.get("region", {}).get("code") == code, f"{name} region code mismatch")
    require(export.get("meta", {}).get("schema_version") == "0.9", f"{name} schema changed")
    datasets = [d for d in export["datasets"] if d["requirement_code"] == "shelter_location"]
    require(len(datasets) == 1, f"{name} legacy location dataset missing")
    locations = datasets[0]
    capabilities = [c for c in export["capabilities"] if c["capability_code"] == "shelter_discovery"]
    require(len(capabilities) == 1, f"{name} legacy capability missing")
    require(capabilities[0]["status"] == legacy_status,
            f"{name} legacy Shelter Discovery status regressed")
    require(len(export.get("scenarios") or []) == 1, f"{name} expected one flood Scenario")
    scenario = export["scenarios"][0]
    require(scenario["scenario_id"] == "flood_shelter_selection",
            f"{name} Scenario ID mismatch")
    require(scenario["requirement_assessment"]["requirement_code"] == "shelter_hazard_applicability",
            f"{name} formal Scenario-local Requirement missing")
    require(scenario["region_code"] == code, f"{name} Scenario region code mismatch")
    loc_ids = [x["id"] for x in locations["records"]]
    results = scenario["facility_results"]
    result_ids = [x["facility_id"] for x in results]
    require(len(result_ids) == len(loc_ids), f"{name} Scenario/location count mismatch")
    require(len(set(result_ids)) == len(result_ids) and set(result_ids) == set(loc_ids),
            f"{name} Scenario facility ID set mismatch")
    require(scenario["requirement_assessment"]["record_count"] == len(loc_ids),
            f"{name} Scenario requirement count mismatch")
    by_id = {x["id"]: x for x in locations["records"]}
    for item in results:
        fact = item["fact"]
        require(item["facility_id"] == fact["facility_id"], f"{name} result/fact ID mismatch")
        source_loc = by_id[item["facility_id"]]
        require(fact.get("latitude") == source_loc.get("latitude") and
                fact.get("longitude") == source_loc.get("longitude"),
                f"{name} Scenario coordinates differ from location source")
        require(fact.get("source_url", "").startswith("https://"),
                f"{name} Scenario official Source URL missing")
    print(name, "records:", len(loc_ids), "scenario:", scenario["status"])
    return scenario, locations


def main():
    for name in EXPECTED_REGIONS:
        path = PIPE / "data/output" / f"{name}.json"
        require(path.is_file(), f"{path} missing; run D's full workflow first")
        export = read_json(path)
        scenario, locations = check_export(name, export)
        if name == "edogawa":
            check_edogawa(scenario)
        elif name == "niigata":
            check_niigata(scenario, locations)
        else:
            check_nagoya(scenario, locations)
    print("C raw trace acceptance: checks PASSED (official semantics remain separate review gate)")


if __name__ == "__main__":
    try:
        main()
    except (AcceptanceFailure, OSError, ValueError, KeyError) as exc:
        print(f"C ACCEPTANCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
