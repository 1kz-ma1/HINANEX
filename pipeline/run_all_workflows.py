"""Run the full HINANEX D-MVP pipeline for all three validation regions."""

from analyze_edogawa_gap import main as analyze_edogawa_gap
from assess_edogawa import main as assess_edogawa
from assess_edogawa_capability import main as assess_edogawa_capability
from build_region_contracts import build_contracts
from build_validation_manifest import build_manifest
from generate_contract_schema import generate_schema
from run_edogawa import main as run_edogawa
from run_nagoya_workflow import main as run_nagoya
from run_niigata_workflow import main as run_niigata
from validate_region_contracts import validate_contracts
from src.hinanex.version import PROJECT_RELEASE


def _run_stage(name: str, func) -> None:
    print()
    print(f"=== {name} ===")
    try:
        func()
    except Exception as exc:
        raise RuntimeError(f"HINANEX pipeline failed at stage: {name}") from exc


def main() -> None:
    print(f"=== HINANEX {PROJECT_RELEASE} full workflow ===")

    _run_stage("Edogawa / normalize", run_edogawa)
    _run_stage("Edogawa / assessment", assess_edogawa)
    _run_stage("Edogawa / capability", assess_edogawa_capability)
    _run_stage("Edogawa / gap", analyze_edogawa_gap)

    _run_stage("Niigata / full workflow", run_niigata)
    _run_stage("Nagoya / full workflow", run_nagoya)

    _run_stage("Build B/C region contracts", build_contracts)
    _run_stage("Validate B/C region contracts", validate_contracts)
    _run_stage("Build C traceability manifest", build_manifest)
    _run_stage("Generate JSON Schema", generate_schema)

    print()
    print("=== COMPLETE ===")
    print("All 3 regions processed, contracted, validated, and documented.")
    print("B output: data/output/{edogawa,niigata,nagoya}.json")
    print("C manifest: data/output/manifest.json")
    print("Contract schema: contracts/region_export.schema.json")


if __name__ == "__main__":
    main()
