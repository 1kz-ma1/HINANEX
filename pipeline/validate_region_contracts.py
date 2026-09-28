from pathlib import Path

from src.hinanex.integration import (
    EXPECTED_REGIONS,
    assert_valid_region_export,
    read_region_export,
)


def validate_contracts() -> dict[str, tuple[Path, object]]:
    contracts: dict[str, tuple[Path, object]] = {}

    for key in EXPECTED_REGIONS:
        path = Path(f"data/output/{key}.json")
        if not path.exists():
            raise FileNotFoundError(
                f"統合契約がありません: {path}. "
                "先に python build_region_contracts.py を実行してください。"
            )

        export = read_region_export(path)
        assert_valid_region_export(export, region_key=key)
        contracts[key] = (path, export)

    return contracts


def main() -> None:
    print("=== HINANEX contract validation ===")
    contracts = validate_contracts()
    for key, (path, export) in contracts.items():
        print(
            f"{key}: OK / {export.region.code} {export.region.name} / "
            f"schema={export.meta.schema_version} / {path}"
        )
    print("Done: all 3 region contracts are semantically valid.")


if __name__ == "__main__":
    main()
