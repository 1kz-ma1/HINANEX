"""Build C's NON-APPROVED source-specific human review packet.

Requires a completed seven-source byte archive and C's independent audit
against exactly the same municipal water HTML and municipal location CSV.
No facility pair or flood-only designation is approved by this script.

Run after archive --verify-dir and verify_edogawa_water_join.py:
  python validation/validation/build_edogawa_identity_review_packet.py \
    --archive-dir /outside-git/official-YYYYMMDD \
    --c-audit /outside-git/c_snapshot_audit.json \
    --output /outside-git/c_priority_review_packet.json
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata

from archive_edogawa_official_sources import (
    SOURCES, SnapshotFailure, verify_snapshot,
)
from verify_edogawa_water_join import PRIORITY_SCHOOL_REFERENCES

AUDIT_STATUS = "SOURCE_SNAPSHOT_CONSISTENCY_CHECKED_NOT_FACILITY_IDENTITY_ACCEPTED"
REVIEW_ONLY = "DOCUMENTARY_PRESENCE_CHECK_NOT_IDENTITY_ACCEPTANCE"


class ReviewPacketFailure(ValueError):
    pass


class DocumentText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skipped += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skipped:
            self.skipped -= 1

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def _visible_text(raw):
    # Source text presence is NOT a proof that it belongs to a given site.
    parser = DocumentText()
    parser.feed(raw.decode("utf-8-sig", errors="replace"))
    return _normalize(" ".join(parser.parts))


def _normalize(value):
    text = unicodedata.normalize("NFKC", value)
    return re.sub(r"[\s\u3000]+", "", text)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _assert_safe_audit(audit, manifest):
    if not isinstance(audit, dict) or audit.get("audit_status") != AUDIT_STATUS:
        raise ReviewPacketFailure("C audit missing or not a snapshot consistency audit")
    if (audit.get("c_approved_pairs") != 0 or
            audit.get("flood_candidates_or_exclusions_added") != 0 or
            audit.get("region_code") != "13123"):
        raise ReviewPacketFailure("C audit contains approval, classification or wrong region")
    hashes = audit.get("source_sha256")
    if not isinstance(hashes, dict):
        raise ReviewPacketFailure("C audit source digests missing")
    items = {x["source_key"]: x for x in manifest["source_items"]}
    for source_key, audit_key in (
        ("water_facilities", "city_saved_water_html"),
        ("municipal_locations", "city_local_location_csv"),
    ):
        if items[source_key]["sha256"] != hashes.get(audit_key):
            raise ReviewPacketFailure(
                "Official source revision differs from C audit; regenerate D/A/C before review: "
                + source_key
            )


def build_packet(archive_dir, c_audit):
    archive_dir = Path(archive_dir)
    try:
        verify_snapshot(archive_dir)
    except (SnapshotFailure, OSError) as exc:
        raise ReviewPacketFailure("Archive byte integrity gate failed: " + str(exc)) from exc
    manifest = json.loads((archive_dir / "snapshot_manifest.json").read_text("utf-8"))
    _assert_safe_audit(c_audit, manifest)
    leads = c_audit.get("priority_identity_leads")
    if not isinstance(leads, list):
        raise ReviewPacketFailure("C audit priority identity leads missing")
    indexed = {x.get("d_location_id"): x for x in leads if x.get("d_location_id")}
    if len(indexed) != 2:
        raise ReviewPacketFailure("Expected exactly two unique priority institution leads")
    by_key = {x["source_key"]: x for x in manifest["source_items"]}

    city_name = "municipal_school_list"
    city_text = _visible_text((archive_dir / SOURCES[city_name][0]).read_bytes())
    cases = []
    for reference in PRIORITY_SCHOOL_REFERENCES:
        loc_id = reference["expected_location_id"]
        lead = indexed.get(loc_id)
        if (not isinstance(lead, dict) or
                lead.get("approved_cross_source_pair") is not False or
                lead.get("flood_specific_eligibility") != "UNKNOWN" or
                lead.get("documentary_state") !=
                "CORROBORATION_LEAD_NOT_INDEPENDENTLY_ACCEPTED" or
                lead.get("water_number") != reference["official_number"] or
                lead.get("water_name_raw") != reference["water_name"] or
                lead.get("water_address_raw") != reference["water_address"] or
                lead.get("d_location_name_raw") != reference["location_name"] or
                lead.get("d_original_csv_url") != reference["location_url"]):
            raise ReviewPacketFailure("Priority lead modified or missing: " + loc_id)

        page_key = ("tokyo_kasaikoka_school_access" if
                    reference["official_number"] == "108" else
                    "kanto_ichiko_school_overview")
        text = _visible_text((archive_dir / SOURCES[page_key][0]).read_bytes())
        address = _normalize(reference["water_address"])
        phone = _normalize(reference["water_phone"])
        cases.append({
            "water_number": reference["official_number"],
            "water_facility_name_raw": lead["water_name_raw"],
            "water_address_raw": reference["water_address"],
            "water_phone_raw": reference["water_phone"],
            "water_floor_raw": lead["water_floor_raw"],
            "d_location_id": loc_id,
            "d_location_name_raw": lead["d_location_name_raw"],
            "d_source_detail_url": lead["d_original_csv_url"],
            "city_directory": {
                "source_key": city_name,
                "source_sha256": by_key[city_name]["sha256"],
                "raw_address_text_present": address in city_text,
                "raw_phone_text_present": phone in city_text,
            },
            "institution_page": {
                "source_key": page_key,
                "source_sha256": by_key[page_key]["sha256"],
                "raw_address_text_present": address in text,
                "raw_phone_text_present": phone in text,
            },
            "automated_result": REVIEW_ONLY,
            "cross_source_same_physical_facility": "UNREVIEWED",
            "c_human_reviewer_signed_off": False,
            "flood_only_eligibility": "UNKNOWN",
            "required_human_review": [
                "Check names, aliases, addresses, source versions and actual campus",
                "Independently associate exact D CSV record/coordinates with campus",
                "Review missing text as formatting/change; present text alone proves no identity",
                "Confirm official facility and document context dates",
                "Keep water-standby versus flood-only semantics as a separate D/C gate",
            ],
        })
    old = [x for x in leads if x.get("documentary_state") ==
           "DISTINCT_ADDRESSES_OLD_SITE_REVIEW_REQUIRED"]
    if (len(old) != 1 or old[0].get("approved_cross_source_pair") is not False or
            old[0].get("flood_specific_eligibility") != "UNKNOWN" or
            old[0].get("same_school_site_url_in_raw") is not True or
            old[0].get("water_address_raw") == old[0].get("new_water_address_raw")):
        raise ReviewPacketFailure("Old/current Shimo-Koiwa site separation is not intact")

    return {
        "status": "REVIEW_PACKET_PREPARED_NOT_APPROVED",
        "archive_captured_at_utc": manifest["captured_at_utc"],
        "archived_source_sha256": {
            key: by_key[key]["sha256"] for key in SOURCES
        },
        "c_original_source_audit_status": c_audit["audit_status"],
        "priority_cases": cases,
        "former_current_shimokoiwa_distinct_site_caution": {
            "old_d_location_id": old[0]["old_d_location_id"],
            "current_d_location_id": old[0]["new_d_location_id"],
            "former_address": old[0]["water_address_raw"],
            "current_address": old[0]["new_water_address_raw"],
            "shared_website_url_is_not_facility_identity": True,
            "old_water_floor_raw": old[0]["old_water_floor_raw"],
            "flood_only_eligibility": "UNKNOWN",
        },
        "independent_publisher_authenticity_attested": False,
        "c_human_reviewer_signed_off": False,
        "approved_cross_source_pairs": 0,
        "new_flood_candidates_or_exclusions": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--c-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, "Refusing to overwrite existing review packet\n")
    try:
        audit = json.loads(args.c_audit.read_text(encoding="utf-8"))
        packet = build_packet(args.archive_dir, audit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, ReviewPacketFailure) as exc:
        parser.exit(2, "Review packet not prepared: " + str(exc) + "\n")
    print(json.dumps({
        "status": packet["status"],
        "priority_cases": len(packet["priority_cases"]),
        "approved_cross_source_pairs": 0,
        "new_flood_candidates_or_exclusions": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
