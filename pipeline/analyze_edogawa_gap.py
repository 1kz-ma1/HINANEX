import json
from pathlib import Path

from src.hinanex.evaluation.gap import analyze_capability_gap
from src.hinanex.models.assessment import DatasetAssessment
from src.hinanex.models.capability import CapabilityAssessment
from src.hinanex.output import write_model_json


def _read_model(path: str, model_class):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return model_class.model_validate(data)


def main() -> None:
    assessment = _read_model(
        "data/normalized/edogawa_shelter_location_assessment.json",
        DatasetAssessment,
    )
    capability = _read_model(
        "data/normalized/edogawa_shelter_discovery_capability.json",
        CapabilityAssessment,
    )

    analysis = analyze_capability_gap(
        capability,
        [assessment],
    )

    output_path = write_model_json(
        analysis,
        "data/normalized/edogawa_shelter_discovery_gap.json",
    )

    print(f"Gap output: {output_path}")
    print(f"Capability: {analysis.capability_name}")
    print(f"Status: {analysis.capability_status.value}")
    print(f"Gaps: {len(analysis.gaps)}")
    print(f"Recommendations: {len(analysis.recommendations)}")
    print(f"Summary: {analysis.summary}")

    if analysis.gaps:
        print()
        print("=== Gaps ===")
        for gap in analysis.gaps:
            print(
                f"- {gap.requirement_code}: "
                f"{gap.kind.value} / {gap.severity.value}"
            )
            print(f"  {gap.reason}")

    if analysis.recommendations:
        print()
        print("=== Recommendations ===")
        for recommendation in analysis.recommendations:
            print(f"- {recommendation.title}")


if __name__ == "__main__":
    main()
