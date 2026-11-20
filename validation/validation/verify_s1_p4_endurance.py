"""C-only bounded endurance of real D S1-P4 in-memory synthetic operations.

This supplements (not replaces) the independent 40-step C golden replay.
Deterministic, no random source, no D preview import, no file writes, no live or
official data, no UI contract and no persistence. Never claims memory profiling.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import sys

from verify_s1_p4_sequential_replay import (
    _flags as c_flags, _projection_audit, _state_audit,
)
from verify_s1_full_chain_replay import ROOT
PIPELINE = ROOT / "pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from src.hinanex.drill_session import (
    Mode, SYNTHETIC_ONLY, SyntheticFixture, safe_view,
)
from src.hinanex.s1_synthetic_narrowing import SyntheticReference
from src.hinanex.s1_synthetic_walkthrough import (
    IntentKind, WalkthroughIntent, WalkthroughState,
    apply_walkthrough_intent, project_walkthrough,
)

SCHEMA = "hinanex.c.s1_p4_endurance.v0.1"
START = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)
MAX_CYCLES = 64
DEFAULT_CYCLES = 48
PET = ("pet_support",)
STEP = ("step_free",)
BOTH = ("pet_support", "step_free")
SOURCE = (
    ("a", True, True),
    ("b", True, False),
    ("c", False, True),
    ("d", None, True),
    ("e", False, None),
)
RESTART_SOURCE = (
    ("a", False, False),
    ("b", None, True),
    ("c", True, True),
    ("d", True, None),
    ("e", False, False),
)
# C-authored expected full classifications, including an out-of-fixture record.
EXPECTED = {
    "A_PET": ("MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC",
              "NOT_MATCHED_SYNTHETIC", "UNKNOWN",
              "NOT_MATCHED_SYNTHETIC", "UNKNOWN"),
    "A_STEP": ("MATCHED_SYNTHETIC", "NOT_MATCHED_SYNTHETIC",
               "MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC", "UNKNOWN", "UNKNOWN"),
    "A_BOTH": ("MATCHED_SYNTHETIC", "NOT_MATCHED_SYNTHETIC",
               "NOT_MATCHED_SYNTHETIC", "UNKNOWN",
               "UNKNOWN", "UNKNOWN"),
    "B_STEP": ("NOT_MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC",
               "MATCHED_SYNTHETIC", "UNKNOWN",
               "NOT_MATCHED_SYNTHETIC", "UNKNOWN"),
    "B_PET": ("NOT_MATCHED_SYNTHETIC", "UNKNOWN",
              "MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC",
              "NOT_MATCHED_SYNTHETIC", "UNKNOWN"),
}


class EnduranceViolation(Exception):
    def __init__(self, reason_code: str, cycle_index: int):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.cycle_index = cycle_index


def require(test: object, code: str, cycle: int) -> None:
    if not test:
        raise EnduranceViolation(code, cycle)


def fictional_data(cycle: int, phase: str) -> tuple[SyntheticFixture, tuple[SyntheticReference, ...]]:
    if type(cycle) is not int or not 0 <= cycle < MAX_CYCLES or phase not in ("A", "B"):
        raise ValueError("bounded fictional cycle and phase required")
    offset = (cycle * 2 + (0 if phase == "A" else 1)) * 40
    now = START + timedelta(minutes=offset)
    fid = f"synthetic:resilience-{cycle:02d}-{phase}"
    fixture = SyntheticFixture(fid, "13123", "flood", now,
                               now + timedelta(minutes=30), SYNTHETIC_ONLY)
    source = SOURCE if phase == "A" else RESTART_SOURCE
    records = tuple(SyntheticReference(
        record_id=f"synthetic:resilience-{cycle:02d}-{phase}-{name}",
        fixture_id=fid, region_code="13123", hazard="flood",
        observed_at=now, expires_at=fixture.expires_at,
        conditions=(("pet_support", pet), ("step_free", step)),
    ) for name, pet, step in source)
    records += (SyntheticReference(
        record_id=f"synthetic:resilience-{cycle:02d}-{phase}-foreign",
        fixture_id=f"synthetic:unrelated-{cycle:02d}-{phase}",
        region_code="13123", hazard="flood",
        observed_at=now, expires_at=fixture.expires_at,
        conditions=(("pet_support", True), ("step_free", True)),
    ),)
    return fixture, records


def run_endurance(cycles: int = DEFAULT_CYCLES) -> dict:
    """Bounded repeat/restart oracle; only current state is retained.

    A clean result means synthetic domain regressions only. Each active
    projection is also independently cross-checked by the older C→P1
    provenance verifier, not only the scenario's hand-authored status arrays.
    """
    if type(cycles) is not int or not 1 <= cycles <= MAX_CYCLES:
        raise ValueError(f"cycles must be an integer in 1..{MAX_CYCLES}")
    count_actions = 0
    count_projections = 0
    expiry_count = 0
    stale_rejects = 0
    state = WalkthroughState()

    def project(records, now, cycle, *,
                statuses=None, before=None, after=None, chosen=None,
                classification=None, missing=(), failed=()):
        nonlocal count_projections
        projection = project_walkthrough(state, records, now)
        count_projections += 1
        issue = _state_audit(state) or _projection_audit(
            state, projection, records, now,
        )
        require(issue is None, issue or "PROJECTION_INVALID", cycle)
        require(c_flags(projection), "PROJECTION_APPROVAL_LEAK", cycle)
        require(projection.generation == state.session.generation and
                projection.revision == state.revision, "PROJECTION_STALE_VERSION", cycle)
        if statuses is None:
            require(projection.status == "BLOCKED" and projection.result is None,
                    "STALE_RESULT_VISIBLE", cycle)
            require(safe_view(state.session, now).mode == Mode.NORMAL,
                    "BLOCKED_VIEW_CLAIMS_ACTIVE_DRILL", cycle)
            return
        require(projection.status == "EVALUATED_SYNTHETIC_ONLY" and
                projection.result is not None, "ACTIVE_PROJECTION_NOT_EVALUATED", cycle)
        result = projection.result
        require(tuple(row.after_status for row in result.rows) == EXPECTED[statuses],
                "INDEPENDENT_EXPECTED_CLASSIFICATION_MISMATCH", cycle)
        require(result.before_conditions == (before or after) and
                result.after_conditions == after, "CONDITION_HISTORY_INCORRECT", cycle)
        require(result.generation == state.session.generation,
                "RESULT_GENERATION_STALE", cycle)
        require(state.selected_record_id == chosen, "STATE_REVIEW_ID_WRONG", cycle)
        if chosen is None:
            require(result.review is None, "IMPLICIT_OR_STALE_REVIEW", cycle)
        else:
            rv = result.review
            require(rv is not None and rv.selected_record_id == chosen and
                    rv.comparison_status == classification and
                    rv.missing == missing and rv.failed == failed and
                    rv.review_only is True, "REVIEW_CHANGED_FACT_OR_SELECTION", cycle)
        require(all(row.record_id.startswith("synthetic:resilience-")
                    for row in result.rows), "FOREIGN_RECORD_LEAK", cycle)

    def issue(cycle, now, records, kind, *, explicit=False, conditions=(),
              record=None, region=None, fixture=None, vintage=None,
              outcome="APPLIED_SYNTHETIC_ONLY", why=None,
              delta_g=0, delta_r=1, unchanged=False):
        nonlocal state, count_actions, stale_rejects
        previous = state
        g, r = previous.session.generation, previous.revision
        use_g, use_r = vintage if vintage is not None else (g, r)
        intent = WalkthroughIntent(
            kind, use_g, use_r, explicit, conditions, record, region, fixture,
        )
        transition = apply_walkthrough_intent(state, intent, records, now)
        state = transition.state
        count_actions += 1
        require(c_flags(transition), "TRANSITION_APPROVAL_LEAK", cycle)
        require(transition.status == outcome, "UNEXPECTED_TRANSITION_STATUS", cycle)
        if why is not None:
            require(transition.reason_code == why, "UNEXPECTED_TRANSITION_REASON", cycle)
        require(state.session.generation == g + delta_g and
                state.revision == r + delta_r, "WRONG_VERSION_INCREMENT", cycle)
        if unchanged:
            require(state is previous and state == previous,
                    "STALE_COMMAND_MUTATED_CURRENT_STATE", cycle)
        if kind == IntentKind.SET_CONDITIONS and outcome == "APPLIED_SYNTHETIC_ONLY":
            require(state.selected_record_id is None,
                    "FILTER_RETAINED_OLD_REVIEW", cycle)
        if kind in (IntentKind.STOP, IntentKind.RESET,
                    IntentKind.SELECT_REGION, IntentKind.SOURCE_FAILED) and outcome == "APPLIED_SYNTHETIC_ONLY":
            require(state.session.mode == Mode.NORMAL and
                    not state.conditions and not state.previous_conditions and
                    state.selected_record_id is None, "TERMINAL_STATE_NOT_CLEARED", cycle)
        if outcome == "BLOCKED" and why == "STALE_WALKTHROUGH_ACTION":
            stale_rejects += 1
        return g, r

    try:
        for cycle in range(cycles):
            f_a, data_a = fictional_data(cycle, "A")
            now_a = f_a.observed_at + timedelta(minutes=5)
            require(state.session.mode == Mode.NORMAL and
                    state.selected_record_id is None and not state.conditions,
                    "CROSS_CYCLE_STATE_LEAK", cycle)

            issue(cycle, f_a.observed_at, data_a, IntentKind.START, explicit=True,
                  conditions=PET, region="13123", fixture=f_a,
                  why="SYNTHETIC_DRILL_STARTED", delta_g=1)
            project(data_a, now_a, cycle, statuses="A_PET", after=PET)
            item_a = data_a[0].record_id
            item_c = data_a[2].record_id
            item_e = data_a[4].record_id
            foreign = data_a[5].record_id

            issue(cycle, now_a, data_a, IntentKind.REVIEW, explicit=True,
                  record=item_a, why="EXPLICIT_FICTIONAL_REVIEW_SELECTION")
            project(data_a, now_a, cycle, statuses="A_PET", after=PET,
                    chosen=item_a, classification="MATCHED_SYNTHETIC")
            before_change = (state.session.generation, state.revision)

            issue(cycle, now_a, data_a, IntentKind.SET_CONDITIONS,
                  explicit=True, conditions=STEP,
                  why="SYNTHETIC_CONDITIONS_CHANGED_SELECTION_CLEARED")
            project(data_a, now_a, cycle, statuses="A_STEP", before=PET, after=STEP)
            issue(cycle, now_a, data_a, IntentKind.REVIEW, explicit=True,
                  record=item_a, vintage=before_change, outcome="BLOCKED",
                  why="STALE_WALKTHROUGH_ACTION", delta_r=0, unchanged=True)
            project(data_a, now_a, cycle, statuses="A_STEP", before=PET, after=STEP)

            issue(cycle, now_a, data_a, IntentKind.REVIEW, explicit=True,
                  record=item_e, why="EXPLICIT_FICTIONAL_REVIEW_SELECTION")
            project(data_a, now_a, cycle, statuses="A_STEP", before=PET, after=STEP,
                    chosen=item_e, classification="UNKNOWN", missing=STEP)
            issue(cycle, now_a, data_a, IntentKind.SET_CONDITIONS,
                  explicit=True, conditions=PET, vintage=before_change,
                  outcome="BLOCKED", why="STALE_WALKTHROUGH_ACTION",
                  delta_r=0, unchanged=True)
            project(data_a, now_a, cycle, statuses="A_STEP", before=PET, after=STEP,
                    chosen=item_e, classification="UNKNOWN", missing=STEP)

            issue(cycle, now_a, data_a, IntentKind.SET_CONDITIONS,
                  explicit=True, conditions=BOTH,
                  why="SYNTHETIC_CONDITIONS_CHANGED_SELECTION_CLEARED")
            project(data_a, now_a, cycle, statuses="A_BOTH", before=STEP, after=BOTH)
            issue(cycle, now_a, data_a, IntentKind.CLEAR_REVIEW,
                  why="SYNTHETIC_REVIEW_CLEARED")
            project(data_a, now_a, cycle, statuses="A_BOTH", before=STEP, after=BOTH)

            issue(cycle, now_a, data_a, IntentKind.REVIEW, explicit=True,
                  record=foreign, outcome="BLOCKED",
                  why="RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE")
            project(data_a, now_a, cycle, statuses="A_BOTH", before=STEP, after=BOTH)
            issue(cycle, now_a, data_a, IntentKind.REVIEW, explicit=True,
                  record=item_c, why="EXPLICIT_FICTIONAL_REVIEW_SELECTION")
            project(data_a, now_a, cycle, statuses="A_BOTH", before=STEP, after=BOTH,
                    chosen=item_c, classification="NOT_MATCHED_SYNTHETIC",
                    failed=PET)
            old_a_version = (state.session.generation, state.revision)

            if cycle % 5 == 0:
                expiry_count += 1
                end = f_a.expires_at
                project(data_a, end, cycle)
                issue(cycle, end, data_a, IntentKind.REVIEW, explicit=True,
                      record=item_c, vintage=old_a_version,
                      outcome="BLOCKED", why="STALE_WALKTHROUGH_ACTION",
                      delta_g=1)
                project(data_a, end, cycle)
            else:
                exits = (IntentKind.STOP, IntentKind.SOURCE_FAILED,
                         IntentKind.SELECT_REGION, IntentKind.RESET)
                kind = exits[cycle % len(exits)]
                issue(cycle, now_a, data_a, kind, delta_g=1,
                      explicit=kind == IntentKind.SELECT_REGION,
                      region="15100" if kind == IntentKind.SELECT_REGION else None,
                      why="SYNTHETIC_CONTEXT_CLEARED")
                project(data_a, now_a, cycle)

            # A delayed callback issued during phase A cannot revive it.
            issue(cycle, now_a if cycle % 5 else f_a.expires_at,
                  data_a, IntentKind.REVIEW, explicit=True, record=item_a,
                  vintage=old_a_version, outcome="BLOCKED",
                  why="STALE_WALKTHROUGH_ACTION", delta_r=0, unchanged=True)

            f_b, data_b = fictional_data(cycle, "B")
            now_b = f_b.observed_at + timedelta(minutes=5)
            issue(cycle, f_b.observed_at, data_b, IntentKind.START,
                  explicit=True, conditions=STEP, region="13123", fixture=f_b,
                  why="SYNTHETIC_DRILL_STARTED", delta_g=1)
            project(data_b, now_b, cycle, statuses="B_STEP", after=STEP)
            require(state.selected_record_id is None and
                    f_a.fixture_id != state.session.fixture.fixture_id,
                    "OLD_FIXTURE_OR_SELECTION_RESTORED", cycle)
            # A valid delayed A command can never apply to a new B generation.
            issue(cycle, now_b, data_b, IntentKind.REVIEW, explicit=True,
                  record=item_e, vintage=old_a_version,
                  outcome="BLOCKED", why="STALE_WALKTHROUGH_ACTION",
                  delta_r=0, unchanged=True)
            item_d_b = data_b[3].record_id
            issue(cycle, now_b, data_b, IntentKind.REVIEW, explicit=True,
                  record=item_d_b, why="EXPLICIT_FICTIONAL_REVIEW_SELECTION")
            project(data_b, now_b, cycle, statuses="B_STEP", after=STEP,
                    chosen=item_d_b, classification="UNKNOWN", missing=STEP)
            issue(cycle, now_b, data_b, IntentKind.SET_CONDITIONS,
                  explicit=True, conditions=PET,
                  why="SYNTHETIC_CONDITIONS_CHANGED_SELECTION_CLEARED")
            project(data_b, now_b, cycle, statuses="B_PET", before=STEP, after=PET)
            issue(cycle, now_b, data_b, IntentKind.REVIEW, explicit=True,
                  record=item_d_b, why="EXPLICIT_FICTIONAL_REVIEW_SELECTION")
            project(data_b, now_b, cycle, statuses="B_PET", before=STEP, after=PET,
                    chosen=item_d_b, classification="MATCHED_SYNTHETIC")
            issue(cycle, now_b, data_b, IntentKind.STOP, delta_g=1,
                  why="SYNTHETIC_CONTEXT_CLEARED")
            project(data_b, now_b, cycle)
            require(state.session.mode == Mode.NORMAL and
                    state.selected_record_id is None and
                    not state.conditions and not state.previous_conditions and
                    state.session.fixture is None, "CYCLE_TERMINAL_LEAK", cycle)

    except EnduranceViolation as issue:
        return {
            "schema_id": SCHEMA, "status": "FAIL",
            "reason_code": issue.reason_code, "first_failed_cycle": issue.cycle_index,
            "cycles_requested": cycles, "cycles_completed": issue.cycle_index,
            "actions_executed": count_actions, "projections_checked": count_projections,
            "stale_actions_rejected": stale_rejects, "expiry_boundaries_checked": expiry_count,
            "synthetic_only": True, "eligible_for_s1_real_facilities": False,
            "official_acceptance": False, "live_data_verified": False,
            "facility_safety_verified": False, "route_safety_verified": False,
            "release_approved": False, "device_qa": "NOT_RUN",
        }

    return {
        "schema_id": SCHEMA, "status": "PASS",
        "reason_code": "C_SYNTHETIC_ENDURANCE_SEQUENCE_MATCHED",
        "cycles_requested": cycles, "cycles_completed": cycles,
        "actions_executed": count_actions, "projections_checked": count_projections,
        "stale_actions_rejected": stale_rejects, "expiry_boundaries_checked": expiry_count,
        "synthetic_only": True, "eligible_for_s1_real_facilities": False,
        "official_acceptance": False, "live_data_verified": False,
        "facility_safety_verified": False, "route_safety_verified": False,
        "release_approved": False, "device_qa": "NOT_RUN",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic-only S1-P4 C endurance replay")
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_endurance(args.cycles)
    except (ValueError, TypeError) as exc:
        print(f"C_ENDURANCE_INPUT_INVALID__NO_APPROVAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'{result["status"]}: {result["reason_code"]}; '
              f'{result["cycles_completed"]}/{result["cycles_requested"]} cycles; '
              f'{result["actions_executed"]} commands; '
              f'{result["projections_checked"]} projections')
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
