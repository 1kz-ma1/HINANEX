"""C fail-closed evidence intake for OLD Shimokamata school official replies.

Intake validation checks source bytes/provenance, NOT what municipal officials
meant, signature legitimacy, physical premises identity or any shelter status.
No D API or flood Scenario is accessed. An actual response always results in
HUMAN_C_REVIEW_REQUIRED, never a facility classification.

python validation/validation/verify_edogawa_official_reply_intake.py \
  --packet validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json \
  --original-dir /outside-git/replies \
  --out /outside-git/C_reply_intake_REVIEW_REQUIRED.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

ISSUE = 141
SITE = "旧下鎌田小学校"
ADDRESS = "東瑞江3丁目11番1号"
PURPOSE = "C_SHIMOKAMATA_OFFICIAL_REPLY_INTAKE_NO_AUTOMATIC_APPROVAL"
SOURCE_REFS = {
    "2026_external_internal_plan_pdf":
        "92e85981c16542e3e28bd80bafc56c8a71f3ded9a8b5e67bcb53919d16e1ebcb",
    "2026_demolition_bill_pdf":
        "aa9051ef17e94da904e7e11fa228239d59a37e3eb256b0bc44f68991e19adc71",
    "2026_demolition_vote_html":
        "83e6d3bac16705d3a842b7129883f8151e40426abd9f2e40c123ff220ec8ab20",
    "2025_reuse_policy_pdf":
        "a4fee786088052e1bb787f0db0473245d01cc1cae9784c80ef40b3174ed089bf",
}
OFFICES = {
    "disaster_plan": {
        "name": "江戸川区 防災危機管理課 計画係",
        "phone": "03-5662-1992",
        "public_reference_url": (
            "https://www.city.edogawa.tokyo.jp/e007/kuseijoho/gaiyo/"
            "soshiki/kikikanri/bousaikikikanri.html"
        ),
    },
    "property_use": {
        "name": "江戸川区 財産活用課 調整係",
        "phone": "03-5662-9017",
        "public_reference_url": (
            "https://www.city.edogawa.tokyo.jp/e085/kuseijoho/"
            "zaisei/zaisankatsuyo/advertisement.html"
        ),
    },
}
STATES = ("NOT_CONTACTED", "CONTACTED_AWAITING_REPLY", "REPLY_ARCHIVED_UNREVIEWED")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ReplyIntakeFailure(ValueError):
    pass


def must(cond, message):
    if not cond:
        raise ReplyIntakeFailure(message)


def iso_utc(value):
    must(isinstance(value, str), "Expected ISO8601 UTC date")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplyIntakeFailure("Invalid response timestamp") from exc
    must(d.utcoffset() is not None and d.utcoffset().total_seconds() == 0,
         "Timestamp must have UTC offset")
    return d


def _safe_evidence_name(name):
    must(isinstance(name, str) and len(name) <= 120 and name, "Evidence filename missing")
    must(name not in (".", "..") and "/" not in name and "\\" not in name
         and name == Path(name).name and not name.startswith("."),
         "Evidence path may not traverse original directory")
    return name


def evaluate(packet, original_dir):
    must(isinstance(packet, dict), "Intake JSON packet must be an object")
    must(packet.get("purpose") == PURPOSE and type(packet.get("issue_number")) is int
         and packet["issue_number"] == ISSUE and
         packet.get("site_name") == SITE and packet.get("site_address_raw") == ADDRESS,
         "Wrong issue or specific physical campus")
    must(packet.get("related_new_school_address_raw") == "瑞江4丁目19番10号",
         "Old and new campuses cannot be collapsed")
    must(packet.get("source_sha256") == SOURCE_REFS,
         "Evidence revisions do not match known independently checked originals")
    must(packet.get("human_c_site_identity_approved") is False
         and packet.get("human_c_hazard_semantics_approved") is False
         and packet.get("human_c_current_opening_approved") is False
         and type(packet.get("new_flood_classifications")) is int
         and packet.get("new_flood_classifications") == 0,
         "Packet claims site/hazard/current-operation approval")
    must(packet.get("outreach_was_automatically_sent") is False,
         "A generated packet cannot claim a message was sent")
    records = packet.get("office_requests")
    must(isinstance(records, list) and len(records) == len(OFFICES),
         "Both responsible municipal offices require separate evidence")
    folder = Path(original_dir)
    must(folder.is_dir() and not folder.is_symlink(), "Evidence root absent/unsafe")
    statuses = {}
    observed = set()
    receipts = []
    used_evidence_files = set()
    for item in records:
        must(isinstance(item, dict), "Office request must be a record")
        role = item.get("office_id")
        must(role in OFFICES and role not in observed, "Office role unknown/duplicate")
        observed.add(role)
        official = OFFICES[role]
        must(item.get("office_name") == official["name"]
             and item.get("phone") == official["phone"]
             and item.get("public_reference_url") == official["public_reference_url"],
             "Official contact routing was substituted")
        state = item.get("state")
        must(state in STATES, "Unknown official inquiry state")
        sent = item.get("contacted_at_utc")
        reply = item.get("response_evidence")
        if state == "NOT_CONTACTED":
            must(sent is None and reply is None,
                 "No contact can include a sent time or a reply")
        else:
            iso_utc(sent)
        if state == "CONTACTED_AWAITING_REPLY":
            must(reply is None, "Pending official reply cannot pretend evidence receipt")
        elif state == "REPLY_ARCHIVED_UNREVIEWED":
            must(isinstance(reply, dict), "Reply requires its raw original evidence")
            name = _safe_evidence_name(reply.get("original_filename"))
            must(name not in used_evidence_files,
                 "One original reply cannot substitute for two responsible offices")
            used_evidence_files.add(name)
            digest = reply.get("sha256")
            must(isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
                 "Official reply evidence SHA256 required")
            received = iso_utc(reply.get("received_at_utc"))
            must(received >= iso_utc(sent), "Reply cannot precede inquiry")
            must(reply.get("claimed_office_name") == official["name"]
                 and reply.get("response_channel") in ("email", "letter", "telephone_memo"),
                 "Claimed office/channel must be recorded for C review")
            must(reply.get("independent_c_authenticity_confirmed") is False
                 and reply.get("human_c_signed_review") is False,
                 "Intake must never self-approve official authorship or signed review")
            f = folder / name
            must(not f.is_symlink() and f.is_file(), "Official reply original missing or symlink")
            raw = f.read_bytes()
            must(0 < len(raw) <= 10_000_000 and sha256(raw).hexdigest() == digest,
                 "Reply original does not match source SHA256")
            if reply["response_channel"] == "telephone_memo":
                must(reply.get("memo_is_not_a_signed_municipal_document") is True,
                     "Telephone memo cannot be used as signed official document")
            receipts.append({
                "office_id": role,
                "channel": reply["response_channel"],
                "original_filename": name,
                "original_sha256": digest,
                "source_bytes": len(raw),
                "received_at_utc": reply["received_at_utc"],
                "original_authorship_not_independently_verified": True,
                "content_not_interpreted_by_intake": True,
            })
        statuses[role] = state
    must(set(statuses) == set(OFFICES), "Missing municipal responsible office")
    return {
        "status": ("C_ORIGINAL_REPLIES_PRESENT_HUMAN_REVIEW_REQUIRED" if receipts else
                   "C_AWAITING_AUTHORITY_CONFIRMATION_NO_SITE_DECISION"),
        "issue": ISSUE,
        "specific_former_site": SITE,
        "office_states": statuses,
        "archived_original_receipts": receipts,
        "source_revisions_bound_to_originals": SOURCE_REFS,
        "physical_old_new_campus_cross_join_approved": False,
        "municipal_reply_authenticity_and_meaning_human_review_required": True,
        "official_site_standby_designation_current": "UNKNOWN",
        "old_buildings_physical_condition": "UNKNOWN",
        "old_onsite_gym_access": "UNKNOWN",
        "real_time_standby_open_status": "UNKNOWN",
        "current_D_flood_scenario_152_facilities_remain_UNKNOWN": True,
        "human_c_approved_site_pairs": 0,
        "new_flood_candidates_or_exclusions": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--original-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Do not overwrite previous C reply intake audit")
    try:
        x = evaluate(json.loads(args.packet.read_text(encoding="utf-8")), args.original_dir)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(json.dumps({"status": x["status"], "office_states": x["office_states"],
                          "approved_sites": 0, "flood_decisions_added": 0}, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        p.exit(2, "C original reply intake failed closed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
