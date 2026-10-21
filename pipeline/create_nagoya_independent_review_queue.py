"""Create a PRIVATE facility position review worksheet, never a GIS export.

Only locally recorded original pilot records and the same localhost ABR may
supply rows. Requires all three prior stage summaries + Stage 4 to agree.
Facility identity and exact site position require independent official sources.
The output contains facility names, addresses and tentative coordinates and
MUST remain inside the gitignored local pilot directory. Never share this CSV.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

from diagnose_nagoya_address_mismatch import (
    CATEGORIES, TARGET_REASON, check_snapshot, comparable_response,
    safe_failure_code, triage_address_mismatch,
)
from diagnose_nagoya_text_difference_stage2 import DIFFERENCE, validate_stage1
from diagnose_nagoya_kanji_chome_stage3 import (
    OUTCOMES, comparison_outcome, validate_stage2,
)
from diagnose_nagoya_chome_stage4_reference_screen import (
    OUTCOME_KEYS, diagnose_stage4, valid_point, screen_exact_reference,
    validate_stage3,
)
from geocode_nagoya_pilot import (
    BlockRedirects, classify, fetch_json, local_url, read_dataset,
    save_new,
)

OFFICIAL_REFERENCE = "https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html"
# Important: never authorize automatic map display from any of these categories.
REVIEW_A_NEW = "A_NEW_ADDRESS_REFERENCE_UNVERIFIED"
REVIEW_A_EXISTING = "A_EXISTING_ADDRESS_REFERENCE_UNVERIFIED"
REVIEW_B_PARCEL = "B_PARCEL_REFERENCE_REQUIRES_SPECIAL_REVIEW"

PRIVATE_FIELDS = (
    "review_priority", "pilot_record_id", "facility_name", "ward",
    "official_listed_address", "abr_reference_longitude", "abr_reference_latitude",
    "abr_coordinates_level", "reference_origin", "official_evidence_url",
    "official_evidence_date", "official_facility_type",
    "facility_identity_confirmed", "listed_address_crosschecked",
    "site_position_checked", "building_vs_entrance_checked",
    "independent_position_source_type", "reviewer", "reviewed_on",
    "review_status", "review_note",
)


def safe_csv_cell(obj: object) -> str:
    """Prevent spreadsheet formula interpretation while preserving private data."""
    val = "" if obj is None else str(obj)
    if val.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + val
    return val


def verify_stage4(stage4: dict, stage3: dict, stage1: dict,
                  original_summary: dict, resolution: dict, sha: str) -> None:
    expected = {
        "report_kind": "NAGOYA_STAGE4_TEXT_EQUAL_ADDRESS_REFERENCE_SCREEN_ONLY",
        "source_dataset_sha256": sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": resolution["provider_version"],
        "provider_db_version": resolution["provider_db_version"],
        "original_mismatches_rechecked": stage1["diagnosed_count"],
        "orthographic_text_equal_rechecked":
            stage3["comparison_outcomes"]["exact_after_kanji_chome_only"],
        "stage1_and_stage3_aggregate_counts_reproduced": True,
        "existing_unverified_candidates_unchanged":
            original_summary["unverified_candidate_count"],
        "source_suffix_cases_not_promoted":
            stage1["categories"]["source_suffix_not_matched"]
            + stage3["comparison_outcomes"]["source_suffix_unmatched_after_kanji_chome"],
        "original_pilot_unchanged": True,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "site_accuracy_independently_verified": False,
        "route_or_disaster_safety_verified": False,
    }
    if any(stage4.get(k) != v for k, v in expected.items()):
        raise ValueError("Stage-4 snapshot invalid")
    counts = stage4.get("screen_categories")
    if (not isinstance(counts, dict) or set(counts) != set(OUTCOME_KEYS)
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != expected["orthographic_text_equal_rechecked"]):
        raise ValueError("Stage-4 category totals invalid")


def make_row(record: dict, priority: str, point: tuple[float, float],
             coordinate_level: str, origin: str) -> dict:
    return {
        "review_priority": priority,
        "pilot_record_id": record["record_id"],
        "facility_name": record["name"],
        "ward": record["ward"],
        "official_listed_address": record["source_address"],
        "abr_reference_longitude": point[0],
        "abr_reference_latitude": point[1],
        "abr_coordinates_level": coordinate_level or "",
        "reference_origin": origin,
        "official_evidence_url": "",
        "official_evidence_date": "",
        "official_facility_type": "",
        "facility_identity_confirmed": "",
        "listed_address_crosschecked": "",
        "site_position_checked": "",
        "building_vs_entrance_checked": "",
        "independent_position_source_type": "",
        "reviewer": "",
        "reviewed_on": "",
        "review_status": "NOT_REVIEWED",
        "review_note": "REFERENCE_POINT_ONLY_NOT_APPROVED",
    }


def build_review_queue(manifest: dict, resolution: dict, summary: dict,
                       stage1: dict, stage2: dict, stage3: dict, stage4: dict,
                       dataset: dict, source_sha: str, server: str
                       ) -> tuple[list[dict], dict]:
    targets = check_snapshot(manifest, resolution, summary, dataset, source_sha)
    validate_stage1(stage1, resolution, source_sha, len(targets))
    validate_stage2(stage2, stage1, resolution, source_sha)
    validate_stage3(stage3, stage2, stage1, resolution, source_sha)
    verify_stage4(stage4, stage3, stage1, summary, resolution, source_sha)

    # Re-run the Stage-4 full aggregate consistency gate, including original
    # candidate duplicate detection. That result must match the saved report.
    live_stage4 = diagnose_stage4(
        manifest, resolution, summary, stage1, stage2, stage3,
        dataset, source_sha, server,
    )
    for key in ("screen_categories", "orthographic_text_equal_rechecked",
                "source_suffix_cases_not_promoted"):
        if live_stage4[key] != stage4[key]:
            raise ValueError("Stage-4 replay counts drift")

    base = local_url(server)
    opener = build_opener(ProxyHandler({}), BlockRedirects())
    health, _ = fetch_json(opener, base + "/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise ValueError("ABR health not OK")
    version, _ = fetch_json(opener, base + "/")
    if (not isinstance(version, dict) or version.get("name") != "abrg"
            or version.get("version") != resolution["provider_version"]
            or version.get("db_version") != resolution["provider_db_version"]
            or version.get("enabled_pref") != "23"
            or version.get("enabled_category") != "all"):
        raise ValueError("Local ABR version/pref/category changed")

    selected = []
    observed = Counter()
    for record in targets:
        uri = base + "/geocode?" + urlencode({
            "address": record["query_address"], "pref": "23",
            "limit": "2", "category": "all",
        })
        p, _ = fetch_json(opener, uri)
        q, _ = fetch_json(opener, uri)
        if comparable_response(p, version) != comparable_response(q, version):
            raise ValueError("ABR replay semantic drift")
        for replay in (p, q):
            result = classify(replay, record["query_address"], record["ward"])
            if result.get("status") != "UNRESOLVED" or result.get("reason") != TARGET_REASON:
                raise ValueError("Original unresolved classification changed")
        feature = p["features"][0]
        props = feature["properties"]
        if triage_address_mismatch(record["query_address"], props["matched_address"],
                                   record["ward"]) != DIFFERENCE:
            continue
        outcome, _ = comparison_outcome(
            record["query_address"], props["matched_address"], record["ward"],
        )
        if outcome != "exact_after_kanji_chome_only":
            continue
        point = valid_point(feature)
        # This is only for preparing the independent review list. The source
        # of truth for categories remains the reproduced Stage-4 aggregate.
        selected.append((record, props, point))

    occurrences = Counter(point for _, _, point in selected if point is not None)
    existing = []
    for row in resolution["results"]:
        if row["status"] not in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW"):
            continue
        g = row["derived_geometry"]
        point = (g["longitude"], g["latitude"])
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in point)
                or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90)
                or 0 in point):
            raise ValueError("Original candidate geometry invalid")
        occurrences[point] += 1
        existing.append((row, point))

    output = []
    for record, props, point in selected:
        category = screen_exact_reference(
            props, point, point is not None and occurrences[point] > 1,
        )
        observed[category] += 1
        if category == "high_resolution_reference_for_independent_review":
            output.append(make_row(
                record, REVIEW_A_NEW, point,
                props.get("coordinates_level"), "CHOME_TEXT_EQUAL_ABR_REFERENCE",
            ))
        elif category == "parcel_reference_requires_review" and point is not None:
            output.append(make_row(
                record, REVIEW_B_PARCEL, point,
                props.get("coordinates_level"), "PARCEL_ABR_REFERENCE",
            ))

    if {k: observed[k] for k in OUTCOME_KEYS} != stage4["screen_categories"]:
        raise ValueError("Stage-4 replay counts drift")
    for record, point in existing:
        priority = (REVIEW_A_EXISTING if record["status"] == "UNVERIFIED_CANDIDATE"
                    else REVIEW_B_PARCEL)
        output.append(make_row(
            record, priority, point, record.get("coordinates_level"),
            "ORIGINAL_UNVERIFIED_ABR_REFERENCE",
        ))

    # Cross-check that the local private file only includes the verified
    # screening categories and previously unapproved, selected pilot rows.
    selected_ids = {r["record_id"] for r in manifest["selected"]}
    if (len(output) != len({r["pilot_record_id"] for r in output})
            or any(r["pilot_record_id"] not in selected_ids for r in output)):
        raise ValueError("Private review queue identities inconsistent")
    tally = Counter(r["review_priority"] for r in output)
    expected_tally = {
        REVIEW_A_NEW: stage4["screen_categories"][
            "high_resolution_reference_for_independent_review"],
        REVIEW_A_EXISTING: summary["unverified_candidate_count"],
        REVIEW_B_PARCEL: stage4["screen_categories"][
            "parcel_reference_requires_review"] + summary["requires_review_count"],
    }
    if tally != Counter(expected_tally):
        raise ValueError("Review queue count mismatch")
    output.sort(key=lambda r: (r["review_priority"], r["ward"],
                               r["pilot_record_id"]))

    aggregate = {
        "report_kind": "NAGOYA_PRIVATE_REVIEW_QUEUE_PREPARATION_NOT_SITE_ACCEPTANCE",
        "source_dataset_sha256": source_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version["version"],
        "provider_db_version": version["db_version"],
        "review_queue_counts": dict(sorted(tally.items())),
        "total_review_rows": len(output),
        "original_sample_total": summary["sample_total"],
        "excluded_source_suffix_cases": stage4["source_suffix_cases_not_promoted"],
        "original_pilot_unchanged": True,
        "all_review_status_not_reviewed": True,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
        "notes": "Private local worksheet contains names, addresses and tentative reference points. Never publish or commit it.",
        "official_context_reference": OFFICIAL_REFERENCE,
    }
    return output, aggregate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--pilot-dir", type=Path, required=True)
    p.add_argument("--local-abr-url", default="http://127.0.0.1:3000")
    args = p.parse_args()

    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != allowed and allowed not in folder.parents:
        p.error("Only a gitignored local pilot directory is allowed")
    private_csv = folder / "independent_facility_position_review_PRIVATE.csv"
    public_counts = folder / "independent_review_queue_aggregate.json"
    if private_csv.exists() or public_counts.exists():
        p.error("Output already exists; review queue cannot overwrite")

    try:
        data, sha = read_dataset(args.dataset)
        names = (
            "manifest.json", "resolution.json", "summary.json",
            "mismatch_diagnostics_aggregate.json",
            "text_difference_stage2_aggregate.json",
            "kanji_chome_stage3_aggregate.json",
            "chome_stage4_reference_screen_aggregate.json",
        )
        inputs = [json.loads((folder / n).read_text("utf-8")) for n in names]
        rows, summary = build_review_queue(
            *inputs, data, sha, args.local_abr_url,
        )
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=PRIVATE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: safe_csv_cell(row.get(k)) for k in PRIVATE_FIELDS})
        # CSV must be written as CSV rather than serialized into JSON;
        # use exclusive creation to avoid destroying any manual review notes.
        with private_csv.open("x", encoding="utf-8", newline="") as handle:
            handle.write(buffer.getvalue())
        save_new(public_counts, summary)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Private review queue aborted [" + safe_failure_code(exc) +
               "]; do not share local files.\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
