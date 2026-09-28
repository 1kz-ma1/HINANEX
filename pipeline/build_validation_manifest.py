from src.hinanex.integration import write_validation_manifest
from validate_region_contracts import validate_contracts


def build_manifest():
    contracts = validate_contracts()
    return write_validation_manifest(contracts)


def main() -> None:
    print("=== HINANEX validation manifest ===")
    output_path = build_manifest()
    print(f"Manifest: {output_path}")
    print("Done: B/C traceability manifest generated.")


if __name__ == "__main__":
    main()
