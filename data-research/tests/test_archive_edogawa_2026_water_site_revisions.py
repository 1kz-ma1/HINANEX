"""Synthetic regression for 2026 flood-plan and former campus originals."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "archive_edogawa_2026_water_site_revisions.py"
spec = importlib.util.spec_from_file_location("a_water_revisions", SCRIPT)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def mocked(key):
    kind = A.SOURCES[key][2]
    if kind == "pdf":
        return b"%PDF-1.6\n" + b"% synthetic test PDF data only\n"*10 + b"%%EOF\n"
    return ("<html><body><article>" +
            "旧下鎌田小学校 統廃合後の学校後利用 " * 8 +
            "</article></body></html>").encode()


def capture(dir_, overrides=None):
    overrides = overrides or {}
    def get(url):
        key = next(k for k,v in A.SOURCES.items() if v[1] == url)
        return overrides.get(key, mocked(key)), url, {"content_type": "text/html"}
    return A.capture(dir_, fetch=get, now=datetime(2026,10,13,tzinfo=timezone.utc))


class DatedFloodPlanArchiveTests(unittest.TestCase):
    def test_manifest_and_unapproved_status(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            capture(path)
            result=A.verify(path)
            self.assertEqual(result["original_sources_verified"],3)
            self.assertEqual(result["human_approved_site_pairs"],0)
            self.assertEqual(result["flood_scenario_changes"],0)

    def test_tampered_original_fails(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            capture(path)
            f=path/"2026_disaster_plan_external_internal_water.pdf"
            f.write_bytes(f.read_bytes()+b"extra")
            with self.assertRaisesRegex(A.ArchiveFailure,"SHA256 mismatch"):
                A.verify(path)

    def test_wrong_city_pdf_does_not_fake_original(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            with self.assertRaisesRegex(A.ArchiveFailure,"intact PDF"):
                capture(path,{"2026_disaster_plan_original":
                    b"<html><body>" + b"error" * 100 + b"</body></html>"})
            self.assertFalse(path.exists())

    def test_html_content_marker_is_required(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            with self.assertRaisesRegex(A.ArchiveFailure,"document-specific markers"):
                capture(path,{"2026_school_afteruse_page":
                   b"<html><body>" + b"all other schools" * 30 + b"</body></html>"})
            self.assertFalse(path.exists())

    def test_fake_approval_fails(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            m=capture(path)
            m["new_flood_scenario_classifications"]=1
            (path/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(A.ArchiveFailure,"falsely claims"):
                A.verify(path)

    def test_duplicate_source_key_fails(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            m=capture(path)
            m["source_items"][1]["source_key"]=m["source_items"][0]["source_key"]
            (path/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaises(A.ArchiveFailure):
                A.verify(path)

    def test_refuses_to_overwrite_existing_archive(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"v2026"
            capture(path)
            with self.assertRaisesRegex(A.ArchiveFailure,"new or empty"):
                capture(path)


if __name__ == "__main__":
    unittest.main()
