"""C-only, offline consistency checks for fictional MVP scenario snapshots.

Not a D evaluator, official-source audit, device QA, or public safety approval.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import sys

SCHEMA_ID = "hinanex.c.mvp_synthetic_consistency.v0.1"
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "fixtures" / "mvp_synthetic_consistency_v01.json"
INPUT_KEYS = ("mode", "hazard", "region", "session_token", "fixture_id", "observed_at", "evaluated_at", "facts")
OUTPUT_KEYS = ("mode", "hazard", "region", "session_token", "fixture_id", "observed_at", "generated_at", "valid_until", "is_drill", "facts", "claims")
CLAIMS = ("facility_safety", "facility_open", "route_passability")
UNCONFIRMED = (None, "UNKNOWN", "UNVERIFIED")
STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")


def outcome(status: str, code: str) -> dict[str, str]:
    return {"status": status, "code": code}


def merge(base: dict, changes: dict) -> dict:
    """Overlay test-only snapshots without modifying the shared template."""
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp is not a string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp is missing timezone")
    return dt


def evaluate(input_snapshot: object, output_snapshot: object) -> dict[str, str]:
    """Evaluate fixture-local envelope consistency, never real-world suitability."""
    if not isinstance(input_snapshot, dict) or not isinstance(output_snapshot, dict):
        return outcome("BLOCKED", "MISSING_SNAPSHOT")
    if any(key not in input_snapshot or input_snapshot[key] is None for key in INPUT_KEYS):
        return outcome("BLOCKED", "MISSING_REQUIRED_FIELD")
    if any(key not in output_snapshot or output_snapshot[key] is None for key in OUTPUT_KEYS):
        return outcome("BLOCKED", "MISSING_REQUIRED_FIELD")
    if not isinstance(input_snapshot["facts"], dict) or not isinstance(output_snapshot["facts"], dict):
        return outcome("BLOCKED", "INVALID_FACTS")
    if not isinstance(output_snapshot["claims"], dict) or any(key not in output_snapshot["claims"] for key in CLAIMS):
        return outcome("BLOCKED", "MISSING_CLAIM")
    if set(output_snapshot["claims"]) != set(CLAIMS):
        return outcome("BLOCKED", "UNRECOGNIZED_CLAIM_FIELD")
    try:
        observed = timestamp(input_snapshot["observed_at"])
        evaluated = timestamp(input_snapshot["evaluated_at"])
        generated = timestamp(output_snapshot["generated_at"])
        valid_until = timestamp(output_snapshot["valid_until"])
        output_observed = timestamp(output_snapshot["observed_at"])
    except ValueError:
        return outcome("BLOCKED", "INVALID_TIMESTAMP")

    if input_snapshot["mode"] not in ("NORMAL", "DRILL"):
        return outcome("FAIL", "INVALID_MODE")
    if output_snapshot["mode"] != input_snapshot["mode"]:
        return outcome("FAIL", "MODE_MISMATCH")
    if type(output_snapshot["is_drill"]) is not bool or output_snapshot["is_drill"] != (input_snapshot["mode"] == "DRILL"):
        return outcome("FAIL", "MODE_TAG_MISMATCH")
    if output_snapshot["hazard"] != input_snapshot["hazard"]:
        return outcome("FAIL", "HAZARD_MISMATCH")
    if output_snapshot["region"] != input_snapshot["region"]:
        return outcome("FAIL", "REGION_MISMATCH")
    if any(output_snapshot[key] != input_snapshot[key] for key in ("session_token", "fixture_id")) or output_observed != observed:
        return outcome("FAIL", "STALE_CONTEXT")
    if generated < observed:
        return outcome("FAIL", "RESULT_PREDATES_OBSERVATION")
    if generated > evaluated:
        return outcome("FAIL", "FUTURE_GENERATED_RESULT")
    if valid_until < evaluated:
        return outcome("FAIL", "EXPIRED_RESULT")

    input_facts, output_facts = input_snapshot["facts"], output_snapshot["facts"]
    for key, value in input_facts.items():
        if key not in output_facts or output_facts[key] != value:
            if value is None or value == "UNKNOWN":
                return outcome("FAIL", "UNKNOWN_PROMOTED")
            return outcome("FAIL", "FACT_MISMATCH")
    for key, value in output_facts.items():
        if key not in input_facts and value not in UNCONFIRMED:
            return outcome("FAIL", "UNTRACEABLE_FACT")
    if any(output_snapshot["claims"][key] not in UNCONFIRMED for key in CLAIMS):
        return outcome("FAIL", "UNAPPROVED_CLAIM")
    return outcome("PASS", "CONSISTENT_SYNTHETIC")


def check_manifest(manifest: object) -> list[dict]:
    if not isinstance(manifest, dict) or manifest.get("schema_id") != SCHEMA_ID or manifest.get("synthetic_only") is not True:
        raise ValueError("invalid or non-synthetic manifest")
    template = manifest.get("template")
    cases = manifest.get("cases")
    if not isinstance(template, dict) or not isinstance(template.get("input"), dict) or not isinstance(template.get("output"), dict):
        raise ValueError("missing template snapshots")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a non-empty list")
    seen = set()
    rows = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise ValueError("invalid or duplicate case id")
        seen.add(case["id"])
        expected = case.get("expected")
        if not isinstance(expected, dict) or expected.get("status") not in STATUSES or not isinstance(expected.get("code"), str):
            raise ValueError(f"invalid expected outcome for {case['id']}")
        if type(case.get("run", True)) is not bool:
            raise ValueError(f"invalid run flag for {case['id']}")
        if not isinstance(case.get("input_delta", {}), dict) or not isinstance(case.get("output_delta", {}), dict):
            raise ValueError(f"invalid overrides for {case['id']}")
        if case.get("run", True):
            actual = evaluate(merge(template["input"], case.get("input_delta", {})),
                              merge(template["output"], case.get("output_delta", {})))
        else:
            actual = outcome("NOT_RUN", "EXPLICITLY_DISABLED")
        rows.append({"id": case["id"], "expected": expected, "actual": actual, "matches_expected": actual == expected})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline C-only synthetic MVP consistency regression")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args(argv)
    try:
        rows = check_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"MANIFEST_ERROR: {exc}", file=sys.stderr)
        return 2
    counts = {status: sum(row["actual"]["status"] == status for row in rows) for status in STATUSES}
    matched = all(row["matches_expected"] for row in rows)
    report = {"synthetic_only": True, "official_acceptance": False, "device_qa": "NOT_RUN",
              "counts": counts, "regression": "PASS" if matched else "FAIL", "cases": rows}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['id']}: {row['actual']['status']} / {row['actual']['code']} "
                  f"(expected={row['expected']['status']}/{row['expected']['code']}; "
                  f"regression={'PASS' if row['matches_expected'] else 'FAIL'})")
        print(f"Regression: {report['regression']}; verdict counts: {counts}; official acceptance: NO; device QA: NOT_RUN")
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
