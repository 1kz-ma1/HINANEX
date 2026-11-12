"""Synthetic only: no real Nagoya source, provider access, or location disclosure."""
import copy
import json
import unittest
from unittest.mock import patch

from diagnose_nagoya_address_mismatch import (
    check_snapshot, comparable_response, diagnose, triage_address_mismatch, safe_failure_code,
)
from geocode_nagoya_pilot import classify, digest, prepare
from report_nagoya_geocoding_pilot import audit


WARD = "千種区"
PREFIX = "愛知県名古屋市千種区"


def provider(query, matched, unmatched=None):
    return {
        "type": "FeatureCollection",
        "query": {"address": query},
        "result_info": {
            "count": 1, "limit": 2,
            "api_version": "synthetic-3.0", "db_version": "synthetic-db",
            "enabled_category": "all", "enabled_pref": "23",
            "duration_ms": 0.9,
        },
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [136.93, 35.16]},
            "properties": {
                "structured_address": {
                    "pref": "愛知県", "city": "名古屋市", "ward": WARD,
                },
                "matched_address": matched,
                "unmatched_address": [] if unmatched is None else unmatched,
                "coordinates_level": "rsdtdsp_rsdt",
            },
        }],
    }


def fixtures():
    dataset = {"records": [
        {"id": "synthetic-a", "name": "架空施設A", "address": "試験町3-2-5",
         "administrative_area": WARD, "latitude": None, "longitude": None},
        {"id": "synthetic-b", "name": "架空施設B", "address": "試験町3-2-6",
         "administrative_area": WARD, "latitude": None, "longitude": None},
        {"id": "synthetic-c", "name": "架空施設C", "address": "試験町3-2-7",
         "administrative_area": WARD, "latitude": None, "longitude": None},
    ]}
    sha = "synthetic-dataset-sha"
    manifest = prepare(dataset, sha)
    matches = [
        PREFIX + "試験町3-2",
        PREFIX + "試験町3-2-9",
        PREFIX + "試験町3-2-7",
    ]
    results = []
    payloads = []
    for row, matched in zip(manifest["selected"], matches):
        payload = provider(row["query_address"], matched)
        classification = classify(payload, row["query_address"], row["ward"])
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        results.append({
            **row, **classification, "provider_response_sha256": digest(raw),
        })
        payloads.append((payload, raw))
    resolution = {
        "pilot_version": 1, "source_dataset_sha256": sha,
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": "synthetic-3.0", "provider_db_version": "synthetic-db",
        "statuses": {"UNRESOLVED": 2, "UNVERIFIED_CANDIDATE": 1},
        "count": 3, "results": results,
        "approved_for_map": False, "data_promotion_authorized": False,
    }
    summary, _ = audit(manifest, resolution)
    return dataset, sha, manifest, resolution, summary, payloads


def response_stream(payloads):
    def two_replays(payload, raw):
        second = copy.deepcopy(payload)
        second["result_info"]["duration_ms"] = 4.2
        second_raw = json.dumps(second, ensure_ascii=False).encode("utf-8")
        return [(payload, raw), (second, second_raw)]

    return [
        ({"status": "ok"}, b'{"status":"ok"}'),
        ({
            "name": "abrg", "version": "synthetic-3.0",
            "db_version": "synthetic-db",
            "enabled_pref": "23", "enabled_category": "all",
        }, b'{}'),
        *two_replays(*payloads[0]),
        *two_replays(*payloads[1]),
    ]


