from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter
from src.hinanex.output import write_model_json
from src.hinanex.pipeline import run_adapter


def main() -> None:
    dataset = run_adapter(EdogawaShelterAdapter())

    output_path = write_model_json(
        dataset,
        "data/normalized/edogawa_shelters.json",
    )

    print(f"Normalized output: {output_path}")
    print(f"Requirement: {dataset.requirement_code}")
    print(f"Records: {len(dataset.records)}")


if __name__ == "__main__":
    main()
