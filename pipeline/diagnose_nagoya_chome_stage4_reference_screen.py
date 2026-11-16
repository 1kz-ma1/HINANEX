"""Local Stage-4 quality SCREEN for address references; never accepts site geometry.

Replays the immutable 37 mismatches against localhost ABR and emits ONLY
anonymous counts for the 27 chome-only text-equal cases. All previous reports,
the canonical dataset, GIS, and official coordinates are read-only.
"""
from __future__ import annotations

import argparse
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
from diagnose_nagoya_text_difference_stage2 import (
    DIFFERENCE, validate_stage1,
)
from diagnose_nagoya_kanji_chome_stage3 import (
    OUTCOMES, comparison_outcome, validate_stage2,
)
from geocode_nagoya_pilot import (
    BlockRedirects, classify, fetch_json, local_url, read_dataset, save_new,
)

HIGH_LEVELS = frozenset({"rsdtdsp_blk", "rsdtdsp_rsdt"})
OUTCOME_KEYS = (
    "high_resolution_reference_for_independent_review",
    "parcel_reference_requires_review",
    "coarse_or_unknown_address_match",
    "coarse_or_unknown_coordinate_reference",
    "invalid_or_missing_point",
    "shared_reference_coordinate_requires_review",
    "unexpected_unmatched_address",
)


def valid_point(feature: dict) -> tuple[float, float] | None:
    geometry = feature.get("geometry")
    coords = (geometry.get("coordinates") if isinstance(geometry, dict)
              and geometry.get("type") == "Point" else None)
    if not isinstance(coords, list) or len(coords) != 2:
        return None
    lon, lat = coords
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in coords):
        return None
    if lon == 0 or lat == 0 or not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return (lon, lat)


def validate_stage3(stage3: dict, stage2: dict, stage1: dict,
                    resolution: dict, source_sha: str) -> None:
    target = stage2["stage2_target_count"]
    expected = {
        "report_kind": "NAGOYA_CHOME_ONLY_STAGE3_ORTHOGRAPHIC_DIAGNOSTIC",
        "source_dataset_sha256": source_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": resolution["provider_version"],
        "provider_db_version": resolution["provider_db_version"],
        "original_mismatches_rechecked": stage1["diagnosed_count"],
        "stage2_target_count": target,
        "stage1_and_stage2_categories_reproduced": True,
        "original_response_semantic_equivalence_proven": False,
        "text_equivalence_is_not_facility_location_verification": True,
        "original_pilot_unchanged": True,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "site_accuracy_independently_verified": False,
        "route_or_disaster_safety_verified": False,
    }
    if any(stage3.get(k) != v for k, v in expected.items()):
        raise ValueError("Stage-3 snapshot invalid")
    counts = stage3.get("comparison_outcomes")
    if (not isinstance(counts, dict) or set(counts) != set(OUTCOMES)
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != target
            or counts["exact_after_kanji_chome_only"] == 0):
        raise ValueError("Stage-3 counts invalid")
    matched = stage3.get("exact_normalized_matches_without_unmatched_field_count")
    if type(matched) is not int or not 0 <= matched <= counts["exact_after_kanji_chome_only"]:
        raise ValueError("Stage-3 count schema invalid")
    converted = stage3.get("chome_number_conversions_count")
    if type(converted) is not int or converted < 0:
        raise ValueError("Stage-3 conversion count invalid")


def screen_exact_reference(props: dict, point: tuple[float, float] | None,
                           shared: bool) -> str:
    """Classify diagnostic reference QUALITY, never infer a facility's location."""
    if props.get("unmatched_address") not in (None, []):
        return "unexpected_unmatched_address"
    # Upstream ABR parcel reference has documented potential offset risks.
    if (props.get("match_level") == "parcel"
            or props.get("coordinates_level") == "parcel"):
        return "parcel_reference_requires_review"
    if props.get("match_level") not in HIGH_LEVELS:
        return "coarse_or_unknown_address_match"
    if props.get("coordinates_level") not in HIGH_LEVELS:
        return "coarse_or_unknown_coordinate_reference"
    if point is None:
        return "invalid_or_missing_point"
    if shared:
        return "shared_reference_coordinate_requires_review"
    return "high_resolution_reference_for_independent_review"


