"""Synthetic negative C tests for official school relocation-version archive."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from verify_edogawa_campus_history import (
    EXPECTED, CSchoolHistoryFailure, review
)


def make(root):
    folder = Path(root) / "campus"
    folder.mkdir()
    items = []
    for key, (filename, url, markers) in EXPECTED.items():
        if filename.endswith(".pdf"):
            data = b"%PDF-1.5\n" + b"% sampled historical test PDF\n" * 10 + b"%%EOF\n"
            kind = "pdf"
        else:
            data = ("<html><body>" + " 。 ".join(markers) +
                    "</body></html>").encode("utf-8")
            kind = "html"
        (folder / filename).write_bytes(data)
        items.append({
            "source_key": key, "archive_filename": filename,
            "requested_url": url, "final_url": url,
            "document_format": kind, "byte_size": len(data),
            "sha256": sha256(data).hexdigest(),
            "reported_page_update_date_not_equivalent_to_effective_date": True,
        })
    manifest = {
        "purpose": "A_EDOGAWA_CAMPUS_TIMELINE_ORIGINAL_BYTES_UNAPPROVED",
        "captured_at_utc": datetime(2026, 10, 13, tzinfo=timezone.utc).isoformat(),
        "official_publication_and_effective_dates_human_reviewed": False,
        "pdf_campus_map_and_meeting_context_human_review_required": True,
        "school_campus_identity_human_approved": False,
        "school_campus_effective_date_human_approved": False,
        "water_facility_site_link_human_approved": False,
        "flood_only_semantics_human_approved": False,
        "approved_cross_source_pairs": 0,
        "flood_scenario_classifications_added": 0,
        "source_items": items,
    }
    (folder / "campus_history_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return folder, manifest


def rewrite(folder, manifest):
    (folder / "campus_history_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )


class CSchoolHistoryArchiveTests(unittest.TestCase):
    def test_complete_source_provenance_is_not_a_site_signoff(self):
        with TemporaryDirectory() as root:
            folder, _ = make(root)
            report = review(folder)
            self.assertEqual(report["official_source_originals_verified"], 7)
            self.assertEqual(report["historical_pdf_originals_byte_structure_checked"], 2)
            self.assertFalse(report["pdf_campus_map_page_content_independently_reviewed"])
            self.assertEqual(report["c_human_site_pairs_approved"], 0)
            self.assertEqual(report["new_flood_eligible_or_excluded"], 0)
            self.assertCountEqual(
                report["school_cases_for_future_human_review"],
                ("平井南小学校", "下鎌田小学校", "瑞江小学校", "三葛西小学校"),
            )
            self.assertFalse(
                report["school_cases_for_future_human_review"]["下鎌田小学校"]
                ["c_human_same_physical_site_approved"]
            )

    def test_one_modified_original_refused(self):
        with TemporaryDirectory() as root:
            folder, _ = make(root)
            p = folder / "hirai_minami_rebuild.html"
            p.write_bytes(p.read_bytes() + b"unknown")
            with self.assertRaisesRegex(CSchoolHistoryFailure, "SHA256 discrepancy"):
                review(folder)

    def test_false_signed_off_date_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            manifest["school_campus_effective_date_human_approved"] = True
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "unsupported approval"):
                review(folder)

    def test_false_flood_decision_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            manifest["flood_scenario_classifications_added"] = 1
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "unsupported approval"):
                review(folder)

    def test_malicious_redirect_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            manifest["source_items"][2]["final_url"] = "https://example.org/other"
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "publisher not official"):
                review(folder)

    def test_duplicate_official_sources_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            manifest["source_items"][2]["source_key"] = manifest["source_items"][0]["source_key"]
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "duplicated"):
                review(folder)

    def test_forged_pdf_bad_magic_with_updated_sha_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            pdf = folder / "shimokamata_2021_campus_plan.pdf"
            raw = b"<html>" + b"x"*180 + b"</html>"
            pdf.write_bytes(raw)
            for item in manifest["source_items"]:
                if item["source_key"] == "historical_shimokamata_site_plan_2021":
                    item["byte_size"] = len(raw)
                    item["sha256"] = sha256(raw).hexdigest()
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "PDF structure"):
                review(folder)

    def test_missing_historical_pdf_does_not_pass(self):
        with TemporaryDirectory() as root:
            folder, _ = make(root)
            (folder / "hirai_2024_school_board_minutes.pdf").unlink()
            with self.assertRaisesRegex(CSchoolHistoryFailure, "missing/excess"):
                review(folder)

    def test_false_school_label_from_official_HTML_with_updated_sha_refused(self):
        with TemporaryDirectory() as root:
            folder, manifest = make(root)
            name = "school_district_2025.html"
            raw = b"<html><body>Not the intended official school document</body></html>"
            p = folder / name
            p.write_bytes(raw)
            for item in manifest["source_items"]:
                if item["archive_filename"] == name:
                    item["byte_size"] = len(raw)
                    item["sha256"] = sha256(raw).hexdigest()
            rewrite(folder, manifest)
            with self.assertRaisesRegex(CSchoolHistoryFailure, "expected date/campus"):
                review(folder)


if __name__ == "__main__":
    unittest.main()
