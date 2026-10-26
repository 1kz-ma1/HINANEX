"""Static evidence-manifest guard: matches AI ledger, does NOT review screenshots."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reference/ichikawa_skhb02_20261026_AI_UNREVIEWED.json"
VISUAL = ROOT / "reference/ichikawa_skhb02_20261026_SCREENSHOT_VISUAL_REVIEW_UNAPPROVED.json"


class ScreenshotEvidenceMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        cls.visual = json.loads(VISUAL.read_text(encoding="utf-8"))

    def test_all_29_transcription_rows_are_covered_without_duplication(self):
        expected = {r["gsi_feature_index"]: r for r in self.ledger["rows"]}
        self.assertEqual(len(expected), 29)
        seen = {r["gsi_feature_index"]: r for r in self.visual["row_observations"]}
        self.assertEqual(len(seen), 29)
        self.assertEqual(set(seen), set(expected))
        for idx, row in seen.items():
            source = expected[idx]
            self.assertEqual(row["municipal_row_number"], source["city_row_number"])
            self.assertEqual(row["municipal_pdf_attachment"],
                             "55026" if source["city_section"] == "C" else "55017")
            self.assertEqual(row["municipal_name_address_transcription_vs_supplied_screenshot"],
                             "VISUALLY_CONSISTENT")
            self.assertEqual(row["municipal_landslide_mark_in_supplied_screenshot"], "○")
            self.assertFalse(row["facility_identity_approved"])

    def test_screenshots_are_not_authority_or_safety_evidence(self):
        v = self.visual
        self.assertEqual(v["status"], "USER_SUPPLIED_SCREENSHOT_VISUAL_REVIEW_UNAPPROVED")
        self.assertEqual(v["raw_gsi_sha256"], self.ledger["gsi_sha256"])
        self.assertEqual(v["reviewer_authority"], "NONE_NO_INDEPENDENT_HUMAN_SIGNOFF")
        for flag in ("screenshot_images_archived_in_git",
                     "original_city_pdf_bytes_and_hashes_verified",
                     "independent_human_c_approved",
                     "municipality_document_version_independently_authenticated",
                     "cross_source_facility_identity_approved",
                     "currently_open_verified", "route_safety_verified",
                     "disaster_use_approved"):
            self.assertIs(v[flag], False)
        self.assertEqual(len(v["user_supplied_screenshots"]), 5)
        for item in v["user_supplied_screenshots"]:
            self.assertEqual(len(item["sha256"]), 64)

    def test_riverside_hazard_and_address_scope_remain_unresolved(self):
        rows = self.visual["row_observations"]
        pending = [r for r in rows if r["separate_human_facility_identity_review_required"]]
        self.assertEqual([r["gsi_feature_index"] for r in pending], [571])
        self.assertEqual(
            [r["gsi_feature_index"] for r in rows
             if r["gsi_city_text_comparison"] == "NAME_AGREES_ADDRESS_SCOPE_DIFFERS"],
            [571],
        )
        hazard = self.visual["special_hazard_semantics_observation"]
        self.assertEqual(hazard["city_landslide_mark"], "○")
        self.assertEqual(hazard["city_edogawa_river_flood_mark"], "－")
        self.assertEqual(hazard["city_small_river_inland_flood_mark"], "－")
        self.assertIs(hazard["cross_source_identity_pending"], True)


if __name__ == "__main__":
    unittest.main()
