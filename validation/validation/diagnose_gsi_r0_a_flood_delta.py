"""Focused C-only diagnostic of R0 A-flood source-byte mismatch.

Reads the original D R0 report/raw/receipt without modifying them, then makes
a *new* opt-in direct HTTPS GET for the EXACT A-flood tile 10/909/403.

Outputs only source hashes, byte/feature counts, and structural difference
indicators. No raw features, names, addresses, coordinates, or source bytes
are exported. This is NOT evidence of why a *prior* replay differed, and
never grants source authorization, site identity, or publication approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from verify_gsi_r0_four_cell_replay import (
    CBlocked, MAX_REPORT_BYTES, _load_json, _no_redirect_http,
    inspect_c_raw, validate_r0_report, verify_local_cell,
)

A_TILE = {"z": 10, "x": 909, "y": 403}
A_FLOOD_SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _typed_equal(a, b):
    """Conservatively compare JSON values, including numeric and bool types."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_typed_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_typed_equal(x, y) for x, y in zip(a, b))
    return a == b


# Fixed, publicly known schema labels only. Never reveal unknown source keys:
# a source property name could itself include a private value.
_SAFE_PROPERTIES = frozenset(("name", "address", "remarks", "disaster1", "disaster2"))
_SAFE_GEOMETRY = frozenset(("type", "coordinates"))
_MISSING = object()


def _changed_attribute_categories(old_feature: object, new_feature: object) -> set[str]:
    """List only allowlisted field *categories*, never keys from source data."""
    if not isinstance(old_feature, dict) or not isinstance(new_feature, dict):
        return {"feature.structure"}
    categories = set()
    for key in old_feature.keys() | new_feature.keys():
        previous = old_feature.get(key, _MISSING)
        current = new_feature.get(key, _MISSING)
        if _typed_equal(previous, current):
            continue
        if key in ("properties", "geometry"):
            if not isinstance(previous, dict) or not isinstance(current, dict):
                categories.add(f"{key}.structure")
                continue
            allowed = _SAFE_PROPERTIES if key == "properties" else _SAFE_GEOMETRY
            for subkey in previous.keys() | current.keys():
                if not _typed_equal(
                    previous.get(subkey, _MISSING), current.get(subkey, _MISSING)
                ):
                    safe_key = subkey if subkey in allowed else "other"
                    categories.add(f"{key}.{safe_key}")
        elif key == "type":
            categories.add("feature.type")
        elif key == "id":
            categories.add("feature.id")
        else:
            categories.add("feature.other")
    return categories


def _diff_summary(old_bytes: bytes, new_bytes: bytes) -> dict:
    """Aggregate per-index field categories; no source field values leave here."""
    old = _load_json(old_bytes)
    new = _load_json(new_bytes)
    a, b = old["features"], new["features"]
    differing = []
    categories: dict[str, int] = {}
    for index in range(max(len(a), len(b))):
        if index >= min(len(a), len(b)):
            labels = {"feature.added_or_removed"}
        elif _typed_equal(a[index], b[index]):
            continue
        else:
            labels = _changed_attribute_categories(a[index], b[index])
        differing.append(index)
        for label in labels:
            categories[label] = categories.get(label, 0) + 1
    # Order-independent, exact JSON-value multiset comparison. Canonicalized
    # strings are retained only in local memory; never emit feature fingerprints.
    # Duplicates must remain counted (a set would silently lose multiplicity).
    def canonical_features(rows):
        return Counter(
            json.dumps(feature, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False)
            for feature in rows
        )

    old_multiset = canonical_features(a)
    new_multiset = canonical_features(b)
    equal_multiset = old_multiset == new_multiset
    unmatched_d = sum((old_multiset - new_multiset).values())
    unmatched_c = sum((new_multiset - old_multiset).values())
    order_differs_with_same_content = (
        equal_multiset and not _typed_equal(a, b)
    )
    no_features_old = dict(old, features=None)
    no_features_new = dict(new, features=None)
    return {
        "parsed_json_typed_equal": _typed_equal(old, new),
        "non_feature_root_changed": not _typed_equal(no_features_old, no_features_new),
        "feature_count_delta_c_minus_d": len(b) - len(a),
        "feature_indices_differing_count": len(differing),
        "first_differing_feature_index": differing[0] if differing else None,
        "feature_multiset_canonical_json_equal": equal_multiset,
        "feature_multiset_d_only_occurrences": unmatched_d,
        "feature_multiset_c_only_occurrences": unmatched_c,
        "same_features_in_different_array_order": order_differs_with_same_content,
        "feature_multiset_comparison_scope": (
            "ORDER_INDEPENDENT_FULL_FEATURE_JSON_MULTISET_NO_SITE_IDENTITY_JOIN"
        ),
        "changed_attribute_category_counts": dict(sorted(categories.items())),
        "changed_attribute_category_scope": (
            "FIXED_ALLOWLIST_PER_ARRAY_INDEX_UNKNOWN_KEYS_REDACTED"
        ),
        "comparison_scope": "SAME_FEATURE_ARRAY_INDEX_NO_IDENTITY_JOIN",
    }


