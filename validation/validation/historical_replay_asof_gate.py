"""C historical replay input preflight: reject future information and unapproved sources.

This checks the *submitted* evidence and independent review ledger. It is NOT a
signature-verification mechanism: humans must separately establish the ledger's
authenticity and confirm historical public availability before any T1/T2 claim.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

CASE_SCHEMA = "hinanex.historical_replay_case.v0.1"
REVIEW_SCHEMA = "hinanex.c.historical_input_reviews.v0.1"
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_ROLES = {"INPUT", "TRUTH", "CONTEXT"}


class ReplayInputError(ValueError):
    pass


def instant(value: str) -> dt.datetime:
    """No timezone-naive or ambiguous local time; enforce explicit +09:00."""
    if not isinstance(value, str):
        raise ReplayInputError("timestamp missing or not ISO-8601")
    try:
        result = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReplayInputError("malformed timestamp") from exc
    if result.tzinfo is None or result.utcoffset() != dt.timedelta(hours=9):
        raise ReplayInputError("must use explicit Asia/Tokyo +09:00 timestamp")
    return result


def digest(value: object) -> bool:
    return isinstance(value, str) and DIGEST.fullmatch(value) is not None


def source_ids(case: dict) -> dict:
    rows = case.get("sources", [])
    if not isinstance(rows, list) or not rows:
        raise ReplayInputError("nonempty source list required")
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("source_id"), str):
            raise ReplayInputError("invalid source entry")
        sid = row["source_id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,127}", sid) or sid in found:
            raise ReplayInputError("duplicate or invalid source identifier")
        if row.get("role") not in ALLOWED_ROLES:
            raise ReplayInputError("source must be INPUT, TRUTH or CONTEXT")
        if not isinstance(row.get("depends_on", []), list):
            raise ReplayInputError("depends_on must be a list")
        if any(not isinstance(x, str) for x in row.get("depends_on", [])):
            raise ReplayInputError("depends_on members must be IDs")
        found[sid] = row
    for sid, row in found.items():
        if sid in row.get("depends_on", []):
            raise ReplayInputError("self-derived source is invalid")
        if any(x not in found for x in row.get("depends_on", [])):
            raise ReplayInputError("missing provenance dependency")
    return found


def check_provenance(found: dict, sid: str, visiting: set[str], done: set[str]) -> None:
    if sid in visiting:
        raise ReplayInputError("provenance dependency cycle")
    if sid in done:
        return
    visiting.add(sid)
    for parent in found[sid].get("depends_on", []):
        check_provenance(found, parent, visiting, done)
    visiting.remove(sid)
    done.add(sid)


def preflight(case: dict, c_reviews: dict) -> dict:
    if case.get("schema_id") != CASE_SCHEMA or c_reviews.get("schema_id") != REVIEW_SCHEMA:
        raise ReplayInputError("unrecognized case or C review contract")
    if case.get("case_id") != c_reviews.get("case_id") or not case.get("case_id"):
        raise ReplayInputError("cross-event review ledger")
    at = instant(case.get("as_of_jst"))
    found = source_ids(case)
    reviewed = c_reviews.get("approved_input_sources", [])
    if not isinstance(reviewed, list):
        raise ReplayInputError("invalid C reviewed source list")
    approvals = {}
    for review in reviewed:
        if not isinstance(review, dict) or not isinstance(review.get("source_id"), str):
            raise ReplayInputError("invalid review entry")
        sid = review["source_id"]
        if sid in approvals:
            raise ReplayInputError("duplicate C review source")
        approvals[sid] = review
    for sid in approvals:
        if sid not in found:
            raise ReplayInputError("C review references unregistered source")
    done: set[str] = set()
    for sid in found:
        check_provenance(found, sid, set(), done)

    output = []
    for sid, row in found.items():
        role = row["role"]
        if role != "INPUT":
            output.append({"source_id": sid, "role": role,
                           "status": "TRUTH_QUARANTINED" if role == "TRUTH" else "CONTEXT_NOT_INPUT",
                           "reasons": []})
            continue
        reasons = []
        raw_sha = row.get("archive_sha256")
        if not digest(raw_sha):
            reasons.append("ORIGINAL_DIGEST_NOT_ESTABLISHED")
        # Never treat observation time as publication time.
        source_release = row.get("published_at_jst")
        if source_release is None:
            reasons.append("PUBLICATION_INSTANT_UNKNOWN")
        else:
            published = instant(source_release)
            if published > at:
                reasons.append("AFTER_AS_OF")
        if row.get("post_event_report") is True:
            reasons.append("POST_EVENT_SOURCE_AS_INPUT")
        stack = list(row.get("depends_on", []))
        seen = set()
        while stack:
            parent = stack.pop()
            if parent in seen:
                continue
            seen.add(parent)
            if found[parent]["role"] == "TRUTH":
                reasons.append("TRUTH_LINEAGE_IN_INPUT")
            stack.extend(found[parent].get("depends_on", []))
        approval = approvals.get(sid)
        if approval is None:
            reasons.append("INDEPENDENT_C_REVIEW_MISSING")
        else:
            if (approval.get("review_state") != "C_APPROVED"
                    or approval.get("historical_version_verified") is not True
                    or not isinstance(approval.get("approval_ref"), str)
                    or not approval["approval_ref"].strip()):
                reasons.append("HISTORICAL_VERSION_NOT_C_APPROVED")
            if not digest(approval.get("original_sha256")) or approval.get("original_sha256") != raw_sha:
                reasons.append("APPROVED_DIGEST_MISMATCH")
            # This timestamp must be independently evidenced; candidate's
            # publication timestamp alone never supplies C's determination.
            released = approval.get("verified_public_at_jst")
            if released is None:
                reasons.append("C_VERIFIED_RELEASE_INSTANT_MISSING")
            else:
                verified_time = instant(released)
                if verified_time > at:
                    reasons.append("C_VERIFIED_RELEASE_AFTER_AS_OF")
                if source_release is not None and verified_time < instant(source_release):
                    reasons.append("REVIEW_TIME_CONFLICT")
        status = "PRECHECK_PASSED__NOT_FINAL_APPROVAL" if not reasons else "BLOCKED"
        output.append({"source_id": sid, "role": role, "status": status,
                       "reasons": sorted(set(reasons))})
    inputs = [row for row in output if row["role"] == "INPUT"]
    return {
        "schema_id": "hinanex.c.historical_replay_preflight_report.v0.1",
        "case_id": case["case_id"],
        "as_of_jst": case["as_of_jst"],
        "status": "PRECHECK_PASSED__HUMAN_REVIEW_REQUIRED"
                  if inputs and all(row["status"].startswith("PRECHECK_PASSED") for row in inputs)
                  else "BLOCKED",
        "source_checks": output,
        "safe_input_source_ids": [x["source_id"] for x in inputs
                                  if x["status"].startswith("PRECHECK_PASSED")],
        "human_independent_review_required": True,
        "prediction_accuracy_evaluated": False,
        "facility_eligibility_evaluated": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--c-reviews", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        case_bytes = args.case.read_bytes()
        review_bytes = args.c_reviews.read_bytes()
        report = preflight(json.loads(case_bytes), json.loads(review_bytes))
        report["case_manifest_sha256"] = hashlib.sha256(case_bytes).hexdigest()
        report["c_review_manifest_sha256"] = hashlib.sha256(review_bytes).hexdigest()
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            if args.out.exists():
                raise ReplayInputError("refuse to overwrite C report")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload, encoding="utf-8")
        print(payload)
        return 0 if report["status"].startswith("PRECHECK_PASSED") else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("C_HISTORICAL_ASOF_GATE_ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
