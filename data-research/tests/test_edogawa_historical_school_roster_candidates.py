"""Validate official-school-history candidate research metadata without fabricating approval."""
import json
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "scenarios" / "2019-typhoon19-edogawa-school-roster-candidate-ledger.json"


class CandidateLedgerTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FILE.read_text(encoding="utf-8"))
        self.by_id = {s["source_id"]: s for s in self.data["candidates"]}

    def test_case_and_all_unapproved(self):
        self.assertEqual(self.data["case_id"], "2019-typhoon19-edogawa")
        self.assertEqual(self.data["input_asof_approved_count"], 0)
        self.assertEqual(self.data["approved_physical_site_pairs"], 0)
        self.assertEqual(len(self.by_id), len(self.data["candidates"]))
        self.assertTrue(all(s["raw_sha256"] is None and s["historical_asof_approved"] is False
                            and s["physical_site_ids_approved"] == 0
                            and s["source_contents_snapshot_verified"] is False
                            and s["source_2019_temporal_continuity_verified"] is False
                            for s in self.data["candidates"]))

    def test_same_month_publication_does_not_imply_pre_typhoon(self):
        row = self.by_id["tokyo-2019-school-directory-print"]
        self.assertEqual(row["publication_interval_jst"]["not_before"], "2019-10-01")
        self.assertEqual(row["publication_interval_jst"]["not_after"], "2019-10-31")
        self.assertTrue(row["publication_interval_jst"]["not_before"] <= "2019-10-12")
        self.assertTrue(row["publication_interval_jst"]["not_after"] >= "2019-10-12")
        self.assertIsNone(row["raw_sha256"])
        self.assertFalse(row["historical_asof_approved"])

    def test_later_november_school_plan_cannot_be_predisaster_input(self):
        self.assertGreater(self.by_id["edogawa-2019-nov-school-placement"]
                           ["publication_interval_jst"]["not_before"], "2019-10-12")

    def test_older_catalog_date_and_staleness_flag_are_both_preserved(self):
        old = self.by_id["tokyo-2017-junior-high-open-data"]
        self.assertEqual(old["catalogue_created_date"], "2018-03-30")
        self.assertEqual(old["catalogue_updated_date"], "2018-03-30")
        self.assertFalse(old["source_2019_temporal_continuity_verified"])
        self.assertIn("http://", old["raw_url_catalogued"])
        self.assertIn("spec.api.metro.tokyo.lg.jp", old["catalogue_url"])


if __name__ == "__main__":
    unittest.main()
