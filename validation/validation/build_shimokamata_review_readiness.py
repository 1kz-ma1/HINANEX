"""C: Build a NON-AUTHORIZING decision-readiness matrix from original reply intake.

The incoming emails/letters/telephone memoranda are untrusted claimed replies.
Receipt integrity != municipal authenticity != human C site verification !=
flood suitability != live opening. This module can NEVER emit an approved,
eligible, excluded, open or closed site, even with all original reply files.

This consumes the existing C packet+original SHA validator, never D/RegionExport.

python validation/validation/build_shimokamata_review_readiness.py \
  --packet validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json \
  --original-dir /private/authority-originals \
  --out /private/decision_readiness_UNAPPROVED.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from verify_edogawa_official_reply_intake import (
    OFFICES, SOURCE_REFS, evaluate as verify_reply_intake,
)

OUTPUT_STATUS = "C_HUMAN_SITE_AND_HAZARD_REVIEW_REQUIRED_NO_DECISION"
NOT_RECEIVED = "AUTHORITY_REPLY_NOT_ARCHIVED"
PRESENT = "CLAIMED_AUTHORITY_REPLY_ARCHIVED_UNVERIFIED"
INDEPENDENT = "INDEPENDENT_HUMAN_EVIDENCE_REVIEW_REQUIRED"
LIVE = "LIVE_OPENING_REQUIRES_SEPARATE_OPERATIONAL_SOURCE"


def make_matrix(packet, original_dir):
    """Validate originals and emit ONLY an evidence-availability/checklist matrix.

    No automatic administrative statement interpretation or self-authorisation.
    """
    incoming = verify_reply_intake(packet, original_dir)
    states = incoming["office_states"]
    receipts = {v["office_id"]: v for v in incoming["archived_original_receipts"]}
    def gate(roles, action, limitation):
        missing = [r for r in roles if r not in receipts]
        return {
            "state": NOT_RECEIVED if missing else INDEPENDENT,
            "claimed_originals_present_not_authenticated": [
                r for r in roles if r in receipts
            ],
            "missing_office_originals": missing,
            "required_human_review": action,
            "limitation": limitation,
            "human_C_signed": False,
        }

    tracks = {
        "water_standby_external_flood": gate(
            ["disaster_plan"],
            "Human C must verify municipal sender, effective source version, actual OLD premises/building/floors, and the exact external inundation scope.",
            "A dated published standby listing cannot establish current designation or opening.",
        ),
        "water_standby_internal_flood": gate(
            ["disaster_plan"],
            "Human C must verify independent applicable inland-water listing, cancellation/suspension changes, actual OLD premises/building/floors.",
            "Inland inundation is not interchangeable with river flooding or GSI earthquake designation.",
        ),
        "old_campus_structure_and_access": gate(
            ["property_use"],
            "Human C must verify municipal reply authorship, dated executed contract, demolition by building, gym access and official closure/restriction notices.",
            "A voted construction contract is not proof of start, demolition completion or closure.",
        ),
        "same_physical_site_and_time": gate(
            ["disaster_plan", "property_use"],
            "Human C must reconcile the 2026-04 old/new campus and 2026-07 work chronology with original source pages, D coordinates and exact site effective dates.",
            "Old 東瑞江3-11-1 and new 瑞江4-19-10 remain separate; the 2026 plan prints the new site's address 瑞江4-19-1.",
        ),
    }
    tracks["real_time_opening"] = {
        "state": LIVE,
        "claimed_originals_present_not_authenticated": sorted(receipts),
        "missing_office_originals": [],
        "required_human_review": (
            "Verify the current incident/date-specific municipal headquarters opening "
            "announcement and physical access in the disaster context."
        ),
        "limitation": (
            "No historical council vote, reply, designated list or demolition plan "
            "can establish that a facility is open now."
        ),
        "human_C_signed": False,
    }
    original_keys = {x["office_id"]: x["original_sha256"] for x in
                     incoming["archived_original_receipts"]}
    return {
        "status": OUTPUT_STATUS,
        "issue": 141,
        "site": "旧下鎌田小学校",
        "source_revisions": dict(SOURCE_REFS),
        "original_source_role_states": {r: states[r] for r in OFFICES},
        "claimed_original_reply_digest_by_office": original_keys,
        "evidence_tracks": tracks,
        "sources_and_review_requirements_not_publication_of_private_reply_contents": True,
        "municipal_sender_not_authenticated_automatically": True,
        "municipal_evidence_factual_meaning_not_interpreted_automatically": True,
        "C_human_site_review_signed": False,
        "D_C_hazard_semantics_agreed": False,
        "reviewer_identity": None,
        "review_signature": None,
        "reviewed_at_utc": None,
        "D_export_modification_authorized": False,
        "old_site_current_physical_condition": "UNKNOWN",
        "old_site_external_standby_status": "UNKNOWN",
        "old_site_internal_standby_status": "UNKNOWN",
        "old_site_open_now": "UNKNOWN",
        "same_physical_old_new_campus_approved": False,
        "new_D_flood_candidate_or_excluded": 0,
        "D_region_export_read_or_mutated": False,
        "D_existing_152_scenario_statuses_not_reverified_by_this_tool": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--original-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Refusing to overwrite an existing C decision-readiness audit")
    try:
        packet_bytes = args.packet.read_bytes()
        record = make_matrix(json.loads(packet_bytes), args.original_dir)
        record["input_packet_sha256"] = sha256(packet_bytes).hexdigest()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(json.dumps({
            "status": record["status"],
            "original_office_states": record["original_source_role_states"],
            "human_site_approval": False, "flood_decisions": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        p.exit(2, "C human-only review-readiness gate rejected: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
