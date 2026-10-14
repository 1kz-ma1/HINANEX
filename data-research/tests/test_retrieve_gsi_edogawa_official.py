"""Offline A regression tests: GSI national CSV must never become D approval."""
import importlib.util
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "retrieve_gsi_edogawa_official.py"
spec = importlib.util.spec_from_file_location("gsi_a", SCRIPT)
gsi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gsi)


COLUMNS = [
    "NO", "共通ID", "都道府県名及び市町村名", "施設・場所名", "住所", "洪水",
    "崖崩れ、土石流及び地滑り", "高潮", "地震", "津波", "大規模な火事",
    "内水氾濫", "火山現象", "指定避難所との住所同一", "緯度", "経度", "備考",
]


def original(*, unknown_municipality=False, illegal_marker=False):
    def row(no, ident, region, name, address, flood, lat, lon):
        return [
            str(no), ident, region, name, address, flood,
            "", "", "", "", "", "", "", "", str(lat), str(lon), "",
        ]
    rows = [
        row(1, "001", "東京都江戸川区", "葛西工科高等学校",
            "東京都江戸川区一之江7丁目68番1号", "1", 35.683604, 139.8788767),
        row(2, "002", "東京都江戸川区", "関東第一高等学校",
            "東京都江戸川区松島二丁目10番11号", "", 35.708171, 139.8602629),
        row(3, "003", "東京都他区", "ほかの施設", "東京都他区1番", "", 35, 139),
    ]
    if unknown_municipality:
        for r in rows[:2]:
            r[2] = "別の自治体"
    if illegal_marker:
        rows[0][5] = "TRUE"
    import csv
    import io
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(COLUMNS)
    w.writerows(rows)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def fake_fetch(raw):
    return lambda: (raw, gsi.OFFICIAL_GSI_NATIONAL_CSV_URL, {
        "content_type": "text/csv",
        "last_modified": "Wed, 01 Jan 2025 00:00:00 GMT",
    })


class GsiOriginalTests(unittest.TestCase):
    def test_original_rows_preserve_source_and_no_hazard_approval(self):
        raw = original()
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "official"
            x = gsi.capture(
                p, fetch=fake_fetch(raw),
                now=datetime(2026, 10, 13, tzinfo=timezone.utc))
            self.assertEqual(x["status"], "GSI_EDOGAWA_ROWS_FOUND_UNREVIEWED")
            self.assertEqual(x["source_manifest"]["national_source_sha256"],
                             sha256(raw).hexdigest())
            self.assertEqual(x["source_manifest"]["edogawa_record_count_observed"], 2)
            self.assertEqual(len(x["priority_keyword_leads_for_human_review_only"]), 2)
            self.assertTrue((p / "gsi_national_original_UNREVIEWED.csv").read_bytes() == raw)
            self.assertEqual(x["edogawa_rows"][0]["gsi_flood_marker_raw"], "1")
            self.assertEqual(x["edogawa_rows"][1]["gsi_flood_marker_raw"], "")
            self.assertTrue(x["edogawa_rows"][0]["common_gsi_id_is_not_d_facility_id"])
            self.assertFalse(x["edogawa_rows"][0]["physical_site_link_c_approved"])
            self.assertIsNone(x["edogawa_rows"][0]["current_d_flood_scenario_change"])
            self.assertEqual(x["new_flood_classifications"], 0)
            self.assertEqual(x["independent_c_site_approvals"], 0)

    def test_no_observed_edogawa_means_review_not_nonpublication(self):
        with TemporaryDirectory() as tmp:
            x = gsi.capture(
                Path(tmp) / "archive",
                fetch=fake_fetch(original(unknown_municipality=True)))
            self.assertEqual(x["status"],
                             "GSI_EDOGAWA_ROWS_NOT_OBSERVED_REVIEW_REQUIRED")
            self.assertTrue(x["source_manifest"]["edogawa_absence_is_not_nonpublication"])
            self.assertEqual(x["independent_c_site_approvals"], 0)

    def test_invalid_flood_marker_refused_without_raw_write(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "archive"
            with self.assertRaisesRegex(gsi.GsiEvidenceFailure, "Unexpected GSI flood"):
                gsi.capture(dest, fetch=fake_fetch(original(illegal_marker=True)))
            self.assertFalse(dest.exists())

    def test_missing_national_municipality_column_refused(self):
        raw = original().replace("都道府県名及び市町村名".encode(), b"changed")
        with self.assertRaisesRegex(gsi.GsiEvidenceFailure, "header differs"):
            gsi.inspect_original(raw)

    def test_gsi_redirect_to_untrusted_url_blocked(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(gsi.GsiEvidenceFailure):
                gsi.capture(
                    Path(tmp) / "out",
                    fetch=lambda: (original(), "https://example.com/notcsv", {}),
                )

    def test_duplicate_gsi_common_id_rejected(self):
        raw = original().replace(b"002,", b"001,")
        with self.assertRaisesRegex(gsi.GsiEvidenceFailure, "duplicated"):
            gsi.inspect_original(raw)

    def test_csv_cannot_overwrite_prior_evidence(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "archive"
            dest.mkdir()
            (dest / "original.txt").write_text("previous")
            with self.assertRaisesRegex(gsi.GsiEvidenceFailure, "new/empty"):
                gsi.capture(dest, fetch=fake_fetch(original()))

    def test_gsi_dataset_hazards_do_not_classify_any_hinanex_record(self):
        x = gsi.inspect_original(original())
        self.assertEqual(len(x[2]), 2)
        self.assertFalse(
            any("CANDIDATE" in json.dumps(row) or
                "EXCLUDED" in json.dumps(row) for row in x[2])
        )


if __name__ == "__main__":
    unittest.main()
