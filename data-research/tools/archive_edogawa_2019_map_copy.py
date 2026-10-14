#!/usr/bin/env python3
"""A-only collector for a potential 2019-version Edogawa map copy.

Do NOT certify as-of availability, Edogawa publishing identity or safety.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

URL = ("https://www.metro.ed.jp/momijigawa-h/news/"
       "7b0ecf0d7ff8894fd949eed62e1bb334e21dc55b.pdf")
ID = "edogawa-2019-map-tokyo-school-alternate"
SCHEMA = "hinanex.a.edogawa_historical_map_copy.v0.1"
PDF = ID + ".pdf"
MAX_BYTES = 20 * 1024 * 1024


class CaptureError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureError("redirect rejected; new URL needs independent review")


def check_pdf(data: bytes) -> None:
    if not 8 <= len(data) <= MAX_BYTES or not data.startswith(b"%PDF-"):
        raise CaptureError("not a valid-size PDF original")


def capture(out_dir: Path) -> dict:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CaptureError("cannot overwrite archival output")
    out_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={
        "User-Agent": "HINANEX-2019-Map-Candidate/0.1", "Accept": "application/pdf"})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=25) as response:
        if response.status != 200 or response.geturl() != URL:
            raise CaptureError("unexpected official URL/HTTP status")
        body = response.read(MAX_BYTES + 1)
        check_pdf(body)
        headers = {
            "date": response.headers.get("Date"),
            "last_modified": response.headers.get("Last-Modified"),
            "content_type": response.headers.get("Content-Type"),
        }
    (out_dir / PDF).write_bytes(body)
    manifest = {
        "schema_id": SCHEMA,
        "source_id": ID,
        "hosting_domain": "www.metro.ed.jp",
        "claimed_issuer_on_map": "江戸川区",
        "url": URL,
        "filename": PDF,
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "response": headers,
        "source_state": "UNREVIEWED_ALTERNATE_COPY",
        "map_printed_edition": "2019-05",
        "original_issue_time_verified": False,
        "same_bytes_available_on_2019_10_12": False,
        "asof_input_approved": False,
        "facility_identity_approved": False,
        "C_human_review": "NOT_RUN",
        "license_review": "NOT_DONE",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if set(p.name for p in folder.iterdir()) != {PDF, "manifest.json"}:
        raise CaptureError("archive member set mismatch")
    for name, expected in {
        "schema_id": SCHEMA, "source_id": ID, "url": URL,
        "filename": PDF, "source_state": "UNREVIEWED_ALTERNATE_COPY",
        "original_issue_time_verified": False,
        "same_bytes_available_on_2019_10_12": False,
        "asof_input_approved": False, "facility_identity_approved": False,
        "C_human_review": "NOT_RUN",
    }.items():
        if manifest.get(name) != expected:
            raise CaptureError("source identity or approval metadata changed: " + name)
    body = (folder / PDF).read_bytes()
    check_pdf(body)
    if len(body) != manifest.get("bytes") or hashlib.sha256(body).hexdigest() != manifest.get("sha256"):
        raise CaptureError("SHA256 original bytes do not match manifest")
    return {"result": "A_HASH_VERIFIED__NOT_ASOF_APPROVED",
            "original_bytes": len(body), "sha256": manifest["sha256"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument("--out-dir", type=Path)
    m.add_argument("--verify-dir", type=Path)
    a = p.parse_args(argv)
    try:
        result = capture(a.out_dir) if a.out_dir is not None else verify(a.verify_dir)
    except (CaptureError, urllib.error.URLError, OSError, ValueError) as exc:
        print("EDOGAWA_2019_MAP_CAPTURE_FAILED: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
