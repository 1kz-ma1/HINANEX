"""C-only evidence-by-evidence review work queue; never an approval engine.

Converts the existing C metadata preflight's reason codes into deterministic,
non-sensitive, actionable review requests. No source bytes are fetched/verified.
No real facility, S1 consumer, browser or deployment is modified or approved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import preflight_facility_evidence_packet as preflight

SCHEMA_ID = "hinanex.c.facility_evidence_review_work_queue.v0.1"
AREAS = ("source", "identity", "hazard_meaning", "reuse")
GATE_ACTIONS = {
    "source": ("C", "INDEPENDENT_SOURCE_ORIGINAL_AND_REVISION_AUDIT",
               ("source.url", "source.raw_sha256", "source.c_raw_audit_sha256",
                "source.source_revision", "asof_evidence_ref")),
    "identity": ("C", "CROSS_SOURCE_PHYSICAL_FACILITY_PAIR_REVIEW",
                 ("source.source_record_locator", "identity.target_record_locator",
                  "identity.independent_pair_review_ref", "identity.bound_source_sha256")),
    "hazard_meaning": ("A/C/D", "OFFICIAL_MARKER_AND_HAZARD_SCOPE_REVIEW",
                       ("hazard", "hazard_meaning.raw_marker",
                        "hazard_meaning.official_meaning_ref",
                        "hazard_meaning.independent_review_ref")),
    "reuse": ("A/OWNER", "DATASET_SPECIFIC_REUSE_AND_CREDIT_REVIEW",
              ("reuse.terms_url", "reuse.attribution_text",
               "reuse.exception_check_ref", "reuse.independent_review_ref")),
}
AREA_ROLE = {"source": "A", "identity": "C", "hazard_meaning": "A/C/D", "reuse": "A"}
SOURCE_AUDIT_CODES = {
    "SOURCE_C_BYTE_AUDIT_MISSING", "SOURCE_RAW_AUDIT_SHA_MISMATCH",
    "SOURCE_C_RAW_AUDIT_SHA256_INVALID_SHA",
    "IDENTITY_TARGET_C_BYTE_AUDIT_MISSING",
    "IDENTITY_TARGET_RAW_AUDIT_SHA_MISMATCH",
    "IDENTITY_TARGET_C_RAW_AUDIT_SHA256_INVALID_SHA",
}
SPECIAL_CODES = {
    "REQUEST_HAZARD_MISSING": ("hazard_meaning", ("hazard",)),
    "REQUEST_ASOF_MISSING_OR_INVALID_UTC": ("source", ("requested_asof",)),
    "SOURCE_ASOF_EVIDENCE_MISSING": ("source", ("asof_evidence_ref",)),
    "SOURCE_URL_NOT_HTTPS": ("source", ("source.url",)),
    "IDENTITY_TARGET_URL_NOT_HTTPS": ("identity", ("identity.target_source_url",)),
    "REUSE_TERMS_URL_NOT_HTTPS": ("reuse", ("reuse.terms_url",)),
    "SOURCE_CAPTURE_TIME_NOT_UTC": ("source", ("source.captured_at_utc",)),
    "IDENTITY_CAPTURE_TIME_NOT_UTC": ("identity", ("identity.target_captured_at_utc",)),
    "SOURCE_RAW_AUDIT_SHA_MISMATCH": (
        "source", ("source.raw_sha256", "source.c_raw_audit_sha256")),
    "IDENTITY_TARGET_RAW_AUDIT_SHA_MISMATCH": (
        "identity", ("identity.target_raw_sha256", "identity.target_c_raw_audit_sha256")),
    "HAZARD_SCOPE_MISMATCH": (
        "hazard_meaning", ("hazard", "hazard_meaning.reviewed_hazard")),
}

# This map is closed over the existing preflight reasons. New reason codes
# must get an explicit review-field mapping, not silently disappear.
REASONS: dict[str, tuple[str, tuple[str, ...]]] = {}
for _area, _fields in preflight.FIELDS.items():
    for _field, _reason in _fields.items():
        REASONS[_reason] = (_area, (f"{_area}.{_field}",))
for _area, _fields in (
    ("source", ("raw_sha256", "c_raw_audit_sha256")),
    ("identity", ("target_raw_sha256", "target_c_raw_audit_sha256", "bound_source_sha256")),
    ("hazard_meaning", ("bound_source_sha256",)),
    ("reuse", ("bound_source_sha256",)),
):
    for _field in _fields:
        REASONS[f"{_area.upper()}_{_field.upper()}_INVALID_SHA"] = (
            _area, (f"{_area}.{_field}",))
for _area in ("identity", "hazard_meaning", "reuse"):
    REASONS[f"{_area.upper()}_SOURCE_REVISION_BINDING_MISMATCH"] = (
        _area, ("source.raw_sha256", f"{_area}.bound_source_sha256"))
    REASONS[f"{_area.upper()}_INDEPENDENT_REVIEW_UNRESOLVED"] = (
        _area, (f"{_area}.disposition",))
    REASONS[f"{_area.upper()}_EVIDENCE_CONFLICT"] = (
        _area, (f"{_area}.disposition",))
REASONS.update(SPECIAL_CODES)


class WorkQueueError(ValueError):
    """Reject unrecognized upstream reason codes; do not produce partial work plans."""


def _make_task(case_id: str, area: str, reason_code: str, *,
               mandatory: bool) -> dict:
    if mandatory:
        owner, action, fields = GATE_ACTIONS[area]
        task_kind = "INDEPENDENT_AUTHENTICATION"
        # A complete metadata packet *still* requires a separate human audit.
        result_reason = action
    else:
        found = REASONS.get(reason_code)
        if found is None or found[0] != area:
            raise WorkQueueError(f"unmapped preflight reason: {area}.{reason_code}")
        fields = found[1]
        owner = ("C" if reason_code in SOURCE_AUDIT_CODES
                 else AREA_ROLE[area])
        action = (
            "RECONCILE_CONFLICT_AND_RECHECK_SOURCE"
            if ("MISMATCH" in reason_code or "CONFLICT" in reason_code)
            else "OBTAIN_INDEPENDENT_REVIEW_RECORD"
            if "REVIEW" in reason_code or "EVIDENCE_CONFLICT" in reason_code
            else "COLLECT_OR_CORRECT_EVIDENCE_REFERENCE"
        )
        task_kind = "GAP_REMEDIATION"
        result_reason = reason_code
    return {
        "task_id": f"{case_id}::{area}::{result_reason}",
        "case_id": case_id,
        "evidence_area": area,
        "kind": task_kind,
        "reason_code": result_reason,
        "responsible_roles": owner.split("/"),
        "action_code": action,
        "required_field_paths": list(fields),
        "status": "OPEN__UNVERIFIED",
        "requires_human_review": True,
        "approval_granted": False,
    }


def plan(packet: object) -> dict:
    """Read an operator-supplied packet, never trust a caller-supplied C report."""
    diagnosis = preflight.preflight(packet)
    rows = diagnosis["rows"]
    if diagnosis["records_checked"] != len(rows):
        raise WorkQueueError("preflight row count is inconsistent")
    cases = []
    gap_task_count = 0
    gate_task_count = 0
    for row in rows:
        case_id = row["case_id"]
        groups = row["reason_codes_by_area"]
        if set(groups) != set(AREAS):
            raise WorkQueueError("missing preflight evidence areas")
        gap_tasks = []
        mandatory_tasks = []
        for area in AREAS:
            for reason in groups[area]:
                gap_tasks.append(_make_task(case_id, area, reason, mandatory=False))
            mandatory_tasks.append(_make_task(case_id, area, "", mandatory=True))
        gap_task_count += len(gap_tasks)
        gate_task_count += len(mandatory_tasks)
        cases.append({
            "case_id": case_id,
            "preflight_status": row["status"],
            "gap_reason_count": len(gap_tasks),
            "tasks": gap_tasks + mandatory_tasks,
        })
    # Even a zero-gap packet cannot be an implicit official or live approval.
    return {
        "schema_id": SCHEMA_ID,
        "status": "REVIEW_WORK_QUEUE_ONLY__REAL_DATA_ADOPTION_HOLD",
        "source_preflight_status": diagnosis["status"],
        "case_count": len(cases),
        "gap_remediation_task_count": gap_task_count,
        "mandatory_authentication_task_count": gate_task_count,
        "open_task_count": gap_task_count + gate_task_count,
        "cases": cases,
        "source_bytes_authenticated_by_this_run": False,
        "independent_human_approval_recorded_by_this_run": False,
        "official_facility_identity_approved": False,
        "hazard_semantics_approved": False,
        "dataset_reuse_approved": False,
        "eligible_for_s1_real_facilities": False,
        "publication_approved": False,
        "human_decision_required": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline C-only evidence review work queue")
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = plan(json.loads(args.packet.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"C_REVIEW_QUEUE_INVALID__NO_APPROVAL: {type(exc).__name__}: {exc}")
        return 2
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f'{output["status"]}: '
              f'{output["open_task_count"]} open tasks / {output["case_count"]} cases')
        for case in output["cases"]:
            print(f'  {case["case_id"]}: {case["gap_reason_count"]} gaps + 4 mandatory reviews')
    # Exit 0 only means work-queue generation succeeded, NEVER data approval.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
