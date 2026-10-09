"""Synthetic C acceptance tests. No private municipality raw files in Git."""
import copy
import hashlib
import json
import unittest

from verify_edogawa_water_join import audit, AuditFailure, WATER_URL


def as_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def fixture():
    water_name = "小松川二小学校"
    location_name = "小松川第二小学校"
    html = (
        '<html><head><meta property="og:url" content="' + WATER_URL + '"></head>'
        '<body><table><tr><th>番号</th><th>名称</th><th>住所</th>'
        '<th>電話番号</th><th>使用可能階数</th></tr>'
        '<tr><td>2</td><td>' + water_name + '</td><td>小松川3丁目6番4号</td>'
        '<td>03-1234-5678</td><td>3階以上</td></tr></table></body></html>'
    ).encode("utf-8")
    csv_raw = (
        '名称,URL,災害種別記号,コメント,緯度,経度\n'
        + location_name + ',https://example.invalid/icon,a,,35.7000,139.8800\n'
    ).encode("cp932")
    key = '13123|' + location_name + '|35.7000000|139.8800000'
    facility_id = "edogawa-" + hashlib.sha256(key.encode()).hexdigest()[:16]
    record = {"id": facility_id, "name": location_name,
              "latitude": 35.7, "longitude": 139.88, "address": None,
              "supported_disasters": None, "facility_type": "shelter"}
    export = {"region": {"code": "13123"}, "meta": {"schema_version": "0.9"},
              "datasets": [{"requirement_code": "shelter_location",
                            "records": [record]}]}
    row = {
        "official_table": 1, "official_table_row": 2, "official_number_raw": "2",
        "official_name_raw": water_name, "official_address_raw": "小松川3丁目6番4号",
        "official_phone_raw": "03-1234-5678", "official_usable_floor_raw": "3階以上",
        "source_url": WATER_URL, "C_independent_verified": False,
        "D_scenario_status": "UNCHANGED_UNKNOWN",
        "candidate_class": "NAME_ABBREVIATION_HINT", "candidate_count": 1,
        "candidate_location_names": [location_name],
        "candidate_location_ids": [facility_id],
    }
    ledger = {
        "official_water_facility_ledger": [row],
        "location_record_lookup": [dict(record, flood_classification="UNKNOWN")]
    }
    return [html, csv_raw, export, ledger]


def verify(source):
    html, csv_raw, export, ledger = source
    return audit(html, csv_raw, as_bytes(export), as_bytes(ledger))


