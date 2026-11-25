"""C independent bounded multi-epoch S1-P4 endurance and mutation checks."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import verify_s1_p4_endurance as c


class S1P4IndependentEnduranceTests(unittest.TestCase):
    def test_full_48_cycles_repeated_actions_and_projections_pass(self):
        result = c.run_endurance()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["cycles_completed"], 48)
        self.assertEqual(result["actions_executed"], 48 * 18)
        self.assertEqual(result["expiry_boundaries_checked"], 10)
        self.assertEqual(result["stale_actions_rejected"], 48 * 4 + 10)
        self.assertEqual(result["projections_checked"], 48 * 16 + 10)

    def test_max_64_cycles_is_bounded_and_succeeds(self):
        result = c.run_endurance(64)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["cycles_completed"], 64)
        self.assertEqual(result["actions_executed"], 64 * 18)
        self.assertEqual(result["expiry_boundaries_checked"], 13)
        self.assertGreater(result["projections_checked"], 64 * 16)

    def test_first_cycle_exercises_expiration_without_reducer_tick(self):
        report = c.run_endurance(1)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["expiry_boundaries_checked"], 1)
        self.assertEqual(report["stale_actions_rejected"], 5)

    def test_all_four_terminal_actions_and_expiry_are_exercised(self):
        report = c.run_endurance(6)
        self.assertEqual(report["status"], "PASS")
        # 0 expiry; 1 source_failed; 2 select_region; 3 reset;
        # 4 stop; 5 expiry. All terminate before the new B phase.
        self.assertEqual(report["expiry_boundaries_checked"], 2)
        self.assertEqual(report["cycles_completed"], 6)
        self.assertEqual(report["actions_executed"], 6 * 18)

    def test_independent_fixture_versions_and_raw_status_source(self):
        a, rows_a = c.fictional_data(0, "A")
        b, rows_b = c.fictional_data(0, "B")
        self.assertNotEqual(a.fixture_id, b.fixture_id)
        self.assertNotEqual({x.record_id for x in rows_a}, {x.record_id for x in rows_b})
        self.assertEqual(len(rows_a), 6)
        self.assertEqual(len(rows_b), 6)
        self.assertEqual(a.source_authorization, "SYNTHETIC_TEST_ONLY")
        self.assertEqual(b.source_authorization, "SYNTHETIC_TEST_ONLY")
        self.assertNotEqual(rows_a[0].conditions, rows_b[0].conditions)
        self.assertNotEqual(rows_a[-1].fixture_id, a.fixture_id)
        self.assertNotEqual(rows_b[-1].fixture_id, b.fixture_id)

    def test_invalid_cycle_inputs_rejected_not_wrapped_or_defaulted(self):
        for value in (-1, 0, 65, True, 1.5, "6", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    c.run_endurance(value)
        for bad in (-1, 64, True, "a"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    c.fictional_data(bad, "A")
        with self.assertRaises(ValueError):
            c.fictional_data(0, "REAL")

    def test_deterministic_bounded_report_no_personal_or_raw_fields(self):
        first = c.run_endurance(2)
        self.assertEqual(first, c.run_endurance(2))
        self.assertEqual(first["schema_id"], c.SCHEMA)
        self.assertIs(first["synthetic_only"], True)
        for key in ("eligible_for_s1_real_facilities", "official_acceptance",
                    "live_data_verified", "facility_safety_verified",
                    "route_safety_verified", "release_approved"):
            self.assertIs(first[key], False)
        self.assertEqual(first["device_qa"], "NOT_RUN")
        text = json.dumps(first)
        for prohibited in ("latitude", "longitude", "address", "raw_sha256",
                           "session_token", "official_shelter", "current_shelter_open",
                           "synthetic:resilience-", "selected_record_id"):
            self.assertNotIn(prohibited, text)
        self.assertLess(len(text), 1200)

    def test_cli_success_is_only_synthetic_test_not_real_approval(self):
        sink = StringIO()
        with redirect_stdout(sink):
            self.assertEqual(c.main(["--cycles", "2", "--json"]), 0)
        report = json.loads(sink.getvalue())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["cycles_completed"], 2)
        self.assertFalse(report["eligible_for_s1_real_facilities"])
        self.assertFalse(report["release_approved"])

    def test_cli_rejects_out_of_range_without_success(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(c.main(["--cycles", "65"]), 2)
        self.assertIn("NO_APPROVAL", stderr.getvalue())

    def test_cli_does_not_generate_files_or_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as path:
            input_path = Path(path) / "do_not_touch.txt"
            input_path.write_text("sentinel", encoding="utf-8")
            before = list(Path(path).iterdir())
            with redirect_stdout(StringIO()):
                self.assertEqual(c.main(["--cycles", "1"]), 0)
            self.assertEqual(list(Path(path).iterdir()), before)
            self.assertEqual(input_path.read_text(encoding="utf-8"), "sentinel")

    def test_mutated_old_callback_selection_is_rejected_by_c(self):
        original = c.apply_walkthrough_intent
        def faulty(state, intent, records, now):
            result = original(state, intent, records, now)
            if (result.reason_code == "STALE_WALKTHROUGH_ACTION"
                    and state.session.mode.value == "DRILL"):
                return replace(result, state=replace(
                    result.state, selected_record_id=records[0].record_id))
            return result
        with patch.object(c, "apply_walkthrough_intent", side_effect=faulty):
            result = c.run_endurance(1)
        self.assertEqual((result["status"], result["reason_code"]),
                         ("FAIL", "STALE_COMMAND_MUTATED_CURRENT_STATE"))

    def test_mutated_filter_cannot_retain_previous_review(self):
        original = c.apply_walkthrough_intent
        def faulty(state, intent, records, now):
            result = original(state, intent, records, now)
            if (intent.kind == c.IntentKind.SET_CONDITIONS
                    and result.status == "APPLIED_SYNTHETIC_ONLY"
                    and state.selected_record_id is not None):
                return replace(result, state=replace(
                    result.state, selected_record_id=state.selected_record_id))
            return result
        with patch.object(c, "apply_walkthrough_intent", side_effect=faulty):
            result = c.run_endurance(1)
        self.assertEqual((result["status"], result["reason_code"]),
                         ("FAIL", "FILTER_RETAINED_OLD_REVIEW"))

    def test_mutated_unknown_as_match_fails_independent_p1_check(self):
        original = c.project_walkthrough
        def faulty(state, records, now):
            projection = original(state, records, now)
            if (projection.result is not None
                    and projection.result.after_conditions == c.STEP):
                rows = list(projection.result.rows)
                rows[4] = replace(rows[4], after_status="MATCHED_SYNTHETIC")
                return replace(projection, result=replace(
                    projection.result, rows=tuple(rows)))
            return projection
        with patch.object(c, "project_walkthrough", side_effect=faulty):
            result = c.run_endurance(1)
        self.assertEqual((result["status"], result["reason_code"]),
                         ("FAIL", "WHAT_IF_CHANGED_SOURCE_CLASSIFICATION"))

    def test_forged_live_status_is_detected_not_counted_as_pass(self):
        original = c.project_walkthrough
        def faulty(*args):
            p = original(*args)
            return SimpleNamespace(**{**vars(p), "live_data_verified": True})
        with patch.object(c, "project_walkthrough", side_effect=faulty):
            result = c.run_endurance(1)
        self.assertEqual((result["status"], result["reason_code"]),
                         ("FAIL", "PROJECTION_REAL_WORLD_APPROVAL_LEAK"))

    def test_broken_version_increments_fail_before_next_epoch(self):
        original = c.apply_walkthrough_intent
        def faulty(state, intent, records, now):
            t = original(state, intent, records, now)
            if (intent.kind == c.IntentKind.SET_CONDITIONS
                    and t.status == "APPLIED_SYNTHETIC_ONLY"):
                return replace(t, state=replace(t.state, revision=state.revision))
            return t
        with patch.object(c, "apply_walkthrough_intent", side_effect=faulty):
            r = c.run_endurance(1)
        self.assertEqual((r["status"], r["reason_code"]),
                         ("FAIL", "WRONG_VERSION_INCREMENT"))

    def test_stale_review_when_restart_uses_new_fixture_does_not_leak(self):
        output = c.run_endurance(6)
        self.assertEqual(output["status"], "PASS")
        self.assertGreaterEqual(output["stale_actions_rejected"], 6 * 4)

    def test_report_does_not_confuse_endurance_with_memory_profiling(self):
        report = c.run_endurance(1)
        self.assertEqual(report["status"], "PASS")
        self.assertNotIn("memory_safe", report)
        self.assertNotIn("rss", report)
        self.assertNotIn("memory_growth", report)


if __name__ == "__main__":
    unittest.main()
