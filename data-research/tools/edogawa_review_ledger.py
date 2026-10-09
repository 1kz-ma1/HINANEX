"""Offline A research tool: create ONLY proposed cross-source Edogawa row links.

Usage:
  python data-research/tools/edogawa_review_ledger.py \
    --water-html /local/official-water-page.html \
    --region-export /local/pipeline/data/output/edogawa.json \
    --location-csv /local/pipeline/data/raw/edogawa/20251211_hinanhokan.csv \
    --out /local/evidence/edogawa-review.json

The output NEVER contains VERIFIED_PAIR or a flood eligibility classification.
Raw source bytes must remain outside Git; C must independently confirm each row.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

WATER_URL = ("https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/"
             "kanrenmap/hazardmap/ikinaihinan.html")
LOCATION_URL = "https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv"
EXPECTED_COLUMNS = ("番号", "名称", "住所", "電話番号", "使用可能階数")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("Nested source table is ambiguous")
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def official_rows(html_bytes):
    parser = Tables()
    parser.feed(html_bytes.decode("utf-8-sig"))
    rows = []
    for table_idx, table in enumerate(parser.tables):
        if not table:
            continue
        header = tuple(c.strip() for c in table[0])
        if header != EXPECTED_COLUMNS:
            continue
        for row_idx, values in enumerate(table[1:], start=2):
            if len(values) != len(EXPECTED_COLUMNS):
                raise ValueError("Water source row has unexpected number of columns")
            entry = dict(zip(EXPECTED_COLUMNS, values))
            if not entry["名称"] or not entry["住所"]:
                raise ValueError("Water source row missing name/address")
            rows.append({
                "source_record_trace": f"table={table_idx+1};row={row_idx}",
                "number_raw": entry["番号"],
                "name_raw": entry["名称"],
                "address_raw": entry["住所"],
                "phone_raw": entry["電話番号"],
                "usable_floor_raw": entry["使用可能階数"],
                "source_url": WATER_URL,
            })
    if not rows:
        raise ValueError("Official HTML has no exact named water facility table")
    return rows


def name_hint(value):
    """Only remove a literal municipality table note; NEVER assert identity."""
    return re.sub(r"(?:\(注\)|（注）)$", "", value.strip()).strip()


def proposal(water_raw, export_raw, location_raw):
    doc = json.loads(export_raw)
    if str(doc.get("region", {}).get("code")) != "13123":
        raise ValueError("Only Edogawa RegionExport is supported")
    datasets = [
        d for d in doc.get("datasets", [])
        if d.get("requirement_code") == "shelter_location"
    ]
    if len(datasets) != 1:
        raise ValueError("Expected precisely one Edogawa shelter_location dataset")
    records = datasets[0]["records"]
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate D facility IDs")
    archive_header = list(next(csv.reader(location_raw.decode("cp932").lstrip("\ufeff").splitlines())))
    if not {"名称", "緯度", "経度"}.issubset(archive_header):
        raise ValueError("Official location CSV required columns unavailable")
    address_cols = [v for v in ("住所", "所在地") if v in archive_header]
    by_name = defaultdict(list)
    for record in records:
        by_name[name_hint(record["name"])].append(record)
    proposals = []
    for row in official_rows(water_raw):
        suggestions = by_name.get(name_hint(row["name_raw"]), [])
        conflicting = len(suggestions) > 1
        candidates = []
        for candidate in suggestions:
            address = candidate.get("address")
            same_address = (
                address.strip() == row["address_raw"].strip()
                if isinstance(address, str) and address.strip() else None
            )
            if same_address is False:
                conflicting = True
            candidates.append({
                "location_facility_id": candidate["id"],
                "location_name_raw": candidate["name"],
                "location_address_raw": address,
                "address_raw_exact_match": same_address,
                "matching_basis": "NAME_HINT_ONLY_NOT_VERIFIED",
            })
        proposals.append({
            **row,
            "review_status": "CONFLICT" if conflicting else "UNREVIEWED",
            "candidate_location_rows": candidates,
            "review_required": "A and C independent row-level identification; hazard scope D/C decision",
            "flood_scenario_status": "UNCHANGED_UNKNOWN",
        })
    return {
        "purpose": "A evidence-only manual review; NEVER use as approved joins",
        "region_code": "13123",
        "source_documents": [
            {"url": WATER_URL, "sha256": digest(water_raw), "type": "municipal_water_html"},
            {"url": LOCATION_URL, "sha256": digest(location_raw), "type": "municipal_location_csv"},
            {"url": "local RegionExport (not an official source)",
             "sha256": digest(export_raw), "type": "D_normalized_output"},
        ],
        "location_csv_columns": archive_header,
        "location_csv_has_address_field": bool(address_cols),
        "record_count_from_current_export": len(records),
        "official_water_rows_found": len(proposals),
        "only_name_hint_proposals": sum(bool(x["candidate_location_rows"]) for x in proposals),
        "all_reviewed_pairs": 0,
        "all_scenario_classifications_added": 0,
        "rows": proposals,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--water-html", type=Path, required=True)
    ap.add_argument("--location-csv", type=Path, required=True)
    ap.add_argument("--region-export", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    output = proposal(args.water_html.read_bytes(),
                      args.region_export.read_bytes(),
                      args.location_csv.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"UNREVIEWED report written: {args.out}; "
          f"water rows={output['official_water_rows_found']}; "
          f"name-only proposals={output['only_name_hint_proposals']}; "
          "verified=0; Scenario decisions=0")


if __name__ == "__main__":
    main()
