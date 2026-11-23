"""Synthetic-only tests for private Nagoya facility independent review queue."""
import copy
import csv
import io
import json
import unittest
from unittest.mock import patch

from create_nagoya_independent_review_queue import (
    REVIEW_A_EXISTING, REVIEW_A_NEW, REVIEW_B_PARCEL,
    PRIVATE_FIELDS, build_review_queue, safe_csv_cell, verify_stage4,
)
from diagnose_nagoya_chome_stage4_reference_screen import diagnose_stage4
from test_nagoya_chome_stage4_reference_screen import fixtures as stage4_fixtures
from test_nagoya_address_mismatch_diagnostic import response_stream


def fixtures(*, match_level="rsdtdsp_rsdt", point=(136.95, 35.18)):
    inputs = stage4_fixtures(match_level=match_level, point=point)
    data, sha, manifest, resolution, summary, stage1, stage2, stage3, payloads = inputs
    with patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json",
               side_effect=response_stream(payloads)):
        stage4 = diagnose_stage4(manifest, resolution, summary, stage1, stage2,
                                 stage3, data, sha, "http://127.0.0.1:3000")
    return data, sha, manifest, resolution, summary, stage1, stage2, stage3, stage4, payloads


def run_queue(inputs):
    data, sha, manifest, resolution, summary, s1, s2, s3, s4, payloads = inputs
    with patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json",
               side_effect=response_stream(payloads)):
        with patch("create_nagoya_independent_review_queue.fetch_json",
                   side_effect=response_stream(payloads)) as mocked:
            return (*build_review_queue(
                manifest, resolution, summary, s1, s2, s3, s4,
                data, sha, "http://127.0.0.1:3000",
            ), mocked.call_count)


class PrivateReviewQueueTests(unittest.TestCase):
    def test_synthetic_address_reference_and_original_candidate_are_private(self):
        rows, agg, calls = run_queue(fixtures())
        self.assertEqual(calls, 6)
        self.assertEqual(agg["total_review_rows"], 2)
        self.assertEqual(agg["review_queue_counts"][REVIEW_A_NEW], 1)
        self.assertEqual(agg["review_queue_counts"][REVIEW_A_EXISTING], 1)
        self.assertFalse(agg["approved_for_map"])
        self.assertFalse(agg["data_promotion_authorized"])
        self.assertEqual(agg["official_facility_positions_accepted"], 0)
        self.assertTrue(agg["all_review_status_not_reviewed"])
        self.assertEqual({row["review_status"] for row in rows}, {"NOT_REVIEWED"})
        self.assertEqual({row["review_priority"] for row in rows},
                         {REVIEW_A_NEW, REVIEW_A_EXISTING})
        self.assertTrue(all(row["site_position_checked"] == "" for row in rows))
        self.assertTrue(all(row["official_evidence_url"] == "" for row in rows))
        self.assertEqual(len({row["pilot_record_id"] for row in rows}), 2)
        self.assertIn("試験町", json.dumps(rows, ensure_ascii=False))
        output = json.dumps(agg, ensure_ascii=False)
        for forbidden in (
            "試験町", "架空施設", "136.95", "35.18", "synthetic-a",
            '"pilot_record_id":', '"facility_name":',
            '"official_listed_address":', '"abr_reference_longitude":',
        ):
            self.assertNotIn(forbidden, output)

    def test_parcel_reference_retained_in_separate_special_review(self):
        rows, agg, _ = run_queue(fixtures(match_level="parcel"))
        self.assertEqual(agg["review_queue_counts"][REVIEW_B_PARCEL], 1)
        self.assertEqual(agg["review_queue_counts"][REVIEW_A_EXISTING], 1)
        self.assertEqual(len(rows), 2)

    def test_duplicate_stage4_not_promoted(self):
        data = fixtures(point=(136.93, 35.16))
        rows, agg, _ = run_queue(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(agg["review_queue_counts"][REVIEW_A_EXISTING], 1)
        self.assertNotIn(REVIEW_A_NEW, agg["review_queue_counts"])

    def test_csv_formulas_escaped_and_fieldnames_protected(self):
        for text in ("=HYPERLINK(1)", "@cmd", "+1+1", "-1", "  =SUM(A:A)"):
            self.assertTrue(safe_csv_cell(text).startswith("'"))
        self.assertEqual(safe_csv_cell("普通の住所"), "普通の住所")
        self.assertEqual(safe_csv_cell(None), "")
        self.assertIn("review_status", PRIVATE_FIELDS)
        self.assertIn("official_facility_type", PRIVATE_FIELDS)
        sio = io.StringIO(newline="")
        writer = csv.DictWriter(sio, fieldnames=PRIVATE_FIELDS)
        writer.writeheader()
        row = {k: "" for k in PRIVATE_FIELDS}
        row["facility_name"] = "=EVIL()"
        writer.writerow({k: safe_csv_cell(v) for k, v in row.items()})
        self.assertIn("'=EVIL()", sio.getvalue())

    @patch("create_nagoya_independent_review_queue.fetch_json")
    @patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json")
    def test_tampered_stage4_rejected_before_any_http(self, stage4_fetch, queue_fetch):
        data, sha, manifest, resolution, summary, s1, s2, s3, s4, _ = fixtures()
        for key, value in (
            ("approved_for_map", True),
            ("source_dataset_sha256", "tampered"),
            ("screen_categories", {"high_resolution_reference_for_independent_review": 99}),
            ("original_pilot_unchanged", False),
        ):
            with self.subTest(key=key):
                modified = {**s4, key: value}
                with self.assertRaises(ValueError):
                    build_review_queue(manifest, resolution, summary, s1, s2, s3,
                                       modified, data, sha, "http://127.0.0.1:3000")
        stage4_fetch.assert_not_called()
        queue_fetch.assert_not_called()

    @patch("create_nagoya_independent_review_queue.fetch_json")
    @patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json")
    def test_external_host_rejected_before_http(self, stage4_fetch, queue_fetch):
        data, sha, manifest, resolution, summary, s1, s2, s3, s4, _ = fixtures()
        with self.assertRaises(ValueError):
            build_review_queue(manifest, resolution, summary, s1, s2, s3,
                               s4, data, sha, "https://outside.example")
        stage4_fetch.assert_not_called()
        queue_fetch.assert_not_called()

    def test_stage4_counts_rechecked_before_private_queue(self):
        data, sha, manifest, resolution, summary, s1, s2, s3, s4, _ = fixtures()
        verify_stage4(s4, s3, s1, summary, resolution, sha)
        bad = copy.deepcopy(s4)
        bad["screen_categories"]["parcel_reference_requires_review"] = 3
        with self.assertRaises(ValueError):
            verify_stage4(bad, s3, s1, summary, resolution, sha)


if __name__ == "__main__":
    unittest.main()
