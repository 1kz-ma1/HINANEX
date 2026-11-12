"""C-owned comparison: archived Edogawa historical sources vs a *new* raw archive.

This is an evidence-drift report, NOT a facility identity match, C human
approval, or flood eligibility judgment. The baseline may be a historical
user-provided browser save and is never deemed current just because rows agree.

Example:
  python validation/validation/compare_edogawa_official_revisions.py \
    --baseline-water-html /evidence/historical_water.html \
    --baseline-location-csv /evidence/20251211_hinanhokan.csv \
    --current-archive /evidence/official-20261013 \
    --report /evidence/c_revision_diff.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from archive_edogawa_official_sources import (
    SOURCES, SnapshotFailure, verify_snapshot,
)
from verify_edogawa_water_join import (
    LOCATION_HEADER, WATER_HEADER, AuditFailure, water_rows,
)

# The raw source is authoritative; these are *review cues*, not IDs or keys.
PRIORITY_NAMES = {
    "都立 葛西工高等学校",
    "私立 関東一高等学校",
    "旧下小岩小学校",
    "下小岩小学校",
}


class RevisionFailure(ValueError):
    pass


def digest(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


def location_rows(raw: bytes):
    try:
        decoded = raw.decode("cp932")
        reader = csv.DictReader(io.StringIO(decoded, newline=""))
        if reader.fieldnames != list(LOCATION_HEADER):
            raise RevisionFailure("Official location CSV header changed: review schema")
        rows = list(reader)
        if not rows or any(None in row for row in rows):
            raise RevisionFailure("Official location CSV is empty or has malformed rows")
        return rows
    except (UnicodeError, csv.Error) as exc:
        raise RevisionFailure("Official location CSV cannot be parsed as CP932") from exc


def _water_records(raw):
    try:
        records, table_count = water_rows(raw)
    except (UnicodeError, AuditFailure, ValueError) as exc:
        raise RevisionFailure("Official water HTML is malformed or source changed") from exc
    if not records or table_count < 1:
        raise RevisionFailure("No official water facility rows")
    return records


def _normalize_space(value):
    return re.sub(r"\s+", " ", value.strip())


def _compare_rows(before, after, columns):
    # Keep all fields, including floor restrictions, phone numbers and URLs.
    # Normalize only whitespace for semantic comparisons; exact raw-byte SHA
    # and raw-row comparisons are reported separately.
    def tuples(rows, whitespace=False):
        return Counter(tuple(
            _normalize_space(str(row[c])) if whitespace else str(row[c])
            for c in columns
        ) for row in rows)
    exact_old, exact_new = tuples(before), tuples(after)
    semantic_old, semantic_new = tuples(before, True), tuples(after, True)

    def sample(removed_or_added):
        return [
            {"record": dict(zip(columns, key)), "occurrences": count}
            for key, count in sorted(removed_or_added.items())
        ]
    return {
        "baseline_row_count": len(before),
        "current_row_count": len(after),
        "exact_source_fields_equal": exact_old == exact_new,
        "whitespace_normalized_rows_equal": semantic_old == semantic_new,
        "removed_rows": sample(semantic_old - semantic_new),
        "added_rows": sample(semantic_new - semantic_old),
        "normalization_rule": "Unicode whitespace runs only; no name/address/floor meaning inferred",
    }


def compare(baseline_water, baseline_csv, current_archive):
    current_archive = Path(current_archive)
    try:
        verify_snapshot(current_archive)
        manifest = json.loads((current_archive / "snapshot_manifest.json").read_text("utf-8"))
        latest_water = (current_archive / SOURCES["water_facilities"][0]).read_bytes()
        latest_csv = (current_archive / SOURCES["municipal_locations"][0]).read_bytes()
    except (SnapshotFailure, OSError, ValueError) as exc:
        raise RevisionFailure("Current 7-source archive failed independent integrity check") from exc

    baseline_water_rows = _water_records(baseline_water)
    current_water_rows = _water_records(latest_water)
    baseline_location_rows = location_rows(baseline_csv)
    current_location_rows = location_rows(latest_csv)

    # Official table/row indices are evidence trace positions, not
    # intrinsic facility properties. A municipality reordering the table
    # must not be reported as a substantive change to school attributes.
    water_fields = [
        "official_number_raw", "official_name_raw",
        "official_address_raw", "official_phone_raw",
        "official_usable_floor_raw",
    ]
    if set(baseline_water_rows[0]) != set(current_water_rows[0]):
        raise RevisionFailure("Official water table fields changed")

    water_diff = _compare_rows(
        baseline_water_rows, current_water_rows, water_fields
    )
    location_diff = _compare_rows(
        baseline_location_rows, current_location_rows, LOCATION_HEADER
    )
    water_changed = (digest(baseline_water) != digest(latest_water))
    csv_changed = (digest(baseline_csv) != digest(latest_csv))
    structured_changed = (
        not water_diff["whitespace_normalized_rows_equal"] or
        not location_diff["whitespace_normalized_rows_equal"]
    )
    snapshots = {item["source_key"]: item for item in manifest["source_items"]}

    # These pairs are not independently verified facility IDs. Detect source
    # row drift for human review without auto-linking the D facility.
    def priority(rows):
        return [
            dict(row) for row in rows
            if row["official_name_raw"] in PRIORITY_NAMES
        ]
    priority_diff = _compare_rows(
        priority(baseline_water_rows),
        priority(current_water_rows),
        water_fields,
    )
    return {
        "status": ("STRUCTURED_SOURCE_DRIFT_REVIEW_REQUIRED" if structured_changed
                   else "SOURCE_BYTES_DIFFER_STRUCTURE_SAME_REVIEW_REQUIRED"
                   if water_changed or csv_changed
                   else "BASELINE_AND_CURRENT_BYTES_EQUAL_STILL_REVIEW_REQUIRED"),
        "archive_captured_at_utc": manifest["captured_at_utc"],
        "baseline_origin": "OPERATOR_SUPPLIED_HISTORICAL_NOT_AUTHENTICATED",
        "baseline": {
            "water_sha256": digest(baseline_water),
            "location_sha256": digest(baseline_csv),
        },
        "current": {
            "water_sha256": snapshots["water_facilities"]["sha256"],
            "location_sha256": snapshots["municipal_locations"]["sha256"],
        },
        "water_bytes_changed": water_changed,
        "location_bytes_changed": csv_changed,
        "water_rows": water_diff,
        "location_rows": location_diff,
        "priority_school_rows": priority_diff,
        "row_order_is_not_an_identity_key": True,
        "source_url_is_not_a_facility_id": True,
        "current_websites_and_source_effective_dates_human_review_required": True,
        "source_drift_is_not_an_approval": True,
        "c_human_reviewer_signed_off": False,
        "approved_cross_source_pairs": 0,
        "new_flood_candidates_or_exclusions": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-water-html", required=True, type=Path)
    parser.add_argument("--baseline-location-csv", required=True, type=Path)
    parser.add_argument("--current-archive", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.exit(2, "Refusing to overwrite existing evidence report\n")
    try:
        result = compare(
            args.baseline_water_html.read_bytes(),
            args.baseline_location_csv.read_bytes(),
            args.current_archive,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, "Official revision comparison failed: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["status"],
        "water_rows": result["water_rows"]["current_row_count"],
        "location_rows": result["location_rows"]["current_row_count"],
        "c_human_reviewer_signed_off": False,
        "flood_classifications_added": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
