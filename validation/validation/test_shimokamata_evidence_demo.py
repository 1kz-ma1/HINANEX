"""Synthetic C educational-source export regression; never creates shelter results."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_shimokamata_evidence_demo import (
    DEMO_STATUS, REQUIRED_SOURCE_KEYS, build_evidence_demo,
)
from build_shimokamata_review_readiness import make_matrix
from verify_edogawa_official_reply_intake import ReplyIntakeFailure
from test_edogawa_official_reply_intake import template, put_response
from test_shimokamata_review_readiness import two_different_claimed_office_replies


class SchoolEvidenceDemoTests(unittest.TestCase):
    def _build(self, folder, packet=None):
        packet = template() if packet is None else packet
        return build_evidence_demo(make_matrix(packet, Path(folder)))

    def test_three_demo_states_from_current_unsent_source_packet(self):
        source = (Path(__file__).resolve().parents[1] / "reviews"
                  / "2026-10-13-old-shimokamata-inquiry-packet.json")
        with TemporaryDirectory() as root:
            result = self._build(root, json.loads(source.read_text(encoding="utf-8")))
        self.assertEqual(result["status"], DEMO_STATUS)
        self.assertEqual(
            [x["key"] for x in result["demo_states"]],
            ["DOCUMENTARY_FACT", "SOURCE_VERSION_RECONCILIATION",
             "CURRENT_OPERATIONS_UNKNOWN"],
        )
        self.assertTrue(result["presentation_only"])
        self.assertFalse(result["may_be_used_as_live_shelter_recommendation"])
        self.assertEqual(result["human_C_site_pairs_approved"], 0)
        self.assertEqual(result["new_flood_candidate_or_excluded"], 0)
        self.assertEqual(result["demo_states"][-1]["current_operational_status"], "UNKNOWN")
        self.assertEqual(set(result["source_documents"]), set(REQUIRED_SOURCE_KEYS))
        self.assertTrue(all(not src["original_bytes_reverified_by_this_public_export"]
                            for src in result["source_documents"].values()))

    def test_emits_dated_originals_without_merging_old_and_new_school(self):
        with TemporaryDirectory() as root:
            result = self._build(root)
        school = result["target_case"]
        self.assertEqual(school["site_address_raw"], "東瑞江3丁目11番1号")
        self.assertEqual(school["separate_current_school_address_raw"], "瑞江4丁目19番10号")
        self.assertEqual(school["new_school_plan_raw_address_2026"], "瑞江4-19-1")
        self.assertFalse(school["old_new_premises_human_link_approved"])
        self.assertEqual(result["source_documents"]["2026_external_internal_plan_pdf"]
                         ["document_date_scope"], "2026-04-01")
        self.assertEqual(result["source_documents"]["2026_demolition_vote_html"]
                         ["document_date_scope"], "2026-07-01")
        self.assertTrue(result["not_reenacted_historical_disaster_or_predictive_accuracy_result"])

    def test_claimed_both_offices_cannot_transform_unknown_into_approved(self):
        with TemporaryDirectory() as root:
            p = template()
            two_different_claimed_office_replies(root, p)
            result = self._build(root, p)
        self.assertEqual(result["status"], DEMO_STATUS)
        self.assertFalse(result["current_site_safety_or_opening_claim"])
        self.assertEqual(result["new_flood_candidate_or_excluded"], 0)
        self.assertEqual(result["demo_states"][-1]["current_operational_status"], "UNKNOWN")

    def test_privacy_even_if_private_original_contains_unique_contact_identifier(self):
        with TemporaryDirectory() as root:
            p = template()
            item = put_response(Path(root), p, role="disaster_plan")
            file = Path(root) / item["response_evidence"]["original_filename"]
            secret = "HUMAN-PRIVATE-DO-NOT-PUBLISH-ABCDEFG"
            file.write_text(secret, encoding="utf-8")
            from hashlib import sha256
            item["response_evidence"]["sha256"] = sha256(file.read_bytes()).hexdigest()
            packet = self._build(root, p)
        rendered = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("original_municipal_reply.txt", rendered)
        self.assertNotIn(item["response_evidence"]["sha256"], rendered)
        self.assertNotIn("claimed_original_reply_digest_by_office", rendered)
        self.assertNotIn("03-5662-", rendered)

    def test_wrong_c_known_original_revision_rejected(self):
        with TemporaryDirectory() as root:
            packet = template()
            evidence = make_matrix(packet, Path(root))
            evidence["source_revisions"]["2026_demolition_vote_html"] = "0"*64
            with self.assertRaisesRegex(ValueError, "Pinned official original"):
                build_evidence_demo(evidence)

    def test_false_review_signature_rejected(self):
        with TemporaryDirectory() as root:
            record = make_matrix(template(), Path(root))
        for name, fake in (
            ("reviewer_identity", "Fake validator"),
            ("review_signature", "claimed approval"),
            ("reviewed_at_utc", "2026-10-13T00:00:00Z"),
            ("C_human_site_review_signed", True),
            ("D_export_modification_authorized", True),
        ):
            with self.subTest(field=name):
                altered = deepcopy(record)
                altered[name] = fake
                with self.assertRaises(ValueError):
                    build_evidence_demo(altered)

    def test_live_or_false_operational_result_fails_closed(self):
        with TemporaryDirectory() as root:
            valid = make_matrix(template(), Path(root))
        cases = (
            ("old_site_open_now", "OPEN"),
            ("old_site_external_standby_status", "CANDIDATE"),
            ("old_site_current_physical_condition", "DEMOLISHED"),
            ("new_D_flood_candidate_or_excluded", 1),
            ("same_physical_old_new_campus_approved", True),
        )
        for name, value in cases:
            with self.subTest(field=name):
                clone = deepcopy(valid)
                clone[name] = value
                with self.assertRaises(ValueError):
                    build_evidence_demo(clone)

    def test_one_evidence_track_false_human_signoff_rejected(self):
        with TemporaryDirectory() as root:
            record = make_matrix(template(), Path(root))
        record["evidence_tracks"]["water_standby_internal_flood"]["human_C_signed"] = True
        with self.assertRaisesRegex(ValueError, "Unsigned C evidence track"):
            build_evidence_demo(record)

    def test_missing_or_fabricated_review_track_rejected(self):
        with TemporaryDirectory() as root:
            record = make_matrix(template(), Path(root))
        del record["evidence_tracks"]["old_campus_structure_and_access"]
        with self.assertRaisesRegex(ValueError, "Missing or unexpected"):
            build_evidence_demo(record)

    def test_bad_source_packet_and_tampered_raw_reply_rejected(self):
        with TemporaryDirectory() as root:
            packet = template()
            packet["human_c_site_identity_approved"] = True
            with self.assertRaisesRegex(ReplyIntakeFailure, "approval"):
                self._build(root, packet)
            packet = template()
            item = put_response(Path(root), packet, role="property_use")
            (Path(root)/item["response_evidence"]["original_filename"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ReplyIntakeFailure, "SHA256"):
                self._build(root, packet)


if __name__ == "__main__":
    unittest.main()
