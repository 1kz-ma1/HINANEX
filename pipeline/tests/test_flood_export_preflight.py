"""Synthetic-only offline tests for the D read-model RegionExport preflight."""
from datetime import timedelta
from hashlib import sha256
import json
import unittest

from src.hinanex.flood_export_preflight import (
    audit_export_bytes, select_from_region_export,
)
from src.hinanex.models.assessment import CapabilityStatus
from src.hinanex.models.export import ExportMeta, RegionExport, RegionInfo
from src.hinanex.models.scenario import FacilityScenarioStatus as Status
from tests.test_scenario_selection import synthetic_snapshot, TIME, SOURCES


def fixture():
    scenario, location = synthetic_snapshot()
    for item in scenario.facility_results:
        item.status = Status.UNKNOWN
    scenario.status = CapabilityStatus.UNKNOWN
    region = RegionExport(
        region=RegionInfo(code="15100", name="合成地域"),
        datasets=[location], scenarios=[scenario],
        meta=ExportMeta(
            generated_at=TIME + timedelta(seconds=1),
            dataset_count=1, assessment_count=0, capability_count=0,
            gap_count=0, recommendation_count=0, evidence_count=0,
        ),
    )
    source = region.model_dump_json().encode("utf-8")
    pins = {
        "region_code": "15100", "export_sha256": sha256(source).hexdigest(),
        "scenario_evaluated_at": TIME.isoformat(),
        # Synthetic test fixtures only. Real pin references must be supplied
        # independently, not copied from an exported ScenarioResult.
        "source_urls_by_facility": SOURCES,
        "review_reference": "SYNTHETIC_TEST_ONLY_NOT_APPROVAL",
    }
    return region, source, pins


def run_audit(source, pins):
    return audit_export_bytes(source, json.dumps(pins).encode("utf-8"))


class FloodExportPreflightTests(unittest.TestCase):
    def test_synthetic_snapshot_is_consistent_but_never_published(self):
        _, source, pins = fixture()
        out = run_audit(source, pins)
        self.assertEqual(out["result"], "SNAPSHOT_CONSISTENCY_ONLY")
        self.assertEqual((out["total_count"], out["unknown_count"]), (3, 3))
        self.assertEqual((out["candidate_count"], out["excluded_count"]), (0, 0))
        self.assertFalse(out["publication_authorized"])
        self.assertEqual(out["location_approval"], "NOT_ESTABLISHED")

    def test_current_policy_refuses_classification_upgrade_even_if_pinned(self):
        region, _, _ = fixture()
        region.scenarios[0].facility_results[0].status = Status.CANDIDATE
        with self.assertRaisesRegex(ValueError, "non-UNKNOWN"):
            select_from_region_export(
                region, region_code="15100", expected_evaluated_at=TIME,
                source_urls_by_facility=SOURCES)

    def test_missing_wrong_or_extra_source_pins_fail(self):
        _, source, pins = fixture()
        for override in ({}, {"a": SOURCES["a"]}, {**SOURCES, "x": SOURCES["a"]},
                         {**SOURCES, "a": SOURCES["b"]}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                run_audit(source, {**pins, "source_urls_by_facility": override})

    def test_export_sha_and_eval_pin_both_require_matching_snapshot(self):
        region, source, pins = fixture()
        changed = region.model_copy(deep=True)
        changed.scenarios[0].facility_results[1].reason = "tampered reason"
        changed_raw = changed.model_dump_json().encode()
        with self.assertRaisesRegex(ValueError, "SHA256"):
            run_audit(changed_raw, pins)
        changed_pin = {**pins, "scenario_evaluated_at": (TIME + timedelta(seconds=1)).isoformat()}
        with self.assertRaisesRegex(ValueError, "timestamp"):
            run_audit(source, changed_pin)

    def test_pin_manifest_needs_explicit_region_review_and_timestamp(self):
        _, source, pins = fixture()
        for changed in (
            {**pins, "region_code": "23100"},
            {**pins, "review_reference": ""},
            {**pins, "scenario_evaluated_at": "2026-10-23T02:00:00"},
            {**pins, "scenario_evaluated_at": "nonsense"},
            {**pins, "extra": "not allowed"},
            {k: v for k, v in pins.items() if k != "review_reference"},
        ):
            with self.subTest(change=changed), self.assertRaises(ValueError):
                run_audit(source, changed)

    def test_wrong_region_name_and_duplicated_scenario_fail(self):
        region, _, _ = fixture()
        region.region.name = "different"
        with self.assertRaisesRegex(ValueError, "names differ"):
            select_from_region_export(
                region, region_code="15100", expected_evaluated_at=TIME,
                source_urls_by_facility=SOURCES)
        region, _, _ = fixture()
        region.scenarios.append(region.scenarios[0].model_copy(deep=True))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            select_from_region_export(
                region, region_code="15100", expected_evaluated_at=TIME,
                source_urls_by_facility=SOURCES)

    def test_missing_scenario_or_location_fails_instead_of_zero_facilities(self):
        for missing in ("scenario", "location"):
            region, _, _ = fixture()
            if missing == "scenario":
                region.scenarios.clear()
            else:
                region.datasets.clear()
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "exactly one"):
                select_from_region_export(
                    region, region_code="15100", expected_evaluated_at=TIME,
                    source_urls_by_facility=SOURCES)

    def test_duplicate_json_keys_fail_even_with_matching_hash(self):
        _, _, pins = fixture()
        source = b'{"region":1,"region":2}'
        pins = {**pins, "export_sha256": sha256(source).hexdigest()}
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            run_audit(source, pins)
        raw = json.dumps(pins).encode()
        bad = raw[:-1] + b', "region_code": "15100"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            audit_export_bytes(source, bad)

    def test_missing_raw_urls_or_modified_coordinates_fail_closed(self):
        region, _, _ = fixture()
        region.scenarios[0].facility_results[0].fact.source_url = "https://another.example.test/flood.csv"
        with self.assertRaisesRegex(ValueError, "pinned source"):
            select_from_region_export(
                region, region_code="15100", expected_evaluated_at=TIME,
                source_urls_by_facility=SOURCES)
        region, _, _ = fixture()
        region.scenarios[0].facility_results[0].fact.latitude = 45.0
        with self.assertRaisesRegex(ValueError, "coordinates disagree"):
            select_from_region_export(
                region, region_code="15100", expected_evaluated_at=TIME,
                source_urls_by_facility=SOURCES)

    def test_empty_valid_snapshot_is_not_misreported_as_not_fetched(self):
        region, _, _ = fixture()
        region.datasets[0].records.clear()
        region.scenarios[0].facility_results.clear()
        ass=region.scenarios[0].requirement_assessment
        ass.record_count=0
        ass.raw_value_count=0
        ass.directly_joined_count=0
        result = select_from_region_export(
            region, region_code="15100", expected_evaluated_at=TIME,
            source_urls_by_facility={})
        self.assertEqual(result.result_kind, "NO_DATA")


if __name__ == "__main__":
    unittest.main()
