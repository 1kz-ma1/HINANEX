"""Build-time, source-verified GSI flood reference publication for staging.

E accepts only C/HTTPS-accepted GSI skhb01 z10 catalogs. This shared staging
step publishes exactly one pinned, independently checked *reference-only* tile
from official bytes without committing raw or generated outputs to Git.

No municipal affiliation, availability, safety or D-facility pairing is inferred.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
# The existing D and C routines are retained as independent implementation
# gates; D creates rows, C parses raw GeoJSON independently and performs a
# second official HTTPS byte-replay before the full C→D→E contract check.
for subdir in ("pipeline", "validation/validation"):
    target = str(ROOT / subdir)
    if target not in sys.path:
        sys.path.insert(0, target)

from src.hinanex.flood_site_reference import (  # noqa: E402
    build_flood_site_catalog, extract_gsi_flood_tile,
)
from run_verified_flood_site_reference import require_provenance  # noqa: E402
from verify_gsi_flood_source import verify_gsi_flood_source  # noqa: E402
from verify_gsi_flood_provenance import verify_https_provenance  # noqa: E402
from verify_gsi_catalog_acceptance import verify_local_catalog  # noqa: E402

# Scope pinned by the existing A/C local acceptance documentation. The z10
# cell is a geographic SOURCE tile and may contain sites outside Edogawa.
# New tiles/regions must receive explicit A/C review; no map-center guesses.
GSI_DEMO_TILES = (("13123", 10, 909, 403),)
MAX_BYTES = 16 * 1024 * 1024


class GsiPublicationBlocked(ValueError):
    """No independently validated official tile may be published."""


def official_source_url(z: int, x: int, y: int) -> str:
    if type(z) is not int or z != 10 or type(x) is not int or type(y) is not int:
        raise GsiPublicationBlocked("only explicitly approved z10 coordinates are supported")
    if not 0 <= x < 2 ** z or not 0 <= y < 2 ** z:
        raise GsiPublicationBlocked("GSI tile coordinates outside permitted range")
    return f"https://cyberjapandata.gsi.go.jp/xyz/skhb01/{z}/{x}/{y}.geojson"


def fetch_official_tile(source_url: str, *, opener=urlopen) -> bytes:
    """Use exact HTTPS official origin, strict status/redirect and byte cap."""
    request = Request(source_url, headers={
        "Accept": "application/geo+json, application/json, */*;q=0.1",
        "Cache-Control": "no-cache",
        "User-Agent": "HINANEX-Shared-GSI-Reference-Staging/1.0",
    })
    with opener(request, timeout=30) as response:
        status = response.getcode()
        final_url = response.geturl()
        raw = response.read(MAX_BYTES + 1)
    if status != 200 or final_url != source_url or not 0 < len(raw) <= MAX_BYTES:
        raise GsiPublicationBlocked("exact GSI HTTPS bytes were not retrieved")
    return raw


def build_official_reference_tile(
    output_dir: Path, *, region_code: str, z: int, x: int, y: int,
    opener=urlopen,
) -> dict:
    """Re-fetch official bytes, run independent C+HTTPS acceptance and publish.

    Writes nothing before all gates pass. Any failure leaves no staged JSON,
    and an existing staged tile is never overwritten.
    """
    if (region_code, z, x, y) not in GSI_DEMO_TILES:
        raise GsiPublicationBlocked("unreviewed GSI region/tile cannot be published")
    source_url = official_source_url(z, x, y)
    raw = fetch_official_tile(source_url, opener=opener)
    rows = extract_gsi_flood_tile(raw, source_url, region_code)
    c_acceptance = verify_gsi_flood_source(raw, rows, source_url, region_code)
    # Real second HTTPS request, not a self-attested MATCH string.
    provenance = verify_https_provenance(
        raw, source_url, c_acceptance, opener=opener,
    )
    require_provenance(raw, rows, c_acceptance, provenance, region_code)
    catalog = build_flood_site_catalog(
        region_code, rows, raw_archive=raw, c_acceptance=c_acceptance,
    )
    if catalog.get("status") != "REFERENCE_ONLY":
        raise GsiPublicationBlocked("C-accepted D catalog is not REFERENCE_ONLY")
    catalog["https_provenance_status"] = "MATCH"
    catalog["https_provenance_checked_at_utc"] = provenance["retrieved_at_utc"]
    verified = verify_local_catalog(
        raw, rows, c_acceptance, provenance, catalog, source_url, region_code,
    )
    if verified["status"] != "LOCAL_CATALOG_CONTRACT_PASS":
        raise GsiPublicationBlocked("independent C→D→E catalog check refused tile")
    if sha256(raw).hexdigest() != verified["raw_sha256"]:
        raise GsiPublicationBlocked("raw digest changed after independent acceptance")

    path = Path(output_dir) / region_code / f"{z}-{x}-{y}.json"
    if path.exists():
        raise GsiPublicationBlocked("refusing to overwrite an already published GSI tile")
    path.parent.mkdir(parents=True, exist_ok=True)
    # A new bundle directory is private until Render publishes it; still
    # write atomically so partial outputs cannot be mistaken for acceptance.
    staged = path.with_suffix(".json.tmp")
    if staged.exists():
        raise GsiPublicationBlocked("stale temporary GSI publication file exists")
    try:
        with staged.open("x", encoding="utf-8") as stream:
            json.dump(catalog, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(staged, path)
    finally:
        if staged.exists():
            staged.unlink()
    return {
        "status": "C_AND_HTTPS_VERIFIED_REFERENCE_ONLY",
        "source": "GSI_SKHB01_FLOOD",
        "source_url": source_url,
        "region_search_context": region_code,
        "tile": f"{z}/{x}/{y}",
        "official_raw_sha256": verified["raw_sha256"],
        "verified_at_utc": provenance["retrieved_at_utc"],
        "tile_wide_source_records": verified["tile_wide_feature_count"],
        "relative_public_path":
            f"pipeline/data/output/gsi_verified_tiles/{region_code}/{z}-{x}-{y}.json",
        "scope_note": (
            "One independently accepted source tile; includes other municipalities. "
            "Not a current safety/open-status or evacuation recommendation."
        ),
    }
