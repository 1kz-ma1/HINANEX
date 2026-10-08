"""Generate conservative flood scenario outputs from existing official raw archives.

Run AFTER shelter_location workflows. Reads exactly the archived bytes those
workflows normalized; never makes a second independent fetch or fuzzy join.
"""
from pathlib import Path

from src.hinanex.flood_scenario import evaluate_flood_scenario
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.output import write_model_json
from src.hinanex.scenario_sources import (
    edogawa_facts, nagoya_facts, niigata_facts,
)


def _load_location(region: str) -> NormalizedDataset:
    path = Path("data/normalized") / f"{region}_shelters.json"
    return NormalizedDataset.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    locations = {
        name: _load_location(name)
        for name in ("edogawa", "niigata", "nagoya")
    }
    inputs = {
        "edogawa": edogawa_facts(locations["edogawa"]),
        "niigata": niigata_facts(
            locations["niigata"],
            Path("data/raw/niigata/niigata_evacuation_space.csv").read_bytes(),
        ),
        "nagoya": nagoya_facts(
            locations["nagoya"],
            Path("data/raw/nagoya/nagoya_indoor_shelters_bundle.zip").read_bytes(),
        ),
    }
    for region, location in locations.items():
        scenario = evaluate_flood_scenario(location, inputs[region])
        path = write_model_json(
            scenario, f"data/normalized/{region}_flood_scenario.json",
        )
        counts = {
            status: sum(result.status.value == status for result in scenario.facility_results)
            for status in ("CANDIDATE", "EXCLUDED", "UNKNOWN")
        }
        print(f"{region}: {path} / {scenario.status.value} / {counts}")


if __name__ == "__main__":
    main()
