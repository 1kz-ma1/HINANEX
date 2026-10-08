"""Independent C checker: archived GSI flood GeoJSON -> D reference rows.

No D imports. No guesswork about city membership, route safety, or current
opening. A passing output is only proof that D's rows match the supplied
archive bytes; it is NOT proof the local file came from the official server.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from urllib.parse import urlparse

_TILE = re.compile(r"^/xyz/skhb01/[0-9]+/[0-9]+/[0-9]+\.geojson$")
_CONTEXT = {"13123", "15100", "23100"}


def _valid_coordinate(value: object, low: float, high: float) -> bool:
    return type(value) in (int, float) and isfinite(value) and low <= value <= high


def verify_gsi_flood_source(
    archive: bytes, rows: list[dict], source_url: str, context_region: str,
) -> dict:
    if context_region not in _CONTEXT:
        raise ValueError("unsupported search context")
    if not isinstance(source_url, str):
        raise ValueError("missing original official source URL")
    url = urlparse(source_url)
    if (
        url.scheme != "https" or url.netloc != "cyberjapandata.gsi.go.jp"
        or not _TILE.fullmatch(url.path) or url.query or url.fragment or url.params
    ):
        raise ValueError("untrusted flood GeoJSON source URL")
    if not isinstance(archive, bytes) or not isinstance(rows, list):
        raise ValueError("source bytes and rows list are required")
    try:
        parsed = json.loads(archive)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid raw source JSON") from exc
    if not isinstance(parsed, dict) or parsed.get("type") != "FeatureCollection":
        raise ValueError("archived source must be a FeatureCollection")
    features = parsed.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("no verifiable flood designated-site features")
    if len(features) != len(rows):
        raise ValueError("source/output feature count mismatch")

    digest = sha256(archive).hexdigest()
    seen = set()
    required_fields = {
        "source_feature_key", "name_raw", "address_raw", "remarks_raw",
        "disaster1_raw", "search_context_region_code", "latitude", "longitude",
        "source_url", "source_record_trace", "source_raw_sha256",
        "designation_kind", "hazard_dataset",
    }
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"source feature {index} invalid")
        geo, props = feature.get("geometry"), feature.get("properties")
        if not isinstance(geo, dict) or geo.get("type") != "Point" or not isinstance(props, dict):
            raise ValueError(f"feature {index} has unverified geometry/properties")
        coord = geo.get("coordinates")
        if not isinstance(coord, list) or not 2 <= len(coord) <= 3:
            raise ValueError(f"feature {index} coordinates unavailable")
        lon, lat = coord[:2]
        if not _valid_coordinate(lat, -90, 90) or not _valid_coordinate(lon, -180, 180):
            raise ValueError(f"feature {index} coordinates invalid")
        if type(props.get("disaster1")) is not int or props["disaster1"] != 1:
            raise ValueError(f"feature {index} is not independently confirmed flood-designated")
        name, address, remarks = props.get("name"), props.get("address"), props.get("remarks")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"source feature {index} missing official name")
        if any(v is not None and not isinstance(v, str) for v in (address, remarks)):
            raise ValueError(f"source feature {index} unrecognized address/remarks")

        row = rows[index]
        if not isinstance(row, dict) or set(row) != required_fields:
            raise ValueError(f"normalized output schema differs from independent audit at {index}")
        trace = f"feature_index={index}"
        key = f"{source_url}#{trace}"
        if key in seen:
            raise ValueError("duplicate source feature key")
        seen.add(key)
        expected = {
            "source_feature_key": key,
            "name_raw": name, "address_raw": address, "remarks_raw": remarks,
            "disaster1_raw": 1, "search_context_region_code": context_region,
            "latitude": lat, "longitude": lon,
            "source_url": source_url, "source_record_trace": trace,
            "source_raw_sha256": digest,
            "designation_kind": "designated_emergency_evacuation_site",
            "hazard_dataset": "GSI_SKHB01_FLOOD",
        }
        if any(type(row[k]) is not type(v) or row[k] != v for k, v in expected.items() if v is not None):
            raise ValueError(f"normalized value differs from original raw feature {index}")
        for nullable in ("address_raw", "remarks_raw"):
            if expected[nullable] is None and row[nullable] is not None:
                raise ValueError(f"raw null transformed at feature {index}")

    return {
        "status": "PASS",
        "source_raw_sha256": digest,
        "search_context_region_code": context_region,
        "hazard_dataset": "GSI_SKHB01_FLOOD",
        "audit_reference": f"C-GSI-SKHB01-SHA256:{digest}",
        "accepted_source_feature_keys": [f"{source_url}#feature_index={i}" for i in range(len(features))],
        "limitations": (
            "Archive bytes and independently prepared rows match the official GSI data schema. "
            "This does not authenticate the local download origin, site opening, route safety, "
            "or municipality membership. GSI publication can be incomplete or out of date."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--region", required=True, choices=sorted(_CONTEXT))
    parser.add_argument("--acceptance-out", type=Path, required=True)
    args = parser.parse_args()
    result = verify_gsi_flood_source(
        args.raw.read_bytes(),
        json.loads(args.records.read_text(encoding="utf-8")),
        args.source_url, args.region
    )
    args.acceptance_out.parent.mkdir(parents=True, exist_ok=True)
    args.acceptance_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"C raw GeoJSON audit PASS: {len(result['accepted_source_feature_keys'])} source features")


if __name__ == "__main__":
    main()
