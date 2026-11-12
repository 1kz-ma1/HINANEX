"""Internal, fail-closed location evidence triage for an UNREVIEWED Ichikawa pilot.

Classifies text discrepancies and area-like place names for human location review.
It NEVER proves cross-source identity, verified entrance, disaster safety or
routing eligibility. No geocoding, third-party queries, UI, or RegionExport.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import asinh, floor, isfinite, pi, radians, tan
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

_SOURCE_PATH = re.compile(r"^/xyz/skhb02/10/([0-9]{1,4})/([0-9]{1,4})\.geojson$")
_AREA_NAME_MARKERS = ("河川敷", "緑地", "公園", "グラウンド", "広場")
_CITY_PREFIX = "千葉県市川市"
_CITY_PAGE = "https://www.city.ichikawa.lg.jp/page/40332.html"
_PDFS = {
    "A": "https://www.city.ichikawa.lg.jp/uploaded/attachment/55017.pdf",
    "C": "https://www.city.ichikawa.lg.jp/uploaded/attachment/55026.pdf",
}
_RAW_LIMIT = 12_000_000


def _tile(url: str) -> tuple[int, int]:
    if not isinstance(url, str) or "\\" in url or any(c.isspace() for c in url):
        raise ValueError("UNTRUSTED_GSI_SOURCE_URL")
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "cyberjapandata.gsi.go.jp"
            or p.username is not None or p.password is not None
            or p.query or p.fragment):
        raise ValueError("UNTRUSTED_GSI_SOURCE_URL")
    try:
        if p.port not in (None, 443):
            raise ValueError("UNTRUSTED_GSI_SOURCE_URL")
    except ValueError as exc:
        raise ValueError("UNTRUSTED_GSI_SOURCE_URL") from exc
    m = _SOURCE_PATH.fullmatch(p.path)
    if m is None:
        raise ValueError("WRONG_GSI_HAZARD_OR_TILE")
    x, y = map(int, m.groups())
    if x >= 1024 or y >= 1024:
        raise ValueError("INVALID_GSI_TILE_NUMBER")
    return x, y


def _point_tile(coords: object) -> tuple[int, int]:
    if not isinstance(coords, list) or len(coords) not in (2, 3):
        raise ValueError("SOURCE_POINT_INVALID")
    lon, lat = coords[:2]
    if (type(lon) not in (int, float) or type(lat) not in (int, float)
            or not isfinite(lon) or not isfinite(lat)
            or not -180 <= lon < 180 or not -85.05112878 < lat < 85.05112878):
        raise ValueError("SOURCE_POINT_INVALID")
    return floor((lon + 180) * 1024 / 360), floor(
        (1 - asinh(tan(radians(lat))) / pi) * 1024 / 2
    )


def triage_ichikawa_location(raw: bytes, reference: dict) -> dict:
    """Compare source values to *AI-transcribed* municipal claims, not authority.

    Nothing in the output can be used as an operational navigation entitlement.
    All user-facing or routing integrations require their own review and gate.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= _RAW_LIMIT:
        raise ValueError("RAW_SOURCE_MISSING_OR_OVERSIZE")
    if not isinstance(reference, dict):
        raise ValueError("UNTRUSTED_REFERENCE")
    mandatory = {
        "status", "gsi_source_url", "gsi_sha256",
        "expected_total_tile_features", "candidate_address_prefix",
        "city_page_url", "city_page_update_date", "transcription_method",
        "municipal_pdf_hazard_column_label", "rows",
    }
    if set(reference) != mandatory or (
        reference["status"] != "AI_TRANSCRIBED_OFFICIAL_TABLE_UNAPPROVED"
        or reference["candidate_address_prefix"] != _CITY_PREFIX
        or reference["city_page_url"] != _CITY_PAGE
        or reference["city_page_update_date"] != "2026-09-08"
        or reference["transcription_method"] !=
        "AI_EXTRACTED_FROM_OFFICIAL_HTML_AND_PDF_RENDER_NOT_HUMAN_APPROVED"
        or reference["municipal_pdf_hazard_column_label"] != "土砂災害"
    ):
        raise ValueError("REFERENCE_OR_AUTHORITY_NOT_SUPPORTED")
    url = reference["gsi_source_url"]
    x, y = _tile(url)
    digest = sha256(raw).hexdigest()
    if reference["gsi_sha256"] != digest:
        raise ValueError("RAW_HASH_MISMATCH")
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("RAW_JSON_INVALID") from exc
    if (not isinstance(document, dict)
            or document.get("type") != "FeatureCollection"
            or not isinstance(document.get("features"), list)):
        raise ValueError("NOT_GSI_FEATURE_COLLECTION")
    features = document["features"]
    if (type(reference["expected_total_tile_features"]) is not int
            or len(features) != reference["expected_total_tile_features"]
            or not isinstance(reference["rows"], list)):
        raise ValueError("SOURCE_COUNT_OR_REFERENCE_ROWS_INVALID")
    # A GSI z10 tile spans municipalities. Membership here is only a *text*
    # filter and never confirms that the location belongs to Ichikawa City.
    city_indices = set()
    for index, item in enumerate(features):
        if (not isinstance(item, dict) or item.get("type") != "Feature"
                or not isinstance(item.get("properties"), dict)
                or not isinstance(item.get("geometry"), dict)
                or item["geometry"].get("type") != "Point"):
            raise ValueError("INVALID_SOURCE_FEATURE")
        p = item["properties"]
        if _point_tile(item["geometry"].get("coordinates")) != (x, y):
            raise ValueError("POINT_OUTSIDE_SOURCE_TILE")
        if type(p.get("disaster2")) is not int or p["disaster2"] != 1:
            raise ValueError("SOURCE_LANDSLIDE_MARKER_INVALID")
        if not isinstance(p.get("name"), str) or not p["name"].strip():
            raise ValueError("SOURCE_NAME_MISSING")
        address = p.get("address")
        if address is not None and not isinstance(address, str):
            raise ValueError("SOURCE_ADDRESS_TYPE_INVALID")
        if isinstance(address, str) and address.startswith(_CITY_PREFIX):
            city_indices.add(index)

    required_row_keys = {
        "gsi_feature_index", "city_section", "city_row_number",
        "city_name", "city_address", "city_pdf_url",
        "landslide_symbol_transcribed",
    }
    result_rows, queue, seen = [], [], set()
    for r in reference["rows"]:
        if not isinstance(r, dict) or set(r) != required_row_keys:
            raise ValueError("C_REFERENCE_ROW_INVALID")
        i = r["gsi_feature_index"]
        if type(i) is not int or i not in city_indices:
            raise ValueError("C_REFERENCE_INDEX_NOT_CITY_CANDIDATE")
        if i in seen:
            raise ValueError("C_REFERENCE_DUPLICATE_FEATURE")
        seen.add(i)
        sec = r["city_section"]
        if (sec not in _PDFS or r["city_pdf_url"] != _PDFS[sec]
                or type(r["city_row_number"]) is not int
                or r["city_row_number"] < 1
                or type(r["city_name"]) is not str or not r["city_name"].strip()
                or type(r["city_address"]) is not str or not r["city_address"].strip()
                or r["landslide_symbol_transcribed"] != "○"):
            raise ValueError("C_REFERENCE_CITY_TEXT_UNSUPPORTED")
        source = features[i]
        props, coords = source["properties"], source["geometry"]["coordinates"]
        name_equal = props["name"] == r["city_name"]
        addr_equal = props.get("address") == _CITY_PREFIX + r["city_address"]
        if name_equal and addr_equal:
            match = "NAME_ADDRESS_TEXT_MATCH_UNAPPROVED"
        elif name_equal:
            match = "NAME_ONLY_ADDRESS_SCOPE_REVIEW"
        else:
            match = "NAME_MISMATCH_REVIEW"
        issues = []
        if not name_equal:
            issues.append("NAME_MISMATCH")
        if not addr_equal:
            issues.append("ADDRESS_SCOPE_MISMATCH")
        if any(marker in props["name"] for marker in _AREA_NAME_MARKERS):
            issues.append("AREA_LIKE_NAME_NEEDS_GEOMETRY_AND_ENTRY_REVIEW")
        if "地先" in r["city_address"]:
            issues.append("AREA_STYLE_ADDRESS_NEEDS_SPATIAL_REVIEW")
        if issues:
            queue.append({
                "gsi_feature_index": i,
                "issues": issues,
                "priority": "HIGH" if not (name_equal and addr_equal) else "STANDARD",
                "human_confirmation_pending": True,
            })
        result_rows.append({
            "source_feature_key": f"{url}#feature_index={i}",
            "gsi_feature_index": i,
            "source_name_raw": props["name"],
            "source_address_raw": props.get("address"),
            "municipal_name_ai_transcribed": r["city_name"],
            "municipal_address_ai_transcribed": r["city_address"],
            "municipal_pdf_url": r["city_pdf_url"],
            "municipal_landslide_symbol_ai_transcribed": "○",
            "text_comparison": match,
            "reference_point": {
                "kind": "GSI_RAW_POINT_ONLY_NOT_AN_ENTRANCE",
                "coordinates": coords[:2],
            },
            "facility_geometry": None,
            "navigation_endpoint": None,
            "endpoint_evidence_status": "NOT_VERIFIED",
            "human_location_review_required": bool(issues),
            "municipal_document_human_approved": False,
            "facility_identity_verified": False,
            "may_publish_reference_point": False,
            "may_offer_navigation": False,
        })
    if city_indices != seen:
        raise ValueError("C_REFERENCE_INCOMPLETE_CITY_ADDRESS_SET")
    exact = sum(r["text_comparison"] == "NAME_ADDRESS_TEXT_MATCH_UNAPPROVED"
                for r in result_rows)
    return {
        "status": "LOCATION_TRIAGE_INTERNAL_ONLY_UNAPPROVED",
        "hazard": "landslide",
        "gsi_source_url": url,
        "source_raw_sha256": digest,
        "tile_source_feature_count": len(features),
        "city_address_prefix_candidate_count": len(result_rows),
        "text_exact_count": exact,
        "text_difference_count": len(result_rows) - exact,
        "location_exception_count": len(queue),
        "human_location_review_queue": queue,
        "batch_source_status": "UNREVIEWED",
        "municipal_transcription_status": "AI_UNREVIEWED",
        "municipal_boundary_verified": False,
        "source_origin_independently_authenticated": False,
        "human_c_approved": False,
        "navigation_allowed_count": 0,
        "safe_destination_count_approved": 0,
        "location_records": result_rows,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gsi-raw", required=True, type=Path)
    p.add_argument("--c-reference", required=True, type=Path)
    p.add_argument("--report-out", required=True, type=Path)
    args = p.parse_args()
    try:
        if args.report_out.exists() or args.report_out.is_symlink():
            raise ValueError("REPORT_ALREADY_EXISTS")
        if args.gsi_raw.stat().st_size > _RAW_LIMIT:
            raise ValueError("GSI_RAW_OVERSIZE")
        result = triage_ichikawa_location(
            args.gsi_raw.read_bytes(),
            json.loads(args.c_reference.read_text(encoding="utf-8")),
        )
        args.report_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": result["status"],
            "text_exact_count": result["text_exact_count"],
            "location_exception_count": result["location_exception_count"],
            "navigation_allowed_count": 0,
        }, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print("LOCATION TRIAGE BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
