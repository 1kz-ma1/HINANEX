"""Independent GSI official flood-source raw audit tests (all fixtures synthetic)."""
import hashlib
import json
import unittest

from validation.verify_gsi_flood_source import verify_gsi_flood_source

URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
REGION = "13123"


def sample_source(**prop_changes):
    props = {"name": "TEST-SITE", "address": "TEST-address", "remarks": None, "disaster1": 1}
    props.update(prop_changes)
    doc = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [139.88, 35.7]},
        "properties": props,
    }]}
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def row(raw: bytes, **changes):
    data = json.loads(raw)
    feat = data["features"][0]
    r = {
        "source_feature_key": f"{URL}#feature_index=0",
        "name_raw": feat["properties"]["name"],
        "address_raw": feat["properties"]["address"],
        "remarks_raw": feat["properties"]["remarks"],
        "disaster1_raw": feat["properties"]["disaster1"],
        "search_context_region_code": REGION,
        "latitude": 35.7, "longitude": 139.88,
        "source_url": URL, "source_record_trace": "feature_index=0",
        "source_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "designation_kind": "designated_emergency_evacuation_site",
        "hazard_dataset": "GSI_SKHB01_FLOOD",
    }
    r.update(changes)
    return r


class GsiFloodAuditTests(unittest.TestCase):
    def test_exact_raw_match_emits_acceptance_no_safety(self):
        raw = sample_source()
        result = verify_gsi_flood_source(raw, [row(raw)], URL, REGION)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["accepted_source_feature_keys"], [f"{URL}#feature_index=0"])
        self.assertNotIn("is_safe", result)
        self.assertNotIn("opening", result)

    def test_tampering_source_name_address_hazard_location_trace_or_hash_fails(self):
        raw = sample_source()
        corrupted = [
            {"name_raw": "different"}, {"address_raw": "different"},
            {"remarks_raw": "guessed"}, {"disaster1_raw": False},
            {"latitude": 35.700001}, {"longitude": 139.9},
            {"source_record_trace": "feature_index=9"},
            {"source_raw_sha256": "0" * 64},
            {"source_feature_key": "guessed-id"},
            {"source_url": "https://untrusted.example/data"},
            {"hazard_dataset": "GSI_SKHB04_EARTHQUAKE"},
        ]
        for change in corrupted:
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_gsi_flood_source(raw, [row(raw, **change)], URL, REGION)

    def test_unverified_flood_marker_fails_closed(self):
        for value in [None, 0, "1", True]:
            raw = sample_source(disaster1=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_gsi_flood_source(raw, [row(raw)], URL, REGION)

    def test_wrong_url_region_geometry_and_empty_archive(self):
        raw = sample_source()
        for bad_url in [
            "https://example.org/tile.geojson",
            "https://cyberjapandata.gsi.go.jp/xyz/skhb04/10/909/403.geojson",
            "http://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson",
        ]:
            with self.assertRaises(ValueError):
                verify_gsi_flood_source(raw, [row(raw)], bad_url, REGION)
        with self.assertRaises(ValueError):
            verify_gsi_flood_source(raw, [row(raw)], URL, "99999")
        with self.assertRaises(ValueError):
            verify_gsi_flood_source(raw, [], URL, REGION)
        with self.assertRaises(ValueError):
            verify_gsi_flood_source(b'{"type":"FeatureCollection","features":[]}', [], URL, REGION)
        broken = json.loads(raw)
        broken["features"][0]["geometry"] = {"type": "Polygon", "coordinates": []}
        with self.assertRaises(ValueError):
            verify_gsi_flood_source(json.dumps(broken).encode(), [row(raw)], URL, REGION)


if __name__ == "__main__":
    unittest.main()
