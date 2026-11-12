"""Synthetic reference-only location triage; no source or human approvals."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from src.hinanex.location_verification import triage_ichikawa_location

SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
PDF = "https://www.city.ichikawa.lg.jp/uploaded/attachment/55017.pdf"


def fixture():
    items = [
        ("SYNTHETIC SCHOOL", "千葉県市川市大洲4-18-1"),
        ("SYNTHETIC PARK 公園", "千葉県市川市大洲1-18"),
        ("SYNTHETIC 江戸川河川敷緑地", "千葉県市川市市川南3"),
    ]
    features = [
        {"type": "Feature", "properties": {
            "name": name, "address": address, "disaster2": 1,
        }, "geometry": {"type": "Point", "coordinates": [139.9, 35.7]}}
        for name, address in items
    ]
    raw = json.dumps({"type": "FeatureCollection", "features": features},
                     ensure_ascii=False).encode()
    entries = [
        {"gsi_feature_index": i, "city_section": "A",
         "city_row_number": i + 1, "city_name": name,
         "city_address": (
             "市川南3・4丁目地先" if i == 2
             else addr.removeprefix("千葉県市川市")
         ),
         "city_pdf_url": PDF, "landslide_symbol_transcribed": "○"}
        for i, (name, addr) in enumerate(items)
    ]
    ledger = {
        "status": "AI_TRANSCRIBED_OFFICIAL_TABLE_UNAPPROVED",
        "gsi_source_url": SOURCE, "gsi_sha256": sha256(raw).hexdigest(),
        "expected_total_tile_features": len(features),
        "candidate_address_prefix": "千葉県市川市",
        "city_page_url": "https://www.city.ichikawa.lg.jp/page/40332.html",
        "city_page_update_date": "2026-09-08",
        "transcription_method":
        "AI_EXTRACTED_FROM_OFFICIAL_HTML_AND_PDF_RENDER_NOT_HUMAN_APPROVED",
        "municipal_pdf_hazard_column_label": "土砂災害",
        "rows": entries,
    }
    return raw, ledger


class LocationTriageTests(unittest.TestCase):
    def test_text_match_is_not_entrance_or_permission(self):
        raw, reference = fixture()
        out = triage_ichikawa_location(raw, reference)
        self.assertEqual(out["status"], "LOCATION_TRIAGE_INTERNAL_ONLY_UNAPPROVED")
        self.assertEqual(out["tile_source_feature_count"], 3)
        self.assertEqual(out["text_exact_count"], 2)
        self.assertEqual(out["text_difference_count"], 1)
        self.assertEqual(out["location_exception_count"], 2)
        self.assertEqual({x["gsi_feature_index"] for x in out["human_location_review_queue"]},
                         {1, 2})
        self.assertEqual(out["navigation_allowed_count"], 0)
        for row in out["location_records"]:
            self.assertEqual(row["reference_point"]["coordinates"], [139.9, 35.7])
            self.assertIsNone(row["facility_geometry"])
            self.assertIsNone(row["navigation_endpoint"])
            for key in ("may_publish_reference_point", "may_offer_navigation",
                        "facility_identity_verified", "municipal_document_human_approved"):
                self.assertIs(row[key], False)
        self.assertEqual(out["human_location_review_queue"][-1]["priority"], "HIGH")
        self.assertIs(out["human_c_approved"], False)

    def test_source_record_mutation_and_hash_change_fail_closed(self):
        raw, ref = fixture()
        with self.assertRaisesRegex(ValueError, "HASH"):
            triage_ichikawa_location(raw + b" ", ref)
        for k, v in (
            ("gsi_sha256", "0"*64), ("status", "HUMAN_APPROVED"),
            ("gsi_source_url", "https://evil.example/fake"),
            ("city_page_url", "https://evil.example/fake"),
            ("candidate_address_prefix", "千葉県江戸川区"),
        ):
            with self.subTest(k=k), self.assertRaises(ValueError):
                triage_ichikawa_location(raw, {**ref, k: v})

    def test_unrecorded_city_site_and_duplicate_index_are_blocked(self):
        raw, ref = fixture()
        for wrong in ({**ref, "rows": ref["rows"][:-1]},
                      {**ref, "rows": ref["rows"]+[ref["rows"][0]]}):
            with self.assertRaises(ValueError):
                triage_ichikawa_location(raw, wrong)

    def test_gsi_hazard_marker_cannot_be_inferred_from_name(self):
        raw, ref = fixture()
        doc = json.loads(raw)
        doc["features"][0]["properties"]["disaster2"] = 0
        bad = json.dumps(doc, ensure_ascii=False).encode()
        with self.assertRaisesRegex(ValueError, "MARKER"):
            triage_ichikawa_location(bad, {**ref, "gsi_sha256": sha256(bad).hexdigest()})

    def test_reference_city_hazard_symbol_cannot_be_forged(self):
        raw, ref = fixture()
        bad = deepcopy(ref)
        bad["rows"][0]["landslide_symbol_transcribed"] = "－"
        with self.assertRaisesRegex(ValueError, "CITY_TEXT"):
            triage_ichikawa_location(raw, bad)

    def test_gsi_point_must_belong_to_source_tile_and_be_finite(self):
        raw, ref = fixture()
        for coord in ([140.1, 35.7], [139.9, float("nan")], [139.9, True]):
            doc = json.loads(raw)
            doc["features"][0]["geometry"]["coordinates"] = coord
            modified = json.dumps(doc, ensure_ascii=False).encode()
            with self.subTest(coord=coord), self.assertRaises(ValueError):
                triage_ichikawa_location(
                    modified, {**ref, "gsi_sha256": sha256(modified).hexdigest()}
                )

    def test_exact_match_still_requires_source_level_human_review(self):
        raw, ref = fixture()
        doc = json.loads(raw)
        doc["features"][1]["properties"]["name"] = "SYNTHETIC PLACE"
        doc["features"][2]["properties"]["name"] = "SYNTHETIC BUILDING"
        modified = json.dumps(doc, ensure_ascii=False).encode()
        rows = deepcopy(ref["rows"])
        rows[1]["city_name"] = "SYNTHETIC PLACE"
        rows[2]["city_name"] = "SYNTHETIC BUILDING"
        rows[2]["city_address"] = "市川南3"
        checked = triage_ichikawa_location(
            modified, {**ref, "gsi_sha256": sha256(modified).hexdigest(), "rows": rows}
        )
        self.assertEqual(checked["location_exception_count"], 0)
        self.assertEqual(checked["navigation_allowed_count"], 0)
        self.assertFalse(checked["human_c_approved"])


if __name__ == "__main__":
    unittest.main()
