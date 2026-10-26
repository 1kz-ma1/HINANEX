"""A original-source skhb02 feasibility checks: offline fixtures only."""
import importlib.util
import json
from pathlib import Path
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "inspect_gsi_skhb02_archive.py"
spec = importlib.util.spec_from_file_location("gsi_skhb02_a", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"


def sample(properties=None, coords=None):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": properties or {
            "name": "合成の避難場所", "address": "訓練用",
            "disaster2": 1, "disaster1": 1,
        }, "geometry": {"type": "Point", "coordinates": coords or [139.9, 35.7]}}],
    }, ensure_ascii=False).encode()


class SourceTileTests(unittest.TestCase):
    def test_flood_and_landslide_labels_stay_separate(self):
        out = mod.inspect_archived_tile(sample(), URL)
        self.assertEqual(out["status"], "SOURCE_TILE_INSPECTED_UNREVIEWED")
        self.assertEqual(out["official_attribute"], "disaster2")
        self.assertEqual(out["source_feature_count"], 1)
        self.assertEqual(out["raw_feature_previews_for_human_review"][0]["disaster2_raw"], 1)
        self.assertTrue(out["not_a_landslide_risk_layer"])
        self.assertFalse(out["independent_c_approved"])
        self.assertEqual(out["safe_destination_count_approved"], 0)
        self.assertFalse(out["municipal_coverage_verified"])
        self.assertTrue(out["not_for_publication"])

    def test_flood_only_is_rejected_even_if_disaster1_is_one(self):
        with self.assertRaisesRegex(mod.GsiLandslideInspectionError, "disaster2"):
            mod.inspect_archived_tile(sample({
                "name": "合成", "disaster1": 1,
            }), URL)

    def test_invalid_marker_boolean_and_string_fail_closed(self):
        for marker in ("1", True, 0, None):
            with self.subTest(marker=marker), self.assertRaises(
                mod.GsiLandslideInspectionError
            ):
                mod.inspect_archived_tile(sample({
                    "name": "合成", "disaster2": marker,
                }), URL)

    def test_wrong_source_and_injection_rejected(self):
        for url in (
            URL.replace("skhb02", "skhb01"),
            URL.replace("skhb02", "skhb03"),
            URL.replace("/10/", "/11/"),
            URL + "?token=test",
            "https://example.org/xyz/skhb02/10/909/403.geojson",
            "https://cyberjapandata.gsi.go.jp@evil.test/xyz/skhb02/10/909/403.geojson",
            URL.replace("/909/", "/1024/"),
        ):
            with self.subTest(url=url), self.assertRaises(
                mod.GsiLandslideInspectionError
            ):
                mod.inspect_archived_tile(sample(), url)

    def test_invalid_points_rejected(self):
        for point in ([float("nan"), 35], [200, 35], [139, True], [139], [139, 35, 0, 0]):
            with self.subTest(point=point), self.assertRaises(
                mod.GsiLandslideInspectionError
            ):
                mod.inspect_archived_tile(sample(coords=point), URL)

    def test_source_feature_outside_tile_refused_even_if_disaster2_one(self):
        with self.assertRaisesRegex(
            mod.GsiLandslideInspectionError, "outside source z10 tile"
        ):
            mod.inspect_archived_tile(sample(coords=[140.1, 35.7]), URL)

    def test_empty_tile_is_not_no_shelters_for_city(self):
        b = b'{"type":"FeatureCollection","features":[]}'
        out = mod.inspect_archived_tile(b, URL)
        self.assertEqual(out["status"], "TILE_EMPTY_MUNICIPAL_COVERAGE_UNKNOWN")
        self.assertEqual(out["source_feature_count"], 0)
        self.assertFalse(out["municipal_coverage_verified"])

    def test_bad_geojson_fails_closed(self):
        for b in (b"", b"not-json", b'{}', b"[]"):
            with self.subTest(raw=b), self.assertRaises(mod.GsiLandslideInspectionError):
                mod.inspect_archived_tile(b, URL)

    def test_raw_hash_is_byte_exact(self):
        from hashlib import sha256
        raw = sample()
        self.assertEqual(mod.inspect_archived_tile(raw, URL)["source_sha256"],
                         sha256(raw).hexdigest())

    def test_unofficial_area_and_open_state_are_not_made_up(self):
        record = mod.inspect_archived_tile(sample(), URL)
        self.assertNotIn("facility_suitability", record)
        self.assertNotIn("safest_site", record)
        self.assertFalse(record["municipal_site_opening_verified"])


if __name__ == "__main__":
    unittest.main()
