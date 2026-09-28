import unittest

from src.hinanex.adapters.niigata_shelter import NiigataShelterAdapter
from src.hinanex.evaluation.shelter_location import assess_shelter_location


class NiigataShelterAdapterTests(unittest.TestCase):
    def test_discovers_current_standard_csv_link(self) -> None:
        html = """
        <html><body>
          <table>
            <tr>
              <td>
                <a href="/files/15100_evacuation_space.csv">
                  <img alt="ダウンロードのリンク">
                  指定緊急避難場所一覧(CSV:171KB)
                </a>
              </td>
              <td>CSV</td>
              <td>防災課</td>
              <td>2026年9月25日</td>
            </tr>
          </table>
        </body></html>
        """

        url = NiigataShelterAdapter.discover_csv_url(html)
        self.assertEqual(
            url,
            "https://www.city.niigata.lg.jp/files/15100_evacuation_space.csv",
        )

        updated = NiigataShelterAdapter.extract_update_date(html)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.date().isoformat(), "2026-09-25")

    def test_normalizes_standard_ods_and_preserves_missing_coordinates(self) -> None:
        csv_text = """全国地方公共団体コード,ID,名称,緯度,経度,災害種別_洪水,災害種別_地震,URL,備考
151009,N001,新潟テスト避難場所A,37.9000,139.0200,1,1,https://example.invalid/a,
151009,N002,新潟テスト避難場所B,,,1,,,
"""

        adapter = NiigataShelterAdapter()
        adapter._resolved_source_url = "https://example.invalid/evacuation.csv"
        dataset = adapter.normalize(csv_text.encode("utf-8"))

        self.assertEqual(dataset.region_code, "15100")
        self.assertEqual(dataset.requirement_code, "shelter_location")
        self.assertEqual(len(dataset.records), 2)

        first = dataset.records[0]
        self.assertEqual(first["name"], "新潟テスト避難場所A")
        self.assertEqual(
            first["supported_disasters"],
            ["flood", "earthquake"],
        )

        second = dataset.records[1]
        self.assertIsNone(second["latitude"])
        self.assertIsNone(second["longitude"])

        assessment = assess_shelter_location(dataset)
        self.assertLess(assessment.data_quality.completeness.score, 4)
        self.assertLess(
            assessment.application_readiness.geospatial_usability.score,
            4,
        )


if __name__ == "__main__":
    unittest.main()
