"""Synthetic tests for A alternate map PDF capture, no network."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

modpath = Path(__file__).resolve().parents[1] / "tools/archive_edogawa_2019_map_copy.py"
spec = importlib.util.spec_from_file_location("map_capture", modpath)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Response:
    status = 200
    headers = {"Content-Type": "application/pdf"}

    def __init__(self, url=None, payload=b"%PDF-1.4\nsynthetic PDF content"):
        self.url = url or m.URL
        self.payload = payload

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.payload[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class Opener:
    def __init__(self, response=None):
        self.response = response or Response()

    def open(self, request, timeout):
        return self.response


class MapCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "map"

    def take(self, response=None):
        with patch.object(m.urllib.request, "build_opener", return_value=Opener(response)):
            return m.capture(self.folder)

    def test_archive_and_verify_but_never_certify_2019(self):
        manifest = self.take()
        self.assertFalse(manifest["same_bytes_available_on_2019_10_12"])
        self.assertFalse(manifest["asof_input_approved"])
        self.assertEqual(m.verify(self.folder)["sha256"], manifest["sha256"])

    def test_reject_broken_pdf(self):
        with self.assertRaisesRegex(m.CaptureError, "not a valid-size PDF"):
            self.take(Response(payload=b"<html>error</html>"))

    def test_reject_redirect(self):
        with self.assertRaisesRegex(m.CaptureError, "unexpected official URL"):
            self.take(Response(url="https://other.example/fake.pdf"))

    def test_reject_archive_tampering(self):
        self.take()
        (self.folder / m.PDF).write_bytes(b"%PDF-1.4\nnew data")
        with self.assertRaisesRegex(m.CaptureError, "SHA256"):
            m.verify(self.folder)

    def test_reject_promoting_to_approved(self):
        self.take()
        p = self.folder / "manifest.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["asof_input_approved"] = True
        p.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(m.CaptureError, "approval metadata"):
            m.verify(self.folder)

    def test_reject_overwriting_archived_raw(self):
        self.take()
        with self.assertRaisesRegex(m.CaptureError, "cannot overwrite"):
            self.take()

    def test_reject_unexpected_files(self):
        self.take()
        (self.folder / "hidden-results.txt").write_text("fake")
        with self.assertRaisesRegex(m.CaptureError, "member set mismatch"):
            m.verify(self.folder)


if __name__ == "__main__":
    unittest.main()
