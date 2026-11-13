"""C-only audit of one Edogawa municipal shelter-location source to D output.

Independent of the D adapter and its runtime models; Python standard library only.
Verifies a local source CSV byte match, source-row -> normalized -> RegionExport
mapping, not source authenticity, physical location, shelter designation, current
opening status, hazard suitability, reuse approval or publication authorization.

Run from any directory with explicit absolute input paths. Raw/private data and
the optional report MUST remain outside the Git working tree.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys

REGION_CODE = "13123"
REQUIREMENT = "shelter_location"
SCHEMA = "0.9"
REQUIRED_COLUMNS = ("名称", "URL", "災害種別記号", "コメント", "緯度", "経度")
OPTIONAL_COLUMNS = {"住所", "所在地"}
SOURCE_PAGE = "https://www.city.edogawa.tokyo.jp/e004/kuseijoho/opendata/map_data.html"
REPO_ROOT = Path(__file__).resolve().parents[2]


class SourceExportAuditFailure(ValueError):
    pass


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise SourceExportAuditFailure(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    ensure(isinstance(value, dict), f"{path.name}: expected a JSON object")
    return value


def source_rows(raw: bytes) -> list[dict[str, str]]:
    try:
        text = raw.decode("cp932")
    except UnicodeError as exc:
        raise SourceExportAuditFailure("Source CSV is not valid CP932") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    columns = reader.fieldnames or []
    ensure(all(column in columns for column in REQUIRED_COLUMNS),
           f"Source CSV missing required headers: {columns!r}")
    ensure(len(columns) == len(set(columns)), "Duplicate source CSV headers")
    ensure(set(columns).issubset(set(REQUIRED_COLUMNS) | OPTIONAL_COLUMNS),
           f"Unexpected source CSV header: {columns!r}")
    rows = list(reader)
    ensure(bool(rows), "Empty source CSV")
    for i, row in enumerate(rows, start=2):
        ensure(None not in row and all(value is not None for value in row.values()),
               f"Source CSV row {i}: missing/extra cells")
    return rows


def numeric(value: str, label: str, bound: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceExportAuditFailure(f"{label}: invalid number") from exc
    ensure(math.isfinite(parsed) and -bound <= parsed <= bound,
           f"{label}: nonfinite or out-of-range")
    return parsed


def optional_source_value(value: str | None) -> str | None:
    # The D adapter treats absent/blank values as null. A non-empty source value
    # is retained verbatim except for surrounding whitespace.
    return value.strip() or None if value is not None else None


def expected_address(row: dict[str, str]) -> str | None:
    candidates = {
        entry for column in ("住所", "所在地")
        if column in row and (entry := optional_source_value(row[column])) is not None
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def check_record(record: dict, row: dict, line: int, label: str) -> str:
    ensure(isinstance(record, dict), f"{label} row {line}: record not an object")
    name = row["名称"].strip()
    ensure(bool(name), f"Source CSV row {line}: missing name")
    lat = numeric(row["緯度"], f"Source CSV row {line} latitude", 90)
    lon = numeric(row["経度"], f"Source CSV row {line} longitude", 180)
    material = f"{REGION_CODE}|{name}|{lat:.7f}|{lon:.7f}"
    record_id = "edogawa-" + digest(material.encode("utf-8"))[:16]
    for key, value in {
        "id": record_id,
        "name": name,
        "address": expected_address(row),
        "facility_type": (
            "supplementary_shelter" if "（補完施設）" in name else "shelter"
        ),
        "detail_url": optional_source_value(row["URL"]),
        "notes": optional_source_value(row["コメント"]),
        "supported_disasters": None,
        "accessibility": None,
        "capacity": None,
    }.items():
        ensure(key in record and record[key] == value,
               f"{label} row {line}: {key} differs from CSV or conservative mapping")
    for key, expected in (("latitude", lat), ("longitude", lon)):
        got = record.get(key)
        ensure(isinstance(got, (int, float)) and not isinstance(got, bool) and
               math.isfinite(got) and abs(got - expected) <= 1e-9,
               f"{label} row {line}: {key} differs from original CSV")
    return record_id


def check_dataset(dataset: dict, rows: list[dict], label: str) -> list[dict]:
    ensure(isinstance(dataset, dict) and
           dataset.get("region_code") == REGION_CODE and
           dataset.get("requirement_code") == REQUIREMENT,
           f"{label}: unexpected region/requirement")
    records = dataset.get("records")
    ensure(isinstance(records, list) and len(records) == len(rows),
           f"{label}: record count differs from source CSV")
    ids = [check_record(rec, row, i, label)
           for i, (row, rec) in enumerate(zip(rows, records), start=2)]
    ensure(len(set(ids)) == len(ids), f"{label}: duplicate IDs in source mapping")
    return records


def audit(source_raw: bytes, d_raw: bytes, normalized: dict, exported: dict,
          expected_sha256: str | None = None) -> dict:
    source_hash = digest(source_raw)
    ensure(source_raw == d_raw, "C independently obtained CSV and D raw CSV differ")
    if expected_sha256 is not None:
        ensure(len(expected_sha256) == 64 and expected_sha256 == source_hash,
               "CSV SHA-256 does not match operator-provided reference")
    rows = source_rows(source_raw)
    norm_records = check_dataset(normalized, rows, "NormalizedDataset")

    ensure(exported.get("region", {}).get("code") == REGION_CODE,
           "RegionExport region mismatch")
    ensure(exported.get("meta", {}).get("schema_version") == SCHEMA,
           "RegionExport schema mismatch")
    datasets = exported.get("datasets")
    ensure(isinstance(datasets, list), "RegionExport datasets not an array")
    matching = [d for d in datasets if isinstance(d, dict) and
                d.get("requirement_code") == REQUIREMENT]
    ensure(len(matching) == 1, "Expected exactly one shelter_location Dataset")
    ds = matching[0]
    export_records = check_dataset(ds, rows, "RegionExport")
    ensure(norm_records == export_records,
           "NormalizedDataset and RegionExport have different record payloads")

    assessments = exported.get("assessments")
    ensure(isinstance(assessments, list), "RegionExport assessments not an array")
    relevant = [a for a in assessments if isinstance(a, dict) and
                a.get("region_code") == REGION_CODE and
                a.get("requirement_code") == REQUIREMENT]
    ensure(len(relevant) == 1 and relevant[0].get("record_count") == len(rows),
           "DatasetAssessment record count mismatch")

    evidence = ds.get("evidence")
    ensure(isinstance(evidence, list) and len(evidence) >= 1,
           "Dataset-level Evidence missing")
    ensure(any(e.get("source_url") == SOURCE_PAGE
               for e in evidence if isinstance(e, dict)),
           "Dataset-level evidence missing expected municipal source page")
    ensure(all(e.get("published_at") is None
               for e in evidence if isinstance(e, dict)),
           "Source update date must not be silently treated as initial published_at")
    ensure(len(evidence) == sum(len(d.get("evidence", []))
                               for d in datasets if isinstance(d, dict))
           if exported.get("meta", {}).get("dataset_count") == 1 else True,
           "Unexpected evidence count for single-dataset export")
    return {
        "status": "C_SOURCE_TO_EXPORT_CONSISTENT",
        "region_code": REGION_CODE,
        "contract_version": SCHEMA,
        "source_sha256": source_hash,
        "d_raw_sha256": digest(d_raw),
        "source_rows": len(rows),
        "normalized_rows_checked": len(norm_records),
        "export_rows_checked": len(export_records),
        "row_mismatches": 0,
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "physical_site_identity": "NOT_APPROVED",
        "flood_suitability": "NOT_EVALUATED",
        "publication_approval": "NOT_GRANTED",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-csv", type=Path, required=True)
    parser.add_argument("--d-raw-csv", type=Path, required=True)
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--region-export", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--report", type=Path,
                        help="Write one new report outside Git; never overwrite")
    args = parser.parse_args()

    try:
        paths = [args.official_csv, args.d_raw_csv, args.normalized, args.region_export]
        if args.report is not None:
            report_file = args.report.resolve()
            ensure(not report_file.is_relative_to(REPO_ROOT),
                   "Report destination must be outside the Git checkout")
            ensure(not report_file.exists(), "Refusing to overwrite existing C report")
        for p in paths:
            ensure(p.is_file(), f"Required input missing: {p}")
        result = audit(
            args.official_csv.read_bytes(), args.d_raw_csv.read_bytes(),
            load_json(args.normalized), load_json(args.region_export),
            expected_sha256=args.expected_sha256,
        )
        if args.report is not None:
            with args.report.open("x", encoding="utf-8") as output:
                json.dump(result, output, indent=2, ensure_ascii=False)
                output.write("\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError) as exc:
        print(json.dumps({
            "status": "C_SOURCE_TO_EXPORT_HOLD",
            "reason": str(exc),
            "publication_approval": "NOT_GRANTED",
        }, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
