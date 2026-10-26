"""Synthetic-only tests for private Stage9 point-origin diagnostic."""
import copy
import json
import unittest
from collections import Counter

from diagnose_nagoya_stage9_duplicate_abr import analyze, REPORT_KIND
from refine_nagoya_gsi_stage7 import refine
from create_nagoya_independent_review_queue import PRIVATE_FIELDS
from test_nagoya_gsi_stage7 import historical_fixture


def sample(stage4=False):
    rows, summary = refine(*historical_fixture())
    rows = copy.deepcopy(rows)
    p1 = [row for row in rows
          if row["stage7_priority"] == "P1_DISTANCE_OR_PARCEL_REVIEW"][:2]
    assert len(p1) == 2
    a, b = p1
    b["abr_reference_latitude"] = a["abr_reference_latitude"]
    b["abr_reference_longitude"] = a["abr_reference_longitude"]
    a["gsi_reference_latitude"], a["gsi_reference_longitude"] = "35.1", "136.91"
    b["gsi_reference_latitude"], b["gsi_reference_longitude"] = "35.2", "136.92"
    queue = [{k: row.get(k, "") for k in PRIVATE_FIELDS} for row in rows]
    queue_by_id = {r["pilot_record_id"]: r for r in queue}
    queue_summary = {
        "report_kind": "NAGOYA_PRIVATE_REVIEW_QUEUE_PREPARATION_NOT_SITE_ACCEPTANCE",
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "official_facility_positions_accepted": 0,
        "all_review_status_not_reviewed": True,
        "total_review_rows": len(queue),
        "original_sample_total": 50,
        "review_queue_counts": dict(Counter(r["review_priority"] for r in queue)),
        "source_dataset_sha256": summary["source_dataset_sha256"],
        "provider_version": summary["provider_version"],
        "provider_db_version": summary["provider_db_version"],
    }
    original = []
    for row in (a, b):
        queue_by_id[row["pilot_record_id"]]["reference_origin"] = (
            "CHOME_TEXT_EQUAL_ABR_REFERENCE" if stage4
            else "ORIGINAL_UNVERIFIED_ABR_REFERENCE"
        )
        entry = {
            "record_id": row["pilot_record_id"],
            "approved_for_map": False,
            "status": "UNRESOLVED" if stage4 else "NEEDS_REVIEW",
            "reason": ("different_street_or_house_number" if stage4
                       else "shared_reference_coordinate"),
        }
        if not stage4:
            entry["derived_geometry"] = {
                "latitude": float(row["abr_reference_latitude"]),
                "longitude": float(row["abr_reference_longitude"]),
            }
        original.append(entry)
    resolution = {
        "source_dataset_sha256": summary["source_dataset_sha256"],
        "provider_version": summary["provider_version"],
        "provider_db_version": summary["provider_db_version"],
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "results": original,
    }
    return rows, summary, queue, queue_summary, resolution, [r["facility_name"] for r in (a, b)]


class Stage9DuplicateDiagnosticTests(unittest.TestCase):
    def test_original_candidates_and_safe_report(self):
        rows, summary, queue, queue_summary, resolution, names = sample()
        before = json.dumps([rows, summary, resolution], ensure_ascii=False)
        report = analyze(rows, summary, queue, queue_summary, resolution, names)
        self.assertEqual(report["report_kind"], REPORT_KIND)
        self.assertTrue(report["same_abr_reference"])
        self.assertEqual(report["gsi_reference_relation"], "DIFFERENT")
        self.assertEqual(report["earliest_recorded_origin_group"],
                         "ORIGINAL_PILOT_BOTH")
        self.assertTrue(report["facility_1"]["original_duplicate_flag"])
        self.assertTrue(report["facility_1"]["initial_reference_preserved"])
        self.assertEqual(report["root_cause"], "UNCONFIRMED")
        self.assertFalse(report["approved_for_map"])
        self.assertFalse(report["data_promotion_authorized"])
        self.assertEqual(report["official_facility_positions_accepted"], 0)
        self.assertEqual(before, json.dumps([rows, summary, resolution],
                                           ensure_ascii=False))
        rendered = json.dumps(report, ensure_ascii=False)
        for secret in (*names, "架空", "fictional-", "136.9", "35.1",
                       "official_listed_address", "pilot_record_id",
                       "source_dataset_sha256", "facility_name"):
            self.assertNotIn(secret, rendered)

    def test_stage4_candidates_are_not_mistaken_for_original(self):
        rows, summary, queue, queue_summary, resolution, names = sample(stage4=True)
        report = analyze(rows, summary, queue, queue_summary, resolution, names)
        self.assertEqual(report["earliest_recorded_origin_group"], "STAGE4_BOTH")
        self.assertIsNone(report["facility_1"]["initial_reference_preserved"])
        self.assertFalse(report["facility_2"]["original_duplicate_flag"])

    def test_aborted_for_drift_or_tampering(self):
        for key, value in (
            ("source_dataset_sha256", "wrong"),
            ("provider_version", "wrong"),
            ("provider_db_version", "wrong"),
            ("approved_for_map", True),
            ("data_promotion_authorized", True),
        ):
            rows, summary, queue, queue_summary, resolution, names = sample()
            resolution[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                analyze(rows, summary, queue, queue_summary, resolution, names)

    def test_rejects_an_approved_stage7_row_and_bad_identity(self):
        rows, summary, queue, queue_summary, resolution, names = sample()
        rows[0]["independent_site_position_approved"] = "YES"
        with self.assertRaises(ValueError):
            analyze(rows, summary, queue, queue_summary, resolution, names)
        rows, summary, queue, queue_summary, resolution, names = sample()
        with self.assertRaises(ValueError):
            analyze(rows, summary, queue, queue_summary, resolution, [names[0], names[0]])
        with self.assertRaises(ValueError):
            analyze(rows, summary, queue, queue_summary, resolution, ["no such place", names[1]])

    def test_detects_point_changes_and_missing_gsi_without_approval(self):
        rows, summary, queue, queue_summary, resolution, names = sample()
        old = resolution["results"][0]["derived_geometry"]
        old["latitude"] = 35.35
        report = analyze(rows, summary, queue, queue_summary, resolution, names)
        self.assertFalse(report["facility_1"]["initial_reference_preserved"])
        target = next(r for r in rows if r["facility_name"] == names[1])
        target["gsi_reference_longitude"] = ""
        report = analyze(rows, summary, queue, queue_summary, resolution, names)
        self.assertEqual(report["gsi_reference_relation"], "INSUFFICIENT_DATA")
        self.assertEqual(report["root_cause"], "UNCONFIRMED")


if __name__ == "__main__":
    unittest.main()
