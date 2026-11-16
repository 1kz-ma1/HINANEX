"""R0 deterministic matrix tests, synthetic sources only, no real HTTPS."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from src.hinanex.gsi_hazard_acquisition import (
    AcquisitionFailure, TransportResult, acquire_one_tile,
)
from src.hinanex.gsi_r0_pilot_batch import (
    PLAN_SCHEMA, build_r0_matrix, _validate_pilots,
)


def plan():
    # Test-only tile positions; NOT two approved regions.
    return {
        "schema": PLAN_SCHEMA,
        "pilots": [
            {"slot": "A", "tile": {"z": 10, "x": 909, "y": 403}},
            {"slot": "B", "tile": {"z": 10, "x": 910, "y": 404}},
        ],
    }


FIXED = datetime(2026, 11, 16, 4, 0, tzinfo=timezone.utc)
EMPTY = b'{"type":"FeatureCollection","features":[]}'
FEATURE = json.dumps({
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"name": "SYNTHETIC ONLY", "disaster1": 1,
                       "disaster2": 1, "address": None, "remarks": None},
        "geometry": {"type": "Point", "coordinates": [139.9, 35.7]},
    }],
}).encode()


class R0TileMatrixTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="hinanex-r0-synthetic-")
        self.addCleanup(self.work.cleanup)
        self.external_dir = Path(self.work.name)
        self.calls = []

    def capture(self, *, hazard, source_url, raw_out):
        self.calls.append((hazard, source_url, raw_out))
        # The same injection does no external network. Test response is
        # synthetically constructed, never a real designated site.
        return acquire_one_tile(
            hazard=hazard, source_url=source_url, raw_out=raw_out,
            transport=lambda url: TransportResult(
                raw=EMPTY, http_status=200, final_url=url,
                content_type="application/geo+json",
                etag=None, last_modified=None,
            ),
            now=lambda: FIXED,
        )

    def test_default_dry_run_zero_network_and_no_raw(self):
        out=build_r0_matrix(plan(), acquire=self.capture)
        self.assertEqual(out["status"], "R0_PREVIEW_ONLY")
        self.assertEqual(out["cells_total"], 4)
        self.assertEqual(out["cells_local_raw_captured"], 0)
        self.assertEqual(out["cells_independently_c_accepted"], 0)
        self.assertFalse(out["pilot_b_geographically_distant_verified"])
        self.assertEqual(self.calls, [])
        self.assertEqual([x["capture_status"] for x in out["cells"]],
                         ["NOT_EXECUTED"]*4)

    def test_explicit_order_exact_hazard_and_four_urls(self):
        backwards=plan()
        backwards["pilots"].reverse()
        out=build_r0_matrix(backwards)
        keys=[(x["slot"],x["hazard"]) for x in out["cells"]]
        self.assertEqual(keys, [
            ("A", "flood"), ("A", "landslide"),
            ("B", "flood"), ("B", "landslide")
        ])
        self.assertEqual(
            out["cells"][0]["source_url"],
            "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson")
        self.assertEqual(out["cells"][1]["expected_hazard_attribute"],"disaster2")
        self.assertEqual(out["cells"][2]["expected_hazard_attribute"],"disaster1")
        self.assertEqual(out["cells"][3]["hazard_dataset"],"GSI_SKHB02_LANDSLIDE")

    def test_explicit_capture_four_cells_still_never_accepted(self):
        out=build_r0_matrix(
            plan(),execute=True,evidence_dir=self.external_dir,
            acquire=self.capture,
        )
        self.assertEqual(out["status"], "R0_FOUR_TILE_CAPTURES_UNAPPROVED")
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(out["cells_local_raw_captured"], 4)
        self.assertEqual(out["cells_independently_c_accepted"], 0)
        self.assertEqual([x["capture_status"] for x in out["cells"]],
                         ["EMPTY_TILE_COVERAGE_UNKNOWN"]*4)
        for cell in out["cells"]:
            self.assertEqual(cell["source_bytes"], len(EMPTY))
            self.assertEqual(cell["tile_wide_feature_count"], 0)
            self.assertEqual(cell["c_https_byte_replay"], "NOT_RUN")
            self.assertEqual(cell["c_independent_acceptance"], "NOT_GRANTED")
            self.assertEqual(cell["human_review"], "DEFERRED_TO_HUMAN_BATCH_REVIEW")
            self.assertEqual(cell["publication_approval"], "NOT_GRANTED")
            self.assertNotIn("sites", cell)
            self.assertNotIn("lat", cell)
        self.assertEqual(len(list(self.external_dir.glob("*.geojson"))), 4)
        self.assertEqual(len(list(self.external_dir.glob("*.receipt.json"))), 4)

    def test_nonempty_synthetic_raw_not_approved(self):
        def nonempty(**kwargs):
            raw_url=kwargs["source_url"]
            return acquire_one_tile(
                **kwargs, transport=lambda url: TransportResult(
                    raw=FEATURE,http_status=200,final_url=url,
                    content_type="application/octet-stream",etag=None,last_modified=None),
                now=lambda: FIXED,
            )
        out=build_r0_matrix(
            plan(),execute=True,evidence_dir=self.external_dir,acquire=nonempty)
        self.assertEqual(out["cells_local_raw_captured"],4)
        self.assertTrue(all(c["capture_status"]=="RAW_CAPTURED_C_UNVERIFIED"
                            for c in out["cells"]))
        self.assertTrue(all(c["tile_wide_feature_count"]==1 for c in out["cells"]))
        self.assertEqual(out["cells_independently_c_accepted"],0)

    def test_source_failure_is_not_zero_sites_and_does_not_stop_other_cells(self):
        def partial(**kw):
            if kw["hazard"]=="landslide" and "/909/403" in kw["source_url"]:
                raise AcquisitionFailure("HTTP_ERROR",http_status=404)
            return self.capture(**kw)
        out=build_r0_matrix(
            plan(),execute=True,evidence_dir=self.external_dir,acquire=partial)
        self.assertEqual(out["status"],"R0_PARTIAL_CAPTURE_HOLD")
        self.assertEqual(out["cells_local_raw_captured"],3)
        failed=out["cells"][1]
        self.assertEqual(failed["capture_status"],"NOT_ACQUIRED_OR_EVIDENCE_HOLD")
        self.assertEqual(failed["reason"],"HTTP_ERROR")
        self.assertNotIn("tile_wide_feature_count",failed)
        self.assertEqual(len(self.calls),3)
        self.assertEqual(out["cells_independently_c_accepted"],0)

    def test_tampered_receipt_hash_is_not_counted(self):
        def tampered(**kw):
            receipt=self.capture(**kw)
            receipt["source_sha256"]="0"*64
            return receipt
        out=build_r0_matrix(
            plan(),execute=True,evidence_dir=self.external_dir,acquire=tampered)
        self.assertEqual(out["status"],"R0_PARTIAL_CAPTURE_HOLD")
        self.assertEqual(out["cells_local_raw_captured"],0)
        self.assertTrue(all(c["reason"]=="EVIDENCE_INTEGRITY_OR_FILESYSTEM_HOLD"
                            for c in out["cells"]))
        self.assertEqual(out["cells_independently_c_accepted"],0)

    def test_c_approval_forged_in_receipt_is_rejected(self):
        def forged(**kw):
            receipt=self.capture(**kw)
            receipt["independent_c_acceptance"]="PASS"
            return receipt
        out=build_r0_matrix(
            plan(),execute=True,evidence_dir=self.external_dir,acquire=forged)
        self.assertEqual(out["cells_local_raw_captured"],0)
        self.assertEqual(out["status"],"R0_PARTIAL_CAPTURE_HOLD")
        self.assertFalse(out["municipal_boundary_verified"])

    def test_refuse_existing_evidence_before_any_network(self):
        preexisting=self.external_dir/"r0-B-landslide-10-910-404.geojson"
        preexisting.write_bytes(b"DO_NOT_OVERWRITE")
        with self.assertRaisesRegex(ValueError,"ALREADY_EXISTS"):
            build_r0_matrix(plan(),execute=True,evidence_dir=self.external_dir,
                            acquire=self.capture)
        self.assertEqual(self.calls,[])
        self.assertEqual(preexisting.read_bytes(),b"DO_NOT_OVERWRITE")

    def test_refuse_existing_receipt_before_any_network(self):
        file=self.external_dir/"r0-A-flood-10-909-403.receipt.json"
        file.write_text("existing")
        with self.assertRaisesRegex(ValueError,"ALREADY_EXISTS"):
            build_r0_matrix(plan(),execute=True,evidence_dir=self.external_dir,
                            acquire=self.capture)
        self.assertEqual(self.calls,[])

    def test_execute_requires_existing_absolute_directory(self):
        for d in (None,Path("relative/dir"),
                  self.external_dir/"missing"):
            with self.subTest(d=d),self.assertRaises(ValueError):
                build_r0_matrix(plan(),execute=True,evidence_dir=d,
                                acquire=self.capture)
        self.assertEqual(self.calls,[])

    def test_execute_rejects_repo_directory(self):
        from src.hinanex import gsi_r0_pilot_batch
        repo=Path(gsi_r0_pilot_batch.__file__).resolve().parents[3]
        with self.assertRaisesRegex(ValueError,"OUTSIDE_REPO"):
            build_r0_matrix(plan(),execute=True,evidence_dir=repo,
                            acquire=self.capture)
        self.assertEqual(self.calls,[])

    def test_rejects_duplicate_or_non_A_B_slots(self):
        for slots in ([],[{"slot":"A","tile":{"z":10,"x":909,"y":403}}],
                      [{"slot":"A","tile":{"z":10,"x":909,"y":403}}]*2,
                      [{"slot":"A","tile":{"z":10,"x":909,"y":403}},
                       {"slot":"C","tile":{"z":10,"x":910,"y":404}}]):
            p=plan()
            p["pilots"]=slots
            with self.subTest(slots=slots),self.assertRaises(ValueError):
                _validate_pilots(p)

    def test_rejects_same_tile_not_two_separate_pilots(self):
        p=plan()
        p["pilots"][1]["tile"]=deepcopy(p["pilots"][0]["tile"])
        with self.assertRaisesRegex(ValueError,"DISTINCT"):
            build_r0_matrix(p)

    def test_invalid_tile_dimensions_and_bool_coordinates_rejected(self):
        for bad in (
            {"z":11,"x":909,"y":403}, {"z":10,"x":-1,"y":403},
            {"z":10,"x":1024,"y":403}, {"z":10,"x":909,"y":1024},
            {"z":True,"x":909,"y":403}, {"z":10,"x":True,"y":403},
            {"z":10,"x":"909","y":403}, {"z":10,"x":909,"y":403.0}
        ):
            p=plan()
            p["pilots"][1]["tile"]=bad
            with self.subTest(tile=bad),self.assertRaisesRegex(ValueError,"TILE"):
                build_r0_matrix(p)

    def test_unknown_provenance_and_region_claims_cannot_be_inserted(self):
        for key,val in (
            ("municipality_code","15100"),
            ("region_name","Niigata"),
            ("source_authorization","APPROVED"),
            ("accepted",True)
        ):
            p=plan()
            p["pilots"][1][key]=val
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"FIELDS"):
                build_r0_matrix(p)

    def test_schema_and_unknown_top_level_rejected(self):
        p=plan()
        p["schema"]="hinanex.gsi.r0_tile_matrix.v99"
        with self.assertRaisesRegex(ValueError,"VERSION"):
            build_r0_matrix(p)
        p=plan()
        p["publish"]=True
        with self.assertRaisesRegex(ValueError,"SCHEMA"):
            build_r0_matrix(p)

    def test_execute_flag_not_truthy_string(self):
        with self.assertRaisesRegex(ValueError,"EXECUTE"):
            build_r0_matrix(plan(),execute="true",
                            evidence_dir=self.external_dir,acquire=self.capture)
        self.assertEqual(self.calls,[])

    def test_a_b_tile_does_not_pretend_to_be_administrative_boundary(self):
        out=build_r0_matrix(plan())
        self.assertEqual(out["matrix_kind"],
                         "TWO_EXPLICIT_GSI_TILE_POSITIONS_X_TWO_HAZARDS")
        self.assertFalse(out["pilot_b_geographically_distant_verified"])
        self.assertFalse(out["municipal_boundary_verified"])
        self.assertEqual(out["cells_independently_c_accepted"],0)
        self.assertNotIn("region",out)
        self.assertNotIn("geocoding",out)

    def test_all_statuses_remain_unchanged_across_repeated_previews(self):
        first=build_r0_matrix(plan(),execute=False)
        second=build_r0_matrix(plan(),execute=False)
        self.assertEqual(first,second)
        self.assertEqual(self.calls,[])


if __name__ == "__main__":
    unittest.main()
