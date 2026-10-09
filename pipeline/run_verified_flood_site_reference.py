"""Build a reference-only GSI catalog after independent C and HTTPS checks.

No network access or municipality/geocoding inference. Requires a *separate*
C HTTPS byte-replay evidence report in addition to C raw-row acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from src.hinanex.flood_site_reference import build_flood_site_catalog


def require_provenance(raw: bytes, records: list[dict], acceptance: dict,
                       evidence: dict, region_code: str) -> None:
    """Fail closed unless the exact archived C-approved tile was replayed."""
    if (
        not isinstance(raw, bytes) or not isinstance(records, list)
        or not records or not isinstance(acceptance, dict)
        or not isinstance(evidence, dict)
    ):
        raise ValueError("archive, normalized rows, C PASS and HTTPS report required")
    digest = sha256(raw).hexdigest()
    source = records[0].get("source_url") if isinstance(records[0], dict) else None
    checks = {
        "verification_kind": "GSI_SKHB01_FLOOD_HTTPS_BYTE_REPLAY",
        "status": "MATCH",
        "source_url": source,
        "response_final_url": source,
        "http_status": 200,
        "archive_sha256": digest,
        "download_sha256": digest,
        "bytes": len(raw),
        "c_audit_reference": acceptance.get("audit_reference"),
        "c_search_context_region_code": region_code,
        "feature_count": len(records),
    }
    try:
        checked_at = datetime.fromisoformat(evidence.get("retrieved_at_utc", ""))
    except (ValueError, TypeError):
        raise ValueError("HTTPS provenance retrieval timestamp invalid")
    if checked_at.tzinfo is None or checked_at.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("HTTPS provenance timestamp must be UTC")
    if (
        type(evidence.get("http_status")) is not int
        or type(evidence.get("bytes")) is not int
        or type(evidence.get("feature_count")) is not int
        or not isinstance(source, str)
        or not source.startswith("https://cyberjapandata.gsi.go.jp/xyz/skhb01/")
        or not isinstance(evidence.get("retrieved_at_utc"), str)
        or not evidence["retrieved_at_utc"]
        or acceptance.get("status") != "PASS"
        or acceptance.get("source_raw_sha256") != digest
        or acceptance.get("search_context_region_code") != region_code
        or not acceptance.get("audit_reference")
        or any(evidence.get(k) != v for k, v in checks.items())
    ):
        raise ValueError("official HTTPS provenance missing or inconsistent with C-accepted source")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, choices=["13123", "15100", "23100"])
    parser.add_argument("--raw", type=Path, required=True, help="Archived GSI skhb01 GeoJSON bytes")
    parser.add_argument("--records", type=Path, required=True, help="A/C-audited normalized records JSON list")
    parser.add_argument("--c-acceptance", type=Path, required=True, help="C independently generated PASS JSON")
    parser.add_argument("--provenance", type=Path, required=True, help="C official HTTPS byte-replay MATCH report")
    parser.add_argument("--out", type=Path, required=True, help="Additive reference catalog JSON; do not serve stale results")
    args = parser.parse_args()

    raw = args.raw.read_bytes()
    records = json.loads(args.records.read_text(encoding="utf-8"))
    acceptance = json.loads(args.c_acceptance.read_text(encoding="utf-8"))
    evidence = json.loads(args.provenance.read_text(encoding="utf-8"))
    require_provenance(raw, records, acceptance, evidence, args.region)
    data = build_flood_site_catalog(
        args.region,
        records,
        raw_archive=raw,
        c_acceptance=acceptance,
    )
    if data["status"] != "REFERENCE_ONLY":
        raise ValueError("cannot publish reference catalog without full C acceptance")
    data["https_provenance_status"] = "MATCH"
    data["https_provenance_checked_at_utc"] = evidence["retrieved_at_utc"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.region}: {data['status']} / {len(data['sites'])} reference-only records -> {args.out}")


if __name__ == "__main__":
    main()
