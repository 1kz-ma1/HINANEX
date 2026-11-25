"""Non-authoritative evacuation ACTION context foundation.

This is an independent, pure prototype. It cannot issue evacuation
instructions, classify building safety, or authenticate official information.
No RegionExport/Scenario schema, network access, or persistence is involved.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class SessionMode(str, Enum):
    NORMAL = "NORMAL"
    DRILL = "DRILL"


class HazardKind(str, Enum):
    FLOOD = "flood"
    LANDSLIDE = "landslide"
    TSUNAMI = "tsunami"
    STORM_SURGE = "storm_surge"
    EARTHQUAKE = "earthquake"


class ActionKind(str, Enum):
    VERIFY_OFFICIAL_INFORMATION = "VERIFY_OFFICIAL_INFORMATION"
    LEAVE_HAZARD_AREA = "LEAVE_HAZARD_AREA"
    INDOOR_SAFETY = "INDOOR_SAFETY"
    EMERGENCY_SAFETY = "EMERGENCY_SAFETY"


class PreEventContext(BaseModel):
    """Optional, self-reported hints. Caller owns consent/storage/deletion.

    No street address, GPS, names, health, age or emergency contact fields.
    Even populated fields never establish actual safety or suitability.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    region_code: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    occupied_floor: int | None = Field(default=None, ge=1, le=200)
    upper_floor_access: bool | None = None
    revision: int = Field(default=0, ge=0)


class DrillFixture(BaseModel):
    """Explicit synthetic disaster input; never a live alert."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fixture_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    fixture_kind: Literal["SYNTHETIC"] = "SYNTHETIC"
    region_code: str = Field(pattern=r"^[0-9]{5}$")
    hazard: HazardKind
    simulated_at: AwareDatetime


class ActionSession(BaseModel):
    """All transitions are explicit; NORMAL cannot carry drill data."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: SessionMode = SessionMode.NORMAL
    prepared: PreEventContext = Field(default_factory=PreEventContext)
    drill: DrillFixture | None = None

    @model_validator(mode="after")
    def check_context(self) -> "ActionSession":
        if self.mode is SessionMode.NORMAL:
            if self.drill is not None:
                raise ValueError("NORMAL cannot carry a DRILL fixture")
        elif self.drill is None:
            raise ValueError("DRILL requires an explicitly synthetic fixture")
        elif (
            self.prepared.region_code is not None
            and self.prepared.region_code != self.drill.region_code
            and (
                self.prepared.occupied_floor is not None
                or self.prepared.upper_floor_access is not None
            )
        ):
            # Old building inputs must never silently cross regional context.
            raise ValueError("cross-region building hints require explicit clearing")
        return self


class ActionReviewItem(BaseModel):
    """Unassessed alternative and evidence categories, not a recommendation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: ActionKind
    status: Literal["UNKNOWN"] = "UNKNOWN"
    evidence_to_check: tuple[str, ...]


class ActionReview(BaseModel):
    """Read-model for a future UI; intentionally exposes no profile values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: SessionMode
    region_code: str | None
    hazard: HazardKind | None
    fixture_id: str | None
    synthetic: bool
    official_event_verified: Literal[False] = False
    published_for_disaster_use: Literal[False] = False
    unverified_profile_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    options: tuple[ActionReviewItem, ...]


# Category IDs for future source/contract design, NOT sufficient conditions.
_ACTION_EVIDENCE: dict[ActionKind, tuple[str, ...]] = {
    ActionKind.VERIFY_OFFICIAL_INFORMATION: (
        "official_instructions", "source_freshness", "affected_area",
    ),
    ActionKind.LEAVE_HAZARD_AREA: (
        "official_instructions", "hazard_area", "destination_acceptance",
        "route_and_travel_feasibility", "available_time",
    ),
    ActionKind.INDOOR_SAFETY: (
        "official_instructions", "hazard_area", "building_exposure",
        "usable_space", "duration_and_resources",
    ),
    ActionKind.EMERGENCY_SAFETY: (
        "official_instructions", "immediate_exposure", "available_protection",
        "movement_risk",
    ),
}

_HAZARD_EVIDENCE: dict[HazardKind, tuple[str, ...]] = {
    HazardKind.FLOOD: ("flood_depth_duration", "house_collapse_zone"),
    HazardKind.LANDSLIDE: ("landslide_hazard_area", "slope_and_building_context"),
    HazardKind.TSUNAMI: ("tsunami_warning_and_designated_refuge",),
    HazardKind.STORM_SURGE: ("storm_surge_inundation_area",),
    HazardKind.EARTHQUAKE: ("earthquake_damage_and_secondary_hazards",),
}


def start_drill(prepared: PreEventContext, fixture: DrillFixture) -> ActionSession:
    """Fail closed when stale building hints belong to a different region."""
    return ActionSession(mode=SessionMode.DRILL, prepared=prepared, drill=fixture)


def stop_drill(session: ActionSession) -> ActionSession:
    """Do not carry a synthetic event back into normal operation."""
    return ActionSession(mode=SessionMode.NORMAL, prepared=session.prepared)


def replace_preparation(
    session: ActionSession, updated: PreEventContext,
) -> ActionSession:
    """Invalidate active drill to prevent stale cross-context comparisons."""
    return ActionSession(mode=SessionMode.NORMAL, prepared=updated)


def review_action_context(session: ActionSession) -> ActionReview:
    """Return only UNKNOWN options and explicit missing verification categories.

    No generated order indicates relative safety; no real event is ingested.
    Inputs reported by a user are *not* accepted as independent evidence.
    """
    fixture = session.drill
    hazard = fixture.hazard if fixture else None
    region = fixture.region_code if fixture else session.prepared.region_code
    supplied = tuple(
        name
        for name in ("region_code", "occupied_floor", "upper_floor_access")
        if getattr(session.prepared, name) is not None
    )
    extension = _HAZARD_EVIDENCE[hazard] if hazard else ()
    options = tuple(
        ActionReviewItem(
            action=kind,
            evidence_to_check=tuple(dict.fromkeys((*needed, *extension))),
        )
        for kind, needed in _ACTION_EVIDENCE.items()
    )
    return ActionReview(
        mode=session.mode,
        region_code=region,
        hazard=hazard,
        fixture_id=fixture.fixture_id if fixture else None,
        synthetic=fixture is not None,
        unverified_profile_fields=supplied,
        reason_codes=(
            ("SIMULATED_NOT_CURRENT", "NO_OFFICIAL_ASSESSMENT")
            if fixture else ("NO_CURRENT_EVENT", "NO_OFFICIAL_ASSESSMENT")
        ),
        options=options,
    )
