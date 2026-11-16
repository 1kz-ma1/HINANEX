"""R0 two explicit GSI *tile positions* x two hazards offline/opt-in capture.

This is a technical feasibility matrix, not two verified municipalities,
four accepted datasets, an approved source license, or shelter suitability.
D-only; requires the H0 acquisition provider from Draft PR #379.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from src.hinanex.gsi_hazard_acquisition import AcquisitionFailure, acquire_one_tile
from src.hinanex.gsi_hazard_preflight import _MAX_BYTES, _check_url


PLAN_SCHEMA = "hinanex.gsi.r0_tile_matrix.v0.1"
HAZARDS = (
    ("flood", "skhb01", "disaster1", "GSI_SKHB01_FLOOD"),
    ("landslide", "skhb02", "disaster2", "GSI_SKHB02_LANDSLIDE"),
)
REVIEW = "DEFERRED_TO_HUMAN_BATCH_REVIEW"
NOT_APPROVED = "NOT_GRANTED"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _validate_pilots(document: object) -> list[dict]:
    """No coordinate inference, no declared municipality or implied coverage."""
    if not isinstance(document, dict) or set(document) != {"schema", "pilots"}:
        raise ValueError("R0_PLAN_SCHEMA_INVALID")
    if document["schema"] != PLAN_SCHEMA:
        raise ValueError("R0_PLAN_VERSION_UNSUPPORTED")
    entries = document["pilots"]
    if not isinstance(entries, list) or len(entries) != 2:
        raise ValueError("R0_REQUIRES_EXACTLY_TWO_EXPLICIT_TILE_SLOTS")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"slot", "tile"}:
            raise ValueError("R0_PILOT_FIELDS_INVALID")
        slot, tile = entry["slot"], entry["tile"]
        if slot not in ("A", "B") or slot in result:
            raise ValueError("R0_SLOTS_MUST_BE_UNIQUE_A_AND_B")
        if not isinstance(tile, dict) or set(tile) != {"z", "x", "y"}:
            raise ValueError("R0_TILE_FIELDS_INVALID")
        if (any(type(tile.get(k)) is not int for k in ("z", "x", "y"))
                or tile["z"] != 10
                or not 0 <= tile["x"] < 1024
                or not 0 <= tile["y"] < 1024):
            raise ValueError("R0_TILE_ZXY_INVALID")
        result[slot] = {"slot": slot, "tile": dict(tile)}
    if set(result) != {"A", "B"}:
        raise ValueError("R0_REQUIRES_A_AND_B")
    if result["A"]["tile"] == result["B"]["tile"]:
        raise ValueError("R0_REQUIRES_DISTINCT_EXPLICIT_TILE_POSITIONS")
    return [result["A"], result["B"]]


def _inside_repo(path: Path) -> bool:
    repository = Path(__file__).resolve().parents[3]
    return path.resolve(strict=False).is_relative_to(repository)


def _evidence_dir(directory: Path | None) -> Path:
    if (directory is None or not isinstance(directory, Path)
            or not directory.is_absolute()):
        raise ValueError("R0_ABSOLUTE_EVIDENCE_DIRECTORY_REQUIRED")
    if not directory.is_dir():
        raise ValueError("R0_EVIDENCE_MUST_BE_EXISTING_DIRECTORY_OUTSIDE_REPO")
    result = directory.resolve(strict=True)
    if _inside_repo(result):
        raise ValueError("R0_EVIDENCE_MUST_BE_EXISTING_DIRECTORY_OUTSIDE_REPO")
    return result


def _utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value
    ):
        return False
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return moment.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _verify_capture_result(
    receipt: object, *, raw_out: Path, hazard: str, source_url: str,
    attribute: str, dataset: str, tile: dict,
) -> dict:
    """Verify the actual local archive, never trust a receipt or a count alone."""
    receipt_path = raw_out.with_suffix(".receipt.json")
    if (not isinstance(receipt, dict) or not raw_out.is_file()
            or not receipt_path.is_file()):
        raise ValueError("R0_CAPTURE_MISSING_RAW_OR_RECEIPT")
    if receipt_path.stat().st_size > 100_000:
        raise ValueError("R0_CAPTURE_RECEIPT_OVERSIZED")
    if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
        raise ValueError("R0_CAPTURE_SAVED_RECEIPT_MISMATCH")
    if not (0 < raw_out.stat().st_size <= _MAX_BYTES):
        raise ValueError("R0_CAPTURE_RAW_SIZE_INVALID")
    raw = raw_out.read_bytes()
    digest = sha256(raw).hexdigest()
    count = receipt.get("archive_feature_count")
    if type(count) is not int or not 0 <= count <= 50000:
        raise ValueError("R0_CAPTURE_FEATURE_COUNT_INVALID")
    required = {
        "acquisition_status": "LOCAL_ARCHIVE_RECEIVED",
        "acquisition_method": "DIRECT_OFFICIAL_HTTPS_GET",
        "status": ("H0_LOCAL_STRUCTURE_ONLY" if count else
                   "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF"),
        "hazard": hazard,
        "hazard_dataset": dataset,
        "expected_hazard_attribute": attribute,
        "source_url": source_url,
        "response_final_url": source_url,
        "tile": tile,
        "http_status": 200,
        "source_sha256": digest,
        "source_bytes": len(raw),
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "official_https_byte_replay": "NOT_RUN",
        "independent_c_acceptance": NOT_APPROVED,
        "publication_approval": NOT_APPROVED,
    }
    for key, value in required.items():
        if type(receipt.get(key)) is not type(value) or receipt[key] != value:
            raise ValueError("R0_CAPTURE_RECEIPT_MISMATCH:" + key)
    if not _DIGEST.fullmatch(digest) or not _utc_timestamp(receipt.get("retrieved_at_utc")):
        raise ValueError("R0_CAPTURE_TIME_OR_HASH_INVALID")
    return {
        "capture_status": ("RAW_CAPTURED_C_UNVERIFIED" if count else
                           "EMPTY_TILE_COVERAGE_UNKNOWN"),
        "reason": "C_INDEPENDENT_REPLAY_AND_HUMAN_REVIEW_NOT_DONE",
        "retrieved_at_utc": receipt["retrieved_at_utc"],
        "source_raw_sha256": digest,
        "source_bytes": len(raw),
        "tile_wide_feature_count": count,
    }


def build_r0_matrix(
    plan: dict,
    *,
    execute: bool = False,
    evidence_dir: Path | None = None,
    acquire=None,
) -> dict:
    """Four deterministic cells. Network is OFF by default, never automatic."""
    pilots = _validate_pilots(plan)
    if type(execute) is not bool:
        raise ValueError("R0_EXECUTE_MUST_BE_BOOLEAN")
    target = _evidence_dir(evidence_dir) if execute else None
    rows = []
    for pilot in pilots:
        tile = pilot["tile"]
        slot = pilot["slot"]
        for hazard, layer, attribute, dataset in HAZARDS:
            url = (f"https://cyberjapandata.gsi.go.jp/xyz/{layer}/10/"
                   f"{tile['x']}/{tile['y']}.geojson")
            # Reuse provider URL preflight; still no network in this step.
            _check_url(url, hazard)
            filename = f"r0-{slot}-{hazard}-10-{tile['x']}-{tile['y']}.geojson"
            rows.append({
                "slot": slot,
                "tile": tile.copy(),
                "hazard": hazard,
                "hazard_dataset": dataset,
                "expected_hazard_attribute": attribute,
                "source_url": url,
                "_filename": filename,
            })

    if execute:
        # Precheck all four output slots *before* any network operation.
        for row in rows:
            raw = target / row["_filename"]
            receipt = raw.with_suffix(".receipt.json")
            if raw.exists() or receipt.exists():
                raise ValueError("R0_EVIDENCE_ALREADY_EXISTS_REFUSE_MIXED_RUNS")

    capture_fn = acquire if acquire is not None else acquire_one_tile
    captured = 0
    for row in rows:
        raw_name = row.pop("_filename")
        if not execute:
            row.update({
                "capture_status": "NOT_EXECUTED",
                "reason": "MANUAL_EXECUTION_REQUIRED",
            })
        else:
            raw_path = target / raw_name
            try:
                receipt = capture_fn(
                    hazard=row["hazard"], source_url=row["source_url"],
                    raw_out=raw_path,
                )
                outcome = _verify_capture_result(
                    receipt, raw_out=raw_path, hazard=row["hazard"],
                    source_url=row["source_url"],
                    attribute=row["expected_hazard_attribute"],
                    dataset=row["hazard_dataset"], tile=row["tile"],
                )
                row.update(outcome)
                captured += 1
            except (AcquisitionFailure, ValueError, OSError) as exc:
                row.update({
                    "capture_status": "NOT_ACQUIRED_OR_EVIDENCE_HOLD",
                    "reason": (exc.category if isinstance(exc, AcquisitionFailure)
                               else "EVIDENCE_INTEGRITY_OR_FILESYSTEM_HOLD"),
                })
        row.update({
            "c_https_byte_replay": "NOT_RUN",
            "c_independent_acceptance": NOT_APPROVED,
            "municipal_coverage_verified": False,
            "physical_facility_identity_approved": False,
            "hazard_safety_verified": False,
            "human_review": REVIEW,
            "publication_approval": NOT_APPROVED,
        })

    return {
        "schema": PLAN_SCHEMA,
        "status": ("R0_PREVIEW_ONLY" if not execute else
                   "R0_FOUR_TILE_CAPTURES_UNAPPROVED" if captured == 4 else
                   "R0_PARTIAL_CAPTURE_HOLD"),
        "matrix_kind": "TWO_EXPLICIT_GSI_TILE_POSITIONS_X_TWO_HAZARDS",
        "cells_total": 4,
        "cells_local_raw_captured": captured,
        "cells_independently_c_accepted": 0,
        "pilot_b_geographically_distant_verified": False,
        "municipal_boundary_verified": False,
        "human_review": REVIEW,
        "publication_approval": NOT_APPROVED,
        "note": (
            "A and B are manual tile slots, NOT verified separate municipal regions. "
            "A tile-wide record count is not a city-wide shelter total. "
            "Raw local capture is not C independent approval or public acceptance."
        ),
        "cells": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True,
                        help="Explicit two-slot plan JSON (no inferred coordinates)")
    parser.add_argument("--execute", action="store_true",
                        help="Opt-in: fetch four GSI official tiles, one request per cell")
    parser.add_argument("--evidence-dir", type=Path,
                        help="Existing absolute directory outside Git (required for execute)")
    parser.add_argument("--report-out", type=Path,
                        help="Optional new absolute report file outside Git, never overwrite")
    args = parser.parse_args()
    try:
        if not args.plan.is_file() or args.plan.stat().st_size > 100_000:
            raise ValueError("R0_PLAN_FILE_MISSING_OR_OVERSIZED")
        document = json.loads(args.plan.read_text(encoding="utf-8"))
        report_path = None
        if args.report_out is not None:
            report_path = args.report_out
            if (not report_path.is_absolute()
                    or _inside_repo(report_path)
                    or not report_path.parent.is_dir()
                    or report_path.exists()):
                raise ValueError("R0_REPORT_PATH_MUST_BE_NEW_OUTSIDE_GIT")
        report = build_r0_matrix(
            document, execute=args.execute, evidence_dir=args.evidence_dir,
        )
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if report_path is not None:
            with report_path.open("x", encoding="utf-8") as dest:
                dest.write(output)
        print(output, end="")
        return 0 if report["status"] != "R0_PARTIAL_CAPTURE_HOLD" else 3
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("R0_SOURCE_MATRIX_HOLD: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
