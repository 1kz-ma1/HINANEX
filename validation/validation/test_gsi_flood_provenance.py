"""Offline unit tests for C's independent HTTPS replay; no live web calls."""
import hashlib
import json
import unittest

from verify_gsi_flood_provenance import verify_https_provenance

URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
RAW = json.dumps({
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [139.9, 35.7]},
        "properties": {"name": "TEST only", "disaster1": 1},
    }],
}).encode("utf-8")
HASH = hashlib.sha256(RAW).hexdigest()


def c_accepted(**changes):
    evidence = {
        "status": "PASS",
        "source_raw_sha256": HASH,
        "hazard_dataset": "GSI_SKHB01_FLOOD",
        "search_context_region_code": "13123",
        "audit_reference": "C-TEST-ONLY",
        "accepted_source_feature_keys": [URL + "#feature_index=0"],
    }
    evidence.update(changes)
    return evidence


class FakeResponse:
    def __init__(self, raw=RAW, status=200, final_url=URL):
        self.raw = raw
        self.status = status
        self.final_url = final_url
        self.headers = {"Content-Type": "application/json", "ETag": '"TEST"'}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def geturl(self):
        return self.final_url

    def read(self, size):
        return self.raw[:size]


def fake_opener(*, raw=RAW, status=200, final_url=URL):
    def open_request(req, timeout=0):
        assert req.full_url == URL
        assert timeout > 0
        return FakeResponse(raw, status, final_url)
    return open_request


class IndependentHttpsReplayTests(unittest.TestCase):
    def test_matching_server_bytes_and_c_manifest_emit_audit_report(self):
        report = verify_https_provenance(RAW, URL, c_accepted(), opener=fake_opener())
        self.assertEqual(report["status"], "MATCH")
        self.assertEqual(report["http_status"], 200)
        self.assertEqual(report["archive_sha256"], HASH)
        self.assertEqual(report["download_sha256"], HASH)
        self.assertEqual(report["feature_count"], 1)
        self.assertEqual(report["c_audit_reference"], "C-TEST-ONLY")
        self.assertIn("tile-wide", report["limitations"][2])
        self.assertNotIn("safe", report)

    def test_modified_server_bytes_are_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "differ"):
            verify_https_provenance(RAW, URL, c_accepted(), opener=fake_opener(raw=RAW + b" "))

    def test_redirect_and_http_failure_are_not_accepted(self):
        for opener in (
            fake_opener(final_url="https://other.example/tile.geojson"),
            fake_opener(status=404),
        ):
            with self.subTest(opener=opener), self.assertRaisesRegex(ValueError, "not 200"):
                verify_https_provenance(RAW, URL, c_accepted(), opener=opener)

    def test_invalid_c_acceptance_or_tampered_raw_fails_before_network(self):
        evidence = [
            c_accepted(status="PENDING"),
            c_accepted(source_raw_sha256="0" * 64),
            c_accepted(accepted_source_feature_keys=[]),
            c_accepted(accepted_source_feature_keys=[URL + "#feature_index=2"]),
            c_accepted(audit_reference=""),
            c_accepted(search_context_region_code="99999"),
        ]
        def forbidden_network(*args, **kwargs):
            raise AssertionError("network called before C acceptance passed")
        for item in evidence:
            with self.subTest(item=item), self.assertRaises(ValueError):
                verify_https_provenance(RAW, URL, item, opener=forbidden_network)
        with self.assertRaises(ValueError):
            verify_https_provenance(RAW + b" ", URL, c_accepted(), opener=forbidden_network)

    def test_untrusted_or_bad_tile_indices_rejected_without_fetch(self):
        for bad in [
            "http://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson",
            "https://evil.example/xyz/skhb01/10/909/403.geojson",
            "https://cyberjapandata.gsi.go.jp/xyz/skhb04/10/909/403.geojson",
            URL + "?v=1",
            "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/1024/403.geojson",
            "https://cyberjapandata.gsi.go.jp/xyz/skhb01/21/909/403.geojson",
        ]:
            with self.subTest(url=bad), self.assertRaises(ValueError):
                verify_https_provenance(RAW, bad, c_accepted(), opener=fake_opener())

    def test_empty_remote_response_rejected(self):
        with self.assertRaises(ValueError):
            verify_https_provenance(RAW, URL, c_accepted(), opener=fake_opener(raw=b""))


if __name__ == "__main__":
    unittest.main()
