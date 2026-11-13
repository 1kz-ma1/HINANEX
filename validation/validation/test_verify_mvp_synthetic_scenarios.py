"""Independent, deterministic C-only tests for fictional MVP envelope checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

import verify_mvp_synthetic_scenarios as audit


class SyntheticMvpConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(audit.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    def test_fixture_expected_outcomes_are_all_reproduced(self):
        rows = audit.check_manifest(self.manifest)
        self.assertGreaterEqual(len(rows), 12)
        self.assertTrue(all(row["matches_expected"] for row in rows))
        self.assertEqual({row["actual"]["status"] for row in rows}, set(audit.STATUSES))
        self.assertEqual(len(rows), len({row["id"] for row in rows}))

    def test_fail_cases_are_not_mislabeled_as_pass(self):
        rows = audit.check_manifest(self.manifest)
        negative = [r for r in rows if r["actual"]["status"] == "FAIL"]
        self.assertGreaterEqual(len(negative), 9)
        self.assertTrue(all(r["expected"]["status"] == "FAIL" for r in negative))
        self.assertEqual(audit.evaluate(self.manifest["template"]["input"],
                                        self.manifest["template"]["output"]),
                         {"status": "PASS", "code": "CONSISTENT_SYNTHETIC"})

    def test_missing_required_snapshot_is_blocked_not_pass(self):
        base = self.manifest["template"]
        output = copy.deepcopy(base["output"])
        del output["claims"]
        self.assertEqual(audit.evaluate(base["input"], output)["status"], "BLOCKED")
        output = copy.deepcopy(base["output"])
        output["claims"].pop("facility_open")
        self.assertEqual(audit.evaluate(base["input"], output)["code"], "MISSING_CLAIM")

    def test_no_unknown_null_or_missing_fact_can_be_inferred(self):
        base = self.manifest["template"]
        for name, new_value in (("capacity", 0), ("opening_state", "OPEN")):
            output = copy.deepcopy(base["output"])
            output["facts"][name] = new_value
            self.assertEqual(audit.evaluate(base["input"], output)["code"], "UNKNOWN_PROMOTED")
        output = copy.deepcopy(base["output"])
        output["facts"]["newly_invented"] = True
        self.assertEqual(audit.evaluate(base["input"], output)["code"], "UNTRACEABLE_FACT")

    def test_claims_cannot_assert_positive_or_negative_safety(self):
        base = self.manifest["template"]
        for claim in audit.CLAIMS:
            for unsupported in (True, False, "CONFIRMED", "CLOSED"):
                output = copy.deepcopy(base["output"])
                output["claims"][claim] = unsupported
                self.assertEqual(audit.evaluate(base["input"], output)["code"], "UNAPPROVED_CLAIM")

    def test_expiration_boundary_is_deterministic(self):
        base = self.manifest["template"]
        incoming = copy.deepcopy(base["input"])
        output = copy.deepcopy(base["output"])
        incoming["evaluated_at"] = output["valid_until"]
        self.assertEqual(audit.evaluate(incoming, output)["status"], "PASS")
        incoming["evaluated_at"] = "2026-11-13T12:05:01Z"
        self.assertEqual(audit.evaluate(incoming, output)["code"], "EXPIRED_RESULT")

    def test_expected_result_tampering_fails_regression(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["cases"][0]["expected"] = {"status": "FAIL", "code": "MADE_UP"}
        rows = audit.check_manifest(tampered)
        self.assertFalse(all(row["matches_expected"] for row in rows))
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "tampered.json"
            file.write_text(json.dumps(tampered), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(audit.main(["--manifest", str(file)]), 1)

    def test_non_synthetic_manifest_is_rejected(self):
        wrong = copy.deepcopy(self.manifest)
        wrong["synthetic_only"] = False
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            audit.check_manifest(wrong)

    def test_json_cli_keeps_verdicts_separate_from_regression_and_qa(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(audit.main(["--json"]), 0)
        report = json.loads(buffer.getvalue())
        self.assertEqual(report["regression"], "PASS")
        self.assertFalse(report["official_acceptance"])
        self.assertEqual(report["device_qa"], "NOT_RUN")
        self.assertGreater(report["counts"]["FAIL"], 0)
        self.assertGreater(report["counts"]["BLOCKED"], 0)
        self.assertGreater(report["counts"]["NOT_RUN"], 0)


if __name__ == "__main__":
    unittest.main()
