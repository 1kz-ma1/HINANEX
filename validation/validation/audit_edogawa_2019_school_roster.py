#!/usr/bin/env python3
"""C independent source-to-output audit for the post-event Edogawa school roster.

Never treats these records as 2019-as-of prediction input, confirmed physical
sites, or shelter-safety proof. Does not import A extraction implementation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

EXPECTED_SHA = "89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380"
EXPECTED_URL = "https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf"
SCHEMA = "hinanex.a.edogawa_2019_school_operational_roster.v0.1"
PAGE = 2
GROUPS = {"elementary": 42, "junior_high": 21, "other": 2}
DETAILS = {"elementary": 42, "junior_high": 22, "other": 2}
EVAC = {"elementary": 19061, "junior_high": 7564, "other": 136}
STAFF_PRESENT = {"elementary":397, "junior_high":192, "other":12}
STAFF_TOTAL = {"elementary":512, "junior_high":261, "other":16}

RANGES = {
    "elementary": {"side":"left","name":(61,164),"group":(44,61),
                   "evac":(164,200),"present":(200,232),
                   "total":(232,253),"percent":(253,282),"y":(100,662)},
    "junior_high": {"side":"right","name":(315,426),"group":(300,315),
                    "evac":(428,458),"present":(458,485),
                    "total":(485,507),"percent":(507,535),"y":(100,398)},
    "other": {"side":"right","name":(315,426),"group":(300,315),
              "evac":(428,458),"present":(458,485),
              "total":(485,507),"percent":(507,535),"y":(449,478)},
}


class AuditError(ValueError):
    pass


def center_y(word):
    return (word[1] + word[3]) / 2


def position_word(word, cat, field, y=None, tolerance=1.3):
    a, b = RANGES[cat][field]
    lo, hi = RANGES[cat]["y"]
    return (a <= word[0] < b and lo < center_y(word) < hi
            and (y is None or abs(center_y(word)-y) <= tolerance))


def source_observations(words):
    """Recover all name coordinates and category row markers directly from PDF."""
    answer = {}
    for category in GROUPS:
        names = sorted([(center_y(w), w[4]) for w in words
                        if position_word(w, category, "name") and "学校" in w[4]])
        markers = sorted([(center_y(w), int(w[4])) for w in words
                          if position_word(w, category, "group") and w[4].isdigit()])
        if len(names) != DETAILS[category]:
            raise AuditError(f"{category}: C independently found incorrect named row count")
        if [n for _, n in markers] != list(range(1, GROUPS[category]+1)):
            raise AuditError(f"{category}: C independent numbered groups inconsistent")
        answer[category] = {"names":names, "markers":markers}
    return answer


def audited_number(words, category, field, y):
    candidates = [w[4] for w in words if position_word(w,category,field,y)]
    if len(candidates) != 1:
        raise AuditError(f"source {category} row has missing/ambiguous {field}")
    original = candidates[0]
    pat = r"\d+%" if field == "percent" else r"\d[\d,]*"
    if not re.fullmatch(pat,original):
        raise AuditError("source numeric cell malformed")
    return int(original.replace(",","").rstrip("%"))


def validate_original_words(words, report):
    observed = source_observations(words)
    details = report.get("detail_rows")
    groups = report.get("operational_groups")
    if not isinstance(details,list) or not isinstance(groups,list):
        raise AuditError("A evidence records missing")
    if len(details) != 66 or len(groups) != 65:
        raise AuditError("65 group / 66 source row coverage violated")
    if len({r.get("source_detail_id") for r in details}) != len(details):
        raise AuditError("duplicated detail trace")
    if len({r.get("source_group_id") for r in groups}) != len(groups):
        raise AuditError("duplicated operational unit ID")
    if any(row.get("normalized_facility_id") is not None
           or row.get("facility_identity_review_state") != "NOT_REVIEWED"
           for row in details):
        raise AuditError("detail attempts unapproved physical identity")
    if any(g.get("facility_id") is not None or
           g.get("is_confirmed_physical_site") is not False or
           g.get("facility_identity_review_state") != "NOT_REVIEWED"
           for g in groups):
        raise AuditError("group attempts unapproved physical identity")
    names_seen = defaultdict(list)
    expected_for_groups = Counter()
    for row in details:
        cat = row.get("category")
        if cat not in GROUPS or row.get("source_page_index") != PAGE:
            raise AuditError("invalid source page or category")
        y = row.get("source_y_pt")
        if isinstance(y,bool) or not isinstance(y,(float,int)):
            raise AuditError("invalid PDF line trace position")
        name = row.get("printed_name")
        if not isinstance(name,str) or not name.strip():
            raise AuditError("missing original source label")
        names = [(origin_y, original_name)
                 for origin_y,original_name in observed[cat]["names"]
                 if original_name == name and abs(origin_y-y) < 0.45]
        if len(names) != 1:
            raise AuditError("PDF source name/coordinate mismatch")
        printed_marker = min(observed[cat]["markers"],
                             key=lambda x:abs(x[0]-y))
        if abs(printed_marker[0]-y)>8 or row.get("source_group_number") != printed_marker[1]:
            raise AuditError("name assigned to wrong official printed group number")
        n=printed_marker[1]
        gid = f"{cat}:{n:02d}"
        if row.get("source_group_id") != gid:
            raise AuditError("source operational group ID altered")
        numbers = {
            "evacuees_reported": audited_number(words,cat,"evac",y),
            "municipal_staff_attended": audited_number(words,cat,"present",y),
            "municipal_staff_total": audited_number(words,cat,"total",y),
            "staff_attendance_rate_displayed": audited_number(words,cat,"percent",y),
        }
        for key,actual in numbers.items():
            if row.get(key) != actual:
                raise AuditError(f"report cell mismatches official source PDF: {key}")
        if row.get("source_detail_id") not in (gid+":1",gid+":2"):
            raise AuditError("unexpected detail lineage key")
        names_seen[cat].append((round(y,1),name))
        expected_for_groups[gid] += 1
    for category in GROUPS:
        expected_names = sorted((round(y,1),name) for y,name in observed[category]["names"])
        if sorted(names_seen[category]) != expected_names:
            raise AuditError("PDF named row coverage differs from A evidence")
        if sum(r["evacuees_reported"] for r in details if r["category"]==category) != EVAC[category]:
            raise AuditError("C independently rejected category evacuee subtotal")
        if sum(r["municipal_staff_attended"] for r in details if r["category"]==category) != STAFF_PRESENT[category]:
            raise AuditError("C independently rejected staff attendance subtotal")
        if sum(r["municipal_staff_total"] for r in details if r["category"]==category) != STAFF_TOTAL[category]:
            raise AuditError("C independently rejected total staff subtotal")
    for g in groups:
        cat=g.get("category")
        gid=g.get("source_group_id")
        if cat not in GROUPS or not isinstance(gid,str):
            raise AuditError("invalid operational unit")
        if not re.fullmatch(fr"{cat}:\d{{2}}",gid):
            raise AuditError("unexpected group identifier")
        supporting = [r for r in details if r["source_group_id"]==gid]
        target_count = 2 if gid=="junior_high:02" else 1
        if (len(supporting) != target_count or g.get("detail_count") != target_count
                or g.get("evacuees_reported") != sum(x["evacuees_reported"] for x in supporting)
                or g.get("printed_group_number") != supporting[0]["source_group_number"]):
            raise AuditError("source detail grouping or total inconsistent")
    for cat,n in GROUPS.items():
        if sum(g["category"]==cat for g in groups)!=n:
            raise AuditError("category operational group count mismatch")
    night = [r for r in details if r["source_group_id"]=="junior_high:02"]
    if sorted((r["printed_name"],r["evacuees_reported"]) for r in night) != [
        ("小松川第二中学校",205),("小松川第二中学校【夜間】",11)]:
        raise AuditError("night class separate detail missing or changed")
    return {"groups":len(groups),"detail_rows":len(details),
            "evacuees":sum(r["evacuees_reported"] for r in details)}


def audit(pdf_raw:bytes, a_json:bytes) ->dict:
    raw_sha=hashlib.sha256(pdf_raw).hexdigest()
    if raw_sha!=EXPECTED_SHA:
        raise AuditError("source original bytes changed without C review")
    report=json.loads(a_json)
    if (report.get("schema_id")!=SCHEMA or report.get("source_raw_sha256")!=raw_sha
            or report.get("source_url")!=EXPECTED_URL
            or report.get("evidence_role")!="POST_EVENT_TRUTH_CANDIDATE_ONLY"
            or report.get("asof_input_approved") is not False
            or report.get("facility_id_pairs_approved") != 0
            or report.get("source_published_at_2019_event_time") is not False):
        raise AuditError("wrong source/version or unapproved input/identity claim")
    if (report.get("operational_groups_total")!=65
            or report.get("detail_rows_total")!=66
            or report.get("reported_evacuations_total")!=26761
            or report.get("source_page_index") != PAGE):
        raise AuditError("reported count or trace altered")
    try:
        import fitz
    except ImportError as exc:
        raise AuditError("PyMuPDF required for independent PDF inspection") from exc
    with fitz.open(stream=pdf_raw,filetype="pdf") as pdf:
        if len(pdf)<3:
            raise AuditError("PDF page containing operational table is missing")
        page=pdf[PAGE]
        source_words=page.get_text("words")
        source_text=page.get_text()
        if not all(x in source_text for x in ["小学校計","中学校計","その他計","26,761","19,061","7,564","136"]):
            raise AuditError("official source printed subtotals changed")
        results=validate_original_words(source_words,report)
        creation_date=pdf.metadata.get("creationDate")
    return {
        "schema_id":"hinanex.c.edogawa_2019_school_roster_source_audit.v0.1",
        "status":"C_SOURCE_TO_OUTPUT_CONFIRMED__POST_EVENT_ONLY__NO_ASOF_APPROVAL",
        "source_sha256":raw_sha,"source_pdf_creation_date":creation_date,
        **results,
        "school_middle_night_detail_verified":True,
        "physical_facility_pairs_approved":0,
        "historical_asof_input_approved":False,
        "prediction_accuracy_evaluated":False,
        "human_c_semantic_review_required":True,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-pdf",type=Path,required=True)
    p.add_argument("--a-roster-json",type=Path,required=True)
    p.add_argument("--report",type=Path)
    a=p.parse_args(argv)
    try:
        output=audit(a.source_pdf.read_bytes(),a.a_roster_json.read_bytes())
        body=json.dumps(output,ensure_ascii=False,indent=2)+"\n"
        if a.report:
            if a.report.exists():
                raise AuditError("refuse to overwrite independent C report")
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(body,encoding="utf-8")
        print(body)
        return 0
    except (OSError,ValueError,TypeError) as exc:
        print("C_2019_SCHOOL_ROSTER_AUDIT_FAILED: "+str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
