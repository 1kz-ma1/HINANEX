"""C independent S1-P4 sequential synthetic replay over the real D reducer.

Fixed C expectations and independent cross-layer invariants. No D preview
import, browser API, live/official data, original bytes, file writes or safety
approval. This runner does not turn synthetic UI selections into shelters.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from verify_s1_full_chain_replay import build_fixture, build_records, moment
from src.hinanex.drill_session import (
    DRILL_NOTICE, NORMAL_NOTICE, Mode, SYNTHETIC_ONLY, safe_view,
)
from src.hinanex.s1_synthetic_narrowing import NarrowRequest
from src.hinanex.s1_synthetic_comparison import compare_synthetic_conditions
from src.hinanex.s1_synthetic_walkthrough import (
    IntentKind, WalkthroughIntent, WalkthroughState,
    apply_walkthrough_intent, project_walkthrough,
)

SCHEMA = "hinanex.c.s1_p4_sequential_replay.v0.1"
FIXTURE = ROOT / "validation" / "fixtures" / "s1_p4_sequential_c_replay_v01.json"
SAFE_FLAGS = (
    "official_acceptance", "live_data_verified", "facility_safety_verified",
    "route_safety_verified", "release_approved",
)
EXPECT_FIELDS = frozenset((
    "transition", "transition_reason", "mode", "view_mode", "generation",
    "revision", "region", "fixture_id", "conditions", "previous_conditions",
    "selected_id", "projection", "projection_reason", "before_statuses",
    "after_statuses", "new_ids", "removed_ids", "unknown_ids",
    "review_id", "review_classification", "review_missing", "review_failed",
))
STEP_FIELDS = frozenset((
    "at", "intent", "expected_generation", "expected_revision", "explicit_user_action",
    "conditions", "selected_record_id", "region_code", "fixture", "expect",
))


class ReplayInputError(ValueError):
    """Malformed or unexpected data is never a successful C replay."""


def _flags(output: object) -> bool:
    return (getattr(output, "synthetic_only", None) is True and
            all(getattr(output, f, None) is False
                for f in SAFE_FLAGS if hasattr(output, f)) and
            getattr(output, "official_acceptance", None) is False and
            getattr(output, "live_data_verified", None) is False and
            getattr(output, "release_approved", None) is False)


def _projection_audit(state, projection, records, now: datetime) -> str | None:
    if not _flags(projection) or projection.facility_safety_verified is not False or projection.route_safety_verified is not False:
        return "PROJECTION_REAL_WORLD_APPROVAL_LEAK"
    if (projection.generation != state.session.generation
            or projection.revision != state.revision):
        return "PROJECTION_VERSION_NOT_CURRENT"

    view = safe_view(state.session, now)
    if view.live_data_verified is not False:
        return "LIVE_SAFETY_ASSERTION"
    if view.mode == Mode.NORMAL:
        if (view.fixture_id is not None or view.hazard is not None
                or view.source_authorization is not None or view.notice != NORMAL_NOTICE):
            return "NORMAL_EXPOSED_STALE_DRILL"
        if projection.status != "BLOCKED" or projection.result is not None:
            return "BLOCKED_PROJECTION_LEAK"
        return None
    if (view.mode != Mode.DRILL or view.notice != DRILL_NOTICE
            or view.source_authorization != SYNTHETIC_ONLY
            or state.session.fixture is None
            or view.fixture_id != state.session.fixture.fixture_id
            or view.selected_region != state.session.fixture.region_code
            or view.hazard != state.session.fixture.hazard):
        return "SYNTHETIC_CONTEXT_NOT_TRACEABLE"
    if projection.status != "EVALUATED_SYNTHETIC_ONLY" or projection.result is None:
        return "ACTIVE_DRILL_PROJECTION_MISSING"
    result = projection.result
    if not _flags(result) or result.facility_safety_verified is not False or result.route_safety_verified is not False:
        return "WHAT_IF_APPROVAL_LEAK"
    if result.generation != state.session.generation or len(result.rows) != len(records):
        return "WHAT_IF_ROW_SCOPE_MISMATCH"
    if (result.before_conditions != state.previous_conditions
            or result.after_conditions != state.conditions):
        return "CONDITION_CONTEXT_DRIFT"
    try:
        earlier = compare_synthetic_conditions(
            state.session, NarrowRequest(state.session.generation,
                                         view.selected_region, view.hazard,
                                         state.previous_conditions), records, now,
        )
        later = compare_synthetic_conditions(
            state.session, NarrowRequest(state.session.generation,
                                         view.selected_region, view.hazard,
                                         state.conditions), records, now,
        )
    except (TypeError, ValueError):
        return "P1_COMPARISON_INVALID"
    if (earlier.status != "EVALUATED_SYNTHETIC_ONLY"
            or later.status != "EVALUATED_SYNTHETIC_ONLY"
            or len(earlier.rows) != len(later.rows)
            or len(result.rows) != len(later.rows)):
        return "P1_COMPARISON_MISSING"
    for before, after, row in zip(earlier.rows, later.rows, result.rows, strict=True):
        if (row.record_id != before.record_id or row.record_id != after.record_id
                or any(not row.record_id.startswith(prefix) for prefix in ("synthetic:",))
                or row.before_status != before.status or row.after_status != after.status
                or row.before_reason_code != before.reason_code
                or row.after_reason_code != after.reason_code
                or row.before_checks != before.checks or row.after_checks != after.checks
                or row.before_missing != before.missing or row.after_missing != after.missing
                or row.before_failed != before.failed or row.after_failed != after.failed):
            return "WHAT_IF_CHANGED_SOURCE_CLASSIFICATION"
    expected_new = tuple(row.record_id for row in result.rows
                         if row.before_status != "MATCHED_SYNTHETIC" and row.after_status == "MATCHED_SYNTHETIC")
    expected_removed = tuple(row.record_id for row in result.rows
                             if row.before_status == "MATCHED_SYNTHETIC" and row.after_status != "MATCHED_SYNTHETIC")
    expected_unknown = tuple(row.record_id for row in result.rows if row.after_status == "UNKNOWN")
    if (result.newly_matching_synthetic_ids != expected_new
            or result.no_longer_matching_synthetic_ids != expected_removed
            or result.unknown_after_synthetic_ids != expected_unknown):
        return "WHAT_IF_MISLEADING_DIFF"
    if state.selected_record_id is None:
        if result.review is not None:
            return "IMPLICIT_REVIEW_SELECTION"
    else:
        review = result.review
        row = next((r for r in later.rows if r.record_id == state.selected_record_id), None)
        if (review is None or not _flags(review)
                or getattr(review, "review_only", None) is not True
                or review.facility_safety_verified is not False
                or review.route_safety_verified is not False
                or row is None or any(c.assessment == "NOT_EVALUATED" for c in row.checks)
                or review.status != "REVIEW_SELECTED_SYNTHETIC_ONLY"
                or review.selected_record_id != row.record_id
                or review.comparison_status != row.status
                or review.comparison_reason_code != row.reason_code
                or review.checks != row.checks
                or review.missing != row.missing or review.failed != row.failed):
            return "REVIEW_CLASSIFICATION_PROMOTED_OR_STALE"
    return None


def _state_audit(state) -> str | None:
    if (state.session.mode == Mode.NORMAL and
            (state.conditions or state.previous_conditions or state.selected_record_id is not None
             or state.session.fixture is not None)):
        return "NORMAL_RETAINS_PRIVATE_DRILL_STATE"
    if state.session.mode == Mode.DRILL and (
            state.session.fixture is None
            or not state.session.fixture.fixture_id.startswith("synthetic:")
            or state.session.fixture.source_authorization != SYNTHETIC_ONLY):
        return "UNTRUSTED_DRILL_FIXTURE"
    if (state.selected_record_id is not None
            and not state.selected_record_id.startswith("synthetic:")):
        return "NON_SYNTHETIC_REVIEW_ID"
    return None


def _snapshot(state, transition, projection, now: datetime) -> dict:
    view = safe_view(state.session, now)
    result = projection.result
    review = result.review if result else None
    return {
        "transition": transition.status if transition is not None else None,
        "transition_reason": transition.reason_code if transition is not None else None,
        "mode": state.session.mode.value, "view_mode": view.mode.value,
        "generation": state.session.generation, "revision": state.revision,
        "region": state.session.selected_region, "fixture_id": view.fixture_id,
        "conditions": list(state.conditions),
        "previous_conditions": list(state.previous_conditions),
        "selected_id": state.selected_record_id,
        "projection": projection.status, "projection_reason": projection.reason_code,
        "before_statuses": [r.before_status for r in result.rows] if result else [],
        "after_statuses": [r.after_status for r in result.rows] if result else [],
        "new_ids": list(result.newly_matching_synthetic_ids) if result else [],
        "removed_ids": list(result.no_longer_matching_synthetic_ids) if result else [],
        "unknown_ids": list(result.unknown_after_synthetic_ids) if result else [],
        "review_id": review.selected_record_id if review else None,
        "review_classification": review.comparison_status if review else None,
        "review_missing": list(review.missing) if review else [],
        "review_failed": list(review.failed) if review else [],
    }


def replay(packet: dict) -> dict:
    if (not isinstance(packet, dict) or set(packet) != {"schema_id", "fixture", "records", "scenarios", "synthetic_only"}
            or packet["schema_id"] != SCHEMA or packet["synthetic_only"] is not True):
        raise ReplayInputError("invalid C-only synthetic replay packet")
    fixture = build_fixture(packet["fixture"])
    if not fixture.fixture_id.startswith("synthetic:"):
        raise ReplayInputError("fixture must have an explicit fictional ID")
    records = build_records(packet["records"], fixture)
    if (not records or any(not r.record_id.startswith("synthetic:") or
                           not r.fixture_id.startswith("synthetic:") for r in records)):
        raise ReplayInputError("synthetic records only")
    scenarios = packet["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ReplayInputError("nonempty scenarios required")
    seen = set()
    traces = []
    for scene in scenarios:
        if (not isinstance(scene, dict) or set(scene) != {"scenario_id", "steps"}
                or not isinstance(scene["scenario_id"], str)
                or not scene["scenario_id"].startswith("synthetic:")
                or scene["scenario_id"] in seen
                or not isinstance(scene["steps"], list) or not scene["steps"]):
            raise ReplayInputError("invalid scenario shape/id")
        seen.add(scene["scenario_id"])
        state = WalkthroughState()
        for index, step in enumerate(scene["steps"]):
            if (not isinstance(step, dict) or set(step) != STEP_FIELDS
                    or not isinstance(step["expect"], dict)
                    or set(step["expect"]) != EXPECT_FIELDS):
                return {"status": "BLOCKED", "code": "MISSING_OR_UNREVIEWED_EXPECTATION", "trace": traces}
            try:
                now = moment(step["at"])
                previous = state
                transition = None
                if step["intent"] is not None:
                    intent = WalkthroughIntent(
                        kind=IntentKind(step["intent"]),
                        expected_generation=step["expected_generation"],
                        expected_revision=step["expected_revision"],
                        explicit_user_action=step["explicit_user_action"],
                        conditions=tuple(step["conditions"]),
                        selected_record_id=step["selected_record_id"],
                        region_code=step["region_code"],
                        fixture=fixture if step["fixture"] == "primary" else None,
                    )
                    transition = apply_walkthrough_intent(state, intent, records, now)
                    state = transition.state
                    if not _flags(transition):
                        return {"status": "FAIL", "code": "TRANSITION_REAL_WORLD_APPROVAL_LEAK", "trace": traces}
                    if transition.status == "BLOCKED" and transition.reason_code == "STALE_WALKTHROUGH_ACTION":
                        # The sole sanctioned state change on a stale command is
                        # expiry-triggered clearance and generation invalidation.
                        old_view = safe_view(previous.session, now)
                        if old_view.mode == Mode.DRILL and state != previous:
                            return {"status": "FAIL", "code": "STALE_ACTION_MUTATED_CURRENT_SESSION", "trace": traces}
                    if intent.kind == IntentKind.SET_CONDITIONS and transition.status == "APPLIED_SYNTHETIC_ONLY" and state.selected_record_id is not None:
                        return {"status": "FAIL", "code": "FILTER_CHANGE_RETAINED_REVIEW", "trace": traces}
                    if intent.kind in (IntentKind.STOP, IntentKind.SOURCE_FAILED, IntentKind.SELECT_REGION, IntentKind.RESET) and transition.status == "APPLIED_SYNTHETIC_ONLY" and (
                            state.selected_record_id is not None or state.conditions or state.previous_conditions):
                        return {"status": "FAIL", "code": "CONTEXT_CLEARED_BUT_REVIEW_RETAINED", "trace": traces}
                projection = project_walkthrough(state, records, now)
                if (error := _state_audit(state) or _projection_audit(state, projection, records, now)):
                    return {"status": "FAIL", "code": error, "trace": traces}
                actual = _snapshot(state, transition, projection, now)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError, AssertionError) as exc:
                traces.append({"scenario_id": scene["scenario_id"], "step": index,
                               "error_type": type(exc).__name__})
                return {"status": "BLOCKED", "code": "INVALID_SYNTHETIC_INPUT_OR_RUNTIME", "trace": traces}
            trace = {"scenario_id": scene["scenario_id"], "step": index, "actual": actual}
            traces.append(trace)
            if actual != step["expect"]:
                trace["mismatches"] = {
                    k: {"expected": step["expect"][k], "actual": actual[k]}
                    for k in EXPECT_FIELDS if actual[k] != step["expect"][k]
                }
                return {"status": "FAIL", "code": "C_FIXED_EXPECTATION_MISMATCH", "trace": traces}
    return {"status": "PASS", "code": "S1_P4_SYNTHETIC_SEQUENCE_MATCHED",
            "scenario_count": len(scenarios), "step_count": len(traces), "trace": traces}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C independent actual S1-P4 sequence replay (fictional only)")
    parser.add_argument("--packet", type=Path, default=FIXTURE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = replay(json.loads(args.packet.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"C_SYNTHETIC_REPLAY_INVALID__NO_APPROVAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    report = {
        "regression": "PASS" if output["status"] == "PASS" else "FAIL",
        "synthetic_only": True, "official_acceptance": False,
        "live_data_verified": False, "facility_safety_verified": False,
        "route_safety_verified": False, "public_release_approved": False,
        "device_qa": "NOT_RUN", **output,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f'{report["status"]}: {report["code"]}; {len(report["trace"])} tested checkpoints')
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
