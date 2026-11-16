"""Independent C consumer tests against the actual draft S0 reducer (no mock reducer)."""
from dataclasses import replace
from contextlib import redirect_stdout
from io import StringIO
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_s0_session_replay as c


class S0RealReducerReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(c.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def test_all_expected_replay_outcomes(self):
        rows = c.check_manifest(self.manifest)
        self.assertEqual(len(rows), 14)
        self.assertTrue(all(row["matches_expected"] for row in rows))
        self.assertEqual({row["actual"]["status"] for row in rows}, {"PASS", "BLOCKED", "NOT_RUN"})

    def test_replays_real_s0_generated_outputs_not_only_fixture_expectations(self):
        case = next(x for x in self.manifest["cases"] if x["id"] == "start_and_stop")
        actual = c.replay_case(case, self.manifest["fixtures"])
        self.assertEqual(actual["status"], "PASS")
        self.assertEqual(actual["trace"][0]["actual_view"]["mode"], "DRILL")
        self.assertEqual(actual["trace"][0]["actual_view"]["generation"], 1)
        self.assertEqual(actual["trace"][1]["actual_view"]["mode"], "NORMAL")
        self.assertIsNone(actual["trace"][1]["actual_view"]["fixture_id"])

    def test_stale_async_action_is_rejected_without_restoring_drill(self):
        case = next(x for x in self.manifest["cases"] if x["id"] == "old_async_event_cannot_restore")
        actual = c.replay_case(case, self.manifest["fixtures"])
        self.assertEqual(actual["status"], "PASS")
        last = actual["trace"][-1]
        self.assertEqual(last["transition"], "STALE_REJECTED")
        self.assertEqual(last["actual_view"]["selected_region"], "15100")
        self.assertEqual(last["actual_view"]["mode"], "NORMAL")
        self.assertIsNone(last["actual_view"]["fixture_id"])

    def test_expired_drill_not_exposed_even_without_tick(self):
        case = next(x for x in self.manifest["cases"] if x["id"] == "expires_without_reducer_tick")
        actual = c.replay_case(case, self.manifest["fixtures"])
        self.assertEqual(actual["status"], "PASS")
        expired = actual["trace"][1]["actual_view"]
        self.assertEqual(expired["mode"], "NORMAL")
        self.assertEqual(expired["reason"], "DRILL_EXPIRED_OR_NOT_YET_VALID")
        self.assertIsNone(expired["hazard"])
        self.assertIsNone(expired["source_authorization"])

    def test_independent_c_check_catches_invalid_live_assertion(self):
        original = c.safe_view
        def unsafe_view(*args):
            return replace(original(*args), live_data_verified=True)
        case = next(x for x in self.manifest["cases"] if x["id"] == "start_and_stop")
        with patch.object(c, "safe_view", side_effect=unsafe_view):
            actual = c.replay_case(case, self.manifest["fixtures"])
        self.assertEqual(actual["status"], "FAIL")
        self.assertEqual(actual["code"], "LIVE_ASSERTION")

    def test_actual_output_mismatch_is_regression_failure(self):
        changed = copy.deepcopy(self.manifest)
        case = changed["cases"][0]
        case["steps"][0]["expect"]["view"]["generation"] = 9
        rows = c.check_manifest(changed)
        self.assertFalse(rows[0]["matches_expected"])
        self.assertEqual(rows[0]["actual"]["code"], "OUTPUT_MISMATCH")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(c.main(["--manifest", str(path)]), 1)

    def test_unknown_or_unsupported_source_is_never_approved(self):
        invalid = copy.deepcopy(self.manifest["fixtures"]["flood_a"])
        invalid["source_authorization"] = "OFFICIAL"
        with self.assertRaises(ValueError):
            c.build_fixture(invalid)

    def test_c_does_not_synthesize_shelter_open_or_route_claims(self):
        row = next(x for x in c.check_manifest(self.manifest) if x["id"] == "switch_hazard_and_region_requires_new_fixture")
        self.assertEqual(row["actual"]["status"], "PASS")
        for step in row["actual"]["trace"]:
            self.assertTrue(set(step["actual_view"]) == set(c.SAFE_OUTPUT_KEYS))
            self.assertFalse({"facility_safety", "facility_open", "route_passability"} & set(step["actual_view"]))
        self.assertEqual(row["actual"]["trace"][-1]["actual_view"]["hazard"], "landslide")
        self.assertEqual(row["actual"]["trace"][-1]["actual_view"]["selected_region"], "15100")

    def test_blocked_and_not_run_are_distinct(self):
        rows = c.check_manifest(self.manifest)
        statuses = {r["id"]: r["actual"]["status"] for r in rows}
        self.assertEqual(statuses["insufficient_steps_are_blocked"], "BLOCKED")
        self.assertEqual(statuses["device_integration_not_executed"], "NOT_RUN")

    def test_invalid_manifest_rejected_and_bad_timestamp_blocked(self):
        invalid = copy.deepcopy(self.manifest)
        invalid["synthetic_only"] = False
        with self.assertRaises(ValueError):
            c.check_manifest(invalid)
        invalid = copy.deepcopy(self.manifest)
        invalid["fixtures"]["flood_a"]["observed_at"] = "2026-11-13T00:00:00"
        case = next(x for x in invalid["cases"] if x["id"] == "start_and_stop")
        actual = c.replay_case(case, invalid["fixtures"])
        self.assertEqual(actual["status"], "BLOCKED")
        self.assertEqual(actual["code"], "INVALID_REPLAY_INPUT")

    def test_cli_reports_regression_separately_from_safety_and_device_qa(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(c.main(["--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["regression"], "PASS")
        self.assertFalse(report["official_acceptance"])
        self.assertEqual(report["device_qa"], "NOT_RUN")
        self.assertEqual(report["counts"], {"PASS": 12, "FAIL": 0, "BLOCKED": 1, "NOT_RUN": 1})


if __name__ == "__main__":
    unittest.main()
