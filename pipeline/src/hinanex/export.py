import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from src.hinanex.models.assessment import DatasetAssessment
from src.hinanex.models.capability import CapabilityAssessment
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.export import ExportMeta, RegionExport, RegionInfo
from src.hinanex.models.gap import GapAnalysis
from src.hinanex.output import write_model_json


ModelT = TypeVar("ModelT", bound=BaseModel)


def _region_identity(model: BaseModel) -> tuple[str, str]:
    code = getattr(model, "region_code", None)
    name = getattr(model, "region_name", None)

    if not code or not name:
        raise ValueError(
            f"地域識別情報を持たないモデルです: {model.__class__.__name__}"
        )

    return str(code), str(name)


def _validate_single_region(models: list[BaseModel]) -> RegionInfo:
    if not models:
        raise ValueError("統合出力には少なくとも1つの地域データが必要です。")

    identities = {_region_identity(model) for model in models}

    if len(identities) != 1:
        detail = ", ".join(
            f"{code}:{name}" for code, name in sorted(identities)
        )
        raise ValueError(
            "複数地域の成果物が混在しています。"
            f" 1地域1JSONを維持してください: {detail}"
        )

    code, name = identities.pop()
    return RegionInfo(code=code, name=name)


def build_region_export(
    *,
    datasets: list[NormalizedDataset],
    assessments: list[DatasetAssessment],
    capabilities: list[CapabilityAssessment],
    gap_analyses: list[GapAnalysis],
) -> RegionExport:
    """各工程の成果物をB/C向けの1地域1JSONへ統合する。"""

    all_models: list[BaseModel] = [
        *datasets,
        *assessments,
        *capabilities,
        *gap_analyses,
    ]
    region = _validate_single_region(all_models)

    gaps = [
        gap
        for analysis in gap_analyses
        for gap in analysis.gaps
    ]
    recommendations = [
        recommendation
        for analysis in gap_analyses
        for recommendation in analysis.recommendations
    ]
    evidence_count = sum(
        len(dataset.evidence) for dataset in datasets
    )

    return RegionExport(
        region=region,
        datasets=datasets,
        assessments=assessments,
        capabilities=capabilities,
        gaps=gaps,
        recommendations=recommendations,
        meta=ExportMeta(
            generated_at=datetime.now(timezone.utc),
            dataset_count=len(datasets),
            assessment_count=len(assessments),
            capability_count=len(capabilities),
            gap_count=len(gaps),
            recommendation_count=len(recommendations),
            evidence_count=evidence_count,
        ),
    )


def _read_model(path: str | Path, model_class: type[ModelT]) -> ModelT:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    return model_class.model_validate(data)


def build_region_export_from_paths(
    *,
    dataset_paths: list[str | Path],
    assessment_paths: list[str | Path],
    capability_paths: list[str | Path],
    gap_paths: list[str | Path],
) -> RegionExport:
    """既存JSON成果物から統合契約を構築する。"""

    datasets = [
        _read_model(path, NormalizedDataset)
        for path in dataset_paths
    ]
    assessments = [
        _read_model(path, DatasetAssessment)
        for path in assessment_paths
    ]
    capabilities = [
        _read_model(path, CapabilityAssessment)
        for path in capability_paths
    ]
    gap_analyses = [
        _read_model(path, GapAnalysis)
        for path in gap_paths
    ]

    return build_region_export(
        datasets=datasets,
        assessments=assessments,
        capabilities=capabilities,
        gap_analyses=gap_analyses,
    )


def write_region_export_from_paths(
    *,
    output_path: str | Path,
    dataset_paths: list[str | Path],
    assessment_paths: list[str | Path],
    capability_paths: list[str | Path],
    gap_paths: list[str | Path],
) -> Path:
    export = build_region_export_from_paths(
        dataset_paths=dataset_paths,
        assessment_paths=assessment_paths,
        capability_paths=capability_paths,
        gap_paths=gap_paths,
    )
    return write_model_json(export, output_path)
