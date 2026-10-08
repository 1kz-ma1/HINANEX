"""Reference catalog fail-closed rules. Synthetic coordinates are not real shelters."""
import hashlib
import unittest

from src.hinanex.flood_site_reference import build_flood_site_catalog

RAW = b'{"type":"FeatureCollection","features":[]}'  # deterministic TEST fixture
HASH = hashlib.sha256(RAW).hexdigest()


def item(**overrides):
    base = {
        "source_feature_key": "https://cyberjapandata.gsi.go.jp/xyz/skhb01/12/3639/1613.geojson#feature_index=0",
        "address_raw": "TEST address", "remarks_raw": None, "disaster1_raw": 1,
        "name_raw": "TEST official name (not a real evacuation place)",
        "search_context_region_code": "13123",
        "latitude": 35.7,
        "longitude": 139.9,
        "source_url": "https://cyberjapandata.gsi.go.jp/xyz/skhb01/12/3639/1613.geojson",
        "source_record_trace": "feature_index=0",
        "source_raw_sha256": HASH,
        "designation_kind": "designated_emergency_evacuation_site",
        "hazard_dataset": "GSI_SKHB01_FLOOD",
    }
    base.update(overrides)
    return base


def audit(**overrides):
    base = {
        "status": "PASS",
        "source_raw_sha256": HASH,
        "search_context_region_code": "13123",
        "hazard_dataset": "GSI_SKHB01_FLOOD",
        "audit_reference": "C-TEST-fixture-only",
        "accepted_source_feature_keys": ["https://cyberjapandata.gsi.go.jp/xyz/skhb01/12/3639/1613.geojson#feature_index=0"],
    }
    base.update(overrides)
    return base


