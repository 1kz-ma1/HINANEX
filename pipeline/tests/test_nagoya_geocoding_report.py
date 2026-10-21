import copy
import unittest

from geocode_nagoya_pilot import prepare
from report_nagoya_geocoding_pilot import audit, presentation_summary


def fixture():
    manifest = prepare({
        "records": [{"id": "nagoya-test-1", "name": "架空施設",
                     "administrative_area": "千種区", "address": "千種3-2-5",
                     "latitude": None, "longitude": None}]
    }, "synthetic-digest")
    result = {
        "pilot_version": 1, "source_dataset_sha256": "synthetic-digest",
        "provider": "DIGITAL_AGENCY_ABR", "provider_db_version": "test-only",
        "approved_for_map": False, "data_promotion_authorized": False,
        "count": 1, "results": [{
            **manifest["selected"][0], "status": "UNVERIFIED_CANDIDATE",
            "reason": "human_site_review_required", "approved_for_map": False,
            "coordinates_level": "rsdtdsp_blk",
            "coordinate_source": "DIGITAL_AGENCY_ABR_ADDRESS_GEOCODER",
            "derived_geometry": {"latitude": 35.16, "longitude": 136.93},
        }],
    }
    return manifest, result


class NagoyaGeocodeReportTests(unittest.TestCase):
    def test_summary_marks_preliminary_and_requires_human(self):
        manifest, result = fixture()
        summary, worksheet = audit(manifest, result)
        self.assertEqual(summary["sample_total"], 1)
        self.assertEqual(summary["unverified_candidate_count"], 1)
        self.assertEqual(summary["unverified_candidate_rate_percent"], 100)
        self.assertEqual(summary["official_site_coordinates_accepted"], 0)
        self.assertFalse(summary["approved_for_map"])
        self.assertEqual(worksheet[0]["human_review"], "NOT_REVIEWED")
        self.assertEqual(worksheet[0]["candidate_latitude"], 35.16)

    def test_presentation_summary_is_explicitly_unverified_and_anonymous(self):
        manifest, result = fixture()
        summary, _ = audit(manifest, result)
        rendered = presentation_summary(summary)
        self.assertIn("1/1", rendered)
        self.assertIn("独立検証は未了", rendered)
        self.assertIn("0件", rendered)
        self.assertNotIn("架空施設", rendered)
        self.assertNotIn("136.93", rendered)

    def test_reject_approved_map_result(self):
        manifest, result = fixture()
        result["results"][0]["approved_for_map"] = True
        with self.assertRaises(ValueError):
            audit(manifest, result)

    def test_reject_hash_mismatch(self):
        manifest, result = fixture()
        result["source_dataset_sha256"] = "other"
        with self.assertRaises(ValueError):
            audit(manifest, result)

    def test_reject_mutated_address(self):
        manifest, result = fixture()
        result["results"][0]["source_address"] = "書き換え"
        with self.assertRaises(ValueError):
            audit(manifest, result)

    def test_reject_duplicate_records_and_mismatched_count(self):
        manifest, result = fixture()
        result["results"].append(copy.deepcopy(result["results"][0]))
        result["count"] = 2
        with self.assertRaises(ValueError):
            audit(manifest, result)

    def test_unresolved_does_not_count_as_success(self):
        manifest, result = fixture()
        result["results"][0]["status"] = "UNRESOLVED"
        del result["results"][0]["derived_geometry"]
        summary, _ = audit(manifest, result)
        self.assertEqual(summary["unverified_candidate_rate_percent"], 0)
        self.assertEqual(summary["unresolved_count"], 1)

    def test_missing_candidate_geometry_rejected(self):
        manifest, result = fixture()
        del result["results"][0]["derived_geometry"]
        with self.assertRaises(ValueError):
            audit(manifest, result)


if __name__ == "__main__":
    unittest.main()
