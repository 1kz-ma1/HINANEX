from copy import deepcopy
import unittest

from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.models.assessment import (
    ApplicationReadinessAssessment,
    CapabilityStatus,
    DataQualityAssessment,
    DatasetAssessment,
    DiscoveryStatus,
    MetricScore,
)
from src.hinanex.models.common import Criticality, DataRequirement


def metric(score: int | None, reason: str = "test") -> MetricScore:
    return MetricScore(score=score, reason=reason)


def full_assessment() -> DatasetAssessment:
    return DatasetAssessment(
        region_code="13123",
        region_name="東京都江戸川区",
        requirement_code="shelter_location",
        discovery_status=DiscoveryStatus.AVAILABLE,
        data_quality=DataQualityAssessment(
            completeness=metric(4),
            coverage=metric(None),
            timeliness=metric(None),
            validity=metric(4),
            consistency=metric(None),
            accuracy_confidence=metric(None),
            traceability=metric(None),
        ),
        application_readiness=ApplicationReadinessAssessment(
            discoverability=metric(None),
            accessibility=metric(None),
            machine_readability=metric(4),
            interoperability=metric(None),
            geospatial_usability=metric(4),
            update_automation=metric(None),
            reusability=metric(None),
            semantic_fitness=metric(None),
        ),
        record_count=152,
        findings=[],
        assessed_at="2026-09-27T00:00:00Z",
    )


class CapabilityTests(unittest.TestCase):
    def test_full_shelter_discovery(self) -> None:
        result = assess_shelter_discovery([full_assessment()])
        self.assertEqual(result.status, CapabilityStatus.FULL)
        self.assertTrue(any("位置ベース" in reason for reason in result.reasons))
        self.assertTrue(
            any("保証するものではありません" in reason for reason in result.reasons)
        )

    def test_partial_required_metric_degrades(self) -> None:
        assessment = full_assessment()
        assessment.data_quality.completeness = metric(3)

        result = assess_shelter_discovery([assessment])
        self.assertEqual(result.status, CapabilityStatus.DEGRADED)

    def test_zero_geospatial_blocks(self) -> None:
        assessment = full_assessment()
        assessment.application_readiness.geospatial_usability = metric(0)

        result = assess_shelter_discovery([assessment])
        self.assertEqual(result.status, CapabilityStatus.BLOCKED)


    def test_confirmed_zero_blocker_wins_over_unassessed_validity(self) -> None:
        assessment = full_assessment()
        assessment.data_quality.completeness = metric(0)
        assessment.data_quality.validity = metric(None)
        assessment.application_readiness.geospatial_usability = metric(0)

        result = assess_shelter_discovery([assessment])
        self.assertEqual(result.status, CapabilityStatus.BLOCKED)

    def test_unassessed_required_metric_is_unknown(self) -> None:
        assessment = full_assessment()
        assessment.data_quality.validity = metric(None)

        result = assess_shelter_discovery([assessment])
        self.assertEqual(result.status, CapabilityStatus.UNKNOWN)

    def test_missing_requirement_assessment_is_unknown(self) -> None:
        result = assess_shelter_discovery([])
        self.assertEqual(result.status, CapabilityStatus.UNKNOWN)

    def test_criticality_is_not_global_data_requirement_property(self) -> None:
        requirement = DataRequirement(
            code="shelter_location",
            name="避難所位置",
            disaster_type="all",
            required_fields=["name", "latitude", "longitude"],
        )
        self.assertEqual(requirement.code, "shelter_location")
        self.assertFalse(hasattr(requirement, "criticality"))
        self.assertEqual(Criticality.CRITICAL.value, 3)


if __name__ == "__main__":
    unittest.main()