class AddressMismatchDiagnosticTests(unittest.TestCase):
    def test_conservative_string_categories(self):
        query = PREFIX + "試験町3-2-5"
        examples = {
            PREFIX + "試験町3-2": "source_suffix_not_matched",
            PREFIX + "試験町3-2-5-1": "provider_has_extra_suffix",
            PREFIX + "試験町3-2-6": "same_text_stem_number_difference",
            PREFIX + "別町3-2-5": "town_or_other_text_difference",
        }
        for matched, expected in examples.items():
            with self.subTest(matched=matched):
                self.assertEqual(
                    triage_address_mismatch(query, matched, WARD), expected,
                )
        with self.assertRaises(ValueError):
            triage_address_mismatch(query, PREFIX + "試験町3-2-5", WARD)
        with self.assertRaises(ValueError):
            triage_address_mismatch(query, "愛知県名古屋市中区試験町3-2", WARD)

    def test_safe_error_codes_do_not_leak_provider_or_address_text(self):
        self.assertEqual(
            safe_failure_code(ValueError("ABR response changed since the original pilot")),
            "ABR_RESPONSE_HASH_CHANGED",
        )
        self.assertEqual(
            safe_failure_code(ValueError("unexpected source address: confidential-location")),
            "VALUEERROR",
        )
        self.assertEqual(
            safe_failure_code(OSError("http://127.0.0.1/private-address")),
            "OSERROR",
        )

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_aggregate_only_unchanged_candidate_statuses(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        mock_fetch.side_effect = response_stream(payloads)
        result = diagnose(
            manifest, resolution, summary, dataset, sha, "http://127.0.0.1:3000",
        )
        self.assertEqual(result["diagnosed_count"], 2)
        self.assertEqual(result["categories"]["source_suffix_not_matched"], 1)
        self.assertEqual(result["categories"]["same_text_stem_number_difference"], 1)
        self.assertEqual(sum(result["categories"].values()), 2)
        self.assertEqual(result["replay_nonvolatile_semantics_agreed_count"], 2)
        self.assertEqual(result["original_raw_response_hash_changed_count"], 0)
        self.assertFalse(result["historical_semantic_equivalence_proven_for_changed_hashes"])
        self.assertFalse(result["approved_for_map"])
        self.assertFalse(result["data_promotion_authorized"])
        self.assertFalse(result["site_accuracy_independently_verified"])
        self.assertEqual(mock_fetch.call_count, 6)
        rendered = json.dumps(result, ensure_ascii=False)
        for forbidden in (
            "架空施設", "試験町", "136.93", "35.16", "synthetic-a",
            "query_address", "matched_address", "record_id",
        ):
            self.assertNotIn(forbidden, rendered)

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_stale_selection_rejected_before_network(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, _ = fixtures()
        tampered = copy.deepcopy(manifest)
        tampered["selected"][0]["source_address"] = "書換町1"
        with self.assertRaises(ValueError):
            diagnose(tampered, resolution, summary, dataset, sha,
                     "http://127.0.0.1:3000")
        mock_fetch.assert_not_called()

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_wrong_summary_rejected_before_network(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, _ = fixtures()
        changed = {**summary, "reasons": {"different_street_or_house_number": 100}}
        with self.assertRaises(ValueError):
            diagnose(manifest, resolution, changed, dataset, sha,
                     "http://127.0.0.1:3000")
        mock_fetch.assert_not_called()

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_changed_provider_version_rejected_before_any_address(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        response = response_stream(payloads)
        response[1][0]["db_version"] = "wrong"
        mock_fetch.side_effect = response
        with self.assertRaises(ValueError):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "http://127.0.0.1:3000")
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_historical_hash_changed_but_live_double_replay_stable(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        responses = response_stream(payloads)
        first_live = copy.deepcopy(payloads[0][0])
        first_live["result_info"]["duration_ms"] = 2.2
        second_live = copy.deepcopy(payloads[0][0])
        second_live["result_info"]["duration_ms"] = 7.4
        responses[2] = (first_live, json.dumps(first_live, ensure_ascii=False).encode())
        responses[3] = (second_live, json.dumps(second_live, ensure_ascii=False).encode())
        mock_fetch.side_effect = responses
        result = diagnose(manifest, resolution, summary, dataset, sha,
                          "http://127.0.0.1:3000")
        self.assertEqual(result["original_raw_response_hash_changed_count"], 1)
        self.assertEqual(result["replay_nonvolatile_semantics_agreed_count"], 2)
        self.assertFalse(result["historical_semantic_equivalence_proven_for_changed_hashes"])

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_nonvolatile_replay_drift_rejected(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        responses = response_stream(payloads)
        shifted = copy.deepcopy(payloads[0][0])
        shifted["features"][0]["properties"]["matched_address"] = PREFIX + "試験町3-2-8"
        responses[3] = (shifted, json.dumps(shifted, ensure_ascii=False).encode())
        mock_fetch.side_effect = responses
        with self.assertRaisesRegex(ValueError, "ABR replay semantic drift"):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "http://127.0.0.1:3000")

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_invalid_response_metadata_rejected(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        responses = response_stream(payloads)
        altered = copy.deepcopy(payloads[0][0])
        altered["result_info"]["enabled_pref"] = "13"
        responses[2] = (altered, json.dumps(altered, ensure_ascii=False).encode())
        mock_fetch.side_effect = responses
        with self.assertRaisesRegex(ValueError, "ABR replay metadata invalid"):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "http://127.0.0.1:3000")

    def test_comparable_response_ignores_only_duration(self):
        payload = provider(PREFIX + "試験町3-2-5", PREFIX + "試験町3-2")
        version = {"version": "synthetic-3.0", "db_version": "synthetic-db"}
        changed_duration = copy.deepcopy(payload)
        changed_duration["result_info"]["duration_ms"] = 100.1
        self.assertEqual(comparable_response(payload, version),
                         comparable_response(changed_duration, version))
        changed_score = copy.deepcopy(payload)
        changed_score["features"][0]["properties"]["score"] = 0.99
        self.assertNotEqual(comparable_response(payload, version),
                            comparable_response(changed_score, version))
        changed_position = copy.deepcopy(payload)
        changed_position["features"][0]["geometry"]["coordinates"][0] += 0.0001
        self.assertNotEqual(comparable_response(payload, version),
                            comparable_response(changed_position, version))

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_external_server_never_called(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, _ = fixtures()
        with self.assertRaises(ValueError):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "https://api.external.example.com")
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
