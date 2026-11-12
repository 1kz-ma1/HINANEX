"""Aggregate-only follow-up for mismatched addresses in a completed Nagoya ABR pilot.

Runs only against the same localhost ABR snapshot. Neither facility identities
nor original/matched addresses nor tentative coordinates are written or printed.
Does NOT change the geocoding outcome, GIS, or official positions.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

from geocode_nagoya_pilot import (
    CITY, BlockRedirects, address_key, classify, digest, fetch_json,
    local_url, prepare, read_dataset, save_new,
)
from report_nagoya_geocoding_pilot import audit

TARGET_REASON = "different_street_or_house_number"
CATEGORIES = (
    "source_suffix_not_matched",
    "provider_has_extra_suffix",
    "same_text_stem_number_difference",
    "town_or_other_text_difference",
)



# Deliberately constant diagnostics: never echo exception text containing source
# addresses, selected IDs, query URLs, or provider response payloads.
SAFE_FAILURE_CODES = {
    "Untrusted pilot manifest": "MANIFEST_INVALID",
    "Selection/source mismatch": "SELECTION_SOURCE_MISMATCH",
    "Pilot report snapshot mismatch": "REPORT_SNAPSHOT_MISMATCH",
    "Unexpected provider": "PROVIDER_MISMATCH",
    "Unapproved and versioned report required": "APPROVAL_OR_VERSION_INVALID",
    "Mismatch counts differ": "TARGET_COUNT_MISMATCH",
    "No matching unresolved rows to diagnose": "NO_TARGET_ROWS",
    "Missing original response hashes": "ORIGINAL_HASHES_MISSING",
    "ABR health not OK": "ABR_HEALTH_INVALID",
    "Local ABR version/pref/category changed": "ABR_CONFIGURATION_CHANGED",
    "ABR response changed since the original pilot": "ABR_RESPONSE_HASH_CHANGED",
    "ABR replay metadata invalid": "ABR_REPLAY_METADATA_INVALID",
    "ABR replay semantic drift": "ABR_REPLAY_SEMANTIC_DRIFT",
    "Original unresolved classification changed": "ORIGINAL_CLASSIFICATION_CHANGED",
    "Untrusted provider address": "PROVIDER_ADDRESS_INVALID",
    "Previously mismatched address now matches": "PREVIOUS_MISMATCH_NOW_MATCHES",
    "Diagnostic counts incomplete": "DIAGNOSTIC_COUNT_INCOMPLETE",
}


def safe_failure_code(exc: Exception) -> str:
    """Only emit predeclared diagnostic codes, never raw exception messages."""
    return SAFE_FAILURE_CODES.get(str(exc), type(exc).__name__.upper())

def triage_address_mismatch(query: str, matched: str, ward: str) -> str:
    """Describe string-level difference, NOT its underlying real-world cause."""
    if not isinstance(matched, str) or not matched.startswith(CITY + ward):
        raise ValueError("Untrusted provider address")
    source_key = address_key(query)
    matched_key = address_key(matched)
    if source_key == matched_key:
        raise ValueError("Previously mismatched address now matches")
    if source_key.startswith(matched_key):
        return "source_suffix_not_matched"
    if matched_key.startswith(source_key):
        return "provider_has_extra_suffix"
    source_digit = re.search(r"\d", source_key)
    matched_digit = re.search(r"\d", matched_key)
    if (source_digit and matched_digit
            and source_key[:source_digit.start()] == matched_key[:matched_digit.start()]):
        return "same_text_stem_number_difference"
    return "town_or_other_text_difference"


def check_snapshot(manifest: dict, resolution: dict, summary: dict,
                   dataset: dict, dataset_sha: str) -> list[dict]:
    """Verify immutable selected identities, outcome, and source before HTTP."""
    if (manifest.get("pilot_version") != 1
            or manifest.get("source_dataset_sha256") != dataset_sha
            or manifest.get("approved_for_map") is not False):
        raise ValueError("Untrusted pilot manifest")
    expected = prepare(dataset, dataset_sha, manifest.get("max_sample"))
    for field in ("selected", "skipped", "source_record_count", "region_code"):
        if manifest.get(field) != expected[field]:
            raise ValueError("Selection/source mismatch")

    audited, _ = audit(manifest, resolution)
    for field in (
        "sample_total", "statuses", "reasons", "source_dataset_sha256",
        "provider_version", "provider_db_version",
    ):
        if summary.get(field) != audited[field]:
            raise ValueError("Pilot report snapshot mismatch")
    if resolution.get("provider") != "DIGITAL_AGENCY_ABR":
        raise ValueError("Unexpected provider")
    if (not resolution.get("provider_version") or
            not resolution.get("provider_db_version") or
            summary.get("approved_for_map") is not False or
            summary.get("data_promotion_authorized") is not False):
        raise ValueError("Unapproved and versioned report required")

    targets = [row for row in resolution["results"]
               if row["status"] == "UNRESOLVED" and row.get("reason") == TARGET_REASON]
    if len(targets) != summary.get("reasons", {}).get(TARGET_REASON, 0):
        raise ValueError("Mismatch counts differ")
    if not targets:
        raise ValueError("No matching unresolved rows to diagnose")
    if any(not isinstance(row.get("provider_response_sha256"), str)
           or len(row["provider_response_sha256"]) != 64 for row in targets):
        raise ValueError("Missing original response hashes")
    return targets



def comparable_response(payload: object, version: dict) -> str:
    """Return canonical JSON excluding ONLY ABR's per-request duration_ms.

    Exact original payloads were not retained by the old pilot, so this
    establishes consistency across fresh requests, not historical identity.
    """
    if not isinstance(payload, dict):
        raise ValueError("ABR replay metadata invalid")
    info = payload.get("result_info")
    expected = {
        "api_version": version["version"],
        "db_version": version["db_version"],
        "enabled_category": "all",
        "enabled_pref": "23",
    }
    if not isinstance(info, dict) or any(info.get(k) != v for k, v in expected.items()):
        raise ValueError("ABR replay metadata invalid")
    if (not isinstance(info.get("count"), int) or isinstance(info["count"], bool)
            or not isinstance(payload.get("features"), list)
            or info["count"] != len(payload["features"])
            or info.get("limit") != 2):
        raise ValueError("ABR replay metadata invalid")
    duration = info.get("duration_ms")
    if duration is not None and (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0):
        raise ValueError("ABR replay metadata invalid")
    without_duration = {
        **payload,
        "result_info": {k: v for k, v in info.items() if k != "duration_ms"},
    }
    try:
        return json.dumps(
            without_duration, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError("ABR replay metadata invalid") from exc


def diagnose(manifest: dict, resolution: dict, summary: dict,
             dataset: dict, dataset_sha: str, server: str) -> dict:
    targets = check_snapshot(manifest, resolution, summary, dataset, dataset_sha)
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
    unmatched_field_count = 0
    original_raw_hash_drift_count = 0
    for row in targets:
        uri = base + "/geocode?" + urlencode({
            "address": row["query_address"], "pref": "23",
            "limit": "2", "category": "all",
        })
        # Re-run each request independently. The original response was not
        # retained; the old byte SHA256 is still counted as provenance, but
        # cannot establish that a mismatched historical payload is equivalent.
        payload, raw = fetch_json(opener, uri)
        second, second_raw = fetch_json(opener, uri)
        if digest(raw) != row["provider_response_sha256"]:
            original_raw_hash_drift_count += 1
        if comparable_response(payload, version) != comparable_response(second, version):
            raise ValueError("ABR replay semantic drift")
        for replay in (payload, second):
            classified = classify(replay, row["query_address"], row["ward"])
            if (classified["status"] != "UNRESOLVED"
                    or classified["reason"] != TARGET_REASON):
                raise ValueError("Original unresolved classification changed")
        # The strict classifier has checked the envelope and structured ward.
        props = payload["features"][0]["properties"]
        categories[triage_address_mismatch(
            row["query_address"], props["matched_address"], row["ward"],
        )] += 1
        if props.get("unmatched_address") not in (None, []):
            unmatched_field_count += 1

    if sum(categories.values()) != len(targets):
        raise ValueError("Diagnostic counts incomplete")
    return {
        "report_kind": "NAGOYA_CURRENT_REPLAY_MISMATCH_TRIAGE_NOT_HISTORICAL_PROOF",
        "source_dataset_sha256": dataset_sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version["version"],
        "provider_db_version": version["db_version"],
        "diagnosed_count": len(targets),
        "replay_nonvolatile_semantics_agreed_count": len(targets),
        "original_raw_response_hash_changed_count": original_raw_hash_drift_count,
        "original_raw_response_hash_equal_count": len(targets) - original_raw_hash_drift_count,
        "historical_semantic_equivalence_proven_for_changed_hashes": False,
        "original_unresolved_reason": TARGET_REASON,
        "categories": {category: categories[category] for category in CATEGORIES},
        "provider_unmatched_field_nonempty_count": unmatched_field_count,
        "interpretation": "Current replay string-pattern diagnosis only; historical bytes with different hashes cannot be proven semantically equivalent because original JSON was not archived",
        "previous_statuses_unchanged": True,
        "site_accuracy_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--local-abr-url", default="http://127.0.0.1:3000")
    args = parser.parse_args()

    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    pilot_dir = args.pilot_dir.resolve()
    if pilot_dir != root and root not in pilot_dir.parents:
        parser.error("Output must remain in gitignored data/geocoding_pilot")
    output = pilot_dir / "mismatch_diagnostics_aggregate.json"
    if output.exists():
        parser.error("Diagnostic already exists; no overwrite")

    try:
        dataset, dataset_sha = read_dataset(args.dataset)
        manifest = json.loads((pilot_dir / "manifest.json").read_text("utf-8"))
        resolution = json.loads((pilot_dir / "resolution.json").read_text("utf-8"))
        summary = json.loads((pilot_dir / "summary.json").read_text("utf-8"))
        result = diagnose(
            manifest, resolution, summary, dataset, dataset_sha, args.local_abr_url,
        )
        save_new(output, result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, "Diagnostic aborted [" + safe_failure_code(exc) +
                    "]; no new report was written.\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
