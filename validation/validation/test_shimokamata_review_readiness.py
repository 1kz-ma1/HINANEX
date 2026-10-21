"""C review-readiness gate remains human-only regardless of received reply count."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from build_shimokamata_review_readiness import (
    make_matrix, INDEPENDENT, LIVE, NOT_RECEIVED, OUTPUT_STATUS,
)
from verify_edogawa_official_reply_intake import ReplyIntakeFailure
from test_edogawa_official_reply_intake import template, put_response


def two_different_claimed_office_replies(folder, packet):
    """Synthetic messages are NOT authentic replies or human signoff."""
    p = Path(folder)
    put_response(p, packet, role="disaster_plan")
    first = p / "original_municipal_reply.txt"
    first.rename(p / "claimed_disaster_reply.txt")
    packet["office_requests"][0]["response_evidence"]["original_filename"] = (
        "claimed_disaster_reply.txt"
    )
    put_response(p, packet, role="property_use")
    packet["office_requests"][1]["response_evidence"]["original_filename"] = (
        "original_municipal_reply.txt"
    )


class ShimokamataReadinessTests(unittest.TestCase):
    def test_unsent_repository_packet_all_gates_blocked(self):
        root = Path(__file__).resolve().parents[1]
        official_template = json.loads(
            (root / "reviews" / "2026-10-13-old-shimokamata-inquiry-packet.json")
            .read_text(encoding="utf-8")
        )
        with TemporaryDirectory() as d:
            report = make_matrix(official_template, Path(d))
            self.assertEqual(report["status"], OUTPUT_STATUS)
            for key in ("water_standby_external_flood",
                        "water_standby_internal_flood",
                        "old_campus_structure_and_access",
                        "same_physical_site_and_time"):
                self.assertEqual(report["evidence_tracks"][key]["state"], NOT_RECEIVED)
            self.assertEqual(report["evidence_tracks"]["real_time_opening"]["state"], LIVE)
            self.assertEqual(report["old_site_open_now"], "UNKNOWN")
            self.assertEqual(report["old_site_external_standby_status"], "UNKNOWN")
            self.assertFalse(report["D_export_modification_authorized"])
            self.assertFalse(report["D_region_export_read_or_mutated"])
            self.assertTrue(report["D_existing_152_scenario_statuses_not_reverified_by_this_tool"])

    def test_one_claimed_disaster_reply_does_not_satisfy_property_site_review(self):
        with TemporaryDirectory() as d:
            packet = template()
            put_response(Path(d), packet, role="disaster_plan")
            result = make_matrix(packet, Path(d))
            self.assertEqual(result["evidence_tracks"]["water_standby_external_flood"]["state"],
                             INDEPENDENT)
            self.assertEqual(result["evidence_tracks"]["old_campus_structure_and_access"]["state"],
                             NOT_RECEIVED)
            self.assertEqual(result["evidence_tracks"]["same_physical_site_and_time"]["state"],
                             NOT_RECEIVED)
            self.assertEqual(result["C_human_site_review_signed"], False)
            self.assertEqual(result["new_D_flood_candidate_or_excluded"], 0)

    def test_two_claimed_official_replies_still_require_independent_human_review(self):
        with TemporaryDirectory() as d:
            packet = template()
            two_different_claimed_office_replies(d, packet)
            r = make_matrix(packet, Path(d))
            for key in ("water_standby_external_flood",
                        "water_standby_internal_flood",
                        "old_campus_structure_and_access",
                        "same_physical_site_and_time"):
                self.assertEqual(r["evidence_tracks"][key]["state"], INDEPENDENT)
                self.assertFalse(r["evidence_tracks"][key]["human_C_signed"])
            self.assertEqual(r["evidence_tracks"]["real_time_opening"]["state"], LIVE)
            self.assertIsNone(r["review_signature"])
            self.assertIsNone(r["reviewer_identity"])
            self.assertFalse(r["same_physical_old_new_campus_approved"])
            self.assertEqual(r["old_site_internal_standby_status"], "UNKNOWN")
            self.assertEqual(r["new_D_flood_candidate_or_excluded"], 0)
            self.assertEqual(set(r["claimed_original_reply_digest_by_office"]),
                             {"disaster_plan", "property_use"})

    def test_no_private_original_reply_contents_in_readiness_matrix(self):
        with TemporaryDirectory() as d:
            packet = template()
            two_different_claimed_office_replies(d, packet)
            r = make_matrix(packet, Path(d))
            content = json.dumps(r, ensure_ascii=False)
            self.assertNotIn("公式窓口への照会に対する人間C未承認の返信原文", content)
            self.assertNotIn("claimed_disaster_reply.txt", content)
            self.assertNotIn("original_municipal_reply.txt", content)

    def test_inquiry_marked_contacted_but_not_answered_yields_no_evidence(self):
        with TemporaryDirectory() as d:
            packet = template()
            packet["office_requests"][1]["state"] = "CONTACTED_AWAITING_REPLY"
            packet["office_requests"][1]["contacted_at_utc"] = "2026-10-13T08:00:00Z"
            r = make_matrix(packet, Path(d))
            self.assertEqual(
                r["evidence_tracks"]["old_campus_structure_and_access"]["state"], NOT_RECEIVED
            )

    def test_underlying_authentication_and_source_hash_fail_closed(self):
        with TemporaryDirectory() as d:
            packet = template()
            packet["human_c_hazard_semantics_approved"] = True
            with self.assertRaisesRegex(ReplyIntakeFailure, "approval"):
                make_matrix(packet, Path(d))

    def test_tampered_original_never_yields_evidence_matrix(self):
        with TemporaryDirectory() as d:
            packet = template()
            put_response(Path(d), packet)
            (Path(d) / "original_municipal_reply.txt").write_text("altered")
            with self.assertRaisesRegex(ReplyIntakeFailure, "SHA256"):
                make_matrix(packet, Path(d))

    def test_two_offices_must_not_reuse_one_original_reply(self):
        with TemporaryDirectory() as d:
            packet = template()
            put_response(Path(d), packet, role="disaster_plan")
            put_response(Path(d), packet, role="property_use")
            with self.assertRaisesRegex(ReplyIntakeFailure, "cannot substitute"):
                make_matrix(packet, Path(d))


if __name__ == "__main__":
    unittest.main()
