"""C metadata-gap preflight tests: synthetic packets, never official approvals."""
from __future__ import annotations

import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

import preflight_facility_evidence_packet as c


def packet():
    return json.loads(c.DEFAULT_MANIFEST.read_text(encoding="utf-8"))


class FacilityEvidencePacketPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = packet()
        cls.results = c.preflight(cls.fixture)
        cls.rows = {x["case_id"]: x for x in cls.results["rows"]}

    def single(self):
        result = packet()
        result["records"] = [result["records"][0]]
        return result

    def test_three_cases_separate_complete_missing_conflicting(self):
        r = self.results
        self.assertEqual(r["records_checked"], 3)
        self.assertEqual(r["records_with_gaps"], 2)
        self.assertEqual(r["status"], "HOLD__NO_REAL_DATA_ADOPTION")
        self.assertEqual(self.rows["synthetic:packet-complete"]["status"],
                         "PACKET_FIELDS_PRESENT__HUMAN_AUDIT_REQUIRED")
        self.assertEqual(self.rows["synthetic:packet-incomplete"]["status"],
                         "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED")
        self.assertEqual(self.rows["synthetic:packet-conflict"]["status"],
                         "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED")

    def test_present_metadata_only_invites_human_review_never_real_use(self):
        r = c.preflight(self.single())
        self.assertEqual(r["status"], "PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED")
        self.assertEqual(r["records_with_gaps"], 0)
        self.assertFalse(r["source_original_bytes_verified_by_this_run"])
        self.assertEqual(r["identity_pairs_approved"], 0)
        for field in ("official_hazard_semantics_approved",
                      "license_and_publication_approved",
                      "eligible_for_s1_real_facilities",
                      "safe_route_verified", "facility_open_now_verified"):
            self.assertIs(r[field], False)
        self.assertIs(r["human_independent_review_required"], True)

    def test_missing_source_digest_publisher_and_version_are_separate(self):
        reasons = self.rows["synthetic:packet-incomplete"]["reason_codes_by_area"]["source"]
        for code in ("SOURCE_PUBLISHER_MISSING", "SOURCE_RAW_SHA_MISSING",
                     "SOURCE_C_BYTE_AUDIT_MISSING", "SOURCE_REVISION_MISSING"):
            self.assertIn(code, reasons)

    def test_unreviewed_cross_source_identity_is_not_accepted(self):
        reasons = self.rows["synthetic:packet-incomplete"]["reason_codes_by_area"]["identity"]
        self.assertIn("IDENTITY_INDEPENDENT_PAIR_REVIEW_MISSING", reasons)
        self.assertIn("IDENTITY_INDEPENDENT_REVIEW_UNRESOLVED", reasons)
        self.assertEqual(self.results["identity_pairs_approved"], 0)

    def test_missing_official_marker_and_meaning_review_remain_unknown(self):
        reasons = self.rows["synthetic:packet-incomplete"]["reason_codes_by_area"]["hazard_meaning"]
        self.assertIn("HAZARD_ORIGINAL_MARKER_MISSING", reasons)
        self.assertIn("HAZARD_MEANING_INDEPENDENT_REVIEW_UNRESOLVED", reasons)
        self.assertFalse(self.results["official_hazard_semantics_approved"])

    def test_unresolved_reuse_terms_and_exception_check_not_assumed_cc_by(self):
        reasons = self.rows["synthetic:packet-incomplete"]["reason_codes_by_area"]["reuse"]
        self.assertIn("REUSE_TERMS_URL_MISSING", reasons)
        self.assertIn("REUSE_EXCEPTION_CHECK_MISSING", reasons)
        self.assertIn("REUSE_INDEPENDENT_REVIEW_UNRESOLVED", reasons)
        self.assertFalse(self.results["license_and_publication_approved"])

    def test_source_raw_and_independent_audit_digest_conflict(self):
        self.assertIn("SOURCE_RAW_AUDIT_SHA_MISMATCH",
                      self.rows["synthetic:packet-conflict"]["reason_codes_by_area"]["source"])

    def test_target_source_raw_digest_conflict_is_separate(self):
        self.assertIn("IDENTITY_TARGET_RAW_AUDIT_SHA_MISMATCH",
                      self.rows["synthetic:packet-conflict"]["reason_codes_by_area"]["identity"])

    def test_stale_cross_source_pair_review_cannot_apply_to_new_raw_sha(self):
        self.assertIn("IDENTITY_SOURCE_REVISION_BINDING_MISMATCH",
                      self.rows["synthetic:packet-conflict"]["reason_codes_by_area"]["identity"])

    def test_hazard_and_license_review_binding_conflicts(self):
        problems = self.rows["synthetic:packet-conflict"]["reason_codes_by_area"]
        self.assertIn("HAZARD_MEANING_SOURCE_REVISION_BINDING_MISMATCH",
                      problems["hazard_meaning"])
        self.assertIn("REUSE_SOURCE_REVISION_BINDING_MISMATCH", problems["reuse"])
        self.assertIn("HAZARD_SCOPE_MISMATCH", problems["hazard_meaning"])

    def test_explicit_human_conflict_cannot_be_overridden_by_full_metadata(self):
        problems = self.rows["synthetic:packet-conflict"]["reason_codes_by_area"]["identity"]
        self.assertIn("IDENTITY_EVIDENCE_CONFLICT", problems)
        self.assertEqual(self.rows["synthetic:packet-conflict"]["status"],
                         "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED")

    def test_source_url_must_be_https_without_embedded_credentials(self):
        p = self.single()
        p["records"][0]["source"]["url"] = "http://example.invalid/csv"
        self.assertIn("SOURCE_URL_NOT_HTTPS",
                      c.preflight(p)["rows"][0]["reason_codes"])
        p["records"][0]["source"]["url"] = "https://user:secret@example.invalid/path"
        self.assertIn("SOURCE_URL_NOT_HTTPS",
                      c.preflight(p)["rows"][0]["reason_codes"])
        p["records"][0]["source"]["url"] = "https://example.invalid/path#fragment"
        self.assertIn("SOURCE_URL_NOT_HTTPS",
                      c.preflight(p)["rows"][0]["reason_codes"])

    def test_license_and_target_url_not_inferred_from_source_url(self):
        p = self.single()
        p["records"][0]["identity"]["target_source_url"] = "http://example.invalid/target"
        p["records"][0]["reuse"]["terms_url"] = "http://example.invalid/cc"
        row = c.preflight(p)["rows"][0]
        self.assertIn("IDENTITY_TARGET_URL_NOT_HTTPS", row["reason_codes"])
        self.assertIn("REUSE_TERMS_URL_NOT_HTTPS", row["reason_codes"])

    def test_capture_timestamp_and_asof_must_be_explicit_utc(self):
        p = self.single()
        p["records"][0]["source"]["captured_at_utc"] = "2026-11-13T00:00:00"
        p["records"][0]["identity"]["target_captured_at_utc"] = "2026-11-13T09:00:00+09:00"
        p["records"][0]["requested_asof"] = "2026-11-13"
        row = c.preflight(p)["rows"][0]
        self.assertIn("SOURCE_CAPTURE_TIME_NOT_UTC", row["reason_codes"])
        self.assertIn("REQUEST_ASOF_MISSING_OR_INVALID_UTC", row["reason_codes"])
        # +09:00 is a timezone-aware instant, but this _utc-only field rejects non-UTC.
        self.assertIn("IDENTITY_CAPTURE_TIME_NOT_UTC", row["reason_codes"])

    def test_bad_or_uppercase_digest_is_not_silently_accepted(self):
        p = self.single()
        p["records"][0]["source"]["raw_sha256"] = "A"*64
        p["records"][0]["hazard_meaning"]["bound_source_sha256"] = "bad"
        row = c.preflight(p)["rows"][0]
        self.assertIn("SOURCE_RAW_SHA256_INVALID_SHA", row["reason_codes"])
        self.assertIn("HAZARD_MEANING_BOUND_SOURCE_SHA256_INVALID_SHA", row["reason_codes"])

    def test_unknown_asof_evidence_is_missing_not_proof(self):
        p = self.single()
        p["records"][0]["asof_evidence_ref"] = "UNKNOWN"
        row = c.preflight(p)["rows"][0]
        self.assertIn("SOURCE_ASOF_EVIDENCE_MISSING", row["reason_codes"])

    def test_reuse_credit_missing_is_not_inferred_from_terms(self):
        p = self.single()
        p["records"][0]["reuse"]["attribution_text"] = None
        self.assertIn("REUSE_CREDIT_TEXT_MISSING",
                      c.preflight(p)["rows"][0]["reason_codes"])

    def test_input_with_official_approval_field_is_rejected(self):
        p = self.single()
        p["records"][0]["facility_safe"] = True
        with self.assertRaisesRegex(c.PacketInputError, "case fields"):
            c.preflight(p)
        p = self.single()
        p["records"][0]["identity"]["approved_one_to_one"] = True
        with self.assertRaisesRegex(c.PacketInputError, "identity fields"):
            c.preflight(p)

    def test_dishonest_disposition_not_allowed(self):
        p = self.single()
        p["records"][0]["hazard_meaning"]["disposition"] = "APPROVED"
        with self.assertRaisesRegex(c.PacketInputError, "disposition"):
            c.preflight(p)

    def test_null_review_disposition_is_unresolved_not_a_schema_failure(self):
        p = self.single()
        p["records"][0]["identity"]["disposition"] = None
        p["records"][0]["hazard_meaning"]["disposition"] = None
        p["records"][0]["reuse"]["disposition"] = None
        row = c.preflight(p)["rows"][0]
        self.assertEqual(row["status"], "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED")
        for code in (
            "IDENTITY_INDEPENDENT_REVIEW_UNRESOLVED",
            "HAZARD_MEANING_INDEPENDENT_REVIEW_UNRESOLVED",
            "REUSE_INDEPENDENT_REVIEW_UNRESOLVED",
        ):
            self.assertIn(code, row["reason_codes"])

    def test_duplicate_case_ids_and_empty_collection_are_rejected(self):
        p = self.single()
        p["records"].append(copy.deepcopy(p["records"][0]))
        with self.assertRaisesRegex(c.PacketInputError, "duplicate"):
            c.preflight(p)
        p["records"] = []
        with self.assertRaisesRegex(c.PacketInputError, "non-empty"):
            c.preflight(p)

    def test_malformed_schema_and_unknown_top_level_flag_rejected(self):
        p = self.single()
        p["schema_id"] = "production.safe.shelters"
        with self.assertRaisesRegex(c.PacketInputError, "schema"):
            c.preflight(p)
        p = self.single()
        p["publication_approved"] = True
        with self.assertRaisesRegex(c.PacketInputError, "schema"):
            c.preflight(p)

    def test_bad_nested_types_or_missing_keys_are_rejected(self):
        p = self.single()
        p["records"][0]["source"]["raw_sha256"] = 123
        with self.assertRaisesRegex(c.PacketInputError, "type"):
            c.preflight(p)
        p = self.single()
        del p["records"][0]["reuse"]["exception_check_ref"]
        with self.assertRaisesRegex(c.PacketInputError, "reuse fields"):
            c.preflight(p)

    def test_cli_incomplete_returns_code2_and_valid_metadata_code0(self):
        with tempfile.TemporaryDirectory() as temp:
            packet_path = Path(temp)/"packet.json"
            packet_path.write_text(json.dumps(packet()), encoding="utf-8")
            with redirect_stdout(StringIO()) as sink:
                self.assertEqual(c.main(["--packet", str(packet_path), "--json"]), 2)
            report = json.loads(sink.getvalue())
            self.assertFalse(report["eligible_for_s1_real_facilities"])
            p = self.single()
            packet_path.write_text(json.dumps(p), encoding="utf-8")
            with redirect_stdout(StringIO()) as sink:
                self.assertEqual(c.main(["--packet", str(packet_path), "--json"]), 0)
            result = json.loads(sink.getvalue())
            self.assertEqual(result["status"],
                             "PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED")
            self.assertEqual(list(Path(temp).iterdir()), [packet_path])

    def test_cli_malformed_packet_returns_code2_never_suggests_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"bad.json"
            path.write_text('{"schema_id":"invalid"}', encoding="utf-8")
            with redirect_stdout(StringIO()) as sink:
                self.assertEqual(c.main(["--packet", str(path)]), 2)
            self.assertIn("NO_APPROVAL", sink.getvalue())

    def test_report_only_contains_case_keys_and_reason_codes_not_private_metadata(self):
        report = c.preflight(self.fixture)
        s = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("synthetic-test-only-publisher", s)
        self.assertNotIn("fictional-source.csv", s)
        self.assertNotIn("synthetic-row:0001", s)
        self.assertNotIn("attribution_text", s)
        self.assertFalse(report["facility_open_now_verified"])

    def test_results_are_deterministic_and_input_not_modified(self):
        p = packet()
        before = json.dumps(p, sort_keys=True)
        a = c.preflight(p)
        b = c.preflight(p)
        self.assertEqual(a, b)
        self.assertEqual(json.dumps(p, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
