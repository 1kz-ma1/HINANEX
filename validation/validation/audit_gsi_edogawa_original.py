"""C independent GSI source audit: documentary/coordinate leads, no identity approval.

Use exact original GSI national CSV, A extraction, current D RegionExport and
existing C source-to-D audit produced on the SAME independent runner.

  python validation/validation/audit_gsi_edogawa_original.py \
    --gsi-raw /external/gsi_national_original_UNREVIEWED.csv \
    --a-gsi-report /external/gsi_edogawa_review_UNREVIEWED.json \
    --current-d /external/edogawa_current_D_UNREVIEWED.json \
    --c-source-audit /external/C_independent_current_D_source_consistency.json \
    --out /external/c_gsi_source_crosscheck_UNAPPROVED.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import unicodedata

from verify_edogawa_water_join import PRIORITY_SCHOOL_REFERENCES

GSI_ORIGIN = (
    "https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv"
)
EXPECTED_REGION = "東京都江戸川区"
REQUIRED = {
    "NO", "共通ID", "都道府県名及び市町村名", "施設・場所名",
    "住所", "洪水", "地震", "緯度", "経度",
}
PRIORITY = (
    ("都立葛西工科高校", "edogawa-d79a702373c6add7"),
    ("私立関東第一高校", "edogawa-fbe048a8e7100768"),
    ("下小岩小", "edogawa-63e5f1484966fd39"),
    ("旧下小岩小", "edogawa-f967bd79a9960d9e"),
)


class GsiIndependentAuditFailure(ValueError):
    pass


def _need(value, text):
    if not value:
        raise GsiIndependentAuditFailure(text)


def _geocoordinate(val, latitude=False):
    try:
        f = float(val)
    except (TypeError, ValueError) as exc:
        raise GsiIndependentAuditFailure("Invalid source coordinate") from exc
    _need(math.isfinite(f) and
          (-90 <= f <= 90 if latitude else -180 <= f <= 180),
          "Out-of-range/nonfinite source coordinate")
    return f


def _distance_m(a_lat, a_lon, b_lat, b_lon):
    """Meters between two separately sourced coordinates: review lead ONLY."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a_lat, a_lon, b_lat, b_lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return round(6371000 * 2 * math.asin(min(1, math.sqrt(h))), 2)


