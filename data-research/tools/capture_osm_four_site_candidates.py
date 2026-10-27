"""One-shot OSM Overpass *candidate source* capture for four archived GSI points.

No place-to-polygon matching, entry authorization, geocoding, GIS or route use.
Requires preserved original GSI tile bytes with locked SHA and explicit notice
acknowledgments. Public Overpass is shared: one narrow query, no retries.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
import socket
from pathlib import Path
import ssl
import sys
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

GSI_SHA256 = "cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84"
GSI_SOURCE_URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
OSM_ENDPOINT = "https://overpass-api.de/api/interpreter"
OSM_COPYRIGHT = "https://www.openstreetmap.org/copyright"
GSI_NOTICE = "https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html"
REPO_ROOT = Path(__file__).resolve().parents[2]
RADIUS_METERS = 300
TARGETS = {
    571: "江戸川河川敷緑地",
    639: "須和田公園",
    682: "大洲防災公園",
    707: "筑波大学附属聴覚特別支援学校（グラウンド等）",
}
MAX_GSI_BYTES = 1_000_000
MAX_OSM_BYTES = 6_000_000
MAX_OSM_ELEMENTS = 4500


class EvidenceBlocked(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def inspect_gsi_original(raw: bytes, *, expected_sha: str = GSI_SHA256) -> list[dict]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_GSI_BYTES:
        raise EvidenceBlocked("GSI_RAW_MISSING_OR_TOO_LARGE")
    if sha256(raw).hexdigest() != expected_sha:
        raise EvidenceBlocked("GSI_RAW_SHA256_MISMATCH")
    try:
        collection = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise EvidenceBlocked("GSI_JSON_UNREADABLE") from exc
    if (not isinstance(collection, dict) or collection.get("type") != "FeatureCollection"
            or not isinstance(collection.get("features"), list)
            or len(collection["features"]) != 800):
        raise EvidenceBlocked("GSI_EXPECTED_TILE_SHAPE_MISMATCH")
    entries = []
    for index, expected_name in TARGETS.items():
        feature = collection["features"][index]
        if not isinstance(feature, dict):
            raise EvidenceBlocked("GSI_TARGET_FEATURE_MISSING")
        p, geom = feature.get("properties"), feature.get("geometry")
        if not isinstance(p, dict) or not isinstance(geom, dict):
            raise EvidenceBlocked("GSI_TARGET_SCHEMA_INVALID")
        xy = geom.get("coordinates")
        if (p.get("name") != expected_name
                or not isinstance(p.get("address"), str)
                or not p["address"].startswith("千葉県市川市")
                or type(p.get("disaster2")) is not int or p["disaster2"] != 1
                or geom.get("type") != "Point"
                or not isinstance(xy, list) or len(xy) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in xy)
                or not (139.8 < xy[0] < 140.1 and 35.6 < xy[1] < 35.9)):
            raise EvidenceBlocked("GSI_TARGET_IDENTITY_OR_POINT_INVALID")
        entries.append({
            "feature_index": index,
            "gsi_name_raw": expected_name,
            "gsi_address_raw": p["address"],
            "reference_coordinates_lon_lat_raw": xy[:],
            "source_feature_key": f"{GSI_SOURCE_URL}#feature_index={index}",
            "reference_point_is_navigation_endpoint": False,
        })
    return entries


def build_query(targets: list[dict]) -> str:
    if len(targets) != 4 or [t["feature_index"] for t in targets] != list(TARGETS):
        raise EvidenceBlocked("FOUR_LOCKED_FEATURES_REQUIRED")
    selectors = []
    for target in targets:
        lon, lat = target["reference_coordinates_lon_lat_raw"]
        point = f"(around:{RADIUS_METERS},{lat:.6f},{lon:.6f})"
        selectors.extend([
            f'node{point}["entrance"];',
            f'way{point}["leisure"~"^(park|recreation_ground|pitch|playground)$"];',
            f'way{point}["landuse"~"^(recreation_ground|grass)$"];',
            f'way{point}["amenity"="school"];',
            f'relation{point}["leisure"~"^(park|recreation_ground|pitch)$"];',
            f'relation{point}["amenity"="school"];',
        ])
    return "[out:json][timeout:35][maxsize:33554432];\n(\n" + "\n".join(selectors) + "\n);\nout body geom;\n"


def fetch_once(query: str) -> tuple[bytes, dict]:
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    body = urlencode({"data": query}).encode("utf-8")
    req = Request(OSM_ENDPOINT, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "HINANEX-Research-Overpass-4-Sites/1.0 (+https://github.com/1kz-ma1/HINANEX)",
    }, method="POST")
    try:
        with opener.open(req, timeout=65) as response:
            if response.getcode() != 200 or response.geturl() != OSM_ENDPOINT:
                raise EvidenceBlocked("OSM_RESPONSE_STATUS_OR_ORIGIN_BLOCKED")
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise EvidenceBlocked("OSM_RESPONSE_NOT_JSON")
            raw = response.read(MAX_OSM_BYTES + 1)
            if not 0 < len(raw) <= MAX_OSM_BYTES:
                raise EvidenceBlocked("OSM_RESPONSE_SIZE_BLOCKED")
            return raw, {
                "status_observed": 200,
                "url_observed": response.geturl(),
                "content_type_observed": content_type,
                "date_observed": response.headers.get("Date"),
            }
    except HTTPError as exc:
        # Log only the numeric status, never a server body or potentially
        # sensitive exception URL/header text. Do not retry any HTTP failure.
        raise EvidenceBlocked(
            f"OSM_HTTP_STATUS_{exc.code}_NO_AUTOMATIC_RETRY") from None
    except URLError as exc:
        # A small allow-list of transport classes; do not echo exc.reason,
        # which can include local proxy, machine, or URL details.
        reason = exc.reason
        if isinstance(reason, ssl.SSLError):
            category = "TLS"
        elif isinstance(reason, (TimeoutError, socket.timeout)):
            category = "TIMEOUT"
        elif isinstance(reason, socket.gaierror):
            category = "DNS"
        elif isinstance(reason, ConnectionRefusedError):
            category = "CONNECTION_REFUSED"
        else:
            category = "UNKNOWN"
        raise EvidenceBlocked(
            f"OSM_TRANSPORT_{category}_NO_AUTOMATIC_RETRY") from None
    except (TimeoutError, OSError):
        # Includes socket failures not wrapped in URLError.
        raise EvidenceBlocked(
            "OSM_TRANSPORT_OS_ERROR_NO_AUTOMATIC_RETRY") from None


def inspect_osm_response(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_OSM_BYTES:
        raise EvidenceBlocked("OSM_RESPONSE_MISSING_OR_TOO_LARGE")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise EvidenceBlocked("OSM_JSON_UNREADABLE") from exc
    if (not isinstance(data, dict) or not isinstance(data.get("elements"), list)
            or len(data["elements"]) > MAX_OSM_ELEMENTS
            or ("remark" in data and data["remark"])):
        raise EvidenceBlocked("OSM_RESULT_SCHEMA_OR_RUNTIME_ERROR")
    seen = set()
    counts = {"node": 0, "way": 0, "relation": 0}
    for item in data["elements"]:
        if not isinstance(item, dict) or item.get("type") not in counts:
            raise EvidenceBlocked("OSM_ELEMENT_UNEXPECTED")
        category, oid = item["type"], item.get("id")
        if type(oid) is not int or oid < 1 or (category, oid) in seen:
            raise EvidenceBlocked("OSM_DUPLICATE_OR_INVALID_ID")
        seen.add((category, oid))
        counts[category] += 1
    return {
        "raw_sha256": sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
        "element_type_counts": counts,
        "element_count": len(seen),
        "source_snapshot_timestamp_claim_unverified": data.get("osm3s", {}).get("timestamp_osm_base")
            if isinstance(data.get("osm3s"), dict) else None,
    }


def capture_osm_candidates(gsi_raw: bytes, destination: Path, *,
                           acknowledged_osm: bool, acknowledged_gsi: bool,
                           fetcher=fetch_once, observed_at=None,
                           expected_gsi_sha: str = GSI_SHA256) -> dict:
    if acknowledged_osm is not True or acknowledged_gsi is not True:
        raise EvidenceBlocked("BOTH_OSM_AND_GSI_USAGE_ACKNOWLEDGMENTS_REQUIRED")
    requested = Path(destination).absolute()
    if requested.exists() or requested.is_symlink():
        raise EvidenceBlocked("OUTPUT_ALREADY_EXISTS")
    if not requested.parent.is_dir():
        raise EvidenceBlocked("OUTPUT_PARENT_MISSING")
    parent = requested.parent.resolve(strict=True)
    out = parent / requested.name
    if out == REPO_ROOT or REPO_ROOT in out.parents:
        raise EvidenceBlocked("RAW_EVIDENCE_CANNOT_BE_WRITTEN_TO_GIT")
    when = observed_at or datetime.now(timezone.utc)
    if not isinstance(when, datetime) or when.utcoffset() is None:
        raise EvidenceBlocked("INVALID_OBSERVED_TIME")
    targets = inspect_gsi_original(gsi_raw, expected_sha=expected_gsi_sha)
    query = build_query(targets)
    raw_osm, http = fetcher(query)
    if (not isinstance(http, dict)
            or type(http.get("status_observed")) is not int
            or http["status_observed"] != 200
            or http.get("url_observed") != OSM_ENDPOINT):
        raise EvidenceBlocked("OSM_FETCHER_STATUS_INVALID")
    info = inspect_osm_response(raw_osm)
    manifest = {
        "status": "OSM_FOUR_SITES_SOURCE_CANDIDATES_UNREVIEWED",
        "gsi_source_url": GSI_SOURCE_URL,
        "gsi_sha256": sha256(gsi_raw).hexdigest(),
        "overpass_api_url": OSM_ENDPOINT,
        "query_sha256": sha256(query.encode("utf-8")).hexdigest(),
        "response_sha256": info["raw_sha256"],
        "response_bytes": info["raw_bytes"],
        "response_element_count": info["element_count"],
        "osm_element_type_counts": info["element_type_counts"],
        "osm_snapshot_time_claim_unverified": info["source_snapshot_timestamp_claim_unverified"],
        "capture_time_utc": when.astimezone(timezone.utc).isoformat(),
        "source_http_observation": http,
        "radius_meters_per_site": RADIUS_METERS,
        "four_target_points_unverified": targets,
        "osm_license": "ODbL-1.0",
        "osm_attribution": "© OpenStreetMap contributors",
        "osm_license_url": OSM_COPYRIGHT,
        "gsi_usage_notice_url": GSI_NOTICE,
        "candidate_to_official_facility_identity_verified": False,
        "candidate_geometry_officially_verified": False,
        "entrance_position_verified": False,
        "current_open_access_verified": False,
        "hazard_safety_verified": False,
        "human_c_approved": False,
        "navigation_allowed": False,
        "safe_destination_count_approved": 0,
        "no_elements_does_not_mean_no_facility": True,
    }
    # Never convert raw OSM ways/relations to a simplified official Polygon.
    # Store the unmodified OSM response and query; matching comes later in D/C.
    files = [
        ("gsi-skhb02-original.geojson", gsi_raw),
        ("osm-overpass-original.json", raw_osm),
        ("osm-query.overpassql", query.encode("utf-8")),
        ("a_candidate_capture_manifest_UNREVIEWED.json",
         (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")),
        ("USAGE_NOTICE_AND_STATUS.txt",
         ("Data © OpenStreetMap contributors (ODbL 1.0): " + OSM_COPYRIGHT
          + "\nGSI notice: " + GSI_NOTICE
          + "\nREFERENCE POINT != entrance, park boundary, safe site or route.\n"
          + "OSM candidates are unassigned, not official evacuation places.\n"
          + "All route/hazard/human C approvals remain FALSE.\n").encode("utf-8")),
    ]
    with TemporaryDirectory(dir=parent, prefix=".osm-four-source-") as tmp:
        root = Path(tmp)
        for name, blob in files:
            fd = os.open(root / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(blob)
        if out.exists() or out.is_symlink():
            raise EvidenceBlocked("OUTPUT_ALREADY_CREATED_BY_OTHER_PROCESS")
        os.rename(root, out)
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gsi-raw", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--fetch", action="store_true")
    p.add_argument("--acknowledged-osm-license", action="store_true")
    p.add_argument("--acknowledged-gsi-notice", action="store_true")
    args = p.parse_args()
    if not args.fetch:
        p.error("--fetch is mandatory; offline tests never access OSM")
    try:
        if args.gsi_raw.stat().st_size > MAX_GSI_BYTES:
            raise EvidenceBlocked("GSI_RAW_TOO_LARGE")
        report = capture_osm_candidates(
            args.gsi_raw.read_bytes(), args.out_dir,
            acknowledged_osm=args.acknowledged_osm_license,
            acknowledged_gsi=args.acknowledged_gsi_notice,
        )
        print(json.dumps({
            "status": report["status"],
            "candidate_elements_unassigned": report["response_element_count"],
            "navigation_allowed": False,
        }, ensure_ascii=False))
        return 0
    except (OSError, EvidenceBlocked) as exc:
        print("OSM FOUR-SITE CAPTURE BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
