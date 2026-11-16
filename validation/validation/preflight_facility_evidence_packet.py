"""C-only preflight inventory of review packet metadata. NO official source verification.

Reads explicitly supplied record metadata (not original bytes or human signatures).
Reports missing/conflicting prerequisites *before* S1 real facility use. Never
turns metadata, names, hashes or a claimed reviewer into safety/public approval.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = "hinanex.c.facility_evidence_packet_preflight.v0.1"
REPORT_SCHEMA = "hinanex.c.facility_evidence_gaps.v0.1"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9._:-]{1,96}\Z")
PENDING = {"unknown", "unverified", "pending", "tbd", "not_found", "not_applicable"}
DISPOSITIONS = {"UNREVIEWED", "CONFLICTING", "DOCUMENTED_PENDING_AUTHENTICATION"}
SOURCE_KEYS = frozenset((
    "url", "publisher", "raw_sha256", "c_raw_audit_sha256",
    "captured_at_utc", "source_revision", "source_record_locator",
))
IDENTITY_KEYS = frozenset((
    "target_source_url", "target_raw_sha256", "target_c_raw_audit_sha256",
    "target_captured_at_utc", "target_source_revision", "target_record_locator",
    "bound_source_sha256", "independent_pair_review_ref", "disposition",
))
HAZARD_KEYS = frozenset((
    "raw_marker", "official_meaning_ref", "reviewed_hazard",
    "bound_source_sha256", "independent_review_ref", "disposition",
))
REUSE_KEYS = frozenset((
    "terms_url", "attribution_text", "exception_check_ref",
    "bound_source_sha256", "independent_review_ref", "disposition",
))
CASE_KEYS = frozenset((
    "case_id", "hazard", "requested_asof", "asof_evidence_ref",
    "source", "identity", "hazard_meaning", "reuse",
))
GROUPS = {
    "source": SOURCE_KEYS,
    "identity": IDENTITY_KEYS,
    "hazard_meaning": HAZARD_KEYS,
    "reuse": REUSE_KEYS,
}
FIELDS = {
    "source": {
        "url": "SOURCE_URL_MISSING", "publisher": "SOURCE_PUBLISHER_MISSING",
        "raw_sha256": "SOURCE_RAW_SHA_MISSING",
        "c_raw_audit_sha256": "SOURCE_C_BYTE_AUDIT_MISSING",
        "captured_at_utc": "SOURCE_CAPTURE_TIME_MISSING",
        "source_revision": "SOURCE_REVISION_MISSING",
        "source_record_locator": "SOURCE_ROW_LOCATOR_MISSING",
    },
    "identity": {
        "target_source_url": "IDENTITY_TARGET_URL_MISSING",
        "target_raw_sha256": "IDENTITY_TARGET_RAW_SHA_MISSING",
        "target_c_raw_audit_sha256": "IDENTITY_TARGET_C_BYTE_AUDIT_MISSING",
        "target_captured_at_utc": "IDENTITY_TARGET_CAPTURE_TIME_MISSING",
        "target_source_revision": "IDENTITY_TARGET_REVISION_MISSING",
        "target_record_locator": "IDENTITY_TARGET_ROW_LOCATOR_MISSING",
        "bound_source_sha256": "IDENTITY_SOURCE_BINDING_MISSING",
        "independent_pair_review_ref": "IDENTITY_INDEPENDENT_PAIR_REVIEW_MISSING",
    },
    "hazard_meaning": {
        "raw_marker": "HAZARD_ORIGINAL_MARKER_MISSING",
        "official_meaning_ref": "HAZARD_OFFICIAL_MEANING_EVIDENCE_MISSING",
        "reviewed_hazard": "HAZARD_REVIEW_SCOPE_MISSING",
        "bound_source_sha256": "HAZARD_SOURCE_BINDING_MISSING",
        "independent_review_ref": "HAZARD_INDEPENDENT_REVIEW_MISSING",
    },
    "reuse": {
        "terms_url": "REUSE_TERMS_URL_MISSING",
        "attribution_text": "REUSE_CREDIT_TEXT_MISSING",
        "exception_check_ref": "REUSE_EXCEPTION_CHECK_MISSING",
        "bound_source_sha256": "REUSE_SOURCE_BINDING_MISSING",
        "independent_review_ref": "REUSE_INDEPENDENT_REVIEW_MISSING",
    },
}


class PacketInputError(ValueError):
    """A structurally untrustworthy packet must not be treated as an empty review."""


def _text(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and
            value.strip().lower() not in PENDING)


def _https(value: object) -> bool:
    if not _text(value) or any(c.isspace() for c in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and bool(u.hostname) and
                not u.username and not u.password and not u.fragment and
                u.port in (None, 443))
    except ValueError:
        return False


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(DIGEST.fullmatch(value))


def _utc(value: object) -> bool:
    if not _text(value):
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.tzinfo is not None and dt.utcoffset() == timedelta(0)
    except (ValueError, OverflowError):
        return False


def _validate_shape(packet: object) -> list[dict]:
    if (not isinstance(packet, dict) or set(packet) !=
            {"schema_id", "records"} or packet["schema_id"] != SCHEMA):
        raise PacketInputError("wrong or unexpected packet schema/fields")
    records = packet["records"]
    if not isinstance(records, list) or not records:
        raise PacketInputError("non-empty record list required")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != CASE_KEYS:
            raise PacketInputError("unexpected case fields; real-world claims not permitted")
        rid = record["case_id"]
        if not isinstance(rid, str) or not IDENTIFIER.fullmatch(rid) or rid in seen:
            raise PacketInputError("case ID invalid or duplicate")
        seen.add(rid)
        for field in ("hazard", "requested_asof", "asof_evidence_ref"):
            if record[field] is not None and not isinstance(record[field], str):
                raise PacketInputError(f"invalid case field type: {field}")
        for group, keys in GROUPS.items():
            item = record[group]
            if not isinstance(item, dict) or set(item) != keys:
                raise PacketInputError(f"unexpected or missing {group} fields")
            for key, value in item.items():
                if value is not None and not isinstance(value, str):
                    raise PacketInputError(f"invalid {group}.{key} type")
            disposition = item.get("disposition")
            if "disposition" in keys and disposition not in DISPOSITIONS:
                raise PacketInputError(f"unsupported {group} disposition")
    return records


def _missing(group: dict, keys: dict[str, str]) -> list[str]:
    return [code for field, code in keys.items() if not _text(group[field])]


def _detect(record: dict) -> dict[str, list[str]]:
    issues = {key: _missing(record[key], FIELDS[key]) for key in GROUPS}
    source, identity = record["source"], record["identity"]
    hazard, reuse = record["hazard_meaning"], record["reuse"]

    if not _text(record["hazard"]):
        issues["hazard_meaning"].append("REQUEST_HAZARD_MISSING")
    if not _utc(record["requested_asof"]):
        issues["source"].append("REQUEST_ASOF_MISSING_OR_INVALID_UTC")
    if not _text(record["asof_evidence_ref"]):
        issues["source"].append("SOURCE_ASOF_EVIDENCE_MISSING")
    for field in ("url",):
        if _text(source[field]) and not _https(source[field]):
            issues["source"].append("SOURCE_URL_NOT_HTTPS")
    if _text(identity["target_source_url"]) and not _https(identity["target_source_url"]):
        issues["identity"].append("IDENTITY_TARGET_URL_NOT_HTTPS")
    if _text(reuse["terms_url"]) and not _https(reuse["terms_url"]):
        issues["reuse"].append("REUSE_TERMS_URL_NOT_HTTPS")

    for group, fields in (
        ("source", ("raw_sha256", "c_raw_audit_sha256")),
        ("identity", ("target_raw_sha256", "target_c_raw_audit_sha256", "bound_source_sha256")),
        ("hazard_meaning", ("bound_source_sha256",)),
        ("reuse", ("bound_source_sha256",)),
    ):
        for field in fields:
            if _text(record[group][field]) and not _sha(record[group][field]):
                issues[group].append(f"{group.upper()}_{field.upper()}_INVALID_SHA")
    for group, fields in (("source", ("captured_at_utc",)),
                           ("identity", ("target_captured_at_utc",))):
        for field in fields:
            if _text(record[group][field]) and not _utc(record[group][field]):
                issues[group].append(f"{group.upper()}_CAPTURE_TIME_NOT_UTC")

    if _sha(source["raw_sha256"]) and _sha(source["c_raw_audit_sha256"]) and (
            source["raw_sha256"] != source["c_raw_audit_sha256"]):
        issues["source"].append("SOURCE_RAW_AUDIT_SHA_MISMATCH")
    if _sha(identity["target_raw_sha256"]) and _sha(identity["target_c_raw_audit_sha256"]) and (
            identity["target_raw_sha256"] != identity["target_c_raw_audit_sha256"]):
        issues["identity"].append("IDENTITY_TARGET_RAW_AUDIT_SHA_MISMATCH")
    for group in ("identity", "hazard_meaning", "reuse"):
        if _sha(source["raw_sha256"]) and _sha(record[group]["bound_source_sha256"]) and (
                source["raw_sha256"] != record[group]["bound_source_sha256"]):
            issues[group].append(f"{group.upper()}_SOURCE_REVISION_BINDING_MISMATCH")

    if _text(record["hazard"]) and _text(hazard["reviewed_hazard"]) and (
            record["hazard"] != hazard["reviewed_hazard"]):
        issues["hazard_meaning"].append("HAZARD_SCOPE_MISMATCH")
    for group in ("identity", "hazard_meaning", "reuse"):
        if record[group]["disposition"] == "CONFLICTING":
            issues[group].append(f"{group.upper()}_EVIDENCE_CONFLICT")
        elif record[group]["disposition"] == "UNREVIEWED":
            issues[group].append(f"{group.upper()}_INDEPENDENT_REVIEW_UNRESOLVED")
    return {group: sorted(set(codes)) for group, codes in issues.items()}


def preflight(packet: object) -> dict:
    """Gap inventory only. Complete metadata is NOT authenticated human review."""
    records = _validate_shape(packet)
    rows = []
    for record in records:
        groups = _detect(record)
        missing = [code for codes in groups.values() for code in codes]
        rows.append({
            "case_id": record["case_id"],
            "status": ("PACKET_FIELDS_PRESENT__HUMAN_AUDIT_REQUIRED" if not missing
                       else "HOLD_MISSING_CONFLICTING_OR_UNREVIEWED"),
            "reason_codes": sorted(missing),
            "reason_codes_by_area": groups,
        })
    any_hold = any(x["reason_codes"] for x in rows)
    return {
        "schema_id": REPORT_SCHEMA,
        "status": ("HOLD__NO_REAL_DATA_ADOPTION" if any_hold else
                   "PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED"),
        "records_checked": len(rows),
        "records_with_gaps": sum(bool(x["reason_codes"]) for x in rows),
        "rows": rows,
        "source_original_bytes_verified_by_this_run": False,
        "identity_pairs_approved": 0,
        "official_hazard_semantics_approved": False,
        "license_and_publication_approved": False,
        "eligible_for_s1_real_facilities": False,
        "safe_route_verified": False,
        "facility_open_now_verified": False,
        "human_independent_review_required": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only C facility evidence gap preflight")
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = preflight(json.loads(args.packet.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"C_PACKET_INVALID__NO_APPROVAL: {type(exc).__name__}: {exc}")
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f'{report["status"]}: {report["records_with_gaps"]}/{report["records_checked"]} with gaps')
        for row in report["rows"]:
            print(f'  {row["case_id"]}: {", ".join(row["reason_codes"]) or "META_FIELDS_PRESENT__NOT_APPROVED"}')
    # Incomplete input never exits cleanly; complete metadata is only a
    # checkable packet, NOT permission to use a real facility record.
    return 2 if report["records_with_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
