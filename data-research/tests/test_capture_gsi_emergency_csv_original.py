"""Synthetic, no-network GSI CSV capture tests; local source is unapproved."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
import json
import unittest

TOOL=Path(__file__).resolve().parents[1]/"tools"/"capture_gsi_emergency_csv_original.py"
spec=importlib.util.spec_from_file_location("gsi_csv_capture_test",TOOL)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def doc():
    row=["1","000123","千葉県市川市","SYNTHETIC SCHOOL","千葉県市川市SYNTHETIC"]
    row += ["","1","","","","","","","","35.7","139.9",""]
    assert len(row)==17
    return (",".join(row)+"\r\n").encode()

def fake(raw=None, url=None, status=200):
    return lambda: ((doc() if raw is None else raw), {
        "status_observed":status,
        "url_observed":url or mod.SOURCE_URL,
        "etag_observed":None,"last_modified_observed":None,"content_type_observed":"text/csv"
    })

class CSVAcquisitionTests(unittest.TestCase):
    def test_requires_terms_and_outside_repo_storage(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/"unreviewed"
            with self.assertRaisesRegex(mod.CaptureBlocked,"ACKNOWLEDGMENT"):
                mod.capture_once(target,acknowledged=False,fetcher=fake())
            self.assertFalse(target.exists())
            m=mod.capture_once(target,acknowledged=True,fetcher=fake(),
                               observed_at=datetime(2026,10,26,tzinfo=timezone.utc))
            self.assertTrue((target/"gsi-emergency-national-original.csv").exists())
            self.assertEqual(m["rows_count_unreviewed"],1)
            self.assertFalse(m["csv_to_geojson_identity_approved"])
            self.assertFalse(m["usable_in_disaster"])
            self.assertFalse(m["official_origin_independently_authenticated"])
            with self.assertRaisesRegex(mod.CaptureBlocked,"MUST_NOT_EXIST"):
                mod.capture_once(target,acknowledged=True,fetcher=fake())
    def test_bad_http_or_format_blocks_without_artifact(self):
        with TemporaryDirectory() as temp:
            for name,fetcher in (
                ("bad_url",fake(url="https://evil.invalid/")),
                ("bad_http",fake(status=404)),
                ("bad_csv",fake(raw=b"broken")),
            ):
                target=Path(temp)/name
                with self.subTest(name=name),self.assertRaises(mod.CaptureBlocked):
                    mod.capture_once(target,acknowledged=True,fetcher=fetcher)
                self.assertFalse(target.exists())
    def test_no_unsafe_tls_or_redirect(self):
        import inspect
        code=inspect.getsource(mod.fetch_one)
        self.assertIn("ssl.create_default_context()",code)
        self.assertIn("NoRedirect()",code)
        self.assertNotIn("CERT_NONE",code)
    def test_no_destination_inside_git(self):
        with self.assertRaisesRegex(mod.CaptureBlocked,"OUTSIDE_GIT"):
            mod.capture_once(mod.REPO_ROOT/"data-research"/"capture",acknowledged=True,fetcher=fake())
