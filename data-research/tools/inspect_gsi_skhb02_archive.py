"""A-only offline inspection of *archived* GSI skhb02 emergency-place tiles.

Uses official tile/schema naming but does not perform network acquisition.
Feature counts from one tile are NOT municipal coverage. This is NOT a
landslide risk polygon, a shelter opening status, or a safe destination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

GSI_REFERENCE = "https://maps.gsi.go.jp/development/ichiran.html"
GSI_ORIGIN = "cyberjapandata.gsi.go.jp"
TILE_PATH = re.compile(r"^/xyz/skhb02/10/([0-9]{1,4})/([0-9]{1,4})\.geojson$")
MAX_ARCHIVE_BYTES = 12_000_000


class GsiLandslideInspectionError(ValueError):
    pass


def validate_source_url(source_url: str) -> tuple[int, int]:
    if not isinstance(source_url, str) or "\\" in source_url or any(
        c.isspace() for c in source_url
    ):
        raise GsiLandslideInspectionError("invalid GSI URL")
    url = urlsplit(source_url)
    if (
        url.scheme != "https" or url.hostname != GSI_ORIGIN
        or url.username is not None or url.password is not None
        or url.query or url.fragment
    ):
        raise GsiLandslideInspectionError("not exact official GSI skhb02 URL")
    try:
        if url.port not in (None, 443):
            raise GsiLandslideInspectionError("unexpected GSI URL port")
    except ValueError as exc:
        raise GsiLandslideInspectionError("invalid GSI URL port") from exc
    m = TILE_PATH.fullmatch(url.path)
    if not m:
        raise GsiLandslideInspectionError("skhb02 z10 tile required")
    x, y = (int(v) for v in m.groups())
    if not (0 <= x < 1024 and 0 <= y < 1024):
        raise GsiLandslideInspectionError("z10 tile coordinate out of range")
    return x, y


def _point_tile(lon: float, lat: float) -> tuple[int, int]:
    """Use z10 Web Mercator; checking a tile is not municipal membership."""
    if not (-180 <= lon < 180 and -85.05112878 < lat < 85.05112878):
        raise GsiLandslideInspectionError("point cannot be projected")
    return (
        math.floor((lon + 180) * 1024 / 360),
        math.floor(
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) * 1024 / 2
        ),
    )


def inspect_archived_tile(raw: bytes, source_url: str) -> dict:
    """Fail closed on malformed input; return no suitability/candidate data."""
    x, y = validate_source_url(source_url)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
        raise GsiLandslideInspectionError("source bytes missing or over limit")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GsiLandslideInspectionError("not valid source GeoJSON") from exc
    if (
        not isinstance(data, dict) or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
    ):
        raise GsiLandslideInspectionError("expected FeatureCollection")
    inspected = []
    for index, feature in enumerate(data["features"]):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise GsiLandslideInspectionError("invalid source feature")
        p, g = feature.get("properties"), feature.get("geometry")
        if (
            not isinstance(p, dict) or not isinstance(g, dict)
            or g.get("type") != "Point"
        ):
            raise GsiLandslideInspectionError("expected Point and properties")
        coords = g.get("coordinates")
        if not isinstance(coords, list) or len(coords) not in (2, 3):
            raise GsiLandslideInspectionError("invalid point coordinates")
        lon, lat = coords[:2]
        if any(
            type(value) not in (float, int)
            or not math.isfinite(value)
            or not minimum <= value <= maximum
            for value, minimum, maximum in ((lon, -180, 180), (lat, -90, 90))
        ):
            raise GsiLandslideInspectionError("invalid GSI point")
        if type(p.get("disaster2")) is not int or p["disaster2"] != 1:
            raise GsiLandslideInspectionError(
                "skhb02 is not verified disaster2=1 designation"
            )
        if not isinstance(p.get("name"), str) or not p["name"].strip():
            raise GsiLandslideInspectionError("GSI name missing")
        for key in ("address", "remarks"):
            if p.get(key) is not None and not isinstance(p[key], str):
                raise GsiLandslideInspectionError("invalid source text")
        if _point_tile(lon, lat) != (x, y):
            raise GsiLandslideInspectionError("point outside source z10 tile")
        inspected.append({
            "feature_index": index,
            "name_raw": p["name"],
            "address_raw": p.get("address"),
            "remarks_raw": p.get("remarks"),
            "coordinates_raw": coords,
            "disaster2_raw": p["disaster2"],
            "source_feature_ref": f"{source_url}#feature_index={index}",
            "not_current_open_or_safe": True,
            "not_a_cross_source_facility_identity": True,
        })
    return {
        "status": "SOURCE_TILE_INSPECTED_UNREVIEWED" if inspected else
                  "TILE_EMPTY_MUNICIPAL_COVERAGE_UNKNOWN",
        "purpose": "A_SKH B02_SOURCE_FEASIBILITY_ONLY".replace(" ", ""),
        "source_url": source_url,
        "official_schema_documentation": GSI_REFERENCE,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_byte_count": len(raw),
        "source_tile": {"z": 10, "x": x, "y": y},
        "source_feature_count": len(inspected),
        "raw_feature_previews_for_human_review": inspected,
        "hazard": "landslide",
        "official_attribute": "disaster2",
        "source_kind": "designated_emergency_evacuation_place",
        "not_a_landslide_risk_layer": True,
        "municipal_coverage_verified": False,
        "municipal_site_opening_verified": False,
        "independent_c_approved": False,
        "safe_destination_count_approved": 0,
        "not_for_publication": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()
    try:
        if not args.archive.is_file() or args.archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise GsiLandslideInspectionError("archive absent or oversized")
        report = inspect_archived_tile(args.archive.read_bytes(), args.source_url)
    except (OSError, GsiLandslideInspectionError) as exc:
        parser.exit(2, f"A skhb02 inspection blocked: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
