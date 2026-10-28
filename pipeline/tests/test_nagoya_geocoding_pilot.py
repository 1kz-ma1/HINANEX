import math
import unittest
from unittest.mock import patch

from geocode_nagoya_pilot import classify, full_address, local_url, prepare, resolve


def sample(count=60):
    wards = ["千種区", "中区", "緑区", "熱田区"]
    return {
        "records": [
            {"id": f"test-{i}", "name": f"架空施設{i}",
             "administrative_area": wards[i % 4],
             "address": f"仮町{i}-2-5", "latitude": None, "longitude": None}
            for i in range(count)
        ]
    }


def provider(address="愛知県名古屋市千種区千種3-2-5", ward="千種区", level="rsdtdsp_blk"):
    return {"type": "FeatureCollection", "query": {"address": address},
            "features": [{"type": "Feature",
                "geometry": {"type": "Point", "coordinates": [136.93, 35.16]},
                "properties": {
                    "matched_address": address, "unmatched_address": [],
                    "coordinates_level": level,
                    "structured_address": {"pref": "愛知県", "city": "名古屋市", "ward": ward},
                }}]}


class NagoyaGeocodingPilotTests(unittest.TestCase):
    def test_deterministic_50_wide_ward_selection(self):
        output = prepare(sample(), "sample-hash")
        self.assertEqual(len(output["selected"]), 50)
        self.assertEqual(len({r["ward"] for r in output["selected"][:4]}), 4)
        self.assertNotIn("latitude", output["selected"][0])
        self.assertFalse(output["approved_for_map"])

    def test_skips_original_coordinates(self):
        data = sample(2)
        data["records"][0]["latitude"] = 35.16
        data["records"][0]["longitude"] = 136.93
        outcome = prepare(data, "hash")
        self.assertEqual(outcome["skipped"]["has_source_coordinates"], 1)
        self.assertEqual(len(outcome["selected"]), 1)

    def test_duplicate_record_id_rejected(self):
        data = sample(2)
        data["records"][1]["id"] = data["records"][0]["id"]
        with self.assertRaises(ValueError):
            prepare(data, "hash")

    def test_prefix_and_ward_conflict(self):
        self.assertEqual(full_address("千種区", "千種3-2-5"), "愛知県名古屋市千種区千種3-2-5")
        self.assertEqual(full_address("千種区", "名古屋市千種区千種3-2-5"), "愛知県名古屋市千種区千種3-2-5")
        with self.assertRaises(ValueError):
            full_address("千種区", "名古屋市中区1-2-3")

    def test_candidate_never_approved(self):
        result = classify(provider(), "愛知県名古屋市千種区千種3-2-5", "千種区")
        self.assertEqual(result["status"], "UNVERIFIED_CANDIDATE")
        self.assertEqual(result["derived_geometry"], {"latitude": 35.16, "longitude": 136.93})
        self.assertFalse(result["approved_for_map"])

    def test_parcel_level_is_review_only_even_with_full_address(self):
        address = "愛知県名古屋市千種区千種3-2-5"
        point = classify(provider(level="parcel"), address, "千種区")
        self.assertEqual(point["status"], "NEEDS_REVIEW")
        self.assertEqual(point["reason"], "parcel_reference_offset_risk")
        self.assertEqual(point["coordinates_level"], "parcel")
        self.assertFalse(point["approved_for_map"])

    def test_query_mismatch(self):
        self.assertEqual(classify(provider(), "愛知県名古屋市千種区他1", "千種区")["reason"], "query_mismatch")

    def test_wrong_ward_and_low_precision(self):
        address = "愛知県名古屋市千種区千種3-2-5"
        self.assertEqual(classify(provider(ward="中区"), address, "千種区")["reason"], "outside_city_or_ward")
        self.assertEqual(classify(provider(level="machiaza"), address, "千種区")["reason"], "low_resolution_or_unknown_level")

    def test_same_ward_but_different_house_number_is_unresolved(self):
        expected = "愛知県名古屋市千種区千種3-2-5"
        data = provider()
        data["features"][0]["properties"]["matched_address"] = "愛知県名古屋市千種区千種3-2-6"
        self.assertEqual(
            classify(data, expected, "千種区")["reason"],
            "different_street_or_house_number",
        )

    def test_fullwidth_digits_and_address_delimiters_are_equivalent(self):
        expected = "愛知県名古屋市千種区千種3-2-5"
        data = provider()
        data["features"][0]["properties"]["matched_address"] = "愛知県名古屋市千種区千種３丁目２番５号"
        self.assertEqual(classify(data, expected, "千種区")["status"], "UNVERIFIED_CANDIDATE")

    def test_mismatched_town_rejected_despite_same_ward(self):
        expected = "愛知県名古屋市千種区千種3-2-5"
        data = provider()
        data["features"][0]["properties"]["matched_address"] = "愛知県名古屋市千種区今池3-2-5"
        self.assertEqual(classify(data, expected, "千種区")["status"], "UNRESOLVED")

    def test_ambiguous_and_unmatched_are_unresolved(self):
        addr = "愛知県名古屋市千種区千種3-2-5"
        data = provider()
        data["features"].append(data["features"][0])
        self.assertEqual(classify(data, addr, "千種区")["reason"], "missing_or_ambiguous_match")
        data["features"].pop()
        data["features"][0]["properties"]["unmatched_address"] = ["建物部分"]
        self.assertEqual(classify(data, addr, "千種区")["reason"], "unmatched_address")

    def test_invalid_coordinates(self):
        addr = "愛知県名古屋市千種区千種3-2-5"
        data = provider()
        data["features"][0]["geometry"]["coordinates"] = [136.93, math.nan]
        self.assertEqual(classify(data, addr, "千種区")["reason"], "invalid_numeric_coordinates")
        data["features"][0]["geometry"]["coordinates"] = [True, 35.16]
        self.assertEqual(classify(data, addr, "千種区")["reason"], "invalid_numeric_coordinates")

    def test_only_16_official_nagoya_wards_accepted(self):
        source = sample(4)
        source["records"][0]["administrative_area"] = "足立区"
        manifest = prepare(source, "digest")
        self.assertEqual(manifest["skipped"]["out_of_scope_ward"], 1)
        self.assertEqual(len(manifest["selected"]), 3)
        with self.assertRaises(ValueError):
            full_address("足立区", "西新井1-1")
        with self.assertRaises(ValueError):
            prepare({"records": [source["records"][0]]}, "digest")

    def test_zero_or_missing_earth_coordinate_not_a_candidate(self):
        address = "愛知県名古屋市千種区千種3-2-5"
        point = provider()
        point["features"][0]["geometry"]["coordinates"] = [0, 0]
        self.assertEqual(classify(point, address, "千種区")["reason"], "out_of_range_coordinates")

    @patch("geocode_nagoya_pilot.fetch_json")
    def test_shared_reference_geometry_across_ward_records_needs_review(self, mocked):
        source = sample(2)
        manifest = prepare(source, "same-source")
        rows = manifest["selected"]
        mocked.side_effect = [
            ({"status": "ok"}, b'{"status":"ok"}'),
            ({"name": "abrg", "db_version": "synthetic", "version": "synthetic"}, b'{}'),
            (provider(rows[0]["query_address"], rows[0]["ward"]), b'{"test": 1}'),
            (provider(rows[1]["query_address"], rows[1]["ward"], "parcel"), b'{"test": 2}'),
        ]
        result = resolve(manifest, source, "same-source", "http://127.0.0.1:3000")
        self.assertEqual(result["statuses"], {"NEEDS_REVIEW": 2})
        self.assertTrue(all(not row["approved_for_map"] for row in result["results"]))
        self.assertIn("parcel_reference_offset_risk", result["results"][1]["reason"])
        self.assertIn("shared_reference_coordinate", result["results"][1]["reason"])

    def test_rejects_nonlocal_geocoder(self):
        for url in ("https://127.0.0.1:3000", "http://example.org:3000",
                    "http://127.0.0.1:3000/evil", "http://user:pw@127.0.0.1:3000"):
            with self.assertRaises(ValueError):
                local_url(url)
        self.assertEqual(local_url("http://localhost:3000"), "http://localhost:3000")

    def test_stale_manifest_rejected_before_http(self):
        with self.assertRaises(ValueError):
            resolve(prepare(sample(1), "old"), sample(1), "new", "http://127.0.0.1:3000")

    @patch("geocode_nagoya_pilot.fetch_json")
    def test_reject_tampered_manifest_before_network(self, mocked):
        source = sample(3)
        original = prepare(source, "digest")
        for field, new_value in (
            ("record_id", "spoofed-site"),
            ("query_address", "愛知県名古屋市千種区別の場所1"),
            ("name", "別の施設"),
            ("source_address", "別の場所1"),
        ):
            manifest = {
                **original,
                "selected": [dict(row) for row in original["selected"]],
            }
            manifest["selected"][0][field] = new_value
            with self.subTest(field=field), self.assertRaises(ValueError):
                resolve(manifest, source, "digest", "http://127.0.0.1:3000")
        mocked.assert_not_called()

    @patch("geocode_nagoya_pilot.fetch_json")
    def test_reject_swapped_dataset_same_digest_claim(self, mocked):
        source = sample(3)
        manifest = prepare(source, "digest")
        different = sample(3)
        different["records"][0]["address"] = "別の場所5-7"
        with self.assertRaises(ValueError):
            resolve(manifest, different, "digest", "http://127.0.0.1:3000")
        mocked.assert_not_called()

    @patch("geocode_nagoya_pilot.fetch_json")
    def test_mocked_provider_pipeline_is_unverified_only(self, mocked):
        source = sample(1)
        manifest = prepare(source, "digest")
        record = manifest["selected"][0]
        mocked.side_effect = [
            ({"status": "ok"}, b'{"status":"ok"}'),
            ({"name": "abrg", "db_version": "synthetic", "version": "synthetic"}, b'{}'),
            (provider(record["query_address"], record["ward"]), b'{"synthetic":true}'),
        ]
        result = resolve(manifest, source, "digest", "http://127.0.0.1:3000")
        self.assertEqual(result["statuses"], {"UNVERIFIED_CANDIDATE": 1})
        self.assertFalse(result["approved_for_map"])
        self.assertFalse(result["data_promotion_authorized"])
        self.assertFalse(result["results"][0]["approved_for_map"])


if __name__ == "__main__":
    unittest.main()
