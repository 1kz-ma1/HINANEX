import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.hinanex.export import (
    build_region_export,
    build_region_export_from_paths,
)
from src.hinanex.models.assessment import (
    ApplicationReadinessAssessment,
    CapabilityStatus,
    DataQualityAssessment,
    DatasetAssessment,
    DiscoveryStatus,
    MetricScore,
)
from src.hinanex.models.capability import CapabilityAssessment
from src.hinanex.models.common import Evidence, NormalizedDataset
from src.hinanex.models.gap import (
    GapAnalysis,
    GapItem,
    GapKind,
    GapSeverity,
    Recommendation,
    RecommendationType,
)


NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)


def metric(score: int | None, reason: str = "test") -> MetricScore:
    return MetricScore(score=score, reason=reason)


def make_dataset(region_code: str = "13123") -> NormalizedDataset:
    return NormalizedDataset(
        region_code=region_code,
        region_name="東京都江戸川区" if region_code == "13123" else "別地域",
        requirement_code="shelter_location",
        records=[
            {
                "id": "s1",
                "name": "避難所A",
                "latitude": 35.0,
                "longitude": 139.0,
            }
        ],
        evidence=[
            Evidence(
                source_name="official",
                source_url="https://example.invalid/source.csv",
                fetched_at=NOW,
            )
        ],
        normalized_at=NOW,
    )


def make_assessment(region_code: str = "13123") -> DatasetAssessment:
    unknown = metric(None, "not assessed")
    return DatasetAssessment(
        region_code=region_code,
        region_name="東京都江戸川区" if region_code == "13123" else "別地域",
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
        findings=["test"],
        assessed_at=NOW,
    )


def make_capability(region_code: str = "13123") -> CapabilityAssessment:
    return CapabilityAssessment(
        region_code=region_code,
        region_name="東京都江戸川区" if region_code == "13123" else "別地域",
        capability_code="shelter_discovery",
        capability_name="Shelter Discovery",
        status=CapabilityStatus.DEGRADED,
        dependency_results=[],
        reasons=["test"],
        assessed_at=NOW,
    )


def make_gap(region_code: str = "13123") -> GapAnalysis:
    gap = GapItem(
        capability_code="shelter_discovery",
        requirement_code="shelter_location",
        kind=GapKind.CONFIRMED_IMPROVEMENT,
        severity=GapSeverity.MEDIUM,
        reason="座標の一部が不足しています。",
        capability_status=CapabilityStatus.DEGRADED,
    )
    recommendation = Recommendation(
        capability_code="shelter_discovery",
        requirement_code="shelter_location",
        recommendation_type=RecommendationType.IMPROVE_DATA,
        priority=GapSeverity.MEDIUM,
        title="機械可読な位置情報を補完する",
        actions=["緯度経度を共通項目として提供する。"],
        rationale="位置ベースの検索精度を改善するため。",
    )
    return GapAnalysis(
        region_code=region_code,
        region_name="東京都江戸川区" if region_code == "13123" else "別地域",
        capability_code="shelter_discovery",
        capability_name="Shelter Discovery",
        capability_status=CapabilityStatus.DEGRADED,
        gaps=[gap],
        recommendations=[recommendation],
        summary="1件のGapを検出しました。",
        analyzed_at=NOW,
    )


class RegionExportTests(unittest.TestCase):
    def test_builds_one_region_contract_and_flattens_gap_outputs(self):
        export = build_region_export(
            datasets=[make_dataset()],
            assessments=[make_assessment()],
            capabilities=[make_capability()],
            gap_analyses=[make_gap()],
        )

        self.assertEqual(export.region.code, "13123")
        self.assertEqual(export.meta.schema_version, "0.9")
        self.assertEqual(export.meta.dataset_count, 1)
        self.assertEqual(export.meta.gap_count, 1)
        self.assertEqual(export.meta.recommendation_count, 1)
        self.assertEqual(export.meta.evidence_count, 1)
        self.assertEqual(export.gaps[0].requirement_code, "shelter_location")

    def test_contract_has_stable_top_level_shape_for_ui(self):
        export = build_region_export(
            datasets=[make_dataset()],
            assessments=[make_assessment()],
            capabilities=[make_capability()],
            gap_analyses=[make_gap()],
        )

        payload = export.model_dump(mode="json")
        self.assertEqual(
            set(payload.keys()),
            {
                "region",
                "datasets",
                "assessments",
                "capabilities",
                "gaps",
                "recommendations",
                "scenarios",
                "meta",
            },
        )

    def test_rejects_mixed_regions(self):
        with self.assertRaisesRegex(ValueError, "複数地域"):
            build_region_export(
                datasets=[make_dataset("13123")],
                assessments=[make_assessment("15100")],
                capabilities=[make_capability("13123")],
                gap_analyses=[make_gap("13123")],
            )

    def test_rejects_empty_contract(self):
        with self.assertRaisesRegex(ValueError, "少なくとも1つ"):
            build_region_export(
                datasets=[],
                assessments=[],
                capabilities=[],
                gap_analyses=[],
            )

    def test_builds_from_existing_json_artifacts(self):
        dataset = make_dataset()
        assessment = make_assessment()
        capability = make_capability()
        gap = make_gap()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {}
            for name, model in {
                "dataset": dataset,
                "assessment": assessment,
                "capability": capability,
                "gap": gap,
            }.items():
                path = root / f"{name}.json"
                path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
                paths[name] = path

            export = build_region_export_from_paths(
                dataset_paths=[paths["dataset"]],
                assessment_paths=[paths["assessment"]],
                capability_paths=[paths["capability"]],
                gap_paths=[paths["gap"]],
            )

            json.loads(export.model_dump_json())
            self.assertEqual(export.region.name, "東京都江戸川区")
            self.assertEqual(len(export.recommendations), 1)


if __name__ == "__main__":
    unittest.main()
