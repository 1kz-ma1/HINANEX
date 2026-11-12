"""Synthetic C safety checks; live PDF inspection runs in isolated hosted job."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from verify_edogawa_demolition_contract import (verify,CouncilAuditFailure,FLAGS,
                                                 NAME,URL,VOTE_PAGE,PURPOSE)


def fixture(path):
    path=Path(path)
    path.mkdir()
    raw=b"%PDF-1.7\n"+b"% mocked official source\n"*12+b"%%EOF\n"
    (path/NAME).write_bytes(raw)
    manifest={
        "purpose":PURPOSE,
        "captured_utc":datetime(2026,10,13,tzinfo=timezone.utc).isoformat(),
        "bill_pdf_url":URL,"final_pdf_url":URL,"source_filename":NAME,
        "approval_record_page_for_separate_human_review":VOTE_PAGE,
        "source_size_bytes":len(raw),"source_sha256":sha256(raw).hexdigest(),
        "bill_number":64,"bill_vote_status_derived_from_pdf":None,
        "actual_construction_progress_human_confirmation_required":True,
        "official_pdf_page_content_independent_c_review_required":True,
        **FLAGS,
    }
    (path/"council_source_manifest_UNAPPROVED.json").write_text(json.dumps(manifest))
    return path,manifest


def save(path,m):
    (path/"council_source_manifest_UNAPPROVED.json").write_text(json.dumps(m))


def synthetic_verify(p):
    with patch("verify_edogawa_demolition_contract.pdf_details",
               return_value={"construction_started_or_finished_verified":False}):
        return verify(p)


class CouncilContractCTests(TestCase):
    def test_valid_archive_stays_unapproved(self):
        with TemporaryDirectory() as d:
            p,_=fixture(Path(d)/"source")
            z=synthetic_verify(p)
            self.assertEqual(z["demolition_completion_status"],"UNKNOWN")
            self.assertEqual(z["C_human_same_building_identity_pairs_approved"],0)
            self.assertEqual(z["D_flood_candidate_or_excluded_added"],0)

    def test_original_digest_tampering_rejected(self):
        with TemporaryDirectory() as d:
            p,_=fixture(Path(d)/"source")
            file=p/NAME
            file.write_bytes(file.read_bytes()+b"modified")
            with self.assertRaisesRegex(CouncilAuditFailure,"digest"):
                synthetic_verify(p)

    def test_fake_council_vote_from_pdf_rejected(self):
        with TemporaryDirectory() as d:
            p,m=fixture(Path(d)/"source")
            m["bill_vote_status_derived_from_pdf"]="PASSED"
            save(p,m)
            with self.assertRaisesRegex(CouncilAuditFailure,"source claims"):
                synthetic_verify(p)

    def test_false_demolition_completion_rejected(self):
        with TemporaryDirectory() as d:
            p,m=fixture(Path(d)/"source")
            m["demolition_work_completed_verified"]=True
            save(p,m)
            with self.assertRaisesRegex(CouncilAuditFailure,"source claims"):
                synthetic_verify(p)

    def test_false_flood_exclusion_rejected(self):
        with TemporaryDirectory() as d:
            p,m=fixture(Path(d)/"source")
            m["flood_scenario_status_changes"]=1
            save(p,m)
            with self.assertRaises(CouncilAuditFailure):
                synthetic_verify(p)

    def test_alternate_council_url_rejected(self):
        with TemporaryDirectory() as d:
            p,m=fixture(Path(d)/"source")
            m["final_pdf_url"]="https://www.gikai.city.edogawa.tokyo.jp/other.pdf"
            save(p,m)
            with self.assertRaises(CouncilAuditFailure):
                synthetic_verify(p)

    def test_extra_original_rejected(self):
        with TemporaryDirectory() as d:
            p,_=fixture(Path(d)/"source")
            (p/"unexpected.pdf").write_bytes(b"pdf")
            with self.assertRaisesRegex(CouncilAuditFailure,"inventory"):
                synthetic_verify(p)


if __name__=="__main__":
    main()
