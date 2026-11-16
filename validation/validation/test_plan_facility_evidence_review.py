"""Offline C review-queue regression; all examples are invented metadata."""
from __future__ import annotations

import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preflight_facility_evidence_packet as packet_check
import plan_facility_evidence_review as queue


def fixture():
    return json.loads(packet_check.DEFAULT_MANIFEST.read_text(encoding="utf-8"))


def one_complete():
    p = fixture()
    p["records"] = [p["records"][0]]
    return p


def find_task(result, case_id, reason):
    case = next(x for x in result["cases"] if x["case_id"] == case_id)
    return next(x for x in case["tasks"] if x["reason_code"] == reason)


class FacilityEvidenceReviewQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = fixture()
        cls.report = queue.plan(cls.original)

    def test_work_queue_has_three_cases_and_four_mandatory_gates_each(self):
        out = self.report
        self.assertEqual(out["schema_id"], queue.SCHEMA_ID)
        self.assertEqual(out["status"], "REVIEW_WORK_QUEUE_ONLY__REAL_DATA_ADOPTION_HOLD")
        self.assertEqual(out["case_count"], 3)
        self.assertEqual(out["mandatory_authentication_task_count"], 12)
        self.assertGreater(out["gap_remediation_task_count"], 0)
        self.assertEqual(out["open_task_count"],
                         out["gap_remediation_task_count"] + 12)
        self.assertEqual([x["case_id"] for x in out["cases"]], [
            "synthetic:packet-complete", "synthetic:packet-incomplete",
            "synthetic:packet-conflict",
        ])

    def test_complete_metadata_is_still_four_open_human_review_tasks(self):
        out = queue.plan(one_complete())
        self.assertEqual(out["source_preflight_status"],
                         "PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED")
        self.assertEqual(out["gap_remediation_task_count"], 0)
        self.assertEqual(out["mandatory_authentication_task_count"], 4)
        self.assertEqual(out["open_task_count"], 4)
        self.assertEqual(
            [task["evidence_area"] for task in out["cases"][0]["tasks"]],
            ["source", "identity", "hazard_meaning", "reuse"],
        )
        self.assertTrue(all(t["kind"] == "INDEPENDENT_AUTHENTICATION"
                            for t in out["cases"][0]["tasks"]))

    def test_no_review_task_or_output_can_approve_real_facilities(self):
        r = self.report
        for key in (
            "source_bytes_authenticated_by_this_run",
            "independent_human_approval_recorded_by_this_run",
            "official_facility_identity_approved",
            "hazard_semantics_approved", "dataset_reuse_approved",
            "eligible_for_s1_real_facilities", "publication_approved",
        ):
            self.assertIs(r[key], False)
        self.assertIs(r["human_decision_required"], True)
        for case in r["cases"]:
            for task in case["tasks"]:
                self.assertEqual(task["status"], "OPEN__UNVERIFIED")
                self.assertFalse(task["approval_granted"])
                self.assertTrue(task["requires_human_review"])

    def test_evidence_gap_reasons_are_not_dropped_or_invented(self):
        original = packet_check.preflight(self.original)
        for planned, diagnosed in zip(self.report["cases"], original["rows"]):
            got = sorted(t["reason_code"] for t in planned["tasks"]
                         if t["kind"] == "GAP_REMEDIATION")
            self.assertEqual(got, diagnosed["reason_codes"])
            self.assertEqual(planned["gap_reason_count"], len(got))

    def test_missing_original_raw_and_source_version_are_assigned_to_a(self):
        case = "synthetic:packet-incomplete"
        raw = find_task(self.report, case, "SOURCE_RAW_SHA_MISSING")
        self.assertEqual(raw["responsible_roles"], ["A"])
        self.assertEqual(raw["required_field_paths"], ["source.raw_sha256"])
        rev = find_task(self.report, case, "SOURCE_REVISION_MISSING")
        self.assertEqual(rev["required_field_paths"], ["source.source_revision"])

    def test_independent_byte_audit_gap_is_assigned_to_c(self):
        t = find_task(self.report, "synthetic:packet-incomplete",
                      "SOURCE_C_BYTE_AUDIT_MISSING")
        self.assertEqual(t["responsible_roles"], ["C"])
        self.assertEqual(t["required_field_paths"], ["source.c_raw_audit_sha256"])

    def test_cross_source_pair_independent_review_is_distinct(self):
        task = find_task(self.report, "synthetic:packet-incomplete",
                         "IDENTITY_INDEPENDENT_PAIR_REVIEW_MISSING")
        self.assertEqual(task["evidence_area"], "identity")
        self.assertEqual(task["responsible_roles"], ["C"])
        self.assertEqual(task["action_code"], "OBTAIN_INDEPENDENT_REVIEW_RECORD")
        gates = [x for x in self.report["cases"][1]["tasks"]
                 if x["action_code"] == "CROSS_SOURCE_PHYSICAL_FACILITY_PAIR_REVIEW"]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0]["kind"], "INDEPENDENT_AUTHENTICATION")

    def test_hazard_meaning_not_derived_from_raw_marker(self):
        task = find_task(self.report, "synthetic:packet-incomplete",
                         "HAZARD_ORIGINAL_MARKER_MISSING")
        self.assertEqual(task["required_field_paths"],
                         ["hazard_meaning.raw_marker"])
        gates = [x for x in self.report["cases"][1]["tasks"]
                 if x["action_code"] == "OFFICIAL_MARKER_AND_HAZARD_SCOPE_REVIEW"]
        self.assertEqual(gates[0]["responsible_roles"], ["A", "C", "D"])

    def test_license_terms_exception_and_independent_credit_remain_separate(self):
        case = "synthetic:packet-incomplete"
        terms = find_task(self.report, case, "REUSE_TERMS_URL_MISSING")
        exception = find_task(self.report, case, "REUSE_EXCEPTION_CHECK_MISSING")
        self.assertEqual(terms["required_field_paths"], ["reuse.terms_url"])
        self.assertEqual(exception["required_field_paths"], ["reuse.exception_check_ref"])
        self.assertEqual(terms["responsible_roles"], ["A"])
        gate = find_task(self.report, case, "DATASET_SPECIFIC_REUSE_AND_CREDIT_REVIEW")
        self.assertEqual(gate["responsible_roles"], ["A", "OWNER"])

    def test_changed_source_sha_reopens_three_different_review_scopes(self):
        case = "synthetic:packet-conflict"
        for reason, area in (
            ("IDENTITY_SOURCE_REVISION_BINDING_MISMATCH", "identity"),
            ("HAZARD_MEANING_SOURCE_REVISION_BINDING_MISMATCH", "hazard_meaning"),
            ("REUSE_SOURCE_REVISION_BINDING_MISMATCH", "reuse"),
        ):
            with self.subTest(reason=reason):
                task = find_task(self.report, case, reason)
                self.assertEqual(task["evidence_area"], area)
                self.assertEqual(task["action_code"],
                                 "RECONCILE_CONFLICT_AND_RECHECK_SOURCE")
                self.assertEqual(task["required_field_paths"],
                                 ["source.raw_sha256", area + ".bound_source_sha256"])

    def test_disagreement_between_raw_and_c_audit_requires_independent_investigation(self):
        task = find_task(self.report, "synthetic:packet-conflict",
                         "SOURCE_RAW_AUDIT_SHA_MISMATCH")
        self.assertEqual(task["responsible_roles"], ["C"])
        self.assertEqual(task["required_field_paths"],
                         ["source.raw_sha256", "source.c_raw_audit_sha256"])

    def test_disposition_conflict_is_a_remediation_task_not_auto_acceptance(self):
        task = find_task(self.report, "synthetic:packet-conflict",
                         "IDENTITY_EVIDENCE_CONFLICT")
        self.assertEqual(task["kind"], "GAP_REMEDIATION")
        self.assertEqual(task["action_code"], "RECONCILE_CONFLICT_AND_RECHECK_SOURCE")
        self.assertFalse(task["approval_granted"])

    def test_null_review_disposition_still_queues_missing_human_review(self):
        p = one_complete()
        p["records"][0]["identity"]["disposition"] = None
        result = queue.plan(p)
        case = result["cases"][0]
        self.assertGreater(case["gap_reason_count"], 0)
        self.assertEqual(
            find_task(result, case["case_id"],
                      "IDENTITY_INDEPENDENT_REVIEW_UNRESOLVED")["status"],
            "OPEN__UNVERIFIED",
        )

    def test_missing_source_timestamp_and_hazard_scope_get_field_specific_tasks(self):
        p = one_complete()
        p["records"][0]["requested_asof"] = "invalid"
        p["records"][0]["hazard_meaning"]["reviewed_hazard"] = "landslide"
        result = queue.plan(p)
        case = result["cases"][0]["case_id"]
        self.assertEqual(
            find_task(result, case, "REQUEST_ASOF_MISSING_OR_INVALID_UTC")["required_field_paths"],
            ["requested_asof"],
        )
        self.assertEqual(
            find_task(result, case, "HAZARD_SCOPE_MISMATCH")["required_field_paths"],
            ["hazard", "hazard_meaning.reviewed_hazard"],
        )

    def test_generated_work_queue_has_only_opaque_ids_and_field_names(self):
        report = json.dumps(self.report, ensure_ascii=False)
        for forbidden in (
            "example.invalid", "fictional-source.csv", "synthetic-test-only-publisher",
            "FICTIONAL_FLOOD_MARKER", "synthetic-row:0001",
            "Synthetic sample source (not an official license)",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ):
            self.assertNotIn(forbidden, report)
        self.assertNotIn('"raw_sha256": "', report)
        self.assertNotIn('"terms_url": "', report)

    def test_task_ids_are_deterministic_unique_and_do_not_use_facility_names(self):
        all_ids = [task["task_id"] for case in self.report["cases"]
                   for task in case["tasks"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(queue.plan(self.original), self.report)
        self.assertEqual(all_ids, [task["task_id"] for case in queue.plan(self.original)["cases"]
                                   for task in case["tasks"]])

    def test_cases_do_not_mutate_operator_supplied_packet(self):
        p = fixture()
        original = copy.deepcopy(p)
        queue.plan(p)
        self.assertEqual(p, original)

    def test_unknown_reason_code_must_fail_closed_not_be_skipped(self):
        fake = {
            "records_checked": 1, "status": "HOLD__NO_REAL_DATA_ADOPTION",
            "rows": [{
                "case_id": "synthetic:somecase",
                "status": "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED",
                "reason_codes_by_area": {
                    "source": ["SOURCE_FUTURE_UNREVIEWED_GATE"],
                    "identity": [], "hazard_meaning": [], "reuse": [],
                },
            }],
        }
        with patch.object(queue.preflight, "preflight", return_value=fake):
            with self.assertRaisesRegex(queue.WorkQueueError, "unmapped"):
                queue.plan(one_complete())

    def test_invalid_packet_structure_fails_in_existing_c_preflight(self):
        p = one_complete()
        p["records"][0]["facility_safe"] = True
        with self.assertRaises(packet_check.PacketInputError):
            queue.plan(p)

    def test_conflicting_target_digest_is_not_reported_as_verified(self):
        task = find_task(self.report, "synthetic:packet-conflict",
                         "IDENTITY_TARGET_RAW_AUDIT_SHA_MISMATCH")
        self.assertEqual(task["responsible_roles"], ["C"])
        self.assertEqual(
            task["required_field_paths"],
            ["identity.target_raw_sha256", "identity.target_c_raw_audit_sha256"],
        )

    def test_cli_success_is_generation_only_and_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "synthetic.json"
            file.write_text(json.dumps(one_complete()), encoding="utf-8")
            before = set(Path(folder).iterdir())
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(queue.main(["--packet", str(file), "--json"]), 0)
            report = json.loads(out.getvalue())
            self.assertEqual(report["mandatory_authentication_task_count"], 4)
            self.assertFalse(report["eligible_for_s1_real_facilities"])
            self.assertEqual(before, set(Path(folder).iterdir()))

    def test_cli_invalid_packet_is_nonzero_and_no_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "invalid.json"
            file.write_text('{"not_schema": true}', encoding="utf-8")
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(queue.main(["--packet", str(file)]), 2)
            self.assertIn("NO_APPROVAL", out.getvalue())

    def test_cli_incomplete_packet_still_generates_open_task_queue(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(queue.main([
                "--packet", str(packet_check.DEFAULT_MANIFEST),
            ]), 0)
        self.assertIn("REVIEW_WORK_QUEUE_ONLY", out.getvalue())
        self.assertIn("open tasks", out.getvalue())


if __name__ == "__main__":
    unittest.main()
