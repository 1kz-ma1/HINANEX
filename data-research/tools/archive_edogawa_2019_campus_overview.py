#!/usr/bin/env python3
"""A evidence only: capture Edogawa's 2019-03-01 campus-rebuild webpage.

Today's bytes are not an authenticated 2019 web snapshot. No shelter locations
or current physical IDs are inferred from a school operations description.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

SOURCE_ID="edogawa-komatsugawa2-rebuild-20190301"
URL="https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html"
RAW_NAME=SOURCE_ID+".html"
SCHEMA="hinanex.a.edogawa_2019_campus_page_raw.v0.1"
MAX_SIZE=3*1024*1024


class ArchiveError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ArchiveError("redirect rejected: source URL requires review")


def check_shape(data):
    if not data or len(data)>MAX_SIZE or b"<html" not in data[:8192].lower():
        raise ArchiveError("empty/oversized/non-HTML source")


def archive(out):
    if out.exists() and any(out.iterdir()):
        raise ArchiveError("refuse to overwrite historical source archive")
    out.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(URL,headers={
        "User-Agent":"HINANEX-2019-Campus-Evidence/0.1","Accept":"text/html"})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=25) as response:
        if response.status!=200 or response.geturl()!=URL:
            raise ArchiveError("HTTP response or official URL changed")
        raw=response.read(MAX_SIZE+1)
        check_shape(raw)
        headers={k:response.headers.get(k) for k in
                 ("Date","Last-Modified","Content-Type")}
    (out/RAW_NAME).write_bytes(raw)
    manifest={
        "schema_id":SCHEMA,"source_id":SOURCE_ID,"source_url":URL,
        "relative_path":RAW_NAME,
        "raw_sha256":hashlib.sha256(raw).hexdigest(),
        "raw_bytes":len(raw),"http_status":200,
        "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
        "http_headers":headers,
        "printed_webpage_updated_date":"2019-03-01",
        "2019_original_revision_authenticated":False,
        "2019_asof_input_approved":False,
        "school_campus_relation":"SOURCE_CANDIDATE_UNREVIEWED",
        "event_shelter_building_identity":None,
        "event_shelter_site_pairs_approved":0,
        "prediction_accuracy_evaluated":False,
        "human_C_review":"NOT_RUN",
    }
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest


def verify(out):
    if {p.name for p in out.iterdir()}!={"manifest.json",RAW_NAME}:
        raise ArchiveError("unexpected raw archive members")
    m=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    expected={
        "schema_id":SCHEMA,"source_id":SOURCE_ID,"source_url":URL,
        "relative_path":RAW_NAME,"http_status":200,
        "printed_webpage_updated_date":"2019-03-01",
        "2019_original_revision_authenticated":False,
        "2019_asof_input_approved":False,
        "school_campus_relation":"SOURCE_CANDIDATE_UNREVIEWED",
        "event_shelter_building_identity":None,
        "event_shelter_site_pairs_approved":0,
        "prediction_accuracy_evaluated":False,
        "human_C_review":"NOT_RUN"}
    for k,v in expected.items():
        if m.get(k)!=v:
            raise ArchiveError("source identity or approval changed: "+k)
    raw=(out/RAW_NAME).read_bytes()
    check_shape(raw)
    if len(raw)!=m.get("raw_bytes") or hashlib.sha256(raw).hexdigest()!=m.get("raw_sha256"):
        raise ArchiveError("SHA256 original bytes mismatch")
    return {"status":"A_PRESENT_WEB_BYTES_VERIFIED__2019_ASOF_UNAPPROVED",
            "raw_sha256":m["raw_sha256"],"raw_bytes":len(raw)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--out-dir",type=Path)
    g.add_argument("--verify-dir",type=Path)
    a=p.parse_args(argv)
    try:
        result=archive(a.out_dir) if a.out_dir is not None else verify(a.verify_dir)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,urllib.error.URLError) as exc:
        print("EDOGAWA_2019_CAMPUS_A_ARCHIVE_FAILED: "+str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
