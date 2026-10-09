"""Reference-only publisher must require independent C HTTPS provenance evidence."""
from hashlib import sha256
import unittest

from run_verified_flood_site_reference import require_provenance

RAW = b'{"type":"FeatureCollection","features":[{"type":"Feature"}]}'
DIGEST = sha256(RAW).hexdigest()
SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
ROWS = [{"source_url": SOURCE}]


def acceptance(**kwargs):
    value = {
        "status": "PASS",
        "source_raw_sha256": DIGEST,
        "audit_reference": "C-TEST-ONLY",
        "search_context_region_code": "13123",
    }
    value.update(kwargs)
    return value


def evidence(**kwargs):
    value = {
        "verification_kind": "GSI_SKHB01_FLOOD_HTTPS_BYTE_REPLAY",
        "status": "MATCH",
        "source_url": SOURCE,
        "response_final_url": SOURCE,
        "http_status": 200,
        "archive_sha256": DIGEST,
        "download_sha256": DIGEST,
        "bytes": len(RAW),
        "feature_count": 1,
        "c_audit_reference": "C-TEST-ONLY",
        "c_search_context_region_code": "13123",
        "retrieved_at_utc": "2026-10-09T03:00:00+00:00",
    }
    value.update(kwargs)
    return value


class ProvenancePublishGateTests(unittest.TestCase):
    def test_matching_c_evidence_and_https_report_accepted(self):
        self.assertIsNone(require_provenance(RAW, ROWS, acceptance(), evidence(), "13123"))

    def test_missing_or_wrong_https_report_fails(self):
        variants = [
            None,
            {},
            evidence(status="PENDING"),
            evidence(verification_kind="NOT_GSI"),
            evidence(source_url="https://evil.example/x"),
            evidence(response_final_url="https://evil.example/x"),
            evidence(http_status=404),
            evidence(http_status=True),
            evidence(archive_sha256="0" * 64),
            evidence(download_sha256="0" * 64),
            evidence(bytes=len(RAW) + 1),
            evidence(feature_count=2),
            evidence(feature_count=True),
            evidence(c_audit_reference="OTHER"),
            evidence(c_search_context_region_code="15100"),
            evidence(retrieved_at_utc="nonsense"),
            evidence(retrieved_at_utc="2026-10-09T03:00:00"),
        ]
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                require_provenance(RAW, ROWS, acceptance(), bad, "13123")

    def test_mismatched_c_acceptance_and_source_fails(self):
        with self.assertRaises(ValueError):
            require_provenance(RAW, ROWS, acceptance(status="PENDING"), evidence(), "13123")
        with self.assertRaises(ValueError):
            require_provenance(RAW, ROWS, acceptance(source_raw_sha256="0" * 64), evidence(), "13123")
        with self.assertRaises(ValueError):
            require_provenance(RAW, ROWS, acceptance(audit_reference=""), evidence(), "13123")
        with self.assertRaises(ValueError):
            require_provenance(RAW, [{"source_url": "https://evil.example/x"}], acceptance(), evidence(), "13123")
        with self.assertRaises(ValueError):
            require_provenance(RAW + b" ", ROWS, acceptance(), evidence(), "13123")


if __name__ == "__main__":
    unittest.main()
