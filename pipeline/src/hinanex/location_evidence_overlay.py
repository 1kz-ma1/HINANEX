"""Phase 2: candidate geometry / entrance evidence triage only.

No entry point, geometry or third-party record is verified or authorized by
this function. Never pass its output to operational GIS routing or advice.
Requires Phase-1 UNAPPROVED source report. No network calls / geocoding.
"""
from __future__ import annotations

from collections import defaultdict
import math
import re
from urllib.parse import urlsplit

_SHA = re.compile(r"^[0-9a-f]{64}$")
_OSM_URL = re.compile(r"^https://www\.openstreetmap\.org/(?:way|relation)/[1-9][0-9]*$")
_GSI_CSV_DOC = "https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
_CANDIDATE_KEYS = {
    "source_feature_key", "provider", "provider_record_id",
    "source_document_url", "source_archive_sha256", "common_id_raw",
    "candidate_geometry", "entrance_hints",
}
_ENTRY_KEYS = {"source_node_id", "coordinates", "entrance_tag", "access_tag"}
_PROVIDERS = {"OSM", "MUNICIPAL_GEOJSON", "GSI_CSV"}
_ENTRY_TAGS = {"yes", "main", "service", "emergency", "exit", "no"}
_ACCESS_TAGS = {None, "yes", "permissive", "private", "no", "customers", "delivery"}


def _point(value):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)
            or not (-180 <= value[0] <= 180 and -90 <= value[1] <= 90)):
        raise ValueError("INVALID_GEOMETRIC_POINT")
    return tuple(value)


def _ring(geometry):
    """Only a simple unholed Polygon: no unsafe assumptions about holes."""
    if geometry is None:
        return None
    if (not isinstance(geometry, dict)
            or set(geometry) != {"type", "coordinates"}
            or geometry["type"] != "Polygon"
            or not isinstance(geometry["coordinates"], list)
            or len(geometry["coordinates"]) != 1):
        raise ValueError("UNSUPPORTED_GEOMETRY_UNVERIFIABLE")
    ring_raw = geometry["coordinates"][0]
    if not isinstance(ring_raw, list) or not (4 <= len(ring_raw) <= 2000):
        raise ValueError("INVALID_POLYGON_RING")
    points = [_point(p) for p in ring_raw]
    if points[0] != points[-1] or len(set(points[:-1])) < 3:
        raise ValueError("INVALID_POLYGON_CLOSURE")
    if (max(p[0] for p in points) - min(p[0] for p in points) >= 180):
        raise ValueError("ANTIMERIDIAN_UNSUPPORTED")
    # No zero-length edges or crossings: a potentially malformed source
    # cannot be labeled INSIDE merely by raycasting a bow-tie polygon.
    def orient(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    def on_segment(a, b, p):
        return (abs(orient(a,b,p)) <= 1e-12
                and min(a[0],b[0]) <= p[0] <= max(a[0],b[0])
                and min(a[1],b[1]) <= p[1] <= max(a[1],b[1]))
    segments = list(zip(points, points[1:]))
    for i, (a,b) in enumerate(segments):
        if a == b:
            raise ValueError("DEGENERATE_POLYGON_EDGE")
        for j in range(i+1, len(segments)):
            if j == i+1 or (i == 0 and j == len(segments)-1):
                continue
            c,d = segments[j]
            oa, ob, oc, od = orient(a,b,c), orient(a,b,d),orient(c,d,a),orient(c,d,b)
            if (oa*ob < 0 and oc*od < 0
                    or on_segment(a,b,c) or on_segment(a,b,d)
                    or on_segment(c,d,a) or on_segment(c,d,b)):
                raise ValueError("SELF_INTERSECTING_POLYGON")
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in segments)
    if abs(area) <= 1e-13:
        raise ValueError("ZERO_AREA_POLYGON")
    return points


