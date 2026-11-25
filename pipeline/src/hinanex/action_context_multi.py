"""Synthetic multi-hazard input integrity and review *gaps*, never decisions.

Experimental D-internal companion to action_context.py (#306).
No official-source acceptance, geo overlap, route/shelter recommendation,
cross-hazard suitability classification, networking or persistence.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.hinanex.action_context import (
    ActionReview, ActionSession, DrillFixture, HazardKind, PreEventContext,
    SessionMode, review_action_context, start_drill,
)


class CueAvailability(str, Enum):
    SYNTHETIC_PRESENT = "SYNTHETIC_PRESENT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    EXPLICITLY_MISSING = "EXPLICITLY_MISSING"


class CueReviewState(str, Enum):
    NOT_PROVIDED = "NOT_PROVIDED"
    SOURCE_UNAVAILABLE_IN_FIXTURE = "SOURCE_UNAVAILABLE_IN_FIXTURE"
    MISSING_IN_FIXTURE = "MISSING_IN_FIXTURE"
    EXPIRED_SYNTHETIC = "EXPIRED_SYNTHETIC"
    SYNTHETIC_ONLY_UNVERIFIED = "SYNTHETIC_ONLY_UNVERIFIED"


class SyntheticCue(BaseModel):
    """An *invented exercise checkpoint*, not source data or proof of safety.

    State SYNTHETIC_PRESENT requires time boundaries. It still NEVER
    authenticates a hazard, a safe route, a destination or an official order.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hazard: HazardKind
    category: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    availability: CueAvailability
    observed_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None
    fixture_kind: Literal["SYNTHETIC"] = "SYNTHETIC"

    @model_validator(mode="after")
    def check_time_metadata(self) -> "SyntheticCue":
        if self.availability is CueAvailability.SYNTHETIC_PRESENT:
            if self.observed_at is None or self.expires_at is None:
                raise ValueError("synthetic cue requires observed_at and expires_at")
            if self.expires_at <= self.observed_at:
                raise ValueError("cue expiry must follow observation")
        elif self.observed_at is not None or self.expires_at is not None:
            raise ValueError("unavailable cue cannot carry observation timestamps")
        return self


class MultiHazardFixture(BaseModel):
    """Single-region synthetic exercise with distinct hazards and cue keys."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fixture_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    fixture_kind: Literal["SYNTHETIC"] = "SYNTHETIC"
    region_code: str = Field(pattern=r"^[0-9]{5}$")
    hazards: tuple[HazardKind, ...] = Field(min_length=1, max_length=5)
    simulated_at: AwareDatetime
    cues: tuple[SyntheticCue, ...] = ()

    @model_validator(mode="after")
    def check_cues(self) -> "MultiHazardFixture":
        if len(set(self.hazards)) != len(self.hazards):
            raise ValueError("duplicate hazards in one fixture")
        seen: set[tuple[HazardKind, str]] = set()
        for cue in self.cues:
            if cue.hazard not in self.hazards:
                raise ValueError("cue hazard is outside fixture hazard set")
            key = (cue.hazard, cue.category)
            if key in seen:
                raise ValueError("duplicate cue key")
            seen.add(key)
            if cue.observed_at is not None and cue.observed_at > self.simulated_at:
                raise ValueError("cue observed after simulated event")
            # The Phase-0 category list is an evidence *request*, never a
            # certified official semantic mapping.
            valid = _evidence_categories(
                cue.hazard, self.region_code, self.fixture_id, self.simulated_at
            )
            if cue.category not in valid:
                raise ValueError("cue category outside declared action review")
        return self


class MultiHazardDrill(BaseModel):
    """A separate DRILL-only session; impossible to pass as a LIVE incident."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: Literal["DRILL"] = "DRILL"
    prepared: PreEventContext = Field(default_factory=PreEventContext)
    fixture: MultiHazardFixture

    @model_validator(mode="after")
    def check_building_region(self) -> "MultiHazardDrill":
        # Invoke Phase-0 fail-closed regional validation, without bypassing it.
        first = DrillFixture(
            fixture_id=self.fixture.fixture_id,
            region_code=self.fixture.region_code,
            hazard=self.fixture.hazards[0],
            simulated_at=self.fixture.simulated_at,
        )
        start_drill(self.prepared, first)
        return self


class CueReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hazard: HazardKind
    category: str
    state: CueReviewState
    status: Literal["UNKNOWN"] = "UNKNOWN"


