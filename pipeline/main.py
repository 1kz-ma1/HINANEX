from datetime import datetime, timezone

from src.hinanex.models.common import Evidence, NormalizedDataset, PipelineResult
from src.hinanex.models.shelter import ShelterRecord
from src.hinanex.output import write_model_json


def main() -> None:
    now = datetime.now(timezone.utc)

    # Pipeline wiring test only. These are not real facilities.
    mock_shelters = [
        ShelterRecord(
            id="mock-edogawa-001",
            name="江戸川避難所A",
            latitude=35.7001,
            longitude=139.8701,
            facility_type="designated_emergency_evacuation_site",
            supported_disasters=None,
            accessibility=True,
            capacity=300,
        ),
        ShelterRecord(
            id="mock-edogawa-002",
            name="江戸川避難所B",
            latitude=35.7052,
            longitude=139.8753,
            facility_type="designated_shelter",
            supported_disasters=None,
            accessibility=None,
            capacity=500,
        ),
        ShelterRecord(
            id="mock-edogawa-003",
            name="江戸川避難所C",
            latitude=35.7104,
            longitude=139.8802,
            facility_type="designated_emergency_evacuation_site",
            supported_disasters=None,
            accessibility=False,
            capacity=None,
        ),
    ]

    evidence = Evidence(
        source_name="HINANEX Mock Data",
        publisher="HINANEX Development Team",
        fetched_at=now,
        source_format="MOCK",
        retrieval_method="LOCAL_GENERATED",
        notes="共通Schema確認用のモックデータ。実在施設ではない。",
    )

    dataset = NormalizedDataset(
        region_code="13123",
        region_name="東京都江戸川区",
        requirement_code="shelter_location",
        records=[shelter.model_dump() for shelter in mock_shelters],
        evidence=[evidence],
        normalized_at=now,
    )

    result = PipelineResult(
        region_code="13123",
        region_name="東京都江戸川区",
        datasets=[dataset],
        generated_at=now,
    )

    output_path = write_model_json(
        result,
        "data/normalized/mock_edogawa_shelters.json",
    )

    print(f"JSON output: {output_path}")


if __name__ == "__main__":
    main()
