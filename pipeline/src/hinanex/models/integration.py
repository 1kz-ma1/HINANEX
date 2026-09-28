from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.hinanex.models.assessment import CapabilityStatus
from src.hinanex.models.export import RegionInfo
from src.hinanex.version import CONTRACT_SCHEMA_VERSION, MANIFEST_VERSION


class SourceManifestItem(BaseModel):
    """Cが根拠ソースを追跡するための最小サマリ。"""

    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_url: str | None = None
    publisher: str | None = None
    source_format: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime


class CapabilityManifestItem(BaseModel):
    """B/Cが地域ごとのCapability状態を一覧確認するためのサマリ。"""

    model_config = ConfigDict(extra="forbid")

    capability_code: str
    capability_name: str
    status: CapabilityStatus
    gap_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)


class RegionManifestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    region: RegionInfo
    contract_path: str
    dataset_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    requirement_codes: list[str] = Field(default_factory=list)
    sources: list[SourceManifestItem] = Field(default_factory=list)
    capabilities: list[CapabilityManifestItem] = Field(default_factory=list)


class ValidationManifest(BaseModel):
    """3地域の統合成果物がB/Cへ引き渡せることを示すmanifest。"""

    model_config = ConfigDict(extra="forbid")

    manifest_version: str = MANIFEST_VERSION
    contract_schema_version: str = CONTRACT_SCHEMA_VERSION
    generated_at: datetime
    all_valid: bool
    regions: list[RegionManifestItem] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
