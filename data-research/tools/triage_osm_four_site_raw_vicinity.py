"""Research-only observed-coordinate vicinity queue from unreviewed OSM source.

This tool intentionally does NOT associate an OSM feature with a GSI facility,
identify a complete property boundary, accept an entrance, or enable routing.
A vertex/point within 300 m is a *review hint*, not an identity match. A feature
without a close observed vertex may still cross or contain the reference point.
Requires the independent #329 original-source audit before reading raw elements.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

from inspect_osm_four_site_evidence import EvidenceBlocked, GSI_SHA256, TARGETS, inspect_evidence_dir

RADIUS_M = 300
MAX_COORDINATES = 200_000
MAX_PER_ELEMENT = 15_000


def _latlon(obj: dict) -> tuple[float, float] | None:
    """Accept only explicit OSM latitude/longitude pairs, never centroids."""
    if not isinstance(obj, dict):
        raise EvidenceBlocked("INVALID_OSM_LOCATION_OBJECT")
    has_lat, has_lon = "lat" in obj, "lon" in obj
    if has_lat != has_lon:
        raise EvidenceBlocked("INCOMPLETE_OSM_LATLON")
    if not has_lat:
        return None
    lat, lon = obj["lat"], obj["lon"]
    if (type(lat) not in (int, float) or type(lon) not in (int, float)
            or not math.isfinite(lat) or not math.isfinite(lon)
            or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        raise EvidenceBlocked("INVALID_OSM_LATLON")
    return float(lat), float(lon)


def _coordinates(element: dict) -> list[tuple[float, float]]:
    """Read only coordinates explicitly present in the raw Overpass response."""
    locations = []

    def add(raw):
        pos = _latlon(raw)
        if pos is not None:
            locations.append(pos)
            if len(locations) > MAX_PER_ELEMENT:
                raise EvidenceBlocked("EXCESSIVE_OSM_GEOMETRY_POINTS")

    add(element)
    geometry = element.get("geometry")
    if geometry is not None:
        if not isinstance(geometry, list):
            raise EvidenceBlocked("OSM_GEOMETRY_SHAPE_INVALID")
        for item in geometry:
            add(item)
    members = element.get("members")
    if members is not None:
        if not isinstance(members, list):
            raise EvidenceBlocked("OSM_MEMBERS_INVALID")
        for member in members:
            if not isinstance(member, dict):
                raise EvidenceBlocked("OSM_MEMBER_INVALID")
            add(member)
            child = member.get("geometry")
            if child is not None:
                if not isinstance(child, list):
                    raise EvidenceBlocked("OSM_MEMBER_GEOMETRY_INVALID")
                for item in child:
                    add(item)
    return locations


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Spherical point-to-point distance, NOT point-to-polygon or safe-route."""
    a_lat, a_lon = (math.radians(z) for z in a)
    b_lat, b_lon = (math.radians(z) for z in b)
    dlat = b_lat - a_lat
    dlon = b_lon - a_lon
    h = math.sin(dlat / 2) ** 2 + math.cos(a_lat) * math.cos(b_lat) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(h)))


