"""Offline regression tests for 2019 official candidate archive. No internet access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODPATH = Path(__file__).resolve().parents[1] / "tools" / "archive_historical_edogawa.py"
spec = importlib.util.spec_from_file_location("archive_historical_edogawa", MODPATH)
archive_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive_mod)

TEST_URLS = {
    "tokyo-20191012-report23": "https://www.bousai.metro.tokyo.lg.jp/23.html",
    "tokyo-20191012-report36": "https://www.bousai.metro.tokyo.lg.jp/36.html",
    "tokyo-20191013-report49": "https://www.bousai.metro.tokyo.lg.jp/49.html",
    "edogawa-mayor-20191101": "https://www.city.edogawa.tokyo.jp/mayor.html",
    "edogawa-school-ops-review": "https://www.city.edogawa.tokyo.jp/19matome.pdf",
}


class Response:
    status = 200

    def __init__(self, url, data):
        self.url = url
        self.data = data
        self.headers = {"Content-Type": "application/pdf" if url.endswith(".pdf") else "text/html"}

    def geturl(self):
        return self.url

    def read(self, length=-1):
        return self.data[:length]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeOpener:
    def open(self, request, timeout=None):
        url = request.full_url
        data = b"%PDF-1.7\nfixture" if url.endswith(".pdf") else b"<!DOCTYPE html><html>official fixture</html>"
        return Response(url, data)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "candidate.json"
        self.rawdir = self.root / "captured"
        self.sources = [
            {"source_id": sid, "url": url, "format": "PDF" if url.endswith(".pdf") else "HTML"}
            for sid, url in TEST_URLS.items()
        ]
        self.write_ledger()

    def write_ledger(self):
        self.ledger.write_text(json.dumps({
            "case_id": "2019-typhoon19-edogawa", "sources": self.sources
        }), encoding="utf-8")

    def capture(self):
        with patch.object(archive_mod.urllib.request, "build_opener", return_value=FakeOpener()):
            return archive_mod.archive(self.ledger, self.rawdir)

    def test_archive_then_independent_sha256_verification(self):
        output = self.capture()
        self.assertEqual(len(output["sources"]), 5)
        self.assertFalse(output["historical_as_of_approved"])
        self.assertEqual(output["facility_pairs_approved"], 0)
        self.assertEqual(archive_mod.verify(self.ledger, self.rawdir)["verified_sources"], 5)

    def test_modified_raw_is_rejected(self):
        self.capture()
        path = self.rawdir / "tokyo-20191012-report23.html"
        path.write_bytes(path.read_bytes() + b"x")
        with self.assertRaisesRegex(archive_mod.EvidenceError, "archived bytes mismatch"):
            archive_mod.verify(self.ledger, self.rawdir)

    def test_modified_ledger_is_rejected(self):
        self.capture()
        self.ledger.write_text(self.ledger.read_text() + "\n")
        with self.assertRaisesRegex(archive_mod.EvidenceError, "ledger changed"):
            archive_mod.verify(self.ledger, self.rawdir)

    def test_manifest_cannot_forge_acceptance(self):
        self.capture()
        p = self.rawdir / "manifest.json"
        manifest = json.loads(p.read_text())
        manifest["historical_as_of_approved"] = True
        p.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(archive_mod.EvidenceError, "may not certify"):
            archive_mod.verify(self.ledger, self.rawdir)

    def test_reject_wrong_source_host(self):
        self.sources[0]["url"] = "https://example.com/23.html"
        self.write_ledger()
        with self.assertRaisesRegex(archive_mod.EvidenceError, "official origin"):
            self.capture()

    def test_reject_duplicate_source_id(self):
        self.sources.append(dict(self.sources[0]))
        self.write_ledger()
        with self.assertRaisesRegex(archive_mod.EvidenceError, "duplicate"):
            self.capture()

    def test_reject_overwrite(self):
        self.capture()
        with self.assertRaisesRegex(archive_mod.EvidenceError, "not empty"):
            self.capture()

    def test_reject_html_error_response(self):
        with self.assertRaisesRegex(archive_mod.EvidenceError, "expected official HTML"):
            archive_mod.check_shape(self.sources[0], b"Not found")

    def test_reject_bad_pdf_signature(self):
        with self.assertRaisesRegex(archive_mod.EvidenceError, "expected PDF"):
            archive_mod.check_shape(self.sources[-1], b"<html>error</html>")


if __name__ == "__main__":
    unittest.main()
