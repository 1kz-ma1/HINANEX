"""Independent historical archive checks. All fixtures synthetic, no network."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
import zipfile

from audit_historical_edogawa_archive import BULLETINS, audit, AuditError

TOKYO_BASE = "https://www.bousai.metro.tokyo.lg.jp/"
EDOGAWA_BASE = "https://www.city.edogawa.tokyo.jp/"


def bulletin_source(sid, policy, value):
    # Match official HTML markup shapes incl. the added text wrappers in report 36.
    cell = f"<span class='skip'>[ここから追加]</span>{value}<span class='skip'>[追加ここまで]</span>"
    return (
        "<!doctype html><html><head><title>official</title></head><body>"
        f"<p>{policy['published']}</p><h2>{policy['observed']}</h2>"
        "<table><tr><th>区</th><th>避難所数</th></tr>"
        f"<tr><td>江戸川区</td><td><p>{cell}</p></td><td>0</td></tr>"
        "</table></body></html>"
    ).encode("utf-8")


class IndependentAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zip_file = Path(self.tmp.name) / "archive.zip"
        self.sources = {}
        self.rows = []
        self.expected = {
            "tokyo-20191012-report23": 48,
            "tokyo-20191012-report36": 73,
            "tokyo-20191013-report49": 98,
        }
        for sid, policy in BULLETINS.items():
            self.sources[sid + ".html"] = bulletin_source(sid, policy, self.expected[sid])
            self.rows.append(self.manifest_row(sid, "https://www.bousai.metro.tokyo.lg.jp/" + sid + ".html",
                                               self.sources[sid + ".html"], policy))
        for sid in ["edogawa-mayor-20191101", "edogawa-school-ops-review"]:
            ext = ".pdf" if sid.endswith("ops-review") else ".html"
            raw = b"%PDF-1.5\nsynthetic" if ext == ".pdf" else b"<!DOCTYPE html><html><body>105</body></html>"
            self.sources[sid + ext] = raw
            self.rows.append(self.manifest_row(sid, EDOGAWA_BASE + sid + ext, raw, {}))
        self.manifest = {
            "schema_id": "hinanex.a.historical_original_archive.v0.1",
            "historical_as_of_approved": False,
            "prediction_accuracy_evaluated": False,
            "facility_pairs_approved": 0,
            "sources": self.rows,
        }
        self.pack()

    @staticmethod
    def manifest_row(sid, url, data, policy):
        ext = ".pdf" if sid.endswith("ops-review") else ".html"
        return {
            "source_id": sid, "relative_path": sid + ext, "url": url,
            "http_status": 200, "review_state": "UNREVIEWED",
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "claimed_published_at_jst": policy.get("published_at"),
            "claimed_observation_at_jst": policy.get("observation_at"),
        }

    def pack(self):
        with zipfile.ZipFile(self.zip_file, "w") as z:
            z.writestr("manifest.json", json.dumps(self.manifest))
            for path, data in self.sources.items():
                z.writestr(path, data)

    def test_three_realistic_bulletins_and_opaque_other_sources(self):
        result = audit(self.zip_file)
        values = {v["source_id"]: v["reported_observation"]["opened_site_count"]
                  for v in result["tokyo_bulletins"]}
        self.assertEqual(values, self.expected)
        self.assertTrue(result["requires_human_c_review"])
        self.assertFalse(result["replay_match_or_mismatch_approved"])
        self.assertFalse(result["historical_as_of_approved"])

    def test_reject_modified_original_even_when_parseable(self):
        self.sources["tokyo-20191012-report23.html"] += b"<!-- changed -->"
        self.pack()
        with self.assertRaisesRegex(AuditError, "SHA256"):
            audit(self.zip_file)

    def test_reject_unreviewed_future_time_mislabel(self):
        self.rows[0]["claimed_published_at_jst"] = "2019-10-12T12:00:00+09:00"
        self.pack()
        with self.assertRaisesRegex(AuditError, "timestamp"):
            audit(self.zip_file)

    def test_reject_spurious_review_approval(self):
        self.manifest["historical_as_of_approved"] = True
        self.pack()
        with self.assertRaisesRegex(AuditError, "downstream acceptance"):
            audit(self.zip_file)

    def test_reject_unlabeled_extra_archive_member(self):
        self.sources["fabricated-safe-site.json"] = b"{}"
        self.pack()
        with self.assertRaisesRegex(AuditError, "archive members"):
            audit(self.zip_file)

    def test_reject_duplicated_edogawa_rows(self):
        self.sources["tokyo-20191012-report23.html"] = self.sources["tokyo-20191012-report23.html"].replace(
            b"</table>", b"<tr><td>\xe6\xb1\x9f\xe6\x88\xb8\xe5\xb7\x9d\xe5\x8c\xba</td><td>1</td></tr></table>")
        raw = self.sources["tokyo-20191012-report23.html"]
        self.rows[0]["bytes"] = len(raw)
        self.rows[0]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.pack()
        with self.assertRaisesRegex(AuditError, "missing or duplicated"):
            audit(self.zip_file)

    def test_reject_pdf_masked_as_html(self):
        self.sources["edogawa-school-ops-review.pdf"] = b"<html>not pdf</html>"
        raw = self.sources["edogawa-school-ops-review.pdf"]
        self.rows[-1]["bytes"] = len(raw)
        self.rows[-1]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.pack()
        with self.assertRaisesRegex(AuditError, "PDF header"):
            audit(self.zip_file)


if __name__ == "__main__":
    unittest.main()
