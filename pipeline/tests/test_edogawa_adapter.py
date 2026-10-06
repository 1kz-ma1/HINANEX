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


if __name__ == "__main__":
    unittest.main()
