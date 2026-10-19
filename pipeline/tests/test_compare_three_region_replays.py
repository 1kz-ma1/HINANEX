"""Deterministic synthetic, offline tests for D's NON-APPROVAL replay comparator.

Expected to run under pipeline/ (imports existing D Pydantic contract tests).
No official source download, raw data or human approval is simulated.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from compare_three_region_replays import ReplayComparisonError, compare_replays, main
from src.hinanex.integration import EXPECTED_REGIONS
from test_integration import make_export
from unittest.mock import patch


def make_snapshot(directory: Path, mutate=None):
    directory.mkdir()
    for key, (code, name) in EXPECTED_REGIONS.items():
        export = copy.deepcopy(make_export())
        export.region.code, export.region.name = code, name
        for item in (*export.datasets, *export.assessments, *export.capabilities):
            item.region_code, item.region_name = code, name
        if mutate is not None:
            mutate(key, export)
        (directory / f"{key}.json").write_text(
            json.dumps(export.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
        )


class DReplayCompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.before, self.after = self.dir / "before", self.dir / "after"
        make_snapshot(self.before)
        make_snapshot(self.after)

    def test_identical_triples_remain_unapproved(self):
        v = compare_replays(self.before, self.after)
        self.assertEqual(v["region_count"], 3)
        self.assertEqual(set(v["regions"]), set(EXPECTED_REGIONS))
        self.assertTrue(all(not x["observed_changes"] for x in v["regions"].values()))
        self.assertEqual(v["status"], "UNREVIEWED_REQUIRES_INDEPENDENT_C_AUDIT")
        self.assertFalse(v["data_promotion_authorized"])
        self.assertFalse(v["raw_original_source_sha256_verified_by_this_tool"])
        self.assertEqual(v["regions"]["edogawa"]["before"]["assessment_metric_scores"], {"null": 11, "positive": 4})

    def test_records_and_null_coordinates_are_reported_not_interpreted(self):
        def mutate(key, export):
            if key == "edogawa":
                export.datasets[0].records[0]["latitude"] = None
                export.datasets[0].records.append({"id": "second", "name": "Fixture B", "latitude": None, "longitude": None})
                export.assessments[0].record_count = 2
        for p in self.after.glob("*.json"): p.unlink()
        self.after.rmdir()
        make_snapshot(self.after, mutate)
        v = compare_replays(self.before, self.after)
        changes = v["regions"]["edogawa"]["observed_changes"]
        self.assertEqual(changes["location_records"], {"before": 1, "after": 2})
        self.assertEqual(changes["missing_location_coordinates"], {"before": 0, "after": 2})
        self.assertIn("location_record_ids_sha256", changes)
        self.assertNotIn("location_records", v["regions"]["nagoya"]["observed_changes"])
        self.assertFalse(v["data_promotion_authorized"])

    def test_mutated_evidence_is_surfaced_with_metadata_not_source_digest(self):
        value = json.loads((self.after / "niigata.json").read_text())
        value["datasets"][0]["evidence"][0]["source_url"] = "https://example.test/changed-source"
        (self.after / "niigata.json").write_text(json.dumps(value))
        v = compare_replays(self.before, self.after)
        self.assertIn("source_evidence_metadata_sha256", v["regions"]["niigata"]["observed_changes"])
        self.assertTrue(any("NOT original publisher source SHA256" in x for x in v["limitations"]))

    def test_score_zero_and_null_remain_distinct(self):
        value = json.loads((self.after / "nagoya.json").read_text())
        value["assessments"][0]["data_quality"]["coverage"]["score"] = 0
        (self.after / "nagoya.json").write_text(json.dumps(value))
        v = compare_replays(self.before, self.after)
        delta = v["regions"]["nagoya"]["observed_changes"]["assessment_metric_scores"]
        self.assertEqual(delta["before"]["null"], delta["after"]["null"] + 1)
        self.assertEqual(delta["after"]["zero"], 1)
        self.assertFalse(v["data_promotion_authorized"])

    def test_missing_required_region_fails_closed(self):
        (self.after / "nagoya.json").unlink()
        with self.assertRaisesRegex(ReplayComparisonError, "missing or symlinked"):
            compare_replays(self.before, self.after)

    def test_invalid_export_contract_fails_closed(self):
        value = json.loads((self.after / "edogawa.json").read_text())
        value["meta"]["schema_version"] = "12345"
        (self.after / "edogawa.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ReplayComparisonError, "contract validation"):
            compare_replays(self.before, self.after)

    def test_swapped_region_identity_fails_closed(self):
        value = json.loads((self.after / "edogawa.json").read_text())
        value["region"]["code"] = "15100"
        (self.after / "edogawa.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ReplayComparisonError, "contract validation"):
            compare_replays(self.before, self.after)

    def test_duplicate_location_identifiers_fail_closed(self):
        value = json.loads((self.after / "edogawa.json").read_text())
        value["datasets"][0]["records"].append(dict(value["datasets"][0]["records"][0]))
        (self.after / "edogawa.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ReplayComparisonError, "Duplicate location"):
            compare_replays(self.before, self.after)

    def test_unverified_output_paths_rejected(self):
        with self.assertRaisesRegex(ReplayComparisonError, "Two independent"):
            compare_replays(self.before, self.before)
        nested = self.before / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(ReplayComparisonError, "Nested"):
            compare_replays(self.before, nested)
        with self.assertRaisesRegex(ReplayComparisonError, "outside both"):
            compare_replays(self.before, self.after, self.after / "report.json")
        existing = self.dir / "exists.json"
        existing.write_text("old, do not overwrite")
        with self.assertRaisesRegex(ReplayComparisonError, "overwrite"):
            compare_replays(self.before, self.after, existing)
        self.assertEqual(existing.read_text(), "old, do not overwrite")

    def test_symlinks_fail_closed(self):
        (self.after / "edogawa.json").unlink()
        (self.after / "edogawa.json").symlink_to(self.before / "edogawa.json")
        with self.assertRaisesRegex(ReplayComparisonError, "symlinked"):
            compare_replays(self.before, self.after)

    def test_missing_evidence_fails_closed(self):
        value = json.loads((self.after / "edogawa.json").read_text())
        value["datasets"][0]["evidence"] = []
        value["meta"]["evidence_count"] = 0
        (self.after / "edogawa.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ReplayComparisonError, "no source Evidence"):
            compare_replays(self.before, self.after)

    def test_cli_creates_single_report_outside_git_and_refuses_overwrite(self):
        dest = self.dir / "reports" / "diff.json"
        args = ["compare_three_region_replays.py", "--before", str(self.before), "--after", str(self.after), "--report", str(dest)]
        with patch("sys.argv", args):
            self.assertEqual(main(), 0)
            self.assertFalse(json.loads(dest.read_text())["data_promotion_authorized"])
            with self.assertRaises(SystemExit) as exc:
                main()
            self.assertEqual(exc.exception.code, 2)


if __name__ == "__main__":
    unittest.main()