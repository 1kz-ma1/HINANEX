"""Offline, synthetic-only checks for #301's read-only scenario selection."""
from datetime import datetime, timedelta, timezone
import unittest

from src.hinanex.models.assessment import CapabilityStatus, DiscoveryStatus
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.scenario import (
    FacilityScenarioResult, FacilityScenarioStatus as Status, HazardFact,
    ScenarioJoinStatus as Join, ScenarioRequirementAssessment, ScenarioResult,
)
from src.hinanex.scenario_selection import select_flood_scenario


TIME = datetime(2026, 10, 23, 2, 0, tzinfo=timezone.utc)
SOURCES = {key: f"https://example.test/{key}.csv" for key in ("a", "b", "c")}


def synthetic_snapshot():
    location = NormalizedDataset(
        region_code="15100", region_name="合成地域",
        requirement_code="shelter_location",
        records=[
            {"id": "c", "name": "C", "latitude": None, "longitude": None},
            {"id": "a", "name": "A", "latitude": 37.1, "longitude": 139.1},
            {"id": "b", "name": "B", "latitude": 37.2, "longitude": 139.2},
        ],
        normalized_at=TIME,
    )
    results = []
    for key, status, raw, coordinates in (
        ("b", Status.EXCLUDED, "×", (37.2, 139.2)),
        ("c", Status.UNKNOWN, "－", (None, None)),
        ("a", Status.CANDIDATE, "○", (37.1, 139.1)),
    ):
        results.append(FacilityScenarioResult(
            facility_id=key, status=status, reason="合成データの評価結果",
            fact=HazardFact(
                facility_id=key, facility_name=f"合成施設{key}",
                hazard_scope_raw="災害種別_洪水", source_semantics="synthetic",
                official_status_raw=raw, source_url=SOURCES[key],
                source_record_trace=f"row={key}", join_status=Join.DIRECT_SAME_SOURCE,
                latitude=coordinates[0], longitude=coordinates[1],
            ),
        ))
    scenario = ScenarioResult(
        region_code="15100", region_name="合成地域",
        status=CapabilityStatus.DEGRADED,
        requirement_assessment=ScenarioRequirementAssessment(
            discovery_status=DiscoveryStatus.AVAILABLE,
            record_count=3, directly_joined_count=3, raw_value_count=3,
            reason="synthetic",
        ),
        facility_results=results, evaluated_at=TIME,
    )
    return scenario, location


