"""Offline A audit of #327's archived OSM/GSI *unreviewed* evidence.

No network, geocoding, facility matching, polygon simplification or navigation.
Returns source integrity and an unassigned OSM candidate inventory only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

GSI_SHA256 = "cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84"
GSI_URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
OSM_URL = "https://overpass-api.de/api/interpreter"
TARGETS = {
    571: ("江戸川河川敷緑地", [139.899193, 35.725904]),
    639: ("須和田公園", [139.912857, 35.739064]),
    682: ("大洲防災公園", [139.910732, 35.718787]),
    707: ("筑波大学附属聴覚特別支援学校（グラウンド等）", [139.902054, 35.744282]),
}
FILES = {
    "gsi_sha256": "gsi-skhb02-original.geojson",
    "response_sha256": "osm-overpass-original.json",
    "query_sha256": "osm-query.overpassql",
}
EXTRAS = {"a_candidate_capture_manifest_UNREVIEWED.json", "USAGE_NOTICE_AND_STATUS.txt"}
NEGATIVE_FLAGS = (
    "candidate_to_official_facility_identity_verified",
    "candidate_geometry_officially_verified",
    "entrance_position_verified",
    "current_open_access_verified",
    "hazard_safety_verified",
    "human_c_approved", "navigation_allowed",
)
MAX_BYTES = {"gsi_sha256": 1_000_000, "response_sha256": 6_000_000,
             "query_sha256": 100_000}


class EvidenceBlocked(ValueError):
    """Archive cannot be trusted for even internal inspection."""


def _expected_query() -> bytes:
    """Reconstruct exactly the approved 4x300m request independently of manifest."""
    selectors = []
    for _, (name, (lon, lat)) in TARGETS.items():
        point = f"(around:300,{lat:.6f},{lon:.6f})"
        selectors.extend((
            f'node{point}["entrance"];',
            f'way{point}["leisure"~"^(park|recreation_ground|pitch|playground)$"];',
            f'way{point}["landuse"~"^(recreation_ground|grass)$"];',
            f'way{point}["amenity"="school"];',
            f'relation{point}["leisure"~"^(park|recreation_ground|pitch)$"];',
            f'relation{point}["amenity"="school"];',
        ))
    return ("[out:json][timeout:35][maxsize:33554432];\n(\n" +
            "\n".join(selectors) + "\n);\nout body geom;\n").encode("utf-8")


def _read_exact(directory: Path, name: str, maximum: int) -> bytes:
    path = directory / name
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size <= maximum):
        raise EvidenceBlocked("ARCHIVED_EVIDENCE_FILE_MISSING_SYMLINK_OR_TOO_LARGE:" + name)
    return path.read_bytes()


def _parse_object(raw: bytes, error: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise EvidenceBlocked(error) from exc
    if not isinstance(value, dict):
        raise EvidenceBlocked(error)
    return value


def _validate_gsi(raw: bytes) -> list[dict]:
    obj = _parse_object(raw, "GSI_FORMAT_BLOCKED")
    if (obj.get("type") != "FeatureCollection" or
            not isinstance(obj.get("features"), list) or
            len(obj["features"]) != 800):
        raise EvidenceBlocked("GSI_TILE_NOT_PINNED_800_FEATURES")
    out = []
    for idx, (name, coordinates) in TARGETS.items():
        feat = obj["features"][idx]
        if not isinstance(feat, dict):
            raise EvidenceBlocked("GSI_TARGET_INVALID")
        p, g = feat.get("properties"), feat.get("geometry")
        if (not isinstance(p, dict) or not isinstance(g, dict) or
                p.get("name") != name or type(p.get("disaster2")) is not int or
                p["disaster2"] != 1 or not isinstance(p.get("address"), str) or
                not p["address"].startswith("千葉県市川市") or
                g.get("type") != "Point" or g.get("coordinates") != coordinates):
            raise EvidenceBlocked("GSI_TARGET_NAME_HAZARD_OR_POINT_MISMATCH")
        out.append({"feature_index": idx, "gsi_name_raw": name,
                    "gsi_address_raw": p["address"],
                    "reference_coordinates_lon_lat_raw": coordinates,
                    "source_feature_key": GSI_URL + "#feature_index=" + str(idx),
                    "reference_point_is_navigation_endpoint": False})
    return out


def inspect_evidence_dir(directory: Path, *, expected_gsi_sha: str = GSI_SHA256) -> dict:
    """Fail-closed verifier; expected_gsi_sha override is for synthetic tests only."""
    folder = Path(directory)
    if folder.is_symlink() or not folder.is_dir():
        raise EvidenceBlocked("EVIDENCE_DIRECTORY_INVALID")
    expected_files = set(FILES.values()) | EXTRAS
    if {entry.name for entry in folder.iterdir()} != expected_files:
        raise EvidenceBlocked("EVIDENCE_ARCHIVE_INCOMPLETE_OR_UNEXPECTED_FILES")
    raw = {k: _read_exact(folder, v, MAX_BYTES[k]) for k, v in FILES.items()}
    manifest = _parse_object(_read_exact(folder,
                             "a_candidate_capture_manifest_UNREVIEWED.json", 100_000),
                             "MANIFEST_JSON_INVALID")
    _read_exact(folder, "USAGE_NOTICE_AND_STATUS.txt", 50_000)
    for key, blob in raw.items():
        digest = sha256(blob).hexdigest()
        if type(manifest.get(key)) is not str or manifest[key] != digest:
            raise EvidenceBlocked("MANIFEST_SHA_MISMATCH:" + key)
    if manifest["gsi_sha256"] != expected_gsi_sha:
        raise EvidenceBlocked("GSI_LOCKED_SHA_MISMATCH")
    targets = _validate_gsi(raw["gsi_sha256"])
    if (manifest.get("gsi_source_url") != GSI_URL or
            manifest.get("overpass_api_url") != OSM_URL or
            manifest.get("four_target_points_unverified") != targets or
            manifest.get("radius_meters_per_site") != 300):
        raise EvidenceBlocked("FOUR_ORIGINAL_TARGETS_OR_SCOPE_MISMATCH")
    if raw["query_sha256"] != _expected_query():
        raise EvidenceBlocked("UNEXPECTED_OVERPASS_QUERY")
    http = manifest.get("source_http_observation")
    if (not isinstance(http, dict) or
            type(http.get("status_observed")) is not int or
            http["status_observed"] != 200 or
            http.get("url_observed") != OSM_URL or
            "json" not in str(http.get("content_type_observed", "")).lower()):
        raise EvidenceBlocked("SOURCE_HTTP_OBSERVATION_MISMATCH")
    if (manifest.get("status") != "OSM_FOUR_SITES_SOURCE_CANDIDATES_UNREVIEWED" or
            manifest.get("osm_attribution") != "© OpenStreetMap contributors" or
            manifest.get("osm_license") != "ODbL-1.0" or
            manifest.get("osm_license_url") != "https://www.openstreetmap.org/copyright" or
            any(manifest.get(flag) is not False for flag in NEGATIVE_FLAGS) or
            type(manifest.get("safe_destination_count_approved")) is not int or
            manifest["safe_destination_count_approved"] != 0 or
            manifest.get("no_elements_does_not_mean_no_facility") is not True):
        raise EvidenceBlocked("ARCHIVE_APPROVAL_OR_ATTRIBUTION_MISMATCH")
    osm = _parse_object(raw["response_sha256"], "OSM_RAW_JSON_INVALID")
    elements = osm.get("elements")
    if (not isinstance(elements, list) or len(elements) > 4500 or
            osm.get("remark")):
        raise EvidenceBlocked("OSM_RESPONSE_RUNTIME_OR_ELEMENTS_INVALID")
    counts = {"node": 0, "way": 0, "relation": 0}
    seen = set()
    records = []
    for e in elements:
        if not isinstance(e, dict) or e.get("type") not in counts:
            raise EvidenceBlocked("OSM_ELEMENT_TYPE_INVALID")
        kind, eid = e["type"], e.get("id")
        if type(eid) is not int or eid <= 0 or (kind, eid) in seen:
            raise EvidenceBlocked("OSM_ELEMENT_ID_INVALID_OR_DUPLICATE")
        seen.add((kind, eid))
        counts[kind] += 1
        # Source remains unassigned to any official facility, even when tags match.
        records.append({"osm_element_type": kind, "osm_element_id": eid,
                        "osm_element_url_unreviewed":
                            f"https://www.openstreetmap.org/{kind}/{eid}",
                        "associated_gsi_feature_index": None,
                        "official_facility_identity_verified": False,
                        "facility_geometry_verified": None,
                        "navigation_endpoint": None,
                        "navigation_allowed": False})
    if (manifest.get("response_element_count") != len(records) or
            manifest.get("osm_element_type_counts") != counts or
            manifest.get("response_bytes") != len(raw["response_sha256"])):
        raise EvidenceBlocked("OSM_MANIFEST_COUNT_MISMATCH")
    snapshot = osm.get("osm3s")
    if snapshot is not None and not isinstance(snapshot, dict):
        raise EvidenceBlocked("OSM_SNAPSHOT_METADATA_INVALID")
    if (manifest.get("osm_snapshot_time_claim_unverified") !=
            (snapshot.get("timestamp_osm_base") if snapshot else None)):
        raise EvidenceBlocked("OSM_SNAPSHOT_CLAIM_MISMATCH")
    return {"status": "A_OSM_ORIGINAL_ARCHIVE_INSPECTED_UNREVIEWED",
            "gsi_sha256": manifest["gsi_sha256"],
            "osm_response_sha256": manifest["response_sha256"],
            "query_sha256": manifest["query_sha256"],
            "capture_time_utc_unverified": manifest.get("capture_time_utc"),
            "osm_snapshot_time_claim_unverified": manifest.get("osm_snapshot_time_claim_unverified"),
            "source_http_observation_unreviewed": http,
            "osm_attribution": manifest["osm_attribution"],
            "osm_license": manifest["osm_license"],
            "osm_element_counts": counts,
            "unassigned_candidates": records,
            "unassigned_candidate_count": len(records),
            "candidate_to_official_facility_identity_verified": False,
            "human_c_approved": False,
            "navigation_allowed": False,
            "safe_destination_count_approved": 0,
            "zero_elements_is_no_facility_evidence": False,
            "may_publish_or_route": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True,
                        help="Path to extracted, exact #327 Actions artifact (outside Git)")
    args = parser.parse_args()
    try:
        report = inspect_evidence_dir(args.evidence_dir)
    except (OSError, EvidenceBlocked) as exc:
        print("OSM archive audit BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
