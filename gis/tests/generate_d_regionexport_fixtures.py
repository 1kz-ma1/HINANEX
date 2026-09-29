"""Generate deterministic E integration fixtures through D's actual RegionExport builder.

These are contract-test records only. They are not real facilities and must not be
used as disaster information.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = Path(os.environ.get("HINANEX_PIPELINE_ROOT", REPO_ROOT / "pipeline"))
if not PIPELINE_ROOT.exists():
    raise SystemExit("pipeline/ is required (or set HINANEX_PIPELINE_ROOT)")
sys.path.insert(0, str(PIPELINE_ROOT))

from src.hinanex.export import build_region_export  # noqa: E402
from src.hinanex.models.common import Evidence, NormalizedDataset  # noqa: E402
from src.hinanex.models.shelter import ShelterRecord  # noqa: E402

OUT = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 9, 29, tzinfo=timezone.utc)

REGIONS = {
    "edogawa": {
        "code": "13123",
        "name": "東京都江戸川区",
        "records": [
            ShelterRecord(
                id="test-edogawa-mappable",
                name="TEST 江戸川 coordinate record",
                latitude=35.7001,
                longitude=139.8701,
                facility_type="shelter",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
            ShelterRecord(
                id="test-edogawa-null",
                name="TEST 江戸川 null-coordinate record",
                latitude=None,
                longitude=None,
                facility_type="shelter",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
        ],
    },
    "niigata": {
        "code": "15100",
        "name": "新潟県新潟市",
        "records": [
            ShelterRecord(
                id="test-niigata-mappable",
                name="TEST 新潟 coordinate record",
                latitude=37.9000,
                longitude=139.0200,
                facility_type="designated_emergency_evacuation_site",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
            ShelterRecord(
                id="test-niigata-null",
                name="TEST 新潟 null-coordinate record",
                latitude=None,
                longitude=None,
                facility_type="designated_emergency_evacuation_site",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
        ],
    },
    "nagoya": {
        "code": "23100",
        "name": "愛知県名古屋市",
        "records": [
            ShelterRecord(
                id="test-nagoya-null-1",
                name="TEST 名古屋 null-coordinate record 1",
                latitude=None,
                longitude=None,
                address="TEST ADDRESS 1",
                administrative_area="TEST WARD",
                facility_type="evacuation_facility",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
            ShelterRecord(
                id="test-nagoya-null-2",
                name="TEST 名古屋 null-coordinate record 2",
                latitude=None,
                longitude=None,
                address="TEST ADDRESS 2",
                administrative_area="TEST WARD",
                facility_type="evacuation_facility",
                supported_disasters=None,
                notes="synthetic E/D contract test record; not a real facility",
            ),
        ],
    },
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, config in REGIONS.items():
        evidence = Evidence(
            source_name="HINANEX E/D CONTRACT TEST",
            publisher="HINANEX Development Test",
            fetched_at=NOW,
            source_format="SYNTHETIC_TEST",
            retrieval_method="LOCAL_DETERMINISTIC_TEST",
            notes="Synthetic integration fixture. Not official disaster data.",
        )
        dataset = NormalizedDataset(
            region_code=config["code"],
            region_name=config["name"],
            requirement_code="shelter_location",
            records=[record.model_dump() for record in config["records"]],
            evidence=[evidence],
            normalized_at=NOW,
        )
        export = build_region_export(
            datasets=[dataset], assessments=[], capabilities=[], gap_analyses=[]
        )
        # build_region_export() stamps current time. Freeze it for reproducible test fixtures.
        export.meta.generated_at = NOW
        path = OUT / f"{key}.json"
        path.write_text(export.model_dump_json(indent=2), encoding="utf-8")
        print(f"generated {path.name}: {len(dataset.records)} records")


if __name__ == "__main__":
    main()
