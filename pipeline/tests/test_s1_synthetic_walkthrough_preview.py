"""Fixed fictional P4 sequence preview tests; no browser/official records."""
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest

from preview_s1_synthetic_walkthrough import main, sample_walkthrough


class S1WalkthroughPreviewTests(unittest.TestCase):
    def test_normal_flow_has_explicit_review_after_condition_change(self):
        result = sample_walkthrough()
        self.assertEqual(result["scenario"], "normal")
        self.assertEqual(len(result["events"]), 3)
        self.assertEqual(result["events"][-1]["status"], "APPLIED_SYNTHETIC_ONLY")
        self.assertEqual(result["frames"][1]["result"]["newly_matching_synthetic_ids"],
                         ["synthetic:c", "synthetic:d"])
        review = result["frames"][-1]["result"]["review"]
        self.assertEqual(review["comparison_status"], "UNKNOWN")
        self.assertEqual(review["selected_record_id"], "synthetic:e")

    def test_stale_callback_cannot_replace_newer_conditions(self):
        result = sample_walkthrough("stale")
        self.assertEqual(result["events"][2]["status"], "BLOCKED")
        self.assertEqual(result["events"][2]["reason_code"], "STALE_WALKTHROUGH_ACTION")
        self.assertEqual(result["frames"][2]["result"]["after_conditions"], ["step_free"])
        self.assertIsNone(result["frames"][2]["result"]["review"])
        self.assertEqual(result["events"][3]["status"], "APPLIED_SYNTHETIC_ONLY")

    def test_expired_scenario_has_no_cached_rows_or_review(self):
        result = sample_walkthrough("expired")
        self.assertEqual(result["frames"][-1]["status"], "BLOCKED")
        self.assertIsNone(result["frames"][-1]["result"])
        self.assertEqual(result["events"][-1]["status"], "BLOCKED")
        self.assertEqual(result["events"][-1]["reason_code"], "STALE_WALKTHROUGH_ACTION")
        self.assertEqual(result["events"][-1]["generation"], 2)

    def test_stopped_scenario_clears_all_presented_results(self):
        result = sample_walkthrough("stopped")
        self.assertEqual(result["events"][-1]["reason_code"], "SYNTHETIC_CONTEXT_CLEARED")
        self.assertEqual(result["frames"][-1]["status"], "BLOCKED")
        self.assertIsNone(result["frames"][-1]["result"])

    def test_preview_never_grants_real_world_approval(self):
        for mode in ("normal", "stale", "expired", "stopped"):
            with self.subTest(mode=mode):
                result = sample_walkthrough(mode)
                self.assertTrue(result["synthetic_only"])
                for flag in ("official_acceptance", "live_data_verified",
                             "facility_safety_verified", "route_safety_verified",
                             "release_approved"):
                    self.assertIs(result[flag], False)
                self.assertNotIn("latitude", json.dumps(result))
                self.assertNotIn("address", json.dumps(result))

    def test_deterministic_and_cli_json(self):
        self.assertEqual(sample_walkthrough(), sample_walkthrough())
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--scenario", "stale"]), 0)
        self.assertEqual(json.loads(output.getvalue())["scenario"], "stale")

    def test_unknown_scenario_rejected_and_parser_rejects_unlisted(self):
        with self.assertRaises(ValueError):
            sample_walkthrough("real")
        with redirect_stdout(StringIO()):
            with self.assertRaises(SystemExit) as ex:
                main(["--scenario", "real"])
        self.assertEqual(ex.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
