"""Synthetic-only H0 HTTPS fetch security and evidence receipt regressions.

The transport is mocked. No real GSI HTTP call, authorized third-party
redistribution, facility discovery or official C certification occurs here.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.hinanex.gsi_hazard_acquisition import (
    AcquisitionFailure, TransportResult, _direct_https_get,
    acquire_one_tile,
)
from src.hinanex.gsi_hazard_preflight import _MAX_BYTES

SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
FLOOD = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
FIXED = datetime(2026, 11, 13, 4, 0, tzinfo=timezone.utc)
RAW = json.dumps({
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [139.5, 35.7]},
        "properties": {"name": "合成訓練施設", "address": "合成地名",
                       "remarks": None, "disaster2": 1},
    }],
}, ensure_ascii=False).encode("utf-8")


def response(*, raw=RAW, status=200, final=SOURCE):
    return TransportResult(
        raw=raw,
        http_status=status,
        final_url=final,
        content_type="application/geo+json",
        etag='"synthetic-not-official"',
        last_modified="Fri, 13 Nov 2026 04:00:00 GMT",
    )


class TestAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hinanex-skhb02-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.gsi.geojson"
        self.called = 0

    def transport(self, url):
        self.assertEqual(url, SOURCE)
        self.called += 1
        return response()

    def run_acquire(self, *, path=None, hazard="landslide", url=SOURCE,
                    transport=None, now=lambda: FIXED):
        return acquire_one_tile(
            hazard=hazard,
            source_url=url,
            raw_out=path if path is not None else self.path,
            transport=transport if transport is not None else self.transport,
            now=now,
        )

    def test_exact_local_archive_and_receipt_saved_with_no_approval(self):
        result = self.run_acquire()
        self.assertEqual(self.called, 1)
        self.assertEqual(self.path.read_bytes(), RAW)
        receipt_path = self.path.with_suffix(".receipt.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["source_url"], SOURCE)
        self.assertEqual(receipt["response_final_url"], SOURCE)
        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["retrieved_at_utc"], "2026-11-13T04:00:00+00:00")
        self.assertEqual(receipt["source_sha256"], sha256(RAW).hexdigest())
        self.assertEqual(receipt["archive_feature_count"], 1)
        self.assertEqual(receipt["expected_hazard_attribute"], "disaster2")
        self.assertEqual(receipt["acquisition_method"], "DIRECT_OFFICIAL_HTTPS_GET")
        self.assertEqual(receipt["independent_c_acceptance"], "NOT_GRANTED")
        self.assertEqual(receipt["official_https_byte_replay"], "NOT_RUN")
        self.assertEqual(receipt["publication_approval"], "NOT_GRANTED")
        self.assertEqual(result, receipt)
        self.assertNotIn("sites", receipt)
        self.assertNotIn("coordinates", receipt)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(receipt_path.stat().st_mode), 0o600)

    def test_no_implicit_overwrite(self):
        self.run_acquire()
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            self.run_acquire()
        self.assertEqual(self.called, 1)
        self.assertEqual(self.path.read_bytes(), RAW)

    def test_fail_before_fetch_if_raw_path_inside_repository(self):
        from src.hinanex import gsi_hazard_acquisition as mod
        root = Path(mod.__file__).resolve().parents[3]
        with self.assertRaisesRegex(ValueError, "outside the Git repository"):
            self.run_acquire(path=root / "pipeline/data/raw/skhb02-unsafe.geojson")
        self.assertEqual(self.called, 0)

    def test_path_must_be_absolute_and_preexisting_parent(self):
        for invalid in (
            Path("relative.geojson"),
            Path(self.temp.name) / "subdir-missing/out.geojson",
            Path(self.temp.name) / "bad-extension.json",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.run_acquire(path=invalid)
        self.assertEqual(self.called, 0)

    def test_url_or_hazard_must_match_before_any_transport(self):
        for url, hazard in (
            (FLOOD, "landslide"),
            (SOURCE, "flood"),
            (SOURCE + "?leak=1", "landslide"),
            (SOURCE.replace("https:", "http:"), "landslide"),
            (SOURCE.replace("cyberjapandata.gsi.go.jp", "attacker.invalid"), "landslide"),
        ):
            with self.subTest(url=url, hazard=hazard), self.assertRaises(ValueError):
                self.run_acquire(url=url, hazard=hazard)
        self.assertEqual(self.called, 0)

    def test_http_404_is_failure_not_zero_facilities(self):
        with self.assertRaises(AcquisitionFailure) as ctx:
            self.run_acquire(transport=lambda url: response(status=404))
        self.assertEqual(ctx.exception.category, "HTTP_ERROR")
        self.assertEqual(ctx.exception.http_status, 404)
        self.assertFalse(self.path.exists())

    def test_redirect_final_url_is_not_accepted_even_if_body_looks_correct(self):
        with self.assertRaisesRegex(AcquisitionFailure, "SOURCE_URL_MISMATCH"):
            self.run_acquire(transport=lambda url: response(final="https://attacker.invalid/archive"))
        self.assertFalse(self.path.exists())

    def test_body_overflow_refused_before_save(self):
        with self.assertRaisesRegex(AcquisitionFailure, "OVERSIZE_OR_INVALID_BODY"):
            self.run_acquire(transport=lambda url: response(raw=b"x" * (_MAX_BYTES + 1)))
        self.assertFalse(self.path.exists())

    def test_invalid_geojson_does_not_create_archive(self):
        with self.assertRaisesRegex(AcquisitionFailure, "SOURCE_STRUCTURE_REJECTED"):
            self.run_acquire(transport=lambda url: response(raw=b"<html>not GeoJSON</html>"))
        self.assertFalse(self.path.exists())

    def test_flood_bytes_cannot_be_passed_as_landslide(self):
        other = json.loads(RAW.decode())
        del other["features"][0]["properties"]["disaster2"]
        other["features"][0]["properties"]["disaster1"] = 1
        raw = json.dumps(other).encode()
        with self.assertRaisesRegex(AcquisitionFailure, "SOURCE_STRUCTURE_REJECTED"):
            self.run_acquire(transport=lambda url: response(raw=raw))
        self.assertFalse(self.path.exists())

    def test_empty_featurecollection_is_recorded_but_not_assumed_zero_region(self):
        empty = b'{"type":"FeatureCollection","features":[]}'
        self.run_acquire(transport=lambda url: response(raw=empty))
        receipt = json.loads(self.path.with_suffix(".receipt.json").read_text())
        self.assertEqual(receipt["status"], "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF")
        self.assertEqual(receipt["archive_feature_count"], 0)
        self.assertEqual(receipt["municipal_coverage"], "NOT_DETERMINED")

    def test_naive_local_clock_does_not_succeed(self):
        with self.assertRaisesRegex(AcquisitionFailure, "CLOCK_IS_NOT_TIMEZONE_AWARE"):
            self.run_acquire(now=lambda: datetime(2026, 11, 13, 4, 0))
        self.assertFalse(self.path.exists())

    def test_cannot_claim_local_time_with_non_utc_offset(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        with self.assertRaisesRegex(AcquisitionFailure, "CLOCK_MUST_BE_UTC"):
            self.run_acquire(now=lambda: datetime(2026, 11, 13, 13, 0, tzinfo=jst))
        self.assertFalse(self.path.exists())

    def test_dns_failure_is_classified_no_archive(self):
        with patch("src.hinanex.gsi_hazard_acquisition.build_opener") as build:
            build.return_value.open.side_effect = URLError(socket.gaierror(-2, "offline"))
            with self.assertRaises(AcquisitionFailure) as ctx:
                _direct_https_get(SOURCE)
        self.assertEqual(ctx.exception.category, "DNS_FAILURE")

    def test_http_exception_keeps_http_code(self):
        with patch("src.hinanex.gsi_hazard_acquisition.build_opener") as build:
            build.return_value.open.side_effect = HTTPError(SOURCE, 404, "Not Found", {}, None)
            with self.assertRaises(AcquisitionFailure) as ctx:
                _direct_https_get(SOURCE)
        self.assertEqual(ctx.exception.category, "HTTP_ERROR")
        self.assertEqual(ctx.exception.http_status, 404)

    def test_no_transport_result_is_accepted(self):
        with self.assertRaisesRegex(AcquisitionFailure, "UNVERIFIED_TRANSPORT"):
            self.run_acquire(transport=lambda url: None)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
