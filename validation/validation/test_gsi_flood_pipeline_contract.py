"""Cross-role *synthetic* GSI flood contract smoke on combined preview.

Unlike the independent C audit unit, this integration test intentionally calls
D's provider to prove interface compatibility. Never use it as a substitute
for independently fetched official source acceptance.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from src.hinanex.flood_site_reference import extract_gsi_flood_tile, build_flood_site_catalog
from verify_gsi_flood_source import verify_gsi_flood_source

SOURCE_URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
REGION = "13123"


def synthetic_tile():
    return json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "TEST_PLACE_1 - not a real shelter",
                    "address": "TEST-ADDRESS", "remarks": "TEST-only", "disaster1": 1,
                },
                "geometry": {"type": "Point", "coordinates": [139.882, 35.705]},
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "TEST_PLACE_2 - not a real shelter",
                    "address": None, "remarks": None, "disaster1": 1,
                },
                "geometry": {"type": "Point", "coordinates": [139.889, 35.709]},
            },
        ],
    }, ensure_ascii=False).encode("utf-8")


class GsiFloodPipelineContractSmoke(unittest.TestCase):
    def setUp(self):
        self.raw = synthetic_tile()
        self.rows = extract_gsi_flood_tile(self.raw, SOURCE_URL, REGION)

    def test_audited_source_to_d_reference_json_contract(self):
        acceptance = verify_gsi_flood_source(self.raw, self.rows, SOURCE_URL, REGION)
        self.assertEqual(acceptance["status"], "PASS")
        self.assertEqual(acceptance["source_raw_sha256"], hashlib.sha256(self.raw).hexdigest())
        output = build_flood_site_catalog(
            REGION, self.rows, raw_archive=self.raw, c_acceptance=acceptance
        )
        dumped = json.loads(json.dumps(output, ensure_ascii=False))
        self.assertEqual(dumped["status"], "REFERENCE_ONLY")
        self.assertEqual(dumped["source_status"], "C_ACCEPTED")
        self.assertEqual(dumped["region_code"], "13123")
        self.assertEqual(dumped["catalog_kind"], "flood_designated_emergency_site_reference")
        self.assertEqual(dumped["hazard"], "flood")
        self.assertEqual(len(dumped["sites"]), 2)
        self.assertEqual(dumped["sites"][0]["name_raw"], "TEST_PLACE_1 - not a real shelter")
        self.assertEqual(dumped["sites"][0]["address_raw"], "TEST-ADDRESS")
        self.assertEqual(dumped["sites"][0]["disaster1_raw"], 1)
        self.assertEqual(dumped["sites"][0]["latitude"], 35.705)
        self.assertEqual(dumped["sites"][0]["longitude"], 139.882)
        self.assertEqual(
            dumped["sites"][0]["source_feature_key"], f"{SOURCE_URL}#feature_index=0"
        )
        self.assertEqual(dumped["sites"][1]["address_raw"], None)
        self.assertNotIn("open", dumped["sites"][0])
        self.assertNotIn("recommended", dumped["sites"][0])
        self.assertNotIn("safe", dumped["sites"][0])

    def test_missing_c_gate_emits_no_reference(self):
        self.assertEqual(
            build_flood_site_catalog(REGION, self.rows, raw_archive=self.raw)["sites"],
            [],
        )

    def test_changes_after_c_audit_are_rejected(self):
        acceptance = verify_gsi_flood_source(self.raw, self.rows, SOURCE_URL, REGION)
        for change in [
            {"name_raw": "FAKE-NAME"}, {"latitude": 35.01},
            {"address_raw": "FAKE-ADDRESS"}, {"disaster1_raw": 0}
        ]:
            changed = [dict(r) for r in self.rows]
            changed[1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_flood_site_catalog(
                    REGION, changed, raw_archive=self.raw, c_acceptance=acceptance
                )


if __name__ == "__main__":
    unittest.main()
