"""Strict *reference discovery* catalog gate for GSI flood-designated emergency sites.

This is deliberately separate from the older flood_shelter_selection Scenario,
whose Edogawa/Niigata/Nagoya facility applicability is still UNKNOWN.

The engine never converts an unverified shelter into a flood candidate.
The C audit object is an integration gate, not a cryptographic signature:
independent Source -> normalized-record checking belongs to C.
"""
from __future__ import annotations

from hashlib import sha256
import json
from math import isfinite
import re
from urllib.parse import urlparse


_REGION_CODES = {"13123", "15100", "23100"}
_TILE_RE = re.compile(r"^/xyz/skhb01/[0-9]+/[0-9]+/[0-9]+\.geojson$")


def _valid_coord(value: object, low: float, high: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and low <= value <= high
    )


def _official_flood_tile(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "cyberjapandata.gsi.go.jp"
        and bool(_TILE_RE.fullmatch(parsed.path))
        and not parsed.params and not parsed.query and not parsed.fragment
        and not parsed.username and not parsed.password
    )


def extract_gsi_flood_tile(
    raw_archive: bytes, source_url: str, search_context_region_code: str,
) -> list[dict]:
    """Normalize one archived official skhb01 tile, retaining every raw feature.

    Values/field names derive from GSI's documented GeoJSON specification
    (name, address, remarks, disaster1=1), not another municipality's ODS.
    Context is the search area; no invented official municipality assignments.
    Any malformed/ambiguous feature stops the whole tile.
    """
    if not _official_flood_tile(source_url):
        raise ValueError("source_url is not an official GSI flood GeoJSON tile")
    if search_context_region_code not in _REGION_CODES:
        raise ValueError("unknown search context")
    if not isinstance(raw_archive, bytes):
        raise ValueError("raw_archive must be bytes")
    try:
        data = json.loads(raw_archive)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid archived source GeoJSON") from exc
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError("GSI flood source must be GeoJSON FeatureCollection")
    digest = sha256(raw_archive).hexdigest()
    records = []
    for index, feature in enumerate(data["features"]):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"invalid GSI source feature at {index}")
        props = feature.get("properties")
        geom = feature.get("geometry")
        if not isinstance(props, dict) or not isinstance(geom, dict) or geom.get("type") != "Point":
            raise ValueError(f"unverified Point/properties at feature {index}")
        coords = geom.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2 or len(coords) > 3:
            raise ValueError(f"unverified geometry at feature {index}")
        longitude, latitude = coords[:2]  # GeoJSON is [longitude, latitude]
        if not _valid_coord(latitude, -90, 90) or not _valid_coord(longitude, -180, 180):
            raise ValueError(f"invalid official coordinate at feature {index}")
        if type(props.get("disaster1")) is not int or props["disaster1"] != 1:
            raise ValueError(f"not verified GSI flood designation at feature {index}")
        if not isinstance(props.get("name"), str) or not props["name"].strip():
            raise ValueError(f"missing official place name at feature {index}")
        for field in ("address", "remarks"):
            if props.get(field) is not None and not isinstance(props[field], str):
                raise ValueError(f"{field} has unverified type at feature {index}")
        trace = f"feature_index={index}"
        records.append({
            "source_feature_key": f"{source_url}#{trace}",
            "name_raw": props["name"],
            "address_raw": props.get("address"),
            "remarks_raw": props.get("remarks"),
            "disaster1_raw": props["disaster1"],
            "search_context_region_code": search_context_region_code,
            "latitude": latitude, "longitude": longitude,
            "source_url": source_url,
            "source_record_trace": trace,
            "source_raw_sha256": digest,
            "designation_kind": "designated_emergency_evacuation_site",
            "hazard_dataset": "GSI_SKHB01_FLOOD",
        })
    return records


