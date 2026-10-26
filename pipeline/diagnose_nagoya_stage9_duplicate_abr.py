"""Read-only, offline Stage-9 provenance diagnostic for two Nagoya ABR points.

Only anonymized categorical output; no names, addresses, IDs or raw coordinates.
Never approves a site or modifies existing trial files.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from view_nagoya_stage7_private import read_stage7_private, validate
from compare_nagoya_gsi_offline import read_csv, validate_queue

ORIGINS = frozenset({
    "ORIGINAL_UNVERIFIED_ABR_REFERENCE",
    "CHOME_TEXT_EQUAL_ABR_REFERENCE",
    "PARCEL_ABR_REFERENCE",
})
STATUSES = frozenset({
    "UNVERIFIED_CANDIDATE", "NEEDS_REVIEW", "UNRESOLVED", "PROVIDER_ERROR",
})
REPORT_KIND = "NAGOYA_STAGE9_ABR_DUPLICATE_PROVENANCE_DIAGNOSTIC_ONLY"


def _point(row, prefix):
    lat, lon = row.get(prefix + "_latitude"), row.get(prefix + "_longitude")
    if lat in (None, "") or lon in (None, ""):
        return None
    lat, lon = float(lat), float(lon)
    if not math.isfinite(lat) or not math.isfinite(lon) or not (33 <= lat <= 38 and 133 <= lon <= 140):
        raise ValueError("invalid reference")
    return lat, lon


def analyze(rows, summary, queue, queue_summary, resolution, names):
    """Pure, fail-closed analysis: output contains no facility attributes."""
    validate(rows, summary)
    validate_queue(queue, queue_summary)
    if (len(queue) != len(rows)
            or queue_summary.get("source_dataset_sha256") != summary["source_dataset_sha256"]
            or queue_summary.get("provider_version") != summary["provider_version"]
            or queue_summary.get("provider_db_version") != summary["provider_db_version"]):
        raise ValueError("review queue snapshot mismatch")
    by_queue = {row["pilot_record_id"]: row for row in queue}
    for row in rows:
        prior = by_queue.get(row["pilot_record_id"])
        if (prior is None or prior["facility_name"] != row["facility_name"]
                or prior["official_listed_address"] != row["official_listed_address"]
                or prior["review_priority"] != row["review_priority"]
                or _point(prior, "abr_reference") != _point(row, "abr_reference")):
            raise ValueError("stage7 and original queue differ")
    if (not isinstance(resolution, dict)
            or resolution.get("source_dataset_sha256") != summary["source_dataset_sha256"]
            or resolution.get("provider_version") != summary["provider_version"]
            or resolution.get("provider_db_version") != summary["provider_db_version"]
            or resolution.get("approved_for_map") is not False
            or resolution.get("data_promotion_authorized") is not False):
        raise ValueError("source/version/safety gate mismatch")
    original = resolution.get("results")
    if not isinstance(original, list) or not original:
        raise ValueError("missing original results")
    by_id = {}
    for old in original:
        if (not isinstance(old, dict) or not isinstance(old.get("record_id"), str)
                or old["record_id"] in by_id
                or old.get("status") not in STATUSES
                or old.get("approved_for_map") is not False):
            raise ValueError("original pilot state invalid")
        by_id[old["record_id"]] = old

    if (not isinstance(names, (tuple, list)) or len(names) != 2
            or not all(isinstance(n, str) and n.strip() for n in names)
            or names[0] == names[1]):
        raise ValueError("invalid selected facilities")

    selected, facts = [], []
    for name in names:
        matches = [r for r in rows if r["facility_name"] == name]
        if len(matches) != 1 or matches[0]["stage7_priority"] != "P1_DISTANCE_OR_PARCEL_REVIEW":
            raise ValueError("facility not uniquely found in P1")
        row = matches[0]
        old = by_id.get(row["pilot_record_id"])
        metadata = by_queue[row["pilot_record_id"]]
        origin = metadata["reference_origin"]
        if old is None or origin not in ORIGINS:
            raise ValueError("unknown origin or original record")
        abr = _point(row, "abr_reference")
        if abr is None:
            raise ValueError("missing ABR point")
        geo = old.get("derived_geometry")
        original_point = None
        if isinstance(geo, dict):
            # Historical pilot stores geometry as latitude/longitude (not prefix).
            original_point = _point({"old_latitude": geo.get("latitude"),
                                     "old_longitude": geo.get("longitude")}, "old")
        is_initial = origin == "ORIGINAL_UNVERIFIED_ABR_REFERENCE"
        if is_initial and (old["status"] not in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW")
                           or original_point is None):
            raise ValueError("initial candidate provenance invalid")
        if not is_initial and old["status"] != "UNRESOLVED":
            raise ValueError("stage4 candidate provenance invalid")
        selected.append(row)
        facts.append({
            "reference_origin": origin,
            "coordinate_level": metadata["abr_coordinates_level"]
                if metadata["abr_coordinates_level"] in ("parcel", "rsdtdsp_blk", "rsdtdsp_rsdt") else "UNCLASSIFIED",
            "original_pilot_status": old["status"],
            "initial_reference_preserved": abr == original_point if original_point else None,
            "original_duplicate_flag": "shared_reference_coordinate" in old.get("reason", "")
                if isinstance(old.get("reason"), str) else False,
        })

    gsi_1 = _point(selected[0], "gsi_reference")
    gsi_2 = _point(selected[1], "gsi_reference")
    if gsi_1 is None or gsi_2 is None:
        gsi_relation = "INSUFFICIENT_DATA"
    else:
        gsi_relation = "SAME" if gsi_1 == gsi_2 else "DIFFERENT"
    initial_count = sum(f["reference_origin"] == "ORIGINAL_UNVERIFIED_ABR_REFERENCE"
                        for f in facts)
    stage = ("ORIGINAL_PILOT_BOTH" if initial_count == 2
             else "STAGE4_BOTH" if initial_count == 0 else "MIXED_ORIGINS")
    return {
        "report_kind": REPORT_KIND,
        "dataset_fingerprint_and_provider_versions_match": True,
        "selected_p1_rows": 2,
        "same_abr_reference": _point(selected[0], "abr_reference") ==
                              _point(selected[1], "abr_reference"),
        "gsi_reference_relation": gsi_relation,
        "earliest_recorded_origin_group": stage,
        "facility_1": facts[0],
        "facility_2": facts[1],
        "root_cause": "UNCONFIRMED",
        "next_step": "HUMAN_LOCAL_ABR_RESPONSE_AND_INDEPENDENT_SITE_EVIDENCE_CHECK",
        "site_position_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "official_facility_positions_accepted": 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Offline anonymized ABR duplicate provenance")
    parser.add_argument("--pilot-dir", required=True, type=Path)
    args = parser.parse_args()
    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != root and root not in folder.parents:
        parser.error("The pilot directory must be within the local gitignored pilot root")
    try:
        rows = read_stage7_private(folder / "gsi_stage7_refined_PRIVATE.csv")
        summary = json.loads((folder / "gsi_stage7_refined_aggregate.json").read_text("utf-8"))
        queue, _ = read_csv(folder / "independent_facility_position_review_PRIVATE.csv")
        queue_summary = json.loads((folder / "independent_review_queue_aggregate.json").read_text("utf-8"))
        resolution = json.loads((folder / "resolution.json").read_text("utf-8"))
        # Private input stays on terminal; neither values nor file content are written out.
        names = (input("対象施設1名（ローカル入力）: ").strip(),
                 input("対象施設2名（ローカル入力）: ").strip())
        report = analyze(rows, summary, queue, queue_summary, resolution, names)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, EOFError):
        print("ABORT: LOCAL_DIAGNOSTIC_INPUT_INVALID; no data changed", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
