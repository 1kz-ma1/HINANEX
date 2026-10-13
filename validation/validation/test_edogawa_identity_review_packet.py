"""Offline synthetic C tests: review packet must never approve disaster decisions."""
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from archive_edogawa_official_sources import SOURCES, capture
from build_edogawa_identity_review_packet import (
    ReviewPacketFailure, build_packet,
)
from verify_edogawa_water_join import PRIORITY_SCHOOL_REFERENCES
from test_edogawa_official_archive_content import water_page, location_csv


def make_fixture(directory, omit_institution_phone=False):
    def fetch(url):
        if url == SOURCES["municipal_locations"][1]:
            raw, content_type = location_csv(), "text/csv"
        elif url == SOURCES["water_facilities"][1]:
            raw, content_type = water_page(), "text/html"
        else:
            content = " 葛西工科高校 関東第一高校 下小岩小学校 " + " ".join(
                x["water_address"] + " " + x["water_phone"]
                for x in PRIORITY_SCHOOL_REFERENCES
            )
            if omit_institution_phone and "kanto-ichiko.ac.jp" in url:
                content = content.replace(PRIORITY_SCHOOL_REFERENCES[1]["water_phone"], "")
            raw, content_type = ("<html><body>" + content + "</body></html>").encode("utf-8"), "text/html"
        return raw, url, {"content_type": content_type}

    out = Path(directory) / "archive"
    manifest = capture(
        out, fetch=fetch,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    items = {x["source_key"]: x for x in manifest["source_items"]}
    leads = []
    for x in PRIORITY_SCHOOL_REFERENCES:
        leads.append({
            "water_number": x["official_number"],
            "water_name_raw": x["water_name"],
            "water_address_raw": x["water_address"],
            "water_floor_raw": x["water_floor_raw"],
            "d_location_id": x["expected_location_id"],
            "d_location_name_raw": x["location_name"],
            "d_original_csv_url": x["location_url"],
            "documentary_state": "CORROBORATION_LEAD_NOT_INDEPENDENTLY_ACCEPTED",
            "approved_cross_source_pair": False,
            "flood_specific_eligibility": "UNKNOWN",
        })
    leads.append({
        "documentary_state": "DISTINCT_ADDRESSES_OLD_SITE_REVIEW_REQUIRED",
        "approved_cross_source_pair": False,
        "flood_specific_eligibility": "UNKNOWN",
        "same_school_site_url_in_raw": True,
        "old_d_location_id": "edogawa-former",
        "new_d_location_id": "edogawa-current",
        "water_address_raw": "南小岩7丁目8番1号",
        "new_water_address_raw": "南小岩5丁目5番1号",
        "old_water_floor_raw": "大規模水害では使用不可",
    })
    audit = {
        "audit_status": "SOURCE_SNAPSHOT_CONSISTENCY_CHECKED_NOT_FACILITY_IDENTITY_ACCEPTED",
        "region_code": "13123",
        "c_approved_pairs": 0,
        "flood_candidates_or_exclusions_added": 0,
        "source_sha256": {
            "city_saved_water_html": items["water_facilities"]["sha256"],
            "city_local_location_csv": items["municipal_locations"]["sha256"],
        },
        "priority_identity_leads": leads,
    }
    return out, audit


class HumanReviewPacketTests(unittest.TestCase):
    def test_packet_contains_two_unapproved_cases_and_old_current_caution(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            packet = build_packet(directory, audit)
            self.assertEqual(packet["original_content_preflight_status"],
                             "ORIGINAL_CONTENT_STRUCTURE_CHECKED_HUMAN_REVIEW_REQUIRED")
            self.assertEqual(packet["status"], "REVIEW_PACKET_PREPARED_NOT_APPROVED")
            self.assertFalse(packet["c_human_reviewer_signed_off"])
            self.assertEqual(packet["approved_cross_source_pairs"], 0)
            self.assertEqual(packet["new_flood_candidates_or_exclusions"], 0)
            self.assertEqual(len(packet["priority_cases"]), 2)
            self.assertEqual(len(packet["archived_source_sha256"]), len(SOURCES))
            for item in packet["priority_cases"]:
                self.assertTrue(item["city_directory"]["raw_address_text_present"])
                self.assertTrue(item["institution_page"]["raw_phone_text_present"])
                self.assertEqual(item["flood_only_eligibility"], "UNKNOWN")
                self.assertEqual(item["cross_source_same_physical_facility"], "UNREVIEWED")
                self.assertFalse(item["c_human_reviewer_signed_off"])
            old = packet["former_current_shimokoiwa_distinct_site_caution"]
            self.assertNotEqual(old["former_address"], old["current_address"])
            self.assertTrue(old["shared_website_url_is_not_facility_identity"])

    def test_missing_official_phone_text_is_review_flag_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp, omit_institution_phone=True)
            packet = build_packet(directory, audit)
            case = packet["priority_cases"][1]
            self.assertFalse(case["institution_page"]["raw_phone_text_present"])
            self.assertFalse(packet["c_human_reviewer_signed_off"])

    def test_modified_original_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            raw = directory / SOURCES["water_facilities"][0]
            raw.write_bytes(raw.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ReviewPacketFailure, "integrity"):
                build_packet(directory, audit)

    def test_new_official_revision_requires_new_c_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            audit["source_sha256"]["city_local_location_csv"] = "0" * 64
            with self.assertRaisesRegex(ReviewPacketFailure, "regenerate D/A/C"):
                build_packet(directory, audit)

    def test_forged_c_approval_or_scenario_change_rejected(self):
        for k, v in (("c_approved_pairs", 1),
                     ("flood_candidates_or_exclusions_added", 1)):
            with self.subTest(field=k), tempfile.TemporaryDirectory() as temp:
                directory, audit = make_fixture(temp)
                audit[k] = v
                with self.assertRaisesRegex(ReviewPacketFailure, "approval"):
                    build_packet(directory, audit)

    def test_identity_claim_in_audit_lead_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            audit["priority_identity_leads"][0]["approved_cross_source_pair"] = True
            with self.assertRaisesRegex(ReviewPacketFailure, "modified"):
                build_packet(directory, audit)

    def test_shimokoiwa_legacy_site_must_stay_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            old = audit["priority_identity_leads"][2]
            old["new_water_address_raw"] = old["water_address_raw"]
            with self.assertRaisesRegex(ReviewPacketFailure, "separation"):
                build_packet(directory, audit)

    def test_html_error_page_blocks_review_even_when_digest_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            # Create a distinct archive with an HTTP-200 school error page and
            # correctly matching manifest hashes: SHA integrity alone must fail.
            old_manifest = directory / "snapshot_manifest.json"
            manifest = json.loads(old_manifest.read_text(encoding="utf-8"))
            institution_key = "kanto_ichiko_school_overview"
            item = next(x for x in manifest["source_items"]
                        if x["source_key"] == institution_key)
            raw = b"<html><body>HTTP 200 temporary error</body></html>"
            (directory / item["archive_filename"]).write_bytes(raw)
            item["byte_size"] = len(raw)
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            old_manifest.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReviewPacketFailure, "preflight failed"):
                build_packet(directory, audit)

    def test_unsupported_manifest_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, audit = make_fixture(temp)
            (directory / SOURCES["municipal_school_list"][0]).unlink()
            with self.assertRaisesRegex(ReviewPacketFailure, "integrity"):
                build_packet(directory, audit)


if __name__ == "__main__":
    unittest.main()
