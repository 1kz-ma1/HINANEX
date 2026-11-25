"""Offline negative regressions for GSI flood-vs-landslide source separation.

All data below is synthetic. These are NOT independent C acceptance, real
HTTPS replay, municipal coverage, or evidence of operating safe destinations.
"""
import json
from hashlib import sha256
import unittest

from src.hinanex.gsi_hazard_preflight import preflight_gsi_tile


URL_FLOOD = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
URL_LANDSLIDE = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
RETRIEVED_AT = "2026-11-13T03:00:00+00:00"


def record(**overrides):
    props = {
        "name": "架空の検証用地点",
        "address": "合成住所",
        "remarks": None,
        "disaster1": 1,
        "disaster2": 1,
    }
    props.update(overrides)
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Point", "coordinates": [139.1, 35.7]}}


def source(features=None):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [record()] if features is None else features,
    }, ensure_ascii=False).encode("utf-8")


def check(raw=None, hazard="landslide", url=None, digest=None, retrieved_at=RETRIEVED_AT):
    raw = source() if raw is None else raw
    return preflight_gsi_tile(
        raw, source_url=url or (URL_LANDSLIDE if hazard == "landslide" else URL_FLOOD),
        hazard=hazard,
        expected_sha256=digest if digest is not None else sha256(raw).hexdigest(),
        retrieved_at_utc=retrieved_at,
    )


