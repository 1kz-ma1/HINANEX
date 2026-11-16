"""S1-P0: deterministic synthetic-only condition narrowing, NEVER safety selection.

Private D-domain prototype. Does not read municipal records, export a shared
contract, store preferences, rank real shelters, or generate a public UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from src.hinanex.drill_session import Mode, SYNTHETIC_ONLY, Session, safe_view


SYNTHETIC_PREFIX = "synthetic:"
CONDITIONS = frozenset({"pet_support", "step_free"})
_SYNTH_ID = re.compile(r"synthetic:[A-Za-z0-9._:-]{1,72}\Z")
_REGION = re.compile(r"[0-9]{5}\Z")
_HAZARD = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
DECISION_MATCH = "MATCHED_SYNTHETIC"
DECISION_NOT_MATCHED = "NOT_MATCHED_SYNTHETIC"
DECISION_UNKNOWN = "UNKNOWN"
NO_REAL_WORLD_APPROVAL = False


def _timezone_aware(time: datetime) -> bool:
    return isinstance(time, datetime) and time.tzinfo is not None and time.utcoffset() is not None


@dataclass(frozen=True)
class SyntheticReference:
    """Fictional test record; no name, address, GPS, actual facility, or official source."""

    record_id: str
    fixture_id: str
    region_code: str
    hazard: str
    observed_at: datetime
    expires_at: datetime
    conditions: tuple[tuple[str, bool | None], ...]
    source_authorization: str = SYNTHETIC_ONLY

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not _SYNTH_ID.fullmatch(self.record_id):
            raise ValueError("record_id must have a synthetic: prefix")
        if not isinstance(self.fixture_id, str) or not _SYNTH_ID.fullmatch(self.fixture_id):
            raise ValueError("fixture_id must have a synthetic: prefix")
        if not isinstance(self.region_code, str) or not _REGION.fullmatch(self.region_code):
            raise ValueError("region_code must be a five-digit test code")
        if not isinstance(self.hazard, str) or not _HAZARD.fullmatch(self.hazard):
            raise ValueError("hazard must be an explicit test token")
        if not _timezone_aware(self.observed_at) or not _timezone_aware(self.expires_at):
            raise ValueError("timestamps must be timezone aware")
        if self.expires_at <= self.observed_at:
            raise ValueError("expires_at must follow observed_at")
        if self.source_authorization != SYNTHETIC_ONLY:
            raise ValueError("official/non-synthetic records are not accepted")
        if not isinstance(self.conditions, tuple):
            raise ValueError("conditions must be a frozen tuple")
        seen = set()
        for pair in self.conditions:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("condition items must be (key, bool|None)")
            key, value = pair
            if key not in CONDITIONS or key in seen or value is not None and type(value) is not bool:
                raise ValueError("unsupported, duplicate or non-boolean condition")
            seen.add(key)


@dataclass(frozen=True)
class NarrowRequest:
    """User-selected synthetic constraints in a single in-memory S0 session."""

    expected_generation: int
    region_code: str
    hazard: str
    required_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.expected_generation) is not int or self.expected_generation < 0:
            raise ValueError("expected_generation must be a nonnegative integer")
        if not isinstance(self.region_code, str) or not _REGION.fullmatch(self.region_code):
            raise ValueError("region_code must be a five-digit test code")
        if not isinstance(self.hazard, str) or not _HAZARD.fullmatch(self.hazard):
            raise ValueError("hazard must be an explicit test token")
        if (not isinstance(self.required_conditions, tuple)
                or any(item not in CONDITIONS for item in self.required_conditions)
                or len(set(self.required_conditions)) != len(self.required_conditions)):
            raise ValueError("invalid or duplicated required conditions")


@dataclass(frozen=True)
class NarrowDecision:
    record_id: str
    status: str
    reason_code: str
    missing: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()


@dataclass(frozen=True)
class NarrowReport:
    """All positive matches here are fictional comparisons, not safety candidates."""

    status: str
    reason_code: str
    generation: int
    decisions: tuple[NarrowDecision, ...] = ()
    matched_synthetic_ids: tuple[str, ...] = ()
    synthetic_only: bool = True
    official_acceptance: bool = NO_REAL_WORLD_APPROVAL
    live_data_verified: bool = NO_REAL_WORLD_APPROVAL
    facility_safety_verified: bool = NO_REAL_WORLD_APPROVAL
    route_safety_verified: bool = NO_REAL_WORLD_APPROVAL
    release_approved: bool = NO_REAL_WORLD_APPROVAL

    def __post_init__(self) -> None:
        if not all((
                self.synthetic_only is True, self.official_acceptance is False,
                self.live_data_verified is False, self.facility_safety_verified is False,
                self.route_safety_verified is False, self.release_approved is False)):
            raise ValueError("S1-P0 cannot approve official/live/safety/publication claims")


def narrow_synthetic_references(
    state: Session,
    request: NarrowRequest,
    records: tuple[SyntheticReference, ...],
    now: datetime,
) -> NarrowReport:
    """Narrow fictional references while refusing stale/ambiguous S0 context.

    All validations happen before a positive result. No real data, storage or
    network calls; caller supplies an explicit clock and current S0 Session.
    """
    if not isinstance(state, Session) or not isinstance(request, NarrowRequest):
        raise TypeError("explicit S0 Session and NarrowRequest are required")
    if not _timezone_aware(now):
        raise ValueError("now must be timezone aware")
    if not isinstance(records, tuple) or any(not isinstance(x, SyntheticReference) for x in records):
        raise ValueError("only immutable synthetic test records are allowed")
    ids = [r.record_id for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate test record_id")

    view = safe_view(state, now)
    if view.mode != Mode.DRILL or state.fixture is None:
        return NarrowReport("BLOCKED", "ACTIVE_SYNTHETIC_DRILL_REQUIRED", state.generation)
    if view.generation != request.expected_generation:
        return NarrowReport("BLOCKED", "STALE_S0_GENERATION", state.generation)
    if (view.selected_region != request.region_code or
            view.hazard != request.hazard or
            view.fixture_id != state.fixture.fixture_id or
            view.source_authorization != SYNTHETIC_ONLY or
            view.live_data_verified is not False):
        return NarrowReport("BLOCKED", "S0_CONTEXT_MISMATCH", state.generation)
    if not request.required_conditions:
        return NarrowReport("BLOCKED", "EXPLICIT_CONDITION_REQUIRED", state.generation)

    decisions = []
    for record in records:
        if (record.fixture_id != state.fixture.fixture_id or
                record.region_code != view.selected_region or
                record.hazard != view.hazard):
            decisions.append(NarrowDecision(record.record_id, DECISION_UNKNOWN, "OUT_OF_SYNTHETIC_SCOPE"))
            continue
        if not record.observed_at <= now < record.expires_at:
            decisions.append(NarrowDecision(record.record_id, DECISION_UNKNOWN, "STALE_OR_FUTURE_SYNTHETIC_FACT"))
            continue
        facts = dict(record.conditions)
        missing = tuple(k for k in request.required_conditions if facts.get(k) is None)
        failed = tuple(k for k in request.required_conditions if facts.get(k) is False)
        if missing:
            decisions.append(NarrowDecision(record.record_id, DECISION_UNKNOWN,
                                            "SYNTHETIC_CONDITION_UNVERIFIED", missing, failed))
        elif failed:
            decisions.append(NarrowDecision(record.record_id, DECISION_NOT_MATCHED,
                                            "EXPLICIT_SYNTHETIC_NONMATCH", (), failed))
        else:
            decisions.append(NarrowDecision(record.record_id, DECISION_MATCH, "EXPLICIT_SYNTHETIC_MATCH"))
    matched = tuple(x.record_id for x in decisions if x.status == DECISION_MATCH)
    return NarrowReport(
        "EVALUATED_SYNTHETIC_ONLY", "NOT_REAL_WORLD_ELIGIBILITY",
        state.generation, tuple(decisions), matched,
    )
