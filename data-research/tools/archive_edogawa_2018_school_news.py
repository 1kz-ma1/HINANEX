#!/usr/bin/env python3
"""Fetch the currently hosted original 2018 Edogawa newsletter.

A source byte archive is NOT proof of its first historical web publication
or evidence of any 2019 shelter physical-site equality.
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

URL="https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf"
SOURCE="edogawa-kouhou-20180820"
FILENAME="edogawa-20180820-original-UNREVIEWED.pdf"
SCHEMA="hinanex.a.edogawa_2018_kouhou_original.v0.1"
LIMIT=20*1024*1024


class ArchiveError(ValueError):
    pass


class RedirectForbidden(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ArchiveError("unexpected redirect")


def shape(raw):
    if not (len(raw)>100 and len(raw)<=LIMIT and raw.startswith(b"%PDF-")):
        raise ArchiveError("unexpected newsletter original bytes or PDF signature")


def capture(out):
    if out.exists() and any(out.iterdir()):
        raise ArchiveError("refuse overwriting archived evidence")
    out.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(URL,headers={"Accept":"application/pdf",
        "User-Agent":"HINANEX-Historical-2018-News-Capture/0.1"})
    with urllib.request.build_opener(RedirectForbidden()).open(req,timeout=30) as rsp:
        if rsp.status!=200 or rsp.geturl()!=URL:
            raise ArchiveError("non-200 HTTP or changed origin URL")
        raw=rsp.read(LIMIT+1)
        shape(raw)
        h={"Date":rsp.headers.get("Date"),
           "Last-Modified":rsp.headers.get("Last-Modified"),
           "Content-Type":rsp.headers.get("Content-Type")}
    (out/FILENAME).write_bytes(raw)
    data={
        "schema_id":SCHEMA,"source_id":SOURCE,"official_url":URL,
        "relative_path":FILENAME,"raw_sha256":hashlib.sha256(raw).hexdigest(),
        "raw_bytes":len(raw),"captured_at_utc":datetime.now(timezone.utc).isoformat(),
        "response_http":200,"response_headers":h,
        "printed_issue_date":"2018-08-20",
        "record_role":"CONTEMPORANEOUS_2018_SCHOOL_NAMES_ONLY",
        "source_first_published_in_2018_verified":False,
        "source_edition_content_2019_valid_verified":False,
        "historical_asof_input_approved":False,
        "school_night_physical_site_equivalence":None,
        "physical_site_pairs_approved":0,
        "C_human_review":"NOT_RUN",
    }
    (out/"manifest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data


def verify(out):
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    fields={
        "schema_id":SCHEMA,"source_id":SOURCE,"official_url":URL,
        "relative_path":FILENAME,"response_http":200,
        "record_role":"CONTEMPORANEOUS_2018_SCHOOL_NAMES_ONLY",
        "source_first_published_in_2018_verified":False,
        "source_edition_content_2019_valid_verified":False,
        "historical_asof_input_approved":False,
        "school_night_physical_site_equivalence":None,
        "physical_site_pairs_approved":0,"C_human_review":"NOT_RUN"
    }
    if set(p.name for p in out.iterdir())!={FILENAME,"manifest.json"}:
        raise ArchiveError("unexpected archive member")
    for key,value in fields.items():
        if manifest.get(key)!=value:
            raise ArchiveError("archive identity/approval metadata mismatch: "+key)
    raw=(out/FILENAME).read_bytes()
    shape(raw)
    if len(raw)!=manifest.get("raw_bytes") or hashlib.sha256(raw).hexdigest()!=manifest.get("raw_sha256"):
        raise ArchiveError("SHA256 mismatch")
    return {"status":"A_BYTES_VERIFIED__2019_SITE_IDENTITY_UNREVIEWED",
            "sha256":manifest["raw_sha256"],"bytes":len(raw)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    grp=p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--out-dir",type=Path)
    grp.add_argument("--verify-dir",type=Path)
    x=p.parse_args(argv)
    try:
        result=capture(x.out_dir) if x.out_dir is not None else verify(x.verify_dir)
    except (ArchiveError,OSError,urllib.error.URLError,ValueError) as exc:
        print("A_KOUHOU_2018_FAILED: "+str(exc),file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
