"""Offline synthetic tests: successful rendering is NOT prediction acceptance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from generate_20261022_t0_evidence_brief import (
    ARTIFACTS, EvidenceError, OFFICIAL, compose, html_document,
    markdown, produce, read_c_report
)


def scenarios():
    school={
        "schema_id":ARTIFACTS["school"][1],
        "status":"C_SOURCE_TO_OUTPUT_CONFIRMED__POST_EVENT_ONLY__NO_ASOF_APPROVAL",
        "source_sha256":ARTIFACTS["school"][2],
        "groups":65,"detail_rows":66,"evacuees":26761,
        "physical_facility_pairs_approved":0,"historical_asof_input_approved":False,
        "prediction_accuracy_evaluated":False,"school_middle_night_detail_verified":True
    }
    campus={
        "schema_id":ARTIFACTS["campus"][1],
        "status":"C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED",
        "raw_sha256":ARTIFACTS["campus"][2],
        "source_school_normal_campus_district":"小松川2丁目",
        "source_school_night_campus_district":"平井3丁目",
        "source_normal_campus_street_address":"小松川2丁目10番2号",
        "source_night_campus_street_address":None,
        "actual_shelter_used_building_for_205":None,
        "actual_shelter_used_building_for_11":None,
        "historical_page_revision_asof_approved":False,
        "shelter_identity_pairs_approved":0
    }
    newsletter={
        "schema_id":ARTIFACTS["newsletter"][1],
        "status":"C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED",
        "source_sha256":ARTIFACTS["newsletter"][2],
        "day_school_label_present":True,
        "night_class_label_present_separately":True,
        "school_night_same_physical_site_2019":None,
        "physical_site_pairs_approved":0,
        "historical_asof_input_approved":False
    }
    cross={
        "schema_id":ARTIFACTS["cross"][1],
        "status":"BLOCKED_ACTUAL_EVENT_SHELTER_BUILDING_LINK__NEEDS_OFFICIAL_OPERATION_LOG",
        "c_source_reports_cross_checked":3,
        "source_operational_groups":1,
        "distinct_source_reporting_rows":2,
        "identified_physical_shelter_buildings":0,
        "approved_occupancy_to_building_pairs":0,
        "historical_asof_input_approvals":0,
        "predictive_match_mismatch_cases":0,
        "prediction_accuracy_evaluated":False,
        "decisions":[
            {"occupancy_detail_id":"ordinary_205","reported_persons":205,
             "actual_2019_shelter_building_id":None,
             "status":"BLOCKED_NO_BUILDING_LEVEL_EVENT_SOURCE"},
            {"occupancy_detail_id":"night_11","reported_persons":11,
             "actual_2019_shelter_building_id":None,
             "status":"BLOCKED_NO_BUILDING_LEVEL_EVENT_SOURCE"}
        ],
        "input_manifest_sha256":{
            "a_ledger":"0"*64,"c_campus_report":"0"*64,
            "c_newsletter_report":"0"*64,"c_ops_report":"0"*64}
    }
    return school,campus,newsletter,cross


class EvidenceDemoTests(unittest.TestCase):
    def test_t0_success_is_not_predicted_match(self):
        o=compose(*scenarios())
        self.assertEqual(o["school_operational_groups"],65)
        self.assertEqual(o["school_occupancy_detail_rows"],66)
        self.assertEqual(o["approved_actual_building_pairs"],0)
        self.assertEqual(o["t1_opening_prediction_accuracy"],"NOT_EVALUABLE")
        self.assertEqual(o["t2_hazard_prediction_accuracy"],"NOT_RUN")
        self.assertIsNone(o["prediction_denominator"])
        self.assertEqual(o["foundation_89_acceptance"],"NOT_SIGNED_OFF_BY_THIS_REPORT")
        self.assertTrue(o["school_diary_operational_leads_not_source_audited"])
        self.assertIn("未評価",html_document(o))
        self.assertIn("T0",markdown(o))

    def test_any_65_66_disagreement_rejected(self):
        a=list(scenarios())
        a[0]["detail_rows"]=65
        with self.assertRaisesRegex(EvidenceError,"detail_rows"):
            compose(*a)

    def test_2019_original_revision_forgery_rejected(self):
        a=list(scenarios())
        a[1]["historical_page_revision_asof_approved"]=True
        with self.assertRaisesRegex(EvidenceError,"asof_approved"):
            compose(*a)

    def test_school_address_as_shelter_rejected(self):
        a=list(scenarios())
        a[1]["actual_shelter_used_building_for_205"]="小松川2丁目10番2号"
        with self.assertRaisesRegex(EvidenceError,"actual_shelter"):
            compose(*a)

    def test_cross_source_predicted_matches_rejected(self):
        a=list(scenarios())
        a[3]["predictive_match_mismatch_cases"]=1
        with self.assertRaisesRegex(EvidenceError,"predictive_match"):
            compose(*a)

    def test_merging_night_detail_rejected(self):
        a=list(scenarios())
        a[3]["decisions"].pop()
        with self.assertRaisesRegex(EvidenceError,"two details"):
            compose(*a)

    def test_wrong_c_status_rejected(self):
        a=list(scenarios())
        a[2]["status"]="C_FULLY_APPROVED"
        with self.assertRaisesRegex(EvidenceError,"newsletter T0"):
            compose(*a)

    def test_false_physical_campus_equivalence_rejected(self):
        a=list(scenarios())
        a[2]["school_night_same_physical_site_2019"]=True
        with self.assertRaisesRegex(EvidenceError,"school_night"):
            compose(*a)

    def test_reject_missing_or_extra_artifact_payloads(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"r.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("wrong.json","{}")
            with self.assertRaisesRegex(EvidenceError,"unexpected C artifact"):
                read_c_report(p,"school")

    def test_generated_files_and_immutable_cross_report_revision(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            objects=list(scenarios())
            report_digests={}
            paths={}
            for key,data in zip(ARTIFACTS,objects):
                paths[key]=td/(key+".zip")
                blob=json.dumps(data,ensure_ascii=False).encode("utf-8")
                with zipfile.ZipFile(paths[key],"w") as z:
                    z.writestr(ARTIFACTS[key][0],blob)
                report_digests[key]=hashlib.sha256(blob).hexdigest()
            # Cross archive must be emitted AFTER recording source JSON digests.
            objects[3]["input_manifest_sha256"].update({
                "c_ops_report":report_digests["school"],
                "c_campus_report":report_digests["campus"],
                "c_newsletter_report":report_digests["newsletter"]})
            with zipfile.ZipFile(paths["cross"],"w") as z:
                z.writestr(ARTIFACTS["cross"][0],json.dumps(objects[3]))
            out=td/"out"
            r=produce(paths,out)
            self.assertEqual(r["approved_actual_building_pairs"],0)
            self.assertEqual(set(p.name for p in out.iterdir()),{
                "C_20261022_evidence_manifest.json",
                "C_20261022_60sec_guide.md",
                "C_20261022_offline_evidence.html"})
            self.assertIn("<!doctype html>",(out/"C_20261022_offline_evidence.html").read_text())
            with self.assertRaisesRegex(EvidenceError,"overwrite"):
                produce(paths,out)
            # Mutate one legitimate C status field, re-sign its isolated ZIP only:
            # provenance must still fail because cross-report digest disagrees.
            objects[0]["school_middle_night_detail_verified"]=True
            objects[0]["evacuees"]=26761  # valid values, but extra harmless field
            objects[0]["note"]="unreviewed mixed revision"
            with zipfile.ZipFile(paths["school"],"w") as z:
                z.writestr(ARTIFACTS["school"][0],json.dumps(objects[0],ensure_ascii=False))
            with self.assertRaisesRegex(EvidenceError,"mixed independent C report"):
                produce(paths,td/"other")


if __name__=="__main__":
    unittest.main()
