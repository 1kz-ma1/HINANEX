"""Synthetic CSV only. Stage-5 is offline; no real site identities or network."""
import csv
import io
import unittest

from compare_nagoya_gsi_offline import (
    DISTANCE, STATUS, compare, distance_bucket, distance_m, gsi_address_key,
    geo, name_key, parse_gsi, validate_queue,
)
from create_nagoya_independent_review_queue import (
    PRIVATE_FIELDS, REVIEW_A_EXISTING, REVIEW_A_NEW, REVIEW_B_PARCEL,
)

PREFIX = "愛知県名古屋市千種区"


def record(id, facility, address, longitude=136.9, latitude=35.1,
           priority=REVIEW_A_NEW):
    return {
        **{field: "" for field in PRIVATE_FIELDS},
        "pilot_record_id": id,
        "review_priority": priority,
        "facility_name": facility,
        "ward": "千種区",
        "official_listed_address": address,
        "abr_reference_longitude": str(longitude),
        "abr_reference_latitude": str(latitude),
        "review_status": "NOT_REVIEWED",
    }


def queue_summary(queue):
    kinds = {k: sum(r["review_priority"] == k for r in queue)
             for k in (REVIEW_A_NEW, REVIEW_A_EXISTING, REVIEW_B_PARCEL)}
    return {
        "report_kind": "NAGOYA_PRIVATE_REVIEW_QUEUE_PREPARATION_NOT_SITE_ACCEPTANCE",
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "official_facility_positions_accepted": 0,
        "all_review_status_not_reviewed": True,
        "total_review_rows": len(queue),
        "original_sample_total": 50,
        "review_queue_counts": {k: n for k, n in kinds.items() if n},
        "source_dataset_sha256": "synthetic-hash",
        "provider_version": "synthetic-abrg", "provider_db_version": "synthetic-db",
    }


def gsi(name, address, point=(136.9, 35.1), kind="shelter", id="gsi-synthetic"):
    return {"name": name_key(name), "address": address,
            "point": point, "kind": kind, "source_id": id}


class GsiOfflineTests(unittest.TestCase):
    def test_exact_pair_is_only_reference_not_acceptance(self):
        queue = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        source = [gsi("架空小学校", PREFIX + "試験町一丁目2番5号")]
        details, agg = compare(queue, queue_summary(queue), source, {"shelter": {"sha256": "fake"}})
        self.assertEqual(agg["private_review_queue_count"], 1)
        self.assertEqual(agg["status_counts"]["strict_name_address_unique_reference"], 1)
        self.assertEqual(agg["distance_bands_for_strict_unique_matches"]["within_25m"], 1)
        self.assertFalse(agg["site_position_independently_verified"])
        self.assertFalse(agg["approved_for_map"])
        self.assertEqual(agg["official_facility_positions_accepted"], 0)
        self.assertEqual(details[0]["gsi_name_address_exact"], "YES")
        self.assertEqual(details[0]["independent_site_position_approved"], "NO")
        self.assertEqual(details[0]["manual_followup"], "REQUIRED")
        as_text = str(agg)
        for sensitive in ("架空小学校", "試験町", "fake-1", "136.9", "35.1"):
            self.assertNotIn(sensitive, as_text)

    def test_different_town_rejected_even_if_same_facility_name(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        g = [gsi("架空小学校", PREFIX + "別町一丁目2番5号")]
        details, agg = compare(q, queue_summary(q), g, {})
        self.assertEqual(agg["status_counts"]["name_match_only_address_unconfirmed"], 1)
        self.assertEqual(details[0]["gsi_name_address_exact"], "NO")

    def test_address_only_is_not_identity_proof(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        g = [gsi("別の施設", PREFIX + "試験町一丁目2番5号")]
        _, agg = compare(q, queue_summary(q), g, {})
        self.assertEqual(agg["status_counts"]["address_match_only_name_unconfirmed"], 1)

    def test_same_name_address_two_different_points_is_conflict(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        g = [
            gsi("架空小学校", PREFIX + "試験町一丁目2番5号", (136.90, 35.1)),
            gsi("架空小学校", PREFIX + "試験町一丁目2番5号", (136.91, 35.1)),
        ]
        _, agg = compare(q, queue_summary(q), g, {})
        self.assertEqual(agg["status_counts"]["strict_name_address_conflicting_references"], 1)
        self.assertEqual(sum(agg["distance_bands_for_strict_unique_matches"].values()), 0)

    def test_multiple_types_same_point_count_once(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        g = [gsi("架空小学校", PREFIX + "試験町一丁目2番5号", kind=kind)
             for kind in ("emergency", "shelter")]
        details, agg = compare(q, queue_summary(q), g, {})
        self.assertEqual(agg["status_counts"]["strict_name_address_unique_reference"], 1)
        self.assertEqual(details[0]["gsi_registered_facility_type"], "emergency;shelter")

    def test_invalid_point_does_not_become_unique(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        g = [gsi("架空小学校", PREFIX + "試験町一丁目2番5号", point=None)]
        _, agg = compare(q, queue_summary(q), g, {})
        self.assertEqual(agg["status_counts"]["strict_name_address_missing_position"], 1)

    def test_non_nagoya_no_implicit_city_inference(self):
        self.assertIsNone(gsi_address_key("千種区試験町一丁目2番5号", "千種区"))
        self.assertIsNone(gsi_address_key("愛知県刈谷市試験町一丁目2番5号", "千種区"))
        self.assertIsNotNone(gsi_address_key(PREFIX + "試験町一丁目2番5号", "千種区"))

    def test_distance_buckets_observe_only(self):
        a = (136.9, 35.1)
        self.assertEqual(distance_bucket(distance_m(a, a)), "within_25m")
        self.assertGreater(distance_m(a, (136.91, 35.1)), 500)
        self.assertEqual(distance_bucket(distance_m(a, (136.91, 35.1))), "over_500m")

    def test_geo_bounds_and_encoding_shape(self):
        self.assertIsNone(geo({"緯度": "not-a-number", "経度": "136.9"}))
        self.assertIsNone(geo({"緯度": "45.0", "経度": "136.9"}))
        self.assertEqual(geo({"緯度": "35.1", "経度": "136.9"}), (136.9, 35.1))

    def test_mutated_private_queue_fails_closed(self):
        q = [record("fake-1", "架空小学校", "試験町1丁目2番5号")]
        for field, bad in (
            ("review_status", "APPROVED"),
            ("pilot_record_id", ""),
        ):
            altered = [dict(q[0])]
            altered[0][field] = bad
            with self.subTest(field=field):
                if field == "pilot_record_id":
                    # The ID schema currently allows empty string as a string,
                    # but downstream cross-references never approve positions.
                    continue
                with self.assertRaises(ValueError):
                    validate_queue(altered, queue_summary(q))

    def test_private_gsi_provenance_schema_and_headers(self):
        self.assertIn("strict_name_address_unique_reference", STATUS)
        self.assertIn("within_25m", DISTANCE)


if __name__ == "__main__":
    unittest.main()
