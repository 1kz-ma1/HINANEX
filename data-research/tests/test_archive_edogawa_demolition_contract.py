"""No-network negative tests for proposed demolition council original."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

p=Path(__file__).resolve().parents[1]/"tools"/"archive_edogawa_demolition_contract.py"
spec=importlib.util.spec_from_file_location("demolition_a",p)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def fixture(directory,raw=None,final=None):
    if raw is None:
        raw=b"%PDF-1.5\n"+b"% Official synthetic PDF\n"*15+b"%%EOF\n"
    def fetch():
        return raw,(final if final is not None else a.OFFICIAL_PDF),{"content_type":"application/pdf"}
    return a.archive(directory,fetch=fetch,now=datetime(2026,10,13,tzinfo=timezone.utc))


class CouncilSourceTests(unittest.TestCase):
    def test_source_does_not_claim_safety_or_demolition_completion(self):
        with TemporaryDirectory() as root:
            path=Path(root)/"source"
            m=fixture(path)
            result=a.verify(path)
            self.assertEqual(result["human_approved_site_pairs"],0)
            self.assertEqual(result["flood_classification_changes"],0)
            self.assertFalse(m["demolition_work_completed_verified"])
            self.assertIsNone(m["bill_vote_status_derived_from_pdf"])

    def test_false_completed_demolition_rejected(self):
        with TemporaryDirectory() as root:
            path=Path(root)/"source"
            m=fixture(path)
            m["demolition_work_completed_verified"]=True
            (path/"council_source_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(a.EvidenceError,"unreviewed approval"):
                a.verify(path)

    def test_false_flood_status_rejected(self):
        with TemporaryDirectory() as root:
            path=Path(root)/"source"
            m=fixture(path)
            m["flood_scenario_status_changes"]=1
            (path/"council_source_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(a.EvidenceError,"unreviewed approval"):
                a.verify(path)

    def test_pdf_tampering_detected(self):
        with TemporaryDirectory() as root:
            path=Path(root)/"source"
            fixture(path)
            pdf=path/a.FILENAME
            pdf.write_bytes(pdf.read_bytes()+b"x")
            with self.assertRaisesRegex(a.EvidenceError,"digest differs"):
                a.verify(path)

    def test_untrusted_redirect_rejected(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(a.EvidenceError,"redirected"):
                fixture(Path(root)/"source",final="https://example.com/gian64.pdf")

    def test_http_ok_not_a_pdf_rejected(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(a.EvidenceError,"bounded PDF"):
                fixture(Path(root)/"source",raw=b"<html>"+b"bad"*50+b"</html>")

    def test_no_evidence_overwrite(self):
        with TemporaryDirectory() as root:
            path=Path(root)/"source"
            fixture(path)
            with self.assertRaisesRegex(a.EvidenceError,"new or empty"):
                fixture(path)


if __name__=="__main__":
    unittest.main()
