"""Stage-2 only runs with synthesized records and mocked localhost ABR replies."""
import copy
import json
import unittest
from unittest.mock import patch

from diagnose_nagoya_text_difference_stage2 import (
    diagnose_stage2, numeric_observation, validate_stage1,
)
from geocode_nagoya_pilot import classify, digest
from report_nagoya_geocoding_pilot import audit
from test_nagoya_address_mismatch_diagnostic import (
    PREFIX, WARD, fixtures as base_fixtures, provider, response_stream,
)


def fixtures():
    dataset, sha, manifest, resolution, _, payloads = base_fixtures()
    matched = PREFIX + "別町3-2-5"
    query = manifest["selected"][0]["query_address"]
    changed = provider(query, matched)
    raw = json.dumps(changed, ensure_ascii=False).encode("utf-8")
    payloads[0] = (changed, raw)
    resolution["results"][0] = {
        **resolution["results"][0],
        **classify(changed, query, WARD),
        "provider_response_sha256": digest(raw),
    }
    summary, _ = audit(manifest, resolution)
    stage1 = {
        "report_kind": "NAGOYA_CURRENT_REPLAY_MISMATCH_TRIAGE_NOT_HISTORICAL_PROOF",
        "source_dataset_sha256": sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": "synthetic-3.0",
        "provider_db_version": "synthetic-db",
        "diagnosed_count": 2,
        "replay_nonvolatile_semantics_agreed_count": 2,
        "original_unresolved_reason": "different_street_or_house_number",
        "previous_statuses_unchanged": True,
        "historical_semantic_equivalence_proven_for_changed_hashes": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "site_accuracy_independently_verified": False,
        "categories": {
            "town_or_other_text_difference": 1,
            "source_suffix_not_matched": 0,
            "provider_has_extra_suffix": 0,
            "same_text_stem_number_difference": 1,
        },
    }
    return dataset, sha, manifest, resolution, summary, stage1, payloads


class Stage2SyntheticTests(unittest.TestCase):
    def test_numeric_observations_are_descriptive_not_approvals(self):
        prefix = PREFIX
        examples = (
            ("試験町3-2-5", "別町3-2-5", "both_have_numbers_text_stem_diff", "same"),
            ("試験町3-2-5", "別町3-2-6", "both_have_numbers_text_stem_diff", "different"),
            ("試験町一丁目", "別町5-2", "source_only_has_no_ascii_number", "not_comparable"),
            ("試験町5-2", "別町一丁目", "provider_only_has_no_ascii_number", "not_comparable"),
            ("試験町一丁目", "別町二丁目", "neither_has_ascii_number", "not_comparable"),
        )
        for source, matched, expected_rel, expected_suffix in examples:
            with self.subTest(source=source, matched=matched):
                relation, suffix, _ = numeric_observation(
                    prefix + source, prefix + matched, WARD,
                )
                self.assertEqual((relation, suffix), (expected_rel, expected_suffix))
        with self.assertRaises(ValueError):
            numeric_observation(
                prefix + "試験町3-2-5", prefix + "試験町3-2-9", WARD,
            )

    @patch("diagnose_nagoya_text_difference_stage2.fetch_json")
    def test_aggregate_report_anonymity_and_replay(self, mock_fetch):
        ds, sha, manifest, res, summary, stage1, payloads = fixtures()
        mock_fetch.side_effect = response_stream(payloads)
        report = diagnose_stage2(
            manifest, res, summary, stage1, ds, sha, "http://127.0.0.1:3000",
        )
        self.assertEqual(report["stage2_target_count"], 1)
        self.assertTrue(report["stage1_categories_reproduced"])
        self.assertEqual(report["numeric_observations"]["both_have_numbers_text_stem_diff"], 1)
        self.assertEqual(report["numeric_suffix_observations"]["same"], 1)
        self.assertEqual(report["match_level_counts"]["other_or_missing"], 1)
        self.assertEqual(sum(report["numeric_observations"].values()), 1)
        self.assertEqual(mock_fetch.call_count, 6)
        self.assertFalse(report["approved_for_map"])
        self.assertFalse(report["data_promotion_authorized"])
        rendered = json.dumps(report, ensure_ascii=False)
        for sensitive in ("試験町", "別町", "架空施設", "synthetic-a",
                          "136.93", "35.16", "query_address", "matched_address"):
            self.assertNotIn(sensitive, rendered)

    @patch("diagnose_nagoya_text_difference_stage2.fetch_json")
    def test_bad_stage1_snapshot_blocks_before_network(self, mock_fetch):
        ds, sha, manifest, res, summary, stage1, _ = fixtures()
        for field, value in (
            ("diagnosed_count", 3),
            ("approved_for_map", True),
            ("source_dataset_sha256", "incorrect"),
        ):
            with self.subTest(field=field):
                bad = {**stage1, field: value}
                with self.assertRaises(ValueError):
                    diagnose_stage2(
                        manifest, res, summary, bad, ds, sha,
                        "http://127.0.0.1:3000",
                    )
        mock_fetch.assert_not_called()

    @patch("diagnose_nagoya_text_difference_stage2.fetch_json")
    def test_drift_between_two_replays_blocks_diagnostic(self, mock_fetch):
        ds, sha, manifest, res, summary, stage1, payloads = fixtures()
        replies = response_stream(payloads)
        mutated = copy.deepcopy(payloads[0][0])
        mutated["features"][0]["properties"]["matched_address"] = PREFIX + "別町3-2-6"
        replies[3] = (mutated, json.dumps(mutated, ensure_ascii=False).encode())
        mock_fetch.side_effect = replies
        with self.assertRaisesRegex(ValueError, "ABR replay semantic drift"):
            diagnose_stage2(
                manifest, res, summary, stage1, ds, sha,
                "http://127.0.0.1:3000",
            )

    @patch("diagnose_nagoya_text_difference_stage2.fetch_json")
    def test_stage1_category_drift_fails_closed(self, mock_fetch):
        ds, sha, manifest, res, summary, stage1, payloads = fixtures()
        modified = copy.deepcopy(stage1)
        modified["categories"]["same_text_stem_number_difference"] = 0
        modified["categories"]["source_suffix_not_matched"] = 1
        mock_fetch.side_effect = response_stream(payloads)
        with self.assertRaisesRegex(ValueError, "Stage-1 category drift"):
            diagnose_stage2(
                manifest, res, summary, modified, ds, sha,
                "http://127.0.0.1:3000",
            )

    @patch("diagnose_nagoya_text_difference_stage2.fetch_json")
    def test_external_hosts_rejected_before_network(self, mock_fetch):
        ds, sha, manifest, res, summary, stage1, _ = fixtures()
        with self.assertRaises(ValueError):
            diagnose_stage2(
                manifest, res, summary, stage1, ds, sha,
                "https://public-geocoder.example",
            )
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
