"""Independent C contract regression for real S0 -> S1-P0/P1/P2 outputs.

The fixture contains expected outcomes, not snapshots copied from the D code.
"""
from __future__ import annotations

import copy
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import verify_s1_full_chain_replay as c


class S1FullChainCReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(c.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def replay(self):
        return c.replay(self.manifest)

    def test_complete_21_step_replay_matches_independent_expectations(self):
        result = self.replay()
        self.assertEqual((result["status"], result["code"]),
                         ("PASS", "REAL_CHAIN_REPLAY_MATCHED"))
        self.assertEqual(len(result["trace"]), 21)
        self.assertEqual(sum(s["kind"] == "EVENT" for s in result["trace"]), 9)
        self.assertEqual(sum(s["kind"] == "CHECK" for s in result["trace"]), 12)

    def test_initial_drill_and_all_three_s1_layers_are_real(self):
        result = self.replay()
        event = result["trace"][0]["actual"]
        self.assertEqual((event["transition"], event["mode"], event["generation"]),
                         ("APPLIED", "DRILL", 1))
        check = result["trace"][1]["actual"]
        self.assertEqual(check["matched_ids"], ["synthetic:chain-a"])
        self.assertEqual(check["row_statuses"], [
            "MATCHED_SYNTHETIC", "NOT_MATCHED_SYNTHETIC",
            "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN",
        ])
        self.assertEqual(check["totals"],
                         {"matched_synthetic": 1, "not_matched_synthetic": 1, "unknown": 4})
        self.assertEqual(check["narrow_status"], "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(check["comparison_status"], "EVALUATED_SYNTHETIC_ONLY")

    def test_unknown_choice_remains_unknown_after_real_full_chain(self):
        chosen = self.replay()["trace"][1]["actual"]
        self.assertEqual(chosen["choice_status"], "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(chosen["chosen_id"], "synthetic:chain-c")
        self.assertEqual(chosen["choice_classification"], "UNKNOWN")
        self.assertEqual(chosen["choice_missing"], ["pet_support"])
        self.assertEqual(chosen["choice_failed"], [])
        self.assertEqual(chosen["choice_checks"], [
            {"condition": "pet_support", "assessment": "UNVERIFIED"},
            {"condition": "step_free", "assessment": "EXPLICIT_SYNTHETIC_TRUE"},
        ])

    def test_nonmatched_choice_is_review_only_not_shelter_approval(self):
        chosen = self.replay()["trace"][3]["actual"]
        self.assertEqual(chosen["choice_classification"], "NOT_MATCHED_SYNTHETIC")
        self.assertEqual(chosen["chosen_id"], "synthetic:chain-b")
        self.assertEqual(chosen["choice_failed"], ["pet_support"])
        self.assertEqual(chosen["choice_missing"], [])

    def test_absent_explicit_user_action_does_not_choose(self):
        actual = self.replay()["trace"][2]["actual"]
        self.assertEqual(actual["choice_status"], "BLOCKED")
        self.assertEqual(actual["choice_reason"], "EXPLICIT_USER_SELECTION_REQUIRED")
        self.assertIsNone(actual["chosen_id"])
        self.assertEqual(actual["narrow_status"], "EVALUATED_SYNTHETIC_ONLY")

    def test_stop_clears_extraction_comparison_and_selection(self):
        trace = self.replay()["trace"]
        self.assertEqual(trace[4]["actual"]["mode"], "NORMAL")
        check = trace[5]["actual"]
        self.assertEqual(check["matched_ids"], [])
        self.assertEqual(check["row_statuses"], [])
        self.assertEqual(check["choice_status"], "BLOCKED")
        self.assertIsNone(check["chosen_id"])
        self.assertEqual(check["totals"], {
            "matched_synthetic": 0, "not_matched_synthetic": 0, "unknown": 0,
        })

    def test_new_generation_rejects_old_delayed_choice(self):
        actual = self.replay()["trace"][7]["actual"]
        self.assertEqual(actual["generation"], 3)
        self.assertEqual(actual["narrow_status"], "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(actual["choice_status"], "BLOCKED")
        self.assertEqual(actual["choice_reason"], "STALE_REVIEW_CHOICE")
        self.assertIsNone(actual["chosen_id"])
        self.assertEqual(self.replay()["trace"][8]["actual"]["chosen_id"], "synthetic:chain-a")

    def test_region_change_blocks_old_comparisons_and_choices(self):
        trace = self.replay()["trace"]
        self.assertEqual(trace[9]["actual"]["selected_region"], "15100")
        actual = trace[10]["actual"]
        self.assertEqual(actual["mode"], "NORMAL")
        self.assertEqual(actual["comparison_status"], "BLOCKED")
        self.assertEqual(actual["row_statuses"], [])
        self.assertIsNone(actual["chosen_id"])

    def test_stale_async_event_cannot_restore_old_fixture(self):
        trace = self.replay()["trace"]
        self.assertEqual(trace[11]["actual"]["transition"], "STALE_REJECTED")
        self.assertEqual(trace[11]["actual"]["generation"], 4)
        self.assertEqual(trace[11]["actual"]["mode"], "NORMAL")
        self.assertIsNone(trace[11]["actual"]["fixture_id"])
        self.assertEqual(trace[12]["actual"]["matched_ids"], [])

    def test_exclusive_expiration_without_reducer_tick_blocks_entire_chain(self):
        actual = self.replay()["trace"][14]["actual"]
        self.assertEqual(actual["generation"], 5)
        self.assertEqual(actual["mode"], "NORMAL")
        self.assertIsNone(actual["fixture_id"])
        self.assertEqual(actual["comparison_status"], "BLOCKED")
        self.assertIsNone(actual["chosen_id"])

    def test_source_failure_expired_restart_and_reset_leave_no_old_data(self):
        trace = self.replay()["trace"]
        for i in (16, 18, 20):
            with self.subTest(i=i):
                actual = trace[i]["actual"]
                self.assertEqual(actual["narrow_status"], "BLOCKED")
                self.assertEqual(actual["row_statuses"], [])
                self.assertEqual(actual["matched_ids"], [])
                self.assertIsNone(actual["chosen_id"])
        self.assertEqual(trace[-1]["actual"]["generation"], 8)
        self.assertIsNone(trace[-1]["actual"]["selected_region"])

    def test_human_review_is_never_a_real_facility_or_route_claim(self):
        s = StringIO()
        with redirect_stdout(s):
            self.assertEqual(c.main(["--json"]), 0)
        report = json.loads(s.getvalue())
        self.assertEqual(report["regression"], "PASS")
        self.assertIs(report["synthetic_only"], True)
        self.assertEqual(report["device_qa"], "NOT_RUN")
        for key in ("official_acceptance", "live_data_verified",
                    "facility_safety_verified", "route_safety_verified",
                    "public_release_approved"):
            self.assertIs(report[key], False)
        for trace in report["trace"]:
            self.assertFalse({"shelter_safe", "shelter_open", "route_safe", "latitude",
                              "longitude", "address"} & set(trace["actual"]))

    def test_tampered_expected_choice_is_detected_and_cli_exits_nonzero(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["steps"][1]["expect"]["choice_classification"] = "MATCHED_SYNTHETIC"
        result = c.replay(manifest)
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "FIXED_EXPECTATION_MISMATCH"))
        self.assertIn("choice_classification", result["trace"][-1]["mismatches"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(c.main(["--manifest", str(path)]), 1)

    def test_tampered_expected_generation_is_not_silently_accepted(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["steps"][0]["expect"]["generation"] = 99
        out = c.replay(manifest)
        self.assertEqual((out["status"], out["code"]),
                         ("FAIL", "FIXED_EXPECTATION_MISMATCH"))

    def test_missing_or_unreviewed_expectations_are_blocked(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["steps"][2]["expect"] = {}
        self.assertEqual(c.replay(manifest)["code"], "INVALID_EXPECTATION")
        manifest = copy.deepcopy(self.manifest)
        manifest["steps"][0]["expect"]["facility_open"] = True
        self.assertEqual(c.replay(manifest)["code"], "INVALID_EXPECTATION")

    def test_bad_timezone_or_missing_event_is_blocked(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["steps"][0]["at"] = "2026-11-13T00:00:00"
        result = c.replay(manifest)
        self.assertEqual((result["status"], result["code"]),
                         ("BLOCKED", "INVALID_REPLAY_INPUT"))
        manifest = copy.deepcopy(self.manifest)
        del manifest["steps"][0]["action"]
        self.assertEqual(c.replay(manifest)["status"], "BLOCKED")

    def test_unapproved_official_fixture_and_real_id_are_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["fixture"]["source_authorization"] = "OFFICIAL"
        with self.assertRaisesRegex(ValueError, "synthetic"):
            c.replay(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][0]["record_id"] = "real-location-123"
        with self.assertRaisesRegex(ValueError, "synthetic"):
            c.replay(manifest)

    def test_duplicate_synthetic_record_ids_are_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["records"][1]["record_id"] = manifest["records"][0]["record_id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            c.replay(manifest)

    def test_forged_live_assertion_from_s0_is_an_independent_failure(self):
        original = c.safe_view
        def unsafe_view(*args):
            return replace(original(*args), live_data_verified=True)
        with patch.object(c, "safe_view", side_effect=unsafe_view):
            result = self.replay()
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "LIVE_SAFETY_ASSERTION"))

    def test_c_detects_forged_p2_unknown_promoted_to_match(self):
        original = c.choose_synthetic_for_review
        def forged(*args):
            v = original(*args)
            if v.selected_record_id == "synthetic:chain-c":
                return SimpleNamespace(**{**vars(v), "comparison_status": "MATCHED_SYNTHETIC"})
            return v
        with patch.object(c, "choose_synthetic_for_review", side_effect=forged):
            result = self.replay()
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "CHOICE_PROMOTED_OR_FORGED"))

    def test_c_detects_misleading_p1_totals(self):
        original = c.compare_synthetic_conditions
        from src.hinanex.s1_synthetic_comparison import ComparisonTotals
        def misleading(*args):
            v = original(*args)
            if v.status == "EVALUATED_SYNTHETIC_ONLY":
                return replace(v, totals=ComparisonTotals(6, 0, 0))
            return v
        with patch.object(c, "compare_synthetic_conditions", side_effect=misleading):
            result = self.replay()
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "MISLEADING_COMPARISON_TOTALS"))

    def test_c_detects_blocked_result_leaking_a_previous_id(self):
        original = c.choose_synthetic_for_review
        def stale(*args):
            v = original(*args)
            if v.status == "BLOCKED":
                return SimpleNamespace(**{**vars(v), "selected_record_id": "synthetic:chain-c"})
            return v
        with patch.object(c, "choose_synthetic_for_review", side_effect=stale):
            result = self.replay()
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "BLOCKED_CHOICE_LEAK"))

    def test_manifest_requires_synthetic_and_known_version(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["synthetic_only"] = False
        with self.assertRaisesRegex(ValueError, "manifest"):
            c.replay(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["schema_id"] = "official.live.approved"
        with self.assertRaisesRegex(ValueError, "manifest"):
            c.replay(manifest)


if __name__ == "__main__":
    unittest.main()