def triage_vicinity(directory: Path, *, expected_gsi_sha: str = GSI_SHA256) -> dict:
    """Return nonexclusive observation queues; raw record ownership stays null."""
    audited = inspect_evidence_dir(directory, expected_gsi_sha=expected_gsi_sha)
    folder = Path(directory)
    original = (folder / "osm-overpass-original.json").read_bytes()
    # Explicitly keep this separate from the archived manifest's own SHA claim.
    if sha256(original).hexdigest() != audited["osm_response_sha256"]:
        raise EvidenceBlocked("OSM_CHANGED_AFTER_INDEPENDENT_AUDIT")
    payload = json.loads(original.decode("utf-8"))
    elements = payload["elements"]
    if len(elements) != audited["unassigned_candidate_count"]:
        raise EvidenceBlocked("OSM_POST_AUDIT_COUNT_CHANGED")
    refs = tuple((index, name, (coord[1], coord[0])) for index, (name, coord) in TARGETS.items())
    queues = {index: [] for index, _, _ in refs}
    no_observed_geometry = []
    not_near_any_observed_point = []
    seen = set()
    budget = 0
    for element in elements:
        typ, eid = element["type"], element["id"]
        key = (typ, eid)
        if key in seen:
            raise EvidenceBlocked("OSM_ID_DUPLICATED_AFTER_AUDIT")
        seen.add(key)
        positions = _coordinates(element)
        budget += len(positions)
        if budget > MAX_COORDINATES:
            raise EvidenceBlocked("OSM_OBSERVED_POINT_BUDGET_EXCEEDED")
        if not positions:
            no_observed_geometry.append({"osm_element_type": typ, "osm_element_id": eid,
                                         "osm_element_url_unreviewed": f"https://www.openstreetmap.org/{typ}/{eid}",
                                         "associated_gsi_feature_index": None,
                                         "reason": "NO_OBSERVED_COORDINATES_NOT_EXCLUSION"})
            continue
        near_some = False
        for index, _, reference in refs:
            closest = min(_distance_m(reference, point) for point in positions)
            if closest <= RADIUS_M:
                near_some = True
                queues[index].append({
                    "osm_element_type": typ,
                    "osm_element_id": eid,
                    "osm_element_url_unreviewed": f"https://www.openstreetmap.org/{typ}/{eid}",
                    "observed_point_count": len(positions),
                    "closest_observed_point_distance_m_approx": round(closest, 1),
                    "review_hint": "OBSERVED_POINT_WITHIN_300M_NOT_FACILITY_MATCH",
                    "associated_gsi_feature_index": None,
                    "official_facility_identity_verified": False,
                    "entrance_verified": False,
                    "navigation_endpoint": None,
                    "navigation_allowed": False,
                })
        if not near_some:
            not_near_any_observed_point.append({
                "osm_element_type": typ,
                "osm_element_id": eid,
                "osm_element_url_unreviewed": f"https://www.openstreetmap.org/{typ}/{eid}",
                "associated_gsi_feature_index": None,
                "reason": "NO_OBSERVED_POINT_WITHIN_300M_NOT_EXCLUSION",
            })
    return {
        "status": "OSM_FOUR_SITE_OBSERVED_VICINITY_UNREVIEWED",
        "source_gsi_sha256": audited["gsi_sha256"],
        "source_osm_sha256": audited["osm_response_sha256"],
        "query_sha256": audited["query_sha256"],
        "osm_attribution": audited["osm_attribution"],
        "osm_license": audited["osm_license"],
        "source_element_count": len(elements),
        "source_observed_coordinate_count": budget,
        "radius_meters_for_observed_points_only": RADIUS_M,
        "source_has_no_exhaustive_facility_coverage_claim": True,
        "per_reference_review_hints_not_matches": [{
            "gsi_feature_index_reference_only": index,
            "gsi_name_reference_only": name,
            "observed_vicinity_element_count": len(queues[index]),
            "nonexclusive_unassigned_elements_needing_review": queues[index],
        } for index, name, _ in refs],
        "no_observed_coordinates_needing_review": no_observed_geometry,
        "not_near_any_observed_vertex_needing_review": not_near_any_observed_point,
        "candidate_to_official_facility_identity_verified": False,
        "facility_geometry_verified": None,
        "entrance_position_verified": False,
        "human_c_approved": False,
        "navigation_endpoint": None,
        "navigation_allowed": False,
        "may_publish_or_route": False,
        "safe_destination_count_approved": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path,
                        help="Original five-file #327 source outside repository")
    args = parser.parse_args()
    try:
        result = triage_vicinity(args.evidence_dir)
    except (OSError, ValueError) as exc:
        print("OSM vicinity review BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
