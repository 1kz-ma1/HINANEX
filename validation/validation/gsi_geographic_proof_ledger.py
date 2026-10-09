"""Read-only, local C proof ledger for GSI flood z10 source coverage.

This is an evidence inventory, NOT a fresh HTTPS replay, browser acceptance,
municipal completeness, route evaluation or evacuation suitability score.

Usage (from repository root):
    python validation/validation/gsi_geographic_proof_ledger.py \
        --region 13123 --origin 35.70,139.90 --origin 35.70,140.10

All required raw bytes, saved C audit, HTTPS MATCH report and published
reference JSON must already exist in this worktree. No data is downloaded,
rewritten, deleted or published by this command.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from verify_gsi_catalog_acceptance import _tile_for_coordinate, verify_local_catalog

ROOT = Path(__file__).resolve().parents[2]
Z = 10
REGIONS = frozenset({"13123", "15100", "23100"})
SOURCE_BASE = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10"
MANUAL_GATES = (
    "live_browser_region_gsi_both_modes",
    "browser_two_distinct_origin_tiles",
    "gps_permission_and_denial_fallback",
    "external_flood_raster_network_status",
    "municipal_source_unknowns_and_missing_geometry",
    "demo_rehearsal_and_release_review",
)


def origin_tile(value: str) -> tuple[int, int]:
    try:
        coords = value.split(",")
        if len(coords) != 2:
            raise ValueError("latitude,longitude pair required")
        latitude, longitude = (float(part.strip()) for part in coords)
    except (ValueError, TypeError) as exc:
        raise ValueError("origin must be LATITUDE,LONGITUDE") from exc
    tile = _tile_for_coordinate(latitude, longitude, Z)
    if tile is None:
        raise ValueError("origin is outside valid GSI Web Mercator coordinates")
    return tile


def nearby_tiles(x: int, y: int) -> list[tuple[int, int]]:
    """Origin first, then the eight bounded z10 neighbors, as the E client does."""
    n = 1 << Z
    tiles = [(x, y)]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            ny = y + dy
            if 0 <= ny < n:
                tiles.append(((x + dx) % n, ny))
    return tiles


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _digest_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def verify_tile(
    x: int, y: int, region: str, published_root: Path,
    evidence_root: Path, raw_root: Path,
) -> dict:
    """Check published bytes against independently recomputed archived C proof."""
    name = f"10-{x}-{y}"
    url = f"{SOURCE_BASE}/{x}/{y}.geojson"
    public = published_root / region / f"{name}.json"
    item = {"tile": f"10/{x}/{y}", "status": "MISSING_PUBLICATION"}
    if not public.is_file():
        return item

    try:
        published_bytes = public.read_bytes()
        catalog = json.loads(published_bytes)
        if not isinstance(catalog, dict):
            raise ValueError("published catalog is not a JSON object")
        raw_sha = catalog.get("source_raw_sha256")
        if not isinstance(raw_sha, str) or len(raw_sha) != 64:
            raise ValueError("missing valid published raw digest")
        # Do not trust a catalog's self-asserted C_ACCEPTED flag alone.
        matching_evidence = [
            directory for directory in sorted(evidence_root.glob("*/"))
            if (directory / "gsi_flood_site_catalog.json").is_file()
            and _digest_file(directory / "gsi_flood_site_catalog.json")
            == sha256(published_bytes).hexdigest()
        ]
        if len(matching_evidence) != 1:
            item["status"] = "UNVERIFIED_C_EVIDENCE"
            return item

        proof_dir = matching_evidence[0]
        requirements = {
            "records": proof_dir / "gsi_records.json",
            "acceptance": proof_dir / "c_raw_acceptance.json",
            "provenance": proof_dir / "c_https_provenance.json",
        }
        if not all(path.is_file() for path in requirements.values()):
            item["status"] = "UNVERIFIED_C_EVIDENCE"
            return item

        raw_candidates = [
            path for path in sorted(raw_root.rglob(f"{name}.geojson"))
            if path.is_file() and _digest_file(path).lower() == raw_sha.lower()
        ]
        if not raw_candidates:
            item["status"] = "UNVERIFIED_RAW_ARCHIVE"
            return item

        raw = raw_candidates[0].read_bytes()
        result = verify_local_catalog(
            raw, _json(requirements["records"]),
            _json(requirements["acceptance"]),
            _json(requirements["provenance"]),
            catalog, url, region,
        )
        item.update({
            "status": "PASS_SAVED_C_EVIDENCE",
            "tile_wide_feature_count": result["tile_wide_feature_count"],
            "raw_sha256": result["raw_sha256"],
            "c_audit_reference": result["c_audit_reference"],
            "saved_https_replay_at_utc": result["https_byte_replay_checked_at_utc"],
        })
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        item["status"] = "BLOCKED_INCONSISTENT"
        item["reason"] = str(exc)[:260]
    return item


def build_report(
    region: str, origins: list[str], published_root: Path,
    evidence_root: Path, raw_root: Path,
) -> dict:
    if region not in REGIONS:
        raise ValueError("unsupported search context; not proof of municipal membership")
    if not origins:
        raise ValueError("at least one explicit origin is required")
    if len(origins) > 4:
        raise ValueError("limit each review to four explicitly selected origins")
    centers = [origin_tile(point) for point in origins]
    cached: dict[tuple[int, int], dict] = {}
    checks = []
    for center in centers:
        keys = nearby_tiles(*center)
        for key in keys:
            if key not in cached:
                cached[key] = verify_tile(
                    *key, region, published_root, evidence_root, raw_root
                )
        verified = [cached[key] for key in keys
                    if cached[key]["status"] == "PASS_SAVED_C_EVIDENCE"]
        checks.append({
            "origin_tile": f"10/{center[0]}/{center[1]}",
            "status": (
                "ORIGIN_UNVERIFIED" if cached[center]["status"] != "PASS_SAVED_C_EVIDENCE"
                else "FULL_LOCAL_SOURCE_PROOF" if len(verified) == len(keys)
                else "PARTIAL_LOCAL_SOURCE_PROOF"
            ),
            "source_tiles_verified": len(verified),
            "source_tiles_requested": len(keys),
            "tile_wide_feature_count": sum(
                tile["tile_wide_feature_count"] for tile in verified
            ),
            "tiles": [dict(cached[key]) for key in keys],
        })
    distinct = len(set(centers)) == len(centers) and len(centers) >= 2
    all_sources = all(x["status"] == "FULL_LOCAL_SOURCE_PROOF" for x in checks)
    return {
        "schema": "HINANEX_C_GSI_LOCAL_PROOF_LEDGER_V1",
        "status": "READ_ONLY_SOURCE_EVIDENCE_INVENTORY",
        "region_context": region,
        "hazard_namespace": "GSI_SKHB01_FLOOD",
        "origin_checks": checks,
        "distinct_origin_tiles_sampled": distinct,
        "all_requested_source_tiles_locally_verified": all_sources,
        "manual_gate_status": {name: "NOT_TESTED" for name in MANUAL_GATES},
        "baseline_accepted": False,
        "limitations": [
            "PASS means recomputed archived raw/C/D agreement with a saved HTTPS MATCH report; no new network replay.",
            "GSI z10 source tiles are not municipality boundaries or municipal counts.",
            "MISSING_PUBLICATION/UNVERIFIED is not evidence that there are no designated sites.",
            "Manual browser, GPS, raster availability, safety, opening status, and routes are NOT tested.",
            "This flood-only report does not validate other disaster types or a two-dimensional matrix.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=sorted(REGIONS), default="13123")
    parser.add_argument("--origin", required=True, action="append",
                        help="Latitude,Longitude; repeat for different z10 origin tiles")
    parser.add_argument("--published-root", type=Path, default=ROOT /
                        "pipeline/data/output/gsi_verified_tiles")
    parser.add_argument("--evidence-root", type=Path, default=ROOT /
                        "pipeline/data/verified/gsi-acceptance-runs")
    parser.add_argument("--raw-root", type=Path, default=ROOT /
                        "pipeline/data/raw/gsi-demo-runs")
    parser.add_argument("--report-out", type=Path,
                        help="Optional new JSON output. Never overwrites an existing report.")
    args = parser.parse_args()
    try:
        if args.report_out and args.report_out.exists():
            raise ValueError("report-out already exists; preserved evidence must not be overwritten")
        report = build_report(
            args.region, args.origin, args.published_root,
            args.evidence_root, args.raw_root,
        )
        formatted = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report_out:
            # Exclusive create, no implicit directories / accidental overwrite.
            with args.report_out.open("x", encoding="utf-8") as output:
                output.write(formatted)
        print(formatted, end="")
        return 0
    except (OSError, ValueError) as exc:
        print(f"GSI PROOF LEDGER NOT RUN: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
