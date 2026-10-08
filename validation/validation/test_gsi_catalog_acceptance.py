"""Synthetic-only independent C->D->E reference catalog acceptance regressions."""
import hashlib
import json
import unittest

from verify_gsi_catalog_acceptance import verify_local_catalog
from verify_gsi_flood_source import verify_gsi_flood_source
from src.hinanex.flood_site_reference import extract_gsi_flood_tile, build_flood_site_catalog

SOURCE = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson"
RAW = json.dumps({
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [139.9, 35.7]},
        "properties": {
            "name": "TEST_ONLY_NOT_REAL", "address": "TEST", "remarks": None, "disaster1": 1
        },
    }],
}).encode("utf-8")


def prepared(raw=RAW):
    rows = extract_gsi_flood_tile(raw, SOURCE, "13123")
    c = verify_gsi_flood_source(raw, rows, SOURCE, "13123")
    provenance = {
        "verification_kind": "GSI_SKHB01_FLOOD_HTTPS_BYTE_REPLAY",
        "status": "MATCH",
        "source_url": SOURCE, "response_final_url": SOURCE,
        "http_status": 200,
        "archive_sha256": hashlib.sha256(raw).hexdigest(),
        "download_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw), "feature_count": len(rows),
        "c_audit_reference": c["audit_reference"],
        "c_search_context_region_code": "13123",
        "retrieved_at_utc": "2026-10-09T03:00:00+00:00",
    }
    catalog = build_flood_site_catalog("13123", rows, raw_archive=raw, c_acceptance=c)
    catalog.update({
        "https_provenance_status": "MATCH",
        "https_provenance_checked_at_utc": provenance["retrieved_at_utc"],
    })
    return raw, rows, c, provenance, catalog


class GsiCatalogLocalAcceptanceTests(unittest.TestCase):
    def test_synthetic_complete_chain_is_local_pass_only(self):
        report = verify_local_catalog(*prepared(), SOURCE, "13123")
        self.assertEqual(report["status"], "LOCAL_CATALOG_CONTRACT_PASS")
        self.assertEqual(report["tile_wide_feature_count"], 1)
        self.assertEqual(report["raw_sha256"], hashlib.sha256(RAW).hexdigest())
        self.assertIn("not a municipality", report["limitations"][2])
        self.assertNotIn("is_safe", report)

    def test_d_catalog_mutation_or_legacy_missing_metadata_is_blocked(self):
        for change in [
            {"https_provenance_status": "UNKNOWN"},
            {"https_provenance_checked_at_utc": None},
            {"total_source_records": 2},
            {"sites": []},
        ]:
            raw, rows, c, provenance, catalog = prepared()
            catalog.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_local_catalog(raw, rows, c, provenance, catalog, SOURCE)

    def test_wrong_c_manifest_or_https_report_is_blocked(self):
        for change in [
            {"download_sha256": "0" * 64},
            {"status": "PENDING"},
            {"source_url": "https://example.invalid/test"},
            {"http_status": 404},
        ]:
            raw, rows, c, provenance, catalog = prepared()
            provenance.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_local_catalog(raw, rows, c, provenance, catalog, SOURCE)
        raw, rows, c, provenance, catalog = prepared()
        c["source_raw_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_local_catalog(raw, rows, c, provenance, catalog, SOURCE)

    def test_out_of_tile_coordinate_rejected_even_with_consistent_c_and_d(self):
        altered_raw = json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [140.1, 35.7]},
                "properties": {"name": "TEST_OFF_TILE", "address": None,
                               "remarks": None, "disaster1": 1},
            }],
        }).encode("utf-8")
        raw, rows, c, provenance, catalog = prepared(altered_raw)
        with self.assertRaisesRegex(ValueError, "outside the archived tile"):
            verify_local_catalog(raw, rows, c, provenance, catalog, SOURCE)

    def test_non_edogawa_context_cannot_claim_gis_browser_ready(self):
        with self.assertRaisesRegex(ValueError, "Edogawa-only"):
            verify_local_catalog(*prepared(), SOURCE, "15100")


if __name__ == "__main__":
    unittest.main()
