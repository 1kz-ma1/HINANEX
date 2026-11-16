"""Synthetic-only R0 anchor-to-tile planning regressions; no source fetch."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.hinanex.gsi_r0_anchor_plan import (
    AnchorPlanInvalid, anchor_tile, build_candidate, dms_degrees,
    _output_path,
)
from src.hinanex.gsi_r0_pilot_batch import _validate_pilots

REFERENCE = "https://www.pref.niigata.lg.jp/uploaded/attachment/389261.pdf"


def candidate(**overrides):
    kwargs = {
        "a_x": 909, "a_y": 403,
        "b_longitude_dms": "139:01:24",
        "b_latitude_dms": "37:54:14",
        "b_reference_url": REFERENCE,
    }
    kwargs.update(overrides)
    return build_candidate(**kwargs)


class TestR0AnchorPlan(unittest.TestCase):
    def test_officially_cited_niigata_geographic_anchor_yields_tile_907_395(self):
        plan, evidence = candidate()
        self.assertEqual(_validate_pilots(plan)[1]["tile"],
                         {"z": 10, "x": 907, "y": 395})
        self.assertEqual(plan["pilots"][0]["tile"],
                         {"z": 10, "x": 909, "y": 403})
        self.assertEqual(evidence["status"],
                         "R0_CANDIDATE_TILE_ONLY_SOURCES_NOT_ACQUIRED")
        self.assertFalse(evidence["reference_url_content_verified_by_tool"])
        self.assertEqual(evidence["reference_is_emergency_shelter"],"NOT_EVALUATED")
        self.assertFalse(evidence["official_municipal_boundary_verified"])
        self.assertFalse(evidence["geographic_distance_verified"])

    def test_input_plan_contains_no_provenance_that_r0_contract_would_reject(self):
        plan, evidence = candidate()
        self.assertEqual(set(plan), {"schema", "pilots"})
        self.assertEqual(len(plan["pilots"]), 2)
        self.assertNotIn("reference_url", str(plan))
        self.assertEqual(evidence["reference_url_claimed"], REFERENCE)
        self.assertEqual(_validate_pilots(plan)[0]["slot"], "A")

    def test_hazard_availability_and_publication_are_not_granted(self):
        _, evidence = candidate()
        self.assertEqual(evidence["gsi_skhb01_source_available"],"NOT_TESTED")
        self.assertEqual(evidence["gsi_skhb02_source_available"],"NOT_TESTED")
        self.assertEqual(evidence["c_independent_acceptance"],"NOT_GRANTED")
        self.assertEqual(evidence["publication_approval"],"NOT_GRANTED")
        self.assertEqual(evidence["human_review"],"DEFERRED_TO_HUMAN_BATCH_REVIEW")

    def test_dms_seconds_mathematically_convert_not_guess(self):
        self.assertAlmostEqual(dms_degrees("139:01:24",longitude=True),
                               139 + 1/60 + 24/3600, places=11)
        self.assertAlmostEqual(dms_degrees("37:54:14",longitude=False),
                               37 + 54/60 + 14/3600, places=11)

    def test_false_dms_strings_and_unbounded_values_rejected(self):
        for value in (
            "139", "139.023333", "139:1", "-139:01:24",
            "139:60:00", "139:00:60", "181:00:00", "139:01:24 extra",
            "99:99:99", None, True,
        ):
            with self.subTest(value=value), self.assertRaises(AnchorPlanInvalid):
                dms_degrees(value,longitude=True)

    def test_lat_outside_mercator_projection_is_rejected(self):
        for value in ("90:00:00","85:04:00","85:59:59"):
            with self.subTest(value=value), self.assertRaises(AnchorPlanInvalid):
                anchor_tile(east_longitude_dms="139:01:24",
                            north_latitude_dms=value)

    def test_near_equator_positive_anchor_has_expected_tile(self):
        tile=anchor_tile(east_longitude_dms="0:00:00",
                         north_latitude_dms="0:00:00")
        self.assertEqual(tile,{"z":10,"x":512,"y":512})

    def test_invalid_a_tile_rejected_not_auto_corrected(self):
        for a in (-1,1024,909.0,True,"909",None):
            with self.subTest(a=a), self.assertRaises(AnchorPlanInvalid):
                candidate(a_x=a)
            with self.subTest(a=a), self.assertRaises(AnchorPlanInvalid):
                candidate(a_y=a)

    def test_duplicate_a_b_tile_is_not_two_pilots(self):
        with self.assertRaisesRegex(ValueError,"DISTINCT"):
            candidate(a_x=907,a_y=395)

    def test_https_official_link_must_be_explicit_not_auto_fetched(self):
        for url in (
            "", "https://example.invalid/source",
            "http://www.pref.niigata.lg.jp/doc.pdf",
            "https://www.pref.niigata.lg.jp.evil.invalid/x",
            "https://user:pass@www.pref.niigata.lg.jp/doc.pdf",
            "https://www.pref.niigata.lg.jp/doc.pdf?foo=bar",
            "https://www.pref.niigata.lg.jp/doc.pdf#page=2",
            "https://www.pref.niigata.lg.jp/",
            "https://www.pref.niigata.lg.jp:8443/doc.pdf",
            None,
        ):
            with self.subTest(url=url), self.assertRaises(AnchorPlanInvalid):
                candidate(b_reference_url=url)

    def test_anchor_reference_claim_does_not_verify_official_license(self):
        _, evidence = candidate(b_reference_url="https://city.example.lg.jp/source")
        self.assertFalse(evidence["reference_url_content_verified_by_tool"])
        self.assertEqual(evidence["reference_is_emergency_shelter"],"NOT_EVALUATED")

    def test_plan_output_must_be_absolute_external_and_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            good=folder/"pilot-plan.json"
            self.assertEqual(_output_path(good),good.resolve(strict=False))
            good.write_text("keep")
            with self.assertRaises(AnchorPlanInvalid):
                _output_path(good)
            self.assertEqual(good.read_text(),"keep")
            for bad in (Path("pilot-plan.json"), folder/"missing",
                        folder/"wrong.txt"):
                with self.subTest(bad=bad),self.assertRaises(AnchorPlanInvalid):
                    _output_path(bad)

    def test_output_inside_repository_is_refused(self):
        from src.hinanex import gsi_r0_anchor_plan
        root=Path(gsi_r0_anchor_plan.__file__).resolve().parents[3]
        with self.assertRaisesRegex(AnchorPlanInvalid,"OUTSIDE_REPOSITORY"):
            _output_path(root/"pilot-plan.json")

    def test_no_network_in_build_candidate_or_anchor_tile(self):
        # Pure functions take explicit values and cannot claim tile availability.
        a,b = candidate()
        self.assertEqual(b["gsi_skhb01_source_available"],"NOT_TESTED")
        self.assertEqual(b["gsi_skhb02_source_available"],"NOT_TESTED")
        self.assertEqual([item["slot"] for item in a["pilots"]],["A","B"])

    def test_not_an_evacuating_facility_location_or_citywide_coverage(self):
        _, e = candidate()
        self.assertNotIn("facility_id",e)
        self.assertNotIn("shelter_name",e)
        self.assertNotIn("recommended_routes",e)
        self.assertFalse(e["official_municipal_boundary_verified"])
        self.assertEqual(e["reference_class"],
                         "MANUAL_GEOGRAPHIC_REFERENCE_NOT_SITE_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