def diagnose_stage4(manifest: dict, resolution: dict, summary: dict,
                    stage1: dict, stage2: dict, stage3: dict,
                    dataset: dict, source_sha: str, server: str) -> dict:
    targets = check_snapshot(manifest, resolution, summary, dataset, source_sha)
    validate_stage1(stage1, resolution, source_sha, len(targets))
    validate_stage2(stage2, stage1, resolution, source_sha)
    validate_stage3(stage3, stage2, stage1, resolution, source_sha)
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

    stage1_counts = Counter()
    outcomes = Counter()
    chome_conversions = 0
    exact_without_unmatched = 0
    exact_rows = []
    for row in targets:
        uri = base + "/geocode?" + urlencode({
            "address": row["query_address"], "pref": "23",
            "limit": "2", "category": "all",
        })
        first, _ = fetch_json(opener, uri)
        second, _ = fetch_json(opener, uri)
        if comparable_response(first, version) != comparable_response(second, version):
            raise ValueError("ABR replay semantic drift")
        for replay in (first, second):
            result = classify(replay, row["query_address"], row["ward"])
            if result.get("status") != "UNRESOLVED" or result.get("reason") != TARGET_REASON:
                raise ValueError("Original unresolved classification changed")
        feature = first["features"][0]
        props = feature["properties"]
        category = triage_address_mismatch(
            row["query_address"], props["matched_address"], row["ward"],
        )
        stage1_counts[category] += 1
        if category != DIFFERENCE:
            continue
        relation, n = comparison_outcome(row["query_address"], props["matched_address"], row["ward"])
        outcomes[relation] += 1
        chome_conversions += n
        if relation == "exact_after_kanji_chome_only":
            if props.get("unmatched_address") in (None, []):
                exact_without_unmatched += 1
            exact_rows.append((props, valid_point(feature)))

    if {k: stage1_counts[k] for k in CATEGORIES} != stage1["categories"]:
        raise ValueError("Stage-1 category drift")
    if ({k: outcomes[k] for k in OUTCOMES} != stage3["comparison_outcomes"]
            or chome_conversions != stage3["chome_number_conversions_count"]
            or exact_without_unmatched != stage3["exact_normalized_matches_without_unmatched_field_count"]):
        raise ValueError("Stage-3 replay counts drift")

    # Check duplicate reference coordinates against BOTH screened records AND
    # the 7 original tentative records. Never write these coordinates anywhere.
    point_counts = Counter(point for _, point in exact_rows if point is not None)
    original = resolution["results"]
    for row in original:
        if row.get("status") in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW"):
            point = row.get("derived_geometry")
            if not isinstance(point, dict):
                raise ValueError("Original candidate geometry invalid")
            lat, lon = point.get("latitude"), point.get("longitude")
            if (type(lat) not in (float, int) or type(lon) not in (float, int)
                    or not math.isfinite(lat) or not math.isfinite(lon)
                    or not (-90 <= lat <= 90 and -180 <= lon <= 180)
                    or lat == 0 or lon == 0):
                raise ValueError("Original candidate geometry invalid")
            point_counts[(lon, lat)] += 1

    screens = Counter()
    for props, point in exact_rows:
        screens[screen_exact_reference(
            props, point, point is not None and point_counts[point] > 1,
        )] += 1
    exact_n = stage3["comparison_outcomes"]["exact_after_kanji_chome_only"]
    if sum(screens.values()) != exact_n:
        raise ValueError("Stage-4 counts incomplete")

    return {
        "report_kind": "NAGOYA_STAGE4_TEXT_EQUAL_ADDRESS_REFERENCE_SCREEN_ONLY",
        "source_dataset_sha256": source_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version["version"],
        "provider_db_version": version["db_version"],
        "original_mismatches_rechecked": len(targets),
        "orthographic_text_equal_rechecked": exact_n,
        "stage1_and_stage3_aggregate_counts_reproduced": True,
        "screen_categories": {k: screens[k] for k in OUTCOME_KEYS},
        "screening_rule": "Only full chome-normalized text match with no leftover tokens, high ABR match+coordinate levels, valid unique reference point; never a facility location acceptance",
        "source_suffix_cases_not_promoted": (
            stage1["categories"]["source_suffix_not_matched"]
            + stage3["comparison_outcomes"]["source_suffix_unmatched_after_kanji_chome"]
        ),
        "existing_unverified_candidates_unchanged": summary["unverified_candidate_count"],
        "original_pilot_unchanged": True,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "site_accuracy_independently_verified": False,
        "route_or_disaster_safety_verified": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--pilot-dir", type=Path, required=True)
    p.add_argument("--local-abr-url", default="http://127.0.0.1:3000")
    args = p.parse_args()
    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    root = args.pilot_dir.resolve()
    if root != allowed and allowed not in root.parents:
        p.error("Only a gitignored pilot directory is allowed")
    out = root / "chome_stage4_reference_screen_aggregate.json"
    if out.exists():
        p.error("Stage-4 report already exists; cannot overwrite")
    try:
        data, source_sha = read_dataset(args.dataset)
        inputs = {
            name: json.loads((root / name).read_text("utf-8"))
            for name in (
                "manifest.json", "resolution.json", "summary.json",
                "mismatch_diagnostics_aggregate.json", "text_difference_stage2_aggregate.json",
                "kanji_chome_stage3_aggregate.json",
            )
        }
        result = diagnose_stage4(
            inputs["manifest.json"], inputs["resolution.json"],
            inputs["summary.json"], inputs["mismatch_diagnostics_aggregate.json"],
            inputs["text_difference_stage2_aggregate.json"],
            inputs["kanji_chome_stage3_aggregate.json"],
            data, source_sha, args.local_abr_url,
        )
        save_new(out, result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Stage-4 aborted [" + safe_failure_code(exc) +
               "]; no new report written.\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
