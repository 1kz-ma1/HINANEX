#!/usr/bin/env python3
"""C independent byte/text check for the official 2018 Edogawa school bulletin.

This validates 2018 source labels and an identity NON-EQUIVALENCE GATE,
NOT whether these were physical shelter locations on 2019-10-12.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import zipfile

SOURCE_ID="edogawa-kouhou-20180820"
PDF_NAME="edogawa-20180820-original-UNREVIEWED.pdf"
URL="https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf"
A_SCHEMA="hinanex.a.edogawa_2018_kouhou_original.v0.1"
C_SCHEMA="hinanex.c.2018_edogawa_school_identity_gate.v0.1"


class CError(ValueError):
    pass


def normalized(s):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",s))


def inspect_source_bytes(raw:bytes, source_text_extractor=None):
    if not (len(raw)>100 and raw.startswith(b"%PDF-")):
        raise CError("original is not a PDF")
    if source_text_extractor is None:
        try:
            import fitz
        except ImportError as exc:
            raise CError("PyMuPDF required for real source text") from exc
        with fitz.open(stream=raw,filetype="pdf") as pdf:
            if len(pdf)!=7:
                raise CError("official newsletter page count changed")
            pages=(pdf[0].get_text(),pdf[1].get_text())
    else:
        pages=source_text_extractor(raw)
    if not isinstance(pages,(list,tuple)) or len(pages)!=2:
        raise CError("original source pages missing")
    first=normalized(pages[0])
    second=normalized(pages[1])
    if "2018" not in first or "8月20日" not in first+second:
        raise CError("printed issue/date not verified in raw PDF")
    if "中学校名" not in second or "学校公開" not in second:
        raise CError("official table semantics no longer matches")
    exact_night="小松川第二夜間学級"
    if exact_night not in second:
        raise CError("explicit 2018 night-class listing missing")
    # The night class must not be the only reference to Komatsugawa II.
    if "小松川第二" not in second.replace(exact_night,"",1):
        raise CError("regular school entry missing independent of night")
    return {
        "current_pdf_original_date_label_verified":True,
        "day_school_label_present":True,
        "night_class_label_present_separately":True,
        "separate_catalog_rows_do_not_imply_shared_building":True,
        "school_night_same_physical_site_2019":None,
        "school_night_distinct_campus_2019_approved":False,
        "physical_site_pairs_approved":0,
        "historical_asof_input_approved":False,
        "predictive_match_or_mismatch_evaluated":False,
    }


def audit(archive,extractor=None):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=2 or set(names)!={"manifest.json",PDF_NAME}:
            raise CError("source archive file identity mismatch")
        manifest=json.loads(z.read("manifest.json"))
        checks={"schema_id":A_SCHEMA,"source_id":SOURCE_ID,"official_url":URL,
                "relative_path":PDF_NAME,"record_role":"CONTEMPORANEOUS_2018_SCHOOL_NAMES_ONLY",
                "source_first_published_in_2018_verified":False,
                "source_edition_content_2019_valid_verified":False,
                "historical_asof_input_approved":False,
                "school_night_physical_site_equivalence":None,
                "physical_site_pairs_approved":0,"C_human_review":"NOT_RUN",
                "response_http":200}
        for k,val in checks.items():
            if manifest.get(k)!=val:
                raise CError("archive source/provenance/approval metadata invalid: "+k)
        raw=z.read(PDF_NAME)
        digest=hashlib.sha256(raw).hexdigest()
        if len(raw)!=manifest.get("raw_bytes") or digest!=manifest.get("raw_sha256"):
            raise CError("C independent SHA256 original mismatch")
        inspected=inspect_source_bytes(raw,extractor)
    return {
        "schema_id":C_SCHEMA,
        "status":"C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED",
        "source_url":URL,"source_sha256":digest,
        "source_raw_bytes":len(raw),
        **inspected,
        "human_2018_original_publication_review_required":True,
        "human_2019_campus_identity_review_required":True,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-zip",type=Path,required=True)
    p.add_argument("--report",type=Path)
    args=p.parse_args(argv)
    try:
        r=audit(args.archive_zip)
        if args.report:
            if args.report.exists():
                raise CError("report overwrite denied")
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(r,ensure_ascii=False,indent=2))
    except (OSError,ValueError,zipfile.BadZipFile,TypeError) as exc:
        print("C_EDOGAWA_2018_SCHOOL_IDENTITY_FAILED: "+str(exc),file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
