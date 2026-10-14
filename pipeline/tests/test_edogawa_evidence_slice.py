"""No-network tests for D's source-pinned Edogawa single-region replay."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from run_edogawa_evidence_slice import replay, EdogawaReplayError
from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter
from src.hinanex.integration import read_region_export, assert_valid_region_export
from src.hinanex.scenario_sources import EDOGAWA_HAZARD_SOURCE


def make_archive(root):
    p = Path(root) / "raw"
    p.mkdir()
    csv = (
        "名称,URL,災害種別記号,コメント,緯度,経度\n"
        "下小岩小学校,https://example.org/school,icon,,35.71,139.88\n"
        "旧下小岩小学校（体育館のみ使用）,https://example.org/school,icon,,35.72,139.89\n"
    ).encode("cp932")
    water = b"<html><body>Water source, not facility identity</body></html>"
    data = [
        ("municipal_locations", "municipal_locations.csv",
         EdogawaShelterAdapter.SOURCE_URL, csv),
        ("water_facilities", "water_facilities.html",
         EDOGAWA_HAZARD_SOURCE, water),
    ]
    items = []
    for key, filename, url, raw in data:
        (p / filename).write_bytes(raw)
        items.append({
            "source_key": key,
            "requested_url": url,
            "final_url": url,
            "archive_filename": filename,
            "byte_size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    for i in range(5):
        items.append({"source_key": f"additional_official_{i}"})
    manifest = {
        "purpose": "C_EVIDENCE_ARCHIVE_ONLY_NO_C_INDEPENDENT_ACCEPTANCE",
        "human_c_reviewer_signed_off": False,
        "flood_scenario_classifications_added": 0,
        "source_items": items,
    }
    (p / "snapshot_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return p, manifest


class DReplayTests(unittest.TestCase):
    def test_region_export_and_unknown_flood_results(self):
        with TemporaryDirectory() as root:
            raw, _ = make_archive(root)
            out = Path(root) / "out"
            report = replay(raw, out)
            export = read_region_export(out / "edogawa_current_D_UNREVIEWED.json")
            assert_valid_region_export(export, region_key="edogawa")
            self.assertEqual(len(export.scenarios), 1)
            self.assertEqual(report["d_location_count"], 2)
            self.assertEqual(report["d_scenario_facility_status_counts"], {"UNKNOWN": 2})
            self.assertEqual(report["d_scenario_join_counts"], {"UNVERIFIED": 2})
            self.assertEqual(report["approved_cross_source_pairs"], 0)
            self.assertEqual(report["new_flood_candidates_or_exclusions"], 0)
            self.assertNotEqual(export.datasets[0].records[0]["id"],
                                export.datasets[0].records[1]["id"])
            self.assertEqual(export.datasets[0].records[0]["detail_url"],
                             export.datasets[0].records[1]["detail_url"])

    def test_changed_csv_rejected(self):
        with TemporaryDirectory() as root:
            raw, _ = make_archive(root)
            p = raw / "municipal_locations.csv"
            p.write_bytes(p.read_bytes() + b"changed")
            with self.assertRaisesRegex(EdogawaReplayError, "SHA256 mismatch"):
                replay(raw, Path(root) / "out")

    def test_wrong_source_url_rejected(self):
        with TemporaryDirectory() as root:
            raw, manifest = make_archive(root)
            manifest["source_items"][0]["requested_url"] = "https://example.org/other"
            (raw / "snapshot_manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(EdogawaReplayError, "URL changed"):
                replay(raw, Path(root) / "out")

    def test_no_overwrite(self):
        with TemporaryDirectory() as root:
            raw, _ = make_archive(root)
            out = Path(root) / "out"
            out.mkdir()
            (out / "keep.json").write_text("{}")
            with self.assertRaisesRegex(EdogawaReplayError, "new or empty"):
                replay(raw, out)


if __name__ == "__main__":
    unittest.main()
