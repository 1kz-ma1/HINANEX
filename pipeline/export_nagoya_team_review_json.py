"""Produce a minimal offline team review JSON from a validated PRIVATE Stage-7 worksheet.

The source PRIVATE CSV never leaves the operator's machine. The output is an
operator-controlled SHARING artifact, not an automatically published data set.
No coordinates, facility-source IDs, candidate points, GSI raw records, URL
parameters, confidential review fields or proof of actual site safety are copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from refine_nagoya_gsi_stage7 import RANKS
from nagoya_team_review_official_sources import official_ward_pdf
from view_nagoya_stage7_private import read_stage7_private, validate as validate_stage7

SCHEMA_ID = "hinanex.team-review.v1"
OFFICIAL_PORTAL = "https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html"
ALLOWED_FLAGS = frozenset((
    "gsi_conflicting_reference_points",
    "different_facility_name_at_same_address",
    "abr_gsi_reference_distance_at_least_100m",
    "parcel_reference_requires_special_review",
    "other_gsi_incomplete_correspondence",
    "near_coincident_gsi_references",
    "source_renovation_notice",
))
STATES = {
    "gsi_distinct_references_under_1mm": (
        "gsi_conflicting_reference_points", "near_coincident_gsi_references"),
    "source_renovation_notice_name_correspondence": (
        "different_facility_name_at_same_address", "source_renovation_notice"),
}
CHECKS = ("official_source", "identity", "address", "position_evidence")


def check_fingerprint(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Stage-7 source fingerprint is invalid")
    return value


def clean_codes(row: dict) -> list[str]:
    flag_text = row["stage6_risk_flags"]
    if not isinstance(flag_text, str):
        raise ValueError("Unexpected Stage-6 risk flag format")
    raw = flag_text.split(";") if flag_text else []
    if len(raw) != len(set(raw)) or not set(raw) <= ALLOWED_FLAGS:
        raise ValueError("Unexpected or duplicated risk flags")
    mapping = STATES.get(row["stage7_classification"])
    if mapping:
        historical, current = mapping
        if historical not in raw:
            raise ValueError("Stage-7 classification missing historical risk evidence")
        raw = [f for f in raw if f != historical]
        raw.append(current)
    return raw


def make_package(rows: list[dict], summary: dict, priorities: tuple[str, ...]) -> dict:
    validate_stage7(rows, summary)
    sha = check_fingerprint(summary.get("source_dataset_sha256"))
    if not priorities or len(set(priorities)) != len(priorities) or set(priorities) - {"P0", "P1", "P2"}:
        raise ValueError("Invalid priority selection")
    ids = set()
    records = []
    for row in rows:
        priority = row["stage7_priority"][:2]
        if priority not in priorities:
            continue
        raw_id = row["pilot_record_id"]
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ValueError("Missing private record identity")
        anonymous_id = hashlib.sha256((sha + "\0" + raw_id).encode("utf-8")).hexdigest()[:24]
        if anonymous_id in ids:
            raise ValueError("Duplicate opaque ID")
        ids.add(anonymous_id)
        name, address = row["facility_name"], row["official_listed_address"]
        if not all(isinstance(item, str) and item.strip() for item in (name, address)):
            raise ValueError("Missing official facility name or listed address")
        if len(name) > 240 or len(address) > 300:
            raise ValueError("Official display field too long for review schema")
        ward_pdf = official_ward_pdf(name, address)
        sources = [{"title": "名古屋市・指定緊急避難場所／指定避難所一覧（公式一覧、2026-09-01時点）",
                    "url": OFFICIAL_PORTAL}]
        if ward_pdf:
            sources.append(ward_pdf)
        records.append({
            "id": "nagoya-" + anonymous_id,
            "name": name,
            "address": address,
            "priority": priority,
            "issues": clean_codes(row),
            "sources": sources,
            "review": {
                "status": "not_reviewed",
                "checks": {key: False for key in CHECKS},
                "reviewer": "",
                "notes": "",
                "evidence_url": "",
                "reviewed_at": None,
            },
        })
    records.sort(key=lambda r: (("P0", "P1", "P2").index(r["priority"]), r["id"]))
    if not records:
        raise ValueError("No selected review records")
    expected = sum(summary["refined_priority_counts"][key] for key in RANKS
                   if key[:2] in priorities)
    if len(records) != expected:
        raise ValueError("Subset total does not reproduce Stage-7 priority counts")
    return {
        "schema_id": SCHEMA_ID,
        "dataset": {
            "id": "nagoya-stage7-" + "-".join(sorted(priorities)),
            "region": "愛知県名古屋市（Stage 7施設資料の照合支援のみ）",
            "source_fingerprint": sha,
        },
        "safety": {
            "approved_for_map": False,
            "data_promotion_authorized": False,
            "official_facility_positions_accepted": 0,
        },
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--priorities", nargs="+", choices=("P0", "P1", "P2"), default=["P1"])
    args = parser.parse_args()
    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != root and root not in folder.parents:
        parser.error("Only a gitignored local pilot directory is allowed")
    filename = "team_review_" + "_".join(sorted(args.priorities)).lower() + "_LOCAL.json"
    output = folder / filename
    if output.exists():
        parser.error("Local team JSON already exists; refusing to overwrite or lose reviewer updates")
    try:
        rows = read_stage7_private(folder / "gsi_stage7_refined_PRIVATE.csv")
        summary = json.loads((folder / "gsi_stage7_refined_aggregate.json").read_text("utf-8"))
        result = make_package(rows, summary, tuple(args.priorities))
        with output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, "Local team JSON export aborted [" + type(exc).__name__ +
                    "]; PRIVATE inputs unchanged. No files published.\n")
    print(json.dumps({
        "report_kind": "NAGOYA_TEAM_REVIEW_LOCAL_PACKAGE_NOT_SITE_APPROVAL",
        "review_records": len(result["records"]),
        "priorities": sorted(args.priorities),
        "contains_candidate_coordinates": False,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "operator_must_authorize_sharing": True,
        "private_source_unchanged": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
