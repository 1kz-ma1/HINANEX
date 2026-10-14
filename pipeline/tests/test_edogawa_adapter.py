import unittest

from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter


class EdogawaShelterAdapterTests(unittest.TestCase):
    def test_source_update_date_is_not_treated_as_initial_publication_date(self) -> None:
        raw = (
            "名称,URL,災害種別記号,コメント,緯度,経度\n"
            "テスト避難所,https://example.test,icon,,35.7000,139.8700\n"
        ).encode("cp932")

        dataset = EdogawaShelterAdapter().normalize(raw)
        evidence = dataset.evidence[0]

        self.assertIsNone(evidence.published_at)
        self.assertIsNotNone(evidence.notes)
        self.assertIn("2025-12-11", evidence.notes)
        self.assertIn("更新日", evidence.notes)
        self.assertIn("初回公開日", evidence.notes)


    def test_optional_original_address_is_passed_through_only_when_present(self) -> None:
        scenarios = (
            ("", "", None),
            (",住所", ",平井4丁目1番23号", "平井4丁目1番23号"),
            (",所在地", ",平井4丁目1番23号", "平井4丁目1番23号"),
            (",住所,所在地", ",平井4丁目1番23号,平井4丁目1番23号", "平井4丁目1番23号"),
            (",住所,所在地", ",平井4丁目1番23号,小松川3丁目6番4号", None),
        )
        baseline_id = None
        for columns, values, expected in scenarios:
            with self.subTest(columns=columns, raw_values=values):
                raw = (
                    "名称,URL,災害種別記号,コメント,緯度,経度" + columns + "\n"
                    "テスト避難所,https://example.test,icon,,35.7000,139.8700" + values + "\n"
                ).encode("cp932")
                item = EdogawaShelterAdapter().normalize(raw).records[0]
                self.assertEqual(item["address"], expected)
                self.assertIsNone(item["supported_disasters"])
                self.assertEqual(item["latitude"], 35.7)
                self.assertEqual(item["longitude"], 139.87)
                if baseline_id is None:
                    baseline_id = item["id"]
                else:
                    self.assertEqual(item["id"], baseline_id,
                                     "Optional address cannot change stable facility IDs")

    def test_missing_address_does_not_borrow_any_location_from_name(self) -> None:
        raw = (
            "名称,URL,災害種別記号,コメント,緯度,経度,住所\n"
            "小松川小学校,https://example.test,icon,,35.7000,139.8700,\n"
        ).encode("cp932")
        item = EdogawaShelterAdapter().normalize(raw).records[0]
        self.assertIsNone(item["address"], "Never substitute the separate city water-hazard table")


if __name__ == "__main__":
    unittest.main()
