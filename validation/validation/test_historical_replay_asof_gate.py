"""Synthetic tests for the strict historical input preflight; no real disaster approvals."""
import copy
import datetime as dt
import hashlib
import json
import tempfile
from pathlib import Path
import unittest

from historical_replay_asof_gate import preflight, instant, ReplayInputError, main

SHA = hashlib.sha256(b"synthetic official source").hexdigest()
SHA2 = hashlib.sha256(b"synthetic alternate source").hexdigest()
ASOF = "2019-10-12T17:00:00+09:00"
RELEASE = "2019-10-12T16:00:00+09:00"


def sample():
    case = {
        "schema_id": "hinanex.historical_replay_case.v0.1",
        "case_id": "synthetic-2019-edogawa",
        "as_of_jst": ASOF,
        "sources": [
            {"source_id": "bulletin", "role": "INPUT",
             "published_at_jst": RELEASE, "archive_sha256": SHA,
             "observation_at_jst": "2019-10-12T12:00:00+09:00"},
            {"source_id": "future-results", "role": "TRUTH",
             "published_at_jst": "2019-10-13T02:00:00+09:00",
             "archive_sha256": SHA2},
        ],
    }
    reviews = {
        "schema_id": "hinanex.c.historical_input_reviews.v0.1",
        "case_id": case["case_id"],
        "approved_input_sources": [
            {"source_id": "bulletin", "review_state": "C_APPROVED",
             "original_sha256": SHA, "historical_version_verified": True,
             "approval_ref": "C-synthetic-test-only",
             "verified_public_at_jst": RELEASE}
        ],
    }
    return case, reviews


def statuses(report):
    return {row["source_id"]: row for row in report["source_checks"]}


class HistoricalInputGateTests(unittest.TestCase):
    def test_valid_synthetic_evidence_precheck_not_prediction_claim(self):
        case, reviews = sample()
        report = preflight(case, reviews)
        self.assertEqual(report["status"], "PRECHECK_PASSED__HUMAN_REVIEW_REQUIRED")
        self.assertEqual(report["safe_input_source_ids"], ["bulletin"])
        self.assertEqual(statuses(report)["future-results"]["status"], "TRUTH_QUARANTINED")
        self.assertFalse(report["prediction_accuracy_evaluated"])
        self.assertFalse(report["facility_eligibility_evaluated"])
        self.assertTrue(report["human_independent_review_required"])

    def test_no_c_review_does_not_silently_pass(self):
        case, reviews = sample()
        reviews["approved_input_sources"] = []
        output = preflight(case, reviews)
        self.assertEqual(output["status"], "BLOCKED")
        self.assertIn("INDEPENDENT_C_REVIEW_MISSING", statuses(output)["bulletin"]["reasons"])

    def test_future_truth_cannot_be_an_input(self):
        case, reviews = sample()
        case["sources"][1]["role"] = "INPUT"
        out = preflight(case, reviews)
        self.assertIn("AFTER_AS_OF", statuses(out)["future-results"]["reasons"])
        self.assertIn("INDEPENDENT_C_REVIEW_MISSING", statuses(out)["future-results"]["reasons"])

    def test_input_transitively_derived_from_truth_rejected(self):
        case, reviews = sample()
        case["sources"].append({"source_id": "intermediate", "role": "CONTEXT",
                                "archive_sha256": SHA2, "depends_on": ["future-results"]})
        case["sources"][0]["depends_on"] = ["intermediate"]
        out = preflight(case, reviews)
        self.assertIn("TRUTH_LINEAGE_IN_INPUT", statuses(out)["bulletin"]["reasons"])

    def test_current_day_date_only_fails_closed(self):
        case, reviews = sample()
        case["sources"][0]["published_at_jst"] = None
        output = preflight(case, reviews)
        self.assertIn("PUBLICATION_INSTANT_UNKNOWN", statuses(output)["bulletin"]["reasons"])

    def test_observation_time_is_not_release_time(self):
        case, reviews = sample()
        case["sources"][0]["published_at_jst"] = "2019-10-12T18:00:00+09:00"
        output = preflight(case, reviews)
        self.assertIn("AFTER_AS_OF", statuses(output)["bulletin"]["reasons"])

    def test_c_review_earlier_than_claimed_publication_is_rejected(self):
        case, reviews = sample()
        reviews["approved_input_sources"][0]["verified_public_at_jst"] = "2019-10-12T15:00:00+09:00"
        output = preflight(case, reviews)
        self.assertIn("REVIEW_TIME_CONFLICT", statuses(output)["bulletin"]["reasons"])

    def test_c_review_after_snapshot_is_rejected(self):
        case, reviews = sample()
        reviews["approved_input_sources"][0]["verified_public_at_jst"] = "2019-10-12T19:00:00+09:00"
        output = preflight(case, reviews)
        self.assertIn("C_VERIFIED_RELEASE_AFTER_AS_OF", statuses(output)["bulletin"]["reasons"])

    def test_tampered_archive_digest_cannot_reuse_approval(self):
        case, reviews = sample()
        case["sources"][0]["archive_sha256"] = SHA2
        output = preflight(case, reviews)
        self.assertIn("APPROVED_DIGEST_MISMATCH", statuses(output)["bulletin"]["reasons"])

    def test_approval_must_explicitly_verify_historical_version(self):
        case, reviews = sample()
        reviews["approved_input_sources"][0]["historical_version_verified"] = False
        output = preflight(case, reviews)
        self.assertIn("HISTORICAL_VERSION_NOT_C_APPROVED", statuses(output)["bulletin"]["reasons"])

    def test_post_event_source_blocked_even_if_reviewed(self):
        case, reviews = sample()
        case["sources"][0]["post_event_report"] = True
        output = preflight(case, reviews)
        self.assertIn("POST_EVENT_SOURCE_AS_INPUT", statuses(output)["bulletin"]["reasons"])

    def test_wrong_timezone_raises(self):
        for value in ["2019-10-12T17:00:00", "2019-10-12T08:00:00Z", "2019-10-12", "bad", None]:
            with self.subTest(value=value), self.assertRaises(ReplayInputError):
                instant(value)

    def test_no_input_blocks(self):
        case, reviews = sample()
        case["sources"][0]["role"] = "TRUTH"
        self.assertEqual(preflight(case, reviews)["status"], "BLOCKED")

    def test_bad_source_relationships_are_rejected(self):
        case, reviews = sample()
        case["sources"][0]["depends_on"] = ["future-results"]
        case["sources"][1]["depends_on"] = ["bulletin"]
        with self.assertRaisesRegex(ReplayInputError, "cycle"):
            preflight(case, reviews)
        case["sources"][1]["depends_on"] = []
        case["sources"][0]["depends_on"] = ["not-registered"]
        with self.assertRaisesRegex(ReplayInputError, "missing provenance dependency"):
            preflight(case, reviews)

    def test_cli_exit_blocked_and_output_report(self):
        case, reviews = sample()
        reviews["approved_input_sources"] = []
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fcase, freviews, freport = (base / "case.json", base / "reviews.json", base / "out.json")
            fcase.write_text(json.dumps(case), encoding="utf-8")
            freviews.write_text(json.dumps(reviews), encoding="utf-8")
            self.assertEqual(main(["--case", str(fcase), "--c-reviews", str(freviews),
                                   "--out", str(freport)]), 2)
            written = json.loads(freport.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], "BLOCKED")
            self.assertEqual(len(written["case_manifest_sha256"]), 64)
            self.assertEqual(main(["--case", str(fcase), "--c-reviews", str(freviews),
                                   "--out", str(freport)]), 1)


if __name__ == "__main__":
    unittest.main()