class GsiCrossHazardPreflightTests(unittest.TestCase):
    def test_landslide_source_structure_does_not_grant_acceptance(self):
        result = check()
        self.assertEqual(result["status"], "H0_LOCAL_STRUCTURE_ONLY")
        self.assertEqual(result["hazard_dataset"], "GSI_SKHB02_LANDSLIDE")
        self.assertEqual(result["expected_hazard_attribute"], "disaster2")
        self.assertEqual(result["tile"], {"z": 10, "x": 909, "y": 403})
        self.assertEqual(result["archive_feature_count"], 1)
        self.assertEqual(result["source_origin"], "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED")
        for k in ("independent_c_acceptance", "publication_approval"):
            self.assertNotIn(result[k], ("PASS", "GRANTED"))
        self.assertEqual(result["official_https_byte_replay"], "NOT_RUN")

    def test_flood_source_structure_is_independently_scoped(self):
        result = check(hazard="flood")
        self.assertEqual(result["hazard_dataset"], "GSI_SKHB01_FLOOD")
        self.assertEqual(result["expected_hazard_attribute"], "disaster1")
        self.assertEqual(result["source_url"], URL_FLOOD)

    def test_other_disaster_attributes_do_not_become_authorized(self):
        only_landslide = record(disaster1=None, disaster2=1)
        result = check(raw=source([only_landslide]))
        self.assertEqual(result["hazard"], "landslide")
        with self.assertRaisesRegex(ValueError, "disaster1=1"):
            check(raw=source([only_landslide]), hazard="flood")

    def test_flood_layer_is_not_substitute_for_landslide_layer(self):
        with self.assertRaisesRegex(ValueError, "requested hazard"):
            check(hazard="landslide", url=URL_FLOOD)
        with self.assertRaisesRegex(ValueError, "requested hazard"):
            check(hazard="flood", url=URL_LANDSLIDE)

    def test_absent_disaster2_rejects_every_feature(self):
        bad = record()
        del bad["properties"]["disaster2"]
        with self.assertRaisesRegex(ValueError, "disaster2=1"):
            check(raw=source([record(), bad]))

    def test_not_matching_designation_or_boolean_is_rejected(self):
        for marker in ("1", 0, True, False, None, 2):
            with self.subTest(marker=marker), self.assertRaisesRegex(ValueError, "disaster2=1"):
                check(raw=source([record(disaster2=marker)]))

    def test_unsupported_hazard_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported hazard"):
            check(hazard="earthquake", url=URL_LANDSLIDE)

    def test_wrong_url_scheme_host_path_or_params(self):
        variants = [
            URL_LANDSLIDE.replace("https:", "http:"),
            URL_LANDSLIDE.replace("cyberjapandata.gsi.go.jp", "attacker.example"),
            URL_LANDSLIDE.replace("cyberjapandata.gsi.go.jp", "cyberjapandata.gsi.go.jp.evil.example"),
            URL_LANDSLIDE.replace("cyberjapandata.gsi.go.jp", "user@cyberjapandata.gsi.go.jp"),
            URL_LANDSLIDE.replace("cyberjapandata.gsi.go.jp", "cyberjapandata.gsi.go.jp:443"),
            URL_LANDSLIDE.replace("/10/", "/11/"),
            URL_LANDSLIDE.replace("/909/", "/0909/"),
            URL_LANDSLIDE.replace("/909/", "/1024/"),
            URL_LANDSLIDE.replace("/403.", "/1024."),
            URL_LANDSLIDE + "?cache=true",
            URL_LANDSLIDE + "#row0",
            URL_LANDSLIDE.replace(".geojson", ".json"),
        ]
        for url in variants:
            with self.subTest(url=url), self.assertRaises(ValueError):
                check(url=url)

    def test_lowercase_exact_sha256_required(self):
        raw = source()
        for digest in ("0"*64, "ab", "G"*64, "A"*64):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                check(raw=raw, digest=digest)

    def test_local_hash_match_does_not_mean_gsi_byte_attestation(self):
        result = check()
        self.assertEqual(result["source_sha256"], sha256(source()).hexdigest())
        self.assertEqual(result["independent_c_acceptance"], "NOT_GRANTED")
        self.assertEqual(result["official_https_byte_replay"], "NOT_RUN")

    def test_empty_archive_has_distinct_unverified_status(self):
        result = check(raw=source([]))
        self.assertEqual(result["status"], "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF")
        self.assertEqual(result["archive_feature_count"], 0)
        self.assertEqual(result["municipal_coverage"], "NOT_DETERMINED")

    def test_missing_archive_or_invalid_bytes_are_not_empty_coverage(self):
        for data in (b"", b"{", b"\xff", b"<html>not found</html>", b"null"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                check(raw=data)

    def test_missing_or_invalid_feature_collection_rejected(self):
        for doc in (
            {},
            {"type": "FeatureCollection"},
            {"type": "FeatureCollection", "features": {}},
            {"type": "Feature", "features": []},
            {"type": "FeatureCollection", "features": [None]},
        ):
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                check(raw=json.dumps(doc).encode())

    def test_duplicate_json_keys_not_silently_resolved(self):
        raw = b'{"type":"FeatureCollection","features":[],"features":[]}'
        with self.assertRaisesRegex(ValueError, "duplicate keys"):
            check(raw=raw)

    def test_non_json_nan_rejected(self):
        raw = b'{"type":"FeatureCollection","features":[NaN]}'
        with self.assertRaisesRegex(ValueError, "non-JSON"):
            check(raw=raw)

    def test_geometry_type_and_coordinate_validation(self):
        variants = [
            {"type": "Polygon", "coordinates": []},
            {"type": "Point", "coordinates": []},
            {"type": "Point", "coordinates": [139.1]},
            {"type": "Point", "coordinates": [139.1, 35.7, 10, 20]},
            {"type": "Point", "coordinates": [139.1, 91]},
            {"type": "Point", "coordinates": [181, 35.7]},
            {"type": "Point", "coordinates": [True, 35.7]},
            {"type": "Point", "coordinates": [139.1, None]},
            {"type": "Point", "coordinates": [139.1, 35.7, "z"]},
        ]
        for geom in variants:
            with self.subTest(geom=geom), self.assertRaises(ValueError):
                feature = record()
                feature["geometry"] = geom
                check(raw=source([feature]))

    def test_source_name_and_optional_properties_must_not_be_forged(self):
        for props in ({"name": ""}, {"name": None}, {"address": 100}, {"remarks": []}):
            with self.subTest(props=props), self.assertRaises(ValueError):
                check(raw=source([record(**props)]))

    def test_retrieval_time_must_be_real_utc_iso8601(self):
        for time in ("", "2026-11-13", "2026-11-13T03:00:00",
                     "2026-11-13T12:00:00+09:00", "not a time",
                     "2026-13-13T03:00:00Z"):
            with self.subTest(time=time), self.assertRaises(ValueError):
                check(retrieved_at=time)

    def test_does_not_require_or_infer_other_disaster_markers(self):
        result = check(raw=source([record(disaster1=None)]))
        self.assertEqual(result["hazard"], "landslide")
        self.assertEqual(result["archive_feature_count"], 1)
        self.assertNotIn("disaster1_raw", result)
        self.assertNotIn("sites", result)

    def test_all_rows_in_tile_checked_including_last(self):
        rows = [record() for _ in range(20)]
        rows[-1]["properties"]["disaster2"] = False
        with self.assertRaisesRegex(ValueError, "feature 19"):
            check(raw=source(rows))

    def test_feature_identity_and_safety_are_not_inferred(self):
        result = check()
        for key in ("facility_identity", "current_open_status", "hazard_safety"):
            self.assertIn(result[key], ("NOT_APPROVED", "NOT_EVALUATED"))
        self.assertNotIn("accepted_sites", result)
        self.assertNotIn("coordinates", result)
        self.assertNotIn("municipality_code", result)


if __name__ == "__main__":
    unittest.main()
