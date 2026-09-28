import json
from pathlib import Path

from src.hinanex.models.export import RegionExport


def generate_schema() -> Path:
    output_path = Path("contracts/region_export.schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            RegionExport.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    path = generate_schema()
    print(f"JSON Schema: {path}")


if __name__ == "__main__":
    main()
