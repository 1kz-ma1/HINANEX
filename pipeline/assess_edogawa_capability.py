import json
from pathlib import Path

from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.models.assessment import DatasetAssessment
from src.hinanex.output import write_model_json


def main() -> None:
    source_path = Path(
        "data/normalized/edogawa_shelter_location_assessment.json"
    )

    data = json.loads(source_path.read_text(encoding="utf-8"))
    assessment = DatasetAssessment.model_validate(data)

    capability = assess_shelter_discovery([assessment])

    output_path = write_model_json(
        capability,
        "data/normalized/edogawa_shelter_discovery_capability.json",
    )

    print(f"Capability output: {output_path}")
    print(f"Capability: {capability.capability_name}")
    print(f"Status: {capability.status.value}")
    print()
    print("=== Reasons ===")
    for reason in capability.reasons:
        print("-", reason)


if __name__ == "__main__":
    main()
