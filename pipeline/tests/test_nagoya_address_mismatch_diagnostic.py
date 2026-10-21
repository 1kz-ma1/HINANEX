"""Synthetic only: no real Nagoya source, provider access, or location disclosure."""
import copy
import json
import unittest
from unittest.mock import patch

from diagnose_nagoya_address_mismatch import (
    check_snapshot, diagnose, triage_address_mismatch,
)
from geocode_nagoya_pilot import classify, digest, prepare
from report_nagoya_geocoding_pilot import audit


WARD = "千種区"
PREFIX = "愛知県名古屋市千種区"


def provider(query, matched, unmatched=None):
    return {
        "type": "FeatureCollection",
        "query": {"address": query},
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
    return [
        ({"status": "ok"}, b'{"status":"ok"}'),
        ({
            "name": "abrg", "version": "synthetic-3.0",
            "db_version": "synthetic-db",
            "enabled_pref": "23", "enabled_category": "all",
        }, b'{}'),
        *payloads[:2],
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
        self.assertFalse(result["approved_for_map"])
        self.assertFalse(result["data_promotion_authorized"])
        self.assertFalse(result["site_accuracy_independently_verified"])
        self.assertEqual(mock_fetch.call_count, 4)
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
    def test_changed_response_hash_rejected(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, payloads = fixtures()
        mock_fetch.side_effect = response_stream(payloads[:1]) + [
            (payloads[1][0], b'{"different":"response"}'),
        ]
        with self.assertRaises(ValueError):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "http://127.0.0.1:3000")

    @patch("diagnose_nagoya_address_mismatch.fetch_json")
    def test_external_server_never_called(self, mock_fetch):
        dataset, sha, manifest, resolution, summary, _ = fixtures()
        with self.assertRaises(ValueError):
            diagnose(manifest, resolution, summary, dataset, sha,
                     "https://api.external.example.com")
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
