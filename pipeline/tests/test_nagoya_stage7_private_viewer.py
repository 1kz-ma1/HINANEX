"""Synthetic facility data only; PRIVATE offline review page does not approve sites."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from refine_nagoya_gsi_stage7 import refine
from test_nagoya_gsi_stage7 import historical_fixture
from view_nagoya_stage7_private import (
    COLUMNS, LEGACY_COLUMNS, OFFICIAL_PORTAL, RANKS,
    read_stage7_private, render, validate,
)


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

    def test_stage7_schema_has_unique_future_headers(self):
        self.assertEqual(len(COLUMNS), len(set(COLUMNS)))
        self.assertEqual(
            LEGACY_COLUMNS.count("independent_site_position_approved"), 2)
        self.assertEqual(COLUMNS.count("independent_site_position_approved"), 1)

    def test_read_realistic_legacy_duplicate_header_without_rewriting(self):
        rows, summary = dummy()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gsi_stage7_refined_PRIVATE.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=LEGACY_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            original = path.read_bytes()
            decoded = read_stage7_private(path)
            self.assertEqual(len(decoded), len(rows))
            self.assertTrue(all(r["independent_site_position_approved"] == "NO"
                                for r in decoded))
            page = render(decoded, summary)
            self.assertIn("P0_IDENTITY_OR_OPERATIONAL_RESTRICTION", page)
            self.assertIn("2027-03-31", page)
            self.assertEqual(path.read_bytes(), original)

    def test_read_canonical_unique_header(self):
        rows, summary = dummy()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "canonical.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            decoded = read_stage7_private(path)
            self.assertEqual(len(decoded), len(rows))
            self.assertIn("未承認", render(decoded, summary))

    def test_fail_closed_on_conflicting_legacy_approval_columns(self):
        rows, _ = dummy()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy-bad.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=LEGACY_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            with path.open("r", encoding="utf-8", newline="") as handle:
                raw = list(csv.reader(handle))
            # Modify only the second instance of the duplicated approval
            # field: accepting this would conceal a security-state conflict.
            second_idx = len(LEGACY_COLUMNS) - 3
            self.assertEqual(LEGACY_COLUMNS[second_idx],
                             "independent_site_position_approved")
            raw[1][second_idx] = "YES"
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows(raw)
            with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
                read_stage7_private(path)

    def test_unrecognized_duplicate_or_truncated_legacy_fails(self):
        rows, _ = dummy()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy-bad.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows(
                    [list(LEGACY_COLUMNS) + ["stage7_review_status"],
                     [rows[0].get(k, "") for k in LEGACY_COLUMNS] + ["NOT_REVIEWED"]])
            with self.assertRaisesRegex(ValueError, "Unexpected Stage-7"):
                read_stage7_private(path)
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows(
                    [list(LEGACY_COLUMNS),
                     [rows[0].get(k, "") for k in LEGACY_COLUMNS][:-1]])
            with self.assertRaisesRegex(ValueError, "Malformed Stage-7"):
                read_stage7_private(path)

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
