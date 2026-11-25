"""Synthetic C-only tests for claimed GSI skhb02 capture manifests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest

from test_verify_gsi_skhb02_archive import URL, fixture
from verify_gsi_skhb02_capture_chain import verify_local_capture_chain

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


def manifest_for(raw, a):
    return {
        "capture_kind": "A_GSI_SKHB02_UNREVIEWED",
        "official_tile_url_requested": URL,
        "source_host": "cyberjapandata.gsi.go.jp",
        "captured_at_utc": (NOW-timedelta(hours=1)).isoformat(),
        "raw_sha256": a["source_sha256"],
        "raw_byte_count": len(raw),
        "source_tile": {"z": 10, "x": 909, "y": 403},
        "feature_count_tile_only": a["source_feature_count"],
        "http_status_observed": 200,
        "response_final_url_observed": URL,
        "content_type_observed": "application/geo+json",
        "etag_observed": '"synthetic"',
        "last_modified_observed": "Mon, 26 Oct 2026 01:00:00 GMT",
        "official_municipal_publication_date_verified": None,
        "official_dataset_update_date_verified": None,
        "response_headers_are_not_publication_dates": True,
        "independent_https_origin_replay_passed": False,
        "independent_c_approved": False,
        "human_approved": False,
        "publishable": False,
    }


class CaptureChainTests(unittest.TestCase):
    def verify(self, raw=None, a=None, capture=None, **kw):
        if raw is None:
            raw, a0 = fixture()
            if a is None:
                a = a0
        if capture is None:
            capture = manifest_for(raw, a)
        return verify_local_capture_chain(
            raw, URL, a, capture, checked_at=kw.get("checked_at", NOW)
        )

    def test_matching_claims_remain_local_unapproved(self):
        result = self.verify()
        self.assertEqual(result["status"], "C_LOCAL_CAPTURE_CHAIN_MATCH_UNAPPROVED")
        for key in (
            "acquisition_headers_independently_authenticated",
            "official_https_origin_authenticated",
            "independent_human_approved",
            "municipal_coverage_verified",
            "published_for_disaster_use",
        ):
            self.assertFalse(result[key])
        self.assertEqual(result["approved_safe_destinations"], 0)
        self.assertIn("ACQUISITION_MANIFEST_SELF_REPORTED", result["reason_codes"])

    def test_false_provenance_and_human_acceptance_blocked(self):
        raw, a = fixture()
        original = manifest_for(raw, a)
        for key, value in (
            ("independent_https_origin_replay_passed", True),
            ("human_approved", True),
            ("publishable", True),
            ("independent_c_approved", True),
            ("official_dataset_update_date_verified", "2026-10-26"),
            ("official_municipal_publication_date_verified", "2026-10-26"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                changed = {**original, key: value}
                self.verify(raw, a, changed)

    def test_tampered_hash_url_tile_count_and_status_blocked(self):
        raw, a = fixture()
        original = manifest_for(raw, a)
        for key, value in (
            ("raw_sha256", "b"*64),
            ("official_tile_url_requested", URL.replace("skhb02", "skhb01")),
            ("source_tile", {"z": 10, "x": 909, "y": 404}),
            ("feature_count_tile_only", 0),
            ("http_status_observed", True),
            ("response_final_url_observed", "https://another.example/"),
            ("source_host", "another.example"),
            ("raw_byte_count", 5),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(raw, a, {**original, key: value})

    def test_unrecognized_fields_missing_fields_and_bad_headers(self):
        raw, a = fixture()
        original = manifest_for(raw, a)
        for change in (
            {**original, "officially_approved": True},
            {k: v for k,v in original.items() if k != "raw_sha256"},
            {**original, "etag_observed": "a\nb"},
            {**original, "content_type_observed": 5},
        ):
            with self.subTest(changed=sorted(change)), self.assertRaises(ValueError):
                self.verify(raw, a, change)

    def test_invalid_time_future_no_zone_or_bad_clock(self):
        raw, a = fixture()
        m = manifest_for(raw, a)
        for when in ("tomorrow", "2026-10-26T12:00:00", "2026-11-01T00:00:00+00:00"):
            with self.subTest(when=when), self.assertRaises(ValueError):
                self.verify(raw, a, {**m, "captured_at_utc": when})
        with self.assertRaises(ValueError):
            self.verify(raw, a, m, checked_at=datetime(2026, 10, 26))

    def test_raw_byte_mutation_does_not_match_a_or_manifest(self):
        raw, a = fixture()
        m = manifest_for(raw, a)
        with self.assertRaises(ValueError):
            self.verify(raw + b"\n", a, m)

    def test_empty_tile_never_implies_absence_in_municipality(self):
        raw, a = fixture([])
        result = self.verify(raw, a, manifest_for(raw, a))
        self.assertEqual(result["status"], "C_EMPTY_TILE_COVERAGE_UNKNOWN")
        self.assertFalse(result["municipal_coverage_verified"])
        self.assertFalse(result["published_for_disaster_use"])
        self.assertEqual(result["approved_safe_destinations"], 0)


if __name__ == "__main__":
    unittest.main()
