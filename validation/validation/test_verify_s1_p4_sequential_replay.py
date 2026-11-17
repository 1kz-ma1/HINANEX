"""C independent sequential S0/S1-P4 regression and fault-injection coverage."""
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

import verify_s1_p4_sequential_replay as c


def load():
    return json.loads(c.FIXTURE.read_text(encoding="utf-8"))


def trace(result, scenario):
    return [row for row in result["trace"] if row["scenario_id"] == f"synthetic:{scenario}"]


class S1P4SequentialIndependentReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = load()
        cls.result = c.replay(cls.packet)

    def test_five_scenarios_forty_fixed_checkpoints_match(self):
        self.assertEqual((self.result["status"], self.result["code"]),
                         ("PASS", "S1_P4_SYNTHETIC_SEQUENCE_MATCHED"))
        self.assertEqual(self.result["scenario_count"], 5)
        self.assertEqual(self.result["step_count"], 40)
        self.assertEqual(len(self.result["trace"]), 40)

    def test_real_p4_start_then_projection_is_current(self):
        rows = trace(self.result, "normal-change-review-stop")
        start = rows[0]["actual"]
        self.assertEqual((start["mode"], start["generation"], start["revision"]),
                         ("DRILL", 1, 1))
        self.assertEqual(start["transition"], "APPLIED_SYNTHETIC_ONLY")
        self.assertEqual(start["fixture_id"], "synthetic:p4-c-fixture")
        self.assertEqual(rows[1]["actual"]["after_statuses"], [
            "MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC",
            "NOT_MATCHED_SYNTHETIC", "UNKNOWN",
            "NOT_MATCHED_SYNTHETIC", "UNKNOWN",
        ])

    def test_before_after_change_is_real_and_independently_checked_against_p1(self):
        state = trace(self.result, "normal-change-review-stop")[3]["actual"]
        self.assertEqual(state["previous_conditions"], ["pet_support"])
        self.assertEqual(state["conditions"], ["step_free"])
        self.assertEqual(state["new_ids"], ["synthetic:c", "synthetic:d"])
        self.assertEqual(state["removed_ids"], ["synthetic:b"])
        self.assertEqual(state["unknown_ids"], ["synthetic:e", "synthetic:foreign"])

    def test_filter_change_clears_previous_user_selection(self):
        steps = trace(self.result, "normal-change-review-stop")
        self.assertEqual(steps[2]["actual"]["selected_id"], "synthetic:a")
        self.assertIsNone(steps[3]["actual"]["selected_id"])
        self.assertIsNone(steps[3]["actual"]["review_id"])
        self.assertEqual(steps[3]["actual"]["revision"], 3)

    def test_explicit_unknown_review_retains_missing_condition(self):
        steps = trace(self.result, "normal-change-review-stop")
        choice = steps[5]["actual"]
        self.assertEqual(choice["selected_id"], "synthetic:e")
        self.assertEqual(choice["review_classification"], "UNKNOWN")
        self.assertEqual(choice["review_missing"], ["step_free"])
        self.assertEqual(choice["review_failed"], [])
        self.assertEqual(choice["projection"], "EVALUATED_SYNTHETIC_ONLY")

    def test_clear_review_and_foreign_fixture_review_are_safe(self):
        steps = trace(self.result, "normal-change-review-stop")
        self.assertIsNone(steps[6]["actual"]["review_id"])
        foreign = steps[7]["actual"]
        self.assertEqual(foreign["transition"], "BLOCKED")
        self.assertEqual(foreign["transition_reason"],
                         "RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE")
        self.assertIsNone(foreign["selected_id"])
        self.assertIn("synthetic:foreign", foreign["unknown_ids"])

    def test_stop_has_zero_comparison_or_selected_data(self):
        steps = trace(self.result, "normal-change-review-stop")
        stopped = steps[-2]["actual"]
        for item in (stopped, steps[-1]["actual"]):
            self.assertEqual(item["projection"], "BLOCKED")
            self.assertEqual(item["after_statuses"], [])
            self.assertEqual(item["new_ids"], [])
            self.assertEqual(item["unknown_ids"], [])
            self.assertIsNone(item["review_id"])
            self.assertIsNone(item["selected_id"])
            self.assertEqual(item["mode"], "NORMAL")

    def test_late_review_same_s0_generation_is_rejected(self):
        steps = trace(self.result, "stale-interaction-region-restart")
        stale = steps[2]["actual"]
        self.assertEqual(stale["transition_reason"], "STALE_WALKTHROUGH_ACTION")
        self.assertEqual((stale["generation"], stale["revision"]), (1, 2))
        self.assertEqual(stale["conditions"], ["step_free"])
        self.assertIsNone(stale["selected_id"])

    def test_late_filter_does_not_erase_newer_selected_review(self):
        steps = trace(self.result, "stale-interaction-region-restart")
        self.assertEqual(steps[3]["actual"]["selected_id"], "synthetic:e")
        late = steps[4]["actual"]
        self.assertEqual(late["transition"], "BLOCKED")
        self.assertEqual(late["conditions"], ["step_free"])
        self.assertEqual(late["revision"], 3)
        self.assertEqual(late["review_classification"], "UNKNOWN")

    def test_region_change_blocks_delayed_choice_then_fresh_start(self):
        steps = trace(self.result, "stale-interaction-region-restart")
        self.assertEqual(steps[6]["actual"]["region"], "15100")
        self.assertEqual(steps[6]["actual"]["mode"], "NORMAL")
        self.assertEqual(steps[7]["actual"]["transition"], "BLOCKED")
        restarted = steps[8]["actual"]
        self.assertEqual((restarted["generation"], restarted["revision"]), (3, 5))
        self.assertEqual(restarted["region"], "13123")
        self.assertEqual(restarted["conditions"], ["pet_support"])
        self.assertIsNone(restarted["review_id"])

    def test_expiry_without_tick_never_projects_old_selected_result(self):
        steps = trace(self.result, "expiry-without-tick")
        self.assertEqual(steps[2]["actual"]["view_mode"], "DRILL")
        expired = steps[3]["actual"]
        self.assertEqual(expired["mode"], "DRILL")
        self.assertEqual(expired["view_mode"], "NORMAL")
        self.assertEqual(expired["projection_reason"], "DRILL_EXPIRED_OR_NOT_YET_VALID")
        self.assertEqual(expired["after_statuses"], [])
        self.assertIsNone(expired["review_id"])
        self.assertIsNone(expired["fixture_id"])

    def test_first_action_after_expiry_clears_state_and_advances_versions(self):
        steps = trace(self.result, "expiry-without-tick")
        after = steps[4]["actual"]
        self.assertEqual(after["transition_reason"], "STALE_WALKTHROUGH_ACTION")
        self.assertEqual((after["generation"], after["revision"]), (2, 3))
        self.assertEqual(after["mode"], "NORMAL")
        self.assertIsNone(after["selected_id"])
        self.assertEqual(after["conditions"], [])
        self.assertEqual(steps[5]["actual"]["transition_reason"],
                         "DRILL_INPUT_INVALID_OR_EXPIRED")

    def test_source_failure_and_reset_cannot_resurrect_old_choice(self):
        steps = trace(self.result, "source-failure-reset")
        self.assertEqual(steps[2]["actual"]["transition_reason"],
                         "SYNTHETIC_CONTEXT_CLEARED")
        self.assertEqual(steps[2]["actual"]["mode"], "NORMAL")
        self.assertEqual(steps[4]["actual"]["generation"], 3)
        self.assertIsNone(steps[4]["actual"]["review_id"])
        self.assertEqual(steps[5]["actual"]["region"], None)
        self.assertEqual(steps[6]["actual"]["projection"], "BLOCKED")

    def test_nonmatching_row_can_be_reviewed_but_never_promoted(self):
        steps = trace(self.result, "invalid-review-and-nonmatch")
        self.assertEqual(steps[1]["actual"]["transition"], "BLOCKED")
        self.assertEqual(steps[1]["actual"]["revision"], 2)
        self.assertEqual(steps[2]["actual"]["review_classification"],
                         "NOT_MATCHED_SYNTHETIC")
        self.assertEqual(steps[2]["actual"]["review_failed"], ["pet_support"])
        self.assertIsNone(steps[3]["actual"]["review_id"])

    def test_no_real_data_claims_in_cli_report(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(c.main(["--json"]), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["regression"], "PASS")
        self.assertEqual(report["device_qa"], "NOT_RUN")
        self.assertIs(report["synthetic_only"], True)
        for field in ("official_acceptance", "live_data_verified",
                      "facility_safety_verified", "route_safety_verified",
                      "public_release_approved"):
            self.assertIs(report[field], False)
        raw = out.getvalue()
        for prohibited in ("latitude", "longitude", "address", "current_shelter_open",
                           "license_approved", "actual_facility"):
            self.assertNotIn(prohibited, raw)

    def test_mutating_fixed_expectation_fails_not_passes(self):
        packet = load()
        packet["scenarios"][0]["steps"][3]["expect"]["new_ids"] = ["synthetic:e"]
        result = c.replay(packet)
        self.assertEqual((result["status"], result["code"]),
                         ("FAIL", "C_FIXED_EXPECTATION_MISMATCH"))
        self.assertIn("new_ids", result["trace"][-1]["mismatches"])

    def test_mutating_only_version_expectation_fails(self):
        packet = load()
        packet["scenarios"][1]["steps"][4]["expect"]["revision"] = 99
        result = c.replay(packet)
        self.assertEqual(result["code"], "C_FIXED_EXPECTATION_MISMATCH")

    def test_missing_expected_field_fails_closed(self):
        packet = load()
        del packet["scenarios"][0]["steps"][0]["expect"]["fixture_id"]
        result = c.replay(packet)
        self.assertEqual((result["status"], result["code"]),
                         ("BLOCKED", "MISSING_OR_UNREVIEWED_EXPECTATION"))

    def test_forged_live_status_is_independent_failure(self):
        original = c.project_walkthrough
        def spoof(*args):
            result = original(*args)
            return SimpleNamespace(**{**vars(result), "live_data_verified": True})
        with patch.object(c, "project_walkthrough", side_effect=spoof):
            result = c.replay(load())
        self.assertEqual(result["code"], "PROJECTION_REAL_WORLD_APPROVAL_LEAK")

    def test_p3_fake_unknown_as_match_detected_without_using_fixture_only(self):
        original = c.project_walkthrough
        def spoof(*args):
            p = original(*args)
            if p.result:
                rows = list(p.result.rows)
                rows[3] = replace(rows[3], after_status="MATCHED_SYNTHETIC")
                return replace(p, result=replace(p.result, rows=tuple(rows)))
            return p
        with patch.object(c, "project_walkthrough", side_effect=spoof):
            result = c.replay(load())
        self.assertEqual(result["code"], "WHAT_IF_CHANGED_SOURCE_CLASSIFICATION")

    def test_p2_fake_unknown_promotion_detected_against_independent_p1(self):
        original = c.project_walkthrough
        def spoof(*args):
            p = original(*args)
            if p.result and p.result.review and p.result.review.comparison_status == "UNKNOWN":
                review = replace(p.result.review, comparison_status="MATCHED_SYNTHETIC")
                return replace(p, result=replace(p.result, review=review))
            return p
        with patch.object(c, "project_walkthrough", side_effect=spoof):
            result = c.replay(load())
        self.assertEqual(result["code"], "REVIEW_CLASSIFICATION_PROMOTED_OR_STALE")

    def test_stale_command_that_mutates_current_selection_fails(self):
        original = c.apply_walkthrough_intent
        def spoof(state, intent, records, now):
            transition = original(state, intent, records, now)
            if transition.reason_code == "STALE_WALKTHROUGH_ACTION" and state.session.mode.value == "DRILL":
                return replace(transition, state=replace(transition.state,
                                                        selected_record_id="synthetic:a"))
            return transition
        with patch.object(c, "apply_walkthrough_intent", side_effect=spoof):
            result = c.replay(load())
        self.assertEqual(result["code"], "STALE_ACTION_MUTATED_CURRENT_SESSION")

    def test_filter_change_that_keeps_old_selection_fails(self):
        original = c.apply_walkthrough_intent
        def spoof(state, intent, records, now):
            transition = original(state, intent, records, now)
            if intent.kind == c.IntentKind.SET_CONDITIONS and state.selected_record_id:
                return replace(transition, state=replace(
                    transition.state, selected_record_id=state.selected_record_id))
            return transition
        with patch.object(c, "apply_walkthrough_intent", side_effect=spoof):
            result = c.replay(load())
        self.assertEqual(result["code"], "FILTER_CHANGE_RETAINED_REVIEW")

    def test_real_record_id_is_not_accepted_in_replay_fixture(self):
        packet = load()
        packet["records"][0]["record_id"] = "actual:facility"
        with self.assertRaisesRegex(c.ReplayInputError, "synthetic"):
            c.replay(packet)

    def test_no_claim_of_official_source_with_tampered_fixture(self):
        packet = load()
        packet["fixture"]["source_authorization"] = "OFFICIAL"
        with self.assertRaises(ValueError):
            c.replay(packet)

    def test_input_timestamp_without_timezone_blocked(self):
        packet = load()
        packet["scenarios"][0]["steps"][0]["at"] = "2026-11-13T00:00:00"
        result = c.replay(packet)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["code"], "INVALID_SYNTHETIC_INPUT_OR_RUNTIME")

    def test_duplicate_scenario_and_record_ids_rejected(self):
        packet = load()
        packet["scenarios"].append(copy.deepcopy(packet["scenarios"][0]))
        with self.assertRaises(c.ReplayInputError):
            c.replay(packet)
        packet = load()
        packet["records"][1]["record_id"] = packet["records"][0]["record_id"]
        with self.assertRaises(ValueError):
            c.replay(packet)

    def test_cli_tamper_exits_nonzero_and_never_overwrites_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = load()
            packet["scenarios"][0]["steps"][0]["expect"]["generation"] = 666
            path = Path(tmp)/"synthetic_c_replay.json"
            content = json.dumps(packet, ensure_ascii=False)
            path.write_text(content, encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(c.main(["--packet", str(path)]), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), content)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),
                             ["synthetic_c_replay.json"])

    def test_determinism_and_no_change_to_expected_packet(self):
        packet = load()
        prior = copy.deepcopy(packet)
        first = c.replay(packet)
        second = c.replay(packet)
        self.assertEqual(first, second)
        self.assertEqual(packet, prior)


if __name__ == "__main__":
    unittest.main()
