"""Offline fail-closed cross-evidence tests. Synthetic reports are NOT source approvals."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verify_2019_event_shelter_building_lineage import (
    assess, main, POLICY, CASES, GateError
)


def fixtures():
    sources=[
        {"id":sid,"role":p["role"],"url":p["url"],
         "source_raw_sha256":p["sha"],"c_machine_audit_run":p["run"],
         "historical_asof_source_version_approved":False,
         "verified_disaster_shelter_site":False}
        for sid,p in POLICY.items()
    ]
    sources+= [
        {"id":"posteventmanual","role":"LATER_REVISED_EQUIPMENT_ROSTER_ONLY",
         "source_raw_sha256":None,"source_original_retrieved":False,
         "c_machine_audit_run":None,
         "historical_asof_source_version_approved":False,
         "verified_disaster_shelter_site":False},
        {"id":"schoolhistorylater","role":"POST_EVENT_SCHOOL_BUILDING_LINEAGE_CONTEXT",
         "source_raw_sha256":None,"source_original_retrieved":False,
         "historical_asof_source_version_approved":False,
         "verified_disaster_shelter_site":False}
    ]
    ledger={
        "schema_id":"hinanex.a.2019_komatsugawa_shelter_building_link_v0.1",
        "case_id":"2019-typhoon19-edogawa","sources":sources,
        "distinct_operational_detail_count":2,"source_operational_group_count":1,
        "historical_asof_input_approvals":0,
        "physical_event_shelter_site_pairs_approved":0,
        "predictive_match_mismatch_cases":0,
        "manual_equipment_data_used_for_2019":False,
        "stated_school_campus_relation":{
            "normal_district":"小松川2丁目",
            "normal_street_address":"小松川2丁目10番2号",
            "night_district":"平井3丁目",
            "night_street_address":None,
            "verified_actual_event_shelter_use":False
        },
        "observations":[
            {"id":rid,"source":"afteraction2020",
             "operational_group":"junior_high:02",
             "printed_name":name,"reported_evacuees":count,
             "confirmed_2019_shelter_building_id":None,
             "confirmed_2019_shelter_address":None,
             "building_site_pair_approved":False}
            for rid,(name,count) in CASES.items()
        ],
        "evidence_needed_to_approve_actual_building_pair":[
            "independent 2019 official occupancy log","source-confirmed building identifier"
        ]
    }
    campus={
        "schema_id":"hinanex.c.edogawa_2019_school_campus_source_audit.v0.1",
        "status":"C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED",
        "raw_sha256":POLICY["campus2019"]["sha"],
        "official_url":POLICY["campus2019"]["url"],
        "source_school_normal_campus_district":"小松川2丁目",
        "source_school_night_campus_district":"平井3丁目",
        "source_normal_campus_street_address":"小松川2丁目10番2号",
        "source_night_campus_street_address":None,
        "source_states_different_school_operation_districts":True,
        "school_building_id_normal":None,
        "school_building_id_night":None,
        "actual_shelter_used_building_for_205":None,
        "actual_shelter_used_building_for_11":None,
        "operational_group_is_physical_site":None,
        "shelter_identity_pairs_approved":0,
        "historical_page_revision_asof_approved":False,
        "prediction_accuracy_evaluated":False,
    }
    news={
        "schema_id":"hinanex.c.2018_edogawa_school_identity_gate.v0.1",
        "status":"C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED",
        "source_sha256":POLICY["newsletter2018"]["sha"],
        "source_url":POLICY["newsletter2018"]["url"],
        "day_school_label_present":True,
        "night_class_label_present_separately":True,
        "school_night_same_physical_site_2019":None,
        "school_night_distinct_campus_2019_approved":False,
        "physical_site_pairs_approved":0,
        "historical_asof_input_approved":False,
        "predictive_match_or_mismatch_evaluated":False,
    }
    after={
        "schema_id":"hinanex.c.edogawa_2019_school_roster_source_audit.v0.1",
        "status":"C_SOURCE_TO_OUTPUT_CONFIRMED__POST_EVENT_ONLY__NO_ASOF_APPROVAL",
        "source_sha256":POLICY["afteraction2020"]["sha"],
        "groups":65,"detail_rows":66,"evacuees":26761,
        "school_middle_night_detail_verified":True,
        "physical_facility_pairs_approved":0,
        "historical_asof_input_approved":False,
        "prediction_accuracy_evaluated":False,
    }
    return ledger,campus,news,after


class ActualBuildingJoinGateTests(unittest.TestCase):
    def test_valid_cross_report_sources_must_still_abstain(self):
        r=assess(*fixtures())
        self.assertEqual(r["c_source_reports_cross_checked"],3)
        self.assertEqual(r["status"],
             "BLOCKED_ACTUAL_EVENT_SHELTER_BUILDING_LINK__NEEDS_OFFICIAL_OPERATION_LOG")
        self.assertEqual(r["source_operational_groups"],1)
        self.assertEqual(r["distinct_source_reporting_rows"],2)
        self.assertEqual(r["approved_occupancy_to_building_pairs"],0)
        self.assertEqual(len(r["decisions"]),2)
        self.assertTrue(all(x["actual_2019_shelter_building_id"] is None
                            for x in r["decisions"]))
        self.assertFalse(r["prediction_accuracy_evaluated"])

    def test_false_normal_school_address_as_shelter_is_rejected(self):
        payload=list(fixtures())
        payload[0]["observations"][0]["confirmed_2019_shelter_address"]="小松川2丁目10番2号"
        with self.assertRaisesRegex(GateError,"misjoined"):
            assess(*payload)

    def test_old_hirai_address_as_night_evacuation_building_rejected(self):
        payload=list(fixtures())
        payload[0]["observations"][1]["confirmed_2019_shelter_building_id"]="old-hirai-campus"
        with self.assertRaisesRegex(GateError,"misjoined"):
            assess(*payload)

    def test_later_equipment_manual_cannot_backdate_a_2019_building(self):
        payload=list(fixtures())
        manual=next(s for s in payload[0]["sources"] if s["id"]=="posteventmanual")
        manual["historical_asof_source_version_approved"]=True
        with self.assertRaisesRegex(GateError,"later equipment"):
            assess(*payload)

    def test_separate_night_record_cannot_disappear(self):
        payload=list(fixtures())
        payload[0]["observations"].pop()
        with self.assertRaisesRegex(GateError,"two separately"):
            assess(*payload)

    def test_changed_original_digest_is_rejected(self):
        payload=list(fixtures())
        payload[0]["sources"][0]["source_raw_sha256"]="f"*64
        with self.assertRaisesRegex(GateError,"provenance"):
            assess(*payload)

    def test_unapproved_C_report_cannot_forge_shelter_mapping(self):
        payload=list(fixtures())
        payload[1]["actual_shelter_used_building_for_11"]="平井3丁目20番1号"
        with self.assertRaisesRegex(GateError,"illegally became"):
            assess(*payload)

    def test_verified_2019_page_claim_is_not_authenticated_2019_snapshot(self):
        payload=list(fixtures())
        payload[1]["historical_page_revision_asof_approved"]=True
        with self.assertRaisesRegex(GateError,"illegally became"):
            assess(*payload)

    def test_65_group_66_detail_truth_denominator_is_preserved(self):
        payload=list(fixtures())
        payload[3]["detail_rows"]=65
        with self.assertRaisesRegex(GateError,"audit altered"):
            assess(*payload)

    def test_role_swapping_2020_truth_into_future_prediction_input_rejected(self):
        payload=list(fixtures())
        src=next(s for s in payload[0]["sources"] if s["id"]=="afteraction2020")
        src["role"]="PREDICTION_INPUT"
        with self.assertRaisesRegex(GateError,"provenance"):
            assess(*payload)

    def test_cli_expected_blocked_exit2_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/f"{i}.json" for i in range(4)]
            out=Path(tmp)/"report.json"
            for p,v in zip(paths,fixtures()):
                p.write_text(json.dumps(v,ensure_ascii=False),encoding="utf-8")
            cmd=sum(([flag,str(path)] for flag,path in zip(
                ("--a-ledger","--c-campus-report","--c-newsletter-report","--c-ops-report"),
                 paths)),[])
            self.assertEqual(main(cmd+["--out",str(out)]),2)
            self.assertEqual(json.loads(out.read_text())["approved_occupancy_to_building_pairs"],0)
            self.assertEqual(main(cmd+["--out",str(out)]),1)


if __name__=="__main__":
    unittest.main()
