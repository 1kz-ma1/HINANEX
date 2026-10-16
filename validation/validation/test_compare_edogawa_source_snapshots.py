"""C offline guards for independently comparing original-source snapshots.

Fixtures only; no HTTP or disaster classification is performed in CI.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from archive_edogawa_official_sources import SOURCES, capture
from compare_edogawa_source_snapshots import ComparisonFailure, compare
from test_edogawa_official_archive_content import raw_sources


def write_snapshot(folder, when, mutate=None):
    raws = raw_sources()
    if mutate is not None:
        mutate(raws)

    def fake_fetch(url):
        key = next(k for k, (_, official_url) in SOURCES.items()
                   if official_url == url)
        return raws[key], url, {
            "content_type": "text/csv" if key == "municipal_locations"
                            else "text/html; charset=utf-8",
            "etag": '"fixture-unverified"',
            "last_modified": "Mon, 12 Oct 2026 01:00:00 GMT",
        }

    capture(folder, fetch=fake_fetch, now=when)


class SnapshotDeltaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.before = Path(self.tmp.name) / "before"
        self.after = Path(self.tmp.name) / "after"
        self.earlier = datetime(2026, 10, 13, tzinfo=timezone.utc)
        self.later = datetime(2026, 10, 16, tzinfo=timezone.utc)

    def fresh_pair(self, mutate_after=None):
        write_snapshot(self.before, self.earlier)
        write_snapshot(self.after, self.later, mutate_after)

    def test_identical_bytes_are_not_approval_or_proof_of_no_revision(self):
        self.fresh_pair()
        result = compare(self.before, self.after)
        self.assertEqual(result["status"], "BYTE_IDENTICAL_SNAPSHOTS_REVIEW_PENDING")
        self.assertEqual(result["changed_source_count"], 0)
        self.assertEqual(len(result["sources"]), len(SOURCES))
        self.assertTrue(all(not item["same_physical_facility_approved"]
                            for item in result["sources"]))
        self.assertFalse(result["source_revision_human_review_completed"])
        self.assertFalse(result["live_opening_or_safety_evaluated"])
        self.assertEqual(result["approved_cross_source_pairs"], 0)
        self.assertEqual(result["flood_scenario_classifications_added"], 0)
        self.assertIsNone(result["sources"][0]["official_publication_or_effective_date"])

    def test_one_valid_new_html_version_is_reviewable_source_delta(self):
        def change(raws):
            raws["municipal_school_list"] = raws["municipal_school_list"].replace(
                b"<body>", b"<body><p>Source context revision test.</p>"
            )
        self.fresh_pair(change)
        result = compare(self.before, self.after)
        self.assertEqual(result["status"], "SOURCE_BYTES_CHANGED_REVIEW_REQUIRED")
        self.assertEqual(result["changed_source_count"], 1)
        self.assertEqual(result["changed_source_keys"], ["municipal_school_list"])
        self.assertEqual(result["content_shape_comparison"]["current_water_rows"], 4)
        self.assertEqual(result["content_shape_comparison"]["current_location_csv_rows"], 2)
        self.assertTrue(result["sources"][2]["human_source_revision_review_required"])
        self.assertFalse(result["sources"][2]["same_physical_facility_approved"])
        self.assertNotEqual(result["sources"][2]["previous_sha256"],
                            result["sources"][2]["current_sha256"])

    def test_tampered_archive_bytes_are_rejected_before_comparison(self):
        self.fresh_pair()
        f = self.after / SOURCES["municipal_locations"][0]
        f.write_bytes(f.read_bytes() + b"manipulated")
        with self.assertRaisesRegex(ComparisonFailure, "integrity/content"):
            compare(self.before, self.after)

    def test_forged_approval_and_changed_original_url_fail_closed(self):
        for field, value in (
            ("human_c_reviewer_signed_off", True),
            ("flood_scenario_classifications_added", 3),
            ("date_context_review_required", False),
        ):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    old = Path(tmp)/"older"
                    recent = Path(tmp)/"recent"
                    write_snapshot(old,self.earlier)
                    write_snapshot(recent,self.later)
                    mf=recent/"snapshot_manifest.json"
                    data=json.loads(mf.read_text(encoding="utf-8"))
                    if field=="date_context_review_required":
                        data["source_items"][0][field]=value
                    else:
                        data[field]=value
                    mf.write_text(json.dumps(data),encoding="utf-8")
                    with self.assertRaises(ComparisonFailure):
                        compare(old,recent)

    def test_wrong_content_http_200_is_rejected(self):
        self.fresh_pair(lambda raws: raws.update(
            municipal_school_list=b"<html><body>Login page</body></html>"
        ))
        with self.assertRaisesRegex(ComparisonFailure, "integrity/content"):
            compare(self.before,self.after)

    def test_same_directory_or_reversed_capture_times_rejected(self):
        self.fresh_pair()
        with self.assertRaisesRegex(ComparisonFailure, "Two independent"):
            compare(self.before,self.before)
        with self.assertRaisesRegex(ComparisonFailure, "later UTC"):
            compare(self.after,self.before)
        with self.assertRaisesRegex(ComparisonFailure, "later UTC"):
            compare(self.after,self.after.parent/"before")

    def test_not_approved_if_http_last_modified_matches(self):
        self.fresh_pair(lambda raws: raws.update(
            municipal_primary_school_list=raws["municipal_primary_school_list"] +
            b"<!-- updated but unreviewed source bytes -->"
        ))
        report=compare(self.before,self.after)
        item=next(x for x in report["sources"]
                  if x["source_key"]=="municipal_primary_school_list")
        self.assertEqual(item["previous_http_last_modified_unverified"],
                         item["current_http_last_modified_unverified"])
        self.assertTrue(item["raw_bytes_changed"])
        self.assertIsNone(item["official_publication_or_effective_date"])
        self.assertFalse(report["physical_site_identity_human_review_completed"])


if __name__=="__main__":
    unittest.main()
