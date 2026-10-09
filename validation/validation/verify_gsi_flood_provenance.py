"""Independent HTTPS byte-replay provenance check for an archived GSI flood tile.

A C raw-row PASS alone proves only agreement between local files.
This check fetches the *same* official HTTPS URL again, compares bytes and ties
them to C's independent raw acceptance. It does not prove municipality
membership, completeness, live opening, route safety or historical origin.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_MAX_BYTES = 16 * 1024 * 1024
_TILE_PATH = re.compile(r"^/xyz/skhb01/(\d+)/(\d+)/(\d+)\.geojson$")


def _official_tile_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    if (
        parsed.scheme != "https" or parsed.netloc != "cyberjapandata.gsi.go.jp"
        or parsed.params or parsed.query or parsed.fragment
    ):
        return False
    match = _TILE_PATH.fullmatch(parsed.path)
    if not match:
        return False
    z, x, y = map(int, match.groups())
    return 0 <= z <= 20 and x < 2 ** z and y < 2 ** z


def verify_https_provenance(
    raw_archive: bytes, source_url: str, c_acceptance: dict, *, opener=urlopen
) -> dict:
    """Return MATCH only when official HTTPS bytes equal the C-accepted raw."""
    if not _official_tile_url(source_url):
        raise ValueError("source URL must be an exact GSI skhb01 flood tile HTTPS URL")
    if not isinstance(raw_archive, bytes) or not 0 < len(raw_archive) <= _MAX_BYTES:
        raise ValueError("local archived bytes are missing or exceed size cap")
    if not isinstance(c_acceptance, dict):
        raise ValueError("independent C acceptance JSON is required")
    digest = sha256(raw_archive).hexdigest()
    try:
        parsed = json.loads(raw_archive)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid archived GeoJSON") from exc
    if (
        not isinstance(parsed, dict) or parsed.get("type") != "FeatureCollection"
        or not isinstance(parsed.get("features"), list) or not parsed["features"]
    ):
        raise ValueError("archive lacks a nonempty FeatureCollection")
    expected_ids = [
        f"{source_url}#feature_index={i}" for i in range(len(parsed["features"]))
    ]
    if (
        c_acceptance.get("status") != "PASS"
        or c_acceptance.get("source_raw_sha256") != digest
        or c_acceptance.get("hazard_dataset") != "GSI_SKHB01_FLOOD"
        or c_acceptance.get("accepted_source_feature_keys") != expected_ids
        or not isinstance(c_acceptance.get("audit_reference"), str)
        or not c_acceptance["audit_reference"].strip()
        or c_acceptance.get("search_context_region_code") not in ("13123", "15100", "23100")
    ):
        raise ValueError("C independent raw-acceptance evidence does not match archive")

    # No automatic cross-host redirect may be treated as an official response.
    request = Request(
        source_url,
        headers={"Accept": "application/geo+json, application/json, */*;q=0.1",
                 "Cache-Control": "no-cache",
                 "User-Agent": "HINANEX-C-GSI-Source-Verification/1.0"},
    )
    with opener(request, timeout=30) as response:
        status = response.getcode()
        final_url = response.geturl()
        headers = {
            key: response.headers.get(key)
            for key in ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Date")
        }
        remote = response.read(_MAX_BYTES + 1)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if status != 200 or final_url != source_url:
        raise ValueError("official HTTPS response was not 200 at the exact original URL")
    if not remote or len(remote) > _MAX_BYTES:
        raise ValueError("remote GSI response empty or exceeded size cap")
    remote_digest = sha256(remote).hexdigest()
    if remote != raw_archive:
        raise ValueError("official HTTPS bytes differ from archived C-accepted bytes")
    return {
        "verification_kind": "GSI_SKHB01_FLOOD_HTTPS_BYTE_REPLAY",
        "status": "MATCH",
        "source_url": source_url,
        "response_final_url": final_url,
        "retrieved_at_utc": fetched_at,
        "http_status": status,
        "archive_sha256": digest,
        "download_sha256": remote_digest,
        "bytes": len(remote),
        "c_audit_reference": c_acceptance["audit_reference"],
        "c_search_context_region_code": c_acceptance["search_context_region_code"],
        "feature_count": len(expected_ids),
        "response_headers": headers,
        "limitations": [
            "Only this exact GSI tile was compared with the server at the retrieval time.",
            "A byte match cannot prove when the earlier local download occurred.",
            "Feature count is tile-wide, not the municipality's shelter count.",
            "Does not verify municipal membership, completeness, suitability, opening, or safe routing.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--c-acceptance", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        # Existing evidence is never silently overwritten by a later check.
        if args.report_out.exists():
            raise ValueError("report path already exists; choose a new evidence filename")
        result = verify_https_provenance(
            args.raw.read_bytes(), args.source_url,
            json.loads(args.c_acceptance.read_text(encoding="utf-8")),
        )
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        with args.report_out.open("x", encoding="utf-8") as destination:
            json.dump(result, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
    except (ValueError, OSError, URLError, HTTPError, json.JSONDecodeError) as exc:
        print(f"C HTTPS provenance NOT VERIFIED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(f"C HTTPS provenance MATCH: {result['feature_count']} tile records / {result['archive_sha256']}")


if __name__ == "__main__":
    main()
