"""Synthetic only: C independently compares A's skhb02 preview with raw bytes."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from verify_gsi_skhb02_archive import verify_archived_skhb02

URL="https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"

def fixture(features=None):
    if features is None:
        features=[{"type":"Feature","properties":{
            "name":"SYNTHETIC ONLY","address":None,"remarks":"test",
            "disaster1":1,"disaster2":1},
            "geometry":{"type":"Point","coordinates":[139.9,35.7]}}]
    raw=json.dumps({"type":"FeatureCollection","features":features},
                   ensure_ascii=False).encode()
    rows=[{
        "feature_index":i, "name_raw":f["properties"]["name"],
        "address_raw":f["properties"].get("address"),
        "remarks_raw":f["properties"].get("remarks"),
        "coordinates_raw":f["geometry"]["coordinates"],
        "disaster2_raw":f["properties"].get("disaster2"),
        "source_feature_ref":URL+"#feature_index="+str(i),
        "not_current_open_or_safe":True,
        "not_a_cross_source_facility_identity":True,
    } for i,f in enumerate(features)]
    a={"purpose":"A_SKHB02_SOURCE_FEASIBILITY_ONLY",
       "source_url":URL,"source_sha256":sha256(raw).hexdigest(),
       "source_byte_count":len(raw),"source_tile":{"z":10,"x":909,"y":403},
       "source_feature_count":len(features),
       "raw_feature_previews_for_human_review":rows,
       "hazard":"landslide","official_attribute":"disaster2",
       "source_kind":"designated_emergency_evacuation_place",
       "not_a_landslide_risk_layer":True,"municipal_coverage_verified":False,
       "municipal_site_opening_verified":False,
       "independent_c_approved":False,"safe_destination_count_approved":0,
       "not_for_publication":True,
       "status":"SOURCE_TILE_INSPECTED_UNREVIEWED" if features else
                "TILE_EMPTY_MUNICIPAL_COVERAGE_UNKNOWN"}
    return raw,a


class CSourceReplayTests(unittest.TestCase):
    def test_match_is_not_approval(self):
        raw,report=fixture()
        r=verify_archived_skhb02(raw,URL,report)
        self.assertEqual(r["status"],"C_LOCAL_MATCH_UNAPPROVED")
        self.assertEqual(r["raw_sha256"],sha256(raw).hexdigest())
        self.assertEqual(r["safe_destination_count_approved"],0)
        for key in ("official_origin_authenticated","independent_human_approved",
                    "municipal_coverage_verified","c_publication_approved"):
            self.assertFalse(r[key])

    def test_report_mutation_or_promotion_fails(self):
        raw,report=fixture()
        for key,val in (
            ("independent_c_approved",True),("not_for_publication",False),
            ("municipal_coverage_verified",True),
            ("source_tile",{"z":10,"x":909,"y":404}),
            ("source_sha256","0"*64),("status","ACCEPTED"),
            ("safe_destination_count_approved",True)):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    verify_archived_skhb02(raw,URL,{**report,key:val})

    def test_row_reorder_and_forged_coordinates_fail(self):
        raw,report=fixture()
        for key,val in (
            ("name_raw","FAKE"),("coordinates_raw",[140,35]),
            ("disaster2_raw",True),("source_feature_ref","FAKE"),
            ("feature_index",9),("not_current_open_or_safe",False)):
            with self.subTest(key=key):
                fake=deepcopy(report)
                fake["raw_feature_previews_for_human_review"][0][key]=val
                with self.assertRaises(ValueError):
                    verify_archived_skhb02(raw,URL,fake)

    def test_even_self_consistent_point_in_wrong_tile_fails(self):
        raw,report=fixture()
        doc=json.loads(raw)
        doc["features"][0]["geometry"]["coordinates"]=[140.1,35.7]
        altered=json.dumps(doc,ensure_ascii=False).encode()
        report["source_sha256"]=sha256(altered).hexdigest()
        report["source_byte_count"]=len(altered)
        report["raw_feature_previews_for_human_review"][0]["coordinates_raw"]=[140.1,35.7]
        with self.assertRaisesRegex(ValueError,"OUTSIDE_GSI_TILE"):
            verify_archived_skhb02(altered,URL,report)

    def test_missing_disaster2_is_not_landslide(self):
        raw,report=fixture()
        source=json.loads(raw)
        del source["features"][0]["properties"]["disaster2"]
        mutated=json.dumps(source,ensure_ascii=False).encode()
        report["source_sha256"]=sha256(mutated).hexdigest()
        report["source_byte_count"]=len(mutated)
        report["raw_feature_previews_for_human_review"][0]["disaster2_raw"]=None
        with self.assertRaisesRegex(ValueError,"WRONG_HAZARD"):
            verify_archived_skhb02(mutated,URL,report)

    def test_zero_tile_is_not_municipal_no_sites(self):
        raw,a=fixture([])
        result=verify_archived_skhb02(raw,URL,a)
        self.assertEqual(result["status"],"C_EMPTY_TILE_COVERAGE_UNKNOWN")
        self.assertFalse(result["municipal_coverage_verified"])

    def test_bad_url_and_archive(self):
        raw,a=fixture()
        for url in (URL.replace("skhb02","skhb01"),URL.replace("/10/","/11/"),
                    "http://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson",
                    "https://evil.test/xyz/skhb02/10/909/403.geojson"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                verify_archived_skhb02(raw,url,a)
        with self.assertRaises(ValueError):
            verify_archived_skhb02(b"broken",URL,a)


if __name__=="__main__":
    unittest.main()
