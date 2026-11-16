"""C-only R0 four-cell GSI raw/receipt verification and opt-in HTTPS replay.

Two *explicit GSI z10 tile positions* by skhb01 flood and skhb02 landslide
are NOT two approved municipalities. Even four HTTPS byte matches do not
authorize site identity, safety, operations, secondary use, or publication.

Independent of pipeline/ and of D's validators. No network unless the caller
explicitly supplies --replay-https. No per-site rows or coordinates emitted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import socket
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from verify_gsi_skhb02_archive import point_tile

SCHEMA = "hinanex.gsi.r0_tile_matrix.v0.1"
MATRIX_KIND = "TWO_EXPLICIT_GSI_TILE_POSITIONS_X_TWO_HAZARDS"
HAZARDS = {"flood": ("skhb01", "disaster1", "GSI_SKHB01_FLOOD"),
           "landslide": ("skhb02", "disaster2", "GSI_SKHB02_LANDSLIDE")}
CAPTURED = {"RAW_CAPTURED_C_UNVERIFIED", "EMPTY_TILE_COVERAGE_UNKNOWN"}
UNCAPTURED = {"NOT_EXECUTED", "NOT_ACQUIRED_OR_EVIDENCE_HOLD"}
MAX_RAW_BYTES = 12_000_000
MAX_RECEIPT_BYTES = 100_000
MAX_REPORT_BYTES = 100_000
SHA = re.compile(r"[a-f0-9]{64}\Z")
UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


class CBlocked(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CBlocked("C_REPLAY_REDIRECT_REFUSED")


def _exact(record: dict, key: str, expected: object, prefix: str) -> None:
    if type(record.get(key)) is not type(expected) or record[key] != expected:
        raise CBlocked(f"{prefix}:{key}")


def _utc(value: object) -> bool:
    if not isinstance(value, str) or not UTC.fullmatch(value):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() == timedelta(0)
    except ValueError:
        return False


def _duplicate_key_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CBlocked("C_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _bad_constant(value):
    raise CBlocked("C_NON_JSON_NUMBER")


def _load_json(data: bytes) -> object:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_duplicate_key_pairs,
            parse_constant=_bad_constant,
        )
    except (UnicodeError, ValueError) as exc:
        raise CBlocked("C_JSON_INVALID") from exc


def _tile(tile: object) -> tuple[int, int]:
    if (not isinstance(tile, dict) or set(tile) != {"z", "x", "y"}
            or any(type(tile.get(k)) is not int for k in ("z", "x", "y"))
            or tile["z"] != 10
            or not 0 <= tile["x"] < 1024
            or not 0 <= tile["y"] < 1024):
        raise CBlocked("C_TILE_NOT_EXPLICIT_Z10")
    return tile["x"], tile["y"]


def canonical_url(hazard: str, tile: dict) -> str:
    if hazard not in HAZARDS:
        raise CBlocked("C_UNSUPPORTED_HAZARD")
    x, y = _tile(tile)
    return f"https://cyberjapandata.gsi.go.jp/xyz/{HAZARDS[hazard][0]}/10/{x}/{y}.geojson"


def _source_row(row: object) -> tuple[str, str, dict, str]:
    if not isinstance(row, dict):
        raise CBlocked("C_CELL_MUST_BE_OBJECT")
    slot, hazard, tile = row.get("slot"), row.get("hazard"), row.get("tile")
    if slot not in ("A", "B") or hazard not in HAZARDS:
        raise CBlocked("C_CELL_SLOT_OR_HAZARD_INVALID")
    x, y = _tile(tile)
    layer, attribute, dataset = HAZARDS[hazard]
    url = f"https://cyberjapandata.gsi.go.jp/xyz/{layer}/10/{x}/{y}.geojson"
    for key, value in (
        ("source_url", url), ("hazard_dataset", dataset),
        ("expected_hazard_attribute", attribute), ("slot", slot),
        ("hazard", hazard), ("tile", {"z": 10, "x": x, "y": y}),
        ("c_https_byte_replay", "NOT_RUN"),
        ("c_independent_acceptance", "NOT_GRANTED"),
        ("human_review", "DEFERRED_TO_HUMAN_BATCH_REVIEW"),
        ("publication_approval", "NOT_GRANTED"),
        ("municipal_coverage_verified", False),
        ("physical_facility_identity_approved", False),
        ("hazard_safety_verified", False),
    ):
        _exact(row, key, value, "C_CELL_REPORT_MISMATCH")
    status = row.get("capture_status")
    if status not in CAPTURED | UNCAPTURED:
        raise CBlocked("C_CELL_CAPTURE_STATUS_INVALID")
    if status in CAPTURED:
        if (not _utc(row.get("retrieved_at_utc"))
                or not isinstance(row.get("source_raw_sha256"), str)
                or not SHA.fullmatch(row["source_raw_sha256"])
                or type(row.get("source_bytes")) is not int
                or not 0 < row["source_bytes"] <= MAX_RAW_BYTES
                or type(row.get("tile_wide_feature_count")) is not int
                or not 0 <= row["tile_wide_feature_count"] <= 50000):
            raise CBlocked("C_CELL_CAPTURE_EVIDENCE_MISSING")
        if (status == "EMPTY_TILE_COVERAGE_UNKNOWN") != (
            row["tile_wide_feature_count"] == 0
        ):
            raise CBlocked("C_EMPTY_TILE_COUNT_MISMATCH")
    elif status == "NOT_EXECUTED":
        _exact(row, "reason", "MANUAL_EXECUTION_REQUIRED", "C_NOT_EXECUTED_MISMATCH")
    elif not isinstance(row.get("reason"), str):
        raise CBlocked("C_CAPTURE_FAILURE_REASON_MISSING")
    return slot, hazard, tile, url


def validate_r0_report(report: object) -> list[dict]:
    """Reject wrong hazard, fake acceptance, missing cell and duplicate tile."""
    if not isinstance(report, dict):
        raise CBlocked("C_R0_REPORT_INVALID")
    for key, value in (
        ("schema", SCHEMA), ("matrix_kind", MATRIX_KIND), ("cells_total", 4),
        ("cells_independently_c_accepted", 0),
        ("pilot_b_geographically_distant_verified", False),
        ("municipal_boundary_verified", False),
        ("human_review", "DEFERRED_TO_HUMAN_BATCH_REVIEW"),
        ("publication_approval", "NOT_GRANTED"),
    ):
        _exact(report, key, value, "C_R0_REPORT_MISMATCH")
    rows = report.get("cells")
    if not isinstance(rows, list) or len(rows) != 4:
        raise CBlocked("C_R0_REQUIRES_FOUR_CELLS")
    seen = set()
    slots = {}
    captured = 0
    for row in rows:
        slot, hazard, tile, _ = _source_row(row)
        if (slot, hazard) in seen:
            raise CBlocked("C_DUPLICATE_CELL")
        seen.add((slot, hazard))
        if slot in slots and slots[slot] != tile:
            raise CBlocked("C_SLOT_TILE_DRIFT")
        slots[slot] = tile
        if row["capture_status"] in CAPTURED:
            captured += 1
    if (seen != {("A", "flood"), ("A", "landslide"),
                 ("B", "flood"), ("B", "landslide")}
            or slots["A"] == slots["B"]):
        raise CBlocked("C_R0_DUPLICATE_TILE_OR_MISSING_HAZARD")
    _exact(report, "cells_local_raw_captured", captured, "C_CAPTURED_TOTAL_MISMATCH")
    status = (
        "R0_PREVIEW_ONLY" if all(r["capture_status"] == "NOT_EXECUTED" for r in rows)
        else "R0_FOUR_TILE_CAPTURES_UNAPPROVED" if captured == 4
        else "R0_PARTIAL_CAPTURE_HOLD"
    )
    _exact(report, "status", status, "C_R0_STATUS_MISMATCH")
    return sorted(rows, key=lambda r: (r["slot"], 0 if r["hazard"] == "flood" else 1))


def inspect_c_raw(raw: bytes, *, hazard: str, tile: dict) -> tuple[str, int]:
    """Inspect *all* source features and tile geometry without skipping rows."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RAW_BYTES:
        raise CBlocked("C_RAW_SIZE_OR_TYPE_INVALID")
    doc = _load_json(raw)
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise CBlocked("C_RAW_NOT_FEATURE_COLLECTION")
    features = doc.get("features")
    if not isinstance(features, list) or len(features) > 50000:
        raise CBlocked("C_RAW_FEATURES_INVALID")
    marker = HAZARDS[hazard][1]
    x, y = _tile(tile)
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise CBlocked(f"C_INVALID_FEATURE:{i}")
        props, geom = feature.get("properties"), feature.get("geometry")
        if not isinstance(props, dict) or not isinstance(geom, dict):
            raise CBlocked(f"C_INVALID_FEATURE_SHAPE:{i}")
        if type(props.get(marker)) is not int or props[marker] != 1:
            raise CBlocked(f"C_HAZARD_MARKER_MISMATCH:{i}")
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            raise CBlocked(f"C_SOURCE_NAME_MISSING:{i}")
        if any(props.get(k) is not None and not isinstance(props[k], str)
               for k in ("address", "remarks")):
            raise CBlocked(f"C_SOURCE_TEXT_INVALID:{i}")
        coords = geom.get("coordinates")
        if geom.get("type") != "Point" or not isinstance(coords, list) or len(coords) not in (2, 3):
            raise CBlocked(f"C_GEOMETRY_INVALID:{i}")
        lon, lat = coords[:2]
        if (type(lon) not in (int, float) or type(lat) not in (int, float)
                or not isfinite(lon) or not isfinite(lat)):
            raise CBlocked(f"C_POINT_INVALID:{i}")
        try:
            actual_tile = point_tile(lon, lat)
        except (ValueError, OverflowError, TypeError) as exc:
            raise CBlocked(f"C_POINT_INVALID:{i}") from exc
        if actual_tile != (x, y):
            raise CBlocked(f"C_POINT_OUTSIDE_EXPECTED_TILE:{i}")
        if len(coords) == 3 and (type(coords[2]) not in (int, float)
                                 or not isfinite(coords[2])):
            raise CBlocked(f"C_ALTITUDE_INVALID:{i}")
    return sha256(raw).hexdigest(), len(features)


