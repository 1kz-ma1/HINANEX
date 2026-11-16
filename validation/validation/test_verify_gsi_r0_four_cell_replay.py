"""Synthetic-only R0 C audit tests. No actual GSI network or raw checked into Git."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import atan, sinh, pi
from pathlib import Path
import tempfile
import unittest

from verify_gsi_r0_four_cell_replay import (
    CBlocked, SCHEMA, MATRIX_KIND, check_four_cells,
    inspect_c_raw, validate_r0_report, canonical_url,
)

NOW = datetime(2026, 11, 16, 3, 0, tzinfo=timezone.utc)
AT = "2026-11-16T02:00:00+00:00"
TILES = {"A": {"z": 10, "x": 909, "y": 403},
         "B": {"z": 10, "x": 910, "y": 404}}
HAZARDS = {"flood": ("disaster1", "GSI_SKHB01_FLOOD"),
           "landslide": ("disaster2", "GSI_SKHB02_LANDSLIDE")}


def point_inside(tile):
    x, y = tile["x"], tile["y"]
    return [(x + 0.5) / 1024 * 360 - 180,
            atan(sinh(pi * (1 - 2 * (y + 0.5) / 1024))) * 180 / pi]


def raw_for(hazard, tile, *, label="SYNTHETIC ONLY", marker=1, coords=None):
    attr, _ = HAZARDS[hazard]
    doc = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "properties": {"name": label, "address": None, "remarks": None,
                       attr: marker},
        "geometry": {"type": "Point",
                     "coordinates": point_inside(tile) if coords is None else coords},
    }]}
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def cell(slot, hazard, *, raw):
    tile = TILES[slot]
    attribute, dataset = HAZARDS[hazard]
    url = canonical_url(hazard, tile)
    return {
        "slot": slot, "tile": tile.copy(), "hazard": hazard,
        "source_url": url, "hazard_dataset": dataset,
        "expected_hazard_attribute": attribute,
        "capture_status": "RAW_CAPTURED_C_UNVERIFIED",
        "reason": "C_INDEPENDENT_REPLAY_AND_HUMAN_REVIEW_NOT_DONE",
        "retrieved_at_utc": AT,
        "source_raw_sha256": sha256(raw).hexdigest(),
        "source_bytes": len(raw), "tile_wide_feature_count": 1,
        "c_https_byte_replay": "NOT_RUN",
        "c_independent_acceptance": "NOT_GRANTED",
        "municipal_coverage_verified": False,
        "physical_facility_identity_approved": False,
        "hazard_safety_verified": False,
        "human_review": "DEFERRED_TO_HUMAN_BATCH_REVIEW",
        "publication_approval": "NOT_GRANTED",
    }


def receipt_for(row, raw):
    return {
        "source_url": row["source_url"],
        "response_final_url": row["source_url"],
        "hazard": row["hazard"],
        "hazard_dataset": row["hazard_dataset"],
        "expected_hazard_attribute": row["expected_hazard_attribute"],
        "tile": row["tile"], "source_sha256": sha256(raw).hexdigest(),
        "source_bytes": len(raw), "archive_feature_count": 1,
        "http_status": 200, "acquisition_status": "LOCAL_ARCHIVE_RECEIVED",
        "acquisition_method": "DIRECT_OFFICIAL_HTTPS_GET",
        "status": "H0_LOCAL_STRUCTURE_ONLY",
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "official_https_byte_replay": "NOT_RUN",
        "independent_c_acceptance": "NOT_GRANTED",
        "publication_approval": "NOT_GRANTED",
        "retrieved_at_utc": AT,
    }


def r0_report(rows):
    return {
        "schema": SCHEMA, "matrix_kind": MATRIX_KIND,
        "cells_total": 4, "cells_local_raw_captured": 4,
        "cells_independently_c_accepted": 0,
        "pilot_b_geographically_distant_verified": False,
        "municipal_boundary_verified": False,
        "human_review": "DEFERRED_TO_HUMAN_BATCH_REVIEW",
        "publication_approval": "NOT_GRANTED",
        "status": "R0_FOUR_TILE_CAPTURES_UNAPPROVED",
        "cells": rows,
    }


class R0CReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hinanex-c-r0-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.raws = {}
        self.paths = {}
        rows = []
        for slot in ("A", "B"):
            for hazard in ("flood", "landslide"):
                raw = raw_for(hazard, TILES[slot])
                row = cell(slot, hazard, raw=raw)
                x, y = TILES[slot]["x"], TILES[slot]["y"]
                path = self.folder / f"r0-{slot}-{hazard}-10-{x}-{y}.geojson"
                path.write_bytes(raw)
                path.with_suffix(".receipt.json").write_text(
                    json.dumps(receipt_for(row, raw)), encoding="utf-8")
                rows.append(row)
                self.raws[row["source_url"]] = raw
                self.paths[(slot, hazard)] = path
        self.report = r0_report(rows)
        self.http_calls = []

    def get(self, url):
        self.http_calls.append(url)
        return (self.raws[url], 200, url)

    def run_audit(self, *, report=None, replay=False, fetch=None, folder=None):
        return check_four_cells(
            self.report if report is None else report,
            evidence_dir=self.folder if folder is None else folder,
            replay_https=replay,
            fetch=self.get if fetch is None else fetch,
            clock=lambda: NOW,
        )

    def test_default_local_only_checks_all_four_without_network(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "R0_C_FOUR_LOCAL_MATCHES_UNAPPROVED")
        self.assertEqual(result["local_raw_matches"], 4)
        self.assertEqual(result["https_byte_matches"], 0)
        self.assertEqual(self.http_calls, [])
        for r in result["cells"]:
            self.assertEqual(r["status"], "C_LOCAL_RAW_MATCH_UNAPPROVED")
            self.assertIsNone(r["https_byte_match"])
            self.assertEqual(r["c_https_replay"], "NOT_RUN")
            self.assertFalse(r["publication_approved"])
            self.assertFalse(r["c_independent_approved"])
            self.assertNotIn("coordinates", r)

    def test_explicit_https_replay_all_four_independent_exact_bytes(self):
        result = self.run_audit(replay=True)
        self.assertEqual(result["status"], "R0_C_FOUR_HTTPS_BYTE_MATCHES_UNAPPROVED")
        self.assertEqual(len(self.http_calls), 4)
        self.assertEqual(result["local_raw_matches"], 4)
        self.assertEqual(result["https_byte_matches"], 4)
        self.assertEqual(result["cells_independently_approved"], 0)
        self.assertFalse(result["municipal_boundary_verified"])
        self.assertFalse(result["pilot_b_geographically_distant_verified"])
        self.assertFalse(result["publication_approved"])
        for cell_result in result["cells"]:
            self.assertTrue(cell_result["https_byte_match"])
            self.assertEqual(cell_result["status"], "C_HTTPS_BYTE_MATCH_UNAPPROVED")
            self.assertEqual(cell_result["d_raw_sha256_recomputed"],
                             cell_result["c_https_sha256"])

    def test_same_raw_bytes_in_one_cell_changed_while_other_cells_remain_match(self):
        changed = raw_for("landslide", TILES["B"], label="NEW SYNTHETIC REVISION")
        url = canonical_url("landslide", TILES["B"])
        def get_with_change(source):
            self.http_calls.append(source)
            return ((changed if source == url else self.raws[source]), 200, source)
        report = self.run_audit(replay=True, fetch=get_with_change)
        self.assertEqual(report["status"], "R0_C_PARTIAL_OR_MISMATCH_HOLD")
        self.assertEqual(report["https_byte_matches"], 3)
        cell_result = report["cells"][3]
        self.assertEqual(cell_result["status"], "C_SOURCE_CHANGED_OR_MISMATCH_HOLD")
        self.assertFalse(cell_result["https_byte_match"])
        self.assertEqual(cell_result["c_https_sha256"], sha256(changed).hexdigest())
        self.assertFalse(cell_result["c_independent_approved"])

    def test_hazard_url_substitution_fails_before_network(self):
        report = deepcopy(self.report)
        report["cells"][0]["source_url"] = canonical_url("landslide", TILES["A"])
        with self.assertRaisesRegex(CBlocked, "CELL_REPORT_MISMATCH"):
            self.run_audit(report=report, replay=True)
        self.assertEqual(self.http_calls, [])

    def test_cross_tile_raw_swapping_is_rejected(self):
        other_raw = self.paths[("B", "flood")].read_bytes()
        self.paths[("A", "flood")].write_bytes(other_raw)
        result = self.run_audit(replay=True)
        self.assertEqual(result["status"], "R0_C_PARTIAL_OR_MISMATCH_HOLD")
        self.assertEqual(result["cells"][0]["status"], "C_EVIDENCE_OR_REPLAY_HOLD")
        self.assertEqual(result["https_byte_matches"], 3)
        self.assertNotEqual(result["cells"][0]["status"], "C_HTTPS_BYTE_MATCH_UNAPPROVED")

    def test_wrong_tile_coordinate_rejected_even_with_self_consistent_receipt(self):
        row = self.report["cells"][0]
        raw = raw_for("flood", TILES["A"], coords=point_inside(TILES["B"]))
        path = self.paths[("A", "flood")]
        path.write_bytes(raw)
        path.with_suffix(".receipt.json").write_text(
            json.dumps(receipt_for(row, raw)), encoding="utf-8")
        row["source_raw_sha256"] = sha256(raw).hexdigest()
        row["source_bytes"] = len(raw)
        out = self.run_audit()
        self.assertIn("POINT_OUTSIDE", out["cells"][0]["reason"])
        self.assertEqual(out["local_raw_matches"], 3)

    def test_fake_c_approval_in_d_report_rejected(self):
        report = deepcopy(self.report)
        report["cells_independently_c_accepted"] = 4
        with self.assertRaisesRegex(CBlocked, "REPORT_MISMATCH"):
            self.run_audit(report=report)
        report = deepcopy(self.report)
        report["cells"][0]["publication_approval"] = "GRANTED"
        with self.assertRaisesRegex(CBlocked, "CELL_REPORT_MISMATCH"):
            self.run_audit(report=report)

    def test_fake_c_acceptance_in_local_receipt_fails_cell(self):
        receipt_path = self.paths[("A", "flood")].with_suffix(".receipt.json")
        receipt = json.loads(receipt_path.read_text())
        receipt["independent_c_acceptance"] = "PASS"
        receipt_path.write_text(json.dumps(receipt))
        out = self.run_audit(replay=True)
        self.assertEqual(out["local_raw_matches"], 3)
        self.assertEqual(out["https_byte_matches"], 3)
        self.assertEqual(out["cells"][0]["status"], "C_EVIDENCE_OR_REPLAY_HOLD")

    def test_raw_sha_or_source_count_tampering_is_not_accepted(self):
        report = deepcopy(self.report)
        report["cells"][0]["source_raw_sha256"] = "0"*64
        out = self.run_audit(report=report)
        self.assertEqual(out["local_raw_matches"], 3)
        self.assertIn("D_REPORT_MISMATCH", out["cells"][0]["reason"])
        report = deepcopy(self.report)
        report["cells"][0]["tile_wide_feature_count"] = 7
        out = self.run_audit(report=report)
        self.assertEqual(out["local_raw_matches"], 3)

    def test_missing_one_raw_file_still_reports_three_local_results(self):
        self.paths[("B", "flood")].unlink()
        out = self.run_audit(replay=True)
        self.assertEqual(out["local_raw_matches"], 3)
        self.assertEqual(out["https_byte_matches"], 3)
        self.assertEqual(out["status"], "R0_C_PARTIAL_OR_MISMATCH_HOLD")
        self.assertEqual(out["cells"][2]["status"], "C_EVIDENCE_OR_REPLAY_HOLD")

    def test_no_capture_is_not_zero_facility_or_official_empty(self):
        report = deepcopy(self.report)
        row = report["cells"][0]
        for key in ("retrieved_at_utc", "source_raw_sha256", "source_bytes",
                    "tile_wide_feature_count"):
            row.pop(key)
        row["capture_status"] = "NOT_ACQUIRED_OR_EVIDENCE_HOLD"
        row["reason"] = "HTTP_ERROR"
        report["cells_local_raw_captured"] = 3
        report["status"] = "R0_PARTIAL_CAPTURE_HOLD"
        out = self.run_audit(report=report, replay=True)
        self.assertEqual(out["cells"][0]["status"], "C_NOT_ACQUIRED_HOLD")
        self.assertIsNone(out["cells"][0]["tile_wide_feature_count"])
        self.assertEqual(out["https_byte_matches"], 3)

    def test_empty_tile_preserves_coverage_unknown(self):
        raw = b'{"type":"FeatureCollection","features":[]}'
        row = self.report["cells"][0]
        row["capture_status"] = "EMPTY_TILE_COVERAGE_UNKNOWN"
        row["tile_wide_feature_count"] = 0
        row["source_raw_sha256"] = sha256(raw).hexdigest()
        row["source_bytes"] = len(raw)
        path = self.paths[("A", "flood")]
        path.write_bytes(raw)
        receipt = receipt_for(row, raw)
        receipt["archive_feature_count"] = 0
        receipt["status"] = "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF"
        path.with_suffix(".receipt.json").write_text(json.dumps(receipt))
        self.raws[row["source_url"]] = raw
        out = self.run_audit(replay=True)
        self.assertEqual(out["status"], "R0_C_FOUR_HTTPS_BYTE_MATCHES_UNAPPROVED")
        self.assertEqual(out["cells"][0]["status"], "C_EMPTY_TILE_BYTE_MATCH_COVERAGE_UNKNOWN")
        self.assertEqual(out["cells"][0]["tile_wide_feature_count"], 0)
        self.assertFalse(out["municipal_boundary_verified"])

    def test_http_404_or_redirect_is_cell_hold_not_absence(self):
        for response in ((b"",404,canonical_url("flood",TILES["A"])),
                         (b"",200,"https://wrong.example/")):
            with self.subTest(response=response):
                def fetched(url):
                    self.http_calls.append(url)
                    return response if url == canonical_url("flood",TILES["A"]) else (
                        self.raws[url],200,url)
                out = self.run_audit(replay=True,fetch=fetched)
                self.assertEqual(out["cells"][0]["status"], "C_EVIDENCE_OR_REPLAY_HOLD")
                self.assertEqual(out["https_byte_matches"],3)
                self.assertIsNone(out["cells"][0]["https_byte_match"])

    def test_wrong_or_incomplete_four_cell_keys_fail_closed(self):
        report=deepcopy(self.report)
        report["cells"][3]["hazard"]="flood"
        with self.assertRaises(CBlocked):
            self.run_audit(report=report)
        report=deepcopy(self.report)
        report["cells"].pop()
        with self.assertRaisesRegex(CBlocked,"FOUR_CELLS"):
            self.run_audit(report=report)

    def test_slot_tile_drift_and_duplicate_tile_rejected(self):
        report=deepcopy(self.report)
        report["cells"][1]["tile"] = TILES["B"].copy()
        with self.assertRaises(CBlocked):
            self.run_audit(report=report)
        report=deepcopy(self.report)
        for row in report["cells"][2:]:
            row["tile"]=TILES["A"].copy()
            row["source_url"]=canonical_url(row["hazard"],TILES["A"])
        with self.assertRaises(CBlocked):
            self.run_audit(report=report)

    def test_flood_disaster2_without_disaster1_rejected(self):
        raw = raw_for("landslide", TILES["A"])
        with self.assertRaisesRegex(CBlocked,"HAZARD_MARKER"):
            inspect_c_raw(raw,hazard="flood",tile=TILES["A"])

    def test_disaster_marker_string_true_zero_and_nan_rejected(self):
        for marker in ("1",True,0,None,False,2):
            with self.subTest(marker=marker),self.assertRaisesRegex(CBlocked,"HAZARD_MARKER"):
                inspect_c_raw(raw_for("flood",TILES["A"],marker=marker),
                              hazard="flood",tile=TILES["A"])
        with self.assertRaises(CBlocked):
            inspect_c_raw(b'{"type":"FeatureCollection","features":[NaN]}',
                          hazard="flood",tile=TILES["A"])

    def test_duplicate_json_keys_in_raw_are_rejected(self):
        with self.assertRaises(CBlocked):
            inspect_c_raw(b'{"type":"FeatureCollection","features":[],"features":[]}',
                          hazard="flood",tile=TILES["A"])

    def test_naive_clock_or_relative_evidence_dir_rejected(self):
        with self.assertRaisesRegex(CBlocked,"CHECK_CLOCK"):
            check_four_cells(self.report,evidence_dir=self.folder,
                             clock=lambda:datetime(2026,11,16,3,0))
        with self.assertRaisesRegex(CBlocked,"EVIDENCE_DIR"):
            self.run_audit(folder=Path("relative"))

    def test_future_d_timestamp_rejected_per_cell(self):
        row=self.report["cells"][0]
        newtime=(NOW+timedelta(days=1)).isoformat()
        row["retrieved_at_utc"] = newtime
        path=self.paths[("A","flood")].with_suffix(".receipt.json")
        receipt=json.loads(path.read_text())
        receipt["retrieved_at_utc"] = newtime
        path.write_text(json.dumps(receipt))
        out=self.run_audit()
        self.assertEqual(out["local_raw_matches"],3)
        self.assertIn("TIME_IN_FUTURE",out["cells"][0]["reason"])

    def test_never_replay_by_default_even_if_fetch_function_provided(self):
        def explode(url):
            raise AssertionError("not to be called")
        out=self.run_audit(fetch=explode)
        self.assertEqual(out["status"],"R0_C_FOUR_LOCAL_MATCHES_UNAPPROVED")
        self.assertEqual(out["https_byte_matches"],0)


if __name__ == "__main__":
    unittest.main()
