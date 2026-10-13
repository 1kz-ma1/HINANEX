"""Offline provenance checks, not original website validation."""
from pathlib import Path
import json
import unittest

PATH=Path(__file__).resolve().parents[1]/"scenarios"/"2019-typhoon19-edogawa-school-diary-candidates.json"


class DiaryCandidatesTest(unittest.TestCase):
    def setUp(self):
        d=json.loads(PATH.read_text(encoding="utf-8"))
        self.d=d
        self.by_id={v["id"]:v for v in d["records"]}

    def test_all_indexed_sources_unapproved(self):
        self.assertEqual(self.d["candidate_count"],4)
        self.assertEqual(self.d["c_verified_byte_originals"],0)
        self.assertEqual(self.d["event_shelter_site_pairs_approved"],0)
        self.assertEqual(self.d["historical_asof_prediction_inputs_approved"],0)
        self.assertEqual(len(self.by_id),4)
        for record in self.d["records"]:
            self.assertTrue(record["official_url"].startswith("https://edogawa.schoolweb.ne.jp/"))
            self.assertIsNone(record["source_raw_sha256"])
            self.assertIsNone(record["first_publication_instant_jst"])
            self.assertFalse(record["source_exact_2019_revision_verified"])
            self.assertFalse(record["independent_C_original_review"])
            self.assertFalse(record["can_be_used_for_2019_10_12_09_input"])
            self.assertIsNone(record["physical_building_id_approved"])
            self.assertIsNone(record["exact_occupancy_count"])

    def test_hirai_over100_not_exact_100(self):
        h=self.by_id["hirai-higashi-20191012"]
        self.assertEqual(h["occupancy_expression"],"MORE_THAN_100")
        self.assertIn("16:00",h["observation_interval"])
        self.assertNotEqual(h["observation_precision"],"WEB_FIRST_PUBLICATION_TIME")

    def test_next_day_report_is_not_oct12_publication(self):
        p=self.by_id["minami-kasai-third-20191013"]
        self.assertEqual(p["published_day_displayed"],"2019-10-13")
        self.assertEqual(p["observation_interval"],"2019-10-12T12:15+09:00")
        self.assertIn("NEXT_DAY",p["role"])

    def test_kasai_school_combined_not_split_to_two_counts(self):
        p=self.by_id["kasai-campus-20191012"]
        self.assertEqual(p["reported_scope"],"KASAI_ELEMENTARY_AND_JUNIOR_HIGH_COMPOSITE_CAMPUS")
        self.assertEqual(p["occupancy_expression"],"APPROX_2500_COMPOSITE_CAMPUS")

    def test_classes_cancelled_is_not_shelter_closed(self):
        p=self.by_id["komatsugawa-second-20191010"]
        self.assertEqual(p["published_day_displayed"],"2019-10-10")
        self.assertEqual(p["role"],"PRE_EVENT_SCHOOL_CLASS_CANCELLATION_NOTICE_NOT_SHELTER_OPENING")
        self.assertEqual(p["occupancy_expression"],"NOT_REPORTED")


if __name__=="__main__":
    unittest.main()
