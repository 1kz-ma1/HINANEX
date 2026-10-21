"""Offline C tests: three-source matrix must never be an approval or spatial join."""
import copy
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from verify_edogawa_three_source_review import audit, ThreeSourceAuditFailure
from verify_edogawa_water_join import WATER_URL

GSI = {"共通ID": "GSI-test-1", "施設・場所名": "新小学校",
       "住所": "東京都江戸川区平井4-1-23", "洪水": "", "地震": "1",
       "緯度": "35.7", "経度": "139.8"}


def inputs():
    water = (
        '<html><body>' + WATER_URL +
        '<table><tr><th>番号</th><th>名称</th><th>住所</th>'
        '<th>電話番号</th><th>使用可能階数</th></tr>'
        '<tr><td>1</td><td>新小学校</td><td>平井4丁目1番23号</td>'
        '<td>03-0000-0000</td><td>2階以上</td></tr>'
        '</table></body></html>'
    ).encode()
    d = {"datasets": [{"requirement_code": "shelter_location", "records": [
        {"id": "d-one", "name": "新小学校", "latitude": 35.7,
         "longitude": 139.8},
    ]}], "region": {"code": "13123"}}
    d_bytes = json.dumps(d).encode()
    aw = {"all_reviewed_pairs": 0, "all_scenario_classifications_added": 0,
          "rows": [{"source_record_trace": "table=1;row=2",
                    "number_raw": "1", "name_raw": "新小学校",
                    "address_raw": "平井4丁目1番23号",
                    "usable_floor_raw": "2階以上",
                    "candidate_location_rows": [
                        {"location_facility_id": "d-one"}
                    ]}]}
    ag = {"edogawa_rows": [{"original_national_csv_row": 2,
                           "original_columns_unmodified": dict(GSI)}]}
    c = {"source_sha256": {"city_saved_water_html": sha256(water).hexdigest()}}
    graw = b"example national source (the upstream C audit is mocked here only)"
    awr, agr, cr = json.dumps(aw).encode(), json.dumps(ag).encode(), json.dumps(c).encode()
    matrix = {
        "purpose": "A_THREE_SOURCE_NAME_ADDRESS_REVIEW_LEADS_NOT_VERIFIED",
        "source_sha256": {
            "municipal_water_original": sha256(water).hexdigest(),
            "a_source_pinned_water_ledger": sha256(awr).hexdigest(),
            "gsi_national_original": sha256(graw).hexdigest(),
            "a_gsi_original_extraction": sha256(agr).hexdigest(),
            "current_d_region_export": sha256(d_bytes).hexdigest(),
        },
        "human_c_site_pairs_approved": 0, "flood_classifications_added": 0,
        "water_rows_total": 1, "gsi_edogawa_rows_source": 1, "d_location_rows_source": 1,
        "number_of_gsi_leads_per_water_row": {"1": 1},
        "gsi_ids_proposed_for_multiple_water_sites": [],
        "water_rows": [{
            "water_source_record_trace": "table=1;row=2",
            "water_number_raw": "1", "water_name_raw": "新小学校",
            "water_address_raw": "平井4丁目1番23号", "water_floor_raw": "2階以上",
            "a_d_name_hint_ids": ["d-one"],
            "gsi_review_lead_count": 1,
            "gsi_review_leads": [{
                "documentary_discrepancy_flags": [],
                "distance_threshold_is_not_eligibility_or_identity_gate": True,
                "gsi_common_id_raw": "GSI-test-1",
                "gsi_national_source_line": 2,
                "gsi_name_raw": GSI["施設・場所名"], "gsi_address_raw": GSI["住所"],
                "gsi_flood_raw": "", "gsi_earthquake_raw": "1",
                "gsi_latitude_raw": "35.7", "gsi_longitude_raw": "139.8",
                "review_name_key_equal": True, "review_address_key_equal": True,
                "d_source_hint_distances": [{
                    "d_facility_id": "d-one", "d_facility_name_raw": "新小学校",
                    "distance_m_not_identity": 0.0,
                }],
                "gsi_common_id_is_not_d_id": True,
                "c_human_same_site_approved": False,
                "flood_scenario_result": "UNCHANGED_UNKNOWN",
            }],
            "cross_source_status": "UNREVIEWED", "flood_specific_eligibility": "UNKNOWN",
            "no_gsi_lead_does_not_mean_no_publication": True,
        }],
    }
    return (water, graw, awr, agr, d_bytes, cr, matrix)


