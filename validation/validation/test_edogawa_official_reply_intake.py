"""C offline regression: official reply intake must not authorize flood status."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from verify_edogawa_official_reply_intake import (
    evaluate, ReplyIntakeFailure, PURPOSE, SOURCE_REFS, OFFICES
)


def template():
    return {
        "purpose": PURPOSE, "issue_number": 141,
        "site_name": "旧下鎌田小学校",
        "site_address_raw": "東瑞江3丁目11番1号",
        "related_new_school_address_raw": "瑞江4丁目19番10号",
        "source_sha256": dict(SOURCE_REFS),
        "human_c_site_identity_approved": False,
        "human_c_hazard_semantics_approved": False,
        "human_c_current_opening_approved": False,
        "new_flood_classifications": 0,
        "outreach_was_automatically_sent": False,
        "office_requests": [
            {
                "office_id": key,
                "office_name": value["name"],
                "phone": value["phone"],
                "public_reference_url": value["public_reference_url"],
                "state": "NOT_CONTACTED",
                "contacted_at_utc": None,
                "response_evidence": None,
            }
            for key, value in OFFICES.items()
        ],
    }


def put_response(folder, data, role="disaster_plan", channel="email"):
    item = next(x for x in data["office_requests"] if x["office_id"] == role)
    content = "公式窓口への照会に対する人間C未承認の返信原文".encode("utf-8")
    filename = "original_municipal_reply.txt"
    (folder / filename).write_bytes(content)
    item["state"] = "REPLY_ARCHIVED_UNREVIEWED"
    item["contacted_at_utc"] = "2026-10-13T09:00:00+00:00"
    item["response_evidence"] = {
        "original_filename": filename,
        "sha256": sha256(content).hexdigest(),
        "received_at_utc": "2026-10-13T10:00:00+00:00",
        "claimed_office_name": OFFICES[role]["name"],
        "response_channel": channel,
        "independent_c_authenticity_confirmed": False,
        "human_c_signed_review": False,
    }
    if channel == "telephone_memo":
        item["response_evidence"]["memo_is_not_a_signed_municipal_document"] = True
    return item


class OriginalAuthorityResponseTests(unittest.TestCase):
    def test_repository_unsent_inquiry_template_is_valid(self):
        template_path = Path(__file__).resolve().parents[1] / "reviews" / (
            "2026-10-13-old-shimokamata-inquiry-packet.json"
        )
        with TemporaryDirectory() as tmp:
            stored = json.loads(template_path.read_text(encoding="utf-8"))
            result = evaluate(stored, Path(tmp))
            self.assertEqual(
                result["status"], "C_AWAITING_AUTHORITY_CONFIRMATION_NO_SITE_DECISION"
            )
            self.assertTrue(all(x == "NOT_CONTACTED" for x in result["office_states"].values()))
            self.assertEqual(result["archived_original_receipts"], [])

    def test_absent_response_does_not_assert_status(self):
        with TemporaryDirectory() as tmp:
            r = evaluate(template(), Path(tmp))
            self.assertEqual(r["status"], "C_AWAITING_AUTHORITY_CONFIRMATION_NO_SITE_DECISION")
            self.assertEqual(len(r["archived_original_receipts"]), 0)
            self.assertEqual(r["human_c_approved_site_pairs"], 0)
            self.assertEqual(r["new_flood_candidates_or_exclusions"], 0)
            self.assertEqual(r["real_time_standby_open_status"], "UNKNOWN")

    def test_answer_arrival_is_not_signed_site_safety(self):
        with TemporaryDirectory() as tmp:
            data = template()
            put_response(Path(tmp), data)
            r = evaluate(data, Path(tmp))
            self.assertEqual(r["status"], "C_ORIGINAL_REPLIES_PRESENT_HUMAN_REVIEW_REQUIRED")
            self.assertEqual(len(r["archived_original_receipts"]), 1)
            self.assertTrue(r["archived_original_receipts"][0]["content_not_interpreted_by_intake"])
            self.assertEqual(r["official_site_standby_designation_current"], "UNKNOWN")
            self.assertEqual(r["old_buildings_physical_condition"], "UNKNOWN")
            self.assertFalse(r["physical_old_new_campus_cross_join_approved"])

    def test_tampered_reply_original_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            put_response(Path(tmp), data)
            (Path(tmp) / "original_municipal_reply.txt").write_bytes(b"tampered")
            with self.assertRaisesRegex(ReplyIntakeFailure, "SHA256"):
                evaluate(data, Path(tmp))

    def test_false_c_human_signoff_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["human_c_site_identity_approved"] = True
            with self.assertRaisesRegex(ReplyIntakeFailure, "approval"):
                evaluate(data, Path(tmp))

    def test_fake_opening_approval_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["human_c_current_opening_approved"] = True
            with self.assertRaisesRegex(ReplyIntakeFailure, "approval"):
                evaluate(data, Path(tmp))

    def test_flood_status_promotion_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["new_flood_classifications"] = 1
            with self.assertRaisesRegex(ReplyIntakeFailure, "approval"):
                evaluate(data, Path(tmp))

    def test_unsigned_reply_cannot_pretend_official_authenticity(self):
        with TemporaryDirectory() as tmp:
            data = template()
            item = put_response(Path(tmp), data)
            item["response_evidence"]["independent_c_authenticity_confirmed"] = True
            with self.assertRaisesRegex(ReplyIntakeFailure, "self-approve"):
                evaluate(data, Path(tmp))

    def test_telephone_memo_not_signed_document(self):
        with TemporaryDirectory() as tmp:
            data = template()
            item = put_response(Path(tmp), data, channel="telephone_memo")
            del item["response_evidence"]["memo_is_not_a_signed_municipal_document"]
            with self.assertRaisesRegex(ReplyIntakeFailure, "signed official document"):
                evaluate(data, Path(tmp))

    def test_reply_path_traversal_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            item = put_response(Path(tmp), data)
            item["response_evidence"]["original_filename"] = "../outside.txt"
            with self.assertRaisesRegex(ReplyIntakeFailure, "path may not traverse"):
                evaluate(data, Path(tmp))

    def test_one_archived_reply_must_not_count_for_both_offices(self):
        with TemporaryDirectory() as tmp:
            data = template()
            put_response(Path(tmp), data, role="disaster_plan")
            put_response(Path(tmp), data, role="property_use")
            with self.assertRaisesRegex(ReplyIntakeFailure, "cannot substitute"):
                evaluate(data, Path(tmp))

    def test_duplicate_agency_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["office_requests"][1] = deepcopy(data["office_requests"][0])
            with self.assertRaisesRegex(ReplyIntakeFailure, "unknown/duplicate"):
                evaluate(data, Path(tmp))

    def test_source_sha_rewrite_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["source_sha256"]["2026_demolition_vote_html"] = "a"*64
            with self.assertRaisesRegex(ReplyIntakeFailure, "Evidence revisions"):
                evaluate(data, Path(tmp))

    def test_new_school_address_in_old_site_case_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["site_address_raw"] = "瑞江4丁目19番10号"
            with self.assertRaisesRegex(ReplyIntakeFailure, "specific physical campus"):
                evaluate(data, Path(tmp))

    def test_contact_not_sent_cannot_have_synthetic_reply(self):
        with TemporaryDirectory() as tmp:
            data = template()
            data["office_requests"][0]["contacted_at_utc"] = "2026-10-13T09:00:00+00:00"
            with self.assertRaisesRegex(ReplyIntakeFailure, "No contact"):
                evaluate(data, Path(tmp))

    def test_future_reply_before_contact_rejected(self):
        with TemporaryDirectory() as tmp:
            data = template()
            item = put_response(Path(tmp), data)
            item["response_evidence"]["received_at_utc"] = "2026-10-13T08:00:00Z"
            with self.assertRaisesRegex(ReplyIntakeFailure, "cannot precede"):
                evaluate(data, Path(tmp))


if __name__ == "__main__":
    unittest.main()
