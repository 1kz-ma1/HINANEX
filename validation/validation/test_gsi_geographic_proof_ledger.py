"""Synthetic-only C proof-ledger tests; no web requests or official claims."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gsi_geographic_proof_ledger import (
    build_report, nearby_tiles, origin_tile, verify_tile,
)
from test_gsi_catalog_acceptance import prepared


class GeographicProofLedgerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.base = Path(self.dir.name)
        self.published = self.base / "published"
        self.evidence = self.base / "evidence"
        self.raw = self.base / "raw"
        self.catalog_dir = self.published / "13123"
        self.proof_dir = self.evidence / "one-run"
        self.archive_dir = self.raw / "one-run"
        for folder in (self.catalog_dir, self.proof_dir, self.archive_dir):
            folder.mkdir(parents=True)
        self.raw_bytes, self.records, self.acceptance, self.provenance, self.catalog = prepared()
        self.source_tile_file = self.catalog_dir / "10-909-403.json"
        self.proof_catalog = self.proof_dir / "gsi_flood_site_catalog.json"
        self.archive_file = self.archive_dir / "10-909-403.geojson"
        self.store_proof()

    def store_proof(self):
        # Recreate a complete local raw -> C -> saved HTTPS MATCH -> D copy.
        self.archive_file.write_bytes(self.raw_bytes)
        catalog_bytes = json.dumps(self.catalog, ensure_ascii=False).encode("utf-8")
        self.source_tile_file.write_bytes(catalog_bytes)
        self.proof_catalog.write_bytes(catalog_bytes)
        values = {
            "gsi_records.json": self.records,
            "c_raw_acceptance.json": self.acceptance,
            "c_https_provenance.json": self.provenance,
        }
        for name, data in values.items():
            (self.proof_dir / name).write_text(json.dumps(data), encoding="utf-8")

    def report(self, *origins):
        return build_report(
            "13123", list(origins), self.published, self.evidence, self.raw
        )

    def test_tile_math_and_two_origin_tile_ids_are_distinct(self):
        self.assertEqual(origin_tile("35.7,139.9"), (909, 403))
        self.assertEqual(origin_tile("35.7,140.1"), (910, 403))
        self.assertEqual(len(nearby_tiles(909, 403)), 9)
        self.assertEqual(len(set(nearby_tiles(909, 403))), 9)
        self.assertRaises(ValueError, origin_tile, "90,140")
        self.assertRaises(ValueError, origin_tile, "35.7")
        self.assertRaises(ValueError, origin_tile, "nan,140")

    def test_independent_proof_passes_only_first_tile_and_browser_gates_not_tested(self):
        item = verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)
        self.assertEqual(item["status"], "PASS_SAVED_C_EVIDENCE")
        self.assertEqual(item["tile_wide_feature_count"], 1)
        self.assertEqual(item["raw_sha256"], sha256(self.raw_bytes).hexdigest())
        r = self.report("35.7,139.9", "35.7,140.1")
        self.assertTrue(r["distinct_origin_tiles_sampled"])
        self.assertEqual(r["origin_checks"][0]["source_tiles_verified"], 1)
        self.assertEqual(r["origin_checks"][0]["status"], "PARTIAL_LOCAL_SOURCE_PROOF")
        self.assertEqual(r["origin_checks"][1]["status"], "ORIGIN_UNVERIFIED")
        self.assertFalse(r["all_requested_source_tiles_locally_verified"])
        self.assertFalse(r["baseline_accepted"])
        self.assertEqual(r["manual_gate_status"]["gps_permission_and_denial_fallback"], "NOT_TESTED")
        self.assertNotIn("safe", item)

    def test_missing_sources_never_become_authoritative_zero_sites(self):
        self.source_tile_file.unlink()
        tile = verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)
        self.assertEqual(tile["status"], "MISSING_PUBLICATION")
        r = self.report("35.7,139.9")
        self.assertEqual(r["origin_checks"][0]["status"], "ORIGIN_UNVERIFIED")
        self.assertTrue(all("no designated" not in s.lower() for s in r["limitations"]))

    def test_missing_raw_or_c_proof_not_accepted(self):
        self.archive_file.unlink()
        self.assertEqual(
            verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)["status"],
            "UNVERIFIED_RAW_ARCHIVE",
        )
        self.archive_file.write_bytes(self.raw_bytes)
        (self.proof_dir / "c_https_provenance.json").unlink()
        self.assertEqual(
            verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)["status"],
            "UNVERIFIED_C_EVIDENCE",
        )
        self.store_proof()
        self.proof_catalog.unlink()
        self.assertEqual(
            verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)["status"],
            "UNVERIFIED_C_EVIDENCE",
        )

    def test_poisoned_tile_and_saved_https_proof_block_instead_of_pass(self):
        saved = deepcopy(self.catalog)
        saved["sites"][0]["source_url"] = (
            "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
        )
        self.catalog = saved
        self.store_proof()
        self.assertEqual(
            verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)["status"],
            "BLOCKED_INCONSISTENT",
        )
        self.catalog = prepared()[4]
        self.provenance["status"] = "PENDING"
        self.store_proof()
        self.assertEqual(
            verify_tile(909, 403, "13123", self.published, self.evidence, self.raw)["status"],
            "BLOCKED_INCONSISTENT",
        )

    def test_duplicate_origin_does_not_claim_two_geographic_samples(self):
        r = self.report("35.70,139.90", "35.71,139.89")
        self.assertFalse(r["distinct_origin_tiles_sampled"])
        self.assertFalse(r["baseline_accepted"])

    def test_cli_report_writes_only_when_explicit_and_never_overwrites(self):
        script = Path(__file__).with_name("gsi_geographic_proof_ledger.py")
        outfile = self.base / "report.json"
        args = [
            sys.executable, str(script), "--region", "13123",
            "--origin", "35.7,139.9",
            "--published-root", str(self.published),
            "--evidence-root", str(self.evidence),
            "--raw-root", str(self.raw),
            "--report-out", str(outfile),
        ]
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(outfile.read_text(encoding="utf-8"))
        self.assertFalse(payload["baseline_accepted"])
        digest_before = sha256(outfile.read_bytes()).hexdigest()
        result_again = subprocess.run(args, capture_output=True, text=True, check=False)
        self.assertNotEqual(result_again.returncode, 0)
        self.assertIn("already exists", result_again.stderr)
        self.assertEqual(sha256(outfile.read_bytes()).hexdigest(), digest_before)


if __name__ == "__main__":
    unittest.main()
