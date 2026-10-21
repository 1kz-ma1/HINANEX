"""Synthetic facility data only; PRIVATE offline review page does not approve sites."""
import copy
import json
import unittest

from refine_nagoya_gsi_stage7 import refine
from test_nagoya_gsi_stage7 import historical_fixture
from view_nagoya_stage7_private import OFFICIAL_PORTAL, RANKS, render, validate


def dummy():
    rows, summary = refine(*historical_fixture())
    return rows, summary


class NagoyaReviewViewerTests(unittest.TestCase):
    def test_renders_all_levels_without_approving_any_site(self):
        rows, summary = dummy()
        page = render(rows, summary)
        self.assertIn("<!doctype html>", page)
        self.assertIn("Content-Security-Policy", page)
        self.assertIn(OFFICIAL_PORTAL, page)
        self.assertIn("P0_IDENTITY_OR_OPERATIONAL_RESTRICTION", page)
        self.assertIn("P1_DISTANCE_OR_PARCEL_REVIEW", page)
        self.assertIn("P2_INDEPENDENT_SITE_REVIEW_REQUIRED", page)
        self.assertIn("工事による使用不可", page)
        self.assertIn("2027-03-31", page)
        self.assertIn("未承認", page)
        self.assertNotIn("google.com", page)
        self.assertNotIn("onload=", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("<script", page)
        self.assertEqual(len(rows), 6)

    def test_injected_facility_metadata_escaped_and_never_in_url(self):
        rows, summary = dummy()
        altered = copy.deepcopy(rows)
        altered[0]["facility_name"] = "<img src=x onerror=alert(1)> & name"
        altered[0]["official_listed_address"] = "<script>alert(1)</script>"
        page = render(altered, summary)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<img src=x", page)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("href='https://www.city.nagoya.jp/search?", page)

    def test_reject_approved_and_mismatched_summaries(self):
        rows, summary = dummy()
        for name, value in (
            ("approved_for_map", True),
            ("official_facility_positions_accepted", 1),
            ("data_promotion_authorized", True),
            ("source_end_date_does_not_auto_reopen", False),
            ("refined_priority_counts", {r: 0 for r in RANKS}),
            ("review_rows_total", 999),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate(rows, dict(summary, **{name: value}))
        tampered = copy.deepcopy(rows)
        tampered[0]["stage7_review_status"] = "APPROVED"
        with self.assertRaises(ValueError):
            render(tampered, summary)
        tampered = copy.deepcopy(rows)
        tampered[0]["facility_reopening_verified"] = "YES"
        with self.assertRaises(ValueError):
            render(tampered, summary)

    def test_reject_unknown_priorities_and_missing_columns(self):
        rows, summary = dummy()
        altered = copy.deepcopy(rows)
        altered[0]["stage7_priority"] = "APPROVED"
        with self.assertRaises(ValueError):
            render(altered, summary)
        altered = copy.deepcopy(rows)
        del altered[0]["manual_review_required"]
        with self.assertRaises(ValueError):
            render(altered, summary)


if __name__ == "__main__":
    unittest.main()
