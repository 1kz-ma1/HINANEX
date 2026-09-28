from datetime import datetime, timezone
from typing import Any

from src.hinanex.models.assessment import (
    ApplicationReadinessAssessment,
    DataQualityAssessment,
    DatasetAssessment,
    DiscoveryStatus,
    MetricScore,
)
from src.hinanex.models.common import NormalizedDataset


def _unassessed(reason: str) -> MetricScore:
    return MetricScore(score=None, reason=reason)


def _score_ratio(
    ratio: float,
    *,
    perfect_reason: str,
    partial_reason: str,
) -> MetricScore:
    """
    Temporary v0.3 ratio-to-score rule.

    4 = 100%
    3 = >=95%
    2 = >=80%
    1 = >0%
    0 = 0%

    Thresholds are intentionally isolated here so they can be revised
    after validation against Nagoya / Niigata and later unseen regions.
    """

    if ratio >= 1.0:
        return MetricScore(score=4, reason=perfect_reason)

    if ratio >= 0.95:
        score = 3
    elif ratio >= 0.80:
        score = 2
    elif ratio > 0:
        score = 1
    else:
        score = 0

    return MetricScore(score=score, reason=partial_reason)


def _is_number(value: Any) -> bool:
    # bool is a subclass of int, but must not be accepted as a coordinate.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_valid_coordinate(latitude: Any, longitude: Any) -> bool:
    return (
        _is_number(latitude)
        and _is_number(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _machine_readability(dataset: NormalizedDataset) -> MetricScore:
    formats = {
        evidence.source_format.strip().upper()
        for evidence in dataset.evidence
        if evidence.source_format and evidence.source_format.strip()
    }
    methods = {
        evidence.retrieval_method.strip().upper()
        for evidence in dataset.evidence
        if evidence.retrieval_method and evidence.retrieval_method.strip()
    }

    machine_formats = {
        "CSV",
        "JSON",
        "GEOJSON",
        "XLSX",
        "XLS",
        "SHAPEFILE",
        "PARQUET",
    }

    if formats & machine_formats and methods:
        return MetricScore(
            score=4,
            reason=(
                "元データ形式と取得方法がEvidenceに記録され、"
                "自動取得・解析・共通Schemaへの正規化に成功しています。"
            ),
        )

    return _unassessed(
        "元データ形式または取得方法のEvidenceが不足しているため、"
        "Machine Readabilityは未評価です。"
    )


def assess_shelter_location(
    dataset: NormalizedDataset,
) -> DatasetAssessment:
    """
    Assess only the `shelter_location` DataRequirement.

    This evaluator intentionally does NOT penalize missing capacity,
    accessibility, or supported-disaster attributes. Those belong to
    separate DataRequirements and will be assessed independently.
    """

    if dataset.requirement_code != "shelter_location":
        raise ValueError(
            "shelter_location以外のDatasetはこの評価器では評価できません"
        )

    total = len(dataset.records)

    if total == 0:
        return DatasetAssessment(
            region_code=dataset.region_code,
            region_name=dataset.region_name,
            requirement_code=dataset.requirement_code,
            discovery_status=DiscoveryStatus.AVAILABLE,
            data_quality=DataQualityAssessment(
                completeness=MetricScore(
                    score=0,
                    reason="取得・正規化されたレコードが0件です。",
                ),
                coverage=_unassessed(
                    "地域内の全対象施設数という比較母数が未定義のため未評価です。"
                ),
                timeliness=_unassessed(
                    "shelter_location用の鮮度閾値が未確定のため未評価です。"
                ),
                validity=_unassessed(
                    "対象レコードがないため妥当性を評価できません。"
                ),
                consistency=_unassessed(
                    "複数ソース間の比較ルールが未確定のため未評価です。"
                ),
                accuracy_confidence=_unassessed(
                    "現地・別ソースとの照合を行っていないため未評価です。"
                ),
                traceability=_unassessed(
                    "Traceability評価ルールは次段階で実装します。"
                ),
            ),
            application_readiness=ApplicationReadinessAssessment(
                discoverability=_unassessed(
                    "Discoverability評価ルールは次段階で実装します。"
                ),
                accessibility=_unassessed(
                    "Accessibility評価ルールは次段階で実装します。"
                ),
                machine_readability=_machine_readability(dataset),
                interoperability=_unassessed(
                    "Interoperability評価ルールは次段階で実装します。"
                ),
                geospatial_usability=_unassessed(
                    "位置レコードがないため評価できません。"
                ),
                update_automation=_unassessed(
                    "更新検知・自動追従ルールは次段階で実装します。"
                ),
                reusability=_unassessed(
                    "Reusability評価ルールは次段階で実装します。"
                ),
                semantic_fitness=_unassessed(
                    "Semantic Fitness評価ルールは次段階で実装します。"
                ),
            ),
            record_count=0,
            findings=[
                "データセットは取得できましたが、正規化レコードが0件です。"
            ],
            assessed_at=datetime.now(timezone.utc),
        )

    required_complete = 0
    validity_sample_count = 0
    structurally_valid = 0
    geospatial_valid = 0
    duplicate_ids = 0
    seen_ids: set[str] = set()

    for record in dataset.records:
        record_id = record.get("id")
        name = record.get("name")
        latitude = record.get("latitude")
        longitude = record.get("longitude")

        # Completeness asks whether the requirement fields exist.
        # Validity asks whether values that are complete enough to validate are
        # structurally/range-valid. Missing values are therefore NOT counted as
        # invalid values; they are handled by Completeness/Geospatial Usability.
        complete_for_location = (
            isinstance(name, str)
            and bool(name.strip())
            and latitude is not None
            and longitude is not None
        )

        if complete_for_location:
            required_complete += 1
            validity_sample_count += 1

            id_valid = isinstance(record_id, str) and bool(record_id.strip())
            name_valid = isinstance(name, str) and bool(name.strip())
            coordinate_valid = _is_valid_coordinate(latitude, longitude)

            if id_valid and name_valid and coordinate_valid:
                structurally_valid += 1
        else:
            coordinate_valid = _is_valid_coordinate(latitude, longitude)

        if coordinate_valid:
            geospatial_valid += 1

        if isinstance(record_id, str) and record_id.strip():
            if record_id in seen_ids:
                duplicate_ids += 1
            else:
                seen_ids.add(record_id)

    completeness_ratio = required_complete / total
    geospatial_ratio = geospatial_valid / total

    completeness = _score_ratio(
        completeness_ratio,
        perfect_reason=(
            f"{total}/{total}件でshelter_locationに必要な"
            "名称・緯度・経度が揃っています。"
        ),
        partial_reason=(
            f"{required_complete}/{total}件でshelter_locationに必要な"
            "名称・緯度・経度が揃っています。"
        ),
    )

    if validity_sample_count == 0:
        validity = _unassessed(
            "名称・緯度・経度が揃ったレコードがないため、"
            "値の妥当性は評価できません。欠損はCompletenessと"
            "Geospatial Usabilityで評価します。"
        )
    else:
        validity_ratio = structurally_valid / validity_sample_count
        validity = _score_ratio(
            validity_ratio,
            perfect_reason=(
                f"評価可能な{validity_sample_count}/{validity_sample_count}件で"
                "ID・名称・緯度経度の基本的な構造/範囲妥当性を確認しました。"
                "実在性や座標の地理的正確性までは意味しません。"
            ),
            partial_reason=(
                f"評価可能な{validity_sample_count}件中{structurally_valid}件が"
                "ID・名称・緯度経度の基本的な構造/範囲チェックを通過しました。"
            ),
        )

    geospatial = _score_ratio(
        geospatial_ratio,
        perfect_reason=(
            f"{total}/{total}件に有効範囲の緯度経度があり、"
            "位置ベースの処理に利用できます。"
        ),
        partial_reason=(
            f"{geospatial_valid}/{total}件に有効範囲の緯度経度があります。"
        ),
    )

    findings: list[str] = []

    if duplicate_ids:
        findings.append(f"重複IDを{duplicate_ids}件検出しました。")

    if required_complete != total:
        findings.append(
            "shelter_locationの必須項目（名称・緯度・経度）が"
            "欠けているレコードがあります。"
        )

    if validity_sample_count == 0:
        findings.append(
            "名称・緯度・経度が揃ったレコードがないため、Validityは未評価です。"
        )
    elif structurally_valid != validity_sample_count:
        findings.append(
            "評価可能なレコードのうち、ID・名称・緯度経度の基本的な"
            "妥当性チェックを通過しないレコードがあります。"
        )

    if not findings:
        findings.append(
            "shelter_locationの必須項目について重大な構造上の問題は"
            "検出されませんでした。"
        )

    return DatasetAssessment(
        region_code=dataset.region_code,
        region_name=dataset.region_name,
        requirement_code=dataset.requirement_code,
        discovery_status=DiscoveryStatus.AVAILABLE,
        data_quality=DataQualityAssessment(
            completeness=completeness,
            coverage=_unassessed(
                "地域内の全対象施設数という比較母数が未定義のため未評価です。"
            ),
            timeliness=_unassessed(
                "shelter_location用の鮮度閾値が未確定のため未評価です。"
            ),
            validity=validity,
            consistency=_unassessed(
                "複数ソース間の比較ルールが未確定のため未評価です。"
            ),
            accuracy_confidence=_unassessed(
                "別ソースや現地情報との照合を行っていないため未評価です。"
            ),
            traceability=_unassessed(
                "Traceability評価ルールは次段階で実装します。"
            ),
        ),
        application_readiness=ApplicationReadinessAssessment(
            discoverability=_unassessed(
                "Discoverability評価ルールは次段階で実装します。"
            ),
            accessibility=_unassessed(
                "Accessibility評価ルールは次段階で実装します。"
            ),
            machine_readability=_machine_readability(dataset),
            interoperability=_unassessed(
                "Interoperability評価ルールは次段階で実装します。"
            ),
            geospatial_usability=geospatial,
            update_automation=_unassessed(
                "更新検知・自動追従ルールは次段階で実装します。"
            ),
            reusability=_unassessed(
                "Reusability評価ルールは次段階で実装します。"
            ),
            semantic_fitness=_unassessed(
                "Semantic Fitness評価ルールは次段階で実装します。"
            ),
        ),
        record_count=total,
        findings=findings,
        assessed_at=datetime.now(timezone.utc),
    )
