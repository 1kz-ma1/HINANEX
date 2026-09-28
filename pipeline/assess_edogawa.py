import json
from pathlib import Path

from src.hinanex.evaluation.shelter_location import assess_shelter_location
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.output import write_model_json


def main() -> None:
    source_path = Path("data/normalized/edogawa_shelters.json")

    data = json.loads(source_path.read_text(encoding="utf-8"))
    dataset = NormalizedDataset.model_validate(data)

    assessment = assess_shelter_location(dataset)

    output_path = write_model_json(
        assessment,
        "data/normalized/edogawa_shelter_location_assessment.json",
    )

    print(f"Assessment output: {output_path}")
    print(f"Records: {assessment.record_count}")
    print()
    print("=== Data Quality ===")
    print("Completeness:", assessment.data_quality.completeness.score)
    print("Validity:", assessment.data_quality.validity.score)
    print()
    print("=== Application Readiness ===")
    print(
        "Machine Readability:",
        assessment.application_readiness.machine_readability.score,
    )
    print(
        "Geospatial Usability:",
        assessment.application_readiness.geospatial_usability.score,
    )
    print()
    print("=== Findings ===")
    for finding in assessment.findings:
        print("-", finding)


if __name__ == "__main__":
    main()
