#!/usr/bin/env python3
"""Independent C byte/PDF-metadata audit for possible 2019 Edogawa map copy.

This cannot approve 2019 historical publication or decode image-only labels.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

SCHEMA = "hinanex.a.edogawa_historical_map_copy.v0.1"
SID = "edogawa-2019-map-tokyo-school-alternate"
PDF_NAME = SID + ".pdf"
URL = ("https://www.metro.ed.jp/momijigawa-h/news/"
       "7b0ecf0d7ff8894fd949eed62e1bb334e21dc55b.pdf")
EVENT_DATE = "2019-10-12"


class MapAuditError(ValueError):
    pass


def read_pdf_properties(body: bytes) -> dict:
    try:
        import fitz
    except ImportError as exc:
        raise MapAuditError("PyMuPDF dependency is required for real PDF audit") from exc
    with fitz.open(stream=body, filetype="pdf") as doc:
        if not (1 <= len(doc) <= 30):
            raise MapAuditError("PDF page count outside expected bounds")
        return {
            "page_count": len(doc),
            "creation_date_raw": doc.metadata.get("creationDate") or None,
            "text_characters": sum(len(page.get_text()) for page in doc),
            "raster_images": sum(len(page.get_images(full=True)) for page in doc),
        }


def pdf_creation_day(meta_value: object) -> str | None:
    if not isinstance(meta_value, str):
        return None
    match = re.fullmatch(r"D:(\d{4})(\d{2})(\d{2})(?:.*)?", meta_value)
    if not match:
        return None
    try:
        return datetime(int(match[1]), int(match[2]), int(match[3])).date().isoformat()
    except ValueError:
        return None


def audit(archive_path: Path, pdf_inspector=None) -> dict:
    inspector = pdf_inspector or read_pdf_properties
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != 2 or set(names) != {"manifest.json", PDF_NAME}:
            raise MapAuditError("archive members must be exactly original PDF and manifest")
        manifest = json.loads(archive.read("manifest.json"))
        for key, expected in {
            "schema_id": SCHEMA,
            "source_id": SID,
            "url": URL,
            "filename": PDF_NAME,
            "source_state": "UNREVIEWED_ALTERNATE_COPY",
            "original_issue_time_verified": False,
            "same_bytes_available_on_2019_10_12": False,
            "asof_input_approved": False,
            "facility_identity_approved": False,
            "C_human_review": "NOT_RUN",
        }.items():
            if manifest.get(key) != expected:
                raise MapAuditError("unexpected source identity or forged approval: "+key)
        body = archive.read(PDF_NAME)
        if not body.startswith(b"%PDF-") or not 8 <= len(body) <= 20*1024*1024:
            raise MapAuditError("invalid PDF raw")
        computed = hashlib.sha256(body).hexdigest()
        if manifest.get("bytes") != len(body) or manifest.get("sha256") != computed:
            raise MapAuditError("independent SHA256 or byte-length mismatch")
        data = inspector(body)
        if not isinstance(data, dict) or not isinstance(data.get("page_count"), int):
            raise MapAuditError("PDF inspection failed")
        if not 1 <= data["page_count"] <= 30:
            raise MapAuditError("invalid PDF page count")
        for k in ("text_characters","raster_images"):
            if not isinstance(data.get(k), int) or data[k] < 0:
                raise MapAuditError("invalid PDF content inspection")
    created = pdf_creation_day(data.get("creation_date_raw"))
    after_event = created is not None and created > EVENT_DATE
    return {
        "schema_id": "hinanex.c.edogawa_2019_map_audit.v0.1",
        "status": "C_BYTES_AND_PDF_CONTAINER_VERIFIED__NO_ASOF_APPROVAL",
        "source_id": SID,
        "sha256_verified": computed,
        "raw_bytes": len(body),
        "pdf_page_count": data["page_count"],
        "pdf_creation_date_raw": data.get("creation_date_raw"),
        "pdf_container_creation_day": created,
        "pdf_container_metadata_indicates_post_event": after_event,
        "raster_image_count": data["raster_images"],
        "extractable_text_characters": data["text_characters"],
        "map_visual_text_review_required": data["text_characters"] == 0,
        "warnings": (["PDF_CONTAINER_CREATED_AFTER_2019_EVENT__MAP_IMAGE_MAY_BE_OLDER"]
                     if after_event else ["NO_CONFIRMED_ORIGINAL_2019_PUBLICATION"]),
        "historical_version_verified": False,
        "source_edition_visual_identity_approved": False,
        "asof_input_approved": False,
        "facility_identity_approved": False,
        "prediction_accuracy_evaluated": False,
        "needs_human_C_review": True,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-zip", type=Path, required=True)
    p.add_argument("--report", type=Path)
    a = p.parse_args(argv)
    try:
        data = audit(a.archive_zip)
        text = json.dumps(data,ensure_ascii=False,indent=2)+"\n"
        if a.report:
            if a.report.exists():
                raise MapAuditError("refuse to overwrite report")
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(text,encoding="utf-8")
        print(text)
    except (OSError, ValueError, zipfile.BadZipFile, TypeError) as exc:
        print("C_EDOGAWA_MAP_AUDIT_FAILED: "+str(exc),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
