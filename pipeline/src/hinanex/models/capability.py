from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.models.assessment import CapabilityStatus
from src.hinanex.models.common import Criticality
from src.hinanex.version import CAPABILITY_ENGINE_VERSION


class DependencyStatus(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CapabilityDependency(BaseModel):
    """Capability と DataRequirement の依存関係。"""

    model_config = ConfigDict(extra="forbid")

    requirement_code: str
    criticality: Criticality
    notes: str | None = None


class CapabilityDefinition(BaseModel):
    """HINANEX が提供できる分析・支援能力の定義。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    disaster_type: str
    dependencies: list[CapabilityDependency] = Field(default_factory=list)


class CapabilityDependencyResult(BaseModel):
    """1つの依存 DataRequirement の Capability 向け判定。"""

    model_config = ConfigDict(extra="forbid")

    requirement_code: str
    criticality: Criticality
    status: DependencyStatus
    reasons: list[str] = Field(default_factory=list)


class CapabilityAssessment(BaseModel):
    """1地域における1 Capability の判定結果。"""

    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    capability_code: str
    capability_name: str
    status: CapabilityStatus
    dependency_results: list[CapabilityDependencyResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    assessed_at: datetime
    engine_version: str = CAPABILITY_ENGINE_VERSION