def _record(record: object, region_code: str, source_hash: str) -> dict:
    if not isinstance(record, dict):
        raise ValueError("each site must be an object")
    keys = {
        "source_feature_key", "name_raw", "address_raw", "remarks_raw",
        "disaster1_raw", "search_context_region_code",
        "latitude", "longitude", "source_url", "source_record_trace",
        "source_raw_sha256", "designation_kind", "hazard_dataset",
    }
    if set(record) != keys:
        raise ValueError("site record fields mismatch")
    for key in ("source_feature_key", "name_raw", "source_record_trace"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"{key} must be non-empty source text")
    # search_context_region_code is the UI search scope, NOT a claim that the
    # raw GSI feature belongs to that municipality: tiles span boundaries.
    if record["search_context_region_code"] != region_code:
        raise ValueError("site search context mismatch")
    if record["source_feature_key"] != f'{record["source_url"]}#{record["source_record_trace"]}':
        raise ValueError("source feature key must refer to its exact raw row")
    if not re.fullmatch(r"feature_index=[0-9]+", record["source_record_trace"]):
        raise ValueError("source trace must be a physical GeoJSON feature index")
    for key in ("address_raw", "remarks_raw"):
        if record[key] is not None and not isinstance(record[key], str):
            raise ValueError(f"{key} must preserve nullable source text")
    if type(record["disaster1_raw"]) is not int or record["disaster1_raw"] != 1:
        raise ValueError("official flood disaster1 source value must be integer 1")
    if not _valid_coord(record["latitude"], -90, 90) or not _valid_coord(record["longitude"], -180, 180):
        raise ValueError("official site latitude/longitude invalid")
    if record["designation_kind"] != "designated_emergency_evacuation_site":
        raise ValueError("not a designated emergency evacuation site")
    if record["hazard_dataset"] != "GSI_SKHB01_FLOOD":
        raise ValueError("flood designation dataset not proven")
    if not _official_flood_tile(record["source_url"]):
        raise ValueError("not a documented official GSI flood tile URL")
    if record["source_raw_sha256"] != source_hash:
        raise ValueError("official raw archive sha256 mismatch")
    return dict(record)  # preserve raw text, no name/geocoding/transforms


def build_flood_site_catalog(
    region_code: str,
    records: list[dict],
    *,
    raw_archive: bytes | None = None,
    c_acceptance: dict | None = None,
) -> dict:
    """Return a reference catalog, never an 'open/safe/recommended' ranking.

    Acceptance must be independently produced by C. A self-asserted string is
    not independent verification. Until then output is explicit BLOCKED with
    zero accepted sites, regardless of input row count.
    """
    if region_code not in _REGION_CODES:
        raise ValueError("unsupported municipality code")
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    blocked = {
        "catalog_kind": "flood_designated_emergency_site_reference",
        "region_code": region_code,
        "hazard": "flood",
        "status": "BLOCKED_UNVERIFIED_SOURCE",
        "source_status": "NOT_ACCEPTED",
        "sites": [],
        "total_source_records": len(records),
        "notice": (
            "国土地理院の洪水対応指定緊急避難場所の元データをCが独立照合するまで"
            "候補表示を行いません。UNKNOWNの既存避難所を候補へ昇格しません。"
        ),
        "limitations": [
            "江戸川区は大規模水害時に広域避難を案内します。区の最新情報を優先してください。",
            "掲載場所は現在の開設・経路・建物の安全や、そこへ行くべきことを保証しません。",
            "直線距離は避難経路の距離や時間ではありません。",
        ],
    }

    if raw_archive is None or c_acceptance is None:
        return blocked
    if not isinstance(raw_archive, bytes) or not isinstance(c_acceptance, dict):
        raise ValueError("raw_archive must be bytes; C acceptance must be a dict")

    source_hash = sha256(raw_archive).hexdigest()
    if (
        c_acceptance.get("status") != "PASS"
        or c_acceptance.get("source_raw_sha256") != source_hash
        or c_acceptance.get("search_context_region_code") != region_code
        or c_acceptance.get("hazard_dataset") != "GSI_SKHB01_FLOOD"
        or not isinstance(c_acceptance.get("audit_reference"), str)
        or not c_acceptance["audit_reference"].strip()
    ):
        raise ValueError("C independent source-acceptance gate not satisfied")

    accepted_ids = c_acceptance.get("accepted_source_feature_keys")
    if not isinstance(accepted_ids, list) or not accepted_ids or any(
        not isinstance(key, str) or not key for key in accepted_ids
    ) or len(set(accepted_ids)) != len(accepted_ids):
        raise ValueError("C accepted official IDs must be unique and nonempty")

    verified = [_record(item, region_code, source_hash) for item in records]
    ids = [item["source_feature_key"] for item in verified]
    if len(ids) != len(set(ids)) or set(ids) != set(accepted_ids):
        raise ValueError("D records and C accepted official IDs must match exactly")

    return {
        **blocked,
        "status": "REFERENCE_ONLY",
        "source_status": "C_ACCEPTED",
        "sites": verified,
        "source_raw_sha256": source_hash,
        "c_audit_reference": c_acceptance["audit_reference"],
        "notice": (
            "洪水に対する指定緊急避難場所としての公式掲載事実のみを表示します。"
            "現在の開設・経路・建物の安全、最適な行き先を保証しません。"
        ),
    }
