"""Offline-only cross-reference of PRIVATE Nagoya ABR review queue with GSI CSV.

The CSVs must be explicitly downloaded by the operator after reading GSI terms.
No network, scraping, fuzzy matching, coordinate promotion or GIS writes.
Only count aggregates may be shared. All individual rows stay gitignored.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from create_nagoya_independent_review_queue import (
    PRIVATE_FIELDS, REVIEW_A_EXISTING, REVIEW_A_NEW, REVIEW_B_PARCEL,
    safe_csv_cell,
)
from diagnose_nagoya_kanji_chome_stage3 import canonical_chome_address
from geocode_nagoya_pilot import CITY, NAGOYA_WARDS

OFFICIAL_GSI_PAGE = "https://hinanmap.gsi.go.jp/index.html"
GSI_REQUIRED = frozenset({"施設・場所名", "住所", "緯度", "経度"})
STATUS = (
    "strict_name_address_unique_reference",
    "strict_name_address_conflicting_references",
    "strict_name_address_missing_position",
    "name_match_only_address_unconfirmed",
    "address_match_only_name_unconfirmed",
    "no_strict_facility_correspondence",
)
DISTANCE = ("within_25m", "25_to_100m", "100_to_500m", "over_500m")
KIND = ("emergency", "shelter")
PRIVATE_COMPARISON_FIELDS = (
    "pilot_record_id", "review_priority", "facility_name", "official_listed_address",
    "abr_reference_longitude", "abr_reference_latitude",
    "gsi_cross_reference_status", "gsi_registered_facility_type",
    "gsi_name_address_exact", "gsi_reference_latitude", "gsi_reference_longitude",
    "gsi_abr_distance_meters", "gsi_registered_record_ids",
    "independent_site_position_approved", "manual_followup",
)


def read_csv(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    content = None
    for encoding in ("utf-8-sig", "cp932"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        raise ValueError("CSV encoding unsupported")
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Invalid CSV columns")
    return list(reader), hashlib.sha256(raw).hexdigest()


def name_key(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Invalid facility name")
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", name))


def address_for_queue(raw: str, ward: str) -> str:
    if ward not in NAGOYA_WARDS or not isinstance(raw, str):
        raise ValueError("Invalid queue ward")
    text = unicodedata.normalize("NFKC", raw).strip()
    if not text:
        raise ValueError("Blank address")
    if text.startswith(CITY):
        if not text.startswith(CITY + ward):
            raise ValueError("Queue ward mismatch")
        return text
    if text.startswith("名古屋市"):
        if not text.startswith("名古屋市" + ward):
            raise ValueError("Queue ward mismatch")
        return "愛知県" + text
    if text.startswith(ward):
        return CITY + text
    if text.startswith("愛知県"):
        raise ValueError("Unexpected queue prefecture")
    return CITY + ward + text


def gsi_address_key(address: str, ward: str) -> str | None:
    """Require explicit city+ward evidence; never infer GSI locality."""
    if not isinstance(address, str):
        return None
    addr = unicodedata.normalize("NFKC", address).strip()
    if addr.startswith(CITY + ward):
        pass
    elif addr.startswith("名古屋市" + ward):
        addr = "愛知県" + addr
    else:
        return None
    key, _, unknown = canonical_chome_address(addr)
    return None if unknown else key


def geo(row: dict) -> tuple[float, float] | None:
    try:
        lat, lon = float(row.get("緯度", "")), float(row.get("経度", ""))
    except (ValueError, TypeError):
        return None
    if not all(math.isfinite(n) for n in (lat, lon)):
        return None
    if not 33.0 <= lat <= 38.0 or not 133.0 <= lon <= 140.0:
        return None
    return (lon, lat)


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle approximate distance of two WGS84-like lon/lat points."""
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 6371000 * 2 * math.asin(min(1.0, math.sqrt(h)))


def distance_bucket(meters: float) -> str:
    if meters < 25:
        return "within_25m"
    if meters < 100:
        return "25_to_100m"
    if meters < 500:
        return "100_to_500m"
    return "over_500m"


