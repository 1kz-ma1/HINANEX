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
from html.parser import HTMLParser
import json
import hashlib
import math
from pathlib import Path
import re
import unicodedata

from archive_edogawa_official_sources import (
    SOURCES, SnapshotFailure, verify_snapshot,
)
from verify_edogawa_water_join import PRIORITY_SCHOOL_REFERENCES, SourceTables
from validate_edogawa_official_archive import (
    ContentPreflightFailure, validate,
)

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




def _city_school_row(raw, expected_name, water_address, water_phone):
    """Require one city's school-directory *row*, not unrelated page strings.

    Presence checks only compare source-text values within that exact row.
    They do NOT link it automatically to a D coordinate or a water facility.
    """
    parser = SourceTables()
    parser.feed(raw.decode("utf-8-sig"))
    expected_header = ("施設名称", "所在地", "電話番号")
    rows = [
        cells
        for table in parser.tables
        if table and tuple(table[0]) == expected_header
        for cells in table[1:]
        if len(cells) == 3 and _normalize(cells[0]) == _normalize(expected_name)
    ]
    if len(rows) != 1:
        raise ReviewPacketFailure(
            "Municipal school directory row absent or ambiguous: " + expected_name
        )
    name, address, phone = rows[0]
    return {
        "school_name_raw": name,
        "school_address_raw": address,
        "school_phone_raw": phone,
        "same_row_address_text_matches_water": (
            _normalize(address) == _normalize(water_address)
        ),
        "same_row_phone_text_matches_water": (
            _normalize(phone) == _normalize(water_phone)
        ),
        "match_d_location_identity_approved": False,
    }


def _phone_context_excerpt(raw, phone):
    """Keep a small raw-text local excerpt for *human* address review only.

    This never normalizes Japanese numerals/hyphens into an identity verdict.
    """
    parser = DocumentText()
    parser.feed(raw.decode("utf-8-sig"))
    visible = " ".join(parser.parts)
    normalized = unicodedata.normalize("NFKC", visible)
    start = normalized.find(phone)
    if start < 0:
        return None
    return normalized[max(0, start - 75):start + len(phone) + 35].strip()


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




def _validated_d_coordinates(export_raw, c_audit):
    """Expose official-CSV-derived D coordinates without cross-source approval."""
    hashes = c_audit.get("source_sha256", {})
    actual = hashlib.sha256(export_raw).hexdigest()
    if actual != hashes.get("old_d_region_export"):
        raise ReviewPacketFailure("D export SHA256 differs from C source audit")
    try:
        doc = json.loads(export_raw)
        if str(doc["region"]["code"]) != "13123":
            raise ValueError("wrong D region")
        datasets = [x for x in doc["datasets"]
                    if x["requirement_code"] == "shelter_location"]
        if len(datasets) != 1:
            raise ValueError("D shelter_location missing/duplicated")
        records = datasets[0]["records"]
        indexed = {x["id"]: x for x in records}
        if not records or len(indexed) != len(records):
            raise ValueError("D location IDs empty/duplicated")
        scenarios = doc["scenarios"]
        if len(scenarios) != 1 or scenarios[0]["scenario_id"] != "flood_shelter_selection":
            raise ValueError("Current D flood Scenario required")
        items = scenarios[0]["facility_results"]
        if (len(items) != len(records) or
                {x["facility_id"] for x in items} != set(indexed) or
                any(x["status"] != "UNKNOWN" or
                    x["fact"]["join_status"] != "UNVERIFIED" or
                    x["fact"]["official_status_raw"] is not None
                    for x in items)):
            raise ValueError("Unreviewed D Scenario promoted or mismatched")
        for record in records:
            lat, lon = record["latitude"], record["longitude"]
            if (type(lat) not in (int, float) or
                    type(lon) not in (int, float) or
                    not math.isfinite(lat) or not math.isfinite(lon) or
                    not -90 <= lat <= 90 or not -180 <= lon <= 180):
                raise ValueError("Invalid original D coordinates")
        return indexed, actual
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ReviewPacketFailure(
            "Current D export not suitable for independent physical site review"
        ) from exc


