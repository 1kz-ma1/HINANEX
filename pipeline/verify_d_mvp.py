"""Local acceptance check for the HINANEX D-MVP release.

Run this after ``python run_all_workflows.py``. It intentionally does not fetch
remote data itself; the full workflow owns acquisition, while this script checks
that the expected integration artifacts are present and internally valid.
"""

from pathlib import Path

from src.hinanex.integration import EXPECTED_REGIONS, read_region_export
from src.hinanex.models.integration import ValidationManifest
from src.hinanex.version import CONTRACT_SCHEMA_VERSION, PROJECT_RELEASE
from validate_region_contracts import validate_contracts


EXPECTED_FILES = [
    *(Path("data/output") / f"{key}.json" for key in EXPECTED_REGIONS),
    Path("data/output/manifest.json"),
    Path("contracts/region_export.schema.json"),
]


def main() -> None:
    missing = [path for path in EXPECTED_FILES if not path.exists()]
    if missing:
        details = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "D-MVP acceptance artifacts are missing. "
            "Run `python run_all_workflows.py` first:\n" + details
        )

    validate_contracts()

    manifest = ValidationManifest.model_validate_json(
        Path("data/output/manifest.json").read_text(encoding="utf-8")
    )
    if not manifest.all_valid:
        raise ValueError("manifest.all_valid is false")
    manifest_keys = {region.key for region in manifest.regions}
    if manifest_keys != set(EXPECTED_REGIONS):
        raise ValueError(
            f"manifest region mismatch: expected={sorted(EXPECTED_REGIONS)}, "
            f"actual={sorted(manifest_keys)}"
        )

    for key in EXPECTED_REGIONS:
        export = read_region_export(Path("data/output") / f"{key}.json")
        if export.meta.schema_version != CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                f"{key}: expected schema {CONTRACT_SCHEMA_VERSION}, "
                f"got {export.meta.schema_version}"
            )

    print(f"HINANEX {PROJECT_RELEASE}: READY")
    print(f"Contract schema: {CONTRACT_SCHEMA_VERSION}")
    print(f"Regions: {', '.join(EXPECTED_REGIONS)}")
    print("B/C contracts, manifest, and JSON Schema are present and valid.")


if __name__ == "__main__":
    main()
