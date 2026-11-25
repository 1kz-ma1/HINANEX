"""Synthetic input-only tests: C never approves CSV-to-GeoJSON identity."""
import json
from hashlib import sha256
import unittest
from compare_gsi_csv_geojson_candidates import compare_gsi_origins

def fixture(scope="national",name="SYNTHETIC SCHOOL",address="千葉県市川市大洲4-18-1",
            marker="1",latitude="35.7",idval="0000123"):
    record={"type":"Feature","properties":{"name":"SYNTHETIC SCHOOL",
        "address":"千葉県市川市大洲4-18-1","disaster2":1},
        "geometry":{"type":"Point","coordinates":[139.9,35.7]}}
    raw=json.dumps({"type":"FeatureCollection","features":[record]},ensure_ascii=False).encode()
    row=["1",idval]
    if scope=="national":row.append("千葉県市川市")
    row.extend([name,address,"",marker,"","","","","","","",latitude,"139.9",""])
    assert len(row)==(17 if scope=="national" else 16),len(row)
    return raw,(",".join(row)+"\n").encode()

def check(g,c,scope="national",**kw):
    return compare_gsi_origins(g,c,scope=scope,
        expected_gsi_sha256=sha256(g).hexdigest(),
        expected_csv_sha256=sha256(c).hexdigest(),**kw)

class CSVGeoJSONTests(unittest.TestCase):
    def test_exact_match_is_not_identity(self):
        g,c=fixture()
        out=check(g,c)
        self.assertEqual(out["classifications"],{"TEXT_AND_COORDINATES_AGREE_UNAPPROVED":1})
        self.assertEqual(out["rows"][0]["csv_candidates"][0]["common_id_raw_unbound"],"0000123")
        self.assertFalse(out["common_id_to_geojson_verified"])
        self.assertFalse(out["human_c_approved"])
        self.assertEqual(out["navigation_allowed_count"],0)
        self.assertIsNone(out["rows"][0]["navigation_endpoint"])
    def test_municipal_scope_does_not_prove_source_origin(self):
        g,c=fixture(scope="municipality")
        out=check(g,c,scope="municipality")
        self.assertEqual(out["gsi_city_address_prefix_count"],1)
        self.assertFalse(out["official_csv_acquisition_authenticated"])
    def test_mismatch_causes_review_not_auto_join(self):
        for opts,decision in [
            ({"name":"OTHER"},"NO_SAME_NAME_CSV_RECORD_UNKNOWN"),
            ({"address":"千葉県市川市市川南3"},"NAME_AGREES_ADDRESS_DIFFERS"),
            ({"latitude":"35.7003"},"NAME_ADDRESS_AGREE_COORDINATES_DIFFER"),
            ({"marker":""},"CSV_LANDSLIDE_MARKER_DISAGREES"),
        ]:
            with self.subTest(opts=opts):
                g,c=fixture(**opts)
                self.assertEqual(check(g,c)["classifications"],{decision:1})
    def test_duplicate_names_are_ambiguous(self):
        g,c=fixture()
        c=c+c.replace(b"1,0000123",b"2,0000123")
        self.assertEqual(check(g,c)["classifications"],{"MULTIPLE_SAME_NAME_CSV_RECORDS":1})
    def test_mismatch_sha_rejected(self):
        g,c=fixture()
        with self.assertRaisesRegex(ValueError,"HASH_MISMATCH"):
            compare_gsi_origins(g,c,expected_gsi_sha256="0"*64,
                                expected_csv_sha256=sha256(c).hexdigest())
    def test_malformed_source_and_layout_rejected(self):
        g,c=fixture()
        with self.assertRaises(ValueError):check(g,c,scope="municipality")
        with self.assertRaises(ValueError):check(g,c,encoding="auto")
        with self.assertRaises(ValueError):check(g,c.replace(b",1,",b",2,"))
        bad=json.loads(g);bad["features"][0]["properties"]["disaster2"]=False
        mod=json.dumps(bad,ensure_ascii=False).encode()
        with self.assertRaisesRegex(ValueError,"MARKER"):check(mod,c)
    def test_missing_csv_coordinates_are_unknown(self):
        g,c=fixture(latitude="")
        with self.assertRaisesRegex(ValueError,"PARTIAL_COORDINATES"):check(g,c)
