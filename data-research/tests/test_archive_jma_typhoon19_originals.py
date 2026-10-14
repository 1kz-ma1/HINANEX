"""Offline synthetic tests for the JMA archive. Never assert real historical release."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / "tools" / "archive_jma_typhoon19_originals.py"
spec = importlib.util.spec_from_file_location("jma_originals", FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeResponse:
    status = 200
    headers = {"Content-Type": "text/html", "Date": "Tue, 13 Oct 2026 01:00:00 GMT"}

    def __init__(self, url):
        self.url = url

    def geturl(self):
        return self.url

    def read(self, n):
        return (b"%PDF-1.7\nsynthetic test pdf" if self.url.endswith(".pdf")
                else b"<!DOCTYPE html><html><body>synthetic JMA test HTML</body></html>")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class FakeOpener:
    def open(self, request, timeout):
        return FakeResponse(request.full_url)


class JmaOriginalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger.json"
        self.folder = self.root / "originals"
        self.rows = [
            {"source_id": sid, "url": urls[0], "publisher": "気象庁",
             "asof_input_accepted": False, "published_at_jst": None}
            for sid, urls in m.SOURCES.items()
        ]
        self.write_ledger()

    def write_ledger(self):
        self.ledger.write_text(json.dumps({
            "case_id": "2019-typhoon19-edogawa", "sources": self.rows
        }), encoding="utf-8")

    def capture(self):
        with patch.object(m.urllib.request, "build_opener",return_value=FakeOpener()):
            return m.collect(self.ledger,self.folder)

    def test_capture_six_originals_and_verify(self):
        output = self.capture()
        self.assertEqual(len(output["records"]), 6)
        self.assertFalse(output["asof_input_approved"])
        self.assertEqual(m.verify(self.ledger,self.folder)["verified_originals"],6)

    def test_tamper_pdf_rejected(self):
        self.capture()
        pdf = self.folder / "jma-20191011-t19.pdf"
        pdf.write_bytes(pdf.read_bytes()+b" changed")
        with self.assertRaisesRegex(m.ArchiveError,"SHA256"):
            m.verify(self.ledger,self.folder)

    def test_tamper_candidate_rejected(self):
        self.capture()
        self.ledger.write_text(self.ledger.read_text()+"\n")
        with self.assertRaisesRegex(m.ArchiveError,"ledger hash"):
            m.verify(self.ledger,self.folder)

    def test_mutated_url_and_historical_approval_refused(self):
        self.rows[0]["url"] = "https://example.net/unsafe.html"
        self.write_ledger()
        with self.assertRaisesRegex(m.ArchiveError,"candidate URL"):
            self.capture()
        self.rows[0]["url"] = list(m.SOURCES.values())[0][0]
        self.rows[0]["asof_input_accepted"] = True
        self.write_ledger()
        with self.assertRaisesRegex(m.ArchiveError,"must not assert"):
            self.capture()

    def test_refuse_overwriting_originals(self):
        self.capture()
        with self.assertRaisesRegex(m.ArchiveError,"overwrite forbidden"):
            self.capture()

    def test_refuse_html_error_or_fake_pdf(self):
        with self.assertRaisesRegex(m.ArchiveError,"not a PDF"):
            m.check_shape("pdf", b"<html>error</html>")
        with self.assertRaisesRegex(m.ArchiveError,"not an HTML"):
            m.check_shape("html", b"server error 200")

    def test_refuse_manifest_escalating_approval(self):
        self.capture()
        path = self.folder / "manifest.json"
        d = json.loads(path.read_text())
        d["asof_input_approved"] = True
        path.write_text(json.dumps(d))
        with self.assertRaisesRegex(m.ArchiveError,"approval violation"):
            m.verify(self.ledger,self.folder)

    def test_refuse_extra_archive_members(self):
        self.capture()
        (self.folder / "unrelated.json").write_text("{}")
        with self.assertRaisesRegex(m.ArchiveError,"extra or missing"):
            m.verify(self.ledger,self.folder)


if __name__ == "__main__":
    unittest.main()
