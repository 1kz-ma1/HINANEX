"""Offline normalization of one archived, official GSI skhb01 flood GeoJSON tile.

Fetch raw separately from documented HTTPS GSI address and keep archived bytes.
A/C must verify the original source and search scope independently.
"""
import argparse
import json
from pathlib import Path

from src.hinanex.flood_site_reference import extract_gsi_flood_tile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, choices=["13123", "15100", "23100"])
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--source-url", required=True, help="Exact HTTPS GSI skhb01 tile URL")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = extract_gsi_flood_tile(args.raw.read_bytes(), args.source_url, args.region)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PREPARED (NOT C-ACCEPTED): {len(records)} GSI flood features -> {args.out}")


if __name__ == "__main__":
    main()
