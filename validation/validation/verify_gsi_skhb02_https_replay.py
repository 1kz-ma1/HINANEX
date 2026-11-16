"""C independent HTTPS-byte replay for one GSI skhb02 z10 tile.

No D code import, no D-generated normalizations, no municipality inference,
and no public catalog. Compare user-supplied archived bytes + D receipt
against a separate, direct GSI HTTPS GET. A byte match is C technical
evidence only, NEVER official legal/site/publication approval.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import socket
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener,
)

from verify_gsi_skhb02_archive import point_tile

SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
TILE = {"z": 10, "x": 909, "y": 403}
MAX_BYTES = 12_000_000
EXPECTED_HAZARD = "GSI_SKHB02_LANDSLIDE"


class ReplayBlocked(ValueError):
    """Expected fail-closed reason, never proof of zero facilities."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReplayBlocked(f"REDIRECT_REFUSED:{code}")


def _no_dup_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ReplayBlocked("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def _reject_non_json(value):
    raise ReplayBlocked("NON_JSON_CONSTANT")


def inspect_raw(raw: bytes) -> tuple[str, int]:
    """C-owned independent full feature inspection; not facility acceptance."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ReplayBlocked("RAW_INVALID_OR_OVERSIZED")
    digest = sha256(raw).hexdigest()
    try:
        doc = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_dup_keys,
            parse_constant=_reject_non_json,
        )
    except (UnicodeError, ValueError) as exc:
        raise ReplayBlocked("RAW_GEOJSON_INVALID") from exc
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise ReplayBlocked("NOT_FEATURE_COLLECTION")
    features = doc.get("features")
    if not isinstance(features, list) or len(features) > 50000:
        raise ReplayBlocked("FEATURES_INVALID")
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ReplayBlocked(f"INVALID_FEATURE:{i}")
        props = feature.get("properties")
        geom = feature.get("geometry")
        if not isinstance(props, dict) or not isinstance(geom, dict):
            raise ReplayBlocked(f"INVALID_FEATURE_SHAPE:{i}")
        if type(props.get("disaster2")) is not int or props["disaster2"] != 1:
            raise ReplayBlocked(f"INVALID_LANDSLIDE_MARKER:{i}")
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            raise ReplayBlocked(f"INVALID_FEATURE_NAME:{i}")
        if any(props.get(k) is not None and not isinstance(props[k], str)
               for k in ("address", "remarks")):
            raise ReplayBlocked(f"INVALID_FEATURE_TEXT:{i}")
        if geom.get("type") != "Point":
            raise ReplayBlocked(f"INVALID_GEOMETRY:{i}")
        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) not in (2, 3):
            raise ReplayBlocked(f"INVALID_COORDINATES:{i}")
        lon, lat = coords[:2]
        if (type(lon) not in (int, float) or type(lat) not in (int, float)
                or not isfinite(lon) or not isfinite(lat)):
            raise ReplayBlocked(f"INVALID_POINT:{i}")
        try:
            if point_tile(lon, lat) != (909, 403):
                raise ReplayBlocked(f"FEATURE_OUTSIDE_TILE:{i}")
        except (OverflowError, ValueError, TypeError) as exc:
            raise ReplayBlocked(f"INVALID_POINT:{i}") from exc
        if len(coords) == 3 and (
            type(coords[2]) not in (int, float) or not isfinite(coords[2])
        ):
            raise ReplayBlocked(f"INVALID_ALTITUDE:{i}")
    return digest, len(features)


def validate_d_receipt(receipt: dict, raw: bytes, digest: str, count: int) -> None:
    if not isinstance(receipt, dict):
        raise ReplayBlocked("D_RECEIPT_INVALID")
    expected = {
        "source_url": SOURCE,
        "response_final_url": SOURCE,
        "hazard": "landslide",
        "hazard_dataset": EXPECTED_HAZARD,
        "expected_hazard_attribute": "disaster2",
        "tile": TILE,
        "status": "H0_LOCAL_STRUCTURE_ONLY" if count else "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF",
        "source_sha256": digest,
        "source_bytes": len(raw),
        "archive_feature_count": count,
        "http_status": 200,
        "acquisition_status": "LOCAL_ARCHIVE_RECEIVED",
        "acquisition_method": "DIRECT_OFFICIAL_HTTPS_GET",
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "official_https_byte_replay": "NOT_RUN",
        "independent_c_acceptance": "NOT_GRANTED",
        "publication_approval": "NOT_GRANTED",
    }
    for key, value in expected.items():
        if type(receipt.get(key)) is not type(value) or receipt[key] != value:
            raise ReplayBlocked("D_RECEIPT_MISMATCH:" + key)
    when = receipt.get("retrieved_at_utc")
    if not isinstance(when, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", when
    ):
        raise ReplayBlocked("D_RETRIEVAL_TIME_INVALID")
    try:
        instant = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayBlocked("D_RETRIEVAL_TIME_INVALID") from exc
    if instant.utcoffset() != timedelta(0):
        raise ReplayBlocked("D_RETRIEVAL_TIME_NOT_UTC")


def direct_official_get() -> tuple[bytes, int, str]:
    """Deliberately bypass environment proxy; reject any redirected response."""
    opener = build_opener(
        ProxyHandler({}), _NoRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    request = Request(
        SOURCE, method="GET", headers={
            "Accept": "application/geo+json, application/json, */*",
            "Cache-Control": "no-cache",
            "User-Agent": "HINANEX-C-independent-replay/1.0",
        },
    )
    try:
        with opener.open(request, timeout=25) as res:
            return res.read(MAX_BYTES + 1), res.status, res.geturl()
    except HTTPError as exc:
        raise ReplayBlocked(f"HTTP_ERROR:{exc.code}") from None
    except (URLError, TimeoutError, socket.gaierror, ssl.SSLError, OSError) as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc
        if isinstance(reason, socket.gaierror):
            code = "DNS_FAILURE"
        elif isinstance(reason, (TimeoutError, socket.timeout)):
            code = "CONNECTION_TIMEOUT"
        elif isinstance(reason, ssl.SSLError):
            code = "TLS_FAILURE"
        else:
            code = "NETWORK_FAILURE"
        raise ReplayBlocked(code) from None


def verify_independent_replay(
    raw: bytes,
    receipt: dict,
    *,
    transport=direct_official_get,
    clock=lambda: datetime.now(timezone.utc),
) -> dict:
    """No C approval is granted, including when raw source bytes match."""
    old_hash, old_count = inspect_raw(raw)
    validate_d_receipt(receipt, raw, old_hash, old_count)
    new_raw, http_status, final_url = transport()
    if type(http_status) is not int or http_status != 200:
        raise ReplayBlocked("REPLAY_HTTP_NOT_200")
    if final_url != SOURCE:
        raise ReplayBlocked("REPLAY_FINAL_URL_MISMATCH")
    new_hash, new_count = inspect_raw(new_raw)
    now = clock()
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ReplayBlocked("C_CLOCK_MUST_BE_UTC")
    matched = raw == new_raw
    return {
        "status": ("C_HTTPS_BYTE_MATCH_UNAPPROVED" if matched
                   else "C_SOURCE_CHANGED_OR_MISMATCH_HOLD"),
        "source_url": SOURCE,
        "hazard": "landslide",
        "hazard_dataset": EXPECTED_HAZARD,
        "tile": TILE,
        "c_checked_at_utc": now.isoformat(timespec="seconds"),
        "d_claimed_retrieved_at_utc": receipt["retrieved_at_utc"],
        "d_archived_sha256_recomputed": old_hash,
        "d_archived_bytes": len(raw),
        "d_archived_tile_feature_count": old_count,
        "c_replayed_sha256": new_hash,
        "c_replayed_bytes": len(new_raw),
        "c_replayed_tile_feature_count": new_count,
        "c_http_status_observed": http_status,
        "c_response_final_url_observed": final_url,
        "same_bytes": matched,
        "independent_https_byte_replay": "MATCH" if matched else "DIFFERENT",
        "origin_certification": "HTTPS_TRANSPORT_ONLY_NO_SIGNED_SOURCE",
        "independent_c_approved": False,
        "municipal_coverage_verified": False,
        "facility_identity_approved": False,
        "current_open_status_verified": False,
        "hazard_safety_verified": False,
        "publication_approved": False,
        "note": ("A raw-byte match is NOT municipality/site/safety/publication approval. "
                 "If bytes differ, determine revision vs capture or transport mismatch "
                 "with new evidence; never silently accept the old audit."),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--d-receipt", type=Path, required=True)
    p.add_argument("--report-out", type=Path)
    args = p.parse_args()
    try:
        if args.report_out is not None and args.report_out.exists():
            raise ReplayBlocked("REPORT_ALREADY_EXISTS")
        if args.raw.stat().st_size > MAX_BYTES:
            raise ReplayBlocked("ARCHIVE_TOO_LARGE")
        receipt = json.loads(args.d_receipt.read_text(encoding="utf-8"))
        result = verify_independent_replay(args.raw.read_bytes(), receipt)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report_out is not None:
            with args.report_out.open("x", encoding="utf-8") as stream:
                stream.write(output)
        print(output, end="")
        return 0 if result["same_bytes"] else 3
    except (OSError, ValueError, TypeError) as exc:
        print("C_H0_REPLAY_HOLD: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