def audit(raw_gsi, a_report_raw, d_export_raw, c_audit_raw):
    try:
        a = json.loads(a_report_raw)
        d = json.loads(d_export_raw)
        c = json.loads(c_audit_raw)
    except (ValueError, TypeError) as exc:
        raise GsiIndependentAuditFailure("A/current-D/C JSON unreadable") from exc

    _need(isinstance(a, dict) and
          a.get("status") in (
              "GSI_EDOGAWA_ROWS_FOUND_UNREVIEWED",
              "GSI_EDOGAWA_ROWS_NOT_OBSERVED_REVIEW_REQUIRED",
          ), "A GSI report status is not original evidence")
    manifest = a.get("source_manifest")
    _need(isinstance(manifest, dict) and
          manifest.get("purpose") == "A_GSI_EDOGAWA_EVIDENCE_ONLY_NEVER_APPROVED"
          and manifest.get("requested_url") == GSI_ORIGIN
          and manifest.get("final_url") == GSI_ORIGIN
          and manifest.get("human_c_physical_pairs_approved") == 0
          and manifest.get("new_flood_candidates_or_exclusions") == 0
          and a.get("independent_c_site_approvals") == 0
          and a.get("new_flood_classifications") == 0
          and a.get("none_of_this_data_was_joined_to_current_d") is True,
          "A evidence source/provenance/approval boundary differs")
    actual_gsi_hash = sha256(raw_gsi).hexdigest()
    _need(actual_gsi_hash == manifest.get("national_source_sha256")
          and len(raw_gsi) == manifest.get("national_source_bytes"),
          "GSI original CSV SHA256/length does not match A source")
    try:
        decoded = raw_gsi.decode("utf-8-sig")
    except UnicodeError as exc:
        raise GsiIndependentAuditFailure("GSI original encoding invalid") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    columns = reader.fieldnames
    _need(isinstance(columns, list) and
          len(columns) == len(set(columns)) and
          REQUIRED.issubset(columns) and
          columns == manifest.get("original_csv_header"),
          "GSI original national CSV header/source version mismatch")

    total, source_rows, seen_ids = 0, [], set()
    for row in reader:
        total += 1
        _need(None not in row and all(v is not None for v in row.values()),
              "Malformed GSI national source row")
        region = unicodedata.normalize("NFKC", row["都道府県名及び市町村名"])
        if region != EXPECTED_REGION:
            continue
        ident = row["共通ID"].strip()
        _need(ident and ident not in seen_ids,
              "GSI municipality common IDs missing/duplicated")
        seen_ids.add(ident)
        _need(row["施設・場所名"].strip() and row["住所"].strip(),
              "GSI official place name or address missing")
        _need(row["洪水"].strip() in ("", "1") and
              row["地震"].strip() in ("", "1"),
              "GSI original disaster column has unexpected value")
        _geocoordinate(row["緯度"], latitude=True)
        _geocoordinate(row["経度"])
        source_rows.append((total + 1, row))

    _need(total == manifest.get("national_record_count_observed") and
          len(source_rows) == manifest.get("edogawa_record_count_observed"),
          "GSI original nationwide/municipality row count differs from A")
    expected_a = a.get("edogawa_rows")
    _need(isinstance(expected_a, list) and len(expected_a) == len(source_rows),
          "A extracted GSI rows missing or extra")
    for (line, row), record in zip(source_rows, expected_a):
        _need(record.get("original_national_csv_row") == line and
              record.get("original_columns_unmodified") == row and
              record.get("gsi_flood_marker_raw") == row["洪水"] and
              record.get("common_gsi_id_is_not_d_facility_id") is True and
              record.get("physical_site_link_c_approved") is False and
              record.get("current_d_flood_scenario_change") is None,
              "A changed official GSI source content or pretended facility acceptance")

    _need(c.get("audit_status") ==
          "SOURCE_SNAPSHOT_CONSISTENCY_CHECKED_NOT_FACILITY_IDENTITY_ACCEPTED"
          and c.get("c_approved_pairs") == 0
          and c.get("flood_candidates_or_exclusions_added") == 0,
          "Existing C source-to-D audit missing/not unapproved")
    _need(sha256(d_export_raw).hexdigest() ==
          c.get("source_sha256", {}).get("old_d_region_export"),
          "Current D exact input revision not bound to C audit")
    try:
        _need(d["region"]["code"] == "13123", "D export wrong region")
        datasets = [x for x in d["datasets"]
                    if x["requirement_code"] == "shelter_location"]
        _need(len(datasets) == 1, "D location dataset missing/duplicate")
        d_records = datasets[0]["records"]
        d_by_id = {record["id"]: record for record in d_records}
        _need(len(d_by_id) == len(d_records), "D facility IDs duplicated")
        scenarios = d["scenarios"]
        _need(len(scenarios) == 1 and
              scenarios[0]["scenario_id"] == "flood_shelter_selection",
              "Current D flood Scenario missing")
        results = scenarios[0]["facility_results"]
        _need(len(results) == len(d_by_id) and
              {x["facility_id"] for x in results} == set(d_by_id) and
              all(x["status"] == "UNKNOWN" and
                  x["fact"]["join_status"] == "UNVERIFIED" and
                  x["fact"]["official_status_raw"] is None for x in results),
              "D Scenario classified a site before independent C site approval")
    except (KeyError, TypeError, AttributeError) as exc:
        raise GsiIndependentAuditFailure("Current D export structure invalid") from exc

    # Exact GSI names are lookup aids, never automatically approved physical IDs.
    gsi_names = {}
    for line, row in source_rows:
        gsi_names.setdefault(row["施設・場所名"], []).append((line, row))

    cases = []
    for name, d_id in PRIORITY:
        entries = gsi_names.get(name, [])
        _need(len(entries) == 1, "Priority GSI institution absent or ambiguous: " + name)
        _need(d_id in d_by_id, "Priority D ID absent; independent review required")
        lineno, g = entries[0]
        dr = d_by_id[d_id]
        g_lat = _geocoordinate(g["緯度"], latitude=True)
        g_lon = _geocoordinate(g["経度"])
        d_lat = _geocoordinate(dr["latitude"], latitude=True)
        d_lon = _geocoordinate(dr["longitude"])
        cases.append({
            "gsi_national_line": lineno,
            "gsi_common_id_raw": g["共通ID"],
            "gsi_name_raw": g["施設・場所名"],
            "gsi_address_raw": g["住所"],
            "gsi_flood_raw": g["洪水"],
            "gsi_earthquake_raw": g["地震"],
            "gsi_latitude_raw": g["緯度"],
            "gsi_longitude_raw": g["経度"],
            "d_facility_id_for_independent_review_only": d_id,
            "d_name_from_official_csv": dr["name"],
            "d_latitude_from_official_csv": dr["latitude"],
            "d_longitude_from_official_csv": dr["longitude"],
            "coordinate_distance_m_review_only": _distance_m(
                g_lat, g_lon, d_lat, d_lon
            ),
            "this_distance_is_not_identity_acceptance": True,
            "c_human_physical_site_pair_approved": False,
            "d_flood_scenario_classification": "UNKNOWN",
            "flood_marker_blank_is_not_hazard_exclusion": True,
        })

    _need(len({x["gsi_common_id_raw"] for x in cases}) == len(cases) and
          len({x["d_facility_id_for_independent_review_only"] for x in cases}) == len(cases),
          "Former/current or independent institution GSI/D IDs collapse")

    hist = {k: dict(sorted(Counter(
        row[k] for _, row in source_rows
    ).items())) for k in ("洪水", "地震")}
    return {
        "status": "GSI_ORIGINAL_TO_A_AND_CURRENT_D_REVIEW_LEADS_NO_FACILITY_ACCEPTANCE",
        "source_gsi_national_sha256": actual_gsi_hash,
        "c_audited_current_d_sha256": sha256(d_export_raw).hexdigest(),
        "national_gsi_rows_independently_read": total,
        "edogawa_gsi_rows_independently_checked": len(source_rows),
        "current_d_facilities": len(d_by_id),
        "observed_gsi_hazard_markers_raw_counts": hist,
        "priority_gsi_to_d_coordinate_leads_ONLY": cases,
        "gsi_id_is_not_official_common_key_with_edogawa_d": True,
        "gsi_earthquake_only_rows_do_not_answer_municipal_water_standby_eligibility": True,
        "empty_gsi_flood_is_not_an_exclusion": True,
        "human_c_physical_site_pairs_approved": 0,
        "new_d_scenario_candidates_or_exclusions": 0,
        "current_d_scenario_all_unknown": True,
        "human_d_c_flood_only_semantics_review_required": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gsi-raw", required=True, type=Path)
    parser.add_argument("--a-gsi-report", required=True, type=Path)
    parser.add_argument("--current-d", required=True, type=Path)
    parser.add_argument("--c-source-audit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.exit(2, "Refusing to overwrite C independent audit\n")
    try:
        result = audit(args.gsi_raw.read_bytes(), args.a_gsi_report.read_bytes(),
                       args.current_d.read_bytes(), args.c_source_audit.read_bytes())
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, "C GSI audit failed; no approval: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["status"],
        "gsi_edogawa_rows": result["edogawa_gsi_rows_independently_checked"],
        "site_review_leads": len(result["priority_gsi_to_d_coordinate_leads_ONLY"]),
        "c_approved_pairs": 0,
        "flood_decisions": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
