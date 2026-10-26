"""Explicit source-provenance capture of a GSI national emergency-place CSV.

The fixed HTTPS CSV endpoint is a candidate inferred from public references,
NOT verified by this source alone. A successful response only gives a local
UNREVIEWED acquisition claim. No implicit network calls or public release.
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
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

SOURCE_URL = "https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv"
SOURCE_INFO = "https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 32_000_000
SPEC = importlib.util.spec_from_file_location(
    "gsi_csv_offline_inspector", Path(__file__).with_name("inspect_gsi_emergency_csv_archive.py")
)
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)

class CaptureBlocked(ValueError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fetch_one() -> tuple[bytes, dict]:
    opener = build_opener(
        HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
    )
    req = Request(SOURCE_URL, headers={
        "User-Agent": "HINANEX-A-GSI-CSV-UNREVIEWED/1.0",
        "Accept": "text/csv,text/plain,*/*;q=0.5",
        "Accept-Encoding": "identity",
    })
    try:
        with opener.open(req, timeout=25) as response:
            if response.getcode() != 200 or response.geturl() != SOURCE_URL:
                raise CaptureBlocked("OFFICIAL_ORIGIN_HTTP_RESPONSE_UNEXPECTED")
            raw = response.read(MAX_BYTES + 1)
            if not 0 < len(raw) <= MAX_BYTES:
                raise CaptureBlocked("OFFICIAL_CSV_EMPTY_OR_TOO_LARGE")
            headers = {
                "status_observed": 200,
                "url_observed": response.geturl(),
                "etag_observed": response.headers.get("ETag"),
                "last_modified_observed": response.headers.get("Last-Modified"),
                "content_type_observed": response.headers.get("Content-Type"),
            }
            return raw, headers
    except (HTTPError, URLError, OSError) as exc:
        raise CaptureBlocked("OFFICIAL_CSV_FETCH_UNAVAILABLE_OR_REJECTED") from exc

def capture_once(destination: Path, *, acknowledged: bool, fetcher=fetch_one,
                 observed_at=None):
    if acknowledged is not True:
        raise CaptureBlocked("EXPLICIT_GSI_NOTICE_ACKNOWLEDGMENT_REQUIRED")
    dest = Path(destination).absolute()
    if dest.exists() or dest.is_symlink():
        raise CaptureBlocked("EVIDENCE_DESTINATION_MUST_NOT_EXIST")
    if not dest.parent.is_dir():
        raise CaptureBlocked("EVIDENCE_PARENT_DIRECTORY_MISSING")
    parent = dest.parent.resolve(strict=True)
    final = parent / dest.name
    if final == REPO_ROOT or REPO_ROOT in final.parents:
        raise CaptureBlocked("EVIDENCE_MUST_BE_OUTSIDE_GIT")
    timestamp = observed_at or datetime.now(timezone.utc)
    if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
        raise CaptureBlocked("INVALID_CAPTURE_CLOCK")
    raw, headers = fetcher()
    if (not isinstance(headers, dict) or type(headers.get("status_observed")) is not int
            or headers["status_observed"] != 200 or headers.get("url_observed") != SOURCE_URL):
        raise CaptureBlocked("SOURCE_URL_OR_STATUS_CLAIM_INVALID")
    # A source layout mismatch blocks creating any evidence bundle.
    try:
        summary = inspector.inspect_emergency_place_csv(raw, "national", encoding="utf-8-sig")
    except ValueError as exc:
        raise CaptureBlocked("GSI_NATIONAL_CSV_FORMAT_UNVERIFIED") from exc
    manifest = {
        "state": "GSI_CSV_ORIGINAL_CAPTURE_UNREVIEWED",
        "source_url": SOURCE_URL,
        "official_specification_url": SOURCE_INFO,
        "captured_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "sha256": summary["source_archive_sha256"],
        "source_bytes": len(raw),
        "rows_count_unreviewed": summary["archive_rows_count"],
        "observed_http": headers,
        "official_origin_independently_authenticated": False,
        "publication_date_verified": False,
        "human_c_approved": False,
        "csv_to_geojson_identity_approved": False,
        "navigation_approved": False,
        "usable_in_disaster": False,
    }
    with TemporaryDirectory(dir=parent, prefix=".gsi-csv-source-") as temporary:
        root = Path(temporary)
        for name, blob in (
            ("gsi-emergency-national-original.csv", raw),
            ("a_gsi_csv_inspection_UNREVIEWED.json",
             (json.dumps(summary,ensure_ascii=False,indent=2)+"\n").encode()),
            ("a_capture_manifest_UNREVIEWED.json",
             (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode())
        ):
            fd = os.open(root/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd,"wb") as stream:
                stream.write(blob)
        if final.exists() or final.is_symlink():
            raise CaptureBlocked("EVIDENCE_PATH_RACE_NO_OVERWRITE")
        os.rename(root,final)
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fetch",action="store_true")
    p.add_argument("--acknowledged-gsi-terms",action="store_true")
    p.add_argument("--out-dir",type=Path,required=True)
    args=p.parse_args()
    if not args.fetch:
        p.error("--fetch required for external access; no implicit access")
    try:
        m=capture_once(args.out_dir,acknowledged=args.acknowledged_gsi_terms)
        print(json.dumps({
            "state":m["state"],"original_sha256":m["sha256"],
            "unreviewed_record_count":m["rows_count_unreviewed"],
            "csv_to_geojson_identity_approved":False,
        },ensure_ascii=False))
        return 0
    except (CaptureBlocked,OSError) as exc:
        print("GSI CSV capture BLOCKED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