def verify_local_cell(row: dict, *, evidence_dir: Path, checked_at: datetime) -> bytes:
    slot, hazard, tile, source_url = _source_row(row)
    x, y = _tile(tile)
    path = evidence_dir / f"r0-{slot}-{hazard}-10-{x}-{y}.geojson"
    receipt_path = path.with_suffix(".receipt.json")
    if (not path.is_file() or not receipt_path.is_file()
            or path.is_symlink() or receipt_path.is_symlink()):
        raise CBlocked("C_RAW_OR_RECEIPT_NOT_STORED")
    if path.stat().st_size > MAX_RAW_BYTES or receipt_path.stat().st_size > MAX_RECEIPT_BYTES:
        raise CBlocked("C_RAW_OR_RECEIPT_OVERSIZED")
    raw = path.read_bytes()
    receipt = _load_json(receipt_path.read_bytes())
    digest, count = inspect_c_raw(raw, hazard=hazard, tile=tile)
    if not isinstance(receipt, dict):
        raise CBlocked("C_RECEIPT_NOT_OBJECT")
    for key, value in (
        ("source_url", source_url), ("response_final_url", source_url),
        ("hazard", hazard), ("hazard_dataset", HAZARDS[hazard][2]),
        ("expected_hazard_attribute", HAZARDS[hazard][1]),
        ("tile", tile), ("source_sha256", digest), ("source_bytes", len(raw)),
        ("archive_feature_count", count), ("http_status", 200),
        ("acquisition_status", "LOCAL_ARCHIVE_RECEIVED"),
        ("acquisition_method", "DIRECT_OFFICIAL_HTTPS_GET"),
        ("status", "H0_LOCAL_STRUCTURE_ONLY" if count else "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF"),
        ("source_origin", "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED"),
        ("official_https_byte_replay", "NOT_RUN"),
        ("independent_c_acceptance", "NOT_GRANTED"),
        ("publication_approval", "NOT_GRANTED"),
    ):
        _exact(receipt, key, value, "C_D_RECEIPT_MISMATCH")
    for key, value in (
        ("source_raw_sha256", digest), ("source_bytes", len(raw)),
        ("tile_wide_feature_count", count),
        ("retrieved_at_utc", receipt.get("retrieved_at_utc")),
    ):
        _exact(row, key, value, "C_D_REPORT_MISMATCH")
    when = receipt.get("retrieved_at_utc")
    if not _utc(when):
        raise CBlocked("C_RECEIPT_TIME_INVALID")
    if datetime.fromisoformat(when.replace("Z", "+00:00")) > checked_at + timedelta(minutes=5):
        raise CBlocked("C_RECEIPT_TIME_IN_FUTURE")
    return raw


