"""Offline, synthetic-only vicinity hints. Never certifies site or navigation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from test_inspect_osm_four_site_evidence import fixture

MODULE = Path(__file__).resolve().parents[1] / "tools" / "triage_osm_four_site_raw_vicinity.py"
spec = importlib.util.spec_from_file_location("a_osm_vicinity_test_target", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def prepare(folder, elements):
    digest, _ = fixture(folder, elements=elements)
    return digest


class VicinityTests(unittest.TestCase):
    def triage(self, elements):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = prepare(folder, elements)
            return mod.triage_vicinity(folder, expected_gsi_sha=digest)

    def test_nearby_node_no_identity_or_navigation(self):
        r = self.triage([{"type": "node", "id": 1, "lat": 35.725904,
                          "lon": 139.899193, "tags": {"entrance": "main", "access": "yes"}}])
        q = r["per_reference_review_hints_not_matches"][0]
        self.assertEqual(q["observed_vicinity_element_count"], 1)
        row = q["nonexclusive_unassigned_elements_needing_review"][0]
        self.assertEqual(row["closest_observed_point_distance_m_approx"], 0)
        self.assertEqual(row["osm_element_url_unreviewed"], "https://www.openstreetmap.org/node/1")
        self.assertIsNone(row["associated_gsi_feature_index"])
        self.assertFalse(row["entrance_verified"])
        self.assertFalse(row["navigation_allowed"])
        self.assertFalse(r["may_publish_or_route"])
        self.assertFalse(r["human_c_approved"])

    def test_four_separate_queues_in_fixed_order(self):
        els = [{"type": "node", "id": i + 1, "lat": loc[1], "lon": loc[0]}
               for i, (_, loc) in enumerate(mod.TARGETS.values())]
        r = self.triage(els)
        self.assertEqual([q["gsi_feature_index_reference_only"]
                          for q in r["per_reference_review_hints_not_matches"]], [571,639,682,707])
        self.assertEqual([q["observed_vicinity_element_count"]
                          for q in r["per_reference_review_hints_not_matches"]], [1,1,1,1])

    def test_way_vertices_and_relation_member_geometry(self):
        r = self.triage([
            {"type": "way", "id": 10, "geometry": [{"lat": 35.725904, "lon": 139.899193}]},
            {"type": "relation", "id": 11, "members": [
                {"type": "way", "ref": 22, "geometry": [{"lat": 35.725904, "lon": 139.899193}]}]},
        ])
        self.assertEqual(r["per_reference_review_hints_not_matches"][0]["observed_vicinity_element_count"], 2)

    def test_same_raw_way_may_appear_in_multiple_review_queues_without_assignment(self):
        vertices = [{"lat": coord[1], "lon": coord[0]} for _, coord in mod.TARGETS.values()]
        r = self.triage([{"type": "way", "id": 81, "geometry": vertices}])
        self.assertEqual([q["observed_vicinity_element_count"]
                          for q in r["per_reference_review_hints_not_matches"]], [1, 1, 1, 1])
        for q in r["per_reference_review_hints_not_matches"]:
            self.assertIsNone(q["nonexclusive_unassigned_elements_needing_review"][0][
                "associated_gsi_feature_index"])

    def test_empty_source_means_no_claim_about_absence(self):
        r = self.triage([])
        self.assertEqual(r["source_element_count"], 0)
        self.assertTrue(r["source_has_no_exhaustive_facility_coverage_claim"])
        self.assertFalse(r["navigation_allowed"])

    def test_missing_geometry_kept_in_unresolved(self):
        r = self.triage([{"type": "way", "id": 3}])
        self.assertEqual(len(r["no_observed_coordinates_needing_review"]), 1)
        self.assertEqual(r["no_observed_coordinates_needing_review"][0]["reason"],
                         "NO_OBSERVED_COORDINATES_NOT_EXCLUSION")

    def test_far_vertices_not_conclusive_exclusion(self):
        r = self.triage([{"type": "way", "id": 3,
                          "geometry": [{"lat": 35.6, "lon": 139.5}]}])
        self.assertEqual(len(r["not_near_any_observed_vertex_needing_review"]), 1)
        self.assertTrue(r["source_has_no_exhaustive_facility_coverage_claim"])

    def test_bad_or_partial_coordinate_fail_closed(self):
        for obj in ({"lat": float('nan'), "lon": 139.9},
                    {"lat": 35.7}, {"lat": True, "lon": 139.9},
                    {"lat": -95, "lon": 139.9}):
            with self.subTest(obj=obj), self.assertRaises(mod.EvidenceBlocked):
                self.triage([{"type":"node", "id": 15, **obj}])

    def test_malformed_nested_geometry_fail_closed(self):
        for obj in ({"type": "way", "id": 2, "geometry": [2]},
                    {"type": "relation", "id": 2, "members": ["invalid"]},
                    {"type": "way", "id": 2, "geometry": "coordinates"}):
            with self.subTest(obj=obj), self.assertRaises(mod.EvidenceBlocked):
                self.triage([obj])

    def test_tampered_manifest_or_source_fail_before_triage(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            digest = prepare(folder, [{"type": "node", "id": 1, "lat": 35.7259, "lon": 139.8992}])
            (folder / "osm-overpass-original.json").write_bytes(b'{"elements":[]}')
            with self.assertRaisesRegex(mod.EvidenceBlocked, "MANIFEST_SHA_MISMATCH"):
                mod.triage_vicinity(folder, expected_gsi_sha=digest)

    def test_synthetic_override_not_exposed_by_cli(self):
        import inspect
        self.assertNotIn("expected-gsi-sha", inspect.getsource(mod.main))
        self.assertEqual(mod.GSI_SHA256, "cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84")


if __name__ == "__main__":
    unittest.main()
