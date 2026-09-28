from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Criticality(IntEnum):
    """
    Capability と DataRequirement の依存関係における重要度。

    DataRequirement 自体の固定属性ではない。
    同じ DataRequirement でも Capability によって重要度は変わり得る。
    """

    SUPPLEMENTAL = 1
    IMPORTANT = 2
    CRITICAL = 3


class Evidence(BaseModel):
    """データや評価結果の根拠となる情報。"""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_url: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    license: str | None = None
    source_format: str | None = None
    retrieval_method: str | None = None
    notes: str | None = None


class DataRequirement(BaseModel):
    """
    HINANEX が分析・Capability 判定のために必要とする全国共通データ項目。

    criticality / required_for はここには持たせない。
    重要度は CapabilityDependency 側で定義する。
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    disaster_type: str
    description: str | None = None
    required_fields: list[str] = Field(default_factory=list)


class NormalizedDataset(BaseModel):
    """各データソースを HINANEX 共通形式へ正規化した結果。"""

    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    requirement_code: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    normalized_at: datetime


class PipelineResult(BaseModel):
    """パイプライン処理結果の共通コンテナ。"""

    model_config = ConfigDict(extra="forbid")

    region_code: str
    region_name: str
    datasets: list[NormalizedDataset] = Field(default_factory=list)
    generated_at: datetime