def build_packet(archive_dir, c_audit, d_export_raw=None):
    archive_dir = Path(archive_dir)
    try:
        content_preflight = validate(archive_dir)
    except (ContentPreflightFailure, OSError) as exc:
        raise ReviewPacketFailure(
            "Archive content/integrity preflight failed: " + str(exc)
        ) from exc
    manifest = json.loads((archive_dir / "snapshot_manifest.json").read_text("utf-8"))
    _assert_safe_audit(c_audit, manifest)
    leads = c_audit.get("priority_identity_leads")
    if not isinstance(leads, list) or len(leads) != 3:
        raise ReviewPacketFailure("C audit priority identity leads missing")
    indexed = {x.get("d_location_id"): x for x in leads if x.get("d_location_id")}
    if len(indexed) != 2:
        raise ReviewPacketFailure("Expected exactly two unique priority institution leads")
    by_key = {x["source_key"]: x for x in manifest["source_items"]}
    d_locations, d_sha256 = (
        _validated_d_coordinates(d_export_raw, c_audit)
        if d_export_raw is not None else (None, None)
    )

    city_name = "municipal_school_list"
    city_raw = (archive_dir / SOURCES[city_name][0]).read_bytes()
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
                lead.get("water_floor_raw") != reference["water_floor_raw"] or
                lead.get("d_location_name_raw") != reference["location_name"] or
                lead.get("d_original_csv_url") != reference["location_url"]):
            raise ReviewPacketFailure("Priority lead modified or missing: " + loc_id)

        page_key = ("tokyo_kasaikoka_school_access" if
                    reference["official_number"] == "108" else
                    "kanto_ichiko_school_overview")
        school_raw = (archive_dir / SOURCES[page_key][0]).read_bytes()
        text = _visible_text(school_raw)
        address = _normalize(reference["water_address"])
        phone = _normalize(reference["water_phone"])
        directory_row = _city_school_row(
            city_raw, reference["location_name"],
            reference["water_address"], reference["water_phone"],
        )
        if d_locations is not None:
            record = d_locations.get(loc_id)
            if (record is None or record.get("name") != lead["d_location_name_raw"]
                    or record.get("detail_url") != lead["d_original_csv_url"]):
                raise ReviewPacketFailure("D facility identity/URL differs from C audit")
            d_context = {
                "d_export_sha256": d_sha256,
                "latitude_from_official_location_csv": record["latitude"],
                "longitude_from_official_location_csv": record["longitude"],
                "municipal_address_in_location_csv": record.get("address"),
                "physical_same_campus_accepted": False,
                "coordinate_to_premises_independent_review_required": True,
            }
        else:
            d_context = {
                "status": "CURRENT_D_NOT_SUPPLIED",
                "coordinate_to_premises_independent_review_required": True,
            }
        cases.append({
            "water_number": reference["official_number"],
            "water_facility_name_raw": lead["water_name_raw"],
            "water_address_raw": reference["water_address"],
            "water_phone_raw": reference["water_phone"],
            "water_floor_raw": lead["water_floor_raw"],
            "d_location_id": loc_id,
            "d_location_name_raw": lead["d_location_name_raw"],
            "d_source_detail_url": lead["d_original_csv_url"],
            "d_official_location_coordinate_context": d_context,
            "city_directory": {
                "source_key": city_name,
                "source_sha256": by_key[city_name]["sha256"],
                "raw_address_text_present": directory_row["same_row_address_text_matches_water"],
                "raw_phone_text_present": directory_row["same_row_phone_text_matches_water"],
                "row_scoped_observation": directory_row,
            },
            "institution_page": {
                "source_key": page_key,
                "source_sha256": by_key[page_key]["sha256"],
                "raw_address_text_present": address in text,
                "raw_phone_text_present": phone in text,
                "phone_nearby_original_text_excerpt": _phone_context_excerpt(
                    school_raw, reference["water_phone"]
                ),
                "address_format_equivalence_reviewed": False,
            },
            "automated_result": REVIEW_ONLY,
            "cross_source_same_physical_facility": "UNREVIEWED",
            "c_human_reviewer_signed_off": False,
            "flood_only_eligibility": "UNKNOWN",
            "required_human_review": [
                "Check names, aliases, addresses, source versions and actual campus",
                "Municipal directory name, address and phone must be from the SAME exact table row",
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
            old[0].get("old_d_location_id") == old[0].get("new_d_location_id") or
            old[0].get("old_water_floor_raw") != "大規模水害では使用不可" or
            old[0].get("water_address_raw") != "南小岩7丁目8番1号" or
            old[0].get("new_water_address_raw") != "南小岩5丁目5番1号"):
        raise ReviewPacketFailure("Old/current Shimo-Koiwa site separation is not intact")

    return {
        "status": "REVIEW_PACKET_PREPARED_NOT_APPROVED",
        "original_content_preflight_status": content_preflight["status"],
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
    parser.add_argument("--d-export", type=Path, default=None)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, "Refusing to overwrite existing review packet\n")
    try:
        audit = json.loads(args.c_audit.read_text(encoding="utf-8"))
        packet = build_packet(
            args.archive_dir, audit,
            args.d_export.read_bytes() if args.d_export is not None else None,
        )
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
