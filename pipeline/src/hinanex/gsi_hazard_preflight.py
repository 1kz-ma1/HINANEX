"""H0 offline GSI skhb01/skhb02 raw-source structural preflight.

This is NOT a Source->Export acceptance, C HTTPS byte replay, municipality
coverage assessment, safety determination, or publication authorization.
No network, coordinate derivation, source joining, output feature catalog,
or changes to the existing skhb01 publication pipeline.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sys

# Source: GSI official tile list https://maps.gsi.go.jp/help/use.html
# Do not infer any other disaster designation from an adjacent GSI layer.
_HAZARDS = {
    "flood": ("skhb01", "disaster1", "GSI_SKHB01_FLOOD"),
    "landslide": ("skhb02", "disaster2", "GSI_SKHB02_LANDSLIDE"),
}
_TILE_URL = re.compile(
    r"https://cyberjapandata\.gsi\.go\.jp/xyz/"
    r"(skhb01|skhb02)/10/([0-9]{1,4})/([0-9]{1,4})\.geojson\Z"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_BYTES = 20 * 1024 * 1024
_MAX_FEATURES = 50000


def _check_utc(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:\+00:00|Z)", value
    ):
        raise ValueError("retrieved_at_utc must be an explicit UTC ISO 8601 timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("retrieved_at_utc is not a valid datetime") from exc
    if dt.utcoffset() != timedelta(0):
        raise ValueError("retrieved_at_utc must be UTC")


def _check_url(source_url: str, hazard: str) -> tuple[int, int, str, str]:
    if not isinstance(hazard, str) or hazard not in _HAZARDS:
        raise ValueError("unsupported hazard; choose flood or landslide explicitly")
    layer, attribute, dataset = _HAZARDS[hazard]
    if not isinstance(source_url, str):
        raise ValueError("source_url must be an exact official GSI tile URL")
    match = _TILE_URL.fullmatch(source_url)
    if not match or match.group(1) != layer:
        raise ValueError("source URL does not match the requested hazard's GSI layer")
    x, y = int(match.group(2)), int(match.group(3))
    # GSI designated-emergency-site GeoJSON is a z=10 tile.
    if x >= 1024 or y >= 1024:
        raise ValueError("GSI z10 tile x/y out of range")
    expected = f"https://cyberjapandata.gsi.go.jp/xyz/{layer}/10/{x}/{y}.geojson"
    if source_url != expected:
        raise ValueError("GSI tile URL is not canonical")
    return x, y, attribute, dataset


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate keys in archived GeoJSON")
        obj[key] = value
    return obj


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant {value}")


def _valid_number(value: object, minimum: float, maximum: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and minimum <= value <= maximum
    )


def preflight_gsi_tile(
    raw_archive: bytes,
    *,
    source_url: str,
    hazard: str,
    expected_sha256: str,
    retrieved_at_utc: str,
) -> dict:
    """Check an explicitly supplied local *archived* tile without accepting it.

    A caller-provided SHA-256 matching the local bytes is not independent GSI
    source authentication. Nonempty/empty results are never proof of regional
    coverage or facility opening/safety. Every malformed source feature fails
    the entire inspection instead of skipping inconvenient rows.
    """
    x, y, attribute, dataset = _check_url(source_url, hazard)
    _check_utc(retrieved_at_utc)
    if not isinstance(raw_archive, bytes) or not (0 < len(raw_archive) <= _MAX_BYTES):
        raise ValueError("raw_archive must be a nonempty bounded local byte archive")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be an explicit lowercase SHA-256 digest")
    actual_hash = sha256(raw_archive).hexdigest()
    if actual_hash != expected_sha256:
        raise ValueError("local archived bytes do not match expected SHA-256")
    try:
        doc = json.loads(
            raw_archive.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 GSI FeatureCollection archive") from exc
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise ValueError("GSI archive must be a GeoJSON FeatureCollection")
    features = doc.get("features")
    if not isinstance(features, list) or len(features) > _MAX_FEATURES:
        raise ValueError("GeoJSON features must be a bounded array")
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"feature {i} is not a GeoJSON Feature")
        props, geometry = feature.get("properties"), feature.get("geometry")
        if not isinstance(props, dict) or not isinstance(geometry, dict):
            raise ValueError(f"feature {i} lacks properties or geometry")
        if type(props.get(attribute)) is not int or props[attribute] != 1:
            raise ValueError(f"feature {i} lacks exact {attribute}=1 for {hazard}")
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            raise ValueError(f"feature {i} has no source name")
        for raw_field in ("address", "remarks"):
            if props.get(raw_field) is not None and not isinstance(props[raw_field], str):
                raise ValueError(f"feature {i} has invalid {raw_field}")
        if geometry.get("type") != "Point":
            raise ValueError(f"feature {i} has unverified GeoJSON geometry")
        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) not in (2, 3):
            raise ValueError(f"feature {i} has invalid Point coordinate array")
        longitude, latitude = coords[:2]
        if not _valid_number(longitude, -180, 180) or not _valid_number(latitude, -90, 90):
            raise ValueError(f"feature {i} has invalid coordinate values")
        if len(coords) == 3 and not _valid_number(coords[2], -100000, 100000):
            raise ValueError(f"feature {i} has invalid altitude")
    return {
        "status": "H0_LOCAL_STRUCTURE_ONLY" if features else "H0_EMPTY_ARCHIVE_NOT_COVERAGE_PROOF",
        "provider": "GSI",
        "hazard": hazard,
        "hazard_dataset": dataset,
        "expected_hazard_attribute": attribute,
        "source_url": source_url,
        "tile": {"z": 10, "x": x, "y": y},
        "retrieved_at_utc": retrieved_at_utc,
        "source_sha256": actual_hash,
        "source_bytes": len(raw_archive),
        "archive_feature_count": len(features),
        "source_origin": "LOCAL_INPUT_NOT_CRYPTOGRAPHICALLY_ATTESTED",
        "official_https_byte_replay": "NOT_RUN",
        "independent_c_acceptance": "NOT_GRANTED",
        "municipal_coverage": "NOT_DETERMINED",
        "facility_identity": "NOT_APPROVED",
        "current_open_status": "NOT_EVALUATED",
        "hazard_safety": "NOT_EVALUATED",
        "publication_approval": "NOT_GRANTED",
        "note": (
            "Archived tile count is not municipality coverage or current facility count; "
            "one source attribute is not disaster safety or an open shelter. "
            "No site records are approved, normalized, joined, or published."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--hazard", required=True, choices=sorted(_HAZARDS))
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--retrieved-at-utc", required=True)
    parser.add_argument("--report", type=Path, help="Optional LOCAL audit summary path; not a published catalog")
    args = parser.parse_args()
    try:
        result = preflight_gsi_tile(
            args.raw.read_bytes(),
            source_url=args.source_url,
            hazard=args.hazard,
            expected_sha256=args.expected_sha256,
            retrieved_at_utc=args.retrieved_at_utc,
        )
    except (OSError, ValueError) as exc:
        print(f"H0_PREFLIGHT_HOLD: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
