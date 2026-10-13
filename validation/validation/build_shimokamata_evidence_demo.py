"""C-only public-safe demonstration evidence, NOT evacuation-site availability.

Produces a fixed, source-cited, three-part case study for the old Shimokamata
school from previously machine-checked municipal historical originals and the
current human-review readiness state. It does not revalidate raw PDFs/HTML in
this run, accept municipal claims, classify hazards, or populate RegionExport.

NEVER feed this bundle into an actual navigation or shelter recommendation API.
The private authority reply packet is accepted only via the C SHA verifier,
and neither its raw content, filename nor digest appears in the export.

python validation/validation/build_shimokamata_evidence_demo.py \
  --packet validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json \
  --original-dir /private/official-replies \
  --out /private/shimokamata_demo_EVIDENCE_ONLY.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_shimokamata_review_readiness import (
    LIVE, NOT_RECEIVED, INDEPENDENT, OUTPUT_STATUS, make_matrix,
)
from verify_edogawa_official_reply_intake import SOURCE_REFS

DEMO_STATUS = "PUBLIC_EDUCATIONAL_EVIDENCE_NOT_SHELTER_GUIDANCE"
REQUIRED_EVIDENCE_TRACKS = (
    "water_standby_external_flood",
    "water_standby_internal_flood",
    "old_campus_structure_and_access",
    "same_physical_site_and_time",
    "real_time_opening",
)
REQUIRED_SOURCE_KEYS = (
    "2025_reuse_policy_pdf",
    "2026_external_internal_plan_pdf",
    "2026_demolition_bill_pdf",
    "2026_demolition_vote_html",
)
PUBLIC_SOURCES = {
    "2025_reuse_policy_pdf": {
        "original_url": "https://www.city.edogawa.tokyo.jp/documents/40376/0704simokamata_1.pdf",
        "document_date_scope": "2025-04",
        "source_type": "municipal_postclosure_policy",
        "verified_detail": "Planned demolition of the old school buildings including gym; completion not established.",
    },
    "2026_external_internal_plan_pdf": {
        "original_url": "https://www.city.edogawa.tokyo.jp/documents/68931/00006.pdf",
        "document_date_scope": "2026-04-01",
        "source_type": "dated_municipal_external_inland_water_standby_roster",
        "verified_detail": "Old and new Shimokamata schools appear separately in external and inland water tables.",
    },
    "2026_demolition_bill_pdf": {
        "original_url": "https://www.gikai.city.edogawa.tokyo.jp/voices/GikaiDoc/attach/Gk/Gk2792_gian64.pdf",
        "document_date_scope": "2026-06-12",
        "source_type": "municipal_assembly_contract_bill",
        "verified_detail": "Bill #64 proposes removal of former campus buildings including the gym; not proof of works completed.",
    },
    "2026_demolition_vote_html": {
        "original_url": (
            "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?"
            "BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152"
            "&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2"
        ),
        "document_date_scope": "2026-07-01",
        "source_type": "municipal_council_vote_result",
        "verified_detail": "Council bill #64 passed unanimously, not a demolition or current-opening certificate.",
    },
}


class DemoContractError(ValueError):
    pass


def _require(ok, issue):
    if not ok:
        raise DemoContractError(issue)


def build_evidence_demo(readiness):
    """Validate no-approval C readiness, return publication-safe source history."""
    _require(isinstance(readiness, dict) and readiness.get("status") == OUTPUT_STATUS,
             "Input must be original C no-decision readiness")
    _require(readiness.get("source_revisions") == SOURCE_REFS,
             "Pinned official original revisions differ")
    _require(readiness.get("site") == "旧下鎌田小学校"
             and type(readiness.get("issue")) is int and readiness["issue"] == 141,
             "Different or ambiguous physical site")
    for k, value in (
        ("C_human_site_review_signed", False),
        ("D_C_hazard_semantics_agreed", False),
        ("D_export_modification_authorized", False),
        ("same_physical_old_new_campus_approved", False),
        ("municipal_sender_not_authenticated_automatically", True),
        ("municipal_evidence_factual_meaning_not_interpreted_automatically", True),
        ("D_region_export_read_or_mutated", False),
        ("D_existing_152_scenario_statuses_not_reverified_by_this_tool", True),
        ("new_D_flood_candidate_or_excluded", 0),
    ):
        _require(type(readiness.get(k)) is type(value) and readiness[k] == value,
                 "C source readiness falsely endorses hazard/identity: " + k)
    for k in ("old_site_current_physical_condition", "old_site_external_standby_status",
              "old_site_internal_standby_status", "old_site_open_now"):
        _require(readiness.get(k) == "UNKNOWN", "Unapproved operational verdict: " + k)
    for k in ("reviewer_identity", "review_signature", "reviewed_at_utc"):
        _require(readiness.get(k) is None, "Forged human C review identity/date")
    tracks = readiness.get("evidence_tracks")
    _require(isinstance(tracks, dict) and set(tracks) == set(REQUIRED_EVIDENCE_TRACKS),
             "Missing or unexpected evidence-review track")
    for name in REQUIRED_EVIDENCE_TRACKS:
        v = tracks[name]
        _require(isinstance(v, dict) and v.get("human_C_signed") is False,
                 "Unsigned C evidence track was promoted")
        _require(v.get("state") in (
            (LIVE,) if name == "real_time_opening" else (NOT_RECEIVED, INDEPENDENT)
        ), "Unknown or falsely approved track state")
    _require(set(PUBLIC_SOURCES) == set(REQUIRED_SOURCE_KEYS)
             and set(SOURCE_REFS) == set(PUBLIC_SOURCES),
             "Original document sources missing from public-safe contract")

    # Compose from a fixed, public, independently documented source catalogue.
    # No source fields, metadata, or arbitrary strings from private office
    # replies / readiness records flow into this public output.
    source_cards = {
        key: {
            **PUBLIC_SOURCES[key],
            "original_sha256": SOURCE_REFS[key],
            "originals_checked_in_prior_separate_github_actions": True,
            "original_bytes_reverified_by_this_public_export": False,
            "human_C_physical_site_approval": False,
        }
        for key in REQUIRED_SOURCE_KEYS
    }
    return {
        "status": DEMO_STATUS,
        "presentation_only": True,
        "current_site_safety_or_opening_claim": False,
        "may_be_used_as_live_shelter_recommendation": False,
        "consumer_contract": "C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1",
        "target_case": {
            "name": "旧下鎌田小学校",
            "site_address_raw": "東瑞江3丁目11番1号",
            "separate_current_school_address_raw": "瑞江4丁目19番10号",
            "new_school_plan_raw_address_2026": "瑞江4-19-1",
            "old_new_premises_human_link_approved": False,
        },
        "source_documents": source_cards,
        "demo_states": [
            {
                "key": "DOCUMENTARY_FACT",
                "label": "公式資料で確認できること",
                "display_state": "HISTORICAL_SOURCE_FACT",
                "source_keys": [
                    "2025_reuse_policy_pdf",
                    "2026_external_internal_plan_pdf",
                    "2026_demolition_bill_pdf",
                    "2026_demolition_vote_html",
                ],
                "message": (
                    "2026年4月1日時点の区の資料では旧・新下鎌田小を別施設として掲載。"
                    "同年7月に旧施設の解体工事契約議案が可決された。"
                ),
                "document_dates_not_current_operating_dates": True,
            },
            {
                "key": "SOURCE_VERSION_RECONCILIATION",
                "label": "資料間で追加確認が必要なこと",
                "display_state": "HUMAN_SOURCE_RECONCILIATION_REQUIRED",
                "source_keys": [
                    "2025_reuse_policy_pdf",
                    "2026_external_internal_plan_pdf",
                    "2026_demolition_bill_pdf",
                ],
                "message": (
                    "水害待避施設一覧と旧校舎の解体計画・契約は対象時点が異なる。"
                    "新校舎の住所表記にも資料間差があるため、指定先の建物・適用時点を確認する。"
                ),
                "not_a_proven_logical_contradiction": True,
            },
            {
                "key": "CURRENT_OPERATIONS_UNKNOWN",
                "label": "現在の状態は未確認",
                "display_state": "UNKNOWN_HUMAN_AND_LIVE_SOURCE_REQUIRED",
                "source_keys": [
                    "2026_external_internal_plan_pdf",
                    "2026_demolition_vote_html",
                ],
                "message": (
                    "旧校舎・体育館の現存、工事による立入制限、外水・内水の指定継続、"
                    "災害当日の開設状況は未確認。安全・危険、利用可・不可のいずれにも確定しない。"
                ),
                "current_operational_status": "UNKNOWN",
            },
        ],
        "not_reenacted_historical_disaster_or_predictive_accuracy_result": True,
        "human_C_site_pairs_approved": 0,
        "new_flood_candidate_or_excluded": 0,
        "region_export_read_or_mutated": False,
        "no_private_reply_text_or_personal_data_included": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--original-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error("Refusing to overwrite existing public-safe case-study artifact")
    try:
        private_packet = json.loads(args.packet.read_text(encoding="utf-8"))
        readiness = make_matrix(private_packet, args.original_dir)
        output = build_evidence_demo(readiness)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(json.dumps({
            "status": output["status"],
            "presentation_stages": len(output["demo_states"]),
            "safe_or_live_conclusions": 0,
        }, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        ap.exit(2, "C source-cited educational export failed closed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
