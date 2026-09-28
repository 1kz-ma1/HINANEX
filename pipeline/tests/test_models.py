import unittest

from pydantic import ValidationError

from src.hinanex.models.assessment import MetricScore
from src.hinanex.models.shelter import ShelterRecord


class ShelterRecordTests(unittest.TestCase):
    def test_valid_shelter(self) -> None:
        shelter = ShelterRecord(
            id="s1",
            name="Test Shelter",
            latitude=35.7,
            longitude=139.8,
            supported_disasters=["flood"],
        )
        self.assertEqual(shelter.name, "Test Shelter")

    def test_invalid_latitude_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ShelterRecord(
                id="s1",
                name="Invalid Shelter",
                latitude=100.0,
                longitude=139.8,
            )


class MetricScoreTests(unittest.TestCase):
    def test_none_means_unassessed(self) -> None:
        metric = MetricScore(score=None, reason="未確認")
        self.assertIsNone(metric.score)

    def test_score_over_four_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            MetricScore(score=5, reason="invalid")


if __name__ == "__main__":
    unittest.main()
