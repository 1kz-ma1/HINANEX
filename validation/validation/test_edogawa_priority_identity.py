"""Synthetic-only C regression for high-risk Edogawa institution ID leads.

The approved-pair count is ALWAYS ZERO. These checks validate only the
historical candidate/URL trace and old-vs-new school separation.
"""
import copy
import unittest

from verify_edogawa_water_join import (
    AuditFailure,
    PRIORITY_SCHOOL_REFERENCES,
    review_priority_identity_leads,
    duplicate_municipal_detail_urls,
)


def fixture():
    p1, p2 = PRIORITY_SCHOOL_REFERENCES
    official = [
        {
            "official_number_raw": p["official_number"],
            "official_name_raw": p["water_name"],
            "official_address_raw": p["water_address"],
            "official_phone_raw": p["water_phone"],
            "official_usable_floor_raw": p["water_floor_raw"],
        }
        for p in (p1, p2)
    ]
    official += [
        {
            "official_number_raw": "60",
            "official_name_raw": "下小岩小学校",
            "official_address_raw": "南小岩5丁目5番1号",
            "official_usable_floor_raw": "2階以上",
            "official_phone_raw": "03-3650-1714",
        },
        {
            "official_number_raw": "-",
            "official_name_raw": "旧下小岩小学校",
            "official_address_raw": "南小岩7丁目8番1号",
            "official_usable_floor_raw": "大規模水害では使用不可",
            "official_phone_raw": "-",
        },
    ]
    schools = [
        {
            "id": p["expected_location_id"],
            "name": p["location_name"],
            "latitude": 35.7 + i * .01,
            "longitude": 139.8 + i * .01,
            "detail_url": p["location_url"],
        }
        for i, p in enumerate((p1, p2))
    ]
    shared_url = "https://edogawa.schoolweb.ne.jp/1310306/page/root"
    schools += [
        {
            "id": "edogawa-63e5f1484966fd39",
            "name": "下小岩小学校", "latitude": 35.72545,
            "longitude": 139.87842, "detail_url": shared_url,
        },
        {
            "id": "edogawa-f967bd79a9960d9e",
            "name": "旧下小岩小学校（体育館のみ使用）",
            "latitude": 35.72768, "longitude": 139.88310,
            "detail_url": shared_url,
        },
    ]
    raw = [{"名称": r["name"], "URL": r["detail_url"]} for r in schools]
    return [official, raw, schools]


def run(x):
    return review_priority_identity_leads(*x)


class PriorityDocumentaryReviewTests(unittest.TestCase):
    def test_two_school_documentary_paths_are_explicitly_not_approved(self):
        checks = run(fixture())
        self.assertEqual(len(checks), 3)
        for item in checks:
            self.assertFalse(item["approved_cross_source_pair"])
            self.assertEqual(item["flood_specific_eligibility"], "UNKNOWN")
        self.assertEqual(
            {x.get("d_location_id") for x in checks[:2]},
            {"edogawa-d79a702373c6add7", "edogawa-fbe048a8e7100768"},
        )
        for item in checks[:2]:
            self.assertTrue(item["institution_authority_url"].startswith("https://"))
            self.assertEqual(item["documentary_state"],
                             "CORROBORATION_LEAD_NOT_INDEPENDENTLY_ACCEPTED")

    def test_old_and_new_site_have_different_ids_addresses_and_coordinates(self):
        entry = run(fixture())[2]
        self.assertNotEqual(entry["old_d_location_id"], entry["new_d_location_id"])
        self.assertNotEqual(entry["water_address_raw"], entry["new_water_address_raw"])
        self.assertTrue(entry["same_school_site_url_in_raw"])
        self.assertTrue(entry["shared_school_site_url_is_not_a_facility_identity_key"])
        self.assertEqual(entry["old_water_floor_raw"], "大規模水害では使用不可")

    def test_changed_municipal_school_address_requires_review(self):
        f = fixture()
        f[0][0]["official_address_raw"] = "別住所"
        with self.assertRaisesRegex(AuditFailure, "source changed"):
            run(f)

    def test_wrong_school_website_is_not_a_verified_identity_hint(self):
        f = fixture()
        f[1][0]["URL"] = "https://third-party.invalid/"
        with self.assertRaisesRegex(AuditFailure, "institution URL differs"):
            run(f)

    def test_d_location_id_change_requires_review(self):
        f = fixture()
        f[2][1]["id"] = "edogawa-replacement"
        with self.assertRaisesRegex(AuditFailure, "facility ID changed"):
            run(f)

    def test_duplicate_location_school_is_ambiguous(self):
        f = fixture()
        f[2].append(copy.deepcopy(f[2][0]))
        with self.assertRaisesRegex(AuditFailure, "institution name missing or ambiguous"):
            run(f)

    def test_old_site_restriction_cannot_be_silently_removed(self):
        f = fixture()
        f[0][3]["official_usable_floor_raw"] = "2階以上"
        with self.assertRaisesRegex(AuditFailure, "conditions changed"):
            run(f)

    def test_same_coordinates_cannot_collapse_old_into_new_school(self):
        f = fixture()
        f[2][3]["latitude"] = f[2][2]["latitude"]
        f[2][3]["longitude"] = f[2][2]["longitude"]
        with self.assertRaisesRegex(AuditFailure, "coordinates collapsed"):
            run(f)

    def test_school_url_is_not_trusted_as_old_site_identity(self):
        f = fixture()
        f[2][3]["detail_url"] = "https://other.invalid/"
        with self.assertRaisesRegex(AuditFailure, "URLs differ"):
            run(f)

    def test_generic_collision_detector_reports_shared_official_url(self):
        official, source, locations = fixture()
        collisions = duplicate_municipal_detail_urls(source, locations)
        self.assertEqual(len(collisions), 1)
        group = collisions[0]
        self.assertEqual(group["record_count"], 2)
        self.assertEqual(group["distinct_original_coordinates"], 2)
        self.assertTrue(group["source_url_not_facility_key"])
        self.assertFalse(group["independent_cross_source_identity_approved"])
        self.assertEqual(group["flood_specific_eligibility"], "UNKNOWN")
        self.assertEqual(set(group["D_facility_names"]), {
            "下小岩小学校", "旧下小岩小学校（体育館のみ使用）",
        })
        self.assertEqual(set(group["D_facility_ids"]), {
            "edogawa-63e5f1484966fd39",
            "edogawa-f967bd79a9960d9e",
        })

    def test_any_mutated_d_homepage_url_fails_original_source_trace(self):
        _, source, locations = fixture()
        locations[0]["detail_url"] = "https://fake.example.net/"
        with self.assertRaisesRegex(AuditFailure, "D link differs"):
            duplicate_municipal_detail_urls(source, locations)

    def test_distinct_homepages_produce_no_collision(self):
        _, source, locations = fixture()
        for i in range(len(source)):
            source[i]["URL"] = "https://school.invalid/" + str(i)
            locations[i]["detail_url"] = source[i]["URL"]
        self.assertEqual(duplicate_municipal_detail_urls(source, locations), [])

    def test_non_priority_fixture_is_unaffected(self):
        self.assertEqual(run([[], [], []]), [])

    def test_old_site_alone_does_not_implicitly_identify_a_school(self):
        f = fixture()
        f[0] = [f[0][3]]  # No new/current official water row.
        with self.assertRaisesRegex(AuditFailure, "water rows ambiguous"):
            run(f)


if __name__ == "__main__":
    unittest.main()
