"""Fail-closed timeline tests. All sources synthetic except official metadata anchors."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from historical_school_directory_gate import assess, main, EXPECTED_SOURCES, SchoolRosterAuditError


def fixture():
    sources=[]
    for key, src in EXPECTED_SOURCES.items():
        sources.append({
            "source_id":key,"catalogue_url":src["url"],
            "publication_interval_jst":{
                "not_before":src["start"],"not_after":src["end"],
                "precision":src["precision"]},
            "historical_asof_approved":False,
            "raw_sha256":None,
            "physical_site_ids_approved":0,
            "source_contents_snapshot_verified":False,
            "source_2019_temporal_continuity_verified":False,
        })
    return {"schema_id":"hinanex.a.edogawa_historical_school_roster_candidates.v0.1",
            "case_id":"2019-typhoon19-edogawa",
            "as_of_jst":"2019-10-12T09:00:00+09:00",
            "input_asof_approved_count":0,
            "approved_physical_site_pairs":0,
            "candidates":sources}


class SchoolDirectoryTemporalTests(unittest.TestCase):
    def test_2018_preceding_period_is_still_unapproved(self):
        output=assess(fixture())
        cases={x["source_id"]:x for x in output["decisions"]}
        self.assertEqual(output["status"],"BLOCKED_ALL__NO_2019_ASOF_INPUT_APPROVED")
        self.assertEqual(output["eligible_historical_input_source_ids"],[])
        self.assertEqual(cases["tokyo-2018-school-directory-print"]["temporal_evidence_state"],
                         "PRIOR_PERIOD_CATALOGUED__VERSION_NOT_VERIFIED")
        self.assertEqual(cases["tokyo-2017-junior-high-open-data"]["replay_input_state"],"BLOCKED")
        self.assertIn("OLDER_2017_SCHOOL_ROSTER_STALENESS",
                      cases["tokyo-2017-junior-high-open-data"]["reason_codes"])

    def test_2019_october_window_overlaps_oct12_and_is_blocked(self):
        output=assess(fixture())
        row=next(x for x in output["decisions"] if x["source_id"]=="tokyo-2019-school-directory-print")
        self.assertEqual(row["temporal_evidence_state"],
                         "WINDOW_SPANS_ASOF__PUBLICATION_INSTANT_UNKNOWN")
        self.assertIn("DATE_WINDOW_OVERLAPS_DISASTER",row["reason_codes"])

    def test_november_record_is_post_event_reference(self):
        output=assess(fixture())
        row=next(x for x in output["decisions"] if x["source_id"]=="edogawa-2019-nov-school-placement")
        self.assertEqual(row["temporal_evidence_state"],"AFTER_ASOF__REFERENCE_ONLY")
        self.assertIn("POST_EVENT_PUBLICATION",row["reason_codes"])

    def test_fabricated_oct_first_publication_is_rejected(self):
        data=fixture()
        row=next(x for x in data["candidates"] if x["source_id"]=="tokyo-2019-school-directory-print")
        row["publication_interval_jst"]["not_after"]="2019-10-01"
        with self.assertRaisesRegex(SchoolRosterAuditError,"contradicts"):
            assess(data)

    def test_swapping_source_for_municipal_current_list_is_rejected(self):
        data=fixture()
        data["candidates"][0]["catalogue_url"]="https://www.city.edogawa.tokyo.jp/current.html"
        with self.assertRaisesRegex(SchoolRosterAuditError,"contradicts"):
            assess(data)

    def test_false_approval_hash_or_continuity_is_rejected(self):
        for field,value in [("historical_asof_approved",True),
                            ("raw_sha256","a"*64),
                            ("physical_site_ids_approved",1),
                            ("source_2019_temporal_continuity_verified",True),
                            ("source_contents_snapshot_verified",True)]:
            with self.subTest(field=field):
                data=fixture()
                data["candidates"][0][field]=value
                with self.assertRaisesRegex(SchoolRosterAuditError,"false approval"):
                    assess(data)

    def test_duplicate_candidate_is_rejected(self):
        data=fixture()
        data["candidates"][3]=copy.deepcopy(data["candidates"][0])
        with self.assertRaisesRegex(SchoolRosterAuditError,"duplicate"):
            assess(data)

    def test_require_explicit_jst_event_time(self):
        for s in ["2019-10-12T09:00:00", "2019-10-12T00:00:00Z",
                  "2019-10-11T09:00:00+09:00", "2019-10-12",
                  "wrong"]:
            with self.subTest(as_of=s):
                data=fixture()
                data["as_of_jst"]=s
                with self.assertRaises(SchoolRosterAuditError):
                    assess(data)

    def test_c_review_report_is_blocked_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"candidate.json"
            report=Path(tmp)/"C_report.json"
            f.write_text(json.dumps(fixture()),encoding="utf-8")
            self.assertEqual(main(["--ledger",str(f),"--out",str(report)]),2)
            parsed=json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(parsed["approved_facility_identity_pairs"],0)
            self.assertFalse(parsed["predictive_match_or_mismatch_approved"])
            self.assertEqual(main(["--ledger",str(f),"--out",str(report)]),1)


if __name__=="__main__":
    unittest.main()
