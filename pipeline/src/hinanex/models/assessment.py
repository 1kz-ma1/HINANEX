from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.version import ASSESSMENT_ENGINE_VERSION


class DiscoveryStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    NOT_MACHINE_READABLE = "NOT_MACHINE_READABLE"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CapabilityStatus(str, Enum):
    FULL = "FULL"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MetricScore(BaseModel):
    """A 0-4 score. None means not assessed/unknown, not zero quality."""

    model_config = ConfigDict(extra="forbid")

    score: int | None = Field(default=None, ge=0, le=4)
    reason: str


class DataQualityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completeness: MetricScore
    coverage: MetricScore
    timeliness: MetricScore
    validity: MetricScore
    consistency: MetricScore
    accuracy_confidence: MetricScore
    traceability: MetricScore


class ApplicationReadinessAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discoverability: MetricScore
    accessibility: MetricScore
    machine_readability: MetricScore
    interoperability: MetricScore
    geospatial_usability: MetricScore
    update_automation: MetricScore
    reusability: MetricScore
    semantic_fitness: MetricScore


class DatasetAssessment(BaseModel):
    """Assessment result for one NormalizedDataset."""

    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    requirement_code: str
    discovery_status: DiscoveryStatus
    data_quality: DataQualityAssessment
    application_readiness: ApplicationReadinessAssessment
    record_count: int = Field(ge=0)
    findings: list[str] = Field(default_factory=list)
    assessed_at: datetime
    assessment_version: str = ASSESSMENT_ENGINE_VERSION
