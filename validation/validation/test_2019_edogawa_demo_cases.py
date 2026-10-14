"""Read-only midterm deck: never turn T0 or synthetic failures into prediction results."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation" / "demo" / "2019_edogawa_evidence_cases.json"

class EducationalCasesTests(unittest.TestCase):
    def setUp(self):
        self.deck = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_the_three_cases_have_distinct_truth_statuses(self):
        d = self.deck
        self.assertEqual(d["schema_id"], "hinanex.c.midterm_explanation_cases.v0.1")
        self.assertEqual([x["id"] for x in d["cases"]], ["trace", "abstain", "negative"])
        self.assertEqual([x["track"] for x in d["cases"]], ["T0", "T1", "T0_TEST"])
        self.assertEqual([x["result"] for x in d["cases"]],
            ["C_MACHINE_TRACE_PASSED_HUMAN_PENDING","NOT_EVALUABLE","SYNTHETIC_INVALID_INPUT_REJECTED"])
        self.assertTrue(all(x["real_prediction_finding"] is None for x in d["cases"]))
        self.assertFalse(d["historical_replay_executed"])
        self.assertFalse(d["historical_prediction_approved"])
        self.assertFalse(d["human_c_approved"])
        self.assertIsNone(d["prediction_denominator"])
        self.assertIsNone(d["prediction_numerator"])
        self.assertEqual(d["approved_actual_building_pairs"],0)
        self.assertEqual(d["approved_historical_prediction_inputs"],0)
        self.assertEqual(d["t1_opening_prediction_accuracy"],"NOT_EVALUABLE")
        self.assertEqual(d["t2_hazard_prediction_accuracy"],"NOT_RUN")

    def test_pinned_original_source_audits(self):
        from generate_20261022_t0_evidence_brief import ARTIFACTS, RUNS, OFFICIAL
        d = self.deck
        sources = {s["id"]:s for s in d["sources"]}
        self.assertEqual(set(sources), {"school","campus","newsletter","cross"})
        for key in ("school","campus","newsletter"):
            self.assertEqual(sources[key]["raw_sha256"], ARTIFACTS[key][2])
            self.assertEqual(sources[key]["official_url"], OFFICIAL[key])
            self.assertEqual(sources[key]["machine_audit_url"],RUNS[key])
        self.assertEqual(sources["cross"]["machine_audit_url"], RUNS["cross"])
        self.assertIsNone(sources["cross"]["official_url"])
        self.assertIsNone(sources["cross"]["raw_sha256"])
        for s in d["sources"]:
            self.assertRegex(s["machine_audit_url"],r"^https://github\.com/1kz-ma1/HINANEX/actions/runs/\d+$")

    def test_fail_closed_explanations_and_case_references(self):
        d = self.deck
        source_ids = {s["id"] for s in d["sources"]}
        for item in d["cases"]:
            self.assertGreaterEqual(item["seconds"], 10)
            self.assertTrue({"input_title","input_text","output_title","output_text",
                             "audit_title","audit_text","takeaway","question","review_label"}
                            <= set(item))
            self.assertTrue(set(item["source_ids"]) <= source_ids)
        self.assertIn("65",d["cases"][0]["input_text"])
        self.assertIn("66",d["cases"][0]["input_text"])
        self.assertIn("26,761",d["cases"][0]["input_text"])
        self.assertIn("205",d["cases"][1]["input_text"])
        self.assertIn("11",d["cases"][1]["input_text"])
        self.assertIn("null",d["cases"][1]["output_text"])
        self.assertIn("合成",d["cases"][2]["audit_text"])
        self.assertNotIn("予測成功",d["cases"][0]["review_label"])
        self.assertIn("未検証",d["cases"][2]["review_label"])

if __name__ == "__main__":
    unittest.main()
