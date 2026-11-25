"""Independent C replay of archived GSI skhb02 and A's unreviewed summary.
Only local byte/feature consistency: not download authenticity, municipal
coverage, independent human approval, or disaster safety.
"""
import argparse
from hashlib import sha256
import json
from math import asinh, floor, isfinite, pi, radians, tan
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

PATTERN = re.compile(r"^/xyz/skhb02/10/([0-9]{1,4})/([0-9]{1,4})\.geojson$")
MAX_BYTES = 12_000_000


def tile(url):
    if not isinstance(url, str) or "\\" in url or any(c.isspace() for c in url):
        raise ValueError("UNTRUSTED_URL")
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "cyberjapandata.gsi.go.jp"
            or p.username or p.password or p.query or p.fragment):
        raise ValueError("UNTRUSTED_URL")
    try:
        if p.port not in (None, 443):
            raise ValueError("UNTRUSTED_URL")
    except ValueError as e:
        raise ValueError("UNTRUSTED_URL") from e
    match = PATTERN.fullmatch(p.path)
    if not match:
        raise ValueError("WRONG_GSI_DATASET_OR_TILE")
    x, y = map(int, match.groups())
    if x >= 1024 or y >= 1024:
        raise ValueError("INVALID_TILE_NUMBER")
    return x, y


def point_tile(lon, lat):
    if (type(lon) not in (int, float) or type(lat) not in (int, float)
            or not isfinite(lon) or not isfinite(lat)
            or not -180 <= lon < 180 or not -85.05112878 < lat < 85.05112878):
        raise ValueError("INVALID_COORDINATE")
    return floor((lon + 180) * 1024 / 360), floor(
        (1 - asinh(tan(radians(lat))) / pi) * 1024 / 2
    )


def verify_archived_skhb02(raw, source_url, a_report):
    x, y = tile(source_url)
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("INVALID_RAW_BYTES")
    if not isinstance(a_report, dict):
        raise ValueError("A_REPORT_MISSING")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as e:
        raise ValueError("INVALID_RAW_JSON") from e
    if (not isinstance(data, dict) or data.get("type") != "FeatureCollection"
            or not isinstance(data.get("features"), list)):
        raise ValueError("NOT_FEATURE_COLLECTION")
    features = data["features"]
    digest = sha256(raw).hexdigest()
    expected = {
        "purpose": "A_SKHB02_SOURCE_FEASIBILITY_ONLY",
        "source_url": source_url,
        "source_sha256": digest,
        "source_byte_count": len(raw),
        "source_tile": {"z": 10, "x": x, "y": y},
        "source_feature_count": len(features),
        "hazard": "landslide",
        "official_attribute": "disaster2",
        "source_kind": "designated_emergency_evacuation_place",
        "not_a_landslide_risk_layer": True,
        "municipal_coverage_verified": False,
        "municipal_site_opening_verified": False,
        "independent_c_approved": False,
        "safe_destination_count_approved": 0,
        "not_for_publication": True,
        "status": ("SOURCE_TILE_INSPECTED_UNREVIEWED" if features
                   else "TILE_EMPTY_MUNICIPAL_COVERAGE_UNKNOWN"),
    }
    for k, value in expected.items():
        actual = a_report.get(k)
        if type(actual) is not type(value) or actual != value:
            raise ValueError("A_REPORT_MISMATCH:" + k)
    previews = a_report.get("raw_feature_previews_for_human_review")
    if not isinstance(previews, list) or len(previews) != len(features):
        raise ValueError("A_REPORT_ROW_COUNT_MISMATCH")
    for i, (feature, reported) in enumerate(zip(features, previews)):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("INVALID_FEATURE")
        p, g = feature.get("properties"), feature.get("geometry")
        if (not isinstance(p, dict) or not isinstance(g, dict)
                or g.get("type") != "Point"):
            raise ValueError("INVALID_POINT_FEATURE")
        coordinates = g.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) not in (2, 3):
            raise ValueError("INVALID_GEOMETRY")
        if point_tile(*coordinates[:2]) != (x, y):
            raise ValueError("POINT_OUTSIDE_GSI_TILE")
        if type(p.get("disaster2")) is not int or p["disaster2"] != 1:
            raise ValueError("WRONG_HAZARD_DISASTER2")
        if not isinstance(p.get("name"), str) or not p["name"].strip():
            raise ValueError("MISSING_NAME")
        if any(p.get(k) is not None and not isinstance(p[k], str)
               for k in ("address", "remarks")):
            raise ValueError("INVALID_RAW_TEXT")
        row = {
            "feature_index": i, "name_raw": p["name"],
            "address_raw": p.get("address"), "remarks_raw": p.get("remarks"),
            "coordinates_raw": coordinates, "disaster2_raw": 1,
            "source_feature_ref": source_url + "#feature_index=" + str(i),
            "not_current_open_or_safe": True,
            "not_a_cross_source_facility_identity": True,
        }
        if (not isinstance(reported, dict) or set(reported) != set(row)
                or any(type(reported[k]) is not type(v) or reported[k] != v
                       for k, v in row.items() if v is not None)
                or any(reported[k] is not None for k, v in row.items()
                       if v is None)):
            raise ValueError("A_REPORT_FEATURE_MISMATCH:" + str(i))
    return {
        "status": "C_LOCAL_MATCH_UNAPPROVED" if features
                  else "C_EMPTY_TILE_COVERAGE_UNKNOWN",
        "source_url": source_url, "raw_sha256": digest,
        "tile_wide_feature_count": len(features),
        "tile": f"10/{x}/{y}",
        "official_origin_authenticated": False,
        "independent_human_approved": False,
        "municipal_coverage_verified": False,
        "c_publication_approved": False,
        "safe_destination_count_approved": 0,
        "next_review": [
            "official_https_download_provenance",
            "municipality_publication_date_and_coverage",
            "independent_human_hazard_and_site_review",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--a-report", type=Path, required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--report-out", type=Path)
    args = p.parse_args()
    try:
        if args.report_out and args.report_out.exists():
            raise ValueError("REPORT_ALREADY_EXISTS")
        if args.raw.stat().st_size > MAX_BYTES:
            raise ValueError("ARCHIVE_TOO_LARGE")
        result = verify_archived_skhb02(
            args.raw.read_bytes(), args.source_url,
            json.loads(args.a_report.read_text(encoding="utf-8")),
        )
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report_out:
            with args.report_out.open("x", encoding="utf-8") as f:
                f.write(output)
        print(output, end="")
        return 0
    except (OSError, ValueError, TypeError) as e:
        print("SKHB02 C REPLAY BLOCKED: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