def _no_redirect_http(source_url: str) -> tuple[bytes, int, str]:
    """One direct, TLS-validated, non-redirected GET for an allowlisted URL."""
    from urllib.parse import urlsplit
    u = urlsplit(source_url)
    if (u.scheme != "https" or u.netloc != "cyberjapandata.gsi.go.jp"
            or u.query or u.fragment):
        raise CBlocked("C_SOURCE_URL_FORBIDDEN")
    opener = build_opener(ProxyHandler({}), _NoRedirect(),
                          HTTPSHandler(context=ssl.create_default_context()))
    request = Request(source_url, method="GET", headers={
        "Accept": "application/geo+json, application/json, */*",
        "Cache-Control": "no-cache",
        "User-Agent": "HINANEX-C-R0-independent-replay/1.0",
    })
    try:
        with opener.open(request, timeout=25) as response:
            return response.read(MAX_RAW_BYTES + 1), response.status, response.geturl()
    except HTTPError as exc:
        raise CBlocked(f"C_HTTP_ERROR:{exc.code}") from None
    except (URLError, TimeoutError, socket.gaierror, ssl.SSLError, OSError) as exc:
        cause = exc.reason if isinstance(exc, URLError) else exc
        if isinstance(cause, socket.gaierror):
            why = "C_DNS_FAILURE"
        elif isinstance(cause, (TimeoutError, socket.timeout)):
            why = "C_CONNECTION_TIMEOUT"
        elif isinstance(cause, ssl.SSLError):
            why = "C_TLS_FAILURE"
        else:
            why = "C_NETWORK_FAILURE"
        raise CBlocked(why) from None


