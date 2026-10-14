"""Synthetic negative tests for archived Edogawa 2018 school bulletin."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_edogawa_2018_school_identity import audit, CError, URL, PDF_NAME, SOURCE_ID, A_SCHEMA


class Official2018LabelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"source.zip"
        self.bytes=b"%PDF-1.4\n"+b"test"*70
        self.manifest={
            "schema_id":A_SCHEMA,"source_id":SOURCE_ID,"official_url":URL,
            "relative_path":PDF_NAME,"raw_sha256":hashlib.sha256(self.bytes).hexdigest(),
            "raw_bytes":len(self.bytes),"record_role":"CONTEMPORANEOUS_2018_SCHOOL_NAMES_ONLY",
            "source_first_published_in_2018_verified":False,
            "source_edition_content_2019_valid_verified":False,
            "historical_asof_input_approved":False,
            "school_night_physical_site_equivalence":None,
            "physical_site_pairs_approved":0,"C_human_review":"NOT_RUN",
            "response_http":200,
        }
        self.pack()

    def pack(self,extra=False):
        with zipfile.ZipFile(self.path,"w") as z:
            z.writestr("manifest.json",json.dumps(self.manifest))
            z.writestr(PDF_NAME,self.bytes)
            if extra:z.writestr("fabricated_site_id.json","{}")

    @staticmethod
    def extract(raw):
        return ["平成30年(2018年) 8月20日　広報えどがわ",
                "区立中学校 学校公開・説明会\n中学校名\n小 松 川 第 二\n小松川第二　夜間学級"]

    def test_official_contemporaneous_two_labels_no_auto_physical_join(self):
        result=audit(self.path,self.extract)
        self.assertTrue(result["day_school_label_present"])
        self.assertTrue(result["night_class_label_present_separately"])
        self.assertIsNone(result["school_night_same_physical_site_2019"])
        self.assertEqual(result["physical_site_pairs_approved"],0)
        self.assertFalse(result["historical_asof_input_approved"])

    def test_night_class_missing_blocks(self):
        with self.assertRaisesRegex(CError,"night-class listing missing"):
            audit(self.path,lambda _: [self.extract(None)[0],
                                      "区立中学校 学校公開・説明会 中学校名 小松川第二"])

    def test_regular_row_missing_blocks(self):
        with self.assertRaisesRegex(CError,"regular school entry missing"):
            audit(self.path,lambda _: [self.extract(None)[0],
                                      "区立中学校 学校公開・説明会 中学校名 小松川第二 夜間学級"])

    def test_same_building_claim_fails(self):
        self.manifest["school_night_physical_site_equivalence"]=True
        self.pack()
        with self.assertRaisesRegex(CError,"approval metadata invalid"):
            audit(self.path,self.extract)

    def test_original_byte_alteration_detected(self):
        self.bytes+=b"new"
        self.pack()
        with self.assertRaisesRegex(CError,"SHA256"):
            audit(self.path,self.extract)

    def test_extra_source_not_allowed(self):
        self.pack(extra=True)
        with self.assertRaisesRegex(CError,"file identity mismatch"):
            audit(self.path,self.extract)


if __name__=="__main__":
    unittest.main()
