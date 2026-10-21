"""Stage-6 test data is synthetic; no real Nagoya facility positions."""
import copy
import json
import unittest

from compare_nagoya_gsi_offline import (
    PRIVATE_COMPARISON_FIELDS, compare,
)
from create_nagoya_independent_review_queue import (
    REVIEW_A_EXISTING, REVIEW_A_NEW, REVIEW_B_PARCEL, safe_csv_cell,
)
from test_nagoya_gsi_offline import PREFIX, gsi, queue_summary, record
from triage_nagoya_gsi_stage6 import FLAGS, LEVELS, triage


def fixtures():
    queue = [
        record("fictional-conflict", "架空A学校", "甲町1丁目1番1号",
               priority=REVIEW_A_NEW),
        record("fictional-name", "架空B学校", "乙町1丁目1番1号",
               priority=REVIEW_A_NEW),
        record("fictional-far", "架空C学校", "丙町1丁目1番1号",
               priority=REVIEW_A_NEW),
        record("fictional-parcel", "架空D学校", "丁町1丁目1番1号",
               priority=REVIEW_B_PARCEL),
        record("fictional-both", "架空E学校", "戊町1丁目1番1号",
               priority=REVIEW_B_PARCEL),
        record("fictional-normal", "架空F学校", "己町1丁目1番1号",
               priority=REVIEW_A_EXISTING),
    ]
    gsi_rows = [
        gsi("架空A学校", PREFIX + "甲町一丁目1番1号",
            point=(136.9, 35.1), id="fictional-g1"),
        gsi("架空A学校", PREFIX + "甲町一丁目1番1号",
            point=(136.91, 35.1), id="fictional-g2"),
        gsi("別名B学園", PREFIX + "乙町一丁目1番1号", id="fictional-g3"),
        gsi("架空C学校", PREFIX + "丙町一丁目1番1号",
            point=(136.906, 35.1), id="fictional-g4"),
        gsi("架空D学校", PREFIX + "丁町一丁目1番1号",
            point=(136.9, 35.1), id="fictional-g5"),
        gsi("架空E学校", PREFIX + "戊町一丁目1番1号",
            point=(136.906, 35.1), id="fictional-g6"),
        gsi("架空F学校", PREFIX + "己町一丁目1番1号",
            point=(136.9, 35.1), id="fictional-g7"),
    ]
    provenance = {"shelter": {"sha256": "synthetic-GSI-hash",
                             "rows_read": len(gsi_rows),
                             "nagoya_rows_in_file": len(gsi_rows)}}
    qs = queue_summary(queue)
    details, agg = compare(queue, qs, gsi_rows, provenance)
    exported_rows = [
        {key: safe_csv_cell(row.get(key)) for key in PRIVATE_COMPARISON_FIELDS}
        for row in details
    ]
    return queue, qs, exported_rows, agg, gsi_rows, provenance