def _relation(point, ring):
    if ring is None:
        return "NO_CANDIDATE_GEOMETRY"
    x,y = point
    inside = False
    for a,b in zip(ring,ring[1:]):
        cross = (b[0]-a[0])*(y-a[1]) - (b[1]-a[1])*(x-a[0])
        if (abs(cross) <= 1e-12
                and min(a[0],b[0]) <= x <= max(a[0],b[0])
                and min(a[1],b[1]) <= y <= max(a[1],b[1]):
            return "ON_CANDIDATE_BOUNDARY_UNVERIFIED"
        if (a[1] > y) != (b[1] > y):
            ix = a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if ix > x:
                inside = not inside
    return "INSIDE_CANDIDATE_ONLY" if inside else "OUTSIDE_CANDIDATE_ONLY"


def triage_candidate_spatial_evidence(phase1: dict, candidates: list[dict]) -> dict:
    """Make a human review queue; never certify IDs, polygons or entrances."""
    if (not isinstance(phase1, dict)
            or phase1.get("status") != "LOCATION_TRIAGE_INTERNAL_ONLY_UNAPPROVED"
            or phase1.get("human_c_approved") is not False
            or phase1.get("navigation_allowed_count") != 0
            or phase1.get("safe_destination_count_approved") != 0
            or phase1.get("batch_source_status") != "UNREVIEWED"
            or phase1.get("municipal_transcription_status") != "AI_UNREVIEWED"):
        raise ValueError("PHASE1_NOT_UNAPPROVED_OR_INCOMPATIBLE")
    rows = phase1.get("location_records")
    if not isinstance(rows, list) or not isinstance(candidates, list) or len(candidates) > 5000:
        raise ValueError("INVALID_ROW_OR_CANDIDATE_COLLECTION")
    unique = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("INVALID_PHASE1_RECORD")
        key = row.get("source_feature_key")
        rp = row.get("reference_point")
        if (not isinstance(key, str) or not key
                or key in unique or not isinstance(rp, dict)
                or rp.get("kind") != "GSI_RAW_POINT_ONLY_NOT_AN_ENTRANCE"
                or row.get("facility_geometry") is not None
                or row.get("navigation_endpoint") is not None
                or row.get("may_publish_reference_point") is not False
                or row.get("may_offer_navigation") is not False
                or row.get("facility_identity_verified") is not False):
            raise ValueError("INVALID_UNAPPROVED_PHASE1_ROW")
        unique[key] = _point(rp.get("coordinates"))
    if len(unique) != phase1.get("city_address_prefix_candidate_count"):
        raise ValueError("PHASE1_ROW_COUNT_MISMATCH")
    by_key = defaultdict(list)
    seen_evidence = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != _CANDIDATE_KEYS:
            raise ValueError("CANDIDATE_SCHEMA_NOT_TRUSTED")
        key = candidate["source_feature_key"]
        provider = candidate["provider"]
        eid = candidate["provider_record_id"]
        url = candidate["source_document_url"]
        if key not in unique or provider not in _PROVIDERS or not isinstance(eid,str) or not eid:
            raise ValueError("UNBOUND_OR_UNKNOWN_PROVIDER_CANDIDATE")
        if (not isinstance(url,str) or not url.startswith("https://")
                or urlsplit(url).username or urlsplit(url).password):
            raise ValueError("UNTRUSTED_EVIDENCE_DOCUMENT_URL")
        if provider == "OSM" and not _OSM_URL.fullmatch(url):
            raise ValueError("OSM_REFERENCE_URL_INVALID")
        if provider == "GSI_CSV" and url != _GSI_CSV_DOC:
            raise ValueError("GSI_CSV_DOCUMENTATION_URL_INVALID")
        digest = candidate["source_archive_sha256"]
        if not isinstance(digest,str) or not _SHA.fullmatch(digest):
            raise ValueError("UNVERIFIED_SOURCE_DIGEST_FORMAT")
        cid = candidate["common_id_raw"]
        if (cid is not None and (provider != "GSI_CSV"
                or not isinstance(cid,str) or not cid.strip() or len(cid)>128)):
            raise ValueError("COMMON_ID_WRONG_SOURCE_OR_VALUE")
        if provider == "GSI_CSV" and cid is None:
            raise ValueError("GSI_CSV_ID_MISSING")
        if (provider == "GSI_CSV" and
                (candidate["candidate_geometry"] is not None or candidate["entrance_hints"])):
            raise ValueError("GSI_CSV_IS_NOT_GEOMETRY_OR_ENTRANCE")
        pair = (key,provider,eid)
        if pair in seen_evidence:
            raise ValueError("DUPLICATE_CANDIDATE_EVIDENCE")
        seen_evidence.add(pair)
        ring = _ring(candidate["candidate_geometry"])
        entries = candidate["entrance_hints"]
        if not isinstance(entries,list) or len(entries)>100:
            raise ValueError("TOO_MANY_OR_INVALID_ENTRANCES")
        seen_entry_ids = set()
        observations = []
        for entry in entries:
            if not isinstance(entry,dict) or set(entry)!=_ENTRY_KEYS:
                raise ValueError("INVALID_ENTRANCE_EVIDENCE")
            if (not isinstance(entry["source_node_id"],str) or not entry["source_node_id"]
                    or entry["source_node_id"] in seen_entry_ids
                    or entry["entrance_tag"] not in _ENTRY_TAGS
                    or entry["access_tag"] not in _ACCESS_TAGS):
                raise ValueError("INVALID_ENTRANCE_TAG_OR_DUPLICATE")
            seen_entry_ids.add(entry["source_node_id"])
            pos=_point(entry["coordinates"])
            observations.append({
                "source_node_id":entry["source_node_id"],
                "entrance_tag_untrusted":entry["entrance_tag"],
                "access_tag_untrusted":entry["access_tag"],
                "relative_to_candidate_geometry":_relation(pos,ring),
                "safe_to_route":False,
            })
        by_key[key].append({
            "provider":provider,
            "provider_record_id":eid,
            "source_url_untrusted":url,
            "source_archive_sha256_unverified":digest,
            "common_id_raw_unverified":cid,
            "candidate_geometry_present":ring is not None,
            "reference_point_relation_unverified":_relation(unique[key],ring),
            "entrance_hints_unverified":observations,
            "facility_identity_proven":False,
            "official_geometry_proven":False,
        })
    reviews = []
    for key in unique:
        e = by_key.get(key,[])
        issues=[]
        if not e:
            issues.append("NO_EXTERNAL_ID_GEOMETRY_OR_ENTRANCE_EVIDENCE")
        if len(e)>1:
            issues.append("MULTIPLE_UNVERIFIED_SOURCE_CANDIDATES")
        for item in e:
            if item["common_id_raw_unverified"] is not None:
                issues.append("GSI_CSV_COMMON_ID_NOT_BOUND_TO_GEOJSON_ID")
            relation=item["reference_point_relation_unverified"]
            if relation=="NO_CANDIDATE_GEOMETRY":
                issues.append("FACILITY_GEOMETRY_NOT_VERIFIED")
            elif relation=="OUTSIDE_CANDIDATE_ONLY":
                issues.append("REFERENCE_POINT_OUTSIDE_UNTRUSTED_GEOMETRY")
            elif relation=="ON_CANDIDATE_BOUNDARY_UNVERIFIED":
                issues.append("BOUNDARY_AMBIGUOUS")
            if not item["entrance_hints_unverified"]:
                issues.append("ENTRANCE_EVIDENCE_MISSING")
            for entry in item["entrance_hints_unverified"]:
                if entry["relative_to_candidate_geometry"] == "OUTSIDE_CANDIDATE_ONLY":
                    issues.append("ENTRANCE_OUTSIDE_CANDIDATE")
                if entry["access_tag_untrusted"] in (None,"private","no","delivery","customers"):
                    issues.append("ENTRANCE_ACCESS_REQUIRES_REVIEW")
                if entry["entrance_tag_untrusted"] in ("no","exit","service"):
                    issues.append("ENTRANCE_TYPE_NOT_PUBLIC_ROUTE")
        reviews.append({
            "source_feature_key":key,
            "evidence_candidate_count":len(e),
            "candidate_evidence_unverified":e,
            "review_reasons":sorted(set(issues)),
            "human_review_required":True,
            "reference_point_is_navigable":False,
            "official_common_id_verified_for_feature":False,
            "facility_geometry_verified":None,
            "navigation_endpoint":None,
            "navigation_allowed":False,
            "safe_destination":False,
        })
    return {
        "status":"LOCATION_SPATIAL_CANDIDATES_UNREVIEWED",
        "input_phase1_source_raw_sha256":phase1.get("source_raw_sha256"),
        "source_feature_count":len(reviews),
        "candidate_evidence_count":len(candidates),
        "human_review_required_count":len(reviews),
        "human_c_approved":False,
        "municipal_hazard_safety_verified":False,
        "navigation_allowed_count":0,
        "approved_safe_destinations":0,
        "review_queue":reviews,
    }
