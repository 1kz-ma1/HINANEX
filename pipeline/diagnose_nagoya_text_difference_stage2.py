"""Stage-2, opt-in and aggregate-only Nagoya address text-difference diagnostic.

Checks immutable local pilot files and the prior aggregate report; independently
replays original mismatches twice against the same localhost ABR configuration.
Nothing here can approve or publish a coordinate or change the initial pilot.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

from diagnose_nagoya_address_mismatch import (
    CATEGORIES, TARGET_REASON, check_snapshot, comparable_response,
    safe_failure_code, triage_address_mismatch,
)
from geocode_nagoya_pilot import (
    CITY, BlockRedirects, address_key, classify, fetch_json, local_url,
    read_dataset, save_new,
)

DIFFERENCE = "town_or_other_text_difference"
MATCH_LEVELS = (
    "pref", "city", "machiaza", "machiaza_detail",
    "rsdtdsp_blk", "rsdtdsp_rsdt", "parcel", "unknown",
    "other_or_missing",
)
NUMBER_RELATIONS = (
    "both_have_numbers_text_stem_diff",
    "source_only_has_no_ascii_number",
    "provider_only_has_no_ascii_number",
    "neither_has_ascii_number",
)
NUMERIC_SUFFIX = ("same", "different", "not_comparable")
KANJI_CHOME = re.compile(r"[一二三四五六七八九十〇零]+丁目")
DIGIT = re.compile(r"\d")


def numeric_observation(query: str, matched: str, ward: str) -> tuple[str, str, dict]:
    """Measure string features after the verified city+ward prefix only."""
    prefix = CITY + ward
    if not query.startswith(prefix) or not matched.startswith(prefix):
        raise ValueError("Stage-2 prefix mismatch")
    source = address_key(query[len(prefix):])
    provider = address_key(matched[len(prefix):])
    a, b = DIGIT.search(source), DIGIT.search(provider)
    if a is None and b is None:
        relation, suffix = "neither_has_ascii_number", "not_comparable"
    elif a is None:
        relation, suffix = "source_only_has_no_ascii_number", "not_comparable"
    elif b is None:
        relation, suffix = "provider_only_has_no_ascii_number", "not_comparable"
    else:
        if source[:a.start()] == provider[:b.start()]:
            raise ValueError("Stage-2 unexpected same numeric stem")
        relation = "both_have_numbers_text_stem_diff"
        suffix = "same" if source[a.start():] == provider[b.start():] else "different"
    patterns = {
        "source_has_kanji_chome": bool(KANJI_CHOME.search(source)),
        "provider_has_kanji_chome": bool(KANJI_CHOME.search(provider)),
        "source_contains_oaza_marker": "大字" in source,
        "provider_contains_oaza_marker": "大字" in provider,
        "source_contains_aza_marker": "字" in source,
        "provider_contains_aza_marker": "字" in provider,
    }
    return relation, suffix, patterns


def validate_stage1(stage1: dict, resolution: dict, dataset_sha: str,
                    target_count: int) -> None:
    if (stage1.get("report_kind") !=
            "NAGOYA_CURRENT_REPLAY_MISMATCH_TRIAGE_NOT_HISTORICAL_PROOF"
            or stage1.get("source_dataset_sha256") != dataset_sha
            or stage1.get("provider") != resolution.get("provider")
            or stage1.get("provider_version") != resolution.get("provider_version")
            or stage1.get("provider_db_version") != resolution.get("provider_db_version")
            or stage1.get("diagnosed_count") != target_count
            or stage1.get("replay_nonvolatile_semantics_agreed_count") != target_count
            or stage1.get("original_unresolved_reason") != TARGET_REASON
            or stage1.get("previous_statuses_unchanged") is not True
            or stage1.get("historical_semantic_equivalence_proven_for_changed_hashes") is not False
            or stage1.get("approved_for_map") is not False
            or stage1.get("data_promotion_authorized") is not False
            or stage1.get("site_accuracy_independently_verified") is not False):
        raise ValueError("Stage-1 snapshot invalid")
    counts = stage1.get("categories")
    if (not isinstance(counts, dict) or set(counts) != set(CATEGORIES)
            or any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                   for v in counts.values())
            or sum(counts.values()) != target_count or counts[DIFFERENCE] <= 0):
        raise ValueError("Stage-1 counts invalid")


def diagnose_stage2(manifest: dict, resolution: dict, summary: dict,
                    stage1: dict, dataset: dict, dataset_sha: str,
                    server: str) -> dict:
    targets = check_snapshot(manifest, resolution, summary, dataset, dataset_sha)
    validate_stage1(stage1, resolution, dataset_sha, len(targets))
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

    overall_categories = Counter()
    numeric_relations = Counter()
    numeric_suffix = Counter()
    match_levels = Counter()
    coordinate_levels = Counter()
    markers = Counter()
    unmatched_nonempty = 0
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
            classified = classify(replay, row["query_address"], row["ward"])
            if (classified.get("status") != "UNRESOLVED"
                    or classified.get("reason") != TARGET_REASON):
                raise ValueError("Original unresolved classification changed")
        props = first["features"][0]["properties"]
        category = triage_address_mismatch(
            row["query_address"], props["matched_address"], row["ward"],
        )
        overall_categories[category] += 1
        if category != DIFFERENCE:
            continue

        relation, suffix, flags = numeric_observation(
            row["query_address"], props["matched_address"], row["ward"],
        )
        numeric_relations[relation] += 1
        numeric_suffix[suffix] += 1
        for key, present in flags.items():
            if present:
                markers[key] += 1
        match_level = props.get("match_level")
        match_levels[match_level if match_level in MATCH_LEVELS[:-1]
                     else "other_or_missing"] += 1
        coordinate_level = props.get("coordinates_level")
        coordinate_levels[coordinate_level if coordinate_level in MATCH_LEVELS[:-1]
                          else "other_or_missing"] += 1
        unmatched = props.get("unmatched_address")
        if unmatched not in (None, []):
            unmatched_nonempty += 1

    if {category: overall_categories[category] for category in CATEGORIES} != stage1["categories"]:
        raise ValueError("Stage-1 category drift")
    n = stage1["categories"][DIFFERENCE]
    if sum(numeric_relations.values()) != n or sum(numeric_suffix.values()) != n:
        raise ValueError("Stage-2 incomplete counts")

    return {
        "report_kind": "NAGOYA_CURRENT_TEXT_DIFFERENCE_STAGE2_AGGREGATE",
        "source_dataset_sha256": dataset_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version["version"],
        "provider_db_version": version["db_version"],
        "original_mismatches_checked": len(targets),
        "stage1_categories_reproduced": True,
        "stage2_target_count": n,
        "numeric_observations": {k: numeric_relations[k] for k in NUMBER_RELATIONS},
        "numeric_suffix_observations": {k: numeric_suffix[k] for k in NUMERIC_SUFFIX},
        "match_level_counts": {k: match_levels[k] for k in MATCH_LEVELS},
        "coordinate_level_counts": {k: coordinate_levels[k] for k in MATCH_LEVELS},
        "provider_unmatched_nonempty_in_stage2_count": unmatched_nonempty,
        "orthographic_markers": dict(sorted(markers.items())),
        "interpretation": "String patterns and ABR levels only; no proof of address equivalence, facility identity, or point accuracy",
        "original_pilot_unchanged": True,
        "site_accuracy_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--pilot-dir", required=True, type=Path)
    parser.add_argument("--local-abr-url", default="http://127.0.0.1:3000")
    args = parser.parse_args()

    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    root = args.pilot_dir.resolve()
    if root != allowed and allowed not in root.parents:
        parser.error("Only a gitignored pilot directory is allowed")
    output = root / "text_difference_stage2_aggregate.json"
    if output.exists():
        parser.error("Stage-2 report already exists; overwriting is forbidden")

    try:
        dataset, dataset_sha = read_dataset(args.dataset)
        manifest = json.loads((root / "manifest.json").read_text("utf-8"))
        resolution = json.loads((root / "resolution.json").read_text("utf-8"))
        summary = json.loads((root / "summary.json").read_text("utf-8"))
        stage1 = json.loads((root / "mismatch_diagnostics_aggregate.json").read_text("utf-8"))
        result = diagnose_stage2(
            manifest, resolution, summary, stage1, dataset, dataset_sha,
            args.local_abr_url,
        )
        save_new(output, result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, "Stage-2 aborted [" + safe_failure_code(exc) +
                    "]; no new report was written.\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
