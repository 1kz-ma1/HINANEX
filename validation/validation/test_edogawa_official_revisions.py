"""Offline synthetic C drift tests: zero implicit facility/flood approval."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from archive_edogawa_official_sources import SOURCES, capture
from compare_edogawa_official_revisions import (
    RevisionFailure, compare, location_rows,
)
from verify_edogawa_water_join import WATER_URL


def html(name="都立 葛西工高等学校", address="一之江7丁目68番1号",
         floor="2階以上", spacer=""):
    return (
        "<html><body>" + WATER_URL +
        "<table><tr><th>番号</th><th>名称</th><th>住所</th>"
        "<th>電話番号</th><th>使用可能階数</th></tr><tr>"
        "<td>108</td><td>" + name + "</td><td>" + address +
        "</td><td>03-3653-4111</td><td>" + floor +
        "</td></tr></table>" + spacer + "</body></html>"
    ).encode("utf-8")


def csv_bytes(name="都立葛西工科高校"):
    return (
        "名称,URL,災害種別記号,コメント,緯度,経度\r\n" +
        name + ",https://www.metro.ed.jp/kasaikoka-h/,icon,コメント,35.7,139.8\r\n"
    ).encode("cp932")


def fixture(root, water=None, locations=None):
    original_water = html()
    original_csv = csv_bytes()
    raw_water = water if water is not None else original_water
    raw_csv = locations if locations is not None else original_csv

    def fetch(url):
        if url == SOURCES["water_facilities"][1]:
            raw = raw_water
        elif url == SOURCES["municipal_locations"][1]:
            raw = raw_csv
        else:
            raw = b"<html><body>synthetic official source</body></html>"
        return raw, url, {"content_type": "text/html"}

    target = Path(root) / "current-archive"
    capture(target, fetch=fetch, now=datetime(2026, 10, 13, tzinfo=timezone.utc))
    return original_water, original_csv, target


class EdogawaRevisionDiffTests(unittest.TestCase):
    def test_exact_same_baseline_still_requires_human_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            water, locations, archive = fixture(tmp)
            report = compare(water, locations, archive)
            self.assertEqual(report["status"],
                             "BASELINE_AND_CURRENT_BYTES_EQUAL_STILL_REVIEW_REQUIRED")
            self.assertFalse(report["water_bytes_changed"])
            self.assertEqual(report["water_rows"]["baseline_row_count"], 1)
            self.assertEqual(report["location_rows"]["current_row_count"], 1)
            self.assertFalse(report["c_human_reviewer_signed_off"])
            self.assertEqual(report["approved_cross_source_pairs"], 0)
            self.assertEqual(report["new_flood_candidates_or_exclusions"], 0)

    def test_html_reformat_does_not_become_material_facility_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(
                tmp, water=html(spacer="<div>cosmetic formatting</div>"))
            result = compare(old_water, old_csv, archive)
            self.assertEqual(result["status"],
                             "SOURCE_BYTES_DIFFER_STRUCTURE_SAME_REVIEW_REQUIRED")
            self.assertTrue(result["water_bytes_changed"])
            self.assertTrue(result["water_rows"]["whitespace_normalized_rows_equal"])
            self.assertEqual(result["water_rows"]["added_rows"], [])

    def test_changed_usable_floor_is_explicit_material_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(
                tmp, water=html(floor="3階以上"))
            result = compare(old_water, old_csv, archive)
            self.assertEqual(result["status"],
                             "STRUCTURED_SOURCE_DRIFT_REVIEW_REQUIRED")
            self.assertFalse(result["priority_school_rows"]["whitespace_normalized_rows_equal"])
            self.assertEqual(
                result["priority_school_rows"]["added_rows"][0]["record"]["official_usable_floor_raw"],
                "3階以上")
            self.assertEqual(result["new_flood_candidates_or_exclusions"], 0)

    def test_renamed_institution_and_address_change_are_not_auto_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(
                tmp, water=html(name="別の学校", address="別の住所"))
            result = compare(old_water, old_csv, archive)
            self.assertFalse(result["water_rows"]["whitespace_normalized_rows_equal"])
            self.assertTrue(result["priority_school_rows"]["removed_rows"])
            self.assertFalse(result["c_human_reviewer_signed_off"])

    def test_changed_d_source_csv_name_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(
                tmp, locations=csv_bytes(name="都立葛西工高校"))
            report = compare(old_water, old_csv, archive)
            self.assertTrue(report["location_bytes_changed"])
            self.assertFalse(report["location_rows"]["whitespace_normalized_rows_equal"])

    def test_unsupported_location_schema_requires_review(self):
        with self.assertRaisesRegex(RevisionFailure, "header changed"):
            location_rows("名称,住所\n学校,所在地".encode("cp932"))

    def test_byte_archive_tampering_prevents_diff_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(tmp)
            official = archive / SOURCES["water_facilities"][0]
            official.write_bytes(official.read_bytes() + b"changed")
            with self.assertRaisesRegex(RevisionFailure, "integrity check"):
                compare(old_water, old_csv, archive)

    def test_not_a_water_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_water, old_csv, archive = fixture(tmp)
            with self.assertRaisesRegex(RevisionFailure, "malformed"):
                compare(b"<html>No municipal table</html>", old_csv, archive)


if __name__ == "__main__":
    unittest.main()
