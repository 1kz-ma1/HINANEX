#!/usr/bin/env python3
"""Independent C source check: 2019-dated Edogawa SCHOOL campuses != shelter sites.

The current official HTML page lists regular/night school operating districts.
No current content or original-byte verification proves its 2019 revision,
or which campus was actually used as an October 2019 evacuation shelter.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unicodedata
import zipfile

A_SCHEMA="hinanex.a.edogawa_2019_campus_page_raw.v0.1"
SCHEMA="hinanex.c.edogawa_2019_school_campus_source_audit.v0.1"
SID="edogawa-komatsugawa2-rebuild-20190301"
URL="https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html"
RAW_NAME=SID+".html"
REQUIRED={
    "printed_page_update":"更新日:2019年3月1日",
    "official_page_title":"小松川第二中学校改築の概要",
    "school_change":"新校舎を小松川2丁目に建設・移転して学校運営しています",
    "night_operation":"夜間学級は平井3丁目で学校運営しています",
    "new_school_since":"平成30年4月より新校舎で学校運営しています",
    "regular_new_site_address":"所在地:小松川2丁目10番2号",
}


class CampusAuditError(ValueError):
    pass


def compact(value):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",value))


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0
        self.text=[]

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self.skip+=1

    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:
            self.skip-=1

    def handle_data(self,data):
        if not self.skip:
            self.text.append(data)


def evidence_from_html(source:bytes):
    if not source or len(source)>3*1024*1024 or b"<html" not in source[:8192].lower():
        raise CampusAuditError("not an official HTML original")
    try:
        page=source.decode("utf-8",errors="strict")
    except UnicodeError as exc:
        raise CampusAuditError("unexpected official HTML character encoding") from exc
    parser=PlainText()
    parser.feed(page)
    text=compact("".join(parser.text))
    for key,phrase in REQUIRED.items():
        if compact(phrase) not in text:
            raise CampusAuditError("required source claim missing or altered: "+key)
    return {
        "source_printed_update_date":"2019-03-01",
        "source_school_normal_campus_district":"小松川2丁目",
        "source_school_night_campus_district":"平井3丁目",
        "source_normal_campus_street_address":"小松川2丁目10番2号",
        "source_night_campus_street_address":None,
        "source_states_different_school_operation_districts":True,
        "new_school_started_in":"2018-04",
        "school_building_id_normal":None,
        "school_building_id_night":None,
        "physical_school_buildings_2019_independently_approved":False,
        "actual_shelter_used_building_for_205":None,
        "actual_shelter_used_building_for_11":None,
        "operational_group_is_physical_site":None,
        "shelter_identity_pairs_approved":0,
        "historical_page_revision_asof_approved":False,
        "prediction_accuracy_evaluated":False,
    }


def audit(archive:Path):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=2 or set(names)!={"manifest.json",RAW_NAME}:
            raise CampusAuditError("unexpected raw archive members")
        m=json.loads(z.read("manifest.json"))
        required_metadata={
            "schema_id":A_SCHEMA,"source_id":SID,"source_url":URL,
            "relative_path":RAW_NAME,"http_status":200,
            "printed_webpage_updated_date":"2019-03-01",
            "2019_original_revision_authenticated":False,
            "2019_asof_input_approved":False,
            "school_campus_relation":"SOURCE_CANDIDATE_UNREVIEWED",
            "event_shelter_building_identity":None,
            "event_shelter_site_pairs_approved":0,
            "prediction_accuracy_evaluated":False,
            "human_C_review":"NOT_RUN",
        }
        for k,expected in required_metadata.items():
            if m.get(k)!=expected:
                raise CampusAuditError("source origin or approval flag mismatch: "+k)
        raw=z.read(RAW_NAME)
        raw_sha=hashlib.sha256(raw).hexdigest()
        if len(raw)!=m.get("raw_bytes") or raw_sha!=m.get("raw_sha256"):
            raise CampusAuditError("independent original SHA256 or size mismatch")
        evidence=evidence_from_html(raw)
    return {
        "schema_id":SCHEMA,"status":"C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED",
        "official_url":URL,"raw_sha256":raw_sha,"raw_bytes":len(raw),
        **evidence,
        "human_historical_revision_review_required":True,
        "human_school_to_disaster_shelter_link_review_required":True,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-zip",type=Path,required=True)
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        out=audit(a.archive_zip)
        if a.report:
            if a.report.exists():
                raise CampusAuditError("refuse to overwrite independent report")
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(out,ensure_ascii=False,indent=2))
    except (OSError,ValueError,TypeError,zipfile.BadZipFile) as exc:
        print("C_2019_CAMPUS_PAGE_AUDIT_FAILED: "+str(exc),file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
