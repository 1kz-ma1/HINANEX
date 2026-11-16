"""S0 pure session boundary for *synthetic drills*, not a live hazard feed.

Private D-domain draft. No persistence, network, device geolocation, or change
to RegionExport/Scenario contracts. Callers must not treat NORMAL as LIVE or
an active synthetic drill as evidence of actual hazard/shelter suitability.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import re


SYNTHETIC_ONLY = "SYNTHETIC_TEST_ONLY"
DRILL_NOTICE = "訓練・模擬情報です。現在発生している災害、施設の開設や安全性を示しません。"
NORMAL_NOTICE = "通常モードです。現在の災害や避難所の開設状態を確認したものではありません。"

_REGION = re.compile(r"[0-9]{5}\Z")
_HAZARD = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
_FIXTURE_ID = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z")


def _validate_region(value: str) -> None:
    if not isinstance(value, str) or not _REGION.fullmatch(value):
        raise ValueError("region_code must be a five-digit municipal code")


def _validate_time(value: datetime, name: str) -> None:
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware")


class Mode(str, Enum):
    NORMAL = "NORMAL"  # NOT a claim of live data availability
    DRILL = "DRILL"


class Action(str, Enum):
    START_DRILL = "START_DRILL"
    STOP_DRILL = "STOP_DRILL"
    SELECT_REGION = "SELECT_REGION"
    SOURCE_FAILED = "SOURCE_FAILED"
    SET_PREFERRED_REGION = "SET_PREFERRED_REGION"
    CLEAR_PREFERRED_REGION = "CLEAR_PREFERRED_REGION"
    RESET = "RESET"


class StaleSessionError(ValueError):
    """A late response must not resurrect an older drill."""


@dataclass(frozen=True)
class SyntheticFixture:
    fixture_id: str
    region_code: str
    hazard: str
    observed_at: datetime
    expires_at: datetime
    source_authorization: str

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, str) or not _FIXTURE_ID.fullmatch(self.fixture_id):
            raise ValueError("fixture_id must be an explicit safe synthetic identifier")
        _validate_region(self.region_code)
        if not isinstance(self.hazard, str) or not _HAZARD.fullmatch(self.hazard):
            raise ValueError("hazard must be an explicit synthetic identifier")
        _validate_time(self.observed_at, "observed_at")
        _validate_time(self.expires_at, "expires_at")
        if self.expires_at <= self.observed_at:
            raise ValueError("fixture expires_at must follow observed_at")
        if self.source_authorization != SYNTHETIC_ONLY:
            raise ValueError("only explicitly synthetic fixture sources are accepted")


@dataclass(frozen=True)
class Session:
    mode: Mode = Mode.NORMAL
    selected_region: str | None = None
    preferred_region: str | None = None  # in-memory only, no storage side effect
    fixture: SyntheticFixture | None = None
    generation: int = 0
    reason: str = "INITIAL"

    def __post_init__(self) -> None:
        if self.selected_region is not None:
            _validate_region(self.selected_region)
        if self.preferred_region is not None:
            _validate_region(self.preferred_region)
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 0:
            raise ValueError("generation must be a nonnegative integer")
        if self.mode == Mode.NORMAL and self.fixture is not None:
            raise ValueError("NORMAL must not retain a synthetic fixture")
        if self.mode == Mode.DRILL and (
            self.fixture is None or self.selected_region != self.fixture.region_code
        ):
            raise ValueError("DRILL requires an exact region-matched fixture")
        if not isinstance(self.mode, Mode):
            raise ValueError("unsupported session mode")


@dataclass(frozen=True)
class Event:
    action: Action
    expected_generation: int
    region_code: str | None = None
    fixture: SyntheticFixture | None = None
    explicit_consent: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.action, Action):
            raise ValueError("unknown action")
        if (isinstance(self.expected_generation, bool)
                or not isinstance(self.expected_generation, int)
                or self.expected_generation < 0):
            raise ValueError("expected_generation must be a nonnegative integer")
        if self.region_code is not None:
            _validate_region(self.region_code)


@dataclass(frozen=True)
class SessionView:
    mode: Mode
    selected_region: str | None
    preferred_region: str | None
    fixture_id: str | None
    hazard: str | None
    source_authorization: str | None
    generation: int
    reason: str
    notice: str
    live_data_verified: bool = False


def safe_view(state: Session, now: datetime) -> SessionView:
    """Never expose stale fixture fields as an active drill, even before a reducer tick."""
    _validate_time(now, "now")
    active = (state.mode == Mode.DRILL and state.fixture is not None
              and state.fixture.observed_at <= now < state.fixture.expires_at)
    if not active:
        reason = "DRILL_EXPIRED_OR_NOT_YET_VALID" if state.mode == Mode.DRILL else state.reason
        return SessionView(
            mode=Mode.NORMAL, selected_region=state.selected_region,
            preferred_region=state.preferred_region, fixture_id=None, hazard=None,
            source_authorization=None, generation=state.generation,
            reason=reason, notice=NORMAL_NOTICE,
        )
    fixture = state.fixture
    return SessionView(
        mode=Mode.DRILL, selected_region=state.selected_region,
        preferred_region=state.preferred_region,
        fixture_id=fixture.fixture_id, hazard=fixture.hazard,
        source_authorization=fixture.source_authorization,
        generation=state.generation, reason=state.reason, notice=DRILL_NOTICE,
    )


def reduce_session(state: Session, event: Event, now: datetime) -> Session:
    """One explicit transition; stale events are rejected, old fixture never reused.

    Invalid/expired START fails closed to NORMAL. Region changes, failures,
    stops and resets always discard the old fixture. Every transition bumps
    generation; callers must compare expected_generation before applying
    delayed asynchronous responses.
    """
    _validate_time(now, "now")
    if event.expected_generation != state.generation:
        raise StaleSessionError("session generation changed; stale event refused")

    expired = (state.mode == Mode.DRILL and
               not (state.fixture.observed_at <= now < state.fixture.expires_at))
    current = replace(state, mode=Mode.NORMAL, fixture=None, reason="DRILL_EXPIRED") if expired else state
    generation = state.generation + 1

    if event.action == Action.START_DRILL:
        fixture = event.fixture
        if fixture is None or event.region_code is None:
            return replace(current, mode=Mode.NORMAL, fixture=None,
                           generation=generation, reason="DRILL_INPUT_MISSING")
        valid = (event.region_code == fixture.region_code
                 and fixture.observed_at <= now < fixture.expires_at)
        if not valid:
            return replace(current, mode=Mode.NORMAL, fixture=None,
                           generation=generation, reason="DRILL_INPUT_INVALID_OR_EXPIRED")
        return replace(current, mode=Mode.DRILL, selected_region=event.region_code,
                       fixture=fixture, generation=generation, reason="DRILL_STARTED")

    if event.action == Action.SELECT_REGION:
        if event.region_code is None:
            raise ValueError("SELECT_REGION requires an explicit region_code")
        return replace(current, mode=Mode.NORMAL, fixture=None,
                       selected_region=event.region_code, generation=generation,
                       reason="REGION_SELECTED_DRILL_CLEARED")

    if event.action == Action.STOP_DRILL:
        return replace(current, mode=Mode.NORMAL, fixture=None,
                       generation=generation, reason="DRILL_STOPPED")

    if event.action == Action.SOURCE_FAILED:
        return replace(current, mode=Mode.NORMAL, fixture=None,
                       generation=generation, reason="SOURCE_FAILED_DRILL_CLEARED")

    if event.action == Action.SET_PREFERRED_REGION:
        if event.region_code is None or event.explicit_consent is not True:
            return replace(current, mode=Mode.NORMAL, fixture=None,
                           generation=generation, reason="PREPARATION_NOT_CONSENTED")
        return replace(current, preferred_region=event.region_code,
                       generation=generation, reason="PREFERRED_REGION_IN_MEMORY_ONLY")

    if event.action == Action.CLEAR_PREFERRED_REGION:
        return replace(current, preferred_region=None, generation=generation,
                       reason="PREFERRED_REGION_CLEARED")

    if event.action == Action.RESET:
        return Session(generation=generation, reason="SESSION_RESET")

    raise ValueError("unsupported action")
