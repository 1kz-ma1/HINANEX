"""Synthetic C regressions, not assertions about historical disaster forecasts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_jma_2019_originals import POLICIES, audit, AuditError


class JmaCIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source.zip"
        self.originals = {}
        self.records = []
        for sid, policy in POLICIES.items():
            html_path, pdf_path, date, time_string = policy
            body = ("<!DOCTYPE html><html><body>"
                    + date + "<p>台風第１９号</p>"
                    + "<a href='" + pdf_path.split("/")[-1] + "'>PDF</a></body></html>")
            for kind, source_path, original in (
                ("html", html_path, body.encode("utf-8")),
                ("pdf",pdf_path, b"%PDF-1.7\nsynthetic-not-a-real-PDF"),
            ):
                filename = f"{sid}.{kind}"
                self.originals[filename] = original
                self.records.append({
                    "source_id":sid, "kind":kind, "url":"https://www.jma.go.jp/jma/press/"+source_path,
                    "relative_path":filename, "review_state":"UNREVIEWED", "http_status":200,
                    "size_bytes":len(original), "sha256":hashlib.sha256(original).hexdigest(),
                })
        self.manifest = {
            "schema_id":"hinanex.a.jma_2019_raw_manifest.v0.1",
            "case_id":"2019-typhoon19-edogawa",
            "records":self.records, "historical_revision_verified":False,
            "asof_input_approved":False, "prediction_accuracy_evaluated":False,
        }
        self.pack()

    def pack(self):
        with zipfile.ZipFile(self.path,"w") as z:
            z.writestr("manifest.json",json.dumps(self.manifest))
            for name, body in self.originals.items():
                z.writestr(name,body)

    def fake_reader(self, data):
        return "台風第１９号\n" + "\n".join(p[3] for p in POLICIES.values())

    def check(self, reader=None):
        return audit(self.path,pdf_reader=reader if reader is not None else self.fake_reader)

    def test_synthetic_records_verifiable_without_claiming_historical_release(self):
        report = self.check()
        self.assertEqual(report["checked_originals"],6)
        self.assertFalse(report["asof_input_approved"])
        self.assertFalse(report["publication_instant_independently_approved"])
        self.assertFalse(report["prediction_accuracy_evaluated"])
        self.assertTrue(report["human_review_still_required"])

    def test_tampered_pdf_body_fails(self):
        self.originals["jma-20191009-t19.pdf"] += b"\nchanged"
        self.pack()
        with self.assertRaisesRegex(AuditError,"hash mismatch"):
            self.check()

    def test_missing_pdf_date_fails_even_if_hash_is_correct(self):
        with self.assertRaisesRegex(AuditError,"documented 2019 time string"):
            self.check(reader=lambda data: "台風第１９号")

    def test_wrong_link_fails_even_if_hash_is_correct(self):
        filename="jma-20191010-t19.html"
        self.originals[filename] = self.originals[filename].replace(b"20191010_1400.pdf",b"bad.pdf")
        new_body = self.originals[filename]
        matching=next(r for r in self.records if r["relative_path"]==filename)
        matching["size_bytes"]=len(new_body)
        matching["sha256"]=hashlib.sha256(new_body).hexdigest()
        self.pack()
        with self.assertRaisesRegex(AuditError,"does not link"):
            self.check()

    def test_forged_asof_flag_refused(self):
        self.manifest["asof_input_approved"] = True
        self.pack()
        with self.assertRaisesRegex(AuditError,"historical approval"):
            self.check()

    def test_other_official_host_refused(self):
        self.records[0]["url"]="https://attacker.example/jma.html"
        self.pack()
        with self.assertRaisesRegex(AuditError,"URL/source identity"):
            self.check()

    def test_extra_archive_member_refused(self):
        self.originals["made-up-flood-prediction.json"]=b"{}"
        self.pack()
        with self.assertRaisesRegex(AuditError,"archive members"):
            self.check()

    def test_duplicate_manifest_key_refused(self):
        self.records[1]["source_id"] = self.records[0]["source_id"]
        self.records[1]["kind"]=self.records[0]["kind"]
        self.pack()
        with self.assertRaisesRegex(AuditError,"duplicate"):
            self.check()


if __name__ == "__main__":
    unittest.main()
