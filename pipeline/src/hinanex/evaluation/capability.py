from datetime import datetime, timezone

from src.hinanex.models.assessment import (
    CapabilityStatus,
    DatasetAssessment,
    DiscoveryStatus,
)
from src.hinanex.models.capability import (
    CapabilityAssessment,
    CapabilityDefinition,
    CapabilityDependency,
    CapabilityDependencyResult,
    DependencyStatus,
)
from src.hinanex.models.common import Criticality


SHELTER_DISCOVERY = CapabilityDefinition(
    code="shelter_discovery",
    name="Shelter Discovery",
    disaster_type="all",
    dependencies=[
        CapabilityDependency(
            requirement_code="shelter_location",
            criticality=Criticality.CRITICAL,
            notes=(
                "避難施設を位置ベースで提示するために、"
                "施設名称と利用可能な位置情報が必要。"
            ),
        )
    ],
)


def _find_assessment(
    assessments: list[DatasetAssessment],
    requirement_code: str,
) -> DatasetAssessment | None:
    for assessment in assessments:
        if assessment.requirement_code == requirement_code:
            return assessment
    return None


def _assess_shelter_location_dependency(
    dependency: CapabilityDependency,
    assessment: DatasetAssessment | None,
) -> CapabilityDependencyResult:
    if assessment is None:
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.UNKNOWN,
            reasons=[
                "shelter_location の DatasetAssessment が存在しないため、"
                "Capability 可否を判定できません。"
            ],
        )

    if assessment.discovery_status == DiscoveryStatus.NOT_APPLICABLE:
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.NOT_APPLICABLE,
            reasons=["この DataRequirement は対象地域では非適用です。"],
        )

    if assessment.discovery_status == DiscoveryStatus.UNKNOWN:
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.UNKNOWN,
            reasons=[
                "データの存在・取得可否が未確認のため判定できません。"
            ],
        )

    if assessment.discovery_status in {
        DiscoveryStatus.NOT_FOUND,
        DiscoveryStatus.ACCESS_RESTRICTED,
        DiscoveryStatus.NOT_MACHINE_READABLE,
    }:
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.BLOCKED,
            reasons=[
                "HINANEX の現在の取得経路では shelter_location を"
                f"利用できません（{assessment.discovery_status.value}）。"
            ],
        )

    critical_metrics = {
        "completeness": assessment.data_quality.completeness.score,
        "validity": assessment.data_quality.validity.score,
        "geospatial_usability": (
            assessment.application_readiness.geospatial_usability.score
        ),
    }

    blocked_metrics = [
        name for name, score in critical_metrics.items() if score == 0
    ]
    if blocked_metrics:
        # A confirmed hard blocker is enough to decide BLOCKED even when a
        # different metric is unassessed. Example: no coordinates at all gives
        # Completeness=0 / GeospatialUsability=0 / Validity=None.
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.BLOCKED,
            reasons=[
                "Shelter Discovery に必要な評価軸が0点です: "
                + ", ".join(blocked_metrics)
            ],
        )

    unknown_metrics = [
        name for name, score in critical_metrics.items() if score is None
    ]
    if unknown_metrics:
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.UNKNOWN,
            reasons=[
                "Capability 判定に必要な評価軸が未評価です: "
                + ", ".join(unknown_metrics)
            ],
        )

    partial_metrics = [
        name for name, score in critical_metrics.items() if score is not None and score < 4
    ]

    if assessment.discovery_status == DiscoveryStatus.PARTIAL or partial_metrics:
        reasons = []
        if assessment.discovery_status == DiscoveryStatus.PARTIAL:
            reasons.append("データ取得状態が PARTIAL です。")
        if partial_metrics:
            reasons.append(
                "Shelter Discovery の必須評価軸が満点ではありません: "
                + ", ".join(partial_metrics)
            )
        return CapabilityDependencyResult(
            requirement_code=dependency.requirement_code,
            criticality=dependency.criticality,
            status=DependencyStatus.DEGRADED,
            reasons=reasons,
        )

    return CapabilityDependencyResult(
        requirement_code=dependency.requirement_code,
        criticality=dependency.criticality,
        status=DependencyStatus.READY,
        reasons=[
            "shelter_location の名称・位置情報が、"
            "Shelter Discovery に必要な条件を満たしています。"
        ],
    )


def _aggregate_status(
    results: list[CapabilityDependencyResult],
) -> CapabilityStatus:
    critical = [
        result
        for result in results
        if result.criticality == Criticality.CRITICAL
    ]
    important = [
        result
        for result in results
        if result.criticality == Criticality.IMPORTANT
    ]

    if any(result.status == DependencyStatus.BLOCKED for result in critical):
        return CapabilityStatus.BLOCKED

    if any(result.status == DependencyStatus.UNKNOWN for result in critical):
        return CapabilityStatus.UNKNOWN

    if critical and all(
        result.status == DependencyStatus.NOT_APPLICABLE for result in critical
    ):
        return CapabilityStatus.NOT_APPLICABLE

    if any(
        result.status in {DependencyStatus.DEGRADED, DependencyStatus.NOT_APPLICABLE}
        for result in critical
    ):
        return CapabilityStatus.DEGRADED

    if any(
        result.status
        in {
            DependencyStatus.BLOCKED,
            DependencyStatus.UNKNOWN,
            DependencyStatus.DEGRADED,
        }
        for result in important
    ):
        return CapabilityStatus.DEGRADED

    return CapabilityStatus.FULL


def assess_shelter_discovery(
    assessments: list[DatasetAssessment],
) -> CapabilityAssessment:
    """
    shelter_location の評価から Shelter Discovery Capability を判定する。

    v0.9では、shelter_location の
    - Completeness
    - Validity
    - Geospatial Usability
    を必須条件として使う。

    Machine Readability は自動取得・保守性には重要だが、
    現在保持している位置情報を用いた Shelter Discovery の可否そのものには
    直接使わない。
    """

    dependency = SHELTER_DISCOVERY.dependencies[0]
    assessment = _find_assessment(
        assessments,
        dependency.requirement_code,
    )

    result = _assess_shelter_location_dependency(
        dependency,
        assessment,
    )
    status = _aggregate_status([result])

    if assessment is not None:
        region_code = assessment.region_code
        region_name = assessment.region_name
    else:
        region_code = "UNKNOWN"
        region_name = "UNKNOWN"

    reasons = [
        reason
        for dependency_result in [result]
        for reason in dependency_result.reasons
    ]

    return CapabilityAssessment(
        region_code=region_code,
        region_name=region_name,
        capability_code=SHELTER_DISCOVERY.code,
        capability_name=SHELTER_DISCOVERY.name,
        status=status,
        dependency_results=[result],
        reasons=reasons,
        assessed_at=datetime.now(timezone.utc),
    )
