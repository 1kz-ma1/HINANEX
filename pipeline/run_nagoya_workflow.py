from src.hinanex.adapters.nagoya_shelter import NagoyaShelterAdapter
from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.evaluation.gap import analyze_capability_gap
from src.hinanex.evaluation.shelter_location import assess_shelter_location
from src.hinanex.output import write_model_json
from src.hinanex.pipeline import run_adapter


def main() -> None:
    dataset = run_adapter(NagoyaShelterAdapter())
    dataset_path = write_model_json(
        dataset,
        "data/normalized/nagoya_shelters.json",
    )

    assessment = assess_shelter_location(dataset)
    assessment_path = write_model_json(
        assessment,
        "data/normalized/nagoya_shelter_location_assessment.json",
    )

    capability = assess_shelter_discovery([assessment])
    capability_path = write_model_json(
        capability,
        "data/normalized/nagoya_shelter_discovery_capability.json",
    )

    gap = analyze_capability_gap(capability, [assessment])
    gap_path = write_model_json(
        gap,
        "data/normalized/nagoya_shelter_discovery_gap.json",
    )

    print(f"Normalized output: {dataset_path}")
    print(f"Requirement: {dataset.requirement_code}")
    print(f"Records: {len(dataset.records)}")
    print(f"Source files: {len(dataset.evidence)}")
    print(f"Assessment output: {assessment_path}")
    print(
        "Scores: "
        f"Completeness={assessment.data_quality.completeness.score}, "
        f"Validity={assessment.data_quality.validity.score}, "
        "MachineReadability="
        f"{assessment.application_readiness.machine_readability.score}, "
        "GeospatialUsability="
        f"{assessment.application_readiness.geospatial_usability.score}"
    )
    print(f"Capability output: {capability_path}")
    print(
        f"Capability: {capability.capability_name} / "
        f"{capability.status.value}"
    )
    print(f"Gap output: {gap_path}")
    print(
        f"Gaps: {len(gap.gaps)} / "
        f"Recommendations: {len(gap.recommendations)}"
    )
    print(f"Summary: {gap.summary}")


if __name__ == "__main__":
    main()
