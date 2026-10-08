"""Deterministic C-only regression for the Nagoya raw-row comparator."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd

import verify_flood_scenario_acceptance as audit


class NagoyaAuditComparisonTests(unittest.TestCase):
    def test_whitespace_only_normalization(self):
        self.assertEqual(audit._normalized_excel_cell(" 千 種　小 学 校 "), "千種小学校")
        self.assertEqual(audit._normalized_excel_cell(" 千種 3-2-5 "), "千種3-2-5")
        self.assertEqual(audit._normalized_excel_cell(" ② "), "②")
        self.assertNotEqual(audit._normalized_excel_cell("千種小学校"), "今池中学校")

    def _make_fixture(self, root: Path):
        excel = io.BytesIO()
        rows = [
            ["学区", "番号", "施設名称", "所在地", "指定緊急避難場所"],
            [None, None, None, None, "洪水 内水"],
            ["千種", "ア1", "千 種　小 学 校", "千種 3-2-5", " ② "],
        ]
        with pd.ExcelWriter(excel, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, index=False, header=False)
        manifest = [
            {
                "ward": f"区{i:02d}",
                "url": f"https://example.test/ward{i:02d}.xlsx",
                "filename": f"ward{i:02d}.xlsx",
            }
            for i in range(16)
        ]
        zip_path = root / "nagoya_indoor_shelters_bundle.zip"
        with ZipFile(zip_path, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
            for item in manifest:
                archive.writestr(item["filename"], excel.getvalue())
        result = {
            "facility_id": "nagoya-test",
            "status": "UNKNOWN",
            "fact": {
                "facility_id": "nagoya-test",
                "facility_name": "千種小学校",
                "hazard_scope_raw": "洪水・内水",
                "join_status": "DIRECT_SAME_SOURCE",
                "source_record_trace": "file=ward00.xlsx;sheet=0;excel_row=3",
                "source_url": "https://example.test/ward00.xlsx",
                "official_status_raw": "②",
            },
        }
        locations = {"records": [{"id": "nagoya-test", "address": "千種3-2-5"}]}
        return zip_path, {"facility_results": [result]}, locations

    def test_whitespace_differences_pass_but_real_name_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            zip_path, scenario, locations = self._make_fixture(Path(temp))
            with patch.object(audit, "NAGOYA_RAW", zip_path):
                audit.check_nagoya(scenario, locations)
                scenario["facility_results"][0]["fact"]["facility_name"] = "今池中学校"
                with self.assertRaisesRegex(audit.AcceptanceFailure, "facility name mismatch"):
                    audit.check_nagoya(scenario, locations)


if __name__ == "__main__":
    unittest.main()
