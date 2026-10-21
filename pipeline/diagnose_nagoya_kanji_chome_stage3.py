"""Stage-3 local experiment: bounded kanji-chome orthographic equivalence ONLY.

Reports anonymous COUNTS, never addresses, IDs, or coordinates. It does not
change the original 50 decisions and cannot approve inferred map positions.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

from diagnose_nagoya_address_mismatch import (
    CATEGORIES, TARGET_REASON, check_snapshot, comparable_response,
    safe_failure_code, triage_address_mismatch,
)
from diagnose_nagoya_text_difference_stage2 import (
    DIFFERENCE, MATCH_LEVELS, NUMBER_RELATIONS, NUMERIC_SUFFIX,
    numeric_observation, validate_stage1,
)
from geocode_nagoya_pilot import (
    CITY, BlockRedirects, address_key, classify, fetch_json, local_url,
    read_dataset, save_new,
)

# Strictly canonical Japanese numerals in the 1..100 chome range. No arbitrary
# kanji numeric replacement, fuzzy string matching, or missing-number filling.
CHOME_RE = re.compile(r"([一二三四五六七八九十百〇零]+)丁目")
DIGITS = "一二三四五六七八九"
OUTCOMES = (
    "exact_after_kanji_chome_only",
    "source_suffix_unmatched_after_kanji_chome",
    "provider_extra_suffix_after_kanji_chome",
    "still_different_after_kanji_chome",
    "unrecognized_kanji_chome",
)
KANJI_TO_INT = {}
for _n in range(1, 101):
    if _n == 100:
        _kanji = "百"
    elif _n < 10:
        _kanji = DIGITS[_n - 1]
    else:
        _tens, _ones = divmod(_n, 10)
        _kanji = ("十" if _tens == 1 else DIGITS[_tens - 1] + "十")
        if _ones:
            _kanji += DIGITS[_ones - 1]
    KANJI_TO_INT[_kanji] = _n


def canonical_chome_address(value: str) -> tuple[str, int, int]:
    """Return comparison key, #converted canonical chome, #unsupported tokens."""
    value = unicodedata.normalize("NFKC", value)
    converted = 0
    unsupported = 0

    def replace(match: re.Match) -> str:
        nonlocal converted, unsupported
        number = KANJI_TO_INT.get(match.group(1))
        if number is None:
            unsupported += 1
            return match.group(0)
        converted += 1
        return str(number) + "丁目"

    return address_key(CHOME_RE.sub(replace, value)), converted, unsupported


def comparison_outcome(query: str, matched: str, ward: str) -> tuple[str, int]:
    """String relation only. An 'exact' observation is not a verified location."""
    prefix = CITY + ward
    if not query.startswith(prefix) or not matched.startswith(prefix):
        raise ValueError("Stage-3 prefix mismatch")
    source, source_converted, source_unknown = canonical_chome_address(query)
    provider, provider_converted, provider_unknown = canonical_chome_address(matched)
    count = source_converted + provider_converted
    if source_unknown + provider_unknown:
        return "unrecognized_kanji_chome", count
    if count == 0:
        raise ValueError("Stage-3 no kanji chome observed")
    if source == provider:
        return "exact_after_kanji_chome_only", count
    if source.startswith(provider):
        return "source_suffix_unmatched_after_kanji_chome", count
    if provider.startswith(source):
        return "provider_extra_suffix_after_kanji_chome", count
    return "still_different_after_kanji_chome", count


