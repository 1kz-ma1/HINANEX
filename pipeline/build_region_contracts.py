from dataclasses import dataclass
from pathlib import Path

from src.hinanex.export import write_region_export_from_paths
from src.hinanex.integration import assert_valid_region_export, read_region_export


@dataclass(frozen=True)
class RegionArtifacts:
    key: str
    dataset: str
    assessment: str
    capability: str
    gap: str
    scenario: str


REGIONS = [
    RegionArtifacts(
        key="edogawa",
        dataset="data/normalized/edogawa_shelters.json",
        assessment="data/normalized/edogawa_shelter_location_assessment.json",
        capability="data/normalized/edogawa_shelter_discovery_capability.json",
        gap="data/normalized/edogawa_shelter_discovery_gap.json",
        scenario="data/normalized/edogawa_flood_scenario.json",
    ),
    RegionArtifacts(
        key="niigata",
        dataset="data/normalized/niigata_shelters.json",
        assessment="data/normalized/niigata_shelter_location_assessment.json",
        capability="data/normalized/niigata_shelter_discovery_capability.json",
        gap="data/normalized/niigata_shelter_discovery_gap.json",
        scenario="data/normalized/niigata_flood_scenario.json",
    ),
    RegionArtifacts(
        key="nagoya",
        dataset="data/normalized/nagoya_shelters.json",
        assessment="data/normalized/nagoya_shelter_location_assessment.json",
        capability="data/normalized/nagoya_shelter_discovery_capability.json",
        gap="data/normalized/nagoya_shelter_discovery_gap.json",
        scenario="data/normalized/nagoya_flood_scenario.json",
    ),
]


def _assert_inputs_exist(region: RegionArtifacts) -> None:
    required = [
        region.dataset,
        region.assessment,
        region.capability,
        region.gap,
        region.scenario,
    ]
    missing = [path for path in required if not Path(path).exists()]

    if missing:
        joined = "\n  - ".join(missing)
        raise FileNotFoundError(
            f"{region.key} の統合前成果物が不足しています:\n  - {joined}\n"
            "先に各地域workflowを実行してください。"
        )


def build_contracts() -> dict[str, Path]:
    """Build + semantic-validate all three B/C region contracts."""

    outputs: dict[str, Path] = {}

    for region in REGIONS:
        _assert_inputs_exist(region)

        output_path = write_region_export_from_paths(
            output_path=f"data/output/{region.key}.json",
            dataset_paths=[region.dataset],
            assessment_paths=[region.assessment],
            capability_paths=[region.capability],
            gap_paths=[region.gap],
            scenario_paths=[region.scenario],
        )

        export = read_region_export(output_path)
        assert_valid_region_export(export, region_key=region.key)
        outputs[region.key] = output_path

    return outputs


def main() -> None:
    print("=== HINANEX B/C contract build ===")

    outputs = build_contracts()
    for key, output_path in outputs.items():
        print(f"{key}: {output_path}")

    print("Done: 3 region contracts generated and validated.")


if __name__ == "__main__":
    main()
