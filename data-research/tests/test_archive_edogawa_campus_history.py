"""Offline A tests for archival safety; no real network and no approvals."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "archive_edogawa_campus_history.py"
spec = importlib.util.spec_from_file_location("a_campus", SCRIPT)
campus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campus)


def valid_source(key):
    _, _, kind, markers = campus.SOURCES[key]
    if kind == "pdf":
        return b"%PDF-1.7\n" + b"% dummy document body\n" * 12 + b"%%EOF\n"
    return ("<html><body><article>" + " 。 ".join(markers) +
            "</article></body></html>").encode("utf-8")


def fixture(folder, override=None, redirected=False):
    override = override or {}
    def fake(url):
        key = next(k for k, (_, value, _, _) in campus.SOURCES.items() if value == url)
        return (override.get(key, valid_source(key)),
                "https://example.org/moved" if redirected else url,
                {"content_type": "application/pdf" if key.endswith("2021") or
                  key.endswith("2024") else "text/html"})
    return campus.capture(folder, downloader=fake,
                          at=datetime(2026, 10, 13, tzinfo=timezone.utc))


class SchoolHistoryArchiveTest(unittest.TestCase):
    def test_seven_official_sources_originals_not_approved(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "evidence"
            manifest = fixture(p)
            result = campus.verify(p)
            self.assertEqual(result["official_originals"], 7)
            self.assertEqual(result["html_originals"], 5)
            self.assertEqual(result["pdf_originals"], 2)
            self.assertFalse(manifest["official_publication_and_effective_dates_human_reviewed"])
            self.assertTrue(manifest["pdf_campus_map_and_meeting_context_human_review_required"])
            self.assertEqual(result["human_approved_campus_pairs"], 0)
            self.assertEqual(result["new_flood_classifications"], 0)

    def test_modifying_original_after_manifest_refused(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "evidence"
            fixture(p)
            src = p / "shimokamata_rebuild.html"
            src.write_bytes(src.read_bytes() + b"changed")
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "SHA256 mismatch"):
                campus.verify(p)

    def test_same_host_redirect_wrong_url_refused(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "Untrusted source"):
                fixture(Path(d) / "new", redirected=True)

    def test_html_error200_rejected_before_partial_archive(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "not recognizable HTML"):
                fixture(p, override={"shimokamata_integration":
                                     b"X" * 110 + b"server error"})
            self.assertFalse(p.exists())

    def test_html_pretend_marker_in_comment_is_not_visible(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            hidden = "<html><body><!--" + " ".join(
                campus.SOURCES["hirai_minami_rebuild"][3]) + "--><p>Unavailable</p></body></html>"
            # Comment is not seen by HTMLParser.handle_data.
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "missing school timeline context"):
                fixture(p, override={"hirai_minami_rebuild": hidden.encode()})
            self.assertFalse(p.exists())

    def test_pdf_invalid_magic_rejected(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "do not look like a PDF"):
                fixture(p, override={"historical_shimokamata_site_plan_2021":
                                     b"<html>" + b"0" * 120 + b"</html>"})
            self.assertFalse(p.exists())

    def test_forged_human_approval_in_manifest_rejected(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            m = fixture(p)
            m["school_campus_identity_human_approved"] = True
            (p / "campus_history_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "false site or flood approvals"):
                campus.verify(p)

    def test_duplicate_source_item_manifest_rejected(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            m = fixture(p)
            m["source_items"][0]["source_key"] = m["source_items"][1]["source_key"]
            (p / "campus_history_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "Duplicate"):
                campus.verify(p)

    def test_reuse_archive_directory_forbidden(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "new"
            fixture(p)
            with self.assertRaisesRegex(campus.CampusArchiveFailure, "new/empty"):
                fixture(p)


if __name__ == "__main__":
    unittest.main()
