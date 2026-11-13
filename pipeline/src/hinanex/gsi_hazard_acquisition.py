"""Explicit one-tile GSI HTTPS acquisition for H0, never a publication gate.

Only a direct, non-redirected TLS GET to the exact hazard-specific official URL
is allowed. Validated raw is saved locally outside this repository, never to Git.
A successful receipt does not replace C independent byte replay or authorization.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener,
)

from src.hinanex.gsi_hazard_preflight import (
    _MAX_BYTES, _check_url, preflight_gsi_tile,
)


class AcquisitionFailure(ValueError):
    def __init__(self, category: str, *, http_status: int | None = None):
        super().__init__(category)
        self.category = category
        self.http_status = http_status


@dataclass(frozen=True)
class TransportResult:
    raw: bytes
    http_status: int
    final_url: str
    content_type: str | None
    etag: str | None
    last_modified: str | None


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionFailure("REDIRECT_REFUSED", http_status=code)


def _direct_https_get(source_url: str) -> TransportResult:
    # Do not honor ambient HTTP_PROXY that could route raw through another host.
    opener = build_opener(
        ProxyHandler({}), _RejectRedirects(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    request = Request(
        source_url, method="GET", headers={
            "Accept": "application/geo+json, application/json, */*",
            "Cache-Control": "no-cache",
            "User-Agent": "HINANEX-H0-research-only/1.0",
        },
    )
    try:
        with opener.open(request, timeout=25) as response:
            body = response.read(_MAX_BYTES + 1)
            return TransportResult(
                raw=body,
                http_status=response.status,
                final_url=response.geturl(),
                content_type=response.headers.get("Content-Type"),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
    except HTTPError as exc:
        raise AcquisitionFailure("HTTP_ERROR", http_status=exc.code) from None
    except (URLError, socket.gaierror, TimeoutError, ssl.SSLError, OSError) as exc:
        if isinstance(exc, URLError):
            reason = exc.reason
        else:
            reason = exc
        if isinstance(reason, socket.gaierror):
            category = "DNS_FAILURE"
        elif isinstance(reason, (TimeoutError, socket.timeout)):
            category = "CONNECTION_TIMEOUT"
        elif isinstance(reason, ssl.SSLError):
            category = "TLS_FAILURE"
        else:
            category = "NETWORK_FAILURE"
        raise AcquisitionFailure(category) from None


def _output_paths(raw_out: Path) -> tuple[Path, Path]:
    if not isinstance(raw_out, Path) or not raw_out.is_absolute():
        raise ValueError("raw output must be an absolute external path")
    if raw_out.suffix != ".geojson":
        raise ValueError("raw output filename must end in .geojson")
    raw_path = raw_out.resolve(strict=False)
    repo_root = Path(__file__).resolve().parents[3]
    if raw_path.is_relative_to(repo_root):
        raise ValueError("raw output must be outside the Git repository")
    if not raw_path.parent.is_dir():
        raise ValueError("raw output parent directory must already exist")
    receipt_path = raw_path.with_suffix(".receipt.json")
    if raw_path.exists() or receipt_path.exists():
        raise ValueError("refusing to overwrite prior raw evidence or receipt")
    return raw_path, receipt_path


def _write_new_private(path: Path, data: bytes) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as dest:
        dest.write(data)
        dest.flush()
        os.fsync(dest.fileno())


def acquire_one_tile(
    *,
    hazard: str,
    source_url: str,
    raw_out: Path,
    transport=_direct_https_get,
    now=lambda: datetime.now(timezone.utc),
) -> dict:
    """Download and preflight exactly one official tile, fail closed.

    Tests inject a synthetic transport and a fixed clock. The default transport
    only opens an explicitly allowlisted GSI HTTPS URL, rejects redirects and
    caps body size before it can write any raw data to disk.
    """
    _check_url(source_url, hazard)
    raw_path, receipt_path = _output_paths(raw_out)
    response = transport(source_url)
    if not isinstance(response, TransportResult):
        raise AcquisitionFailure("UNVERIFIED_TRANSPORT")
    if type(response.http_status) is not int or response.http_status != 200:
        raise AcquisitionFailure("HTTP_ERROR", http_status=response.http_status)
    if response.final_url != source_url:
        raise AcquisitionFailure("SOURCE_URL_MISMATCH")
    if not isinstance(response.raw, bytes) or len(response.raw) > _MAX_BYTES:
        raise AcquisitionFailure("OVERSIZE_OR_INVALID_BODY")
    observed_at = now()
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise AcquisitionFailure("CLOCK_IS_NOT_TIMEZONE_AWARE")
    if observed_at.utcoffset() != timezone.utc.utcoffset(None):
        raise AcquisitionFailure("CLOCK_MUST_BE_UTC")
    retrieved_at = observed_at.isoformat(timespec="seconds")
    digest = sha256(response.raw).hexdigest()
    try:
        result = preflight_gsi_tile(
            response.raw,
            source_url=source_url,
            hazard=hazard,
            expected_sha256=digest,
            retrieved_at_utc=retrieved_at,
        )
    except ValueError as exc:
        raise AcquisitionFailure("SOURCE_STRUCTURE_REJECTED") from exc
    receipt = {
        **result,
        "acquisition_status": "LOCAL_ARCHIVE_RECEIVED",
        "acquisition_method": "DIRECT_OFFICIAL_HTTPS_GET",
        "http_status": response.http_status,
        "response_final_url": response.final_url,
        "http_content_type": response.content_type,
        "http_etag_raw": response.etag,
        "http_last_modified_raw": response.last_modified,
        "raw_local_path": str(raw_path),
        "receipt_local_path": str(receipt_path),
        "independent_c_acceptance": "NOT_GRANTED",
        "publication_approval": "NOT_GRANTED",
    }
    raw_created = False
    try:
        _write_new_private(raw_path, response.raw)
        raw_created = True
        _write_new_private(
            receipt_path,
            (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
    except OSError:
        if raw_created:
            raw_path.unlink(missing_ok=True)
        raise AcquisitionFailure("LOCAL_ARCHIVE_WRITE_FAILURE") from None
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hazard", choices=("flood", "landslide"), required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--raw-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = acquire_one_tile(
            hazard=args.hazard,
            source_url=args.source_url,
            raw_out=args.raw_out,
        )
    except (AcquisitionFailure, ValueError) as exc:
        error = {
            "status": "H0_ACQUISITION_HOLD",
            "reason": exc.category if isinstance(exc, AcquisitionFailure) else "INVALID_REQUEST",
            "http_status": exc.http_status if isinstance(exc, AcquisitionFailure) else None,
            "archive_created": False,
            "feature_count": None,
            "publication_approval": "NOT_GRANTED",
        }
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
