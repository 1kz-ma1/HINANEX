from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.models.assessment import CapabilityStatus
from src.hinanex.version import GAP_ENGINE_VERSION


class GapKind(str, Enum):
    """Gapの扱い方。

    CONFIRMED_IMPROVEMENT:
        不足・品質低下を十分に確認できており、改善候補として扱える。

    INVESTIGATION:
        データの存在・取得可否・評価状態が十分に確認できず、
        追加調査を優先する。自治体側の不足とは断定しない。
    """

    CONFIRMED_IMPROVEMENT = "CONFIRMED_IMPROVEMENT"
    INVESTIGATION = "INVESTIGATION"


class GapSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationType(str, Enum):
    IMPROVE_DATA = "IMPROVE_DATA"
    INVESTIGATE_DATA = "INVESTIGATE_DATA"


class GapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_code: str
    requirement_code: str
    kind: GapKind
    severity: GapSeverity
    reason: str
    capability_status: CapabilityStatus


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_code: str
    requirement_code: str
    recommendation_type: RecommendationType
    priority: GapSeverity
    title: str
    actions: list[str] = Field(default_factory=list)
    rationale: str


class GapAnalysis(BaseModel):
    """1 Capability に対する Gap / Recommendation 出力。"""

    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    capability_code: str
    capability_name: str
    capability_status: CapabilityStatus
    gaps: list[GapItem] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str
    analyzed_at: datetime
    engine_version: str = GAP_ENGINE_VERSION