class NagoyaStage6Tests(unittest.TestCase):
    def test_overlap_count_and_ranking(self):
        rows, agg = triage(*fixtures())
        self.assertEqual(agg["total_private_review_rows"], 6)
        self.assertEqual(agg["priority_counts"][LEVELS[0]], 2)
        self.assertEqual(agg["priority_counts"][LEVELS[1]], 3)
        self.assertEqual(agg["priority_counts"][LEVELS[2]], 1)
        self.assertEqual(agg["distinct_rows_flagged"], 5)
        self.assertEqual(agg["rows_with_overlapping_flags"], 1)
        self.assertEqual(agg["risk_flag_counts"][FLAGS[0]], 1)
        self.assertEqual(agg["risk_flag_counts"][FLAGS[1]], 1)
        self.assertEqual(agg["risk_flag_counts"][FLAGS[2]], 2)
        self.assertEqual(agg["risk_flag_counts"][FLAGS[3]], 2)
        self.assertEqual(agg["risk_flag_counts"][FLAGS[4]], 0)
        self.assertTrue(agg["stage5_status_counts_reproduced"])
        self.assertFalse(agg["approved_for_map"])
        self.assertFalse(agg["data_promotion_authorized"])
        self.assertFalse(agg["site_position_independently_verified"])
        self.assertEqual(agg["official_facility_positions_accepted"], 0)
        self.assertEqual({r["review_status"] for r in rows}, {"NOT_REVIEWED"})
        self.assertEqual({r["approval_gate"] for r in rows},
                         {"BLOCKED_PENDING_MANUAL_SITE_VERIFICATION"})
        rendered = json.dumps(agg, ensure_ascii=False)
        for text in ("架空", "甲町", "乙町", "fictional-", "136.9", "35.1",
                     '"pilot_record_id":', '"abr_reference_latitude":'):
            self.assertNotIn(text, rendered)

    def test_conflict_points_private_only(self):
        rows, _ = triage(*fixtures())
        conflict = next(r for r in rows
                        if r["gsi_cross_reference_status"] ==
                        "strict_name_address_conflicting_references")
        details = json.loads(conflict["gsi_conflict_points_PRIVATE"])
        self.assertEqual(len(details), 2)
        self.assertTrue(all(item["abr_distance_meters"] >= 0 for item in details))
        name = next(r for r in rows if r["gsi_cross_reference_status"] ==
                    "address_match_only_name_unconfirmed")
        self.assertIn("別名B学園", name["gsi_other_names_PRIVATE"])
        self.assertEqual(name["gsi_reference_latitude"], "")

    def test_never_auto_accept_even_same_coordinates(self):
        rows, _ = triage(*fixtures())
        same = next(r for r in rows if r["facility_name"] == "架空F学校")
        self.assertEqual(same["gsi_abr_distance_meters"], 0.0)
        self.assertEqual(same["independent_site_position_approved"], "NO")
        self.assertEqual(same["review_status"], "NOT_REVIEWED")

    def test_stage5_private_mutation_aborts(self):
        queue, qs, previous, agg, gsi_rows, provenance = fixtures()
        modified = copy.deepcopy(previous)
        modified[0]["gsi_abr_distance_meters"] = "99999"
        with self.assertRaisesRegex(ValueError, "Stage-5 private record differs"):
            triage(queue, qs, modified, agg, gsi_rows, provenance)

    def test_approval_and_summary_mutation_aborts(self):
        queue, qs, previous, agg, gsi_rows, provenance = fixtures()
        for key, value in (
            ("approved_for_map", True),
            ("official_facility_positions_accepted", 1),
            ("site_position_independently_verified", True),
            ("source_dataset_sha256", "tampered"),
        ):
            with self.subTest(key=key):
                changed = {**agg, key: value}
                with self.assertRaises(ValueError):
                    triage(queue, qs, previous, changed, gsi_rows, provenance)

    def test_changed_official_input_aborts(self):
        queue, qs, previous, agg, gsi_rows, provenance = fixtures()
        bad_provenance = copy.deepcopy(provenance)
        bad_provenance["shelter"]["sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "Stage-5 provenance changed"):
            triage(queue, qs, previous, agg, gsi_rows, bad_provenance)
        bad_records = copy.deepcopy(gsi_rows)
        bad_records[0]["point"] = (136.93, 35.1)
        with self.assertRaises(ValueError):
            triage(queue, qs, previous, agg, bad_records, provenance)

    def test_no_gsi_coverage_means_incomplete_not_rejected_facility(self):
        queue, qs, previous, agg, gsi_rows, provenance = fixtures()
        # GSI coverage drift must not be interpreted as absence of shelter.
        gsi_rows = [r for r in gsi_rows if r["name"] != "架空F学校"]
        with self.assertRaises(ValueError):
            triage(queue, qs, previous, agg, gsi_rows, provenance)


if __name__ == "__main__":
    unittest.main()