class CThreeSourceTests(unittest.TestCase):
    def run_validated(self, fixture):
        w, g, aw, ag, d, c, m = fixture
        with patch("verify_edogawa_three_source_review.audit_original_gsi",
                   return_value={"edogawa_gsi_rows_independently_checked": 1}):
            return audit(w, g, aw, ag, d, c, json.dumps(m).encode())

    def test_unapproved_name_address_hint_is_not_site_or_flood_verdict(self):
        result = self.run_validated(inputs())
        self.assertEqual(result["water_rows_independently_verified"], 1)
        self.assertEqual(result["gsi_review_leads_per_water_row"], {"1": 1})
        self.assertEqual(result["independent_c_human_site_pairs_approved"], 0)
        self.assertEqual(result["d_flood_classifications_added"], 0)

    def test_cannot_propose_gsi_match_without_name_or_address(self):
        sample = list(inputs())
        matrix = copy.deepcopy(sample[-1])
        ag = json.loads(sample[3])
        ag["edogawa_rows"][0]["original_columns_unmodified"]["住所"] = "東京都江戸川区別の場所"
        ag["edogawa_rows"][0]["original_columns_unmodified"]["施設・場所名"] = "他の学校"
        sample[3] = json.dumps(ag).encode()
        matrix["source_sha256"]["a_gsi_original_extraction"] = sha256(sample[3]).hexdigest()
        sample[-1] = matrix
        with self.assertRaisesRegex(ThreeSourceAuditFailure, "omitted/added"):
            self.run_validated(sample)

    def test_wrong_coordinate_distance_rejected_even_when_same_name(self):
        sample = list(inputs())
        matrix = copy.deepcopy(sample[-1])
        matrix["water_rows"][0]["gsi_review_leads"][0]["d_source_hint_distances"][0]["distance_m_not_identity"] = 99.9
        sample[-1] = matrix
        with self.assertRaisesRegex(ThreeSourceAuditFailure, "distance altered"):
            self.run_validated(sample)

    def test_gsi_blank_flood_does_not_permit_a_flood_candidate(self):
        sample = list(inputs())
        matrix = copy.deepcopy(sample[-1])
        matrix["water_rows"][0]["flood_specific_eligibility"] = "EXCLUDED"
        sample[-1] = matrix
        with self.assertRaisesRegex(ThreeSourceAuditFailure, "prematurely"):
            self.run_validated(sample)

    def test_discrepancy_flags_cannot_be_misrepresented(self):
        sample = list(inputs())
        matrix = copy.deepcopy(sample[-1])
        matrix["water_rows"][0]["gsi_review_leads"][0]["documentary_discrepancy_flags"] = [
            "ADDRESS_NORMALIZATION_DIFFERS_REVIEW"
        ]
        sample[-1] = matrix
        with self.assertRaisesRegex(ThreeSourceAuditFailure, "Discrepancy flags"):
            self.run_validated(sample)

    def test_relabeling_source_origin_rejected(self):
        sample = list(inputs())
        matrix = copy.deepcopy(sample[-1])
        matrix["source_sha256"]["municipal_water_original"] = "0"*64
        sample[-1] = matrix
        with self.assertRaisesRegex(ThreeSourceAuditFailure, "provenance mismatch"):
            self.run_validated(sample)

    def test_original_gsi_independent_verifier_must_run(self):
        with patch("verify_edogawa_three_source_review.audit_original_gsi",
                   side_effect=ValueError("Original not verified")):
            with self.assertRaisesRegex(ValueError, "Original not verified"):
                w, g, aw, ag, d, c, m = inputs()
                audit(w, g, aw, ag, d, c, json.dumps(m).encode())


if __name__ == "__main__":
    unittest.main()
