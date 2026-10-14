"""Independent synthetic tests for a scanned 2019-map candidate, not real approvals."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
import zipfile

from audit_edogawa_2019_map_copy import audit, MapAuditError, pdf_creation_day, SID, PDF_NAME, URL, SCHEMA


class CMapAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "archive.zip"
        self.body = b"%PDF-1.4\nsynthetic file"
        self.manifest = {
            "schema_id": SCHEMA, "source_id": SID, "url": URL,
            "filename": PDF_NAME, "source_state": "UNREVIEWED_ALTERNATE_COPY",
            "original_issue_time_verified": False,
            "same_bytes_available_on_2019_10_12": False,
            "asof_input_approved": False,
            "facility_identity_approved": False,
            "C_human_review": "NOT_RUN",
            "bytes": len(self.body),
            "sha256": hashlib.sha256(self.body).hexdigest(),
        }
        self.pack()

    def pack(self, extra=None):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("manifest.json", json.dumps(self.manifest))
            z.writestr(PDF_NAME, self.body)
            if extra is not None:
                z.writestr("unapproved_prediction.json", b"{}")

    def inspect(self, body):
        return {"page_count": 1, "creation_date_raw": "D:20200821165450+00'00'",
                "text_characters": 0, "raster_images": 1}

    def test_identifies_2020_pdf_container_with_unapproved_2019_map(self):
        result = audit(self.path, pdf_inspector=self.inspect)
        self.assertTrue(result["pdf_container_metadata_indicates_post_event"])
        self.assertEqual(result["pdf_container_creation_day"], "2020-08-21")
        self.assertTrue(result["map_visual_text_review_required"])
        self.assertFalse(result["asof_input_approved"])
        self.assertFalse(result["historical_version_verified"])
        self.assertFalse(result["prediction_accuracy_evaluated"])

    def test_altered_raw_is_rejected(self):
        self.body += b"changed"
        self.pack()
        with self.assertRaisesRegex(MapAuditError, "SHA256"):
            audit(self.path, pdf_inspector=self.inspect)

    def test_attempt_to_forge_2019_approval_is_rejected(self):
        self.manifest["asof_input_approved"] = True
        self.pack()
        with self.assertRaisesRegex(MapAuditError, "forged approval"):
            audit(self.path, pdf_inspector=self.inspect)

    def test_non_official_url_rejected(self):
        self.manifest["url"] = "https://other.example/fake.pdf"
        self.pack()
        with self.assertRaisesRegex(MapAuditError, "source identity"):
            audit(self.path, pdf_inspector=self.inspect)

    def test_extra_file_rejected(self):
        self.pack(extra=True)
        with self.assertRaisesRegex(MapAuditError, "archive members"):
            audit(self.path, pdf_inspector=self.inspect)

    def test_invalid_metadata_not_imputed(self):
        for value in ["D:bad", None, "D:20191304", "20200821", ""]:
            with self.subTest(value=value):
                self.assertIsNone(pdf_creation_day(value))

    def test_pdf_creation_date_is_not_equated_to_map_issue(self):
        self.assertEqual(pdf_creation_day("D:20200821165450+00'00'"), "2020-08-21")
        self.assertEqual(pdf_creation_day("D:20190501120000+09'00'"), "2019-05-01")
        self.assertIsNone(pdf_creation_day("D:202013999999"))

    def test_broken_pdf_inspector_is_rejected(self):
        with self.assertRaisesRegex(MapAuditError,"PDF inspection failed"):
            audit(self.path,pdf_inspector=lambda body: {})
        with self.assertRaisesRegex(MapAuditError,"invalid PDF content inspection"):
            audit(self.path,pdf_inspector=lambda body: {"page_count":1,"text_characters":-1,"raster_images":0})


if __name__=="__main__":
    unittest.main()
