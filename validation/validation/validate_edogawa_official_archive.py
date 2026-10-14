"""C fail-closed checks for 200-OK wrong-content official Edogawa archives.

Run after the seven-source HTTPS archiver. Unlike its byte/hash verifier,
this verifies that responses plausibly contain the *intended original source*.
It is NOT publisher attestation, a reviewed physical facility association, or
flood-only suitability approval. Never commit the resulting raw archive.

  python validation/validation/validate_edogawa_official_archive.py \
    --archive-dir /outside-git/official-YYYYMMDD \
    --report /outside-git/official_content_preflight.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import re
from collections import Counter

from archive_edogawa_official_sources import (
    SOURCES, SnapshotFailure, verify_snapshot,
)
from verify_edogawa_water_join import (
    AuditFailure, LOCATION_HEADER, PRIORITY_SCHOOL_REFERENCES, water_rows,
)

# Source meaning and site identity MUST NOT be inferred from presence of a marker.
HTML_MARKERS = {
    "municipal_school_list": ("葛西工科", "関東第一"),
    "municipal_primary_school_list": ("下小岩",),
    "municipal_2025_school_relocation": ("下小岩",),
    "tokyo_kasaikoka_school_access": ("葛西工科",),
    "kanto_ichiko_school_overview": ("関東第一",),
}
HTML_ROOT_PATTERN = re.compile(rb"<html(?:\s|>)", flags=re.I)
HTML_BODY_PATTERN = re.compile(rb"<body(?:\s|>)", flags=re.I)
CSV_MEDIA_TYPES = {
    "text/csv", "application/csv", "text/plain",
    "application/octet-stream", "application/vnd.ms-excel",
    "binary/octet-stream",
}


class ContentPreflightFailure(ValueError):
    pass


def _source_bytes(folder, key):
    return (folder / SOURCES[key][0]).read_bytes()


def _html_page(raw, key):
    if not HTML_ROOT_PATTERN.search(raw) or not HTML_BODY_PATTERN.search(raw):
        raise ContentPreflightFailure(
            f"{key}: HTTP 200 response is not a recognizable HTML page"
        )
    # Decode conservatively: search keywords without treating a success
    # response as publication/date/publisher proof. Official HTML is UTF-8.
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ContentPreflightFailure(f"{key}: unexpected HTML encoding") from exc
    for marker in HTML_MARKERS[key]:
        if marker not in decoded:
            raise ContentPreflightFailure(
                f"{key}: expected institution/context marker absent: {marker}"
            )


def _csv_rows(raw):
    try:
        decoded = raw.decode("cp932")
    except UnicodeError as exc:
        raise ContentPreflightFailure("municipal_locations: invalid CP932 source") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    if reader.fieldnames != list(LOCATION_HEADER):
        raise ContentPreflightFailure(
            "municipal_locations: original source header differs or HTML masquerades as CSV"
        )
    rows = list(reader)
    if not rows:
        raise ContentPreflightFailure("municipal_locations: empty original CSV")
    for line, row in enumerate(rows, start=2):
        if (None in row or any(k not in row or row[k] is None for k in LOCATION_HEADER)
                or not row["名称"].strip()):
            raise ContentPreflightFailure(
                f"municipal_locations: malformed original CSV row {line}"
            )
        try:
            latitude = float(row["緯度"])
            longitude = float(row["経度"])
        except ValueError as exc:
            raise ContentPreflightFailure(
                f"municipal_locations: invalid numeric source coordinate at row {line}"
            ) from exc
        if (not math.isfinite(latitude) or not math.isfinite(longitude)
                or not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
            raise ContentPreflightFailure(
                f"municipal_locations: non-finite/out-of-range coordinate at row {line}"
            )
    return rows


def validate(archive_dir):
    archive_dir = Path(archive_dir)
    try:
        byte_check = verify_snapshot(archive_dir)
        manifest = json.loads(
            (archive_dir / "snapshot_manifest.json").read_text(encoding="utf-8")
        )
    except (SnapshotFailure, OSError, ValueError) as exc:
        raise ContentPreflightFailure(
            "Official raw archive failed its independent byte integrity check"
        ) from exc

    sources = {x["source_key"]: x for x in manifest["source_items"]}
    csv_type = (sources["municipal_locations"].get("http_content_type") or "").split(";")[0].strip().lower()
    if csv_type and csv_type not in CSV_MEDIA_TYPES:
        raise ContentPreflightFailure(
            "municipal_locations: HTTP Content-Type is not a CSV-compatible media type"
        )

    water_raw = _source_bytes(archive_dir, "water_facilities")
    if not HTML_ROOT_PATTERN.search(water_raw) or not HTML_BODY_PATTERN.search(water_raw):
        raise ContentPreflightFailure("water_facilities: HTTP 200 response is not HTML")
    try:
        official_water, water_table_count = water_rows(water_raw)
    except (UnicodeError, AuditFailure, ValueError) as exc:
        raise ContentPreflightFailure(
            "water_facilities: missing expected official source URL or table/header"
        ) from exc

    rows = _csv_rows(_source_bytes(archive_dir, "municipal_locations"))
    for key in HTML_MARKERS:
        _html_page(_source_bytes(archive_dir, key), key)

    priority = []
    for institution in PRIORITY_SCHOOL_REFERENCES:
        found = [r for r in official_water
                 if r["official_number_raw"] == institution["official_number"]]
        if len(found) != 1:
            raise ContentPreflightFailure(
                "water_facilities: priority source row missing/duplicated; manual revision review"
            )
        row = found[0]
        priority.append({
            "water_number": row["official_number_raw"],
            "name_raw": row["official_name_raw"],
            "address_raw": row["official_address_raw"],
            "floor_raw": row["official_usable_floor_raw"],
            "matches_historical_reference": (
                row["official_name_raw"] == institution["water_name"]
                and row["official_address_raw"] == institution["water_address"]
                and row["official_usable_floor_raw"] == institution["water_floor_raw"]
            ),
            "cross_source_identity_approved": False,
            "flood_only_eligibility": "UNKNOWN",
        })
    old = [x for x in official_water if x["official_name_raw"] == "旧下小岩小学校"]
    current = [x for x in official_water if x["official_name_raw"] == "下小岩小学校"]
    if len(old) != 1 or len(current) != 1:
        raise ContentPreflightFailure(
            "water_facilities: distinct old/current Shimo-Koiwa source rows absent"
        )
    if old[0]["official_address_raw"] == current[0]["official_address_raw"]:
        raise ContentPreflightFailure(
            "water_facilities: former/current Shimo-Koiwa sites unexpectedly collapse"
        )

    # No number of records, name string, or same URL proves current flood suitability.
    return {
        "status": "ORIGINAL_CONTENT_STRUCTURE_CHECKED_HUMAN_REVIEW_REQUIRED",
        "captured_at_utc": manifest["captured_at_utc"],
        "bytes_checked": byte_check["source_bytes_verified"],
        "source_count": byte_check["sources_verified"],
        "official_water_tables": water_table_count,
        "official_water_rows": len(official_water),
        "location_csv_rows": len(rows),
        "raw_usable_floor_histogram": dict(sorted(Counter(
            x["official_usable_floor_raw"] for x in official_water
        ).items())),
        "priority_institution_rows": priority,
        "former_current_school_addresses_distinct": True,
        "content_check_is_not_source_authenticity_or_version_approval": True,
        "independent_human_c_review_signed_off": False,
        "approved_cross_source_pairs": 0,
        "flood_classifications_added": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.exit(2, "Refusing to overwrite existing C content preflight report\n")
    try:
        result = validate(args.archive_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, "C source content preflight failed; no approval: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["status"],
        "water_rows": result["official_water_rows"],
        "csv_rows": result["location_csv_rows"],
        "c_pairs_approved": 0,
        "flood_classifications_added": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
