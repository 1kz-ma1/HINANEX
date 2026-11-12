"""Synthetic-only tests of kanji-chome normalization and conservative Stage 3."""
import copy
import json
import unittest
from unittest.mock import patch

from diagnose_nagoya_kanji_chome_stage3 import (
    canonical_chome_address, comparison_outcome, diagnose_stage3, validate_stage2,
)
from diagnose_nagoya_text_difference_stage2 import diagnose_stage2
from geocode_nagoya_pilot import classify, digest, prepare
from report_nagoya_geocoding_pilot import audit
from test_nagoya_address_mismatch_diagnostic import (
    PREFIX, WARD, provider, response_stream,
)
from test_nagoya_text_difference_stage2 import fixtures as stage2_fixtures


def fixtures():
    data, sha, manifest, resolution, _, stage1, payloads = stage2_fixtures()
    data["records"][0]["address"] = "試験町1丁目2番5号"
    manifest = prepare(data, sha)
    first = provider(manifest["selected"][0]["query_address"],
                     PREFIX + "試験町一丁目2番5号")
    first_raw = json.dumps(first, ensure_ascii=False).encode("utf-8")
    payloads[0] = first, first_raw
    original = resolution["results"][0]
    resolution["results"][0] = {
        **manifest["selected"][0],
        **classify(first, manifest["selected"][0]["query_address"], WARD),
        "provider_response_sha256": digest(first_raw),
    }
    # The other synthetic records retain their initial identity and statuses.
    summary, _ = audit(manifest, resolution)
    with patch("diagnose_nagoya_text_difference_stage2.fetch_json",
               side_effect=response_stream(payloads)):
        stage2 = diagnose_stage2(
            manifest, resolution, summary, stage1, data, sha, "http://127.0.0.1:3000",
        )
    return data, sha, manifest, resolution, summary, stage1, stage2, payloads


class KanjiChomeStage3Tests(unittest.TestCase):
    def test_strict_kanji_chome_values_and_unknown_tokens(self):
        cases = {
            "一丁目": "1",
            "九丁目": "9",
            "十丁目": "10",
            "十一丁目": "11",
            "二十一丁目": "21",
            "九十九丁目": "99",
            "百丁目": "100",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                key, number, unknown = canonical_chome_address(
                    PREFIX + "架空町" + original,
                )
                self.assertEqual(key, PREFIX + "架空町" + expected)
                self.assertEqual((number, unknown), (1, 0))
        for invalid in ("〇丁目", "零丁目", "一百丁目", "十十丁目", "一一丁目"):
            with self.subTest(invalid=invalid):
                key, number, unknown = canonical_chome_address(invalid)
                self.assertEqual((number, unknown), (0, 1))
        self.assertEqual(canonical_chome_address("試験町三番5号")[1:], (0, 0))

    def test_normalized_relation_never_fills_in_missing_house_number(self):
        a = PREFIX + "試験町1丁目2番5号"
        equivalent = PREFIX + "試験町一丁目2番5号"
        prefix_only = PREFIX + "試験町一丁目2番"
        wrong_number = PREFIX + "試験町一丁目2番6号"
        wrong_town = PREFIX + "別町一丁目2番5号"
        self.assertEqual(comparison_outcome(a, equivalent, WARD)[0],
                         "exact_after_kanji_chome_only")
        self.assertEqual(comparison_outcome(a, prefix_only, WARD)[0],
                         "source_suffix_unmatched_after_kanji_chome")
        self.assertEqual(comparison_outcome(a, wrong_number, WARD)[0],
                         "still_different_after_kanji_chome")
        self.assertEqual(comparison_outcome(a, wrong_town, WARD)[0],
                         "still_different_after_kanji_chome")
        self.assertEqual(comparison_outcome(a, PREFIX + "試験町十十丁目2-5", WARD)[0],
                         "unrecognized_kanji_chome")
        with self.assertRaises(ValueError):
            comparison_outcome(a, PREFIX + "試験町1-2-5", WARD)

    @patch("diagnose_nagoya_kanji_chome_stage3.fetch_json")
    def test_complete_aggregate_without_sensitive_data(self, mock_fetch):
        ds, sha, manifest, resolution, summary, stage1, stage2, payloads = fixtures()
        mock_fetch.side_effect = response_stream(payloads)
        result = diagnose_stage3(
            manifest, resolution, summary, stage1, stage2, ds,
            sha, "http://127.0.0.1:3000",
        )
        self.assertEqual(result["original_mismatches_rechecked"], 2)
        self.assertEqual(result["stage2_target_count"], 1)
        self.assertEqual(result["comparison_outcomes"]["exact_after_kanji_chome_only"], 1)
        self.assertEqual(result["exact_normalized_matches_without_unmatched_field_count"], 1)
        self.assertEqual(sum(result["comparison_outcomes"].values()), 1)
        self.assertEqual(mock_fetch.call_count, 6)
        self.assertFalse(result["approved_for_map"])
        self.assertFalse(result["data_promotion_authorized"])
        self.assertFalse(result["site_accuracy_independently_verified"])
        self.assertEqual(result["official_facility_positions_accepted"], 0)
        rendered = json.dumps(result, ensure_ascii=False)
        for excluded in ("試験町", "一丁目", "架空施設", "synthetic-a",
                         "136.93", "35.16", "query_address", "matched_address"):
            self.assertNotIn(excluded, rendered)

    @patch("diagnose_nagoya_kanji_chome_stage3.fetch_json")
    def test_stage2_counts_tampered_fail_before_network(self, mock_fetch):
        ds, sha, manifest, resolution, summary, stage1, stage2, _ = fixtures()
        for mutation in (
            {"stage2_target_count": 2},
            {"approved_for_map": True},
            {"provider_version": "different"},
            {"numeric_observations": {"both_have_numbers_text_stem_diff": -1}},
        ):
            with self.subTest(mutation=mutation):
                tampered = {**stage2, **mutation}
                with self.assertRaises(ValueError):
                    diagnose_stage3(manifest, resolution, summary, stage1, tampered,
                                    ds, sha, "http://127.0.0.1:3000")
        mock_fetch.assert_not_called()

    @patch("diagnose_nagoya_kanji_chome_stage3.fetch_json")
    def test_replay_semantic_drift_aborts(self, mock_fetch):
        ds, sha, manifest, resolution, summary, stage1, stage2, payloads = fixtures()
        replay = response_stream(payloads)
        mismatch = copy.deepcopy(payloads[0][0])
        mismatch["features"][0]["properties"]["matched_address"] = PREFIX + "試験町一丁目2番6号"
        replay[3] = mismatch, json.dumps(mismatch, ensure_ascii=False).encode()
        mock_fetch.side_effect = replay
        with self.assertRaisesRegex(ValueError, "ABR replay semantic drift"):
            diagnose_stage3(manifest, resolution, summary, stage1, stage2,
                            ds, sha, "http://127.0.0.1:3000")

    @patch("diagnose_nagoya_kanji_chome_stage3.fetch_json")
    def test_nonlocal_server_rejected_without_network(self, mock_fetch):
        ds, sha, manifest, resolution, summary, stage1, stage2, _ = fixtures()
        with self.assertRaises(ValueError):
            diagnose_stage3(manifest, resolution, summary, stage1, stage2,
                            ds, sha, "https://external.example")
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
