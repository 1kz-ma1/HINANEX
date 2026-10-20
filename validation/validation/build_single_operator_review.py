"""Prepare and structurally check ONE owner's decisions on A/C AI prereview.

This is documentation, NOT D data promotion or validation of a human identity.
The seven C originals + ten item review remain separate evidence trails.
No network, writes to repository, or inferred hazard classification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from check_edogawa_review_packet import snapshot_and_receipt, ReviewPacketError, require

TOPICS = (
    "C-SITE-OLD-NEW",
    "C-MUNICIPAL-CROSSSOURCE",
    "C-GSI-FLOOD-SEPARATION",
    "A-LICENSE",
)
DECISIONS = {"PENDING", "ACCEPT_FACTS_ONLY", "HOLD", "REJECT"}


def _load_json(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    result = json.loads(data)
    require(type(result) is dict, "AI prereview or packet must be an object")
    return result, hashlib.sha256(data).hexdigest()


def _evidence_url(url: str) -> bool:
    if type(url) is not str:
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def _required_proposals(report: dict, receipt: dict, rhash: str, ai: dict) -> list[dict]:
    require(ai.get("status") == "AI_PREREVIEW_UNAPPROVED", "AI prereview is not an unapproved suggestion")
    require(type(ai.get("human_approvals")) is int and ai["human_approvals"] == 0
            and ai.get("d_source_promotion_authorized") is False,
            "AI prereview asserts a human approval")
    require(ai.get("formal_report_sha256") == rhash and
            ai.get("old_archive_zip_sha256") == receipt["old_artifact_sha256"] and
            ai.get("new_archive_zip_sha256") == receipt["new_artifact_sha256"] and
            ai.get("pinned_git_head") == receipt["pinned_git_head"] and
            ai.get("snapshot_old_utc") == report["previous_captured_at_utc"] and
            ai.get("snapshot_new_utc") == report["current_captured_at_utc"],
            "AI prereview provenance does not match actual C report and receipt")
    raw_sources = report["sources"]
    previews = ai.get("source_previews")
    require(type(previews) is list and len(previews) == len(raw_sources), "AI source inventory incomplete")
    for source, preview in zip(raw_sources, previews):
        require(type(preview) is dict and
                preview.get("source_key") == source["source_key"] and
                preview.get("source_url") == source["requested_url"] and
                preview.get("old_sha256") == source["previous_sha256"] and
                preview.get("new_sha256") == source["current_sha256"] and
                preview.get("original_bytes") == source["current_byte_size"] and
                preview.get("changed") is source["raw_bytes_changed"] and
                preview.get("human_review_disposition") == "PENDING" and
                preview.get("original_effective_date_verified") is None and
                preview.get("license_specific_to_this_source_verified") is None,
                "AI source preview disagrees with pinned originals or falsely approves")
    clusters = ai.get("critical_human_review_clusters")
    require(type(clusters) is list and len(clusters) == len(TOPICS), "Expected exactly 4 human decision clusters")
    result = []
    for expect, cluster in zip(TOPICS, clusters):
        require(type(cluster) is dict and cluster.get("decision_id") == expect,
                "review cluster IDs/order mismatch")
        expected_fields = ("issue", "evidence", "ai_finding", "restriction", "required_human_action")
        require(all(type(cluster.get(k)) is str and cluster[k].strip() for k in expected_fields),
                "AI decision proposal is incomplete")
        require(cluster.get("status") in ("HUMAN_REVIEW_REQUIRED", "FOLLOWUP_IF_REPUBLISHING"),
                "AI decision proposal falsely approved")
        result.append({
            "id": expect,
            "question": cluster["issue"],
            "ai_proposal_unsigned": cluster["ai_finding"],
            "review_evidence_lead": cluster["evidence"],
            "limitations": cluster["restriction"],
            "requested_operator_action": cluster["required_human_action"],
            "decision": "PENDING",  # explicitly no implied consent
            "reason": None,
            "reviewed_evidence_urls": [],
        })
    return result


def make_packet(report: dict, receipt: dict, rsha: str, esha: str, ai: dict, ai_sha: str) -> dict:
    proposals = _required_proposals(report, receipt, rsha, ai)
    return {
        "schema_version": 1,
        "scope": "ONE_OPERATOR_DOCUMENTATION_ONLY_NO_D_PROMOTION",
        "formal_c_report_sha256": rsha,
        "operator_receipt_sha256": esha,
        "ai_prereview_sha256": ai_sha,
        "git_source_head_sha": receipt["pinned_git_head"],
        "source_runs": [receipt["old_run"], receipt["new_run"]],
        "source_originals": [{"source_key": x["source_key"],
                              "requested_url": x["requested_url"],
                              "previous_sha256": x["previous_sha256"],
                              "current_sha256": x["current_sha256"]}
                             for x in report["sources"]],
        "single_operator": {"github_login_claimed": None, "reviewed_at_utc": None},
        "decisions": proposals,
        "independent_technical_checks_preserved": True,
        "independent_second_human_reviewer_claimed": False,
        "d_source_promotion_authorized": False,
        "approved_cross_source_pairs": 0,
        "new_flood_classifications": 0,
    }


def check_packet(report: dict, receipt: dict, rsha: str, esha: str,
                 ai: dict, ai_sha: str, packet: dict) -> dict:
    expected = make_packet(report, receipt, rsha, esha, ai, ai_sha)
    require(type(packet) is dict and set(packet) == set(expected), "Packet shape/fields modified")
    for key, value in expected.items():
        if key in ("decisions", "single_operator"):
            continue
        require(type(packet[key]) is type(value) and packet[key] == value,
                "Tampered provenance or safety invariant: " + key)
    user = packet["single_operator"]
    require(type(user) is dict and set(user) == {"github_login_claimed", "reviewed_at_utc"},
            "Single operator identity fields invalid")
    rows = packet["decisions"]
    require(type(rows) is list and len(rows) == len(TOPICS), "Expected 4 human decisions")
    counts = {x: 0 for x in DECISIONS}
    for old, row in zip(expected["decisions"], rows):
        require(type(row) is dict and set(row) == set(old), "Decision fields missing or added")
        for field in ("id", "question", "ai_proposal_unsigned", "review_evidence_lead",
                      "limitations", "requested_operator_action"):
            require(row[field] == old[field], "AI evidence was altered in decision " + old["id"])
        decision = row.get("decision")
        require(type(decision) is str and decision in DECISIONS, "Unexpected decision option")
        counts[decision] += 1
        reason, urls = row["reason"], row["reviewed_evidence_urls"]
        require(type(urls) is list and all(_evidence_url(u) for u in urls),
                "Evidence references must be literal HTTPS URLs")
        if decision == "PENDING":
            require(reason is None and urls == [], "PENDING row cannot claim a human finding")
        else:
            require(type(reason) is str and len(reason.strip()) >= 12,
                    "Explicit decision needs a substantive operator reason")
            if decision == "ACCEPT_FACTS_ONLY":
                require(bool(urls), "Accepting evidence facts requires at least one reviewed official URL")
    active = sum(value for k, value in counts.items() if k != "PENDING")
    login, timestamp = user["github_login_claimed"], user["reviewed_at_utc"]
    if active:
        require(type(login) is str and login.strip() and login not in ("AI", "ChatGPT"),
                "A nonempty claimed human GitHub identity is required")
        require(type(timestamp) is str, "Human review timestamp required")
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReviewPacketError("Invalid operator UTC timestamp") from exc
        require(dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0,
                "Review timestamp must be UTC")
        # This only checks the timestamp syntax; it cannot prove when a human actually reviewed.
    else:
        require(login is None and timestamp is None, "Unsigned PENDING template must be anonymous")
    return {
        "status": "HOLD_EXTERNAL_OWNER_SIGNOFF_AND_SCOPE_REQUIRED",
        "review_decisions": counts,
        "source_documentation_covered_by_ai": 7,
        "independent_technical_checks_preserved": True,
        "single_operator_identity_verified_by_tool": False,
        "human_approval_verified_by_tool": False,
        "independent_second_human_reviewer_claimed": False,
        "d_source_promotion_authorized": False,
        "approved_cross_source_pairs": 0,
        "new_flood_classifications": 0,
        "limitations": "An owner can decide all four topics in one pass, but this unsigned JSON cannot release data. Any specific physical-site join, flood designation or deployment needs explicit separately authenticated, scope-bound authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-report", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--ai-prereview", required=True, type=Path)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create", type=Path)
    actions.add_argument("--check", type=Path)
    args = parser.parse_args()
    try:
        report, receipt, rsha, esha = snapshot_and_receipt(args.formal_report, args.receipt)
        ai, ai_sha = _load_json(args.ai_prereview)
        if args.create:
            dest = args.create
            repo_root = Path(__file__).resolve().parents[2]
            resolved = dest.resolve()
            require(resolved != repo_root and repo_root not in resolved.parents,
                    "Private operator decisions must stay outside Git checkout")
            require(not dest.exists() and not dest.is_symlink(), "Refusing to overwrite an existing decision file")
            packet = make_packet(report, receipt, rsha, esha, ai, ai_sha)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as stream:
                json.dump(packet, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        else:
            packet, _ = _load_json(args.check)
        status = check_packet(report, receipt, rsha, esha, ai, ai_sha, packet)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "Single-operator review REJECTED (NO DATA AUTHORITY): " + str(exc) + "\n")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())