"""Synthetic C negative tests. Campus layout is not shelter-use evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_edogawa_2019_campus_source import (
    A_SCHEMA, SID, URL, RAW_NAME, CampusAuditError, audit, evidence_from_html
)


def mock_source():
    return ("""<!DOCTYPE html><html><head><title>江戸川区</title></head><body>
更新日：2019年3月1日
<h1>小松川第二中学校　改築の概要</h1>
<p>小松川第二中学校は、改築前は平井3丁目で学校運営していましたが、
新校舎を小松川2丁目に建設・移転して学校運営しています。
なお、夜間学級は平井3丁目で学校運営しています。</p>
<p>平成30年4月より新校舎で学校運営しています。</p>
<p>所在地：小松川2丁目10番2号</p></body></html>""").encode("utf-8")


class CampusPageTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"a-source.zip"
        self.raw=mock_source()
        self.manifest={
            "schema_id":A_SCHEMA,"source_id":SID,"source_url":URL,
            "relative_path":RAW_NAME,"http_status":200,
            "raw_sha256":hashlib.sha256(self.raw).hexdigest(),
            "raw_bytes":len(self.raw),"printed_webpage_updated_date":"2019-03-01",
            "2019_original_revision_authenticated":False,
            "2019_asof_input_approved":False,
            "school_campus_relation":"SOURCE_CANDIDATE_UNREVIEWED",
            "event_shelter_building_identity":None,
            "event_shelter_site_pairs_approved":0,
            "prediction_accuracy_evaluated":False,
            "human_C_review":"NOT_RUN",
        }
        self.pack()

    def pack(self,extra=False):
        with zipfile.ZipFile(self.path,"w") as z:
            z.writestr("manifest.json",json.dumps(self.manifest))
            z.writestr(RAW_NAME,self.raw)
            if extra:
                z.writestr("unsafe_facility_identity.json","{}")

    def test_verified_school_campus_claims_but_not_shelter(self):
        data=audit(self.path)
        self.assertTrue(data["source_states_different_school_operation_districts"])
        self.assertEqual(data["source_normal_campus_street_address"],"小松川2丁目10番2号")
        self.assertEqual(data["source_school_night_campus_district"],"平井3丁目")
        self.assertIsNone(data["source_night_campus_street_address"])
        self.assertIsNone(data["actual_shelter_used_building_for_205"])
        self.assertIsNone(data["actual_shelter_used_building_for_11"])
        self.assertEqual(data["shelter_identity_pairs_approved"],0)
        self.assertFalse(data["historical_page_revision_asof_approved"])

    def test_night_school_claim_missing_blocks(self):
        raw=mock_source().replace("夜間学級は平井3丁目".encode(),"夜間学級は小松川2丁目".encode())
        with self.assertRaisesRegex(CampusAuditError,"night_operation"):
            evidence_from_html(raw)

    def test_forged_approval_blocks(self):
        self.manifest["event_shelter_site_pairs_approved"]=1
        self.pack()
        with self.assertRaisesRegex(CampusAuditError,"approval flag mismatch"):
            audit(self.path)

    def test_tampered_original_sha_blocks(self):
        self.raw+=b"<!--extra-->"
        self.pack()
        with self.assertRaisesRegex(CampusAuditError,"SHA256"):
            audit(self.path)

    def test_unreviewed_page_date_change_blocks(self):
        self.raw=mock_source().replace(b"2019",b"2021")
        with self.assertRaisesRegex(CampusAuditError,"printed_page_update"):
            evidence_from_html(self.raw)

    def test_missing_full_address_blocks(self):
        raw=mock_source().replace("小松川2丁目10番2号".encode(),"小松川2丁目".encode())
        with self.assertRaisesRegex(CampusAuditError,"regular_new_site_address"):
            evidence_from_html(raw)

    def test_extra_raw_archive_member_blocks(self):
        self.pack(extra=True)
        with self.assertRaisesRegex(CampusAuditError,"raw archive members"):
            audit(self.path)


if __name__=="__main__":
    unittest.main()