def diagnose_a_flood(
    d_report: dict,
    *,
    evidence_dir: Path,
    transport=_no_redirect_http,
    clock=lambda: datetime.now(timezone.utc),
    prior_c_sha256: str | None = None,
) -> dict:
    """One snapshot comparison. A prior unarchived C response cannot be diffed."""
    rows = validate_r0_report(d_report)
    if prior_c_sha256 is not None and (
        not isinstance(prior_c_sha256, str) or not _SHA256.fullmatch(prior_c_sha256)
    ):
        raise CBlocked("C_PRIOR_SHA256_INVALID")
    if (not isinstance(evidence_dir, Path) or not evidence_dir.is_absolute()
            or not evidence_dir.is_dir()):
        raise CBlocked("C_EVIDENCE_DIR_INVALID")
    root = evidence_dir.resolve(strict=True)
    if root.is_relative_to(Path(__file__).resolve().parents[2]):
        raise CBlocked("C_EVIDENCE_MUST_REMAIN_OUTSIDE_GIT")
    timestamp = clock()
    if (not isinstance(timestamp, datetime) or timestamp.tzinfo is None
            or timestamp.utcoffset() != timezone.utc.utcoffset(None)):
        raise CBlocked("C_CHECK_CLOCK_MUST_BE_UTC")

    a = next(row for row in rows if row["slot"] == "A" and row["hazard"] == "flood")
    if a["tile"] != A_TILE or a["source_url"] != A_FLOOD_SOURCE:
        raise CBlocked("C_FLOOD_TILE_SCOPE_MISMATCH")
    if a["capture_status"] != "RAW_CAPTURED_C_UNVERIFIED":
        raise CBlocked("C_A_FLOOD_LOCAL_SOURCE_NOT_CAPTURED")

    d_raw = verify_local_cell(a, evidence_dir=root, checked_at=timestamp)
    d_sha, d_count = inspect_c_raw(d_raw, hazard="flood", tile=A_TILE)
    replay_bytes, code, final_url = transport(A_FLOOD_SOURCE)
    if type(code) is not int or code != 200:
        raise CBlocked("C_A_FLOOD_HTTP_NOT_200")
    if final_url != A_FLOOD_SOURCE:
        raise CBlocked("C_A_FLOOD_REDIRECT_OR_FINAL_URL_MISMATCH")
    c_sha, c_count = inspect_c_raw(replay_bytes, hazard="flood", tile=A_TILE)
    equal = d_raw == replay_bytes

    summary = _diff_summary(d_raw, replay_bytes)
    return {
        "status": ("C_A_FLOOD_CURRENT_BYTE_MATCH_UNAPPROVED" if equal
                   else "C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD"),
        "checked_at_utc": timestamp.isoformat(timespec="seconds"),
        "source_url": A_FLOOD_SOURCE,
        "tile": A_TILE,
        "hazard": "flood",
        "previous_c_sha256_user_supplied": prior_c_sha256,
        "current_c_equals_previous_c_sha256": (
            c_sha == prior_c_sha256 if prior_c_sha256 is not None else None
        ),
        "d_archived_sha256": d_sha,
        "d_archived_bytes": len(d_raw),
        "d_archived_tile_feature_count": d_count,
        "c_new_https_sha256": c_sha,
        "c_new_https_bytes": len(replay_bytes),
        "c_new_https_tile_feature_count": c_count,
        "http_status": code,
        "response_final_url": final_url,
        "same_bytes": equal,
        **summary,
        "prior_c_https_raw_preserved": False,
        "cause_of_prior_mismatch": "UNDETERMINED",
        "c_independent_approved": False,
        "official_source_signed": False,
        "facility_identity_approved": False,
        "hazard_safety_verified": False,
        "publication_approved": False,
        "human_review": "DEFERRED_TO_HUMAN_BATCH_REVIEW",
        "note": (
            "Current HTTPS GET is an additional observation. A byte difference "
            "does not prove an official revision; JSON equality is a structural "
            "comparison, not facility identity. A newly matching byte hash does "
            "not retrospectively erase the earlier mismatch."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d-report", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--prior-c-sha256", help="Previously reported hash only; not raw evidence")
    parser.add_argument("--report-out", required=True, type=Path,
                        help="New JSON path outside Git. Refuses overwrite.")
    args = parser.parse_args()
    try:
        if (not args.d_report.is_file() or args.d_report.is_symlink()
                or args.d_report.stat().st_size > MAX_REPORT_BYTES):
            raise CBlocked("C_D_REPORT_INVALID")
        if (not args.report_out.is_absolute() or args.report_out.suffix != ".json"
                or args.report_out.is_symlink() or args.report_out.exists()
                or not args.report_out.parent.is_dir()
                or args.report_out.resolve(strict=False).is_relative_to(
                    Path(__file__).resolve().parents[2])):
            raise CBlocked("C_REPORT_OUTPUT_MUST_BE_NEW_OUTSIDE_GIT")
        report = _load_json(args.d_report.read_bytes())
        result = diagnose_a_flood(
            report, evidence_dir=args.evidence_dir,
            prior_c_sha256=args.prior_c_sha256,
        )
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        with args.report_out.open("x", encoding="utf-8") as file:
            file.write(output)
        print(output, end="")
        return 0 if result["same_bytes"] else 3
    except (CBlocked, OSError, ValueError, TypeError) as exc:
        print("C_A_FLOOD_DIAGNOSTIC_HOLD: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
