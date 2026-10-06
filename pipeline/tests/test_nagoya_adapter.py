import json
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from src.hinanex.adapters.nagoya_shelter import NagoyaShelterAdapter
from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.evaluation.gap import analyze_capability_gap
from src.hinanex.evaluation.shelter_location import assess_shelter_location
from src.hinanex.models.common import Evidence, NormalizedDataset


class NagoyaShelterAdapterTests(unittest.TestCase):
    def test_discovers_only_indoor_excel_links(self) -> None:
        html = """
        <html><body>
          <a href="/data/chikusa.xls">千種区（屋内施設） （Excel 44 KB）</a>
          <a href="/data/higashi.xlsx">東区（屋内施設） （Excel 41 KB）</a>
          <a href="/data/chikusa.pdf">千種区（屋内施設） （PDF）</a>
          <a href="/data/outdoor.xls">広域避難場所 （Excel）</a>
        </body></html>
        """

        links = NagoyaShelterAdapter.discover_indoor_excel_links(html)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0][0], "千種区")
        self.assertTrue(links[0][1].endswith("chikusa.xls"))
        self.assertEqual(links[1][0], "東区")

    def test_dataset_scope_explicitly_excludes_outdoor_files(self) -> None:
        self.assertIn("16区別の屋内施設Excelのみ", NagoyaShelterAdapter.DATASET_SCOPE_NOTE)
        self.assertIn("屋外施設データは含めていない", NagoyaShelterAdapter.DATASET_SCOPE_NOTE)

    def test_extracts_page_update_date(self) -> None:
        html = "<p>ページID1013492 更新日 2026年9月15日</p>"
        updated = NagoyaShelterAdapter.extract_page_update_date(html)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.date().isoformat(), "2026-09-15")

    def test_page_update_date_stays_out_of_published_at(self) -> None:
        rows = [
            ["【屋内施設】", None, None, None, None],
            ["学区", "番号", "施設名称", "所在地", "指定避難所"],
            [None, None, None, None, None],
            ["千種", "ア1", "千種小学校", "千種3-2-5", "○"],
        ]
        workbook = BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(
                writer,
                sheet_name="Sheet1",
                header=False,
                index=False,
            )

        manifest = [
            {
                "ward": "千種区",
                "url": "https://example.invalid/chikusa.xlsx",
                "filename": "chikusa.xlsx",
            }
        ]
        bundle = BytesIO()
        with ZipFile(bundle, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False),
            )
            archive.writestr("chikusa.xlsx", workbook.getvalue())

        adapter = NagoyaShelterAdapter()
        adapter._page_updated_at = datetime(
            2026,
            9,
            15,
            tzinfo=timezone(timedelta(hours=9)),
        )
        dataset = adapter.normalize(bundle.getvalue())

        evidence = dataset.evidence[0]
        self.assertIsNone(evidence.published_at)
        self.assertIsNotNone(evidence.notes)
        self.assertIn("2026-09-15", evidence.notes)
        self.assertIn("更新日", evidence.notes)
        self.assertIn("Evidence.published_atには使用しない", evidence.notes)

    def test_normalizes_multirow_excel_table_without_inventing_coordinates(self) -> None:
        rows = [
            ["【屋内施設】", None, None, None, None, None, None, None, None],
            [
                "学区",
                "番号",
                "施設名称",
                "所在地",
                "指定緊急避難場所",
                None,
                None,
                None,
                "指定避難所",
            ],
            [None, None, None, None, "洪水 内水", "高潮", "土砂", "津波", None],
            ["千種", "ア1", "千種小学校", "千種3-2-5", "○", "－", "○", "－", "○"],
            [None, "ア2", "今池中学校", "今池3-19-1", "②", "－", "②", "－", "○"],
        ]
        table = pd.DataFrame(rows)

        records = NagoyaShelterAdapter.normalize_table(table, ward="千種区")
        self.assertEqual(len(records), 2)

        first = records[0]
        self.assertEqual(first.name, "千種小学校")
        self.assertEqual(first.address, "千種3-2-5")
        self.assertEqual(first.administrative_area, "千種区")
        self.assertIsNone(first.latitude)
        self.assertIsNone(first.longitude)
        self.assertEqual(
            first.supported_disasters,
            ["flood", "inland_flood", "landslide"],
        )
        self.assertEqual(
            first.facility_type,
            "designated_shelter_and_emergency_evacuation_site",
        )

    def test_missing_coordinates_become_confirmed_gap_not_dropped_rows(self) -> None:
        rows = [
            ["学区", "番号", "施設名称", "所在地", "指定緊急避難場所", None, None, None, "指定避難所"],
            [None, None, None, None, "洪水内水", "高潮", "土砂", "津波", None],
            ["千種", "ア1", "千種小学校", "千種3-2-5", "○", "－", "○", "－", "○"],
        ]
        records = NagoyaShelterAdapter.normalize_table(
            pd.DataFrame(rows),
            ward="千種区",
        )

        dataset = NormalizedDataset(
            region_code="23100",
            region_name="愛知県名古屋市",
            requirement_code="shelter_location",
            records=[record.model_dump() for record in records],
            evidence=[
                Evidence(
                    source_name="Nagoya test",
                    source_url="https://example.invalid/test.xls",
                    publisher="名古屋市",
                    fetched_at=datetime.now(timezone.utc),
                    source_format="XLS",
                    retrieval_method="TEST",
                )
            ],
            normalized_at=datetime.now(timezone.utc),
        )

        assessment = assess_shelter_location(dataset)
        capability = assess_shelter_discovery([assessment])
        gap = analyze_capability_gap(capability, [assessment])

        self.assertEqual(assessment.data_quality.completeness.score, 0)
        self.assertIsNone(assessment.data_quality.validity.score)
        self.assertEqual(
            assessment.application_readiness.geospatial_usability.score,
            0,
        )
        self.assertEqual(capability.status.value, "BLOCKED")
        self.assertEqual(len(gap.gaps), 1)
        self.assertEqual(gap.gaps[0].kind.value, "CONFIRMED_IMPROVEMENT")


if __name__ == "__main__":
    unittest.main()
