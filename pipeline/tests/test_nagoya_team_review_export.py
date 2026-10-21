"""Synthetic-only tests of local shareable review JSON; no private data committed."""
import copy
import json
import unittest

from export_nagoya_team_review_json import (
    ALLOWED_FLAGS, SCHEMA_ID, make_package,
)
from refine_nagoya_gsi_stage7 import refine
from test_nagoya_gsi_stage7 import historical_fixture


def synthetic_stage7():
    return refine(*historical_fixture())


class TeamReviewExportTests(unittest.TestCase):
    def test_p1_default_only_and_public_field_allowlist(self):
        rows, agg = synthetic_stage7()
        package = make_package(rows, agg, ("P1",))
        self.assertEqual(package["schema_id"], SCHEMA_ID)
        self.assertEqual(len(package["records"]), 3)
        self.assertEqual({r["priority"] for r in package["records"]}, {"P1"})
        self.assertEqual(package["safety"], {
            "approved_for_map": False,
            "data_promotion_authorized": False,
            "official_facility_positions_accepted": 0,
        })
        self.assertEqual(set(package), {"schema_id", "dataset", "safety", "records"})
        self.assertTrue(all(set(r) == {
            "id", "name", "address", "priority", "issues", "sources", "review",
        } for r in package["records"]))
        self.assertTrue(all(r["review"]["status"] == "not_reviewed" for r in package["records"]))
        self.assertTrue(all(not any(r["review"]["checks"].values())
                            for r in package["records"]))

    def test_all_34_like_synthetic_produces_all_without_approvals(self):
        rows, agg = synthetic_stage7()
        package = make_package(rows, agg, ("P0", "P1", "P2"))
        self.assertEqual(len(package["records"]), agg["review_rows_total"])
        self.assertEqual(
            {level: sum(r["priority"] == level for r in package["records"])
             for level in ("P0", "P1", "P2")},
            {"P0": 1, "P1": 3, "P2": 2})
        serialized = json.dumps(package, ensure_ascii=False)
        for secret in (
            "abr_reference_longitude", "abr_reference_latitude",
            "gsi_reference_longitude", "gsi_reference_latitude",
            "gsi_conflict_points_PRIVATE", "gsi_registered_record_ids",
            "pilot_record_id", "independent_site_position_approved",
            "approved_for_map\": true", "data_promotion_authorized\": true",
            "source_notice_verbatim_PRIVATE", "136.90", "35.10",
        ):
            self.assertNotIn(secret, serialized)
        self.assertTrue(all(set(r["issues"]).issubset(ALLOWED_FLAGS)
                            for r in package["records"]))

    def test_classifications_are_review_codes_not_new_safety_facts(self):
        rows, agg = synthetic_stage7()
        package = make_package(rows, agg, ("P0", "P2"))
        p0 = next(r for r in package["records"] if r["priority"] == "P0")
        self.assertIn("source_renovation_notice", p0["issues"])
        self.assertNotIn("different_facility_name_at_same_address", p0["issues"])
        p2 = [r for r in package["records"] if r["priority"] == "P2"]
        self.assertTrue(any("near_coincident_gsi_references" in r["issues"]
                            for r in p2))
        self.assertFalse(any(r["review"]["checks"]["position_evidence"]
                             for r in package["records"]))

    def test_fail_closed_if_stage7_approval_or_source_changed(self):
        rows, agg = synthetic_stage7()
        changed = copy.deepcopy(agg)
        changed["approved_for_map"] = True
        with self.assertRaises(ValueError):
            make_package(rows, changed, ("P1",))
        changed = copy.deepcopy(agg)
        changed["source_dataset_sha256"] = "not sha"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            make_package(rows, changed, ("P1",))
        changed = copy.deepcopy(rows)
        changed[0]["stage7_review_status"] = "APPROVED"
        with self.assertRaises(ValueError):
            make_package(changed, agg, ("P1",))
        changed = copy.deepcopy(rows)
        changed[0]["independent_site_position_approved"] = "YES"
        with self.assertRaises(ValueError):
            make_package(changed, agg, ("P1",))

    def test_flag_whitelist_and_priority_guards(self):
        rows, agg = synthetic_stage7()
        with self.assertRaisesRegex(ValueError, "Invalid priority"):
            make_package(rows, agg, ("P3",))
        with self.assertRaisesRegex(ValueError, "Invalid priority"):
            make_package(rows, agg, ("P1", "P1"))
        changed = copy.deepcopy(rows)
        changed[0]["stage6_risk_flags"] = "safe_for_flood"
        with self.assertRaisesRegex(ValueError, "risk flags"):
            make_package(changed, agg, ("P0", "P1", "P2"))

    def test_stable_opaque_identifiers_not_private_record_ids(self):
        rows, agg = synthetic_stage7()
        a = make_package(rows, agg, ("P0", "P1", "P2"))
        b = make_package(rows, agg, ("P0", "P1", "P2"))
        self.assertEqual([r["id"] for r in a["records"]],
                         [r["id"] for r in b["records"]])
        self.assertEqual(len(set(r["id"] for r in a["records"])),
                         len(a["records"]))
        private_ids = {r["pilot_record_id"] for r in rows}
        self.assertTrue(all(r["id"] not in private_ids for r in a["records"]))


if __name__ == "__main__":
    unittest.main()
