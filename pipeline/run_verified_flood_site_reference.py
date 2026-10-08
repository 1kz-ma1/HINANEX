"""Build an opt-in flood designated-place catalog from C-approved archived GeoJSON.

No network access, municipality matching, raw marker guessing, or geocoding.
Input records + C acceptance MUST be produced from an independent raw audit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from src.hinanex.flood_site_reference import build_flood_site_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, choices=["13123", "15100", "23100"])
    parser.add_argument("--raw", type=Path, required=True, help="Archived GSI skhb01 GeoJSON bytes")
    parser.add_argument("--records", type=Path, required=True, help="A/C-audited normalized records JSON list")
    parser.add_argument("--c-acceptance", type=Path, required=True, help="C independently generated PASS JSON")
    parser.add_argument("--out", type=Path, required=True, help="Separate additive reference catalog JSON")
    args = parser.parse_args()

    records = json.loads(args.records.read_text(encoding="utf-8"))
    acceptance = json.loads(args.c_acceptance.read_text(encoding="utf-8"))
    data = build_flood_site_catalog(
        args.region,
        records,
        raw_archive=args.raw.read_bytes(),
        c_acceptance=acceptance,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.region}: {data['status']} / {len(data['sites'])} reference-only records -> {args.out}")


if __name__ == "__main__":
    main()