def parse_gsi(inputs: list[tuple[str, Path]]) -> tuple[list[dict], dict]:
    records, provenance = [], {}
    for kind, path in inputs:
        rows, sha = read_csv(path)
        if not rows:
            raise ValueError("Empty GSI CSV")
        # Check CSV source before use. No guesses or fuzzy header inference.
        with path.open("rb") as stream:
            header_sample = stream.read(1)
        del header_sample
        if not GSI_REQUIRED.issubset(rows[0].keys()):
            raise ValueError("GSI CSV required columns absent")
        accepted = 0
        for row in rows:
            name = row.get("施設・場所名")
            address = row.get("住所")
            if not isinstance(name, str) or not name.strip() or not isinstance(address, str):
                continue
            # GSI source must explicitly identify the city; ward matching
            # happens again against each local queue record.
            if "名古屋市" not in address:
                continue
            accepted += 1
            records.append({
                "name": name_key(name), "address": address, "point": geo(row),
                "kind": kind, "source_id": str(row.get("共通ID") or ""),
            })
        provenance[kind] = {"sha256": sha, "rows_read": len(rows),
                            "nagoya_rows_in_file": accepted}
    return records, provenance


def validate_queue(queue: list[dict], summary: dict) -> None:
    if (summary.get("report_kind") !=
            "NAGOYA_PRIVATE_REVIEW_QUEUE_PREPARATION_NOT_SITE_ACCEPTANCE"
            or summary.get("approved_for_map") is not False
            or summary.get("data_promotion_authorized") is not False
            or summary.get("official_facility_positions_accepted") != 0
            or summary.get("all_review_status_not_reviewed") is not True
            or summary.get("total_review_rows") != len(queue)
            or summary.get("original_sample_total") != 50):
        raise ValueError("Private queue summary invalid")
    priority = Counter(r.get("review_priority") for r in queue)
    if (priority != Counter(summary.get("review_queue_counts"))
            or set(priority) - {REVIEW_A_NEW, REVIEW_A_EXISTING, REVIEW_B_PARCEL}
            or len(queue) != len({r.get("pilot_record_id") for r in queue})
            or any(r.get("review_status") != "NOT_REVIEWED" for r in queue)):
        raise ValueError("Private queue altered or inconsistent")
    for row in queue:
        if not all(field in row for field in PRIVATE_FIELDS):
            raise ValueError("Private queue schema invalid")


