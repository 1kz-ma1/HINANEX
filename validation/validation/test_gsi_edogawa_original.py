"""Offline C negative controls for GSI-to-actual D *review leads*, never joins."""
import csv
from hashlib import sha256
import io
import json
import unittest

from audit_gsi_edogawa_original import (
    GSI_ORIGIN, PRIORITY, GsiIndependentAuditFailure, audit,
)

COLUMNS = [
    "NO", "共通ID", "都道府県名及び市町村名", "施設・場所名", "住所",
    "洪水", "崖崩れ、土石流及び地滑り", "高潮", "地震", "津波",
    "大規模な火事", "内水氾濫", "火山現象",
    "指定避難所との住所同一", "緯度", "経度", "備考",
]
SOURCE_ROWS = (
    ("都立葛西工科高校", 35.683604, 139.878877),
    ("私立関東第一高校", 35.707960, 139.860354),
    ("下小岩小", 35.725785, 139.878612),
    ("旧下小岩小", 35.727959723381, 139.88269733303),
)


def fixture():
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    csv_records = []
    for i, (name, lat, lon) in enumerate(SOURCE_ROWS, 1):
        vals = [
            str(i), "GSI-test-" + str(i), "東京都江戸川区", name,
            "東京都江戸川区テスト所在地" + str(i), "", "", "", "1",
            "", "", "", "", "", str(lat), str(lon), "",
        ]
        writer.writerow(vals)
        csv_records.append(dict(zip(COLUMNS, vals)))
    raw = b"\xef\xbb\xbf" + out.getvalue().encode("utf-8")
    rows = [{
        "original_national_csv_row": i + 2,
        "original_columns_unmodified": row,
        "gsi_flood_marker_raw": row["洪水"],
        "common_gsi_id_is_not_d_facility_id": True,
        "physical_site_link_c_approved": False,
        "current_d_flood_scenario_change": None,
    } for i, row in enumerate(csv_records)]
    a = {
        "status": "GSI_EDOGAWA_ROWS_FOUND_UNREVIEWED",
        "source_manifest": {
            "purpose": "A_GSI_EDOGAWA_EVIDENCE_ONLY_NEVER_APPROVED",
            "requested_url": GSI_ORIGIN,
            "final_url": GSI_ORIGIN,
            "national_source_sha256": sha256(raw).hexdigest(),
            "national_source_bytes": len(raw),
            "original_csv_header": COLUMNS,
            "national_record_count_observed": 4,
            "edogawa_record_count_observed": 4,
            "human_c_physical_pairs_approved": 0,
            "new_flood_candidates_or_exclusions": 0,
        },
        "edogawa_rows": rows,
        "independent_c_site_approvals": 0,
        "new_flood_classifications": 0,
        "none_of_this_data_was_joined_to_current_d": True,
    }
    d_records = [{
        "id": d_id,
        "name": name + " from municipality",
        "latitude": lat + .0001,
        "longitude": lon,
    } for ((name, lat, lon), (_, d_id)) in zip(SOURCE_ROWS, PRIORITY)]
    d = {
        "region": {"code": "13123"},
        "datasets": [{"requirement_code": "shelter_location", "records": d_records}],
        "scenarios": [{
            "scenario_id": "flood_shelter_selection",
            "facility_results": [{
                "facility_id": record["id"], "status": "UNKNOWN",
                "fact": {"join_status": "UNVERIFIED", "official_status_raw": None}
            } for record in d_records],
        }],
    }
    d_raw = json.dumps(d).encode("utf-8")
    c = {
        "audit_status": "SOURCE_SNAPSHOT_CONSISTENCY_CHECKED_NOT_FACILITY_IDENTITY_ACCEPTED",
        "c_approved_pairs": 0,
        "flood_candidates_or_exclusions_added": 0,
        "source_sha256": {"old_d_region_export": sha256(d_raw).hexdigest()},
    }
    return raw, a, d, c


def run(parts):
    original, a, d, c = parts
    return audit(original, json.dumps(a).encode(), json.dumps(d).encode(),
                 json.dumps(c).encode())


class GsiCIndependentTests(unittest.TestCase):
    def test_four_priority_sites_are_documentary_leads_only(self):
        result = run(fixture())
        self.assertEqual(result["edogawa_gsi_rows_independently_checked"], 4)
        self.assertEqual(result["observed_gsi_hazard_markers_raw_counts"]["洪水"], {"": 4})
        self.assertEqual(result["observed_gsi_hazard_markers_raw_counts"]["地震"], {"1": 4})
        cases = result["priority_gsi_to_d_coordinate_leads_ONLY"]
        self.assertEqual(len(cases), 4)
        self.assertTrue(all(x["coordinate_distance_m_review_only"] > 0 for x in cases))
        self.assertTrue(all(not x["c_human_physical_site_pair_approved"] for x in cases))
        self.assertEqual(len({x["gsi_common_id_raw"] for x in cases}), 4)
        self.assertEqual(len({x["d_facility_id_for_independent_review_only"] for x in cases}), 4)
        self.assertEqual(result["new_d_scenario_candidates_or_exclusions"], 0)
        self.assertTrue(result["current_d_scenario_all_unknown"])

    def test_raw_changed_after_a_generation_rejected(self):
        parts = list(fixture())
        parts[0] += b"bad bytes"
        with self.assertRaisesRegex(GsiIndependentAuditFailure, "SHA256"):
            run(parts)

    def test_a_report_claimed_approval_rejected(self):
        parts = list(fixture())
        parts[1]["independent_c_site_approvals"] = 1
        with self.assertRaisesRegex(GsiIndependentAuditFailure, "approval"):
            run(parts)

    def test_a_row_mutated_even_with_original_sha_refused(self):
        parts = list(fixture())
        parts[1]["edogawa_rows"][0]["original_columns_unmodified"]["住所"] = "false"
        with self.assertRaisesRegex(GsiIndependentAuditFailure, "changed official"):
            run(parts)

    def test_stale_d_snapshot_rejected(self):
        parts = list(fixture())
        parts[2]["datasets"][0]["records"][0]["latitude"] = 0
        with self.assertRaisesRegex(GsiIndependentAuditFailure, "exact input revision"):
            run(parts)

    def test_premature_flood_candidate_is_rejected(self):
        parts = list(fixture())
        parts[2]["scenarios"][0]["facility_results"][0]["status"] = "CANDIDATE"
        parts[3]["source_sha256"]["old_d_region_export"] = sha256(
            json.dumps(parts[2]).encode()).hexdigest()
        with self.assertRaisesRegex(GsiIndependentAuditFailure, "classified"):
            run(parts)

    def test_no_gsi_priority_school_means_review_not_auto_match(self):
        parts = list(fixture())
        parts[1]["edogawa_rows"][0]["original_columns_unmodified"]["施設・場所名"] = "other"
        with self.assertRaises(GsiIndependentAuditFailure):
            run(parts)


if __name__ == "__main__":
    unittest.main()
