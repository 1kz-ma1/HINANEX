"""C-independent verification of an A skhb02 local acquisition *claim*.

Recompute source bytes, A per-feature report and acquisition manifest fields
without trusting either JSON. A matching chain remains UNAPPROVED: it does NOT
cryptographically authenticate the HTTPS response or the human reviewer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from verify_gsi_skhb02_archive import tile, verify_archived_skhb02

EXPECTED_KEYS = frozenset({
    "capture_kind", "official_tile_url_requested", "source_host",
    "captured_at_utc", "raw_sha256", "raw_byte_count", "source_tile",
    "feature_count_tile_only", "http_status_observed",
    "response_final_url_observed", "content_type_observed",
    "etag_observed", "last_modified_observed",
    "official_municipal_publication_date_verified",
    "official_dataset_update_date_verified",
    "response_headers_are_not_publication_dates",
    "independent_https_origin_replay_passed",
    "independent_c_approved", "human_approved", "publishable",
})
MAX_SOURCE_BYTES = 12_000_000


def _exact(value, expected, key):
    # Do not equate False with 0 or an integer with a string.
    if type(value) is not type(expected) or value != expected:
        raise ValueError("C_CAPTURE_MANIFEST_MISMATCH:" + key)


def _observed_header(value, key):
    if value is None:
        return
    if (not isinstance(value, str) or len(value) > 1024
            or any(c in value for c in ("\r", "\n", "\x00"))):
        raise ValueError("C_INVALID_CAPTURE_HEADER:" + key)


def verify_local_capture_chain(
    raw: bytes,
    source_url: str,
    a_report: dict,
    manifest: dict,
    *,
    checked_at: datetime | None = None,
) -> dict:
    """Check local equality only; never infer official origin/authenticity."""
    c = verify_archived_skhb02(raw, source_url, a_report)
    if not isinstance(manifest, dict) or set(manifest) != EXPECTED_KEYS:
        raise ValueError("C_CAPTURE_MANIFEST_FIELDS_MISMATCH")
    x, y = tile(source_url)
    fixed = {
        "capture_kind": "A_GSI_SKHB02_UNREVIEWED",
        "official_tile_url_requested": source_url,
        "source_host": "cyberjapandata.gsi.go.jp",
        "raw_sha256": sha256(raw).hexdigest(),
        "raw_byte_count": len(raw),
        "source_tile": {"z": 10, "x": x, "y": y},
        "feature_count_tile_only": c["tile_wide_feature_count"],
        "http_status_observed": 200,
        "response_final_url_observed": source_url,
        "official_municipal_publication_date_verified": None,
        "official_dataset_update_date_verified": None,
        "response_headers_are_not_publication_dates": True,
        "independent_https_origin_replay_passed": False,
        "independent_c_approved": False,
        "human_approved": False,
        "publishable": False,
    }
    for key, value in fixed.items():
        _exact(manifest[key], value, key)

    for key in ("content_type_observed", "etag_observed", "last_modified_observed"):
        _observed_header(manifest[key], key)

    recorded_at = manifest["captured_at_utc"]
    if not isinstance(recorded_at, str):
        raise ValueError("C_CAPTURE_TIME_INVALID")
    try:
        moment = datetime.fromisoformat(recorded_at)
    except ValueError as exc:
        raise ValueError("C_CAPTURE_TIME_INVALID") from exc
    if moment.utcoffset() is None:
        raise ValueError("C_CAPTURE_TIME_WITHOUT_ZONE")

    now = checked_at if checked_at is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("C_CHECK_CLOCK_WITHOUT_ZONE")
    if moment > now + timedelta(minutes=5):
        raise ValueError("C_CAPTURE_TIME_IN_FUTURE")

    return {
        "status": "C_LOCAL_CAPTURE_CHAIN_MATCH_UNAPPROVED"
        if c["tile_wide_feature_count"] else "C_EMPTY_TILE_COVERAGE_UNKNOWN",
        "audit_scope": "LOCAL_RAW_AND_TWO_UNTRUSTED_REPORTS_ONLY",
        "source_url": source_url,
        "raw_sha256_recomputed": c["raw_sha256"],
        "source_feature_count_tile_only": c["tile_wide_feature_count"],
        "captured_at_claimed": recorded_at,
        "acquisition_headers_independently_authenticated": False,
        "official_https_origin_authenticated": False,
        "municipal_coverage_verified": False,
        "independent_human_approved": False,
        "published_for_disaster_use": False,
        "approved_safe_destinations": 0,
        "reason_codes": [
            "ACQUISITION_MANIFEST_SELF_REPORTED",
            "INDEPENDENT_OFFICIAL_HTTPS_REPLAY_NOT_DONE",
            "HUMAN_C_SOURCE_REVIEW_NOT_DONE",
            "MUNICIPAL_SCOPE_AND_UPDATE_DATE_NOT_VERIFIED",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--a-report", type=Path, required=True)
    ap.add_argument("--capture-manifest", type=Path, required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--report-out", type=Path)
    args = ap.parse_args()
    try:
        if args.report_out is not None and args.report_out.exists():
            raise ValueError("C_REPORT_ALREADY_EXISTS")
        if not args.raw.is_file() or not 0 < args.raw.stat().st_size <= MAX_SOURCE_BYTES:
            raise ValueError("C_RAW_ARCHIVE_SIZE_INVALID")
        result = verify_local_capture_chain(
            args.raw.read_bytes(), args.source_url,
            json.loads(args.a_report.read_text(encoding="utf-8")),
            json.loads(args.capture_manifest.read_text(encoding="utf-8")),
        )
        printed = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report_out is not None:
            with args.report_out.open("x", encoding="utf-8") as destination:
                destination.write(printed)
        print(printed, end="")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print("C skhb02 capture chain BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
