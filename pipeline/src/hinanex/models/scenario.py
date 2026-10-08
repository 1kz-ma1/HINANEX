"""Additive, evidence-bound flood scenario contract; independent of legacy scores."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.models.assessment import CapabilityStatus, DiscoveryStatus


class FacilityScenarioStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"


class ScenarioJoinStatus(str, Enum):
    DIRECT_SAME_SOURCE = "DIRECT_SAME_SOURCE"
    UNVERIFIED = "UNVERIFIED"


class HazardFact(BaseModel):
    """Raw source value; never implicitly interpreted as disaster safety."""

    model_config = ConfigDict(extra="forbid")

    facility_id: str
    facility_name: str
    hazard_scope_raw: str
    source_semantics: str
    official_status_raw: str | None = None
    usable_floor_raw: str | None = None
    source_url: str
    source_record_trace: str | None = None
    join_status: ScenarioJoinStatus
    latitude: float | None = None
    longitude: float | None = None


class FacilityScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str
    status: FacilityScenarioStatus
    reason: str
    fact: HazardFact


class ScenarioRequirementAssessment(BaseModel):
    """Scenario-local requirement assessment; NOT a legacy 0-4 quality score."""

    model_config = ConfigDict(extra="forbid")

    requirement_code: str = "shelter_hazard_applicability"
    discovery_status: DiscoveryStatus
    record_count: int = Field(ge=0)
    directly_joined_count: int = Field(ge=0)
    raw_value_count: int = Field(ge=0)
    reason: str


class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    scenario_id: str = "flood_shelter_selection"
    scenario_name: str = "洪水時の避難候補探索"
    hazard: str = "flood"
    requirement_assessment: ScenarioRequirementAssessment
    status: CapabilityStatus
    facility_results: list[FacilityScenarioResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: datetime
