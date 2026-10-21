"""Local-only Stage 6: prioritize ABR/GSI differences for human site review.

Rebuilds Stage-5 results from the original operator-provided GSI CSV files.
Writes precise facility details ONLY inside the gitignored private CSV;
the JSON printed to stdout contains anonymous counts and explicit NO-GO.
No network calls, no GIS/RegionExport updates, no automatic acceptance.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import Counter
from pathlib import Path

from compare_nagoya_gsi_offline import (
    PRIVATE_COMPARISON_FIELDS, STATUS, address_for_queue, compare,
    distance_m, gsi_address_key, name_key, parse_gsi, read_csv,
)
from create_nagoya_independent_review_queue import (
    REVIEW_B_PARCEL, safe_csv_cell,
)
from diagnose_nagoya_kanji_chome_stage3 import canonical_chome_address
from geocode_nagoya_pilot import save_new

FLAGS = (
    "gsi_conflicting_reference_points",
    "different_facility_name_at_same_address",
    "abr_gsi_reference_distance_at_least_100m",
    "parcel_reference_requires_special_review",
    "other_gsi_incomplete_correspondence",
)
LEVELS = ("P0_IDENTITY_OR_GSI_CONFLICT", "P1_DISTANCE_OR_PARCEL",
          "P2_STANDARD_SITE_REVIEW")
EXTRA = (
    "stage6_priority", "stage6_risk_flags", "gsi_conflict_points_PRIVATE",
    "gsi_other_names_PRIVATE", "official_site_evidence_url",
    "official_evidence_date", "facility_identity_evidence",
    "site_position_evidence", "entrance_or_building_evidence",
    "gsi_conflict_explanation", "distance_discrepancy_explanation",
    "parcel_offset_evaluation", "facility_type_confirmed",
    "reviewer", "reviewed_at", "review_status", "approval_gate",
)


def verify_prior_results(queue: list[dict], queue_summary: dict,
                         old_rows: list[dict], old_aggregate: dict,
                         gsi: list[dict], provenance: dict) -> list[dict]:
    if (old_aggregate.get("report_kind") !=
            "NAGOYA_STAGE5_GSI_OFFLINE_CROSS_REFERENCE_NOT_SITE_ACCEPTANCE"
            or old_aggregate.get("approved_for_map") is not False
            or old_aggregate.get("data_promotion_authorized") is not False
            or old_aggregate.get("site_position_independently_verified") is not False
            or old_aggregate.get("official_facility_positions_accepted") != 0
            or old_aggregate.get("route_or_disaster_safety_verified") is not False
            or old_aggregate.get("original_pilot_unchanged") is not True
            or old_aggregate.get("source_dataset_sha256")
               != queue_summary.get("source_dataset_sha256")
            or old_aggregate.get("provider_version")
               != queue_summary.get("provider_version")
            or old_aggregate.get("provider_db_version")
               != queue_summary.get("provider_db_version")
            or old_aggregate.get("gsi_csv_provenance") != provenance):
        raise ValueError("Stage-5 provenance changed")
    reconstructed, summary = compare(queue, queue_summary, gsi, provenance)
    for field in (
        "status_counts", "status_by_review_priority",
        "distance_bands_for_strict_unique_matches", "private_review_queue_count",
        "gsi_csv_provenance", "source_dataset_sha256",
    ):
        if summary[field] != old_aggregate.get(field):
            raise ValueError("Stage-5 aggregate changed")
    if len(old_rows) != len(reconstructed):
        raise ValueError("Stage-5 private rows changed")
    for old, new in zip(old_rows, reconstructed):
        if set(old) != set(PRIVATE_COMPARISON_FIELDS):
            raise ValueError("Stage-5 private header changed")
        for key in PRIVATE_COMPARISON_FIELDS:
            if old[key] != safe_csv_cell(new.get(key)):
                raise ValueError("Stage-5 private record changed")
        if old["independent_site_position_approved"] != "NO":
            raise ValueError("Site position approval forbidden")
    return reconstructed


def local_references(row: dict, gsi: list[dict]) -> tuple[list[dict], list[str]]:
    ward = row["ward"]
    full = address_for_queue(row["official_listed_address"], ward)
    key, _, unknown = canonical_chome_address(full)
    if unknown:
        raise ValueError("Unrecognized source chome")
    by_address = [r for r in gsi if gsi_address_key(r["address"], ward) == key]
    name = name_key(row["facility_name"])
    strict = [r for r in by_address if r["name"] == name]
    different_names = sorted({r["name"] for r in by_address if r["name"] != name})
    return strict, different_names


def triage(queue: list[dict], queue_summary: dict,
           old_rows: list[dict], old_aggregate: dict,
           gsi: list[dict], provenance: dict) -> tuple[list[dict], dict]:
    reconstructed = verify_prior_results(
        queue, queue_summary, old_rows, old_aggregate, gsi, provenance,
    )
    ranks, flags_total, statuses = Counter(), Counter(), Counter()
    flagged_rows = multi_flag_rows = 0
    results = []
    for row in reconstructed:
        status = row["gsi_cross_reference_status"]
        if status not in STATUS:
            raise ValueError("Unknown GSI status")
        flags = []
        if status == "strict_name_address_conflicting_references":
            flags.append(FLAGS[0])
        elif status == "address_match_only_name_unconfirmed":
            flags.append(FLAGS[1])
        elif status != "strict_name_address_unique_reference":
            flags.append(FLAGS[4])
        if status == "strict_name_address_unique_reference":
            meters = row["gsi_abr_distance_meters"]
            if type(meters) not in (float, int) or not math.isfinite(meters) or meters < 0:
                raise ValueError("Invalid GSI distance")
            if meters >= 100:
                flags.append(FLAGS[2])
        if row["review_priority"] == REVIEW_B_PARCEL:
            flags.append(FLAGS[3])
        rank = (LEVELS[0] if any(flag in flags for flag in
                                (FLAGS[0], FLAGS[1], FLAGS[4]))
                else LEVELS[1] if flags else LEVELS[2])
        strict, alternate_names = local_references(row, gsi)
        points = sorted({r["point"] for r in strict if r["point"] is not None})
        if status == "strict_name_address_conflicting_references" and len(points) < 2:
            raise ValueError("Missing GSI conflicting references")
        if status == "address_match_only_name_unconfirmed" and not alternate_names:
            raise ValueError("Missing GSI alternate facility identity")
        private_points = []
        if status == "strict_name_address_conflicting_references":
            abr = (float(row["abr_reference_longitude"]),
                   float(row["abr_reference_latitude"]))
            for point in points:
                private_points.append({
                    "longitude": point[0], "latitude": point[1],
                    "abr_distance_meters": round(distance_m(abr, point), 1),
                    "gsi_types": sorted({r["kind"] for r in strict
                                         if r["point"] == point}),
                })
        entry = {k: row.get(k, "") for k in PRIVATE_COMPARISON_FIELDS}
        entry.update({
            "stage6_priority": rank,
            "stage6_risk_flags": ";".join(flags),
            "gsi_conflict_points_PRIVATE": json.dumps(
                private_points, ensure_ascii=False) if private_points else "",
            "gsi_other_names_PRIVATE": (
                ";".join(alternate_names)
                if status == "address_match_only_name_unconfirmed" else ""),
            **{k: "" for k in EXTRA[4:-2]},
            "review_status": "NOT_REVIEWED",
            "approval_gate": "BLOCKED_PENDING_MANUAL_SITE_VERIFICATION",
        })
        results.append(entry)
        ranks[rank] += 1
        flags_total.update(flags)
        statuses[status] += 1
        flagged_rows += bool(flags)
        multi_flag_rows += len(flags) > 1

    if (len(results) != old_aggregate["private_review_queue_count"]
            or {status: statuses[status] for status in STATUS}
               != old_aggregate["status_counts"]):
        raise ValueError("Stage-6 totals do not match Stage-5")
    results.sort(key=lambda r: (
        LEVELS.index(r["stage6_priority"]), r["review_priority"],
        r["pilot_record_id"],
    ))
    aggregate = {
        "report_kind": "NAGOYA_STAGE6_MANUAL_GSI_DISCREPANCY_TRIAGE_NOT_SITE_APPROVAL",
        "source_dataset_sha256": old_aggregate["source_dataset_sha256"],
        "provider_version": old_aggregate["provider_version"],
        "provider_db_version": old_aggregate["provider_db_version"],
        "gsi_csv_provenance": provenance,
        "total_private_review_rows": len(results),
        "priority_counts": {rank: ranks[rank] for rank in LEVELS},
        "risk_flag_counts": {flag: flags_total[flag] for flag in FLAGS},
        "distinct_rows_flagged": flagged_rows,
        "rows_with_overlapping_flags": multi_flag_rows,
        "stage5_status_counts_reproduced": True,
        "all_review_status_not_reviewed": True,
        "privacy": "Do not upload or commit the private Stage-6 worksheet",
        "official_facility_positions_accepted": 0,
        "site_position_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
        "original_pilot_unchanged": True,
    }
    return results, aggregate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-dir", required=True, type=Path)
    p.add_argument("--gsi-emergency", type=Path)
    p.add_argument("--gsi-shelter", type=Path)
    args = p.parse_args()
    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != allowed and allowed not in folder.parents:
        p.error("Only a gitignored pilot directory is allowed")
    sources = [(kind, path.resolve()) for kind, path in
               (("emergency", args.gsi_emergency),
                ("shelter", args.gsi_shelter)) if path is not None]
    if not sources or len({path for _, path in sources}) != len(sources):
        p.error("Specify the actual distinct GSI CSVs used in Stage-5")
    if any(folder not in path.parents for _, path in sources):
        p.error("GSI CSVs must remain inside the gitignored pilot directory")
    out_private = folder / "gsi_stage6_review_PRIVATE.csv"
    out_aggregate = folder / "gsi_stage6_triage_aggregate.json"
    if out_private.exists() or out_aggregate.exists():
        p.error("Stage-6 outputs already exist; manual review must not be overwritten")
    try:
        queue, _ = read_csv(folder / "independent_facility_position_review_PRIVATE.csv")
        queue_summary = json.loads((folder / "independent_review_queue_aggregate.json").read_text("utf-8"))
        old_rows, _ = read_csv(folder / "gsi_cross_reference_PRIVATE.csv")
        old_aggregate = json.loads((folder / "gsi_cross_reference_aggregate.json").read_text("utf-8"))
        gsi, provenance = parse_gsi(sources)
        rows, aggregate = triage(queue, queue_summary, old_rows,
                                 old_aggregate, gsi, provenance)
        buffer = io.StringIO(newline="")
        columns = (*PRIVATE_COMPARISON_FIELDS, *EXTRA)
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: safe_csv_cell(row.get(field, ""))
                             for field in columns})
        with out_private.open("x", encoding="utf-8", newline="") as handle:
            handle.write(buffer.getvalue())
        save_new(out_aggregate, aggregate)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Stage-6 stopped [" + type(exc).__name__ +
               "]; no site positions approved.\n")
    print(json.dumps(aggregate, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