def compare(queue: list[dict], queue_summary: dict,
            gsi: list[dict], provenance: dict) -> tuple[list[dict], dict]:
    validate_queue(queue, queue_summary)
    results, statuses, distances, breakdown = [], Counter(), Counter(), Counter()
    for row in queue:
        ward = row["ward"]
        reference_name = name_key(row["facility_name"])
        address, _, unknown = canonical_chome_address(
            address_for_queue(row["official_listed_address"], ward),
        )
        if unknown:
            raise ValueError("Unsupported queue chome numeral")
        reference = (float(row["abr_reference_longitude"]),
                     float(row["abr_reference_latitude"]))
        if not all(math.isfinite(v) for v in reference):
            raise ValueError("Invalid ABR reference")
        locality = [(entry, gsi_address_key(entry["address"], ward))
                    for entry in gsi if gsi_address_key(entry["address"], ward) is not None]
        same_name = [e for e, _ in locality if e["name"] == reference_name]
        same_addr = [e for e, k in locality if k == address]
        strict = [e for e, k in locality if e["name"] == reference_name and k == address]
        points = {e["point"] for e in strict if e["point"] is not None}
        measured, chosen = None, None
        if strict and len(points) > 1:
            status = "strict_name_address_conflicting_references"
        elif strict and not points:
            status = "strict_name_address_missing_position"
        elif strict:
            status = "strict_name_address_unique_reference"
            chosen = next(iter(points))
            measured = round(distance_m(reference, chosen), 1)
            distances[distance_bucket(measured)] += 1
        elif same_name:
            status = "name_match_only_address_unconfirmed"
        elif same_addr:
            status = "address_match_only_name_unconfirmed"
        else:
            status = "no_strict_facility_correspondence"
        statuses[status] += 1
        breakdown[(row["review_priority"], status)] += 1
        entry = dict(row)
        entry.update({
            "gsi_cross_reference_status": status,
            "gsi_registered_facility_type": (
                ";".join(sorted({e["kind"] for e in strict})) if strict else ""),
            "gsi_name_address_exact": "YES" if strict else "NO",
            "gsi_reference_latitude": chosen[1] if chosen else "",
            "gsi_reference_longitude": chosen[0] if chosen else "",
            "gsi_abr_distance_meters": measured if measured is not None else "",
            "gsi_registered_record_ids": (
                ";".join(sorted({e["source_id"] for e in strict if e["source_id"]}))
                if strict else ""),
            "independent_site_position_approved": "NO",
            "manual_followup": "REQUIRED",
        })
        results.append(entry)
    n = len(results)
    if sum(statuses.values()) != n:
        raise ValueError("Cross reference count invariant failed")
    return results, {
        "report_kind": "NAGOYA_STAGE5_GSI_OFFLINE_CROSS_REFERENCE_NOT_SITE_ACCEPTANCE",
        "source_dataset_sha256": queue_summary["source_dataset_sha256"],
        "provider": "DIGITAL_AGENCY_ABR",
        "provider_version": queue_summary["provider_version"],
        "provider_db_version": queue_summary["provider_db_version"],
        "gsi_source_page": OFFICIAL_GSI_PAGE,
        "gsi_csv_provenance": provenance,
        "private_review_queue_count": n,
        "status_counts": {key: statuses[key] for key in STATUS},
        "distance_bands_for_strict_unique_matches": {key: distances[key] for key in DISTANCE},
        "status_by_review_priority": {
            key: {st: breakdown[(key, st)] for st in STATUS}
            for key in (REVIEW_A_NEW, REVIEW_A_EXISTING, REVIEW_B_PARCEL)
        },
        "site_position_independently_verified": False,
        "gsi_city_coverage_not_guaranteed": True,
        "gsi_records_originated_from_municipal_registration": True,
        "notes": "Exact normalized name+address match and reference-point distance are evidence for manual review, never automatic facility acceptance",
        "original_pilot_unchanged": True,
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--gsi-emergency", type=Path)
    parser.add_argument("--gsi-shelter", type=Path)
    args = parser.parse_args()
    if not args.gsi_emergency and not args.gsi_shelter:
        parser.error("Provide at least one GSI CSV downloaded after accepting its terms")
    allowed = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != allowed and allowed not in folder.parents:
        parser.error("Review queue must remain in gitignored pilot data")
    sources = [(kind, path.resolve())
               for kind, path in (("emergency", args.gsi_emergency),
                                  ("shelter", args.gsi_shelter)) if path]
    if any(not (p == folder or folder in p.parents) for _, p in sources):
        parser.error("GSI source CSV must be inside the gitignored pilot directory")
    out_private = folder / "gsi_cross_reference_PRIVATE.csv"
    out_summary = folder / "gsi_cross_reference_aggregate.json"
    if out_private.exists() or out_summary.exists():
        parser.error("Existing Stage-5 output cannot be overwritten")
    try:
        queue, _ = read_csv(folder / "independent_facility_position_review_PRIVATE.csv")
        summary = json.loads((folder / "independent_review_queue_aggregate.json").read_text("utf-8"))
        gsi, provenance = parse_gsi(sources)
        details, aggregate = compare(queue, summary, gsi, provenance)
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=PRIVATE_COMPARISON_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        for row in details:
            writer.writerow({k: safe_csv_cell(row.get(k)) for k in PRIVATE_COMPARISON_FIELDS})
        with out_private.open("x", encoding="utf-8", newline="") as stream:
            stream.write(buffer.getvalue())
        with out_summary.open("x", encoding="utf-8") as stream:
            json.dump(aggregate, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, "Offline cross-reference aborted [" + type(exc).__name__ +
                    "]; no public information was written.\n")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
