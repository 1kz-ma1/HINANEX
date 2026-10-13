"""Offline C regression: mock network; never contact official sites in CI."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from archive_edogawa_official_sources import (
    SOURCES,
    MAX_RAW_BYTES,
    SnapshotFailure,
    capture,
    ensure_trusted_url,
)


class OfficialArchiveTests(unittest.TestCase):
    @staticmethod
    def sample_fetch(url):
        raw = ("2026 test synthetic bytes for " + url).encode("utf-8")
        return raw, url, {
            "content_type": "text/html; charset=UTF-8",
            "etag": '"fixture"',
            "last_modified": None,
        }

    def test_snapshot_uses_exact_response_bytes_and_never_self_approves(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "archive"
            stamp = datetime(2026, 10, 13, 0, 0, tzinfo=timezone.utc)
            manifest = capture(folder, fetch=self.sample_fetch, now=stamp)
            self.assertEqual(manifest["captured_at_utc"], stamp.isoformat())
            self.assertEqual(manifest["purpose"],
                             "C_EVIDENCE_ARCHIVE_ONLY_NO_C_INDEPENDENT_ACCEPTANCE")
            self.assertFalse(manifest["human_c_reviewer_signed_off"])
            self.assertEqual(manifest["flood_scenario_classifications_added"], 0)
            self.assertEqual(len(manifest["source_items"]), len(SOURCES))
            stored = json.loads((folder / "snapshot_manifest.json").read_text())
            self.assertEqual(stored, manifest)
            for item in manifest["source_items"]:
                original = (folder / item["archive_filename"]).read_bytes()
                self.assertEqual(item["byte_size"], len(original))
                self.assertEqual(item["sha256"], hashlib.sha256(original).hexdigest())
                self.assertTrue(item["date_context_review_required"])
                self.assertIsNone(item["official_publication_or_effective_date"])
                self.assertEqual(item["requested_url"], item["final_url"])

    def test_empty_response_does_not_create_partial_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "archive"
            def fetch(url):
                if "kasaikoka" in url:
                    return b"", url, {}
                return self.sample_fetch(url)
            with self.assertRaisesRegex(SnapshotFailure, "no acceptable"):
                capture(folder, fetch=fetch)
            self.assertFalse(folder.exists())

    def test_wrong_redirect_host_is_rejected_before_save(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "archive"
            def fetch(url):
                raw, _, headers = self.sample_fetch(url)
                return raw, "https://attacker.invalid/malicious", headers
            with self.assertRaisesRegex(SnapshotFailure, "Untrusted"):
                capture(folder, fetch=fetch)
            self.assertFalse(folder.exists())

    def test_http_or_lookalike_domain_cannot_be_archived(self):
        for url in (
            "http://www.city.edogawa.tokyo.jp/foo",
            "https://www.city.edogawa.tokyo.jp.evil.net/a",
            "https://edogawa.tokyo.jp/a",
            "https://www.city.edogawa.tokyo.jp:8443/foo",
        ):
            with self.subTest(url=url), self.assertRaises(SnapshotFailure):
                ensure_trusted_url(url)

    def test_existing_versioned_snapshot_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / "old.txt").write_text("old original")
            with self.assertRaisesRegex(SnapshotFailure, "must be empty"):
                capture(out, fetch=self.sample_fetch)
            self.assertEqual((out / "old.txt").read_text(), "old original")

    def test_oversized_download_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "snapshot"
            def fetch(url):
                return b"x" * (MAX_RAW_BYTES + 1), url, {}
            with self.assertRaisesRegex(SnapshotFailure, "no acceptable"):
                capture(target, fetch=fetch)
            self.assertFalse(target.exists())

    def test_cannot_claim_snapshot_is_safety_or_identity_certification(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = capture(Path(temp) / "files", fetch=self.sample_fetch)
            self.assertTrue(manifest["http_content_is_not_facility_identity"])
            self.assertFalse(manifest["human_c_reviewer_signed_off"])
            self.assertTrue(all(x["date_context_review_required"]
                                for x in manifest["source_items"]))


if __name__ == "__main__":
    unittest.main()
