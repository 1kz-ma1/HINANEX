"""Versioned, offline Stage-7 refinement of GSI reference / name-note diagnostics.

Keeps Stage-5 and Stage-6 reports immutable. The new PRIVATE worksheet retains
all raw references and source notice verbatim; only anonymous counts are printed.
A reference point or name match NEVER authorizes site acceptance or reopening.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from compare_nagoya_gsi_offline import (
    address_for_queue, distance_m, gsi_address_key, name_key, parse_gsi,
    read_csv,
)
from create_nagoya_independent_review_queue import safe_csv_cell
from diagnose_nagoya_kanji_chome_stage3 import canonical_chome_address
from geocode_nagoya_pilot import save_new
from triage_nagoya_gsi_stage6 import (
    EXTRA, FLAGS, LEVELS, local_references, triage,
)
from compare_nagoya_gsi_offline import PRIVATE_COMPARISON_FIELDS

# Diagnostic tolerance ONLY. Never alters, rounds or chooses stored GSI coords.
NEAR_COINCIDENT_METERS = 0.001

# Supported source notice: "施設名※R8.7.11～R9.3.31まで改修工事のため、使用不可".
# Do not strip unrelated annotations, inferred abbreviations, or names.
RENOVATION_NOTICE = re.compile(
    r"^(?P<base>[^※]+)※R(?P<sy>[1-9]\d?)\.(?P<sm>\d{1,2})\.(?P<sd>\d{1,2})"
    r"[~〜～]R(?P<ey>[1-9]\d?)\.(?P<em>\d{1,2})\.(?P<ed>\d{1,2})"
    r"まで(?P<reason>[^※]*工事)のため、使用不可$"
)
STATES = (
    "gsi_distinct_references_under_1mm",
    "source_renovation_notice_name_correspondence",
    "unchanged_unresolved_identity_or_gsi_conflict",
    "unchanged_standard_reference",
)
RANKS = ("P0_IDENTITY_OR_OPERATIONAL_RESTRICTION",
         "P1_DISTANCE_OR_PARCEL_REVIEW",
         "P2_INDEPENDENT_SITE_REVIEW_REQUIRED")
ADDED_FIELDS = (
    "stage7_classification", "stage7_priority", "source_base_facility_name_PRIVATE",
    "source_renovation_start", "source_renovation_end",
    "source_renovation_reason_PRIVATE", "source_notice_verbatim_PRIVATE",
    "original_gsi_reference_points_preserved", "facility_use_status_verified",
    "facility_reopening_verified", "independent_site_position_approved",
    "manual_review_required", "stage7_review_status",
)


def parse_renovation_notice(name: str) -> dict | None:
    if not isinstance(name, str):
        return None
    text = unicodedata.normalize("NFKC", name).strip()
    m = RENOVATION_NOTICE.fullmatch(text)
    if not m or not m.group("base").strip() or not m.group("reason").strip():
        return None
    try:
        start = date(2018 + int(m.group("sy")), int(m.group("sm")), int(m.group("sd")))
        end = date(2018 + int(m.group("ey")), int(m.group("em")), int(m.group("ed")))
    except ValueError:
        return None
    if end < start:
        return None
    return {
        "base_name": m.group("base").strip(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "reason": m.group("reason"),
        "source_notice": name,
    }


def match_official_name_without_notice(queue_row: dict, gsi: list[dict],
                                        parsed: dict) -> bool:
    ward = queue_row["ward"]
    key, _, unknown = canonical_chome_address(
        address_for_queue(queue_row["official_listed_address"], ward)
    )
    if unknown:
        return False
    targets = [
        r for r in gsi
        if (gsi_address_key(r["address"], ward) == key
            and r["name"] == name_key(parsed["base_name"]))
    ]
    # A name/address correspondence, not a unique-coordinate conclusion.
    return bool(targets)


def near_coincident_strict_references(stage6_row: dict, gsi: list[dict]) -> bool:
    strict, _ = local_references(stage6_row, gsi)
    points = sorted({r["point"] for r in strict if r["point"] is not None})
    if len(points) < 2:
        return False
    return all(
        distance_m(left, right) < NEAR_COINCIDENT_METERS
        for i, left in enumerate(points) for right in points[i + 1:]
    )


def verify_stage6(queue: list[dict], queue_summary: dict,
                  stage5_rows: list[dict], stage5_summary: dict,
                  stage6_rows: list[dict], stage6_summary: dict,
                  gsi: list[dict], provenance: dict) -> list[dict]:
    if (stage6_summary.get("report_kind") !=
            "NAGOYA_STAGE6_MANUAL_GSI_DISCREPANCY_TRIAGE_NOT_SITE_APPROVAL"
            or stage6_summary.get("gsi_csv_provenance") != provenance
            or stage6_summary.get("source_dataset_sha256") !=
               queue_summary.get("source_dataset_sha256")
            or stage6_summary.get("all_review_status_not_reviewed") is not True
            or stage6_summary.get("original_pilot_unchanged") is not True
            or stage6_summary.get("site_position_independently_verified") is not False
            or stage6_summary.get("official_facility_positions_accepted") != 0
            or stage6_summary.get("approved_for_map") is not False
            or stage6_summary.get("data_promotion_authorized") is not False
            or stage6_summary.get("route_or_disaster_safety_verified") is not False):
        raise ValueError("Stage-6 provenance or safety invariant changed")
    rebuilt, agg = triage(queue, queue_summary, stage5_rows, stage5_summary,
                          gsi, provenance)
    for field in ("priority_counts", "risk_flag_counts", "distinct_rows_flagged",
                  "rows_with_overlapping_flags", "total_private_review_rows",
                  "stage5_status_counts_reproduced"):
        if stage6_summary.get(field) != agg[field]:
            raise ValueError("Stage-6 aggregate replay changed")
    if len(stage6_rows) != len(rebuilt):
        raise ValueError("Stage-6 private row count changed")
    expected = (*PRIVATE_COMPARISON_FIELDS, *EXTRA)
    by_id = {r["pilot_record_id"]: r for r in rebuilt}
    if len(by_id) != len(rebuilt):
        raise ValueError("Stage-6 duplicate record ID")
    for prior in stage6_rows:
        if (set(prior) != set(expected) or prior.get("pilot_record_id") not in by_id
                or prior.get("review_status") != "NOT_REVIEWED"
                or prior.get("approval_gate") !=
                   "BLOCKED_PENDING_MANUAL_SITE_VERIFICATION"):
            raise ValueError("Stage-6 private record invalid")
        current = by_id[prior["pilot_record_id"]]
        if any(prior[k] != safe_csv_cell(current.get(k, "")) for k in expected):
            raise ValueError("Stage-6 private row changed")
    return rebuilt


def refine(queue: list[dict], queue_summary: dict,
           stage5_rows: list[dict], stage5_summary: dict,
           stage6_rows: list[dict], stage6_summary: dict,
           gsi: list[dict], provenance: dict) -> tuple[list[dict], dict]:
    previous = verify_stage6(queue, queue_summary, stage5_rows, stage5_summary,
                             stage6_rows, stage6_summary, gsi, provenance)
    qids = {r["pilot_record_id"]: r for r in queue}
    refined, states, ranks = [], Counter(), Counter()
    notice_count = near_count = 0

    for row in previous:
        original_status = row["gsi_cross_reference_status"]
        original_flags = row["stage6_risk_flags"].split(";") if row["stage6_risk_flags"] else []
        state = "unchanged_standard_reference"
        parsed = None
        near = False
        if original_status == "strict_name_address_conflicting_references":
            near = near_coincident_strict_references(row, gsi)
            state = ("gsi_distinct_references_under_1mm" if near
                     else "unchanged_unresolved_identity_or_gsi_conflict")
        elif original_status == "address_match_only_name_unconfirmed":
            parsed = parse_renovation_notice(row["facility_name"])
            if parsed and match_official_name_without_notice(
                qids[row["pilot_record_id"]], gsi, parsed
            ):
                state = "source_renovation_notice_name_correspondence"
            else:
                parsed = None
                state = "unchanged_unresolved_identity_or_gsi_conflict"
        elif original_status != "strict_name_address_unique_reference":
            state = "unchanged_unresolved_identity_or_gsi_conflict"

        if near:
            near_count += 1
        if parsed:
            notice_count += 1

        # A name with a declared unusable interval is ALWAYS P0 until an
        # authorized operator verifies current operational status independently.
        if (parsed or state == "unchanged_unresolved_identity_or_gsi_conflict"):
            rank = RANKS[0]
        elif ((FLAGS[2] in original_flags) or (FLAGS[3] in original_flags)):
            rank = RANKS[1]
        else:
            rank = RANKS[2]

        result = dict(row)
        result.update({
            "stage7_classification": state,
            "stage7_priority": rank,
            "source_base_facility_name_PRIVATE": parsed["base_name"] if parsed else "",
            "source_renovation_start": parsed["start"] if parsed else "",
            "source_renovation_end": parsed["end"] if parsed else "",
            "source_renovation_reason_PRIVATE": parsed["reason"] if parsed else "",
            "source_notice_verbatim_PRIVATE": parsed["source_notice"] if parsed else "",
            "original_gsi_reference_points_preserved": "YES",
            "facility_use_status_verified": "NO",
            "facility_reopening_verified": "NO",
            "independent_site_position_approved": "NO",
            "manual_review_required": "YES",
            "stage7_review_status": "NOT_REVIEWED",
        })
        refined.append(result)
        states[state] += 1
        ranks[rank] += 1

    refined.sort(key=lambda row: (
        RANKS.index(row["stage7_priority"]), row["review_priority"],
        row["pilot_record_id"],
    ))
    if len(refined) != stage6_summary["total_private_review_rows"]:
        raise ValueError("Refined count changed")
    aggregate = {
        "report_kind": "NAGOYA_STAGE7_VERSIONED_REFERENCE_AND_RENOVATION_REFINEMENT",
        "source_dataset_sha256": stage6_summary["source_dataset_sha256"],
        "provider_version": stage6_summary["provider_version"],
        "provider_db_version": stage6_summary["provider_db_version"],
        "gsi_csv_provenance": provenance,
        "historical_stage6_priority_counts": stage6_summary["priority_counts"],
        "review_rows_total": len(refined),
        "refined_classifications": {k: states[k] for k in STATES},
        "refined_priority_counts": {k: ranks[k] for k in RANKS},
        "near_coincident_distinct_gsi_reference_cases": near_count,
        "recognized_source_renovation_notice_name_matches": notice_count,
        "near_coincident_threshold_m": NEAR_COINCIDENT_METERS,
        "all_raw_gsi_reference_points_preserved": True,
        "source_restrictions_do_not_establish_current_availability": True,
        "source_end_date_does_not_auto_reopen": True,
        "all_review_status_not_reviewed": True,
        "historical_stage5_stage6_unchanged": True,
        "official_facility_positions_accepted": 0,
        "site_position_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }
    return refined, aggregate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-dir", type=Path, required=True)
    p.add_argument("--gsi-emergency", type=Path)
    p.add_argument("--gsi-shelter", type=Path)
    args = p.parse_args()
    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != allowed and allowed not in folder.parents:
        p.error("Only a gitignored local pilot directory is allowed")
    inputs = [(kind, path.resolve()) for kind, path in (
        ("emergency", args.gsi_emergency), ("shelter", args.gsi_shelter)
    ) if path is not None]
    if (not inputs or len({path for _, path in inputs}) != len(inputs)
            or any(folder not in path.parents for _, path in inputs)):
        p.error("GSI inputs must be distinct original CSV files inside pilot directory")
    private_out = folder / "gsi_stage7_refined_PRIVATE.csv"
    aggregate_out = folder / "gsi_stage7_refined_aggregate.json"
    if private_out.exists() or aggregate_out.exists():
        p.error("Stage-7 outputs already exist; previous results are immutable")
    try:
        queue, _ = read_csv(folder / "independent_facility_position_review_PRIVATE.csv")
        queue_agg = json.loads((folder / "independent_review_queue_aggregate.json").read_text("utf-8"))
        stage5, _ = read_csv(folder / "gsi_cross_reference_PRIVATE.csv")
        stage5_agg = json.loads((folder / "gsi_cross_reference_aggregate.json").read_text("utf-8"))
        stage6, _ = read_csv(folder / "gsi_stage6_review_PRIVATE.csv")
        stage6_agg = json.loads((folder / "gsi_stage6_triage_aggregate.json").read_text("utf-8"))
        gsi, provenance = parse_gsi(inputs)
        rows, aggregate = refine(queue, queue_agg, stage5, stage5_agg,
                                  stage6, stage6_agg, gsi, provenance)
        cols = (*PRIVATE_COMPARISON_FIELDS, *EXTRA, *ADDED_FIELDS)
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_csv_cell(row.get(key, "")) for key in cols})
        with private_out.open("x", encoding="utf-8", newline="") as output:
            output.write(buffer.getvalue())
        save_new(aggregate_out, aggregate)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Stage-7 aborted [" + type(exc).__name__ +
               "]; no existing data or approvals changed.\n")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
