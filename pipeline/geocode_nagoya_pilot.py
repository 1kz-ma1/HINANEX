"""Opt-in Nagoya address geocoding trial; never modifies canonical coordinates.

Use only a locally running Digital Agency ABR geocoder; source and trial
outputs remain outside Git. No inferred location is approved for GIS or routing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_SAMPLE = 50
REGION = "23100"
CITY = "愛知県名古屋市"
# Verify ward labels against the city of Nagoya's official 16-ward directory.
# https://www.city.nagoya.jp/shisei/gaiyou/1015754/1015781/index.html
NAGOYA_WARDS = frozenset({
    "千種区", "東区", "北区", "西区", "中村区", "中区", "昭和区", "瑞穂区",
    "熱田区", "中川区", "港区", "南区", "守山区", "緑区", "名東区", "天白区",
})
LEVELS = {"rsdtdsp_blk", "rsdtdsp_rsdt", "parcel"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_dataset(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    obj = json.loads(raw)
    if (not isinstance(obj, dict) or obj.get("region_code") != REGION
            or obj.get("requirement_code") != "shelter_location"
            or not isinstance(obj.get("records"), list)):
        raise ValueError("Requires a Nagoya shelter_location normalized dataset")
    return obj, digest(raw)


def full_address(ward: str, address: str) -> str:
    if not isinstance(ward, str) or not isinstance(address, str):
        raise ValueError("Ward/address missing")
    ward, address = ward.strip(), address.strip()
    if ward not in NAGOYA_WARDS or not address:
        raise ValueError("Ward/address invalid")
    if address.startswith(CITY):
        if not address.startswith(CITY + ward):
            raise ValueError("Ward and address differ")
        return address
    if address.startswith("名古屋市"):
        if not address.startswith("名古屋市" + ward):
            raise ValueError("Ward and address differ")
        return "愛知県" + address
    if address.startswith(ward):
        return CITY + address
    if address.startswith("愛知県"):
        raise ValueError("Unexpected prefecture/city prefix")
    return CITY + ward + address


def prepare(dataset: dict, source_sha256: str, limit: int = MAX_SAMPLE) -> dict:
    if not 1 <= limit <= MAX_SAMPLE:
        raise ValueError("Sample must contain 1..50 items")
    by_ward: dict[str, deque] = defaultdict(deque)
    identifiers: set[str] = set()
    skipped = Counter()
    for record in dataset["records"]:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError("Invalid normalized record")
        if record["id"] in identifiers:
            raise ValueError("Duplicate normalized record ID")
        identifiers.add(record["id"])
        if record.get("latitude") is not None or record.get("longitude") is not None:
            skipped["has_source_coordinates"] += 1
            continue
        if not isinstance(record.get("name"), str) or not record["name"].strip():
            skipped["missing_name"] += 1
            continue
        if record.get("administrative_area") not in NAGOYA_WARDS:
            skipped["out_of_scope_ward"] += 1
            continue
        try:
            query = full_address(record.get("administrative_area"), record.get("address"))
        except ValueError:
            skipped["incomplete_address"] += 1
            continue
        by_ward[record["administrative_area"]].append({
            "record_id": record["id"], "name": record["name"],
            "ward": record["administrative_area"],
            "source_address": record["address"], "query_address": query,
        })
    wards = sorted(by_ward)
    selected = []
    while wards and len(selected) < limit:
        remaining = []
        for ward in wards:
            if len(selected) >= limit:
                break
            selected.append(by_ward[ward].popleft())
            if by_ward[ward]:
                remaining.append(ward)
        wards = remaining
    if not selected:
        raise ValueError("No eligible Nagoya records for address geocoding")
    return {
        "pilot_version": 1, "region_code": REGION,
        "source_dataset_sha256": source_sha256,
        "source_record_count": len(dataset["records"]),
        "max_sample": limit, "selected": selected,
        "skipped": dict(skipped), "approved_for_map": False,
    }


def address_key(value: str) -> str:
    """Compare ABR-normalized addresses without blindly accepting other house numbers.

    Japanese full-width digits and common address delimiters are normalized.
    This is intentionally conservative: unrecognized variants remain UNRESOLVED.
    """
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[−‐‑–―ー]", "-", value)
    value = re.sub(r"(?<=\d)丁目", "-", value)
    value = re.sub(r"(?<=\d)番地の?", "-", value)
    value = re.sub(r"(?<=\d)番", "-", value)
    value = re.sub(r"(?<=\d)号", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def classify(payload: object, query: str, ward: str) -> dict:
    def unresolved(reason: str) -> dict:
        return {"status": "UNRESOLVED", "reason": reason, "approved_for_map": False}
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        return unresolved("invalid_response")
    if not isinstance(payload.get("query"), dict) or payload["query"].get("address") != query:
        return unresolved("query_mismatch")
    features = payload.get("features")
    if not isinstance(features, list) or len(features) != 1:
        return unresolved("missing_or_ambiguous_match")
    feat = features[0]
    if not isinstance(feat, dict) or not isinstance(feat.get("properties"), dict):
        return unresolved("invalid_feature")
    props = feat["properties"]
    structured = props.get("structured_address")
    if (not isinstance(structured, dict) or structured.get("pref") != "愛知県"
            or structured.get("city") != "名古屋市" or structured.get("ward") != ward):
        return unresolved("outside_city_or_ward")
    matched = props.get("matched_address")
    if not isinstance(matched, str) or not matched.startswith(CITY + ward):
        return unresolved("matched_address_outside_ward")
    if address_key(matched) != address_key(query):
        return unresolved("different_street_or_house_number")
    if props.get("unmatched_address") not in ([], None):
        return unresolved("unmatched_address")
    level = props.get("coordinates_level")
    if level not in LEVELS:
        return unresolved("low_resolution_or_unknown_level")
    geom = feat.get("geometry")
    coords = geom.get("coordinates") if isinstance(geom, dict) and geom.get("type") == "Point" else None
    if not isinstance(coords, list) or len(coords) != 2:
        return unresolved("missing_coordinates")
    lon, lat = coords
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lon, lat)):
        return unresolved("invalid_numeric_coordinates")
    if lon == 0 or lat == 0 or not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return unresolved("out_of_range_coordinates")
    # ABR upstream issue #256 reports some parcel-level coordinates with
    # very large offsets. Preserve the reference point for independent review
    # but never count parcel precision as an ordinary candidate success.
    needs_review = level == "parcel"
    return {
        "status": "NEEDS_REVIEW" if needs_review else "UNVERIFIED_CANDIDATE",
        "reason": "parcel_reference_offset_risk" if needs_review else "human_site_review_required",
        "derived_geometry": {"latitude": lat, "longitude": lon},
        "coordinate_source": "DIGITAL_AGENCY_ABR_ADDRESS_GEOCODER",
        "coordinates_level": level, "matched_address": matched,
        "review_status": "PENDING", "approved_for_map": False,
    }


class BlockRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect disallowed")


def local_url(value: str) -> str:
    parts = urlparse(value)
    if (parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parts.username or parts.password or parts.path not in ("", "/")
            or parts.query or parts.fragment or parts.port is None):
        raise ValueError("Only an explicit local http ABR server is allowed")
    return value.rstrip("/")


def fetch_json(opener, uri: str) -> tuple[object, bytes]:
    with opener.open(Request(uri, headers={"Accept": "application/json, application/geo+json"}), timeout=10) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("ABR response too large")
    return json.loads(raw), raw


def resolve(manifest: dict, source_dataset: dict, dataset_sha256: str, server: str) -> dict:
    if (manifest.get("pilot_version") != 1 or manifest.get("region_code") != REGION
            or manifest.get("source_dataset_sha256") != dataset_sha256):
        raise ValueError("Invalid or stale manifest")
    rows = manifest.get("selected")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_SAMPLE:
        raise ValueError("Invalid sample")
    # A hash alone does not prove that the chosen IDs/addresses match the
    # unchanged dataset. Rebuild the deterministic sample before any HTTP.
    if manifest.get("approved_for_map") is not False:
        raise ValueError("Pilot manifest must remain unapproved")
    expected = prepare(source_dataset, dataset_sha256, manifest.get("max_sample"))
    if (manifest.get("selected") != expected["selected"]
            or manifest.get("source_record_count") != expected["source_record_count"]
            or manifest.get("skipped") != expected["skipped"]):
        raise ValueError("Manifest selection differs from the source dataset")
    base = local_url(server)
    opener = build_opener(ProxyHandler({}), BlockRedirects())
    health, _ = fetch_json(opener, base + "/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise ValueError("ABR health check failed")
    version, _ = fetch_json(opener, base + "/")
    if not isinstance(version, dict) or version.get("name") != "abrg" or not version.get("db_version"):
        raise ValueError("ABR DB version unavailable")
    results = []
    seen = set()
    duplicates = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("record_id"), str) or row["record_id"] in seen:
            raise ValueError("Tampered or duplicate record")
        seen.add(row["record_id"])
        if full_address(row["ward"], row["source_address"]) != row["query_address"]:
            raise ValueError("Tampered address query")
        result = {
            "record_id": row["record_id"], "name": row["name"], "ward": row["ward"],
            "source_address": row["source_address"], "query_address": row["query_address"],
            "approved_for_map": False,
        }
        uri = base + "/geocode?" + urlencode({"address": row["query_address"], "pref": "23", "limit": "2", "category": "all"})
        try:
            payload, raw = fetch_json(opener, uri)
            result.update(classify(payload, row["query_address"], row["ward"]))
            result["provider_response_sha256"] = digest(raw)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            result.update({"status": "PROVIDER_ERROR", "reason": type(exc).__name__})
        if result["status"] in {"UNVERIFIED_CANDIDATE", "NEEDS_REVIEW"}:
            p = result["derived_geometry"]
            duplicates[(p["latitude"], p["longitude"])].append(result)
        results.append(result)
    for group in duplicates.values():
        if len(group) > 1:
            for item in group:
                item["status"] = "NEEDS_REVIEW"
                if item.get("reason") != "shared_reference_coordinate":
                    item["reason"] += ";shared_reference_coordinate"
    return {
        "pilot_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset_sha256": dataset_sha256, "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": version.get("version"), "provider_db_version": version["db_version"],
        "statuses": dict(Counter(r["status"] for r in results)),
        "count": len(results), "results": results,
        "approved_for_map": False, "data_promotion_authorized": False,
        "not_shelter_or_route_safety_assessment": True,
    }


def save_new(path: Path, value: dict) -> None:
    with path.open("xb") as out:
        out.write((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "resolve"))
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=MAX_SAMPLE)
    parser.add_argument("--local-abr-url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    data, source_sha = read_dataset(args.dataset)
    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    target = args.out.resolve()
    if target != allowed and allowed not in target.parents:
        parser.error("Output must be within pipeline/data/geocoding_pilot (gitignored)")
    target.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        manifest = prepare(data, source_sha, args.limit)
        save_new(target / "manifest.json", manifest)
        print("Prepared", len(manifest["selected"]), "records. No network or geocoding.")
    else:
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        report = resolve(manifest, data, source_sha, args.local_abr_url)
        save_new(target / "resolution.json", report)
        print(json.dumps(report["statuses"], ensure_ascii=False, sort_keys=True))
        print("No geocoded result was approved or copied into RegionExport")


if __name__ == "__main__":
    main()