def validate_stage2(stage2: dict, stage1: dict, resolution: dict,
                    dataset_sha: str) -> None:
    count = stage1["categories"][DIFFERENCE]
    expected = {
        "report_kind": "NAGOYA_CURRENT_TEXT_DIFFERENCE_STAGE2_AGGREGATE",
        "source_dataset_sha256": dataset_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": resolution["provider_version"],
        "provider_db_version": resolution["provider_db_version"],
        "original_mismatches_checked": stage1["diagnosed_count"],
        "stage2_target_count": count,
        "stage1_categories_reproduced": True,
        "original_pilot_unchanged": True,
        "site_accuracy_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }
    if any(stage2.get(k) != v for k, v in expected.items()):
        raise ValueError("Stage-2 snapshot invalid")
    for field, options in (
        ("numeric_observations", NUMBER_RELATIONS),
        ("numeric_suffix_observations", NUMERIC_SUFFIX),
        ("match_level_counts", MATCH_LEVELS),
        ("coordinate_level_counts", MATCH_LEVELS),
    ):
        counts = stage2.get(field)
        if (not isinstance(counts, dict) or set(counts) != set(options)
                or any(type(v) is not int or v < 0 for v in counts.values())
                or sum(counts.values()) != count):
            raise ValueError("Stage-2 count schema invalid")
    flags = stage2.get("orthographic_markers")
    if (not isinstance(flags, dict) or
            any(type(v) is not int or v < 0 or v > count for v in flags.values())):
        raise ValueError("Stage-2 marker schema invalid")
    if (type(stage2.get("provider_unmatched_nonempty_in_stage2_count")) is not int
            or not 0 <= stage2["provider_unmatched_nonempty_in_stage2_count"] <= count):
        raise ValueError("Stage-2 unmatched count invalid")


def diagnose_stage3(manifest: dict, resolution: dict, summary: dict,
                    stage1: dict, stage2: dict, dataset: dict,
                    dataset_sha: str, server: str) -> dict:
    targets = check_snapshot(manifest, resolution, summary, dataset, dataset_sha)
    validate_stage1(stage1, resolution, dataset_sha, len(targets))
    validate_stage2(stage2, stage1, resolution, dataset_sha)
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

    categories = Counter()
    number_relations = Counter()
    number_suffixes = Counter()
    match_levels = Counter()
    coordinate_levels = Counter()
    flags = Counter()
    nonempty_unmatched = 0
    outcomes = Counter()
    matched_without_unmatched = 0
    conversion_total = 0

    for row in targets:
        uri = base + "/geocode?" + urlencode({
            "address": row["query_address"], "pref": "23",
            "limit": "2", "category": "all",
        })
        first, _ = fetch_json(opener, uri)
        second, _ = fetch_json(opener, uri)
        if comparable_response(first, version) != comparable_response(second, version):
            raise ValueError("ABR replay semantic drift")
        for payload in (first, second):
            status = classify(payload, row["query_address"], row["ward"])
            if status.get("status") != "UNRESOLVED" or status.get("reason") != TARGET_REASON:
                raise ValueError("Original unresolved classification changed")
        props = first["features"][0]["properties"]
        matched = props["matched_address"]
        category = triage_address_mismatch(row["query_address"], matched, row["ward"])
        categories[category] += 1
        if category != DIFFERENCE:
            continue
        rel, suffix, marks = numeric_observation(row["query_address"], matched, row["ward"])
        number_relations[rel] += 1
        number_suffixes[suffix] += 1
        flags.update({name: 1 for name, present in marks.items() if present})
        for v, bucket in ((props.get("match_level"), match_levels),
                          (props.get("coordinates_level"), coordinate_levels)):
            bucket[v if v in MATCH_LEVELS[:-1] else "other_or_missing"] += 1
        unmatched = props.get("unmatched_address")
        if unmatched not in (None, []):
            nonempty_unmatched += 1
        outcome, conversions = comparison_outcome(row["query_address"], matched, row["ward"])
        outcomes[outcome] += 1
        conversion_total += conversions
        if outcome == "exact_after_kanji_chome_only" and unmatched in (None, []):
            matched_without_unmatched += 1

    if {k: categories[k] for k in CATEGORIES} != stage1["categories"]:
        raise ValueError("Stage-1 category drift")
    for actual, expected, keys in (
        (number_relations, stage2["numeric_observations"], NUMBER_RELATIONS),
        (number_suffixes, stage2["numeric_suffix_observations"], NUMERIC_SUFFIX),
        (match_levels, stage2["match_level_counts"], MATCH_LEVELS),
        (coordinate_levels, stage2["coordinate_level_counts"], MATCH_LEVELS),
    ):
        if {k: actual[k] for k in keys} != expected:
            raise ValueError("Stage-2 replay counts drift")
    if (dict(sorted(flags.items())) != stage2["orthographic_markers"]
            or nonempty_unmatched != stage2["provider_unmatched_nonempty_in_stage2_count"]):
        raise ValueError("Stage-2 replay counts drift")
    count = stage2["stage2_target_count"]
    if sum(outcomes.values()) != count:
        raise ValueError("Stage-3 incomplete counts")
    return {
        "report_kind": "NAGOYA_CHOME_ONLY_STAGE3_ORTHOGRAPHIC_DIAGNOSTIC",
        "source_dataset_sha256": dataset_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version["version"],
        "provider_db_version": version["db_version"],
        "original_mismatches_rechecked": len(targets),
        "stage2_target_count": count,
        "stage1_and_stage2_categories_reproduced": True,
        "normalization_scope": "Canonical kanji numeral 1..100 immediately before 丁目; all other text unchanged beyond existing address_key",
        "comparison_outcomes": {k: outcomes[k] for k in OUTCOMES},
        "chome_number_conversions_count": conversion_total,
        "exact_normalized_matches_without_unmatched_field_count": matched_without_unmatched,
        "original_response_semantic_equivalence_proven": False,
        "text_equivalence_is_not_facility_location_verification": True,
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

    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != root and root not in folder.parents:
        p.error("Only a gitignored pilot directory is allowed")
    output = folder / "kanji_chome_stage3_aggregate.json"
    if output.exists():
        p.error("Existing Stage-3 output cannot be overwritten")
    try:
        dataset, source_hash = read_dataset(args.dataset)
        manifest = json.loads((folder / "manifest.json").read_text("utf-8"))
        resolution = json.loads((folder / "resolution.json").read_text("utf-8"))
        summary = json.loads((folder / "summary.json").read_text("utf-8"))
        stage1 = json.loads((folder / "mismatch_diagnostics_aggregate.json").read_text("utf-8"))
        stage2 = json.loads((folder / "text_difference_stage2_aggregate.json").read_text("utf-8"))
        result = diagnose_stage3(
            manifest, resolution, summary, stage1, stage2,
            dataset, source_hash, args.local_abr_url,
        )
        save_new(output, result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Stage-3 aborted [" + safe_failure_code(exc) +
               "]; no new report was written.\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
