"""Synthetic-only tests for C independent GSI skhb02 HTTPS byte replay."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import socket
from urllib.error import HTTPError, URLError

from verify_gsi_skhb02_https_replay import (
    SOURCE, ReplayBlocked, direct_official_get, inspect_raw,
    validate_d_receipt, verify_independent_replay,
)

NOW = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)


def synthetic_raw(name="SYNTHETIC"):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": name, "address": None,
                           "remarks": None, "disaster2": 1},
            "geometry": {"type": "Point", "coordinates": [139.9, 35.7]},
        }],
    }, ensure_ascii=False).encode("utf-8")


def d_receipt(raw):
    return {
        "source_url": SOURCE,
        "response_final_url": SOURCE,
        "hazard": "landslide",
        "hazard_dataset": "GSI_SKHB02_LANDSLIDE",
        "expected_hazard_attribute": "disaster2",
        "tile": {"z": 10, "x": 909, "y": 403},
        "status": "H0_LOCAL_STRUCTURE_ONLY",
        "source_sha256": sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "archive_feature_count": 1,
        "http_status": 200,
        "acquisition_status": "LOCAL_ARCHIVE_RECEIVED",
        "acquisition_method": "DIRECT_OFFICIAL_HTTPS_GET",
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "official_https_byte_replay": "NOT_RUN",
        "independent_c_acceptance": "NOT_GRANTED",
        "publication_approval": "NOT_GRANTED",
        "retrieved_at_utc": "2026-11-16T01:42:30+00:00",
    }


def run(raw=None, receipt=None, replay=None, status=200, final=SOURCE):
    raw = synthetic_raw() if raw is None else raw
    return verify_independent_replay(
        raw,
        d_receipt(raw) if receipt is None else receipt,
        transport=lambda: (raw if replay is None else replay, status, final),
        clock=lambda: NOW,
    )


class TestGsiSkhb02IndependentHttpsReplay(unittest.TestCase):
    def test_exact_byte_match_is_not_c_approval(self):
        out = run()
        self.assertEqual(out["status"], "C_HTTPS_BYTE_MATCH_UNAPPROVED")
        self.assertEqual(out["independent_https_byte_replay"], "MATCH")
        self.assertTrue(out["same_bytes"])
        self.assertEqual(out["d_archived_sha256_recomputed"], sha256(synthetic_raw()).hexdigest())
        self.assertEqual(out["c_replayed_sha256"], out["d_archived_sha256_recomputed"])
        self.assertEqual(out["d_archived_tile_feature_count"], 1)
        for k in ("independent_c_approved", "municipal_coverage_verified",
                  "facility_identity_approved", "current_open_status_verified",
                  "hazard_safety_verified", "publication_approved"):
            self.assertFalse(out[k])

    def test_revision_or_response_change_is_a_hold_not_auto_approval(self):
        out = run(replay=synthetic_raw("CHANGED"))
        self.assertEqual(out["status"], "C_SOURCE_CHANGED_OR_MISMATCH_HOLD")
        self.assertEqual(out["independent_https_byte_replay"], "DIFFERENT")
        self.assertFalse(out["same_bytes"])
        self.assertFalse(out["independent_c_approved"])

    def test_d_receipt_hash_bytes_count_and_scope_rechecked(self):
        raw = synthetic_raw()
        original = d_receipt(raw)
        for key, value in (
            ("source_sha256", "0"*64), ("source_bytes", len(raw)+1),
            ("archive_feature_count", 0), ("source_url", SOURCE.replace("skhb02","skhb01")),
            ("response_final_url", "https://evil.invalid"), ("http_status", True),
            ("tile", {"z": 10, "x": 909, "y": 404}),
            ("acquisition_status", "C_ACCEPTED"),
            ("publication_approval", "GRANTED"),
            ("independent_c_acceptance", "PASS"),
            ("hazard_dataset", "GSI_SKHB01_FLOOD"),
            ("source_origin", "CRYPTOGRAPHICALLY_AUTHENTICATED"),
            ("official_https_byte_replay", "MATCH"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ReplayBlocked, "D_RECEIPT"):
                validate_d_receipt({**original, key: value}, raw, sha256(raw).hexdigest(), 1)

    def test_boolean_marker_and_string_marker_refused(self):
        for bad in (True, "1", None, 0, 2, False):
            with self.subTest(bad=bad), self.assertRaisesRegex(ReplayBlocked, "MARKER"):
                doc=json.loads(synthetic_raw())
                doc["features"][0]["properties"]["disaster2"] = bad
                inspect_raw(json.dumps(doc).encode())

    def test_flood_only_attribute_not_landslide(self):
        doc=json.loads(synthetic_raw())
        props=doc["features"][0]["properties"]
        del props["disaster2"]
        props["disaster1"]=1
        with self.assertRaisesRegex(ReplayBlocked, "MARKER"):
            inspect_raw(json.dumps(doc).encode())

    def test_geojson_point_must_belong_to_specific_tile(self):
        doc=json.loads(synthetic_raw())
        doc["features"][0]["geometry"]["coordinates"] = [140.5, 35.7]
        with self.assertRaisesRegex(ReplayBlocked, "OUTSIDE_TILE"):
            inspect_raw(json.dumps(doc).encode())

    def test_corrupt_replay_source_blocks_not_a_false_zero(self):
        with self.assertRaises(ReplayBlocked):
            run(replay=b"<html>service unavailable</html>")
        with self.assertRaises(ReplayBlocked):
            run(replay=b"")
        with self.assertRaises(ReplayBlocked):
            run(replay=b'{"type":"FeatureCollection","features":[NaN]}')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ReplayBlocked):
            inspect_raw(b'{"type":"FeatureCollection","features":[],"features":[]}')

    def test_wrong_http_status_and_redirect_final_url_rejected(self):
        for value in (404, 500, True, 204):
            with self.subTest(value=value), self.assertRaisesRegex(ReplayBlocked, "REPLAY_HTTP"):
                run(status=value)
        with self.assertRaisesRegex(ReplayBlocked, "REPLAY_FINAL_URL"):
            run(final="https://evil.invalid/snapshot.geojson")

    def test_naive_and_non_utc_clock_are_rejected(self):
        raw = synthetic_raw()
        for clock in (
            lambda: datetime(2026, 11, 16, 2, 0),
            lambda: datetime(2026, 11, 16, 11, 0,
                             tzinfo=timezone(__import__("datetime").timedelta(hours=9))),
        ):
            with self.subTest(clock=clock), self.assertRaisesRegex(ReplayBlocked, "CLOCK"):
                verify_independent_replay(raw, d_receipt(raw),
                                          transport=lambda: (raw,200,SOURCE), clock=clock)

    def test_naive_future_or_malformed_d_timestamp_fails(self):
        raw=synthetic_raw()
        for when in ("2026-11-16T01:42:30",
                     "2026-11-16T10:42:30+09:00", "2026-14-16T00:00:00Z",
                     "notatime"):
            with self.subTest(when=when), self.assertRaisesRegex(ReplayBlocked, "D_RETRIEVAL"):
                receipt = d_receipt(raw)
                receipt["retrieved_at_utc"] = when
                run(raw=raw, receipt=receipt)

    def test_empty_tile_remains_without_region_coverage(self):
        raw=b'{"type":"FeatureCollection","features":[]}'
        receipt=d_receipt(raw)
        receipt["status"]="H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF"
        receipt["archive_feature_count"]=0
        out=run(raw=raw,receipt=receipt)
        self.assertEqual(out["d_archived_tile_feature_count"], 0)
        self.assertFalse(out["municipal_coverage_verified"])

    def test_dns_failure_reports_distinct_reason(self):
        with patch("verify_gsi_skhb02_https_replay.build_opener") as op:
            op.return_value.open.side_effect=URLError(socket.gaierror(-2, "offline"))
            with self.assertRaisesRegex(ReplayBlocked, "DNS_FAILURE"):
                direct_official_get()

    def test_http_404_reports_distinct_reason(self):
        with patch("verify_gsi_skhb02_https_replay.build_opener") as op:
            op.return_value.open.side_effect=HTTPError(SOURCE,404,"Not Found",{},None)
            with self.assertRaisesRegex(ReplayBlocked, "HTTP_ERROR:404"):
                direct_official_get()

    def test_no_actual_network_in_synthetic_regression(self):
        raw=synthetic_raw()
        out=verify_independent_replay(raw,d_receipt(raw),
                                      transport=lambda: (raw,200,SOURCE),
                                      clock=lambda: NOW)
        self.assertFalse(out["independent_c_approved"])
        self.assertFalse(out["publication_approved"])


if __name__ == "__main__":
    unittest.main()
