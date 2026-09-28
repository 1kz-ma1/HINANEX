from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.models.assessment import DatasetAssessment
from src.hinanex.models.capability import CapabilityAssessment
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.gap import GapItem, Recommendation
from src.hinanex.version import CONTRACT_SCHEMA_VERSION


class RegionInfo(BaseModel):
    """B/Cへ渡す地域識別情報。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    name: str


class ExportMeta(BaseModel):
    """統合出力そのもののメタデータ。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = CONTRACT_SCHEMA_VERSION
    generated_at: datetime
    dataset_count: int = Field(ge=0)
    assessment_count: int = Field(ge=0)
    capability_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)


class RegionExport(BaseModel):
    """
    HINANEX B/C引き渡し用の1地域1JSON契約。

    Bは自治体固有の元形式を意識せず、このSchemaだけを読む。
    Cは requirement_code / capability_code と各reason/evidenceを辿り、
    Source -> Normalized -> Assessment -> Capability -> Gap -> Recommendation
    の判定根拠を確認できる。
    """

    model_config = ConfigDict(extra="forbid")

    region: RegionInfo
    datasets: list[NormalizedDataset] = Field(default_factory=list)
    assessments: list[DatasetAssessment] = Field(default_factory=list)
    capabilities: list[CapabilityAssessment] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    meta: ExportMeta