class ScenarioSelectionTests(unittest.TestCase):
    def run_selection(self, scenario=None, location=None, **changes):
        if scenario is None or location is None:
            scenario, location = synthetic_snapshot()
        options = dict(
            region_code="15100", hazard="flood",
            expected_evaluated_at=TIME, source_urls_by_facility=SOURCES,
        )
        options.update(changes)
        return select_flood_scenario(scenario, location, **options)

    def test_categories_are_preserved_and_stably_sorted(self):
        output = self.run_selection()
        self.assertEqual([row.facility_id for row in output.rows], ["a", "b", "c"])
        self.assertEqual([row.status for row in output.rows],
                         [Status.CANDIDATE, Status.EXCLUDED, Status.UNKNOWN])
        self.assertEqual((output.candidate_count, output.excluded_count, output.unknown_count),
                         (1, 1, 1))
        self.assertEqual(output.result_kind, "HAS_ROWS")
        self.assertFalse(output.rows[2].coordinates_present)
        self.assertEqual(output.rows[2].official_status_raw, "－")
        scenario, location = synthetic_snapshot()
        scenario.facility_results.reverse()
        self.assertEqual(self.run_selection(scenario, location), output)

    def test_filter_does_not_change_status_or_hide_total_unknown_count(self):
        output = self.run_selection(include_statuses=(Status.CANDIDATE, Status.UNKNOWN))
        self.assertEqual([row.status for row in output.rows], [Status.CANDIDATE, Status.UNKNOWN])
        self.assertEqual((output.total_count, output.unknown_count, output.excluded_count), (3, 1, 1))
        self.assertEqual(output.result_kind, "HAS_ROWS")

    def test_zero_match_is_distinct_from_no_data(self):
        scenario, location = synthetic_snapshot()
        scenario.facility_results = [row for row in scenario.facility_results if row.status != Status.EXCLUDED]
        location.records = [row for row in location.records if row["id"] != "b"]
        scenario.requirement_assessment.record_count = 2
        scenario.requirement_assessment.directly_joined_count = 2
        scenario.requirement_assessment.raw_value_count = 2
        out = self.run_selection(scenario, location, source_urls_by_facility={"a": SOURCES["a"], "c": SOURCES["c"]}, include_statuses=(Status.EXCLUDED,))
        self.assertEqual(out.result_kind, "NO_MATCH")
        self.assertEqual((out.total_count, out.unknown_count), (2, 1))
        scenario.facility_results = []
        location.records = []
        scenario.requirement_assessment.record_count = 0
        scenario.requirement_assessment.directly_joined_count = 0
        scenario.requirement_assessment.raw_value_count = 0
        out = self.run_selection(scenario, location, source_urls_by_facility={})
        self.assertEqual(out.result_kind, "NO_DATA")

    def test_unknown_remains_unknown_for_unverified_or_combined_hazard(self):
        scenario, location = synthetic_snapshot()
        item = scenario.facility_results[1]
        item.fact.hazard_scope_raw = "洪水・内水"
        item.fact.join_status = Join.UNVERIFIED
        scenario.requirement_assessment.directly_joined_count -= 1
        out = self.run_selection(scenario, location)
        self.assertEqual(out.unknown_count, 1)
        self.assertEqual(next(row for row in out.rows if row.facility_id == "c").status, Status.UNKNOWN)

    def test_region_hazard_and_snapshot_must_match(self):
        for options in (
            {"region_code": "23100"}, {"hazard": "inland"},
            {"expected_evaluated_at": TIME - timedelta(seconds=1)},
            {"expected_evaluated_at": TIME.replace(tzinfo=None)},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.run_selection(**options)
        scenario, location = synthetic_snapshot()
        scenario.hazard = "inland"
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)

    def test_source_pins_missing_extra_mismatch_or_unsafe_url(self):
        for pins in (None, {}, {**SOURCES, "extra": SOURCES["a"]},
                     {**SOURCES, "a": SOURCES["b"]}):
            with self.subTest(pins=pins), self.assertRaises((ValueError, TypeError)):
                self.run_selection(source_urls_by_facility=pins)
        scenario, location = synthetic_snapshot()
        scenario.facility_results[0].fact.source_url = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)

    def test_duplicate_missing_and_cross_record_ids_rejected(self):
        scenario, location = synthetic_snapshot()
        scenario.facility_results[0].fact.facility_id = "a"
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)
        scenario, location = synthetic_snapshot()
        location.records[0]["id"] = "a"
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)
        scenario, location = synthetic_snapshot()
        scenario.facility_results.pop()
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)

    def test_decided_rows_require_direct_exact_flood_fact(self):
        for change in ("scope", "join", "raw", "trace"):
            scenario, location = synthetic_snapshot()
            row = scenario.facility_results[0]
            if change == "scope":
                row.fact.hazard_scope_raw = "洪水・内水"
            if change == "join":
                row.fact.join_status = Join.UNVERIFIED
                scenario.requirement_assessment.directly_joined_count -= 1
            if change == "raw":
                row.fact.official_status_raw = None
                scenario.requirement_assessment.raw_value_count -= 1
            if change == "trace":
                row.fact.source_record_trace = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_selection(scenario, location)

    def test_mismatched_coordinates_and_counts_rejected(self):
        scenario, location = synthetic_snapshot()
        scenario.facility_results[0].fact.latitude += 1
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)
        scenario, location = synthetic_snapshot()
        scenario.requirement_assessment.record_count += 1
        with self.assertRaises(ValueError):
            self.run_selection(scenario, location)

    def test_invalid_requested_statuses_rejected(self):
        for statuses in ((), (Status.UNKNOWN, Status.UNKNOWN), ("UNKNOWN",), [Status.UNKNOWN]):
            with self.subTest(statuses=statuses), self.assertRaises(ValueError):
                self.run_selection(include_statuses=statuses)


if __name__ == "__main__":
    unittest.main()
