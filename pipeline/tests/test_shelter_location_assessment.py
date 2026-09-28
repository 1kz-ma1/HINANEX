import unittest
from datetime import datetime, timezone

from src.hinanex.evaluation.shelter_location import assess_shelter_location
from src.hinanex.models.common import Evidence, NormalizedDataset


class ShelterLocationAssessmentTests(unittest.TestCase):
    def _dataset(self, records: list[dict]) -> NormalizedDataset:
        now = datetime.now(timezone.utc)
        return NormalizedDataset(
            region_code="13123",
            region_name="東京都江戸川区",
            requirement_code="shelter_location",
            records=records,
            evidence=[
                Evidence(
                    source_name="test CSV",
                    fetched_at=now,
                    source_format="CSV",
                    retrieval_method="HTTP_DOWNLOAD",
                )
            ],
            normalized_at=now,
        )

    def test_complete_valid_location_dataset_scores_four(self) -> None:
        dataset = self._dataset(
            [
                {
                    "id": "s1",
                    "name": "Shelter A",
                    "latitude": 35.7,
                    "longitude": 139.8,
                },
                {
                    "id": "s2",
                    "name": "Shelter B",
                    "latitude": 35.71,
                    "longitude": 139.81,
                },
            ]
        )

        result = assess_shelter_location(dataset)

        self.assertEqual(result.data_quality.completeness.score, 4)
        self.assertEqual(result.data_quality.validity.score, 4)
        self.assertEqual(
            result.application_readiness.machine_readability.score,
            4,
        )
        self.assertEqual(
            result.application_readiness.geospatial_usability.score,
            4,
        )
        self.assertIsNone(result.data_quality.coverage.score)

    def test_missing_location_reduces_completeness(self) -> None:
        dataset = self._dataset(
            [
                {
                    "id": "s1",
                    "name": "Shelter A",
                    "latitude": 35.7,
                    "longitude": 139.8,
                },
                {
                    "id": "s2",
                    "name": "Shelter B",
                    "latitude": None,
                    "longitude": None,
                },
            ]
        )

        result = assess_shelter_location(dataset)

        self.assertEqual(result.data_quality.completeness.score, 1)
        self.assertEqual(
            result.application_readiness.geospatial_usability.score,
            1,
        )


    def test_missing_coordinates_do_not_count_as_invalid_values(self) -> None:
        dataset = self._dataset(
            [
                {
                    "id": "s1",
                    "name": "Shelter A",
                    "latitude": 35.7,
                    "longitude": 139.8,
                },
                {
                    "id": "s2",
                    "name": "Shelter B",
                    "latitude": None,
                    "longitude": None,
                },
            ]
        )

        result = assess_shelter_location(dataset)

        self.assertEqual(result.data_quality.completeness.score, 1)
        self.assertEqual(result.data_quality.validity.score, 4)
        self.assertEqual(
            result.application_readiness.geospatial_usability.score,
            1,
        )

    def test_no_coordinates_make_validity_unassessed_not_zero(self) -> None:
        dataset = self._dataset(
            [
                {
                    "id": "s1",
                    "name": "Shelter A",
                    "latitude": None,
                    "longitude": None,
                },
                {
                    "id": "s2",
                    "name": "Shelter B",
                    "latitude": None,
                    "longitude": None,
                },
            ]
        )

        result = assess_shelter_location(dataset)

        self.assertEqual(result.data_quality.completeness.score, 0)
        self.assertIsNone(result.data_quality.validity.score)
        self.assertEqual(
            result.application_readiness.geospatial_usability.score,
            0,
        )

    def test_other_requirement_is_rejected(self) -> None:
        dataset = self._dataset([])
        dataset.requirement_code = "shelter_capacity"

        with self.assertRaises(ValueError):
            assess_shelter_location(dataset)


if __name__ == "__main__":
    unittest.main()
