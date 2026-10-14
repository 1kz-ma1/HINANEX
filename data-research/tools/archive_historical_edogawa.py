#!/usr/bin/env python3
"""Collect immutable-bytes candidates; never certify historical availability.

Run outside git working tree when possible. Raw bytes and manifests are UNREVIEWED.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SOURCE_IDS = (
    "tokyo-20191012-report23",
    "tokyo-20191012-report36",
    "tokyo-20191013-report49",
    "edogawa-mayor-20191101",
    "edogawa-school-ops-review",
)
ALLOWED_HOSTS = frozenset({"www.bousai.metro.tokyo.lg.jp", "www.city.edogawa.tokyo.jp"})
MAX_BYTES = 8 * 1024 * 1024


class EvidenceError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("redirect rejected; manual review required")


def require_source(source: dict) -> None:
    sid = source.get("source_id")
    if sid not in SOURCE_IDS:
        raise EvidenceError("source ID is not in the reviewed candidate list")
    url = source.get("url", "")
    u = urllib.parse.urlsplit(url)
    if (u.scheme != "https" or u.hostname not in ALLOWED_HOSTS
            or u.username or u.password or u.port is not None
            or u.query or u.fragment or "\\" in u.path):
        raise EvidenceError("not an exact HTTPS official origin URL")
    if sid.startswith("tokyo-") and u.hostname != "www.bousai.metro.tokyo.lg.jp":
        raise EvidenceError("Tokyo bulletin host mismatch")
    if sid.startswith("edogawa-") and u.hostname != "www.city.edogawa.tokyo.jp":
        raise EvidenceError("Edogawa official host mismatch")
    expected_suffix = ".pdf" if source.get("format") == "PDF" else ".html"
    if not u.path.endswith(expected_suffix):
        raise EvidenceError("source type mismatch")


def check_shape(source: dict, data: bytes) -> None:
    if not data or len(data) > MAX_BYTES:
        raise EvidenceError("source is empty or oversized")
    if source["format"] == "PDF":
        if not data.startswith(b"%PDF-"):
            raise EvidenceError("expected PDF original bytes")
    elif not re.search(rb"<(?:!doctype\s+html|html)(?:\s|>)", data[:8192], re.I):
        raise EvidenceError("expected official HTML document, not an error/login page")


def candidates(path: pathlib.Path) -> dict:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("case_id") != "2019-typhoon19-edogawa":
        raise EvidenceError("wrong event")
    sources = {v["source_id"]: v for v in ledger["sources"]}
    if len(sources) != len(ledger["sources"]):
        raise EvidenceError("duplicate source ID")
    for sid in SOURCE_IDS:
        if sid not in sources:
            raise EvidenceError("missing required candidate " + sid)
        require_source(sources[sid])
    return sources


def archive(ledger_path: pathlib.Path, out_dir: pathlib.Path) -> dict:
    sources = candidates(ledger_path)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise EvidenceError("output directory is not empty; never overwrite archived evidence")
    out_dir.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(NoRedirect())
    entries = []
    for sid in SOURCE_IDS:
        item = sources[sid]
        req = urllib.request.Request(
            item["url"],
            headers={"User-Agent": "HINANEX-Historical-Evidence-Capture/0.1",
                     "Accept": "text/html,application/pdf"},
        )
        with opener.open(req, timeout=20) as response:
            if response.status != 200 or response.geturl() != item["url"]:
                raise EvidenceError("unexpected HTTP status or final URL: " + sid)
            data = response.read(MAX_BYTES + 1)
            check_shape(item, data)
            response_type = response.headers.get("Content-Type")
            response_modified = response.headers.get("Last-Modified")
            response_date = response.headers.get("Date")
        ext = ".pdf" if item["format"] == "PDF" else ".html"
        filename = sid + ext
        (out_dir / filename).write_bytes(data)
        entries.append({
            "source_id": sid,
            "url": item["url"],
            "relative_path": filename,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "http_status": 200,
            "response_content_type": response_type,
            "response_last_modified": response_modified,
            "response_date": response_date,
            "claimed_published_at_jst": item.get("published_at_jst"),
            "claimed_observation_at_jst": item.get("observation_at_jst"),
            "review_state": "UNREVIEWED",
        })
    manifest = {
        "schema_id": "hinanex.a.historical_original_archive.v0.1",
        "case_id": "2019-typhoon19-edogawa",
        "source_candidate_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "status": "ORIGINAL_BYTES_CAPTURED__UNREVIEWED",
        "historical_as_of_approved": False,
        "facility_pairs_approved": 0,
        "prediction_accuracy_evaluated": False,
        "sources": entries,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(ledger_path: pathlib.Path, folder: pathlib.Path) -> dict:
    sources = candidates(ledger_path)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_id") != "hinanex.a.historical_original_archive.v0.1":
        raise EvidenceError("incorrect manifest schema")
    if manifest.get("source_candidate_ledger_sha256") != hashlib.sha256(ledger_path.read_bytes()).hexdigest():
        raise EvidenceError("ledger changed since capture")
    if manifest.get("historical_as_of_approved") is not False or manifest.get("facility_pairs_approved") != 0:
        raise EvidenceError("unreviewed archive may not certify historical eligibility")
    entries = manifest.get("sources", [])
    if len(entries) != len(SOURCE_IDS) or {e.get("source_id") for e in entries} != set(SOURCE_IDS):
        raise EvidenceError("archive source set mismatch")
    for entry in entries:
        sid = entry["source_id"]
        source = sources[sid]
        if entry.get("url") != source["url"] or entry.get("review_state") != "UNREVIEWED":
            raise EvidenceError("source URL or review state tampered")
        filename = sid + (".pdf" if source["format"] == "PDF" else ".html")
        if entry.get("relative_path") != filename:
            raise EvidenceError("unexpected file path")
        data = (folder / filename).read_bytes()
        check_shape(source, data)
        if (len(data) != entry.get("bytes")
                or hashlib.sha256(data).hexdigest() != entry.get("sha256")):
            raise EvidenceError("archived bytes mismatch: " + sid)
    return {"status": "BYTES_MATCH_MANIFEST__NO_SEMANTIC_ACCEPTANCE", "verified_sources": len(entries)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=pathlib.Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out-dir", type=pathlib.Path)
    group.add_argument("--verify-dir", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = archive(args.ledger, args.out_dir) if args.out_dir else verify(args.ledger, args.verify_dir)
    except (EvidenceError, OSError, ValueError, urllib.error.URLError) as exc:
        print("HISTORICAL_ARCHIVE_FAILED: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
