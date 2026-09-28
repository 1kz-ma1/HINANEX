import unittest
from datetime import datetime, timezone

from src.hinanex.integration import (
    assert_valid_region_export,
    build_validation_manifest,
    validate_region_export,
)
from src.hinanex.models.assessment import (
    ApplicationReadinessAssessment,
    CapabilityStatus,
    DataQualityAssessment,
    DatasetAssessment,
    DiscoveryStatus,
    MetricScore,
)
from src.hinanex.models.capability import (
    CapabilityAssessment,
    CapabilityDependencyResult,
    DependencyStatus,
)
from src.hinanex.models.common import Criticality, Evidence, NormalizedDataset
from src.hinanex.models.export import ExportMeta, RegionExport, RegionInfo


NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)


def metric(score: int | None) -> MetricScore:
    return MetricScore(score=score, reason="test")


def make_export() -> RegionExport:
    dataset = NormalizedDataset(
        region_code="13123",
        region_name="東京都江戸川区",
        requirement_code="shelter_location",
        records=[
            {
                "id": "s1",
                "name": "Shelter A",
                "latitude": 35.7,
                "longitude": 139.8,
            }
        ],
        evidence=[
            Evidence(
                source_name="Official source",
                source_url="https://example.test/data.csv",
                publisher="Test publisher",
                fetched_at=NOW,
                source_format="CSV",
                retrieval_method="HTTP_DOWNLOAD",
            )
        ],
        normalized_at=NOW,
    )

    unknown = metric(None)
    assessment = DatasetAssessment(
        region_code="13123",
        region_name="東京都江戸川区",
        requirement_code="shelter_location",
        discovery_status=DiscoveryStatus.AVAILABLE,
        data_quality=DataQualityAssessment(
            completeness=metric(4),
            coverage=unknown,
            timeliness=unknown,
            validity=metric(4),
            consistency=unknown,
            accuracy_confidence=unknown,
            traceability=unknown,
        ),
        application_readiness=ApplicationReadinessAssessment(
            discoverability=unknown,
            accessibility=unknown,
            machine_readability=metric(4),
            interoperability=unknown,
            geospatial_usability=metric(4),
            update_automation=unknown,
            reusability=unknown,
            semantic_fitness=unknown,
        ),
        record_count=1,
        findings=[],
        assessed_at=NOW,
    )

    capability = CapabilityAssessment(
        region_code="13123",
        region_name="東京都江戸川区",
        capability_code="shelter_discovery",
        capability_name="Shelter Discovery",
        status=CapabilityStatus.FULL,
        dependency_results=[
            CapabilityDependencyResult(
                requirement_code="shelter_location",
                criticality=Criticality.CRITICAL,
                status=DependencyStatus.READY,
                reasons=["ready"],
            )
        ],
        reasons=["ready"],
        assessed_at=NOW,
    )

    return RegionExport(
        region=RegionInfo(code="13123", name="東京都江戸川区"),
        datasets=[dataset],
        assessments=[assessment],
        capabilities=[capability],
        gaps=[],
        recommendations=[],
        meta=ExportMeta(
            generated_at=NOW,
            dataset_count=1,
            assessment_count=1,
            capability_count=1,
            gap_count=0,
            recommendation_count=0,
            evidence_count=1,
        ),
    )


class IntegrationContractTests(unittest.TestCase):
    def test_valid_contract_passes_semantic_validation(self) -> None:
        export = make_export()
        self.assertEqual(validate_region_export(export, region_key="edogawa"), [])
        assert_valid_region_export(export, region_key="edogawa")

    def test_wrong_region_identity_is_rejected(self) -> None:
        export = make_export()
        export.region.name = "別地域"
        errors = validate_region_export(export, region_key="edogawa")
        self.assertTrue(any("region identity mismatch" in item for item in errors))

    def test_meta_count_mismatch_is_rejected(self) -> None:
        export = make_export()
        export.meta.dataset_count = 2
        errors = validate_region_export(export, region_key="edogawa")
        self.assertIn("meta.dataset_count does not match datasets length", errors)

    def test_dataset_without_assessment_is_rejected(self) -> None:
        export = make_export()
        export.assessments = []
        export.meta.assessment_count = 0
        errors = validate_region_export(export, region_key="edogawa")
        self.assertTrue(any("dataset without assessment" in item for item in errors))

    def test_manifest_summarizes_traceability(self) -> None:
        export = make_export()
        manifest = build_validation_manifest(
            {"edogawa": ("data/output/edogawa.json", export)}
        )
        self.assertTrue(manifest.all_valid)
        self.assertEqual(manifest.contract_schema_version, "0.9")
        self.assertEqual(manifest.regions[0].record_count, 1)
        self.assertEqual(
            manifest.regions[0].capabilities[0].status,
            CapabilityStatus.FULL,
        )
        self.assertEqual(manifest.regions[0].sources[0].source_format, "CSV")


if __name__ == "__main__":
    unittest.main()
