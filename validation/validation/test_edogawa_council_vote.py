"""Offline C guards for independently verified municipal assembly decision."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from verify_edogawa_council_vote import (
    NAME, MANIFEST, SOURCE_URL, IndependentVoteFailure, verify
)


def source_html(decision="可決", extra=""):
    return (
        "<html><body><table><tr><td>議案第63号</td><td>可決 全会一致</td></tr>"
        "<tr><td>議案第64号</td><td>旧下鎌田小学校校舎等解体工事請負契約</td>"
        "<td>令和8年7月1日 "+decision+" 全会一致"+extra+"</td></tr>"
        "<tr><td>議案第65号</td><td>可決 全会一致</td></tr></table></body></html>"
    ).encode("utf-8")


def fixture(path,raw=None):
    folder=Path(path)
    folder.mkdir()
    raw=source_html() if raw is None else raw
    (folder/NAME).write_bytes(raw)
    m={
        "purpose":"A_EDOGAWA_GIKAI_BILL64_SEPARATE_VOTE_ORIGINAL_UNAPPROVED",
        "captured_utc":datetime(2026,10,13,tzinfo=timezone.utc).isoformat(),
        "requested_url":SOURCE_URL,"final_url":SOURCE_URL,
        "original_filename":NAME,"original_bytes":len(raw),
        "original_sha256":sha256(raw).hexdigest(),
        "council_bill_64_original_pdf_is_a_separate_source":True,
        "source_row_machine_checked_not_independent_human_signoff":True,
        "vote_is_a_demolition_completion_record":False,
        "site_open_or_closed_verified":False,
        "site_identity_human_signed":False,
        "flood_classifications_added":0,
        "vote_row_observation":{
            "bill_number":64,"exact_vote_result_from_council_row":"可決",
            "unanimous_result_visible":True,"vote_date_original":"令和8年7月1日",
            "vote_has_no_current_building_condition":True,
        }
    }
    (folder/MANIFEST).write_text(json.dumps(m))
    return folder,m


def put(folder,m):
    (folder/MANIFEST).write_text(json.dumps(m))


class CouncilVoteTests(unittest.TestCase):
    def test_independent_official_vote_not_current_opening(self):
        with TemporaryDirectory() as root:
            folder,_=fixture(Path(root)/"council")
            x=verify(folder)
            self.assertTrue(x["bill_64_passed_unanimously_on_council_record"])
            self.assertEqual(x["current_external_inland_flood_standby"],"UNKNOWN")
            self.assertEqual(x["new_flood_candidates_or_exclusions"],0)

    def test_vote_for_other_bill_cannot_validate_this_one(self):
        with TemporaryDirectory() as root:
            folder,_=fixture(Path(root)/"council",source_html("否決"))
            with self.assertRaisesRegex(IndependentVoteFailure,"bill64 voted approved"):
                verify(folder)

    def test_new_html_version_with_same_manifest_refused(self):
        with TemporaryDirectory() as root:
            folder,_=fixture(Path(root)/"council")
            p=folder/NAME
            p.write_bytes(p.read_bytes()+b"garbage")
            with self.assertRaisesRegex(IndependentVoteFailure,"SHA256 mismatch"):
                verify(folder)

    def test_closure_fabrication_refused(self):
        with TemporaryDirectory() as root:
            folder,m=fixture(Path(root)/"council")
            m["site_open_or_closed_verified"]=True
            put(folder,m)
            with self.assertRaisesRegex(IndependentVoteFailure,"safety proof"):
                verify(folder)

    def test_wrong_meeting_cannot_substitute(self):
        with TemporaryDirectory() as root:
            folder,m=fixture(Path(root)/"council")
            m["final_url"]=m["final_url"].replace("2026%2F07%2F01","2026%2F07%2F02")
            put(folder,m)
            with self.assertRaisesRegex(IndependentVoteFailure,"requested council meeting"):
                verify(folder)

    def test_human_signoff_is_not_pretended(self):
        with TemporaryDirectory() as root:
            folder,m=fixture(Path(root)/"council")
            m["site_identity_human_signed"]=True
            put(folder,m)
            with self.assertRaisesRegex(IndependentVoteFailure,"safety proof"):
                verify(folder)

    def test_fake_flood_decision_fails(self):
        with TemporaryDirectory() as root:
            folder,m=fixture(Path(root)/"council")
            m["flood_classifications_added"]=1
            put(folder,m)
            with self.assertRaises(IndependentVoteFailure):
                verify(folder)


if __name__=="__main__":
    unittest.main()
