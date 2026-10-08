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
        print(f"{name}: records={len(location.records)}, "
              f"scenario={scenario.status.value}, {counts}")
    print("Flood Scenario: 3-region RegionExport READY (safety semantics validated)")


if __name__ == "__main__":
    main()
