"""S1-P4: private synthetic walkthrough interaction reducer and live projection.

No D→B transport contract. Only explicit fictional records in the current S0
DRILL; interaction revision rejects late filter/choice commands within one S0
generation. Never stores comparison reports, official facts or personal data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.hinanex.drill_session import (
    Action, Event, Mode, Session, SyntheticFixture, reduce_session, safe_view,
)
from src.hinanex.s1_synthetic_narrowing import NarrowRequest, SyntheticReference
from src.hinanex.s1_synthetic_review_choice import (
    ExplicitReviewChoice, choose_synthetic_for_review,
)
from src.hinanex.s1_synthetic_what_if import (
    WhatIfRequest, WhatIfResult, compare_what_if,
)


class IntentKind(str, Enum):
    START = "START"
    SET_CONDITIONS = "SET_CONDITIONS"
    REVIEW = "REVIEW"
    CLEAR_REVIEW = "CLEAR_REVIEW"
    STOP = "STOP"
    SELECT_REGION = "SELECT_REGION"
    SOURCE_FAILED = "SOURCE_FAILED"
    RESET = "RESET"


@dataclass(frozen=True)
class WalkthroughIntent:
    kind: IntentKind
    expected_generation: int
    expected_revision: int
    explicit_user_action: bool = False
    conditions: tuple[str, ...] = ()
    selected_record_id: str | None = None
    region_code: str | None = None
    fixture: SyntheticFixture | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, IntentKind):
            raise ValueError("unknown synthetic walkthrough action")
        if (type(self.expected_generation) is not int or self.expected_generation < 0
                or type(self.expected_revision) is not int or self.expected_revision < 0
                or type(self.explicit_user_action) is not bool):
            raise ValueError("expected generation/revision and user action must be explicit types")
        if not isinstance(self.conditions, tuple):
            raise ValueError("conditions must be an immutable tuple")
        if self.kind == IntentKind.START:
            if (not self.explicit_user_action or not isinstance(self.fixture, SyntheticFixture)
                    or self.region_code != self.fixture.region_code
                    or not self.fixture.fixture_id.startswith("synthetic:")
                    or self.selected_record_id is not None):
                raise ValueError("START requires explicit synthetic fixture and exact region")
            NarrowRequest(self.expected_generation, self.region_code,
                          self.fixture.hazard, self.conditions)
            if not self.conditions:
                raise ValueError("START requires conditions")
        elif self.kind == IntentKind.SET_CONDITIONS:
            if (not self.explicit_user_action or not self.conditions
                    or self.region_code is not None or self.fixture is not None
                    or self.selected_record_id is not None):
                raise ValueError("SET_CONDITIONS requires explicit conditions only")
            # Contents depend on the active S0 hazard and are validated in apply.
        elif self.kind == IntentKind.REVIEW:
            if (not self.explicit_user_action or not isinstance(self.selected_record_id, str)
                    or not self.selected_record_id.startswith("synthetic:")
                    or self.conditions or self.region_code is not None or self.fixture is not None):
                raise ValueError("REVIEW requires an explicit synthetic record only")
        elif self.kind == IntentKind.SELECT_REGION:
            if (self.conditions or self.selected_record_id is not None or self.fixture is not None
                    or self.explicit_user_action is not True):
                raise ValueError("region change requires explicit region alone")
            # Event validates its exact region format in apply.
        elif (self.conditions or self.selected_record_id is not None
              or self.region_code is not None or self.fixture is not None
              or self.explicit_user_action):
            raise ValueError("unexpected action payload")


@dataclass(frozen=True)
class WalkthroughState:
    """Internal immutable state: no old comparisons, no persisted preferences."""

    session: Session = field(default_factory=Session)
    conditions: tuple[str, ...] = ()
    previous_conditions: tuple[str, ...] = ()
    selected_record_id: str | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.session, Session) or type(self.revision) is not int or self.revision < 0:
            raise ValueError("invalid walkthrough state")
        if self.session.mode == Mode.NORMAL:
            if self.conditions or self.previous_conditions or self.selected_record_id is not None:
                raise ValueError("NORMAL state must not retain drill choices")
        else:
            f = self.session.fixture
            if (f is None or not f.fixture_id.startswith("synthetic:")
                    or not self.conditions or not self.previous_conditions):
                raise ValueError("DRILL state requires a synthetic fixture and explicit choices")
            NarrowRequest(self.session.generation, f.region_code, f.hazard, self.conditions)
            NarrowRequest(self.session.generation, f.region_code, f.hazard, self.previous_conditions)
            if (self.selected_record_id is not None
                    and (not isinstance(self.selected_record_id, str)
                         or not self.selected_record_id.startswith("synthetic:"))):
                raise ValueError("only synthetic review IDs can be held in memory")


@dataclass(frozen=True)
class WalkthroughTransition:
    status: str
    reason_code: str
    state: WalkthroughState
    synthetic_only: bool = True
    official_acceptance: bool = False
    live_data_verified: bool = False
    release_approved: bool = False

    def __post_init__(self) -> None:
        if (self.synthetic_only is not True
                or any(x is not False for x in (
                    self.official_acceptance, self.live_data_verified, self.release_approved
                ))):
            raise ValueError("synthetic interaction cannot grant public/live access")


@dataclass(frozen=True)
class WalkthroughProjection:
    status: str
    reason_code: str
    generation: int
    revision: int
    result: WhatIfResult | None = None
    synthetic_only: bool = True
    official_acceptance: bool = False
    live_data_verified: bool = False
    facility_safety_verified: bool = False
    route_safety_verified: bool = False
    release_approved: bool = False

    def __post_init__(self) -> None:
        if (self.synthetic_only is not True or
                any(x is not False for x in (
                    self.official_acceptance, self.live_data_verified,
                    self.facility_safety_verified, self.route_safety_verified,
                    self.release_approved,
                ))):
            raise ValueError("synthetic projection cannot grant real-world approval")
        if self.status == "BLOCKED" and self.result is not None:
            raise ValueError("blocked projection must not contain stale comparison data")


def _clear(state: WalkthroughState, session: Session) -> WalkthroughState:
    return WalkthroughState(session=session, revision=state.revision + 1)


def _invalidate_expired(state: WalkthroughState, now: datetime) -> WalkthroughState:
    # A reducer event advances the S0 generation to invalidate delayed actions
    # even when no periodic timer tick ran at the expiration boundary.
    if state.session.mode == Mode.DRILL and safe_view(state.session, now).mode != Mode.DRILL:
        stopped = reduce_session(state.session, Event(
            Action.STOP_DRILL, state.session.generation,
        ), now)
        return _clear(state, stopped)
    return state


def apply_walkthrough_intent(
    state: WalkthroughState,
    intent: WalkthroughIntent,
    records: tuple[SyntheticReference, ...],
    now: datetime,
) -> WalkthroughTransition:
    """Explicit one-step command. Never accepts an old interaction revision."""
    if not isinstance(state, WalkthroughState) or not isinstance(intent, WalkthroughIntent):
        raise TypeError("explicit state and command required")
    if (not isinstance(records, tuple) or
            any(not isinstance(x, SyntheticReference) for x in records)):
        raise ValueError("only immutable fictional record tuples allowed")
    state = _invalidate_expired(state, now)
    if (intent.expected_generation != state.session.generation
            or intent.expected_revision != state.revision):
        return WalkthroughTransition("BLOCKED", "STALE_WALKTHROUGH_ACTION", state)

    if intent.kind == IntentKind.START:
        event = Event(
            Action.START_DRILL, state.session.generation,
            region_code=intent.region_code, fixture=intent.fixture,
        )
        session = reduce_session(state.session, event, now)
        if session.mode != Mode.DRILL:
            return WalkthroughTransition(
                "BLOCKED", session.reason, _clear(state, session),
            )
        return WalkthroughTransition(
            "APPLIED_SYNTHETIC_ONLY", "SYNTHETIC_DRILL_STARTED",
            WalkthroughState(
                session, intent.conditions, intent.conditions, None, state.revision + 1,
            ),
        )

    s = state.session
    if intent.kind in (IntentKind.STOP, IntentKind.SELECT_REGION,
                       IntentKind.SOURCE_FAILED, IntentKind.RESET):
        action = {
            IntentKind.STOP: Action.STOP_DRILL,
            IntentKind.SELECT_REGION: Action.SELECT_REGION,
            IntentKind.SOURCE_FAILED: Action.SOURCE_FAILED,
            IntentKind.RESET: Action.RESET,
        }[intent.kind]
        session = reduce_session(s, Event(
            action, s.generation, region_code=intent.region_code,
        ), now)
        return WalkthroughTransition(
            "APPLIED_SYNTHETIC_ONLY", "SYNTHETIC_CONTEXT_CLEARED",
            _clear(state, session),
        )

    if safe_view(s, now).mode != Mode.DRILL or s.fixture is None:
        return WalkthroughTransition("BLOCKED", "ACTIVE_SYNTHETIC_DRILL_REQUIRED", state)

    if intent.kind == IntentKind.SET_CONDITIONS:
        NarrowRequest(s.generation, s.fixture.region_code,
                      s.fixture.hazard, intent.conditions)
        return WalkthroughTransition(
            "APPLIED_SYNTHETIC_ONLY", "SYNTHETIC_CONDITIONS_CHANGED_SELECTION_CLEARED",
            WalkthroughState(
                s, intent.conditions, state.conditions, None, state.revision + 1,
            ),
        )
    if intent.kind == IntentKind.CLEAR_REVIEW:
        return WalkthroughTransition(
            "APPLIED_SYNTHETIC_ONLY", "SYNTHETIC_REVIEW_CLEARED",
            WalkthroughState(
                s, state.conditions, state.previous_conditions, None, state.revision + 1,
            ),
        )
    if intent.kind == IntentKind.REVIEW:
        decision = choose_synthetic_for_review(
            s,
            NarrowRequest(s.generation, s.fixture.region_code,
                          s.fixture.hazard, state.conditions),
            records,
            ExplicitReviewChoice(intent.selected_record_id, s.generation, True),
            now,
        )
        next_state = WalkthroughState(
            s, state.conditions, state.previous_conditions,
            decision.selected_record_id if decision.status == "REVIEW_SELECTED_SYNTHETIC_ONLY" else None,
            state.revision + 1,
        )
        return WalkthroughTransition(
            "APPLIED_SYNTHETIC_ONLY" if decision.selected_record_id else "BLOCKED",
            decision.reason_code, next_state,
        )
    raise ValueError("unsupported synthetic walkthrough intent")


def project_walkthrough(
    state: WalkthroughState,
    records: tuple[SyntheticReference, ...],
    now: datetime,
) -> WalkthroughProjection:
    """Never projects a cached comparison; checks exact current S0 fixture/time."""
    if not isinstance(state, WalkthroughState):
        raise TypeError("WalkthroughState required")
    view = safe_view(state.session, now)
    if view.mode != Mode.DRILL or state.session.fixture is None:
        return WalkthroughProjection(
            "BLOCKED", view.reason if state.session.mode == Mode.DRILL
            else "ACTIVE_SYNTHETIC_DRILL_REQUIRED",
            view.generation, state.revision,
        )
    fixture = state.session.fixture
    choice = (ExplicitReviewChoice(state.selected_record_id, state.session.generation, True)
              if state.selected_record_id is not None else None)
    result = compare_what_if(
        state.session,
        WhatIfRequest(
            state.session.generation, fixture.region_code, fixture.hazard,
            state.previous_conditions, state.conditions, choice,
        ),
        records, now,
    )
    if result.status != "EVALUATED_SYNTHETIC_ONLY":
        return WalkthroughProjection(
            "BLOCKED", result.reason_code, result.generation, state.revision,
        )
    return WalkthroughProjection(
        "EVALUATED_SYNTHETIC_ONLY", "INTERNAL_SYNTHETIC_WALKTHROUGH",
        result.generation, state.revision, result,
    )
