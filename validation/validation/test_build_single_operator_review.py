"""Offline synthetic guards for single-owner evidence-review convenience layer."""
import copy
import unittest

from build_single_operator_review import (
    TOPICS, ReviewPacketError, make_packet, check_packet,
)


def fixtures():
    sources = []
    previews = []
    keys = [
        "water_facilities", "municipal_locations", "municipal_school_list",
        "municipal_primary_school_list", "municipal_2025_school_relocation",
        "tokyo_kasaikoka_school_access", "kanto_ichiko_school_overview",
    ]
    for i, key in enumerate(keys):
        old, new = f"{i + 1:064x}", f"{i + 11:064x}" if i == 5 else f"{i + 1:064x}"
        url = f"https://example.invalid/{key}.html"
        sources.append({"source_key": key, "requested_url": url,
                        "previous_sha256": old, "current_sha256": new,
                        "current_byte_size": 100 + i, "raw_bytes_changed": old != new})
        previews.append({"source_key": key, "source_url": url,
                         "old_sha256": old, "new_sha256": new,
                         "original_bytes": 100 + i, "changed": old != new,
                         "human_review_disposition": "PENDING",
                         "original_effective_date_verified": None,
                         "license_specific_to_this_source_verified": None})
    report = {"previous_captured_at_utc": "2026-10-14T03:14:55+00:00",
              "current_captured_at_utc": "2026-10-16T05:46:02+00:00", "sources": sources}
    receipt = {"old_artifact_sha256": "a" * 64, "new_artifact_sha256": "b" * 64,
               "pinned_git_head": "f" * 40, "old_run": 38505232094,
               "new_run": 38857462945}
    ai = {"status": "AI_PREREVIEW_UNAPPROVED", "human_approvals": 0,
          "d_source_promotion_authorized": False,
          "formal_report_sha256": "c" * 64,
          "old_archive_zip_sha256": "a" * 64,
          "new_archive_zip_sha256": "b" * 64,
          "pinned_git_head": "f" * 40,
          "snapshot_old_utc": report["previous_captured_at_utc"],
          "snapshot_new_utc": report["current_captured_at_utc"],
          "source_previews": previews,
          "critical_human_review_clusters": [
              {"decision_id": k, "issue": "原本の用途を確認する",
               "evidence": "公式根拠", "ai_finding": "原本記載と資料対応の候補",
               "restriction": "災害判定は未承認", "required_human_action": "根拠の採用範囲を限定する",
               "status": "FOLLOWUP_IF_REPUBLISHING" if k == "A-LICENSE" else "HUMAN_REVIEW_REQUIRED"}
              for k in TOPICS]}
    return report, receipt, ai


class OwnerReviewTests(unittest.TestCase):
    def setUp(self):
        self.report, self.receipt, self.ai = fixtures()
        self.packet = make_packet(self.report, self.receipt, "c" * 64, "d" * 64,
                                  self.ai, "e" * 64)

    def check(self):
        return check_packet(self.report, self.receipt, "c" * 64, "d" * 64,
                            self.ai, "e" * 64, self.packet)

    def decide(self, i=0, value="HOLD"):
        self.packet["single_operator"] = {"github_login_claimed": "owner123",
                                          "reviewed_at_utc": "2026-10-19T04:01:00Z"}
        self.packet["decisions"][i]["decision"] = value
        self.packet["decisions"][i]["reason"] = "公式出典との対応を見直す必要がある"
        if value == "ACCEPT_FACTS_ONLY":
            self.packet["decisions"][i]["reviewed_evidence_urls"] = ["https://example.invalid/source"]

    def test_template_four_pending_requires_no_reviewer(self):
        status = self.check()
        self.assertEqual(status["review_decisions"]["PENDING"], 4)
        self.assertFalse(status["human_approval_verified_by_tool"])
        self.assertFalse(status["d_source_promotion_authorized"])

    def test_one_owner_can_record_all_four_but_cannot_grant_data_authority(self):
        for i in range(4):
            self.decide(i, "ACCEPT_FACTS_ONLY")
        result = self.check()
        self.assertEqual(result["review_decisions"]["ACCEPT_FACTS_ONLY"], 4)
        self.assertFalse(result["d_source_promotion_authorized"])
        self.assertFalse(result["human_approval_verified_by_tool"])
        self.assertEqual(result["approved_cross_source_pairs"], 0)

    def test_hold_and_reject_are_documentable_without_url(self):
        self.decide(0, "REJECT")
        self.decide(1, "HOLD")
        self.assertEqual(self.check()["review_decisions"]["PENDING"], 2)

    def test_no_auto_acceptance_without_evidence_link(self):
        self.decide(0, "ACCEPT_FACTS_ONLY")
        self.packet["decisions"][0]["reviewed_evidence_urls"] = []
        with self.assertRaisesRegex(ReviewPacketError, "at least one"):
            self.check()

    def test_owner_login_is_required_for_review(self):
        self.decide()
        self.packet["single_operator"]["github_login_claimed"] = None
        with self.assertRaisesRegex(ReviewPacketError, "claimed human"):
            self.check()

    def test_fake_second_reviewer_is_rejected(self):
        self.packet["independent_second_human_reviewer_claimed"] = True
        with self.assertRaisesRegex(ReviewPacketError, "safety invariant"):
            self.check()

    def test_forged_promotion_is_rejected(self):
        self.packet["d_source_promotion_authorized"] = True
        with self.assertRaisesRegex(ReviewPacketError, "safety invariant"):
            self.check()

    def test_altered_review_question_is_rejected(self):
        self.packet["decisions"][0]["ai_proposal_unsigned"] = "すべての洪水判定は安全"
        with self.assertRaisesRegex(ReviewPacketError, "altered"):
            self.check()

    def test_ai_sha_changed_rejected(self):
        self.packet["ai_prereview_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReviewPacketError, "safety invariant"):
            self.check()

    def test_changed_source_hash_in_ai_is_rejected(self):
        self.ai["source_previews"][0]["new_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReviewPacketError, "pinned originals"):
            self.check()

    def test_approved_ai_prereview_is_rejected(self):
        self.ai["human_approvals"] = 1
        with self.assertRaisesRegex(ReviewPacketError, "human approval"):
            self.check()

    def test_timestamp_requires_utc(self):
        self.decide()
        self.packet["single_operator"]["reviewed_at_utc"] = "2026-10-19T13:01:00+09:00"
        with self.assertRaisesRegex(ReviewPacketError, "must be UTC"):
            self.check()

    def test_no_hidden_extra_approval_fields(self):
        self.packet["already_authorized"] = True
        with self.assertRaisesRegex(ReviewPacketError, "Packet shape"):
            self.check()

    def test_changed_proposal_order_rejected(self):
        self.packet["decisions"].reverse()
        with self.assertRaisesRegex(ReviewPacketError, "altered"):
            self.check()


if __name__ == "__main__":
    unittest.main()