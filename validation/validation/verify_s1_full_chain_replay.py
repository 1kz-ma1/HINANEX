"""C-only integrated S0 -> S1-P0 -> P1 -> P2 replay over real D code.

Fixed invented inputs and independent expected outputs. Neither a D adapter nor
a B display/API. No live/official sources, filesystem writes or user data.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
D_ROOT = ROOT / "pipeline"
if str(D_ROOT) not in sys.path:
    sys.path.insert(0, str(D_ROOT))
DEFAULT_MANIFEST = ROOT / "validation" / "fixtures" / "s1_full_chain_c_replay_v01.json"

from src.hinanex.drill_session import (
    Action, DRILL_NOTICE, Event, Mode, NORMAL_NOTICE, SYNTHETIC_ONLY,
    Session, StaleSessionError, SyntheticFixture, reduce_session, safe_view,
)
from src.hinanex.s1_synthetic_narrowing import (
    NarrowRequest, SyntheticReference, narrow_synthetic_references,
)
from src.hinanex.s1_synthetic_comparison import compare_synthetic_conditions
from src.hinanex.s1_synthetic_review_choice import (
    ExplicitReviewChoice, choose_synthetic_for_review,
)

MANIFEST_ID = "hinanex.c.s1_full_chain_real_output_replay.v0.1"
REPORT_STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
SAFE_FLAGS = (
    "official_acceptance", "live_data_verified", "facility_safety_verified",
    "route_safety_verified", "release_approved",
)
EXPECTED_KEYS = frozenset((
    "transition", "mode", "generation", "selected_region", "fixture_id",
    "notice_kind", "live_data_verified", "narrow_status", "narrow_reason",
    "matched_ids", "row_statuses", "comparison_status", "comparison_reason",
    "totals", "choice_status", "choice_reason", "chosen_id",
    "choice_classification", "choice_missing", "choice_failed", "choice_checks",
))


def moment(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("a timezone-bearing timestamp string is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp missing an explicit timezone")
    return parsed


def build_fixture(raw: dict) -> SyntheticFixture:
    if not isinstance(raw, dict) or set(raw) != {
        "fixture_id", "region_code", "hazard", "observed_at", "expires_at",
        "source_authorization",
    }:
        raise ValueError("invalid synthetic fixture shape")
    return SyntheticFixture(
        fixture_id=raw["fixture_id"], region_code=raw["region_code"],
        hazard=raw["hazard"], observed_at=moment(raw["observed_at"]),
        expires_at=moment(raw["expires_at"]),
        source_authorization=raw["source_authorization"],
    )


def build_records(raw: list, fixture: SyntheticFixture) -> tuple[SyntheticReference, ...]:
    if not isinstance(raw, list):
        raise ValueError("records must be a list")
    records = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {
            "record_id", "fixture_id", "region_code", "hazard",
            "observed_at", "expires_at", "conditions",
        }:
            raise ValueError("invalid record fields")
        conditions = item["conditions"]
        if not isinstance(conditions, dict):
            raise ValueError("synthetic record conditions must be named")
        records.append(SyntheticReference(
            record_id=item["record_id"], fixture_id=item["fixture_id"],
            region_code=item["region_code"], hazard=item["hazard"],
            observed_at=moment(item["observed_at"]),
            expires_at=moment(item["expires_at"]),
            conditions=tuple(conditions.items()),
            source_authorization=SYNTHETIC_ONLY,
        ))
    if len(set(record.record_id for record in records)) != len(records):
        raise ValueError("duplicate synthetic record ID")
    return tuple(records)


def _safe_view_check(state: Session, now: datetime) -> tuple[dict, str | None]:
    v = safe_view(state, now)
    view = {
        "mode": v.mode.value, "generation": v.generation,
        "selected_region": v.selected_region, "fixture_id": v.fixture_id,
        "notice_kind": (
            "DRILL" if v.notice == DRILL_NOTICE else
            "NORMAL" if v.notice == NORMAL_NOTICE else "UNKNOWN"
        ),
        "live_data_verified": v.live_data_verified,
    }
    if v.live_data_verified is not False:
        return view, "LIVE_SAFETY_ASSERTION"
    if v.mode == Mode.NORMAL:
        if (v.fixture_id is not None or v.hazard is not None
                or v.source_authorization is not None or v.notice != NORMAL_NOTICE):
            return view, "NORMAL_EXPOSED_DRILL"
    elif v.mode == Mode.DRILL:
        f = state.fixture
        if (f is None or v.notice != DRILL_NOTICE or
                f.source_authorization != SYNTHETIC_ONLY or
                v.source_authorization != SYNTHETIC_ONLY or
                v.fixture_id != f.fixture_id or
                v.hazard != f.hazard or
                v.selected_region != f.region_code or
                not f.observed_at <= now < f.expires_at):
            return view, "UNTRACEABLE_SYNTHETIC_DRILL"
    else:
        return view, "UNKNOWN_S0_MODE"
    return view, None


def _flags_check(*outputs: object) -> bool:
    return all(
        getattr(output, "synthetic_only", None) is True
        and all(getattr(output, field, None) is False for field in SAFE_FLAGS)
        for output in outputs
    )


def _invariant(narrow, comparison, choice) -> str | None:
    if not _flags_check(narrow, comparison, choice) or choice.review_only is not True:
        return "REAL_WORLD_APPROVAL_LEAK"
    if narrow.status == "BLOCKED":
        if (narrow.decisions or narrow.matched_synthetic_ids or
                comparison.status != "BLOCKED" or comparison.rows or
                comparison.required_conditions or comparison.expires_at is not None or
                (comparison.totals.matched_synthetic != 0 or
                 comparison.totals.not_matched_synthetic != 0 or
                 comparison.totals.unknown != 0) or
                choice.status != "BLOCKED" or choice.selected_record_id is not None or
                choice.checks or choice.missing or choice.failed):
            return "BLOCKED_STATE_LEAK"
        return None
    if narrow.status != "EVALUATED_SYNTHETIC_ONLY" or comparison.status != narrow.status:
        return "UNSUPPORTED_EVALUATION"
    if (len(narrow.decisions) != len(comparison.rows)
            or tuple(x.record_id for x in narrow.decisions) != tuple(x.record_id for x in comparison.rows)):
        return "COMPARISON_ROW_PROVENANCE_MISMATCH"
    if tuple((x.status, x.reason_code, x.missing, x.failed) for x in narrow.decisions) != tuple(
        (x.status, x.reason_code, x.missing, x.failed) for x in comparison.rows
    ):
        return "COMPARISON_STATUS_CHANGED"
    if tuple(x.record_id for x in comparison.rows if x.status == "MATCHED_SYNTHETIC") != narrow.matched_synthetic_ids:
        return "MATCH_SET_MISMATCH"
    statuses = [row.status for row in comparison.rows]
    if (comparison.totals.matched_synthetic != statuses.count("MATCHED_SYNTHETIC")
            or comparison.totals.not_matched_synthetic != statuses.count("NOT_MATCHED_SYNTHETIC")
            or comparison.totals.unknown != statuses.count("UNKNOWN")
            or len(statuses) != sum((
                comparison.totals.matched_synthetic, comparison.totals.not_matched_synthetic,
                comparison.totals.unknown,
            ))):
        return "MISLEADING_COMPARISON_TOTALS"
    if choice.status == "BLOCKED":
        if (choice.selected_record_id is not None or choice.comparison_status is not None
                or choice.comparison_reason_code is not None or
                choice.checks or choice.missing or choice.failed):
            return "BLOCKED_CHOICE_LEAK"
    elif choice.status == "REVIEW_SELECTED_SYNTHETIC_ONLY":
        chosen = next((row for row in comparison.rows if row.record_id == choice.selected_record_id), None)
        if (chosen is None or choice.comparison_status != chosen.status
                or choice.comparison_reason_code != chosen.reason_code or
                choice.checks != chosen.checks or choice.missing != chosen.missing
                or choice.failed != chosen.failed
                or any(check.assessment == "NOT_EVALUATED" for check in chosen.checks)):
            return "CHOICE_PROMOTED_OR_FORGED"
    else:
        return "UNEXPECTED_CHOICE_RESULT"
    return None


def _actual_check(state: Session, step: dict, records: tuple[SyntheticReference, ...],
                  now: datetime) -> tuple[dict, str | None]:
    current, view_error = _safe_view_check(state, now)
    if view_error:
        return current, view_error
    request = NarrowRequest(
        expected_generation=step["request_generation"],
        region_code=step["request_region"],
        hazard=step["request_hazard"],
        required_conditions=tuple(step["required_conditions"]),
    )
    choice_request = ExplicitReviewChoice(
        selected_record_id=step["select_id"],
        expected_generation=step["choice_generation"],
        explicit_user_action=step["explicit_user_action"],
    )
    # Invoke each real D component independently; do not trust the earlier
    # component's output as the oracle for a later component.
    narrow = narrow_synthetic_references(state, request, records, now)
    compare = compare_synthetic_conditions(state, request, records, now)
    choice = choose_synthetic_for_review(state, request, records, choice_request, now)
    invariant_error = _invariant(narrow, compare, choice)
    actual = {
        **current,
        "narrow_status": narrow.status, "narrow_reason": narrow.reason_code,
        "matched_ids": list(narrow.matched_synthetic_ids),
        "row_statuses": [row.status for row in compare.rows],
        "comparison_status": compare.status, "comparison_reason": compare.reason_code,
        "totals": {
            "matched_synthetic": compare.totals.matched_synthetic,
            "not_matched_synthetic": compare.totals.not_matched_synthetic,
            "unknown": compare.totals.unknown,
        },
        "choice_status": choice.status, "choice_reason": choice.reason_code,
        "chosen_id": choice.selected_record_id,
        "choice_classification": choice.comparison_status,
        "choice_missing": list(choice.missing),
        "choice_failed": list(choice.failed),
        "choice_checks": [
            {"condition": check.condition, "assessment": check.assessment}
            for check in choice.checks
        ],
    }
    return actual, invariant_error


def _actual_event(state: Session, step: dict, now: datetime,
                  fixture: SyntheticFixture) -> tuple[Session, dict, str | None]:
    event = Event(
        action=Action(step["action"]),
        expected_generation=step["expected_generation"],
        region_code=step.get("region_code"),
        fixture=fixture if step.get("fixture") == "primary" else None,
    )
    old = state
    try:
        state = reduce_session(state, event, now)
        transition = "APPLIED"
    except StaleSessionError:
        transition = "STALE_REJECTED"
        if state is not old:
            raise AssertionError("stale D operation unexpectedly mutated state")
    view, invariant_error = _safe_view_check(state, now)
    return state, {**view, "transition": transition}, invariant_error


def replay(manifest: dict) -> dict:
    if (not isinstance(manifest, dict) or manifest.get("schema_id") != MANIFEST_ID
            or manifest.get("synthetic_only") is not True
            or set(manifest) != {"schema_id", "synthetic_only", "fixture", "records", "steps"}):
        raise ValueError("invalid C synthetic-only manifest")
    fixture = build_fixture(manifest["fixture"])
    records = build_records(manifest["records"], fixture)
    steps = manifest["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("missing replay steps")
    state = Session()
    trace = []
    for i, step in enumerate(steps):
        if (not isinstance(step, dict) or not isinstance(step.get("expect"), dict)
                or not step["expect"] or
                not set(step["expect"]) <= EXPECTED_KEYS or
                step.get("kind") not in ("EVENT", "CHECK")):
            return {"status": "BLOCKED", "code": "INVALID_EXPECTATION", "trace": trace}
        try:
            now = moment(step["at"])
            if step["kind"] == "EVENT":
                state, actual, safety_error = _actual_event(state, step, now, fixture)
            else:
                actual, safety_error = _actual_check(state, step, records, now)
        except (ValueError, TypeError, KeyError, OverflowError, AssertionError, AttributeError) as exc:
            trace.append({"step": i, "kind": step["kind"], "error_type": type(exc).__name__})
            return {"status": "BLOCKED", "code": "INVALID_REPLAY_INPUT", "trace": trace}
        mismatches = {
            field: {"expected": wanted, "actual": actual.get(field)}
            for field, wanted in step["expect"].items() if actual.get(field) != wanted
        }
        trace.append({"step": i, "kind": step["kind"], "actual": actual})
        if safety_error:
            return {"status": "FAIL", "code": safety_error, "trace": trace}
        if mismatches:
            trace[-1]["mismatches"] = mismatches
            return {"status": "FAIL", "code": "FIXED_EXPECTATION_MISMATCH", "trace": trace}
    return {"status": "PASS", "code": "REAL_CHAIN_REPLAY_MATCHED", "trace": trace}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C-only actual S0/S1 full-chain synthetic replay")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = replay(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"INVALID_SYNTHETIC_MANIFEST: {exc}", file=sys.stderr)
        return 2
    report = {
        "regression": "PASS" if result["status"] == "PASS" else "FAIL",
        "synthetic_only": True, "official_acceptance": False,
        "live_data_verified": False, "facility_safety_verified": False,
        "route_safety_verified": False, "public_release_approved": False,
        "device_qa": "NOT_RUN", **result,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f'{result["status"]} / {result["code"]} / {len(result["trace"])} replay steps')
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
