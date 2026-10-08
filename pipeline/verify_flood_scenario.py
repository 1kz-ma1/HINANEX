"""Acceptance gate for the three-region flood Scenario export.

Run from pipeline/ AFTER python run_all_workflows.py. Never assumes fixed
municipal record counts; raw Source updates can legitimately change them.
"""
from pathlib import Path

from src.hinanex.integration import (
    EXPECTED_REGIONS, assert_valid_region_export, read_region_export,
)
from src.hinanex.models.scenario import FacilityScenarioStatus


def main() -> None:
    for name, (code, _) in EXPECTED_REGIONS.items():
        path = Path("data/output") / f"{name}.json"
        export = read_region_export(path)
        assert_valid_region_export(export, region_key=name)
        if len(export.scenarios) != 1:
            raise ValueError(f"{name}: expected exactly one flood scenario")
        scenario = export.scenarios[0]
        if scenario.scenario_id != "flood_shelter_selection":
            raise ValueError(f"{name}: unexpected scenario id")
        if scenario.requirement_assessment.requirement_code != "shelter_hazard_applicability":
            raise ValueError(f"{name}: unexpected scenario requirement")
        location = next(d for d in export.datasets if d.requirement_code == "shelter_location")
        if scenario.requirement_assessment.record_count != len(location.records):
            raise ValueError(f"{name}: scenario/legacy location record count mismatch")
        counts = {status.value: sum(item.status == status for item in scenario.facility_results)
                  for status in FacilityScenarioStatus}
        if name in {"edogawa", "nagoya"} and (
            counts["CANDIDATE"] or counts["EXCLUDED"]
        ):
            raise ValueError(f"{name}: non-flood-only scope was classified")
        if name == "niigata":
            # Count by values present now, not fixed 2026-10-08 record totals:
            # official CSV may change and this must not hide unverified rows.
            floor_markers = {"2階以上", "3階以上", "全階可"}
            floor_items = [
                item for item in scenario.facility_results
                if item.fact.official_status_raw in floor_markers
            ]
            if any(
                item.fact.usable_floor_raw != item.fact.official_status_raw
                or item.status != FacilityScenarioStatus.UNKNOWN
                for item in floor_items
            ):
                raise ValueError("niigata: floor raw was lost or classified before semantic acceptance")
            print(f"niigata: raw floor constraints preserved={len(floor_items)} "
                  "(eligibility remains unverified)")
        print(f"{name}: records={len(location.records)}, "
              f"scenario={scenario.status.value}, {counts}")
    print("Flood Scenario: 3-region raw trace/contract boundary checks PASSED (official marker semantics require A/C acceptance)")


if __name__ == "__main__":
    main()
