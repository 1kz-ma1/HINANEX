from datetime import datetime, timezone

from src.hinanex.models.assessment import DatasetAssessment, DiscoveryStatus
from src.hinanex.models.capability import (
    CapabilityAssessment,
    CapabilityDependencyResult,
    DependencyStatus,
)
from src.hinanex.models.gap import (
    GapAnalysis,
    GapItem,
    GapKind,
    GapSeverity,
    Recommendation,
    RecommendationType,
)


def _find_assessment(
    assessments: list[DatasetAssessment],
    requirement_code: str,
) -> DatasetAssessment | None:
    for assessment in assessments:
        if assessment.requirement_code == requirement_code:
            return assessment
    return None


def _severity_for_dependency(
    dependency: CapabilityDependencyResult,
) -> GapSeverity:
    if dependency.status in {
        DependencyStatus.BLOCKED,
        DependencyStatus.UNKNOWN,
    }:
        return GapSeverity.HIGH

    if dependency.status == DependencyStatus.DEGRADED:
        return GapSeverity.MEDIUM

    return GapSeverity.LOW


def _classify_gap_kind(
    dependency: CapabilityDependencyResult,
    assessment: DatasetAssessment | None,
) -> GapKind:
    """改善候補と追加調査を分ける。

    原則:
    - 評価対象が取得でき、具体的な品質・利用性の不足を確認できた
      -> CONFIRMED_IMPROVEMENT
    - データの存在、取得可否、評価そのものが十分に確認できない
      -> INVESTIGATION

    NOT_FOUND は「HINANEXの現在の取得経路で見つからない」であって、
    自治体が公開していないという断定ではないため INVESTIGATION にする。
    """

    if assessment is None:
        return GapKind.INVESTIGATION

    if assessment.discovery_status in {
        DiscoveryStatus.UNKNOWN,
        DiscoveryStatus.NOT_FOUND,
        DiscoveryStatus.ACCESS_RESTRICTED,
    }:
        return GapKind.INVESTIGATION

    if dependency.status == DependencyStatus.UNKNOWN:
        return GapKind.INVESTIGATION

    return GapKind.CONFIRMED_IMPROVEMENT


def _gap_reason(
    dependency: CapabilityDependencyResult,
    assessment: DatasetAssessment | None,
    kind: GapKind,
) -> str:
    dependency_reason = (
        " ".join(dependency.reasons)
        if dependency.reasons
        else "Capability依存関係に不足があります。"
    )

    if kind == GapKind.INVESTIGATION:
        if assessment is None:
            return (
                f"{dependency.requirement_code} の評価結果が存在しないため、"
                "データの有無や利用可否を追加調査する必要があります。"
            )

        if assessment.discovery_status == DiscoveryStatus.NOT_FOUND:
            return (
                f"HINANEXの現在の取得経路では {dependency.requirement_code} を"
                "確認できませんでした。公開されていないとは断定せず、"
                "取得経路・公開ページ・別形式の有無を追加調査します。"
            )

        if assessment.discovery_status == DiscoveryStatus.ACCESS_RESTRICTED:
            return (
                f"{dependency.requirement_code} へのアクセス制約を確認しました。"
                "利用条件、別の公式取得経路、公開範囲を追加調査します。"
            )

        return (
            f"{dependency.requirement_code} の状態を十分に確定できません。"
            f" {dependency_reason}"
        )

    return (
        f"{dependency.requirement_code} は取得・評価できていますが、"
        f"Capability条件を十分に満たしていません。 {dependency_reason}"
    )


def _recommendation_for_gap(gap: GapItem) -> Recommendation:
    if gap.kind == GapKind.INVESTIGATION:
        return Recommendation(
            capability_code=gap.capability_code,
            requirement_code=gap.requirement_code,
            recommendation_type=RecommendationType.INVESTIGATE_DATA,
            priority=gap.severity,
            title=f"{gap.requirement_code} の取得・評価状況を追加調査する",
            actions=[
                "公式公開ページと現在の取得経路を再確認する。",
                "CSV・Excel・GeoJSON・PDFなど別形式の公式データ有無を確認する。",
                "確認できない場合も『未公開』とは断定せず、調査結果と取得経路を記録する。",
            ],
            rationale=gap.reason,
        )

    return Recommendation(
        capability_code=gap.capability_code,
        requirement_code=gap.requirement_code,
        recommendation_type=RecommendationType.IMPROVE_DATA,
        priority=gap.severity,
        title=f"{gap.requirement_code} のCapability利用性を改善する",
        actions=[
            "低下している評価軸と対象レコードを特定する。",
            "不足属性・無効値・位置情報など、確認済みの問題を改善候補として整理する。",
            "代替公式データで補完できる場合は統合方法を検討する。",
        ],
        rationale=gap.reason,
    )


def analyze_capability_gap(
    capability: CapabilityAssessment,
    assessments: list[DatasetAssessment],
) -> GapAnalysis:
    """Capability結果からGapとRecommendationを生成する最小エンジン。"""

    gaps: list[GapItem] = []

    for dependency in capability.dependency_results:
        if dependency.status in {
            DependencyStatus.READY,
            DependencyStatus.NOT_APPLICABLE,
        }:
            continue

        assessment = _find_assessment(
            assessments,
            dependency.requirement_code,
        )
        kind = _classify_gap_kind(dependency, assessment)
        severity = _severity_for_dependency(dependency)

        gaps.append(
            GapItem(
                capability_code=capability.capability_code,
                requirement_code=dependency.requirement_code,
                kind=kind,
                severity=severity,
                reason=_gap_reason(dependency, assessment, kind),
                capability_status=capability.status,
            )
        )

    recommendations = [_recommendation_for_gap(gap) for gap in gaps]

    if not gaps:
        summary = (
            f"{capability.capability_name} について、現在の判定ルールで"
            "対応が必要なData Gapは検出されませんでした。"
        )
    else:
        confirmed = sum(
            gap.kind == GapKind.CONFIRMED_IMPROVEMENT for gap in gaps
        )
        investigation = sum(
            gap.kind == GapKind.INVESTIGATION for gap in gaps
        )
        summary = (
            f"{capability.capability_name} で {len(gaps)}件のGapを検出。"
            f"確認済み改善候補 {confirmed}件、追加調査 {investigation}件です。"
        )

    return GapAnalysis(
        region_code=capability.region_code,
        region_name=capability.region_name,
        capability_code=capability.capability_code,
        capability_name=capability.capability_name,
        capability_status=capability.status,
        gaps=gaps,
        recommendations=recommendations,
        summary=summary,
        analyzed_at=datetime.now(timezone.utc),
    )
