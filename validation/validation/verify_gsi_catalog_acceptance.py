"""Read-only real-data acceptance gate for C -> D -> E GSI flood reference catalog.

This deliberately imports the D provider to verify cross-role contract compatibility;
C's independent raw audit itself still does NOT import D.
A successful result proves local consistency only, not a live-browser or safety review.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import asinh, floor, isfinite, pi, radians, tan
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from src.hinanex.flood_site_reference import build_flood_site_catalog
from run_verified_flood_site_reference import require_provenance
from verify_gsi_flood_source import verify_gsi_flood_source

TILE_URL = re.compile(
    r"^https://cyberjapandata\.gsi\.go\.jp/xyz/skhb01/(\d+)/(\d+)/(\d+)\.geojson$"
)


def _tile_for_coordinate(latitude: object, longitude: object, zoom: int):
    if (
        type(latitude) not in (int, float)
        or type(longitude) not in (int, float)
        or not isfinite(latitude) or not isfinite(longitude)
        or abs(latitude) > 85.05112878 or not -180 <= longitude <= 180
    ):
        return None
    n = 2 ** zoom
    x = min(n - 1, max(0, floor((longitude + 180) / 360 * n)))
    y = floor((1 - asinh(tan(radians(latitude))) / pi) / 2 * n)
    return (x, min(n - 1, max(0, y)))


def verify_local_catalog(raw: bytes, rows: list[dict], acceptance: dict,
                         provenance: dict, catalog: dict, source_url: str,
                         region_code: str = "13123") -> dict:
    """Independently assert original archive, C manifest, D output and E tiles."""
    if region_code not in ("13123", "15100", "23100"):
        raise ValueError("unsupported verified tile search context")
    if not isinstance(catalog, dict):
        raise ValueError("catalog JSON object required")
    independent_c = verify_gsi_flood_source(raw, rows, source_url, region_code)
    if acceptance != independent_c:
        raise ValueError("C manifest differs from freshly recomputed independent raw audit")
    require_provenance(raw, rows, acceptance, provenance, region_code)
    expected_catalog = build_flood_site_catalog(
        region_code, rows, raw_archive=raw, c_acceptance=acceptance,
    )
    if expected_catalog["status"] != "REFERENCE_ONLY":
        raise ValueError("D reference catalog remains blocked")
    expected_catalog["https_provenance_status"] = "MATCH"
    expected_catalog["https_provenance_checked_at_utc"] = provenance["retrieved_at_utc"]
    if catalog != expected_catalog:
        raise ValueError("published JSON differs from independently accepted D export")

    tile_match = TILE_URL.fullmatch(source_url)
    if not tile_match:
        raise ValueError("not a single official skhb01 tile URL")
    z, x, y = map(int, tile_match.groups())
    if z != 10 or not 0 <= x < 2 ** z or not 0 <= y < 2 ** z:
        raise ValueError("invalid official GSI tile coordinates")
    for index, site in enumerate(catalog["sites"]):
        if site["source_url"] != source_url:
            raise ValueError("mixed-tile source rows are not supported by current E consumer")
        if _tile_for_coordinate(site["latitude"], site["longitude"], z) != (x, y):
            raise ValueError(f"site {index} coordinate is outside the archived tile")

    return {
        "status": "LOCAL_CATALOG_CONTRACT_PASS",
        "catalog_kind": catalog["catalog_kind"],
        "source_url": source_url,
        "search_context_region_code": region_code,
        "tile_wide_feature_count": len(rows),
        "raw_sha256": sha256(raw).hexdigest(),
        "c_audit_reference": acceptance["audit_reference"],
        "https_byte_replay_checked_at_utc": provenance["retrieved_at_utc"],
        "limitations": [
            "This verifies local archive/C/provenance-report/D-catalog consistency only.",
            "HTTPS provenance MATCH was recorded separately; this tool does not contact GSI.",
            "Tile-wide records are not a municipality-specific count or completeness proof.",
            "Browser, GPS permission, municipality membership and evacuation suitability still require separate checks.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--c-acceptance", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--region", default="13123")
    args = parser.parse_args()
    try:
        report = verify_local_catalog(
            args.raw.read_bytes(),
            json.loads(args.records.read_text(encoding="utf-8")),
            json.loads(args.c_acceptance.read_text(encoding="utf-8")),
            json.loads(args.provenance.read_text(encoding="utf-8")),
            json.loads(args.catalog.read_text(encoding="utf-8")),
            args.source_url, args.region,
        )
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"LOCAL CATALOG CONTRACT NOT VERIFIED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