class ConflictReview(BaseModel):
    """A reason to inspect multiple hazards, NOT detected geographic danger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    hazards: tuple[HazardKind, ...]
    status: Literal["REQUIRES_INDEPENDENT_VERIFICATION"] = (
        "REQUIRES_INDEPENDENT_VERIFICATION"
    )


class MultiHazardActionReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["DRILL"] = "DRILL"
    fixture_id: str
    region_code: str
    hazards: tuple[HazardKind, ...]
    synthetic: Literal[True] = True
    official_event_verified: Literal[False] = False
    published_for_disaster_use: Literal[False] = False
    action_reviews: tuple[ActionReview, ...]
    cue_reviews: tuple[CueReview, ...]
    conflict_reviews: tuple[ConflictReview, ...]
    reason_codes: tuple[str, ...] = (
        "SIMULATED_NOT_CURRENT", "MULTI_HAZARD_NOT_ASSESSED"
    )


def _single_review(
    hazard: HazardKind, region: str, fixture_id: str, simulated_at: AwareDatetime,
) -> ActionReview:
    return review_action_context(start_drill(
        PreEventContext(),
        DrillFixture(
            fixture_id=fixture_id, region_code=region,
            hazard=hazard, simulated_at=simulated_at,
        ),
    ))


def _evidence_categories(
    hazard: HazardKind, region: str, fixture_id: str, simulated_at: AwareDatetime,
) -> set[str]:
    review = _single_review(hazard, region, fixture_id, simulated_at)
    return {name for item in review.options for name in item.evidence_to_check}


def start_multi_hazard_drill(
    prepared: PreEventContext, fixture: MultiHazardFixture,
) -> MultiHazardDrill:
    return MultiHazardDrill(prepared=prepared, fixture=fixture)


def stop_multi_hazard_drill(session: MultiHazardDrill) -> ActionSession:
    """Drop all cues and hazards; preserve only user-entered preparation."""
    return ActionSession(mode=SessionMode.NORMAL, prepared=session.prepared)


def replace_multi_hazard_fixture(
    session: MultiHazardDrill, fixture: MultiHazardFixture,
) -> MultiHazardDrill:
    """Atomic replacement; do not retain cues from the previous exercise."""
    return start_multi_hazard_drill(session.prepared, fixture)


def review_multi_hazard_drill(session: MultiHazardDrill) -> MultiHazardActionReview:
    """Compute missing/stale/synthetic-only states, never suitability."""
    fixture = session.fixture
    hazards = tuple(sorted(fixture.hazards, key=lambda hazard: hazard.value))
    reviews = tuple(
        _single_review(h, fixture.region_code, fixture.fixture_id, fixture.simulated_at)
        for h in hazards
    )
    index = {(cue.hazard, cue.category): cue for cue in fixture.cues}
    cues = []
    for review in reviews:
        categories = sorted({
            category
            for item in review.options for category in item.evidence_to_check
        })
        for category in categories:
            cue = index.get((review.hazard, category))
            if cue is None:
                state = CueReviewState.NOT_PROVIDED
            elif cue.availability is CueAvailability.SOURCE_UNAVAILABLE:
                state = CueReviewState.SOURCE_UNAVAILABLE_IN_FIXTURE
            elif cue.availability is CueAvailability.EXPLICITLY_MISSING:
                state = CueReviewState.MISSING_IN_FIXTURE
            elif cue.expires_at is not None and cue.expires_at <= fixture.simulated_at:
                state = CueReviewState.EXPIRED_SYNTHETIC
            else:
                state = CueReviewState.SYNTHETIC_ONLY_UNVERIFIED
            cues.append(CueReview(hazard=review.hazard, category=category, state=state))
    conflict_reviews = []
    if len(hazards) > 1:
        conflict_reviews.append(ConflictReview(
            code="INDEPENDENT_HAZARD_SCOPE_CHECK_REQUIRED", hazards=hazards,
        ))
    if HazardKind.LANDSLIDE in hazards and (
        HazardKind.FLOOD in hazards or HazardKind.TSUNAMI in hazards
    ):
        relevant = tuple(h for h in hazards if h in (
            HazardKind.FLOOD, HazardKind.LANDSLIDE, HazardKind.TSUNAMI
        ))
        conflict_reviews.append(ConflictReview(
            code="HIGH_GROUND_IS_NOT_PROOF_OF_CROSS_HAZARD_SAFETY",
            hazards=relevant,
        ))
    if HazardKind.FLOOD in hazards and HazardKind.STORM_SURGE in hazards:
        conflict_reviews.append(ConflictReview(
            code="INUNDATION_SOURCES_REQUIRE_SEPARATE_SCOPE_REVIEW",
            hazards=(HazardKind.FLOOD, HazardKind.STORM_SURGE),
        ))
    return MultiHazardActionReview(
        fixture_id=fixture.fixture_id, region_code=fixture.region_code,
        hazards=hazards, action_reviews=reviews,
        cue_reviews=tuple(cues), conflict_reviews=tuple(conflict_reviews),
    )
