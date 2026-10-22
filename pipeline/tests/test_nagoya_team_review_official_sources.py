"""Synthetic and public municipal-source-only tests; no PRIVATE payloads."""
import copy
import unittest

from export_nagoya_team_review_json import make_package
from nagoya_team_review_official_sources import (
    OFFICIAL_LICENSE,
    OFFICIAL_MAIN,
    OFFICIAL_NAME_ADDRESS_WARD,
    WARD_PDFS,
    official_ward_pdf,
)
from refine_nagoya_gsi_stage7 import refine
from test_nagoya_gsi_stage7 import historical_fixture


class OfficialSourcePrefillTests(unittest.TestCase):
    def test_all_nine_public_source_pairs_have_official_pdf(self):
        self.assertEqual(len(OFFICIAL_NAME_ADDRESS_WARD), 9)
        self.assertEqual(set(OFFICIAL_NAME_ADDRESS_WARD.values()), set(WARD_PDFS))
        self.assertTrue(OFFICIAL_MAIN.startswith("https://www.city.nagoya.jp/"))
        self.assertIn("creativecommons.org/licenses/by/4.0", OFFICIAL_LICENSE)
        for (name, address), ward in OFFICIAL_NAME_ADDRESS_WARD.items():
            src = official_ward_pdf(name, address)
            self.assertIn(ward, src["title"])
            self.assertEqual(src["url"], WARD_PDFS[ward])
            self.assertTrue(src["url"].startswith("https://www.city.nagoya.jp/"))

    def test_mismatched_name_or_address_never_produces_official_match(self):
        name, address = next(iter(OFFICIAL_NAME_ADDRESS_WARD))
        self.assertIsNone(official_ward_pdf(name, address + "-DIFFERENT"))
        self.assertIsNone(official_ward_pdf("OTHER" + name, address))
        self.assertIsNone(official_ward_pdf("", address))

    def test_package_adds_only_source_link_without_marking_reviewed(self):
        rows, agg = refine(*historical_fixture())
        agg["source_dataset_sha256"] = "b" * 64
        row = next(r for r in rows if r["stage7_priority"].startswith("P1"))
        row["facility_name"] = "平針南小学校"
        row["official_listed_address"] = "平針南4-402"
        package = make_package(rows, agg, ("P1",))
        entry = next(r for r in package["records"] if r["name"] == "平針南小学校")
        self.assertEqual(len(entry["sources"]), 2)
        self.assertEqual(entry["review"]["status"], "not_reviewed")
        self.assertFalse(any(entry["review"]["checks"].values()))
        self.assertEqual(package["safety"]["approved_for_map"], False)
        changed = copy.deepcopy(rows)
        next(r for r in changed if r["facility_name"] == "平針南小学校")[
            "official_listed_address"] = "平針南4-403"
        wrong = make_package(changed, agg, ("P1",))
        entry = next(r for r in wrong["records"] if r["name"] == "平針南小学校")
        self.assertEqual(len(entry["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
