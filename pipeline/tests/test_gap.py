import unittest

from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.evaluation.gap import analyze_capability_gap
from src.hinanex.models.assessment import (
    ApplicationReadinessAssessment,
    CapabilityStatus,
    DataQualityAssessment,
    DatasetAssessment,
    DiscoveryStatus,
    MetricScore,
)
from src.hinanex.models.gap import (
    GapKind,
    GapSeverity,
    RecommendationType,
)


def metric(score: int | None, reason: str = "test") -> MetricScore:
    return MetricScore(score=score, reason=reason)


def assessment(
    *,
    discovery_status: DiscoveryStatus = DiscoveryStatus.AVAILABLE,
    completeness: int | None = 4,
    validity: int | None = 4,
    geospatial: int | None = 4,
) -> DatasetAssessment:
    return DatasetAssessment(
        region_code="13123",
        region_name="東京都江戸川区",
        requirement_code="shelter_location",
        discovery_status=discovery_status,
        data_quality=DataQualityAssessment(
            completeness=metric(completeness),
            coverage=metric(None),
            timeliness=metric(None),
            validity=metric(validity),
            consistency=metric(None),
            accuracy_confidence=metric(None),
            traceability=metric(None),
        ),
        application_readiness=ApplicationReadinessAssessment(
            discoverability=metric(None),
            accessibility=metric(None),
            machine_readability=metric(4),
            interoperability=metric(None),
            geospatial_usability=metric(geospatial),
            update_automation=metric(None),
            reusability=metric(None),
            semantic_fitness=metric(None),
        ),
        record_count=152,
        findings=[],
        assessed_at="2026-09-27T00:00:00Z",
    )


class GapTests(unittest.TestCase):
    def test_full_capability_has_no_gap(self) -> None:
        dataset_assessment = assessment()
        capability = assess_shelter_discovery([dataset_assessment])
        result = analyze_capability_gap(capability, [dataset_assessment])

        self.assertEqual(capability.status, CapabilityStatus.FULL)
        self.assertEqual(result.gaps, [])
        self.assertEqual(result.recommendations, [])

    def test_degraded_confirmed_metric_creates_improvement_gap(self) -> None:
        dataset_assessment = assessment(completeness=3)
        capability = assess_shelter_discovery([dataset_assessment])
        result = analyze_capability_gap(capability, [dataset_assessment])

        self.assertEqual(capability.status, CapabilityStatus.DEGRADED)
        self.assertEqual(len(result.gaps), 1)
        self.assertEqual(
            result.gaps[0].kind,
            GapKind.CONFIRMED_IMPROVEMENT,
        )
        self.assertEqual(result.gaps[0].severity, GapSeverity.MEDIUM)
        self.assertEqual(
            result.recommendations[0].recommendation_type,
            RecommendationType.IMPROVE_DATA,
        )

    def test_blocked_confirmed_metric_creates_high_improvement_gap(self) -> None:
        dataset_assessment = assessment(geospatial=0)
        capability = assess_shelter_discovery([dataset_assessment])
        result = analyze_capability_gap(capability, [dataset_assessment])

        self.assertEqual(capability.status, CapabilityStatus.BLOCKED)
        self.assertEqual(result.gaps[0].kind, GapKind.CONFIRMED_IMPROVEMENT)
        self.assertEqual(result.gaps[0].severity, GapSeverity.HIGH)
        actions = result.recommendations[0].actions
        self.assertTrue(any("現在取得しているSource" in action for action in actions))
        self.assertTrue(any("別の公式データ" in action for action in actions))
        self.assertTrue(any("推定値を公式値として扱わない" in action for action in actions))

    def test_unknown_metric_creates_investigation_gap(self) -> None:
        dataset_assessment = assessment(validity=None)
        capability = assess_shelter_discovery([dataset_assessment])
        result = analyze_capability_gap(capability, [dataset_assessment])

        self.assertEqual(capability.status, CapabilityStatus.UNKNOWN)
        self.assertEqual(result.gaps[0].kind, GapKind.INVESTIGATION)
        self.assertEqual(
            result.recommendations[0].recommendation_type,
            RecommendationType.INVESTIGATE_DATA,
        )

    def test_not_found_is_investigation_not_publication_accusation(self) -> None:
        dataset_assessment = assessment(
            discovery_status=DiscoveryStatus.NOT_FOUND,
        )
        capability = assess_shelter_discovery([dataset_assessment])
        result = analyze_capability_gap(capability, [dataset_assessment])

        self.assertEqual(result.gaps[0].kind, GapKind.INVESTIGATION)
        self.assertIn("現在の取得経路", result.gaps[0].reason)
        self.assertIn("断定せず", result.gaps[0].reason)

    def test_missing_assessment_is_investigation_gap(self) -> None:
        capability = assess_shelter_discovery([])
        result = analyze_capability_gap(capability, [])

        self.assertEqual(capability.status, CapabilityStatus.UNKNOWN)
        self.assertEqual(result.gaps[0].kind, GapKind.INVESTIGATION)
        self.assertEqual(result.gaps[0].severity, GapSeverity.HIGH)


if __name__ == "__main__":
    unittest.main()