class EdogawaSnapshotAuditTests(unittest.TestCase):
    def test_rechecks_unapproved_abbreviation_without_promoting_hazard_status(self):
        outcome = verify(fixture())
        self.assertEqual(outcome["water_rows"], 1)
        self.assertEqual(outcome["csv_to_export_rows_rechecked"], 1)
        self.assertEqual(outcome["unapproved_hints"]["NAME_ABBREVIATION_HINT"], 1)
        self.assertEqual(outcome["c_approved_pairs"], 0)
        self.assertEqual(outcome["flood_candidates_or_exclusions_added"], 0)

    def test_original_usable_floor_cannot_be_mutated(self):
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["official_usable_floor_raw"] = "すべての階"
        with self.assertRaisesRegex(AuditFailure, "usable_floor_raw"):
            verify(doc)

    def test_original_address_cannot_be_replaced(self):
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["official_address_raw"] = "別住所"
        with self.assertRaisesRegex(AuditFailure, "address_raw"):
            verify(doc)

    def test_wrong_candidate_id_and_status_promotion_are_rejected(self):
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["candidate_location_ids"] = ["invented"]
        with self.assertRaisesRegex(AuditFailure, "candidate ID/name"):
            verify(doc)
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["D_scenario_status"] = "CANDIDATE"
        with self.assertRaisesRegex(AuditFailure, "unauthorized D classification"):
            verify(doc)

    def test_claimed_c_acceptance_is_rejected(self):
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["C_independent_verified"] = True
        with self.assertRaisesRegex(AuditFailure, "falsely claims C"):
            verify(doc)

    def test_unsupported_flood_scenario_promotion_is_rejected(self):
        doc = fixture()
        doc[2]["scenarios"] = [{
            "facility_results": [{"status": "CANDIDATE", "facility_id": "invented"}]
        }]
        with self.assertRaisesRegex(AuditFailure, "preapproval audit"):
            verify(doc)

    def test_source_coords_and_stable_id_are_checked(self):
        doc = fixture()
        doc[2]["datasets"][0]["records"][0]["latitude"] = 35.8
        with self.assertRaisesRegex(AuditFailure, "latitude or longitude"):
            verify(doc)
        doc = fixture()
        doc[2]["datasets"][0]["records"][0]["id"] = "wrong"
        with self.assertRaisesRegex(AuditFailure, "derived ID"):
            verify(doc)

    def test_csv_without_address_does_not_justify_added_address(self):
        doc = fixture()
        doc[2]["datasets"][0]["records"][0]["address"] = "小松川3丁目6番4号"
        with self.assertRaisesRegex(AuditFailure, "address not present"):
            verify(doc)

    def test_source_name_variation_must_be_explained(self):
        doc = fixture()
        doc[3]["official_water_facility_ledger"][0]["candidate_class"] = "NAME_ALIGNED_HINT"
        with self.assertRaisesRegex(AuditFailure, "nonmatching string"):
            verify(doc)

    def test_source_digest_mismatch_rejected(self):
        doc = fixture()
        doc[3]["summary"] = {"raw_source_file_sha256": [
            {"sha256": "0"*64}, {"sha256": "1"*64}, {"sha256": "2"*64}
        ]}
        with self.assertRaisesRegex(AuditFailure, "source SHA256"):
            verify(doc)

    def test_original_multiline_phone_normalization_is_reported(self):
        doc = fixture()
        doc[0] = doc[0].replace(b"03-1234-5678", b"03-1234-5678\n03-9012-3456")
        doc[3]["official_water_facility_ledger"][0]["official_phone_raw"] = (
            "03-1234-5678 03-9012-3456"
        )
        report = verify(doc)
        self.assertEqual(report["phone_whitespace_only_ledger_differences"], 1)
        doc[3]["official_water_facility_ledger"][0]["official_phone_raw"] = (
            "03-1234-5678 03-1111-2222"
        )
        with self.assertRaisesRegex(AuditFailure, "phone content differs"):
            verify(doc)

    def test_a_proposal_ledger_format_is_supported_but_not_certified(self):
        doc = fixture()
        html, csv_raw, export, old = doc
        old_row = old["official_water_facility_ledger"][0]
        rec = export["datasets"][0]["records"][0]
        proposed = {
            "region_code": "13123", "record_count_from_current_export": 1,
            "location_csv_columns": ["名称", "URL", "災害種別記号", "コメント", "緯度", "経度"],
            "all_reviewed_pairs": 0, "all_scenario_classifications_added": 0,
            "source_documents": [{"sha256": hashlib.sha256(blob).hexdigest()}
                                 for blob in (html, csv_raw, as_bytes(export))],
            "rows": [{
                "source_record_trace": "table=1;row=2",
                "number_raw": "2", "name_raw": old_row["official_name_raw"],
                "address_raw": old_row["official_address_raw"],
                "phone_raw": old_row["official_phone_raw"],
                "usable_floor_raw": old_row["official_usable_floor_raw"],
                "source_url": WATER_URL,
                "review_status": "UNREVIEWED",
                "flood_scenario_status": "UNCHANGED_UNKNOWN",
                "candidate_location_rows": [{
                    "location_facility_id": rec["id"],
                    "location_name_raw": rec["name"],
                    "location_address_raw": None,
                    "address_raw_exact_match": None,
                    "matching_basis": "ABBREVIATION_HINT_ONLY_NOT_VERIFIED",
                }],
            }],
        }
        doc[3] = proposed
        result = verify(doc)
        self.assertEqual(result["unapproved_hints"]["NAME_ABBREVIATION_HINT"], 1)
        self.assertEqual(result["c_approved_pairs"], 0)
        proposed["rows"][0]["review_status"] = "VERIFIED_PAIR"
        with self.assertRaisesRegex(AuditFailure, "verified pair"):
            verify(doc)


if __name__ == "__main__":
    unittest.main()
