"""Synthetic-only quality screening tests: no genuine addresses, ABR, or geometry."""
import copy
import json
import unittest
from unittest.mock import patch

from diagnose_nagoya_chome_stage4_reference_screen import (
    OUTCOME_KEYS, diagnose_stage4, screen_exact_reference,
)
from diagnose_nagoya_kanji_chome_stage3 import diagnose_stage3
from diagnose_nagoya_text_difference_stage2 import diagnose_stage2
from test_nagoya_kanji_chome_stage3 import fixtures as stage3_fixtures
from test_nagoya_address_mismatch_diagnostic import response_stream


def fixtures(match_level=None, coordinates_level=None, point=(136.95, 35.18)):
    ds, sha, manifest, resolution, summary, stage1, _, payloads = stage3_fixtures()
    # Synthetic feature with controlled independent location; status remains
    # UNRESOLVED in the original pilot regardless of its point.
    result = copy.deepcopy(payloads[0][0])
    props = result["features"][0]["properties"]
    if match_level is not None:
        props["match_level"] = match_level
    if coordinates_level is not None:
        props["coordinates_level"] = coordinates_level
    if point is not None:
        result["features"][0]["geometry"]["coordinates"] = list(point)
    else:
        result["features"][0]["geometry"] = None
    payloads[0] = result, json.dumps(result, ensure_ascii=False).encode()
    with patch("diagnose_nagoya_text_difference_stage2.fetch_json",
               side_effect=response_stream(payloads)):
        stage2 = diagnose_stage2(
            manifest, resolution, summary, stage1,
            ds, sha, "http://127.0.0.1:3000",
        )
    with patch("diagnose_nagoya_kanji_chome_stage3.fetch_json",
               side_effect=response_stream(payloads)):
        stage3 = diagnose_stage3(
            manifest, resolution, summary, stage1, stage2,
            ds, sha, "http://127.0.0.1:3000",
        )
    return (ds, sha, manifest, resolution, summary, stage1,
            stage2, stage3, payloads)


def execute(ensemble, replies=None):
    ds, sha, manifest, resolution, summary, s1, s2, s3, payloads = ensemble
    with patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json",
               side_effect=response_stream(payloads) if replies is None else replies) as mocked:
        result = diagnose_stage4(
            manifest, resolution, summary, s1, s2, s3,
            ds, sha, "http://127.0.0.1:3000",
        )
    return result, mocked.call_count


class Stage4SyntheticTests(unittest.TestCase):
    def test_qualifying_screen_is_not_map_approval(self):
        result, calls = execute(fixtures(match_level="rsdtdsp_rsdt"))
        self.assertEqual(calls, 6)
        self.assertEqual(result["orthographic_text_equal_rechecked"], 1)
        self.assertEqual(result["screen_categories"]["high_resolution_reference_for_independent_review"], 1)
        self.assertEqual(sum(result["screen_categories"].values()), 1)
        self.assertEqual(result["source_suffix_cases_not_promoted"], 0)
        self.assertEqual(result["existing_unverified_candidates_unchanged"], 1)
        self.assertFalse(result["approved_for_map"])
        self.assertFalse(result["data_promotion_authorized"])
        self.assertEqual(result["official_facility_positions_accepted"], 0)
        message = json.dumps(result, ensure_ascii=False)
        for forbidden in ("試験町", "架空施設", "136.95", "35.18",
                          "synthetic-a", "query_address", "matched_address"):
            self.assertNotIn(forbidden, message)

    def test_parcel_match_rejected_even_with_high_resolution_coordinate(self):
        result, _ = execute(fixtures(match_level="parcel",
                                     coordinates_level="rsdtdsp_rsdt"))
        self.assertEqual(result["screen_categories"]["parcel_reference_requires_review"], 1)

    def test_unknown_match_level_not_screened_as_high_quality(self):
        result, _ = execute(fixtures(match_level=None))
        self.assertEqual(result["screen_categories"]["coarse_or_unknown_address_match"], 1)

    def test_coarse_reference_coordinate_is_not_approved(self):
        result, _ = execute(fixtures(match_level="rsdtdsp_rsdt",
                                     coordinates_level="machiaza_detail"))
        self.assertEqual(result["screen_categories"]["coarse_or_unknown_coordinate_reference"], 1)

    def test_missing_geometry_does_not_pass(self):
        result, _ = execute(fixtures(match_level="rsdtdsp_rsdt", point=None))
        self.assertEqual(result["screen_categories"]["invalid_or_missing_point"], 1)

    def test_same_coordinate_as_original_candidate_requires_review(self):
        result, _ = execute(fixtures(match_level="rsdtdsp_rsdt", point=(136.93, 35.16)))
        self.assertEqual(result["screen_categories"]["shared_reference_coordinate_requires_review"], 1)

    def test_unmatched_address_is_conservative(self):
        props = {"unmatched_address": ["synthetic"], "match_level": "rsdtdsp_rsdt",
                 "coordinates_level": "rsdtdsp_rsdt"}
        self.assertEqual(screen_exact_reference(props, (136.95, 35.18), False),
                         "unexpected_unmatched_address")
        props["unmatched_address"] = []
        self.assertEqual(screen_exact_reference(props, (136.95, 35.18), False),
                         "high_resolution_reference_for_independent_review")

    def test_all_screen_categories_declared(self):
        self.assertEqual(len(OUTCOME_KEYS), 7)

    @patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json")
    def test_reject_tampered_stage3_before_network(self, mocked):
        ds, sha, manifest, res, summary, s1, s2, s3, _ = fixtures()
        for change in (
            {"approved_for_map": True},
            {"comparison_outcomes": {"exact_after_kanji_chome_only": 999}},
            {"provider_db_version": "different"},
            {"original_pilot_unchanged": False},
        ):
            bad = {**s3, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                diagnose_stage4(manifest, res, summary, s1, s2, bad, ds, sha,
                                "http://127.0.0.1:3000")
        mocked.assert_not_called()

    @patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json")
    def test_non_local_server_rejected_without_network(self, mocked):
        ds, sha, manifest, res, summary, s1, s2, s3, _ = fixtures()
        with self.assertRaises(ValueError):
            diagnose_stage4(manifest, res, summary, s1, s2, s3, ds, sha,
                            "https://unknown-location.example")
        mocked.assert_not_called()

    def test_double_replay_drift_aborts(self):
        prepared = fixtures(match_level="rsdtdsp_rsdt")
        replies = response_stream(prepared[-1])
        mutated = copy.deepcopy(replies[2][0])
        mutated["features"][0]["properties"]["match_level"] = "parcel"
        replies[3] = mutated, json.dumps(mutated, ensure_ascii=False).encode()
        ds, sha, manifest, res, summary, s1, s2, s3, _ = prepared
        with patch("diagnose_nagoya_chome_stage4_reference_screen.fetch_json",
                   side_effect=replies):
            with self.assertRaisesRegex(ValueError, "ABR replay semantic drift"):
                diagnose_stage4(manifest, res, summary, s1, s2, s3, ds, sha,
                                "http://127.0.0.1:3000")


if __name__ == "__main__":
    unittest.main()
