#!/usr/bin/env python3
"""Capture exact *currently served* JMA October 2019 source bytes.

Archive success DOES NOT prove that the present revision existed at that time.
No raw bytes are written into git; use an isolated artifact directory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

SOURCES = {
    "jma-20191009-t19": ("https://www.jma.go.jp/jma/press/1910/09a/201910091400.html",
                          "https://www.jma.go.jp/jma/press/1910/09a/20191009_1400.pdf"),
    "jma-20191010-t19": ("https://www.jma.go.jp/jma/press/1910/10c/201910101400.html",
                          "https://www.jma.go.jp/jma/press/1910/10c/20191010_1400.pdf"),
    "jma-20191011-t19": ("https://www.jma.go.jp/jma/press/1910/11b/201910111100.html",
                          "https://www.jma.go.jp/jma/press/1910/11b/20191011_1100.pdf"),
}
SCHEMA = "hinanex.a.jma_2019_raw_manifest.v0.1"
MAX_BYTES = 12 * 1024 * 1024


class ArchiveError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ArchiveError("unexpected redirect: human URL review required")


def sources_from_ledger(path: Path) -> list[dict]:
    raw = path.read_bytes()
    ledger = json.loads(raw)
    if ledger.get("case_id") != "2019-typhoon19-edogawa":
        raise ArchiveError("wrong historical event")
    source_list = ledger.get("sources")
    if not isinstance(source_list, list):
        raise ArchiveError("source ledger missing")
    lookup = {x["source_id"]: x for x in source_list}
    if len(lookup) != len(source_list):
        raise ArchiveError("duplicate candidates")
    entries = []
    for sid, urls in SOURCES.items():
        row = lookup.get(sid)
        if not row or row.get("url") != urls[0] or row.get("publisher") != "気象庁":
            raise ArchiveError("candidate URL or publisher changed: " + sid)
        if row.get("asof_input_accepted") is not False or row.get("published_at_jst") is not None:
            raise ArchiveError("unreviewed candidate must not assert exact publication time or approval")
        for kind, url in (("html", urls[0]), ("pdf", urls[1])):
            parts = urllib.parse.urlsplit(url)
            if (parts.scheme != "https" or parts.hostname != "www.jma.go.jp"
                    or parts.port is not None or parts.username or parts.password
                    or parts.query or parts.fragment):
                raise ArchiveError("nonallowlisted JMA URL")
            entries.append({"source_id": sid, "kind": kind, "url": url,
                            "relative_path": f"{sid}.{kind}"})
    return entries


def check_shape(kind: str, data: bytes) -> None:
    if not data or len(data) > MAX_BYTES:
        raise ArchiveError("empty/oversized official response")
    if kind == "pdf":
        if not data.startswith(b"%PDF-"):
            raise ArchiveError("not a PDF original")
    elif not re.search(rb"<(?:!doctype\s+html|html)(?:\s|>)", data[:8192], re.I):
        raise ArchiveError("not an HTML document")


def collect(ledger_path: Path, out: Path) -> dict:
    entries = sources_from_ledger(ledger_path)
    if out.exists() and any(out.iterdir()):
        raise ArchiveError("archive directory not empty, overwrite forbidden")
    out.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(NoRedirect())
    captured = []
    for entry in entries:
        request = urllib.request.Request(entry["url"], headers={
            "User-Agent": "HINANEX-JMA-Historical-Original/0.1",
            "Accept": "text/html,application/pdf",
        })
        with opener.open(request, timeout=25) as response:
            if response.status != 200 or response.geturl() != entry["url"]:
                raise ArchiveError("HTTP status/URL mismatch: " + entry["source_id"])
            data = response.read(MAX_BYTES + 1)
            check_shape(entry["kind"], data)
            ctype = response.headers.get("Content-Type")
            server_date = response.headers.get("Date")
            last_modified = response.headers.get("Last-Modified")
        (out / entry["relative_path"]).write_bytes(data)
        captured.append({
            **entry, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
            "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "http_status": 200, "response_content_type": ctype,
            "response_date": server_date, "response_last_modified": last_modified,
            "review_state": "UNREVIEWED",
        })
    manifest = {
        "schema_id": SCHEMA,
        "case_id": "2019-typhoon19-edogawa",
        "source_candidate_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "records": captured,
        "raw_bytes_integrity_verified": False,
        "historical_revision_verified": False,
        "asof_input_approved": False,
        "independent_c_semantic_review": "NOT_RUN",
        "prediction_accuracy_evaluated": False,
        "note": "HTTP Date/Last-Modified prove neither 2019 issuance nor historical byte identity.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    return manifest


def verify(ledger: Path, out: Path) -> dict:
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_id") != SCHEMA
            or manifest.get("asof_input_approved") is not False
            or manifest.get("historical_revision_verified") is not False):
        raise ArchiveError("manifest contract/approval violation")
    if hashlib.sha256(ledger.read_bytes()).hexdigest() != manifest.get("source_candidate_ledger_sha256"):
        raise ArchiveError("source ledger hash mismatch")
    expected = sources_from_ledger(ledger)
    actual = manifest.get("records")
    if not isinstance(actual, list) or len(actual) != len(expected):
        raise ArchiveError("source record count mismatch")
    if {p.name for p in out.iterdir()} != ({"manifest.json"} | {s["relative_path"] for s in expected}):
        raise ArchiveError("extra or missing original files")
    for row, spec in zip(actual, expected):
        if any(row.get(k) != spec[k] for k in ("source_id","kind","url","relative_path")):
            raise ArchiveError("source identity tampered")
        if row.get("review_state") != "UNREVIEWED" or row.get("http_status") != 200:
            raise ArchiveError("source approval/status tampered")
        data = (out / spec["relative_path"]).read_bytes()
        check_shape(spec["kind"], data)
        if len(data) != row.get("size_bytes") or hashlib.sha256(data).hexdigest() != row.get("sha256"):
            raise ArchiveError("original bytes SHA256 mismatch: " + spec["source_id"])
    return {"status": "A_BYTES_VERIFIED__NO_ASOF_APPROVAL", "verified_originals": len(expected)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ledger", required=True, type=Path)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--out-dir", type=Path)
    group.add_argument("--verify-dir", type=Path)
    args = p.parse_args(argv)
    try:
        answer = collect(args.ledger, args.out_dir) if args.out_dir else verify(args.ledger,args.verify_dir)
        print(json.dumps(answer,ensure_ascii=False,indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print("JMA_ARCHIVE_FAILED: " + str(exc),file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
