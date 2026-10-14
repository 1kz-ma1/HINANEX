#!/usr/bin/env python3
"""Independent C audit of current JMA 2019 web originals (not as-of approval).

Inspect original artifact ZIP; do not import A collection code or trust A's
metadata as ground truth. PDF text needs PyMuPDF for the real audit; regression
tests inject a synthetic PDF text reader, never treating it as official data.
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
import zipfile

POLICIES = {
    "jma-20191009-t19": ("1910/09a/201910091400.html", "1910/09a/20191009_1400.pdf",
                          "令和元年10月9日", "令和元年10月9日14時00分"),
    "jma-20191010-t19": ("1910/10c/201910101400.html", "1910/10c/20191010_1400.pdf",
                          "令和元年10月10日", "令和元年10月10日14時00分"),
    "jma-20191011-t19": ("1910/11b/201910111100.html", "1910/11b/20191011_1100.pdf",
                          "令和元年10月11日", "令和元年10月11日11時00分"),
}
SCHEMA = "hinanex.a.jma_2019_raw_manifest.v0.1"
MAX_FILE_BYTES = 12 * 1024 * 1024


class AuditError(ValueError):
    pass


def compact(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words = []
        self.links = []

    def handle_data(self, data):
        self.words.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs)
            if a.get("href"):
                self.links.append(a["href"])


def pdf_text(data: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise AuditError("PyMuPDF required to inspect actual PDF text") from exc
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            if not (1 <= len(doc) <= 100):
                raise AuditError("unexpected PDF page count")
            return "\n".join(doc[i].get_text() for i in range(min(2, len(doc))))
    except Exception as exc:
        raise AuditError("PDF text extraction failed") from exc


def audit(zip_path: Path, pdf_reader=None) -> dict:
    read_pdf = pdf_reader if pdf_reader is not None else pdf_text
    expected = {"manifest.json"} | {f"{sid}.{ext}" for sid in POLICIES for ext in ("html","pdf")}
    checks = []
    with zipfile.ZipFile(zip_path) as archive:
        files = archive.namelist()
        if len(files) != len(expected) or set(files) != expected:
            raise AuditError("archive members missing, duplicated or unexpected")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema_id") != SCHEMA or manifest.get("case_id") != "2019-typhoon19-edogawa":
            raise AuditError("not the expected JMA artifact schema/event")
        if (manifest.get("historical_revision_verified") is not False or
            manifest.get("asof_input_approved") is not False or
            manifest.get("prediction_accuracy_evaluated") is not False):
            raise AuditError("A archive must not claim historical approval")
        records = manifest.get("records")
        if not isinstance(records, list) or len(records) != 6:
            raise AuditError("expected exactly six source records")
        index = {}
        for row in records:
            key = (row.get("source_id"), row.get("kind"))
            if key in index or key[0] not in POLICIES or key[1] not in ("html","pdf"):
                raise AuditError("duplicate/unknown source key")
            index[key] = row
        for sid, policy in POLICIES.items():
            html_path, pdf_path, printed_date, printed_time = policy
            source_text = None
            for kind, path in (("html", html_path),("pdf",pdf_path)):
                row = index.get((sid, kind))
                if row is None:
                    raise AuditError("missing source pair")
                filename = f"{sid}.{kind}"
                expected_url = "https://www.jma.go.jp/jma/press/" + path
                if (row.get("url") != expected_url or row.get("relative_path") != filename or
                    row.get("review_state") != "UNREVIEWED" or row.get("http_status") != 200):
                    raise AuditError("official URL/source identity/approval mismatch")
                original = archive.read(filename)
                if not (0 < len(original) <= MAX_FILE_BYTES):
                    raise AuditError("empty or oversized archived bytes")
                if (row.get("size_bytes") != len(original) or
                    row.get("sha256") != hashlib.sha256(original).hexdigest()):
                    raise AuditError("C independent byte/hash mismatch")
                if kind == "html":
                    if b"<html" not in original.lower()[:8192]:
                        raise AuditError("original HTML signature missing")
                    parser = HtmlText()
                    parser.feed(original.decode("utf-8", errors="strict"))
                    text = compact("".join(parser.words))
                    if compact(printed_date) not in text or "台風第19号" not in text:
                        raise AuditError("JMA press page date/content mismatch")
                    if not any(path.endswith(pdf_path.split("/")[-1]) for path in parser.links):
                        raise AuditError("official page does not link to expected PDF")
                    source_text = text
                else:
                    if not original.startswith(b"%PDF-"):
                        raise AuditError("PDF signature mismatch")
                    extracted = compact(read_pdf(original))
                    if compact(printed_time) not in extracted:
                        raise AuditError("PDF does not contain the documented 2019 time string")
                    if "台風第19号" not in extracted:
                        raise AuditError("PDF topic mismatch")
                checks.append({"source_id":sid,"kind":kind,"sha256":row["sha256"],
                               "original_bytes_independently_verified":True})
    return {
        "schema_id":"hinanex.c.jma_2019_original_audit.v0.1",
        "status":"C_ORIGINAL_BYTES_AND_PRINTED_TIMES_CHECKED__NO_HISTORICAL_RELEASE_APPROVAL",
        "checked_originals":len(checks),
        "records":checks,
        "historical_original_revision_verified":False,
        "publication_instant_independently_approved":False,
        "asof_input_approved":False,
        "prediction_accuracy_evaluated":False,
        "human_review_still_required":True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-zip", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.archive_zip)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            if args.report.exists():
                raise AuditError("report overwrite refused")
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(payload, encoding="utf-8")
        print(payload)
        return 0
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        print("C_JMA_AUDIT_FAILED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
