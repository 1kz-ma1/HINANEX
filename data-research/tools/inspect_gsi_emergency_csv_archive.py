"""A-only offline inspector for archived official GSI emergency-site CSV data.

The national and municipality/prefecture layouts differ. Read exactly as
documented, preserve common ID as source text; never infer an ID or join it
to a separate GSI GeoJSON point by name/address/distance.
NO NETWORK, NO PUBLIC DISASTER CLAIMS, NO C HUMAN APPROVAL.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

DOC_URL = "https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
MAX_ARCHIVE_BYTES = 32_000_000
BASE_COLS = 16  # municipality and prefecture emergency-place CSV
ALLOWED_SCOPES = {"municipality": 16, "prefecture": 16, "national": 17}
ALLOWED_ENCODINGS = {"utf-8-sig", "cp932"}


def _decimal_coordinate(text: str, lower: int, upper: int) -> str | None:
    if not text:
        return None
    try:
        value = Decimal(text.strip())
    except InvalidOperation as exc:
        raise ValueError("INVALID_GSI_CSV_COORDINATE") from exc
    if not value.is_finite() or not lower <= value <= upper:
        raise ValueError("INVALID_GSI_CSV_COORDINATE")
    return text  # preserve exact official value, including precision


def inspect_emergency_place_csv(
    original: bytes, scope: str, *, encoding: str = "utf-8-sig"
) -> dict:
    if scope not in ALLOWED_SCOPES or encoding not in ALLOWED_ENCODINGS:
        raise ValueError("UNSUPPORTED_GSI_CSV_LAYOUT_OR_ENCODING")
    if type(original) is not bytes or not 0 < len(original) <= MAX_ARCHIVE_BYTES:
        raise ValueError("MISSING_OR_OVERSIZED_GSI_CSV_ORIGINAL")
    try:
        decoded = original.decode(encoding)
    except UnicodeError as exc:
        raise ValueError("GSI_CSV_ENCODING_INVALID") from exc
    try:
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        lines = list(reader)
    except csv.Error as exc:
        raise ValueError("GSI_CSV_SYNTAX_INVALID") from exc
    if not lines:
        raise ValueError("GSI_CSV_ROWS_MISSING")
    ncols = ALLOWED_SCOPES[scope]
    if (len(lines[0]) == ncols and lines[0][0].strip().upper() == "NO"
            and "共通ID" in lines[0][1]):
        lines = lines[1:]
    if not lines or len(lines) > 200_000:
        raise ValueError("GSI_CSV_DATA_ROW_COUNT_INVALID")

    records = []
    seen_no = set()
    for position, row in enumerate(lines):
        if len(row) != ncols:
            raise ValueError("GSI_CSV_COLUMNS_NOT_EXPECTED")
        no = row[0].strip()
        if not no.isascii() or not no.isdigit() or int(no) < 1:
            raise ValueError("GSI_CSV_NO_INVALID")
        if no in seen_no:
            raise ValueError("GSI_CSV_DUPLICATE_ROW_NO")
        seen_no.add(no)
        offset = 1 if scope == "national" else 0
        cid = row[1]  # may be absent; do NOT synthesize a surrogate common ID
        if len(cid) > 128 or any(c in cid for c in ("\r","\n","\x00")):
            raise ValueError("GSI_CSV_COMMON_ID_INVALID")
        name, address = row[2 + offset], row[3 + offset]
        if not name.strip() or len(name)>1000 or len(address)>2000:
            raise ValueError("GSI_CSV_NAME_OR_ADDRESS_INVALID")
        if scope == "national":
            jurisdiction = row[2]
            if not jurisdiction.strip():
                raise ValueError("GSI_CSV_MUNICIPALITY_NAME_MISSING")
        else:
            jurisdiction = None
        hazard_markers = row[4+offset:12+offset]
        if len(hazard_markers)!=8 or any(h not in ("", "1") for h in hazard_markers):
            raise ValueError("GSI_CSV_HAZARD_MARKER_INVALID")
        # The value '1' in the second hazard column means GSI designation
        # against landslide-type hazards, NOT current safe/open status.
        latitude, longitude = row[13+offset],row[14+offset]
        lat = _decimal_coordinate(latitude,-90,90)
        lon = _decimal_coordinate(longitude,-180,180)
        if (lat is None) != (lon is None):
            raise ValueError("GSI_CSV_PARTIAL_COORDINATE_PAIR")
        if row[12+offset] not in ("", "1"):
            raise ValueError("GSI_CSV_SHELTER_ADDRESS_MATCH_MARKER_INVALID")
        records.append({
            "raw_record_position": position,
            "source_no_raw": row[0],
            "common_id_raw": cid if cid else None,
            "municipality_name_raw": jurisdiction,
            "name_raw": name,
            "address_raw": address,
            "landslide_designation_marker_raw": hazard_markers[1],
            "latitude_raw": lat, "longitude_raw": lon,
            "source_csv_scope": scope,
            "source_csv_layout_column_count": ncols,
            "geojson_feature_identity_verified": False,
            "location_endpoint_verified": False,
        })
    id_counts = {}
    for row in records:
        cid=row["common_id_raw"]
        if cid is not None:
            id_counts[cid]=id_counts.get(cid,0)+1
    return {
        "status":"GSI_CSV_ARCHIVE_INSPECTED_UNREVIEWED",
        "source_schema_documentation":DOC_URL,
        "source_archive_sha256":sha256(original).hexdigest(),
        "source_bytes":len(original),
        "scope":scope,"encoding_selected":encoding,
        "archive_rows_count":len(records),
        "landslide_designated_rows_count":sum(
            r["landslide_designation_marker_raw"]=="1" for r in records
        ),
        "common_id_present_count":sum(r["common_id_raw"] is not None for r in records),
        "duplicate_common_id_values_unresolved":sorted(
            cid for cid,count in id_counts.items() if count>1
        ),
        "official_download_origin_independently_authenticated":False,
        "municipality_publication_date_verified":False,
        "cross_source_geojson_identity_approved":False,
        "independent_human_c_approved":False,
        "approved_safe_destinations":0,
        "for_disaster_use":False,
        "rows":records,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--scope",choices=sorted(ALLOWED_SCOPES),required=True)
    p.add_argument("--encoding",choices=sorted(ALLOWED_ENCODINGS),default="utf-8-sig")
    p.add_argument("--report-out",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.report_out.exists() or args.report_out.is_symlink():
            raise ValueError("OUTPUT_ALREADY_EXISTS")
        if not args.archive.is_file() or args.archive.stat().st_size>MAX_ARCHIVE_BYTES:
            raise ValueError("ARCHIVE_UNAVAILABLE_OR_TOO_LARGE")
        report=inspect_emergency_place_csv(
            args.archive.read_bytes(), args.scope, encoding=args.encoding
        )
        args.report_out.write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
        )
        print(json.dumps({
            "status":report["status"],
            "archive_rows_count":report["archive_rows_count"],
            "common_id_present_count":report["common_id_present_count"],
            "cross_source_geojson_identity_approved":False,
        },ensure_ascii=False))
        return 0
    except (OSError,ValueError) as exc:
        print("A GSI CSV ARCHIVE BLOCKED: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
