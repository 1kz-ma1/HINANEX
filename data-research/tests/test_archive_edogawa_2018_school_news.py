"""Synthetic tests; source details are not facility IDs or weather predictions."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SRC=Path(__file__).resolve().parents[1]/"tools"/"archive_edogawa_2018_school_news.py"
spec=importlib.util.spec_from_file_location("news2018",SRC)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Response:
    status=200
    headers={"Content-Type":"application/pdf"}
    def __init__(self,url=None,raw=None):
        self.url=url or mod.URL
        self.raw=raw if raw is not None else b"%PDF-1.7\n"+b"x"*150
    def geturl(self): return self.url
    def read(self,n): return self.raw[:n]
    def __enter__(self): return self
    def __exit__(self,*_): return False


class Opener:
    def __init__(self,rsp): self.rsp=rsp
    def open(self,req,timeout): return self.rsp


class NewsArchiveTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.folder=Path(t.name)/"raw"

    def take(self,rsp=None):
        with patch.object(mod.urllib.request,"build_opener",return_value=Opener(rsp or Response())):
            return mod.capture(self.folder)

    def test_archive_verify_no_facility_equivalence(self):
        report=self.take()
        self.assertEqual(report["printed_issue_date"],"2018-08-20")
        self.assertIsNone(report["school_night_physical_site_equivalence"])
        self.assertFalse(report["historical_asof_input_approved"])
        self.assertEqual(mod.verify(self.folder)["sha256"],report["raw_sha256"])

    def test_reject_wrong_url(self):
        with self.assertRaisesRegex(mod.ArchiveError,"changed origin URL"):
            self.take(Response(url="https://example.org/2018.pdf"))

    def test_reject_html_error(self):
        with self.assertRaisesRegex(mod.ArchiveError,"PDF signature"):
            self.take(Response(raw=b"<html>404</html>"))

    def test_reject_raw_tampering(self):
        self.take()
        (self.folder/mod.FILENAME).write_bytes(b"%PDF-1.7\n"+b"y"*150)
        with self.assertRaisesRegex(mod.ArchiveError,"SHA256"):
            mod.verify(self.folder)

    def test_reject_escalated_site_identity(self):
        self.take()
        p=self.folder/"manifest.json"
        data=json.loads(p.read_text())
        data["school_night_physical_site_equivalence"]=True
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(mod.ArchiveError,"approval metadata mismatch"):
            mod.verify(self.folder)

    def test_no_archive_overwrite(self):
        self.take()
        with self.assertRaisesRegex(mod.ArchiveError,"overwriting"):
            self.take()


if __name__=="__main__":
    unittest.main()