class FloodSiteReferenceTests(unittest.TestCase):
    def test_documented_geojson_fields_are_preserved(self):
        import json
        from src.hinanex.flood_site_reference import extract_gsi_flood_tile
        raw = json.dumps({"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [139.9, 35.7]},
            "properties": {
                "name": "TEST named place", "address": "TEST address",
                "remarks": "TEST notes", "disaster1": 1,
            },
        }]}).encode()
        url = item()["source_url"]
        rows = extract_gsi_flood_tile(raw, url, "13123")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name_raw"], "TEST named place")
        self.assertEqual(rows[0]["address_raw"], "TEST address")
        self.assertEqual(rows[0]["remarks_raw"], "TEST notes")
        self.assertEqual(rows[0]["disaster1_raw"], 1)
        self.assertEqual(rows[0]["latitude"], 35.7)
        self.assertEqual(rows[0]["longitude"], 139.9)
        self.assertEqual(rows[0]["source_feature_key"], f"{url}#feature_index=0")
        self.assertEqual(build_flood_site_catalog("13123", rows)["sites"], [])
        approved = build_flood_site_catalog("13123", rows, raw_archive=raw, c_acceptance={
            "status": "PASS", "source_raw_sha256": hashlib.sha256(raw).hexdigest(),
            "search_context_region_code": "13123", "hazard_dataset": "GSI_SKHB01_FLOOD",
            "audit_reference": "C-TEST", "accepted_source_feature_keys": [rows[0]["source_feature_key"]],
        })
        self.assertEqual(approved["status"], "REFERENCE_ONLY")

    def test_fail_closed_for_undocumented_or_malformed_geojson(self):
        import json
        from src.hinanex.flood_site_reference import extract_gsi_flood_tile
        url = item()["source_url"]
        bad_shapes = [
            {"type": "FeatureCollection", "features": [{"type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139, 35]},
                "properties": {"name": "TEST", "disaster1": "1"}}]},
            {"type": "FeatureCollection", "features": [{"type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139, None]},
                "properties": {"name": "TEST", "disaster1": 1}}]},
            {"type": "FeatureCollection", "features": [{"type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": []},
                "properties": {"name": "TEST", "disaster1": 1}}]},
        ]
        for bad in bad_shapes:
            with self.assertRaises(ValueError):
                extract_gsi_flood_tile(json.dumps(bad).encode(), url, "13123")


    def test_no_verified_source_returns_no_candidates(self):
        for kwargs in ({}, {"raw_archive": RAW}, {"c_acceptance": audit()}):
            result = build_flood_site_catalog("13123", [item()], **kwargs)
            self.assertEqual(result["status"], "BLOCKED_UNVERIFIED_SOURCE")
            self.assertEqual(result["sites"], [])
            self.assertEqual(result["total_source_records"], 1)

    def test_strict_accepted_fixture_is_reference_not_safety(self):
        result = build_flood_site_catalog("13123", [item()], raw_archive=RAW, c_acceptance=audit())
        self.assertEqual(result["status"], "REFERENCE_ONLY")
        self.assertEqual(len(result["sites"]), 1)
        self.assertEqual(result["sites"][0]["name_raw"], item()["name_raw"])
        self.assertEqual(result["sites"][0]["source_raw_sha256"], HASH)
        self.assertNotIn("safe", result["sites"][0])
        self.assertNotIn("route", result["sites"][0])
        self.assertNotIn("is_open", result["sites"][0])
        self.assertIn("広域避難", result["limitations"][0])

    def test_acceptance_is_pinned_to_archived_bytes_and_exact_ids(self):
        for bad in [
            audit(status="UNKNOWN"), audit(source_raw_sha256="x" * 64),
            audit(search_context_region_code="15100"),
            audit(hazard_dataset="GSI_SKHB02_LANDSLIDE"),
            audit(audit_reference=""), audit(accepted_source_feature_keys=[]),
            audit(accepted_source_feature_keys=[item()["source_feature_key"], item()["source_feature_key"]]),
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_flood_site_catalog("13123", [item()], raw_archive=RAW, c_acceptance=bad)
        with self.assertRaises(ValueError):
            build_flood_site_catalog("13123", [item()], raw_archive=RAW + b"x", c_acceptance=audit())
        with self.assertRaises(ValueError):
            build_flood_site_catalog("13123", [item()], raw_archive=RAW, c_acceptance=audit(accepted_source_feature_keys=["other"]))
        with self.assertRaises(ValueError):
            build_flood_site_catalog("13123", [item(), item()], raw_archive=RAW, c_acceptance=audit())

    def test_rejects_untrusted_raw_fields_and_sources(self):
        broken = [
            {"latitude": None}, {"latitude": float("nan")},
            {"latitude": True}, {"longitude": 181},
            {"search_context_region_code": "15100"}, {"designation_kind": "designated_shelter"},
            {"hazard_dataset": "GSI_SKHB07_INLAND"}, {"source_raw_sha256": "x" * 64},
            {"source_url": "http://cyberjapandata.gsi.go.jp/xyz/skhb01/12/3639/1613.geojson"},
            {"source_url": "https://evil.example/xyz/skhb01/12/3639/1613.geojson"},
            {"source_url": "https://cyberjapandata.gsi.go.jp/xyz/skhb04/12/3639/1613.geojson"},
            {"source_url": "https://cyberjapandata.gsi.go.jp/xyz/skhb01/12/3639/1613.geojson?x=1"},
            {"source_feature_key": ""}, {"disaster1_raw": 0}, {"address_raw": 23}, {"name_raw": ""},
            {"source_record_trace": ""}, {"source_record_trace": "fake_trace"}, {"unexpected_extra": "value"},
        ]
        for change in broken:
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_flood_site_catalog("13123", [item(**change)], raw_archive=RAW, c_acceptance=audit())

    def test_cannot_promote_old_unknown_scenario(self):
        # A legacy Niigata flood raw marker is not a verified GSI designation.
        with self.assertRaises(ValueError):
            build_flood_site_catalog("13123", [{
                **item(), "hazard_dataset": "NIIGATA_ODS_FLOOD",
                "name_raw": "TEST: ○ / 2階以上 / UNKNOWN",
            }], raw_archive=RAW, c_acceptance=audit())

    def test_only_declared_regions_are_accepted(self):
        with self.assertRaises(ValueError):
            build_flood_site_catalog("99999", [])
        with self.assertRaises(ValueError):
            build_flood_site_catalog("13123", "not-a-list")


if __name__ == "__main__":
    unittest.main()
