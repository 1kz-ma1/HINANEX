"""Deterministic fake-PDF tests; never fetch live websites in CI."""
import copy
import unittest

from check_nagoya_official_pdf_updates import (
    CHANGED_STATUS, MAX_BYTES, NoRedirect, SAFETY, UNCHANGED_STATUS,
    WATCH_SOURCES, capture_snapshot, compare_snapshots, fetch_pdf,
    local_file, validate_snapshot,
)


class NagoyaOfficialPdfByteWatchTests(unittest.TestCase):
    def make_capture(self, altered_ward=None, captured="2026-10-22T08:15:00Z"):
        names_by_url = {url: ward for ward, url in WATCH_SOURCES}

        def fake_fetch(url):
            ward = names_by_url[url]
            return b"%PDF-1.7\n" + ward.encode("utf-8") + (
                b"changed" if ward == altered_ward else b"stable")
        return capture_snapshot(fake_fetch, captured_at=captured)

    def test_collects_exactly_pinned_public_sources_and_no_site_approvals(self):
        current = self.make_capture()
        self.assertEqual(len(current["sources"]), 5)
        self.assertEqual(current["safety"], SAFETY)
        self.assertTrue(all(s["url"].startswith("https://www.city.nagoya.jp/")
                            for s in current["sources"]))
        self.assertTrue(all(len(s["sha256"]) == 64 for s in current["sources"]))
        self.assertFalse("data" in current)
        self.assertEqual(validate_snapshot(copy.deepcopy(current)), current)

    def test_no_change_does_not_assert_official_meaning_or_site_approval(self):
        before = self.make_capture(captured="2026-10-20T08:15:00Z")
        after = self.make_capture(captured="2026-10-22T08:15:00Z")
        result = compare_snapshots(before, after)
        self.assertEqual(result["status"], UNCHANGED_STATUS)
        self.assertEqual(result["changed_source_count"], 0)
        self.assertFalse(result["official_site_position_human_review_completed"])
        self.assertFalse(result["shelter_opening_or_disaster_safety_evaluated"])
        self.assertEqual(result["safety"], SAFETY)

    def test_one_modified_pdf_requires_human_review_and_never_approves(self):
        before = self.make_capture()
        after = self.make_capture(altered_ward=WATCH_SOURCES[0][0])
        result = compare_snapshots(before, after)
        self.assertEqual(result["status"], CHANGED_STATUS)
        self.assertEqual(result["changed_source_count"], 1)
        self.assertTrue(result["human_original_content_review_required"])
        self.assertEqual(sum(s["raw_bytes_changed"] for s in result["sources"]), 1)
        self.assertFalse(result["safety"]["approved_for_map"])

    def test_refuses_missing_renamed_extra_urls_or_fingerprint_forgery(self):
        before = self.make_capture()
        for transform in [
            lambda d: d["sources"].pop(),
            lambda d: d["sources"][0].update(url="https://example.invalid/a.pdf"),
            lambda d: d["sources"][0].update(sha256="bad"),
            lambda d: d["sources"][0].update(byte_size=True),
            lambda d: d["safety"].update(approved_for_map=True),
            lambda d: d.update(private_coordinates=[136.9, 35.1]),
            lambda d: d.update(captured_at_utc="2026-99-99T00:00:00Z"),
        ]:
            bad = copy.deepcopy(before)
            transform(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                compare_snapshots(before, bad)

    def test_capture_aborts_for_html_instead_of_pdf_or_missing_source(self):
        for payload in (b"<html>permission denied</html>",
                        b"", b"%PDF-1.7\n" + (b"x" * MAX_BYTES)):
            with self.subTest(length=len(payload)), self.assertRaises(ValueError):
                capture_snapshot(lambda url: payload)
        with self.assertRaises(ValueError):
            fetch_pdf("https://untrusted.example.net/file.pdf")
        # Redirect is never silently followed to a new source.
        with self.assertRaisesRegex(ValueError, "REDIRECT"):
            NoRedirect().redirect_request(None, None, 302, "moved", None, "https://example.org/new.pdf")

    def test_filesystem_basename_is_constrained_to_local_review_directory(self):
        from pathlib import Path
        folder = Path("/temporary/locally-held-only")
        self.assertEqual(
            local_file(folder, "official_pdf_snapshot_LOCAL.json"),
            folder / "official_pdf_snapshot_LOCAL.json")
        self.assertEqual(
            local_file(folder, "official_pdf_comparison_day2_LOCAL.json"),
            folder / "official_pdf_comparison_day2_LOCAL.json")
        for bad in ("/tmp/external.json", "../official_pdf_snapshot_LOCAL.json",
                    "team_review_p1_LOCAL.json", "official_pdf_snapshot_LOCAL.exe"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                local_file(folder, bad)


if __name__ == "__main__":
    unittest.main()
