"""No external network and no real source fabricated; Phase-2 safety regression."""
import unittest

from src.hinanex.location_evidence_overlay import triage_candidate_spatial_evidence

KEY = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson#feature_index=571"
POLY = {"type":"Polygon","coordinates":[[
    [139.89,35.72],[139.91,35.72],[139.91,35.73],[139.89,35.73],[139.89,35.72]
]]}


def phase1(coordinates=None):
    return {
        "status":"LOCATION_TRIAGE_INTERNAL_ONLY_UNAPPROVED",
        "human_c_approved":False,
        "batch_source_status":"UNREVIEWED",
        "municipal_transcription_status":"AI_UNREVIEWED",
        "navigation_allowed_count":0,
        "safe_destination_count_approved":0,
        "source_raw_sha256":"a"*64,
        "city_address_prefix_candidate_count":1,
        "location_records":[{
            "source_feature_key":KEY,
            "reference_point":{"kind":"GSI_RAW_POINT_ONLY_NOT_AN_ENTRANCE",
                               "coordinates":coordinates or [139.9,35.725]},
            "facility_geometry":None,"navigation_endpoint":None,
            "may_offer_navigation":False,"may_publish_reference_point":False,
            "facility_identity_verified":False,
        }],
    }


def osm(**updates):
    record={
        "source_feature_key":KEY,
        "provider":"OSM",
        "provider_record_id":"way/123",
        "source_document_url":"https://www.openstreetmap.org/way/123",
        "source_archive_sha256":"b"*64,
        "common_id_raw":None,
        "candidate_geometry":POLY,
        "entrance_hints":[{
            "source_node_id":"node/44","coordinates":[139.89,35.725],
            "entrance_tag":"main","access_tag":"yes",
        }],
    }
    record.update(updates)
    return record


class EvidenceOverlayTests(unittest.TestCase):
    def test_even_entrance_yes_and_inside_geometry_never_authorizes(self):
        r=triage_candidate_spatial_evidence(phase1(),[osm()])
        self.assertEqual(r["status"],"LOCATION_SPATIAL_CANDIDATES_UNREVIEWED")
        self.assertEqual(r["human_review_required_count"],1)
        self.assertEqual(r["navigation_allowed_count"],0)
        self.assertFalse(r["human_c_approved"])
        row=r["review_queue"][0]
        self.assertEqual(row["candidate_evidence_unverified"][0]["reference_point_relation_unverified"],
                         "INSIDE_CANDIDATE_ONLY")
        self.assertEqual(row["candidate_evidence_unverified"][0]["entrance_hints_unverified"][0]
                         ["relative_to_candidate_geometry"],"ON_CANDIDATE_BOUNDARY_UNVERIFIED")
        self.assertIsNone(row["navigation_endpoint"])
        self.assertFalse(row["navigation_allowed"])
        self.assertFalse(row["official_common_id_verified_for_feature"])

    def test_no_evidence_means_unknown_not_no_facility(self):
        r=triage_candidate_spatial_evidence(phase1(),[])
        self.assertEqual(r["candidate_evidence_count"],0)
        self.assertIn("NO_EXTERNAL_ID_GEOMETRY_OR_ENTRANCE_EVIDENCE",
                      r["review_queue"][0]["review_reasons"])
        self.assertIsNone(r["review_queue"][0]["facility_geometry_verified"])
        self.assertEqual(r["approved_safe_destinations"],0)

    def test_candidate_point_outside_polygon_needs_review(self):
        r=triage_candidate_spatial_evidence(phase1([139.93,35.725]),[osm()])
        self.assertIn("REFERENCE_POINT_OUTSIDE_UNTRUSTED_GEOMETRY",
                      r["review_queue"][0]["review_reasons"])

    def test_unverified_private_or_wrong_entrance_never_directions(self):
        for tag,access in [("service","yes"),("yes","private"),("main",None),
                           ("exit","no")]:
            c=osm(entrance_hints=[{"source_node_id":"node/1",
                    "coordinates":[139.95,35.725],
                    "entrance_tag":tag,"access_tag":access}])
            r=triage_candidate_spatial_evidence(phase1(),[c])
            self.assertIn("ENTRANCE_OUTSIDE_CANDIDATE",r["review_queue"][0]["review_reasons"])
            self.assertEqual(r["navigation_allowed_count"],0)

    def test_bad_and_self_intersecting_polygons_fail_closed(self):
        cases=[
            {"type":"Polygon","coordinates":[[
                [139.89,35.72],[139.91,35.73],[139.89,35.73],
                [139.91,35.72],[139.89,35.72]]},
            {"type":"Polygon","coordinates":[[
                [139.89,35.72],[139.91,35.72],[139.91,35.73],
                [139.89,35.73]]},
            {"type":"Polygon","coordinates":[[
                [139.89,35.72],[139.91,35.72],[139.91,35.73],
                [139.89,35.73],[139.89,35.72]
            ],[
                [139.895,35.721],[139.897,35.721],
                [139.897,35.723],[139.895,35.721]]]},
        ]
        for shape in cases:
            with self.subTest(shape=shape),self.assertRaises(ValueError):
                triage_candidate_spatial_evidence(phase1(),[osm(candidate_geometry=shape)])

    def test_csv_id_unverified_even_with_exact_claim(self):
        c=osm(provider="GSI_CSV",provider_record_id="csv-row-1",
              source_document_url="https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html",
              common_id_raw="synthetic-id-42",candidate_geometry=None,entrance_hints=[])
        r=triage_candidate_spatial_evidence(phase1(),[c])
        row=r["review_queue"][0]
        self.assertIn("GSI_CSV_COMMON_ID_NOT_BOUND_TO_GEOJSON_ID",row["review_reasons"])
        self.assertFalse(row["official_common_id_verified_for_feature"])
        self.assertIsNone(row["navigation_endpoint"])

    def test_source_and_contract_spoofing_blocks(self):
        for mutated in (
            {"status":"APPROVED"},{"human_c_approved":True},
            {"navigation_allowed_count":1},
        ):
            with self.subTest(mutated=mutated),self.assertRaises(ValueError):
                triage_candidate_spatial_evidence({**phase1(),**mutated},[])
        for changed in (
            {"provider":"MALICIOUS"},{"source_feature_key":"different"},
            {"source_archive_sha256":"not-a-hash"},
            {"source_document_url":"https://evil.test/way/123"},
            {"official_approval":True},
            {"common_id_raw":"invented-without-csv"},
        ):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                triage_candidate_spatial_evidence(phase1(),[osm(**changed)])

    def test_multiple_evidence_not_assumed_same_facility(self):
        second=osm(provider_record_id="way/456",
                   source_document_url="https://www.openstreetmap.org/way/456")
        r=triage_candidate_spatial_evidence(phase1(),[osm(),second])
        self.assertIn("MULTIPLE_UNVERIFIED_SOURCE_CANDIDATES",
                      r["review_queue"][0]["review_reasons"])
        self.assertFalse(r["review_queue"][0]["navigation_allowed"])
