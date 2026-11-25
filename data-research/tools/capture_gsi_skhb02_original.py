"""Explicit, offline-by-default A capture of one official GSI skhb02 z10 tile.

Running this command with --fetch performs ONE direct HTTPS request to the
strictly fixed official host/path. It creates an immutable unreviewed local
evidence bundle outside the Git repository; never publishes or certifies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import ssl
import sys
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, Request, build_opener,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = Path(__file__).with_name("inspect_gsi_skhb02_archive.py")
_spec = importlib.util.spec_from_file_location("a_skhb02_inspector", INSPECTOR)
if _spec is None or _spec.loader is None:
    raise RuntimeError("local A source inspector unavailable")
_a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a)
MAX_BYTES = _a.MAX_ARCHIVE_BYTES


class CaptureError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    """Reject all redirects, including same-host: preserve exact requested URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def official_tile_url(x: int, y: int) -> str:
    if any(type(v) is not int or not (0 <= v < 1024) for v in (x, y)):
        raise CaptureError("z10 tile numbers must be integers in [0,1023]")
    url = f"https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/{x}/{y}.geojson"
    if _a.validate_source_url(url) != (x, y):
        raise CaptureError("GSI tile URL did not round trip")
    return url


def fetch_direct_https(source_url: str, timeout: int = 20) -> tuple[bytes, dict]:
    """Trust the system TLS root store; reject redirect/non-200/oversize.

    This is an A acquisition observation only, NOT an independently verified
    authentic source archive or permission to reuse/distribute.
    """
    _a.validate_source_url(source_url)
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise CaptureError("timeout out of bounds")
    opener = build_opener(
        HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
    )
    request = Request(source_url, headers={
        "User-Agent": "HINANEX-A-skHB02-unreviewed/1.0",
        "Accept": "application/geo+json,application/json,*/*;q=0.5",
        "Accept-Encoding": "identity",
    })
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.getcode()
            final_url = response.geturl()
            if status != 200 or final_url != source_url:
                raise CaptureError("unexpected status/redirect during source fetch")
            raw = response.read(MAX_BYTES + 1)
            if not (0 < len(raw) <= MAX_BYTES):
                raise CaptureError("official response empty or beyond size limit")
            return raw, {
                "http_status": status,
                "response_final_url": final_url,
                "content_type_observed": response.headers.get("Content-Type"),
                "etag_observed": response.headers.get("ETag"),
                "last_modified_observed": response.headers.get("Last-Modified"),
            }
    except (HTTPError, URLError, OSError) as exc:
        raise CaptureError("official HTTPS acquisition unavailable") from exc


def capture_one(
    x: int,
    y: int,
    out_dir: Path,
    *,
    fetcher=fetch_direct_https,
    now=None,
) -> dict:
    """Archive original exact bytes, A-only inspection and acquisition manifest.

    fetcher is injected only in offline tests. An untrusted/mock fetcher can
    NEVER produce an independently authenticated provenance proof.
    """
    url = official_tile_url(x, y)
    target = Path(out_dir).absolute()
    if target.is_symlink() or target.exists():
        raise CaptureError("destination already exists; existing proof not replaced")
    if not target.parent.is_dir():
        raise CaptureError("parent directory must already exist")
    parent = target.parent.resolve(strict=True)
    final = parent / target.name
    if REPO_ROOT == final or REPO_ROOT in final.parents:
        raise CaptureError("source archives must be stored OUTSIDE the repository")
    if final.exists() or final.is_symlink():
        raise CaptureError("destination already exists")
    captured_at = now if now is not None else datetime.now(timezone.utc)
    if (not isinstance(captured_at, datetime) or captured_at.utcoffset() is None):
        raise CaptureError("captured_at must be timezone-aware")
    raw, observed = fetcher(url)
    if not isinstance(observed, dict):
        raise CaptureError("fetch metadata unavailable")
    if (observed.get("http_status") != 200
            or observed.get("response_final_url") != url):
        raise CaptureError("fetcher returned no exact official HTTP 200 response")
    try:
        report = _a.inspect_archived_tile(raw, url)
    except _a.GsiLandslideInspectionError as exc:
        raise CaptureError("source inspection failed; no archive created") from exc

    manifest = {
        "capture_kind": "A_GSI_SKHB02_UNREVIEWED",
        "official_tile_url_requested": url,
        "source_host": "cyberjapandata.gsi.go.jp",
        "captured_at_utc": captured_at.astimezone(timezone.utc).isoformat(),
        "raw_sha256": report["source_sha256"],
        "raw_byte_count": report["source_byte_count"],
        "source_tile": report["source_tile"],
        "feature_count_tile_only": report["source_feature_count"],
        "http_status_observed": 200,
        "response_final_url_observed": url,
        "content_type_observed": observed.get("content_type_observed"),
        "etag_observed": observed.get("etag_observed"),
        "last_modified_observed": observed.get("last_modified_observed"),
        "official_municipal_publication_date_verified": None,
        "official_dataset_update_date_verified": None,
        "response_headers_are_not_publication_dates": True,
        "independent_https_origin_replay_passed": False,
        "independent_c_approved": False,
        "human_approved": False,
        "publishable": False,
    }
    with TemporaryDirectory(prefix=".skhb02-unreviewed-", dir=parent) as staging:
        staging_dir = Path(staging)

        def exclusive_file(name, data):
            path = staging_dir / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)

        exclusive_file(
            f"skhb02-10-{x}-{y}.geojson", raw
        )
        exclusive_file(
            "a_inspection_UNREVIEWED.json",
            (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        exclusive_file(
            "capture_manifest_UNREVIEWED.json",
            (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        if final.exists() or final.is_symlink():
            raise CaptureError("destination was created concurrently; no overwrite")
        os.rename(staging_dir, final)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true",
                        help="Explicitly authorize one official HTTPS fetch")
    parser.add_argument("--tile-x", type=int, required=True)
    parser.add_argument("--tile-y", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.fetch:
        parser.error("--fetch is required; no implicit network access")
    try:
        manifest = capture_one(args.tile_x, args.tile_y, args.out_dir)
    except (CaptureError, OSError) as exc:
        print(f"GSI skhb02 capture not accepted: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "ARCHIVED_UNREVIEWED",
        "source_url": manifest["official_tile_url_requested"],
        "raw_sha256": manifest["raw_sha256"],
        "tile_feature_count_unreviewed": manifest["feature_count_tile_only"],
        "destination": str(args.out_dir),
        "independent_c_approved": False,
        "publishable": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