def check_four_cells(
    report: dict,
    *,
    evidence_dir: Path,
    replay_https: bool = False,
    fetch=None,
    clock=lambda: datetime.now(timezone.utc),
) -> dict:
    """Technical checks only. Successful byte equality never sets approval."""
    rows = validate_r0_report(report)
    if type(replay_https) is not bool:
        raise CBlocked("C_REPLAY_OPT_IN_MUST_BE_BOOLEAN")
    if (not isinstance(evidence_dir, Path) or not evidence_dir.is_absolute()
            or not evidence_dir.is_dir()):
        raise CBlocked("C_EVIDENCE_DIR_INVALID")
    where = evidence_dir.resolve(strict=True)
    if where.is_relative_to(Path(__file__).resolve().parents[2]):
        raise CBlocked("C_EVIDENCE_MUST_REMAIN_OUTSIDE_GIT")
    checked_at = clock()
    if (not isinstance(checked_at, datetime) or checked_at.tzinfo is None
            or checked_at.utcoffset() != timedelta(0)):
        raise CBlocked("C_CHECK_CLOCK_MUST_BE_UTC")
    transport = fetch if fetch is not None else _no_redirect_http
    out, local_matches, byte_matches = [], 0, 0
    for row in rows:
        entry = {
            "slot": row["slot"], "tile": row["tile"],
            "hazard": row["hazard"], "source_url": row["source_url"],
            "status": "C_NOT_ACQUIRED_HOLD",
            "reason": "D_CELL_NOT_CAPTURED",
            "d_raw_sha256_recomputed": None, "c_https_sha256": None,
            "tile_wide_feature_count": None,
            "https_byte_match": None, "c_https_replay": "NOT_RUN",
            "c_independent_approved": False, "human_review": "DEFERRED",
            "municipal_coverage_verified": False, "facility_identity_approved": False,
            "hazard_safety_verified": False, "publication_approved": False,
        }
        if row["capture_status"] not in CAPTURED:
            out.append(entry)
            continue
        try:
            raw = verify_local_cell(row, evidence_dir=where, checked_at=checked_at)
            entry["d_raw_sha256_recomputed"] = sha256(raw).hexdigest()
            entry["tile_wide_feature_count"] = row["tile_wide_feature_count"]
            entry.update(status="C_LOCAL_RAW_MATCH_UNAPPROVED",
                         reason="HTTPS_REPLAY_NOT_REQUESTED")
            local_matches += 1
            if replay_https:
                replay_raw, status, final_url = transport(row["source_url"])
                if type(status) is not int or status != 200:
                    raise CBlocked("C_REPLAY_HTTP_NOT_200")
                if final_url != row["source_url"]:
                    raise CBlocked("C_REPLAY_FINAL_URL_MISMATCH")
                replay_digest, replay_count = inspect_c_raw(
                    replay_raw, hazard=row["hazard"], tile=row["tile"])
                entry["c_https_sha256"] = replay_digest
                entry["c_https_replay"] = "REPLAY_COMPLETED"
                if raw == replay_raw:
                    byte_matches += 1
                    entry.update(
                        status=("C_HTTPS_BYTE_MATCH_UNAPPROVED" if replay_count
                                else "C_EMPTY_TILE_BYTE_MATCH_COVERAGE_UNKNOWN"),
                        reason="BYTE_MATCH_IS_NOT_APPROVAL",
                        https_byte_match=True,
                    )
                else:
                    entry.update(status="C_SOURCE_CHANGED_OR_MISMATCH_HOLD",
                                 reason="DIFFERENT_BYTES_OR_SOURCE_REVISION",
                                 https_byte_match=False)
        except (CBlocked, OSError, TypeError, UnicodeError, ValueError) as exc:
            entry.update(
                status="C_EVIDENCE_OR_REPLAY_HOLD",
                reason=str(exc) if isinstance(exc, CBlocked) else "C_IO_OR_JSON_FAILURE",
                c_https_replay="HOLD" if replay_https else "NOT_RUN",
            )
        out.append(entry)
    if byte_matches == 4:
        status = "R0_C_FOUR_HTTPS_BYTE_MATCHES_UNAPPROVED"
    elif local_matches == 4 and not replay_https:
        status = "R0_C_FOUR_LOCAL_MATCHES_UNAPPROVED"
    else:
        status = "R0_C_PARTIAL_OR_MISMATCH_HOLD"
    return {
        "status": status, "schema": "hinanex.c.gsi_r0_four_cell_replay.v0.1",
        "checked_at_utc": checked_at.isoformat(timespec="seconds"),
        "matrix_kind": MATRIX_KIND,
        "cells_total": 4, "local_raw_matches": local_matches,
        "https_byte_matches": byte_matches,
        "https_replay_explicitly_requested": replay_https,
        "cells_independently_approved": 0,
        "pilot_b_geographically_distant_verified": False,
        "municipal_boundary_verified": False,
        "official_source_signed": False,
        "human_review": "DEFERRED_TO_HUMAN_BATCH_REVIEW",
        "publication_approved": False,
        "note": ("A/B are tile positions, not verified regions. Byte equality is not "
                 "facility identity, municipality coverage, hazard safety or permission to publish."),
        "cells": out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d-report", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--replay-https", action="store_true",
                        help="Explicit opt-in: independent GSI HTTPS GET for each captured cell")
    parser.add_argument("--report-out", type=Path,
                        help="Optional new report path outside Git; never overwrite")
    args = parser.parse_args()
    try:
        if (not args.d_report.is_file() or args.d_report.stat().st_size > MAX_REPORT_BYTES):
            raise CBlocked("C_D_REPORT_MISSING_OR_OVERSIZED")
        report = _load_json(args.d_report.read_bytes())
        if args.report_out is not None:
            target = args.report_out
            if (not target.is_absolute() or not target.parent.is_dir()
                    or target.exists()
                    or target.resolve(strict=False).is_relative_to(
                        Path(__file__).resolve().parents[2])):
                raise CBlocked("C_REPORT_OUTPUT_MUST_BE_NEW_OUTSIDE_GIT")
        result = check_four_cells(
            report, evidence_dir=args.evidence_dir, replay_https=args.replay_https)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report_out is not None:
            with args.report_out.open("x", encoding="utf-8") as dst:
                dst.write(output)
        print(output, end="")
        return 0 if result["status"] in (
            "R0_C_FOUR_LOCAL_MATCHES_UNAPPROVED",
            "R0_C_FOUR_HTTPS_BYTE_MATCHES_UNAPPROVED",
        ) else 3
    except (CBlocked, OSError, ValueError, TypeError) as exc:
        print("C_R0_FOUR_CELL_HOLD: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
