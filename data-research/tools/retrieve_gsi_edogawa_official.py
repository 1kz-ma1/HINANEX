"""A-only: fetch GSI national designated-emergency-evacuation CSV and extract Edogawa.

Source is the GSI-published all-municipality designated emergency evacuation
place CSV, NOT designated shelters or municipality water-standby facilities.
This code performs no D cross-source join, official designation acceptance,
flood eligibility promotion, or live-open-status assessment.

python data-research/tools/retrieve_gsi_edogawa_official.py \
  --out-dir /outside-git/gsi-edogawa-unreviewed
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import ipaddress
import json
import math
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import unicodedata

OFFICIAL_GSI_NATIONAL_CSV_URL = (
    "https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv"
)
OFFICIAL_INDEX_URL = (
    "https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
)
TARGET_MUNICIPALITY = "東京都江戸川区"
MAX_ORIGINAL_BYTES = 130_000_000
REQUIRED_COLUMNS = {
    "NO", "共通ID", "都道府県名及び市町村名",
    "施設・場所名", "住所", "洪水", "緯度", "経度",
}
REVIEW_TOKENS = ("葛西工科", "関東第一", "下小岩")
PURPOSE = "A_GSI_EDOGAWA_EVIDENCE_ONLY_NEVER_APPROVED"


class GsiEvidenceFailure(ValueError):
    pass


def _safe_official_url(url):
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "hinanmap.gsi.go.jp" or
            p.username is not None or p.password is not None or
            p.port not in (None, 443) or p.fragment or p.query):
        raise GsiEvidenceFailure("GSI origin is not approved HTTPS host")
    if p.path != urlsplit(OFFICIAL_GSI_NATIONAL_CSV_URL).path:
        raise GsiEvidenceFailure("GSI response is not the official national evacuation CSV")


def fetch_national_csv(timeout=100):
    _safe_official_url(OFFICIAL_GSI_NATIONAL_CSV_URL)
    req = Request(
        OFFICIAL_GSI_NATIONAL_CSV_URL,
        headers={"User-Agent": "HINANEX-A-GSI-unreviewed-evidence/1.0"},
    )
    with urlopen(req, timeout=timeout) as resp:
        if resp.getcode() != 200:
            raise GsiEvidenceFailure("GSI original HTTPS response was not HTTP 200")
        final_url = resp.geturl()
        _safe_official_url(final_url)
        raw = resp.read(MAX_ORIGINAL_BYTES + 1)
        if not 0 < len(raw) <= MAX_ORIGINAL_BYTES:
            raise GsiEvidenceFailure("GSI national original empty or above bound")
        return raw, final_url, {
            "content_type": resp.headers.get("Content-Type"),
            "last_modified": resp.headers.get("Last-Modified"),
            "etag": resp.headers.get("ETag"),
        }


def inspect_original(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ORIGINAL_BYTES:
        raise GsiEvidenceFailure("No valid original GSI bytes")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise GsiEvidenceFailure("GSI CSV is not expected UTF-8 text") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    columns = reader.fieldnames
    if (not columns or len(set(columns)) != len(columns)
            or not REQUIRED_COLUMNS.issubset(columns)):
        raise GsiEvidenceFailure(
            "GSI original header differs from published national emergency-place CSV schema"
        )
    if len(columns) < 17:
        raise GsiEvidenceFailure("Unexpectedly short GSI designated-emergency-place header")
    total = 0
    edogawa = []
    found_ids = set()
    for row in reader:
        total += 1
        if None in row or any(v is None for v in row.values()):
            raise GsiEvidenceFailure("GSI original malformed row: " + str(total))
        area = unicodedata.normalize("NFKC", row["都道府県名及び市町村名"])
        if area != TARGET_MUNICIPALITY:
            continue
        if not row["施設・場所名"].strip() or not row["住所"].strip():
            raise GsiEvidenceFailure("Edogawa GSI row lacks name/address")
        uid = row["共通ID"].strip()
        if not uid or uid in found_ids:
            raise GsiEvidenceFailure("Edogawa GSI common ID absent/duplicated")
        found_ids.add(uid)
        raw_flood = row["洪水"].strip()
        if raw_flood not in ("", "1"):
            raise GsiEvidenceFailure("Unexpected GSI flood marker; do not interpret")
        for k in ("緯度", "経度"):
            try:
                val = float(row[k])
            except ValueError as exc:
                raise GsiEvidenceFailure("Invalid GSI coordinate") from exc
            if not math.isfinite(val):
                raise GsiEvidenceFailure("Nonfinite GSI coordinate")
            if (k == "緯度" and not -90 <= val <= 90 or
                    k == "経度" and not -180 <= val <= 180):
                raise GsiEvidenceFailure("GSI coordinate out of range")
        edogawa.append({
            "original_national_csv_row": total + 1,
            "original_columns_unmodified": {k: row[k] for k in columns},
            "common_gsi_id_is_not_d_facility_id": True,
            "gsi_flood_marker_raw": row["洪水"],
            "physical_site_link_c_approved": False,
            "current_d_flood_scenario_change": None,
        })
    if total == 0:
        raise GsiEvidenceFailure("GSI national data CSV contains no records")
    leads = [
        {"original_national_csv_row": item["original_national_csv_row"],
         "original_gsi_common_id": item["original_columns_unmodified"]["共通ID"],
         "name_raw": item["original_columns_unmodified"]["施設・場所名"],
         "matched_keyword_for_review_only": next(
             token for token in REVIEW_TOKENS
             if token in unicodedata.normalize(
                 "NFKC", item["original_columns_unmodified"]["施設・場所名"]
             )
         ),
         "not_a_d_join_or_verified_pair": True}
        for item in edogawa
        if any(token in unicodedata.normalize(
            "NFKC", item["original_columns_unmodified"]["施設・場所名"]
        ) for token in REVIEW_TOKENS)
    ]
    return columns, total, edogawa, leads


def capture(out_dir, fetch=fetch_national_csv, now=None):
    folder = Path(out_dir)
    if (folder.is_symlink() or
            (folder.exists() and
             (not folder.is_dir() or any(folder.iterdir())))):
        raise GsiEvidenceFailure("GSI archive destination must be new/empty")
    raw, final, headers = fetch()
    _safe_official_url(final)
    if not isinstance(headers, dict):
        raise GsiEvidenceFailure("GSI HTTP headers missing")
    columns, total, rows, leads = inspect_original(raw)
    snapshot = {
        "purpose": PURPOSE,
        "captured_at_utc": (now or datetime.now(timezone.utc)).isoformat(),
        "requested_url": OFFICIAL_GSI_NATIONAL_CSV_URL,
        "final_url": final,
        "official_publisher": "Geospatial Information Authority of Japan",
        "official_index_url": OFFICIAL_INDEX_URL,
        "national_source_sha256": sha256(raw).hexdigest(),
        "national_source_bytes": len(raw),
        "original_csv_header": columns,
        "national_record_count_observed": total,
        "municipality_search_exact": TARGET_MUNICIPALITY,
        "edogawa_record_count_observed": len(rows),
        "edogawa_absence_is_not_nonpublication": True,
        "http_content_type": headers.get("content_type"),
        "http_last_modified": headers.get("last_modified"),
        "http_etag": headers.get("etag"),
        "official_database_updated_at_verified": None,
        "official_municipal_designation_effective_date": None,
        "publication_scope_and_coverage_review_required": True,
        "source_hazard_values_are_not_application_suitability": True,
        "source_gsi_id_is_not_shared_with_d": True,
        "human_c_physical_pairs_approved": 0,
        "new_flood_candidates_or_exclusions": 0,
    }
    report = {
        "status": ("GSI_EDOGAWA_ROWS_FOUND_UNREVIEWED"
                   if rows else "GSI_EDOGAWA_ROWS_NOT_OBSERVED_REVIEW_REQUIRED"),
        "source_manifest": snapshot,
        "edogawa_rows": rows,
        "priority_keyword_leads_for_human_review_only": leads,
        "source_semantics": "GSI designated emergency evacuation places, not municipal standby facilities",
        "none_of_this_data_was_joined_to_current_d": True,
        "independent_c_site_approvals": 0,
        "new_flood_classifications": 0,
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "gsi_national_original_UNREVIEWED.csv").write_bytes(raw)
    (folder / "gsi_manifest_UNREVIEWED.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "gsi_edogawa_review_UNREVIEWED.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = capture(args.out_dir)
    except (GsiEvidenceFailure, OSError, TimeoutError) as exc:
        parser.exit(2, "GSI A evidence acquisition failed (no approval): " + str(exc) + "\n")
    print(json.dumps({
        "status": report["status"],
        "national_records": report["source_manifest"]["national_record_count_observed"],
        "edogawa_rows": report["source_manifest"]["edogawa_record_count_observed"],
        "keyword_review_leads": len(report["priority_keyword_leads_for_human_review_only"]),
        "human_c_approved": 0,
        "new_flood_classifications": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
