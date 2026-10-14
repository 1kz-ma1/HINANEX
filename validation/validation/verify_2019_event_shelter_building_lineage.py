#!/usr/bin/env python3
"""C independent join gate for 2019 Komatsugawa II event shelter buildings.

Uses *three prior independently produced C reports* and separate A research
metadata. Confirms their limited facts without converting a school campus,
source operational group, or later-revised equipment list into a 2019 shelter
building link. Not a 2019 prediction or human source-authentication approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA="hinanex.a.2019_komatsugawa_shelter_building_link_v0.1"
C_SCHEMA="hinanex.c.2019_event_shelter_building_link_gate.v0.1"
CASES={
    "ordinary_205":("小松川第二中学校",205),
    "night_11":("小松川第二中学校【夜間】",11),
}
POLICY={
    "campus2019":{
        "url":"https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html",
        "sha":"542d615df1df07139c37eab45d65e0ea3e4ac87783e868471f79746702a673df",
        "role":"SCHOOL_CAMPUS_OPERATIONS_REFERENCE","run":38350260260,
    },
    "newsletter2018":{
        "url":"https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf",
        "sha":"c44db027ac7d75444a5684e0a1c37973c6c6dc50fbe9974374c566713c219e33",
        "role":"PRE_EVENT_SCHOOL_NAMES_REFERENCE","run":38349472925,
    },
    "afteraction2020":{
        "url":"https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf",
        "sha":"89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380",
        "role":"POST_EVENT_OPERATIONAL_TRUTH","run":38344307696,
    },
}


class GateError(ValueError):
    pass


def require(value, condition, message):
    if not condition:
        raise GateError(message)
    return value


def check_source_list(ledger):
    if ledger.get("schema_id") != SCHEMA or ledger.get("case_id") != "2019-typhoon19-edogawa":
        raise GateError("unexpected A evidence schema/event")
    sources=ledger.get("sources")
    if not isinstance(sources,list) or len(sources)!=5:
        raise GateError("evidence sources must be exactly three C-audited + two contextual")
    by_id={}
    for src in sources:
        if not isinstance(src,dict) or not isinstance(src.get("id"),str):
            raise GateError("invalid evidence source")
        if src["id"] in by_id:
            raise GateError("duplicate official evidence identifier")
        by_id[src["id"]]=src
    if set(by_id)!=set(POLICY)|{"posteventmanual","schoolhistorylater"}:
        raise GateError("unexpected source added or missing")
    for source_id,anchor in POLICY.items():
        item=by_id[source_id]
        if (item.get("url")!=anchor["url"] or
            item.get("source_raw_sha256")!=anchor["sha"] or
            item.get("role")!=anchor["role"] or
            item.get("c_machine_audit_run")!=anchor["run"] or
            item.get("historical_asof_source_version_approved") is not False or
            item.get("verified_disaster_shelter_site") is not False):
            raise GateError("official evidence provenance/role/approval corrupted: "+source_id)
    manual=by_id["posteventmanual"]
    if (manual.get("role")!="LATER_REVISED_EQUIPMENT_ROSTER_ONLY" or
        manual.get("source_raw_sha256") is not None or
        manual.get("source_original_retrieved") is not False or
        manual.get("c_machine_audit_run") is not None or
        manual.get("historical_asof_source_version_approved") is not False or
        manual.get("verified_disaster_shelter_site") is not False):
        raise GateError("later equipment list promoted to unreviewed 2019 original")
    history=by_id["schoolhistorylater"]
    if (history.get("role")!="POST_EVENT_SCHOOL_BUILDING_LINEAGE_CONTEXT" or
        history.get("source_raw_sha256") is not None or
        history.get("source_original_retrieved") is not False or
        history.get("historical_asof_source_version_approved") is not False or
        history.get("verified_disaster_shelter_site") is not False):
        raise GateError("later school history promoted into 2019 input or event truth")
    return by_id


def check_c_reports(campus,newsletter,after):
    if (campus.get("schema_id")!="hinanex.c.edogawa_2019_school_campus_source_audit.v0.1"
        or campus.get("status")!="C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED"
        or campus.get("raw_sha256")!=POLICY["campus2019"]["sha"]
        or campus.get("official_url")!=POLICY["campus2019"]["url"]):
        raise GateError("C independent school-campus audit identity or source changed")
    for k,expected in {
        "source_school_normal_campus_district":"小松川2丁目",
        "source_school_night_campus_district":"平井3丁目",
        "source_normal_campus_street_address":"小松川2丁目10番2号",
        "source_night_campus_street_address":None,
        "source_states_different_school_operation_districts":True,
        "school_building_id_normal":None,"school_building_id_night":None,
        "actual_shelter_used_building_for_205":None,
        "actual_shelter_used_building_for_11":None,
        "operational_group_is_physical_site":None,
        "shelter_identity_pairs_approved":0,
        "historical_page_revision_asof_approved":False,
        "prediction_accuracy_evaluated":False,
    }.items():
        if campus.get(k)!=expected:
            raise GateError("campus school location illegally became event shelter building: "+k)
    if (newsletter.get("schema_id")!="hinanex.c.2018_edogawa_school_identity_gate.v0.1"
        or newsletter.get("status")!="C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED"
        or newsletter.get("source_sha256")!=POLICY["newsletter2018"]["sha"]
        or newsletter.get("source_url")!=POLICY["newsletter2018"]["url"]):
        raise GateError("C 2018 newsletter audit/source mismatch")
    for k,expected in {
        "day_school_label_present":True,
        "night_class_label_present_separately":True,
        "school_night_same_physical_site_2019":None,
        "school_night_distinct_campus_2019_approved":False,
        "physical_site_pairs_approved":0,
        "historical_asof_input_approved":False,
        "predictive_match_or_mismatch_evaluated":False,
    }.items():
        if newsletter.get(k)!=expected:
            raise GateError("C newsletter identity claim escalated: "+k)
    if (after.get("schema_id")!="hinanex.c.edogawa_2019_school_roster_source_audit.v0.1"
        or after.get("status")!="C_SOURCE_TO_OUTPUT_CONFIRMED__POST_EVENT_ONLY__NO_ASOF_APPROVAL"
        or after.get("source_sha256")!=POLICY["afteraction2020"]["sha"]):
        raise GateError("C post-event original/role mismatch")
    for k,expected in {
        "groups":65,"detail_rows":66,"evacuees":26761,
        "school_middle_night_detail_verified":True,
        "physical_facility_pairs_approved":0,
        "historical_asof_input_approved":False,
        "prediction_accuracy_evaluated":False,
    }.items():
        if after.get(k)!=expected:
            raise GateError("C school operations audit altered: "+k)


def assess(ledger,campus,newsletter,after):
    check_source_list(ledger)
    check_c_reports(campus,newsletter,after)
    if (ledger.get("historical_asof_input_approvals")!=0 or
        ledger.get("physical_event_shelter_site_pairs_approved")!=0 or
        ledger.get("predictive_match_mismatch_cases")!=0 or
        ledger.get("manual_equipment_data_used_for_2019") is not False or
        ledger.get("distinct_operational_detail_count")!=2 or
        ledger.get("source_operational_group_count")!=1):
        raise GateError("A cross-source state attempts fabricated approval or changed denominators")
    loc=ledger.get("stated_school_campus_relation",{})
    for k,expected in {
        "normal_district":"小松川2丁目",
        "normal_street_address":"小松川2丁目10番2号",
        "night_district":"平井3丁目",
        "night_street_address":None,
        "verified_actual_event_shelter_use":False,
    }.items():
        if loc.get(k)!=expected:
            raise GateError("A school source/shelter relation altered: "+k)
    rows=ledger.get("observations")
    if not isinstance(rows,list) or len(rows)!=2:
        raise GateError("two separately reported occupancies required")
    seen=set()
    for row in rows:
        rid=row.get("id")
        if rid in seen or rid not in CASES:
            raise GateError("duplicate or unexpected school occupancy detail")
        seen.add(rid)
        label,count=CASES[rid]
        if (row.get("source")!="afteraction2020" or
            row.get("operational_group")!="junior_high:02" or
            row.get("printed_name")!=label or
            row.get("reported_evacuees")!=count or
            row.get("confirmed_2019_shelter_building_id") is not None or
            row.get("confirmed_2019_shelter_address") is not None or
            row.get("building_site_pair_approved") is not False):
            raise GateError("report occupancy misjoined or transformed into physical shelter ID")
    if seen!=set(CASES):
        raise GateError("missing night/ordinary source detail")
    if not isinstance(ledger.get("evidence_needed_to_approve_actual_building_pair"),list) or len(ledger["evidence_needed_to_approve_actual_building_pair"])<2:
        raise GateError("missing evidence requirements for future human review")
    return {
        "schema_id":C_SCHEMA,"case_id":"2019-typhoon19-edogawa",
        "status":"BLOCKED_ACTUAL_EVENT_SHELTER_BUILDING_LINK__NEEDS_OFFICIAL_OPERATION_LOG",
        "c_source_reports_cross_checked":3,
        "school_campus_operation_districts_source_verified":True,
        "day_and_night_operation_rows_independently_verified":True,
        "distinct_source_reporting_rows":2,
        "source_operational_groups":1,
        "identified_physical_shelter_buildings":0,
        "approved_occupancy_to_building_pairs":0,
        "historical_asof_input_approvals":0,
        "predictive_match_mismatch_cases":0,
        "source_roles":{
            "campus2019":"SCHOOL_CAMPUS_REFERENCE_NOT_EVENT_SHELTER",
            "newsletter2018":"SCHOOL_NAMES_REFERENCE_NOT_EVENT_SHELTER",
            "afteraction2020":"POST_EVENT_OPERATIONAL_TRUTH_NOT_PREDICTION_INPUT",
            "posteventmanual":"LATER_REVISED_ROSTER_NOT_2019_INPUT",
            "schoolhistorylater":"RETROSPECTIVE_HISTORY_NOT_2019_INPUT",
        },
        "decisions":[{
            "occupancy_detail_id":rid,
            "reported_persons":count,
            "actual_2019_shelter_building_id":None,
            "source_school_campus_is_same_as_2019_shelter":None,
            "status":"BLOCKED_NO_BUILDING_LEVEL_EVENT_SOURCE",
            "reason_codes":[
                "CAMPUS_LOCATION_IS_NOT_ACTUAL_SHELTER_USE",
                "OPERATIONAL_GROUP_IS_NOT_PHYSICAL_BUILDING_ID",
                "NO_2019_10_12_OCCUPANCY_TO_BUILDING_TRACE",
                "HISTORICAL_SOURCE_REVISION_NOT_HUMAN_APPROVED",
            ],
        } for rid,(_,count) in CASES.items()],
        "human_C_historical_building_identity_review_required":True,
        "prediction_accuracy_evaluated":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a-ledger",type=Path,required=True)
    p.add_argument("--c-campus-report",type=Path,required=True)
    p.add_argument("--c-newsletter-report",type=Path,required=True)
    p.add_argument("--c-ops-report",type=Path,required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        b=[x.read_bytes() for x in
           (a.a_ledger,a.c_campus_report,a.c_newsletter_report,a.c_ops_report)]
        report=assess(*(json.loads(v) for v in b))
        report["input_manifest_sha256"]={
            k:hashlib.sha256(v).hexdigest() for k,v in
            zip(("a_ledger","c_campus_report","c_newsletter_report","c_ops_report"),b)}
        body=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            if a.out.exists():
                raise GateError("refuse to overwrite C independent comparison report")
            a.out.parent.mkdir(parents=True,exist_ok=True)
            a.out.write_text(body,encoding="utf-8")
        print(body)
        return 2  # Expected result: no approved 2019 event building match.
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        print("C_EVENT_BUILDING_LINK_GATE_FAILED: "+str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
