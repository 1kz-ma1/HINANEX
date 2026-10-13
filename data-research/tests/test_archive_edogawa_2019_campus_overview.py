"""Synthetic A regressions. No claim about authenticated 2019 revision."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SRC=Path(__file__).resolve().parents[1]/"tools"/"archive_edogawa_2019_campus_overview.py"
spec=importlib.util.spec_from_file_location("campus2019",SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Response:
    status=200
    headers={"Content-Type":"text/html; charset=utf-8"}
    def __init__(self,url=None,data=None):
        self.url=url or m.URL
        self.data=data if data is not None else b"<!DOCTYPE html><html><body>test</body></html>"
    def geturl(self):return self.url
    def read(self,n):return self.data[:n]
    def __enter__(self):return self
    def __exit__(self,*_):return False


class Opener:
    def __init__(self,response):self.response=response
    def open(self,request,timeout):return self.response


class CampusArchiveTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/"archive"

    def capture(self,response=None):
        with patch.object(m.urllib.request,"build_opener",
                          return_value=Opener(response or Response())):
            return m.archive(self.path)

    def test_source_bytes_stable_and_approval_is_false(self):
        meta=self.capture()
        self.assertFalse(meta["2019_original_revision_authenticated"])
        self.assertFalse(meta["2019_asof_input_approved"])
        self.assertIsNone(meta["event_shelter_building_identity"])
        self.assertEqual(m.verify(self.path)["raw_sha256"],meta["raw_sha256"])

    def test_reject_redirected_origin(self):
        with self.assertRaisesRegex(m.ArchiveError,"official URL changed"):
            self.capture(Response(url="https://other.example/site"))

    def test_reject_spoofed_html_or_empty(self):
        with self.assertRaisesRegex(m.ArchiveError,"non-HTML"):
            self.capture(Response(data=b"404 page"))

    def test_original_bytes_are_not_mutable(self):
        self.capture()
        (self.path/m.RAW_NAME).write_bytes(b"<html>changed</html>")
        with self.assertRaisesRegex(m.ArchiveError,"SHA256"):
            m.verify(self.path)

    def test_forged_historical_approval_fails(self):
        self.capture()
        p=self.path/"manifest.json"
        doc=json.loads(p.read_text())
        doc["2019_asof_input_approved"]=True
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(m.ArchiveError,"approval changed"):
            m.verify(self.path)

    def test_forged_event_building_fails(self):
        self.capture()
        p=self.path/"manifest.json"
        doc=json.loads(p.read_text())
        doc["event_shelter_building_identity"]="regular_campus"
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(m.ArchiveError,"approval changed"):
            m.verify(self.path)

    def test_no_overwrite(self):
        self.capture()
        with self.assertRaisesRegex(m.ArchiveError,"overwrite"):
            self.capture()


if __name__=="__main__":
    unittest.main()
