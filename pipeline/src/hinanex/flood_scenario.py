"""Conservative Scenario evaluation, separate from Shelter Discovery 0.9."""
from datetime import datetime, timezone

from src.hinanex.models.assessment import CapabilityStatus, DiscoveryStatus
from src.hinanex.models.common import DataRequirement, NormalizedDataset
from src.hinanex.models.scenario import (
    FacilityScenarioResult, FacilityScenarioStatus, HazardFact,
    ScenarioJoinStatus, ScenarioRequirementAssessment, ScenarioResult,
)

SHELTER_HAZARD_APPLICABILITY = DataRequirement(
    code="shelter_hazard_applicability",
    name="施設単位の災害別公式適用情報",
    disaster_type="all",
    description=(
        "Source固有の災害範囲と公式生値を保持する。"
        "公式の指定・条件を安全/危険の保証に変換しない。"
    ),
    required_fields=[
        "facility_id", "hazard_scope_raw", "source_semantics",
        "official_status_raw", "source_url", "join_status",
        "source_record_trace",
    ],
)

POSITIVE_NIIGATA = {"1", "○", "〇", "true", "yes", "可", "有"}
NEGATIVE_NIIGATA = {"0", "×", "false"}


def _evaluate_fact(fact: HazardFact) -> FacilityScenarioResult:
    if fact.join_status != ScenarioJoinStatus.DIRECT_SAME_SOURCE:
        status = FacilityScenarioStatus.UNKNOWN
        reason = (
            "公式水害Sourceと現在のshelter_location間に確認済み共通IDがない。"
            "名称による推測joinを行っていない。水害を洪水単独指定とは扱わない。"
        )
    elif fact.hazard_scope_raw != "災害種別_洪水":
        status = FacilityScenarioStatus.UNKNOWN
        reason = (
            "公式の洪水・内水は結合列。洪水単独の指定可否には分解しない。"
            "座標がない場合も公式値を推測補完しない。"
        )
    elif fact.official_status_raw is None:
        status = FacilityScenarioStatus.UNKNOWN
        reason = "洪水の公式列の値が欠損・未確認である。"
    else:
        raw = fact.official_status_raw.strip().lower()
        if fact.usable_floor_raw is not None:
            status = FacilityScenarioStatus.UNKNOWN
            reason = (
                "公式CSVには利用階に関するraw表記があるが、"
                "ODS列での正式な災害適合性・条件付き利用意味の照合が未確定。"
                "階数条件を除去して無条件候補へ変換しない。"
            )
        elif raw in NEGATIVE_NIIGATA:
            status = FacilityScenarioStatus.EXCLUDED
            reason = (
                "同一公式CSV行の災害種別_洪水に明示的な非該当値がある。"
                "これは洪水時の安全性やリアルタイム開設状態の判定ではない。"
            )
        elif raw in POSITIVE_NIIGATA:
            if fact.latitude is not None and fact.longitude is not None:
                status = FacilityScenarioStatus.CANDIDATE
                reason = (
                    "同一公式CSV行に洪水の該当値と位置情報を確認。"
                    "候補であり安全・開設状況を保証しない。"
                )
            else:
                status = FacilityScenarioStatus.UNKNOWN
                reason = "洪水の該当値があるが、位置情報が不足している。"
        else:
            status = FacilityScenarioStatus.UNKNOWN
            reason = "公式列のraw値に確定した解釈ルールがなく、推測しない。"
    return FacilityScenarioResult(
        facility_id=fact.facility_id,
        status=status,
        reason=reason,
        fact=fact,
    )


def evaluate_flood_scenario(
    location: NormalizedDataset, facts: list[HazardFact],
) -> ScenarioResult:
    if location.requirement_code != "shelter_location":
        raise ValueError("flood scenario requires existing shelter_location")
    location_ids = [record["id"] for record in location.records]
    ids = [fact.facility_id for fact in facts]
    if len(ids) != len(location_ids) or len(set(ids)) != len(ids) or set(ids) != set(location_ids):
        raise ValueError("Scenario facts must represent exact location IDs, without duplicates")
    results = [_evaluate_fact(fact) for fact in facts]
    total = len(results)
    raw_count = sum(fact.official_status_raw is not None for fact in facts)
    direct_count = sum(fact.join_status == ScenarioJoinStatus.DIRECT_SAME_SOURCE for fact in facts)
    decided_count = sum(result.status != FacilityScenarioStatus.UNKNOWN for result in results)

    if direct_count == 0:
        discovery = DiscoveryStatus.PARTIAL
        assessment_reason = "公式Sourceは確認済みだが施設単位の確定joinはできていない。"
    elif raw_count == 0:
        discovery = DiscoveryStatus.UNKNOWN
        assessment_reason = "公式災害列の機械可読な値を取得できていない。"
    elif direct_count < total or raw_count < total:
        discovery = DiscoveryStatus.PARTIAL
        assessment_reason = "一部施設の公式値または同一Source joinが未確定。"
    else:
        discovery = DiscoveryStatus.AVAILABLE
        assessment_reason = "全施設に同一Sourceのhazard raw factを追跡できる。"

    if total == 0 or decided_count == 0:
        overall = CapabilityStatus.UNKNOWN
    elif decided_count < total:
        overall = CapabilityStatus.DEGRADED
    else:
        overall = CapabilityStatus.FULL

    reasons = [
        "Scenarioは公式の洪水関連情報と現在取得できる位置情報から"
        "候補を検討できるかを表す。安全や開設を保証しない。",
        f"判定可能 {decided_count}/{total}件。UNKNOWNはEXCLUDEDではない。",
    ]
    unknown = total - decided_count
    gaps = []
    recommendations = []
    if unknown:
        gaps.append(f"未確定の施設{unknown}件。現行Evidenceだけでは洪水候補か否かを確定できない。")
        if location.region_code == "13123":
            recommendations.append("公式水害待避施設とshelter_locationの共通ID/住所照合を調査する。曖昧joinは確定しない。")
        elif location.region_code == "23100":
            recommendations.append("洪水・内水の結合意味を維持し、公式の洪水単独判断根拠と位置情報の有無を調査する。")
        else:
            recommendations.append("公式CSVの未解釈raw markerを確認し、判断不能のまま記録する。")

    return ScenarioResult(
        region_code=location.region_code,
        region_name=location.region_name,
        requirement_assessment=ScenarioRequirementAssessment(
            discovery_status=discovery,
            record_count=total,
            directly_joined_count=direct_count,
            raw_value_count=raw_count,
            reason=assessment_reason,
        ),
        status=overall,
        facility_results=results,
        reasons=reasons,
        gaps=gaps,
        recommendations=recommendations,
        evaluated_at=datetime.now(timezone.utc),
    )
