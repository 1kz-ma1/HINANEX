from __future__ import annotations

from pathlib import Path

from src.hinanex.a_handoff_integration import (
    FORMAL_REQUIREMENT_CODE,
    assert_a_d_integration,
    load_json,
)
from src.hinanex.integration import (
    EXPECTED_REGIONS,
    assert_valid_region_export,
    read_region_export,
)


PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
HANDOFF_PATH = (
    REPO_ROOT
    / "data-research"
    / "handoff"
    / "HINANEX_A_final_handoff.json"
)
OUTPUT_DIR = PIPELINE_ROOT / "data" / "output"


def main() -> None:
    handoff = load_json(HANDOFF_PATH)

    exports = {}
    raw_exports = {}

    missing = []
    for region_key in EXPECTED_REGIONS:
        output_path = OUTPUT_DIR / f"{region_key}.json"
        if not output_path.exists():
            missing.append(str(output_path))
            continue

        export = read_region_export(output_path)
        assert_valid_region_export(export, region_key=region_key)
        exports[region_key] = export
        raw_exports[region_key] = export.model_dump(mode="json")

    if missing:
        detail = "\n  - ".join(missing)
        raise FileNotFoundError(
            "D RegionExport artifacts are missing. "
            "Run python run_all_workflows.py first:\n  - " + detail
        )

    assert_a_d_integration(handoff, raw_exports)

    print("A-D Integration: READY")
    print(
        "Contract schema: "
        f"{handoff['contract']['region_export_schema_version']}"
    )
    print(f"Formal requirement: {FORMAL_REQUIREMENT_CODE}")
    print()

    for region_key, (_, region_name) in EXPECTED_REGIONS.items():
        export = exports[region_key]
        dataset = next(
            item
            for item in export.datasets
            if item.requirement_code == FORMAL_REQUIREMENT_CODE
        )
        capability = next(
            item
            for item in export.capabilities
            if item.capability_code == "shelter_discovery"
        )
        related_gaps = [
            gap
            for gap in export.gaps
            if gap.requirement_code == FORMAL_REQUIREMENT_CODE
        ]
        related_recommendations = [
            recommendation
            for recommendation in export.recommendations
            if recommendation.requirement_code == FORMAL_REQUIREMENT_CODE
        ]

        status = getattr(capability.status, "value", str(capability.status))
        print(region_name)
        print(f"  records: {len(dataset.records)}")
        print(f"  D evidence: {len(dataset.evidence)}")
        print(f"  capability: {status}")
        print(f"  gaps: {len(related_gaps)}")
        print(f"  recommendations: {len(related_recommendations)}")

    future = handoff["contract"].get(
        "future_or_not_yet_formalized_requirements",
        [],
    )
    print()
    print("Not yet formalized in D:")
    for requirement in future:
        print(f"  - {requirement}")


if __name__ == "__main__":
    main()
