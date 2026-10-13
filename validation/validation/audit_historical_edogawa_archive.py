#!/usr/bin/env python3
"""Independently audit A's 2019 Typhoon 19 *current* archived original bytes.

This checks archive integrity and Tokyo HTML row/text, NOT historical as-of
availability, truth validity, model prediction accuracy, or shelter safety.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit
import zipfile

BULLETINS = {
    "tokyo-20191012-report23": {
        "published": "令和元年10月12日16時00分",
        "observed": "避難所開設(12日12:00時点)",
        "published_at": "2019-10-12T16:00:00+09:00",
        "observation_at": "2019-10-12T12:00:00+09:00",
    },
    "tokyo-20191012-report36": {
        "published": "令和元年10月12日21時00分",
        "observed": "避難所開設(12日15:00時点)",
        "published_at": "2019-10-12T21:00:00+09:00",
        "observation_at": "2019-10-12T15:00:00+09:00",
    },
    "tokyo-20191013-report49": {
        "published": "令和元年10月13日2時00分",
        "observed": "避難所開設(13日00:00時点)",
        "published_at": "2019-10-13T02:00:00+09:00",
        "observation_at": "2019-10-13T00:00:00+09:00",
    },
}
OTHER_IDS = {"edogawa-mayor-20191101", "edogawa-school-ops-review"}
SOURCE_IDS = set(BULLETINS) | OTHER_IDS
MAX_BYTES = 8 * 1024 * 1024


class AuditError(ValueError):
    pass


def compact(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.all_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        self.all_text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            value = "".join(self.cell).replace("[ここから追加]", "").replace("[追加ここまで]", "")
            self.row.append(compact(value))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def get_observation(self, reference: dict) -> dict:
        combined = compact("".join(self.all_text))
        if reference["published"] not in combined or reference["observed"] not in combined:
            raise AuditError("official publication/observation label not found")
        matching = [row for row in self.rows if row and row[0] == "江戸川区"]
        if len(matching) != 1 or len(matching[0]) < 2:
            raise AuditError("Edogawa row missing or duplicated")
        value = matching[0][1]
        if not re.fullmatch(r"[0-9]+", value):
            raise AuditError("Edogawa opened-site count is not an unambiguous integer")
        return {"area": "江戸川区", "opened_site_count": int(value),
                "source_row_cells": matching[0], "publication_text_verified": True,
                "observation_label_verified": True}


def audit(zip_path: Path) -> dict:
    entries_out = []
    with zipfile.ZipFile(zip_path) as archive:
        files = archive.namelist()
        expected = {"manifest.json"} | {
            sid + (".pdf" if sid.endswith("ops-review") else ".html") for sid in SOURCE_IDS
        }
        if set(files) != expected or len(files) != len(expected):
            raise AuditError("unexpected, duplicated or missing archive members")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema_id") != "hinanex.a.historical_original_archive.v0.1":
            raise AuditError("manifest schema mismatch")
        if (manifest.get("historical_as_of_approved") is not False
                or manifest.get("prediction_accuracy_evaluated") is not False
                or manifest.get("facility_pairs_approved") != 0):
            raise AuditError("archive attempts to claim downstream acceptance")
        rows = manifest.get("sources", [])
        if len(rows) != len(SOURCE_IDS) or {r.get("source_id") for r in rows} != SOURCE_IDS:
            raise AuditError("manifest source identity mismatch")
        for row in rows:
            sid = row["source_id"]
            name = sid + (".pdf" if sid.endswith("ops-review") else ".html")
            url = row.get("url", "")
            domain = urlsplit(url).hostname
            if (row.get("relative_path") != name or row.get("review_state") != "UNREVIEWED"
                    or urlsplit(url).scheme != "https" or
                    domain not in {"www.city.edogawa.tokyo.jp", "www.bousai.metro.tokyo.lg.jp"}):
                raise AuditError("unexpected source URL, path or approval flag")
            if sid.startswith("tokyo-") and domain != "www.bousai.metro.tokyo.lg.jp":
                raise AuditError("Tokyo official source host changed")
            if sid.startswith("edogawa-") and domain != "www.city.edogawa.tokyo.jp":
                raise AuditError("Edogawa official source host changed")
            if row.get("http_status") != 200:
                raise AuditError("source was not fetched with HTTP 200")
            data = archive.read(name)
            if not data or len(data) > MAX_BYTES:
                raise AuditError("original source empty or oversized")
            if len(data) != row.get("bytes") or hashlib.sha256(data).hexdigest() != row.get("sha256"):
                raise AuditError("independent SHA256 / byte-length mismatch")
            if sid.endswith("ops-review"):
                if not data.startswith(b"%PDF-"):
                    raise AuditError("missing original PDF header")
                kind = "PDF_STRUCTURE_ONLY"
                observation = None
            else:
                if not re.search(rb"<(?:!doctype\s+html|html)(?:\s|>)", data[:8192], re.I):
                    raise AuditError("not an HTML original")
                match = re.search(
                    rb"charset\s*=\s*['\"]?\s*([A-Za-z0-9_-]+)",
                    data[:8192], re.I
                )
                declared = match.group(1).decode("ascii").lower() if match else "utf-8"
                codec = {
                    "utf-8": "utf-8", "utf8": "utf-8",
                    "shift_jis": "cp932", "shift-jis": "cp932",
                    "windows-31j": "cp932", "cp932": "cp932",
                }.get(declared)
                if codec is None:
                    raise AuditError("unknown HTML encoding: " + declared)
                reader = TableReader()
                reader.feed(data.decode(codec, errors="strict"))
                if sid in BULLETINS:
                    policy = BULLETINS[sid]
                    if (row.get("claimed_published_at_jst") != policy["published_at"]
                            or row.get("claimed_observation_at_jst") != policy["observation_at"]):
                        raise AuditError("candidate timestamp disagrees with C expected report")
                    observation = reader.get_observation(policy)
                    kind = "TOKYO_BULLETIN_ROW_AND_TIME_VERIFIED"
                else:
                    observation = None
                    kind = "HTML_STRUCTURE_ONLY"
            entries_out.append({
                "source_id": sid, "sha256_verified": True,
                "source_shape": kind,
                "reported_observation": observation,
                "historical_as_of_approved": False,
            })
    return {
        "status": "C_INDEPENDENT_BYTE_AND_HTML_CHECKS_PASSED__UNREVIEWED",
        "archived_sources": len(entries_out),
        "tokyo_bulletins": [
            e for e in entries_out if e["source_id"] in BULLETINS
        ],
        "other_originals": [
            e for e in entries_out if e["source_id"] not in BULLETINS
        ],
        "historical_as_of_approved": False,
        "facility_pairs_approved": 0,
        "replay_match_or_mismatch_approved": False,
        "requires_human_c_review": True,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-zip", required=True, type=Path)
    p.add_argument("--report", type=Path)
    args = p.parse_args(argv)
    try:
        report = audit(args.archive_zip)
    except (AuditError, OSError, ValueError, zipfile.BadZipFile, UnicodeError) as exc:
        print("C_HISTORICAL_AUDIT_FAILED: " + str(exc), file=sys.stderr)
        return 1
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        if args.report.exists():
            print("C_HISTORICAL_AUDIT_FAILED: refusal to overwrite report", file=sys.stderr)
            return 1
        args.report.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
