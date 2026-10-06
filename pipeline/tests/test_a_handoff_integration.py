import copy
import unittest
from pathlib import Path

from src.hinanex.a_handoff_integration import (
    FORMAL_REQUIREMENT_CODE,
    SHELTER_CAPABILITY_CODE,
    load_json,
    validate_a_handoff,
    validate_region_exports_against_handoff,
)
from src.hinanex.integration import EXPECTED_REGIONS
from src.hinanex.version import CONTRACT_SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_PATH = (
    REPO_ROOT
    / "data-research"
    / "handoff"
    / "HINANEX_A_final_handoff.json"
)


def make_exports() -> dict[str, dict]:
    exports: dict[str, dict] = {}

    for region_key, (region_code, region_name) in EXPECTED_REGIONS.items():
        exports[region_key] = {
            "region": {
                "code": region_code,
                "name": region_name,
            },
            "datasets": [
                {
                    "region_code": region_code,
                    "region_name": region_name,
                    "requirement_code": FORMAL_REQUIREMENT_CODE,
                    "records": [],
                    "evidence": [
                        {
                            "source_name": "D adapter evidence",
                            "source_url": "https://example.test/source",
                        }
                    ],
                }
            ],
            "assessments": [
                {
                    "region_code": region_code,
                    "region_name": region_name,
                    "requirement_code": FORMAL_REQUIREMENT_CODE,
                }
            ],
            "capabilities": [
                {
                    "region_code": region_code,
                    "region_name": region_name,
                    "capability_code": SHELTER_CAPABILITY_CODE,
                    "dependency_results": [
                        {
                            "requirement_code": FORMAL_REQUIREMENT_CODE,
                        }
                    ],
                }
            ],
            "gaps": [],
            "recommendations": [],
            "meta": {
                "schema_version": CONTRACT_SCHEMA_VERSION,
            },
        }

    return exports


class AHandoffIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handoff = load_json(HANDOFF_PATH)

    def test_committed_a_handoff_matches_d_contract_and_adapter_sources(self) -> None:
        self.assertEqual(validate_a_handoff(self.handoff), [])

    def test_three_region_exports_have_a_to_d_traceability_chain(self) -> None:
        errors = validate_region_exports_against_handoff(
            self.handoff,
            make_exports(),
        )
        self.assertEqual(errors, [])

    def test_uncoordinated_formal_requirement_is_rejected(self) -> None:
        handoff = copy.deepcopy(self.handoff)
        handoff["contract"]["current_formal_requirement_codes"].append(
            "flood_hazard"
        )

        errors = validate_a_handoff(handoff)

        self.assertTrue(
            any("formal requirement codes mismatch" in item for item in errors)
        )

    def test_missing_d_assessment_breaks_traceability(self) -> None:
        exports = make_exports()
        exports["nagoya"]["assessments"] = []

        errors = validate_region_exports_against_handoff(
            self.handoff,
            exports,
        )

        self.assertTrue(
            any(
                "nagoya: expected exactly one shelter_location assessment"
                in item
                for item in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
