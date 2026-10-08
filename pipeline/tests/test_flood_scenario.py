"""Deterministic Scenario tests; no municipal network requests."""
from datetime import datetime, timezone
from io import BytesIO
import json
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from src.hinanex.adapters.nagoya_shelter import NagoyaShelterAdapter
from src.hinanex.adapters.niigata_shelter import NiigataShelterAdapter
from src.hinanex.flood_scenario import evaluate_flood_scenario
from src.hinanex.models.assessment import CapabilityStatus, DiscoveryStatus
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.scenario import FacilityScenarioStatus, ScenarioJoinStatus
from src.hinanex.scenario_sources import edogawa_facts, nagoya_facts, niigata_facts


class FloodScenarioTests(unittest.TestCase):
    @staticmethod
    def niigata_fixture():
        df = pd.DataFrame([
            {"ID": "A", "名称": "A", "緯度": 37.9, "経度": 139.0, "災害種別_洪水": "○"},
            {"ID": "B", "名称": "B", "緯度": 37.9, "経度": 139.1, "災害種別_洪水": "×"},
            {"ID": "C", "名称": "C", "緯度": 37.9, "経度": 139.2, "災害種別_洪水": "－"},
        ])
        raw = df.to_csv(index=False).encode("utf-8-sig")
        dataset = NiigataShelterAdapter().normalize(raw)
        return dataset, raw

    def test_niigata_same_row_preserves_raw_and_unknown(self):
        dataset, raw = self.niigata_fixture()
        facts = niigata_facts(dataset, raw)
        scenario = evaluate_flood_scenario(dataset, facts)
        self.assertEqual([item.status for item in scenario.facility_results], [
            FacilityScenarioStatus.CANDIDATE,
            FacilityScenarioStatus.EXCLUDED,
            FacilityScenarioStatus.UNKNOWN,
        ])
        self.assertEqual([item.fact.official_status_raw for item in scenario.facility_results], ["○", "×", "－"])
        self.assertEqual(facts[0].join_status, ScenarioJoinStatus.DIRECT_SAME_SOURCE)
        self.assertEqual(facts[0].source_record_trace, "csv_row=2")
        self.assertEqual(scenario.status, CapabilityStatus.DEGRADED)
        self.assertEqual(scenario.requirement_assessment.discovery_status, DiscoveryStatus.AVAILABLE)
        self.assertEqual(scenario.requirement_assessment.raw_value_count, 3)

    def test_niigata_raw_floor_conditions_preserved_without_premature_classification(self):
        """C raw histogram contains floor wording; preserve it, not eligibility."""
        raw_values = ["○", "×", "2階以上", "3階以上", "全階可", "－"]
        df = pd.DataFrame([
            {
                "ID": f"floor-{index}", "名称": f"施設{index}",
                "緯度": 37.9, "経度": 139.0 + index / 100,
                "災害種別_洪水": marker,
            }
            for index, marker in enumerate(raw_values)
        ])
        raw = df.to_csv(index=False).encode("utf-8-sig")
        dataset = NiigataShelterAdapter().normalize(raw)
        facts = niigata_facts(dataset, raw)
        self.assertEqual([fact.usable_floor_raw for fact in facts],
                         [None, None, "2階以上", "3階以上", "全階可", None])
        scenario = evaluate_flood_scenario(dataset, facts)
        self.assertEqual([item.status for item in scenario.facility_results], [
            FacilityScenarioStatus.CANDIDATE,
            FacilityScenarioStatus.EXCLUDED,
            FacilityScenarioStatus.UNKNOWN,
            FacilityScenarioStatus.UNKNOWN,
            FacilityScenarioStatus.UNKNOWN,
            FacilityScenarioStatus.UNKNOWN,
        ])
        for item in scenario.facility_results[2:5]:
            self.assertEqual(item.fact.usable_floor_raw, item.fact.official_status_raw)
            self.assertIn("階", item.reason)
            self.assertIn("条件", item.reason)
        self.assertEqual(scenario.status, CapabilityStatus.DEGRADED)
        reloaded = type(scenario).model_validate_json(scenario.model_dump_json())
        self.assertEqual([item.fact.usable_floor_raw for item in reloaded.facility_results],
                         [None, None, "2階以上", "3階以上", "全階可", None])

    def test_niigata_source_mismatch_fails_closed(self):
        dataset, raw = self.niigata_fixture()
        dataset.records[0]["id"] = "spoofed"
        with self.assertRaisesRegex(ValueError, "same-source facility IDs differ"):
            niigata_facts(dataset, raw)

    def test_nagoya_combined_flood_inland_never_becomes_flood_only_candidate(self):
        table = pd.DataFrame([
            ["学区", "番号", "施設名称", "所在地", "指定緊急避難場所", None, "指定避難所"],
            [None, None, None, None, "洪水 内水", "高潮", None],
            ["千種", "ア1", "千種小学校", "千種3-2-5", "②", "－", "○"],
        ])
        excel = BytesIO()
        with pd.ExcelWriter(excel, engine="openpyxl") as writer:
            table.to_excel(writer, index=False, header=False)
        manifest = [{"ward": "千種区", "url": "https://example.test/chikusa.xlsx", "filename": "chikusa.xlsx"}]
        raw = BytesIO()
        with ZipFile(raw, "w", compression=ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
            zf.writestr("chikusa.xlsx", excel.getvalue())
        dataset = NagoyaShelterAdapter().normalize(raw.getvalue())
        facts = nagoya_facts(dataset, raw.getvalue())
        scenario = evaluate_flood_scenario(dataset, facts)
        self.assertEqual(len(scenario.facility_results), 1)
        self.assertEqual(scenario.facility_results[0].status, FacilityScenarioStatus.UNKNOWN)
        self.assertEqual(facts[0].official_status_raw, "②")
        self.assertEqual(facts[0].usable_floor_raw, "②")
        self.assertEqual(facts[0].hazard_scope_raw, "洪水・内水")
        self.assertIn("excel_row=3", facts[0].source_record_trace)
        self.assertEqual(scenario.status, CapabilityStatus.UNKNOWN)

    def test_edogawa_unverified_join_is_unknown_not_excluded(self):
        dataset = NormalizedDataset(
            region_code="13123", region_name="東京都江戸川区",
            requirement_code="shelter_location",
            records=[{"id": "edogawa-test", "name": "テスト避難所", "latitude": 35.7, "longitude": 139.8}],
            evidence=[],
            normalized_at=datetime.now(timezone.utc),
        )
        facts = edogawa_facts(dataset)
        scenario = evaluate_flood_scenario(dataset, facts)
        self.assertEqual(facts[0].join_status, ScenarioJoinStatus.UNVERIFIED)
        self.assertIsNone(facts[0].official_status_raw)
        self.assertEqual(scenario.facility_results[0].status, FacilityScenarioStatus.UNKNOWN)
        self.assertEqual(scenario.status, CapabilityStatus.UNKNOWN)
        self.assertEqual(scenario.requirement_assessment.discovery_status, DiscoveryStatus.PARTIAL)

    def test_duplicate_or_missing_location_reference_is_rejected(self):
        dataset, raw = self.niigata_fixture()
        facts = niigata_facts(dataset, raw)
        with self.assertRaisesRegex(ValueError, "exact location IDs"):
            evaluate_flood_scenario(dataset, facts[:2])


if __name__ == "__main__":
    unittest.main()
