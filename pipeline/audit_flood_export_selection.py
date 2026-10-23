"""Read-only D flood-snapshot consistency preflight.

Usage from pipeline/:
 python audit_flood_export_selection.py --export data/output/edogawa.json \
   --pins /path/to/independently-reviewed-pin-manifest.json

Neither path is changed. A successful exit is NOT approval to publish.
"""
import argparse
import json
from pathlib import Path

from src.hinanex.flood_export_preflight import audit_export_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--pins", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_export_bytes(args.export.read_bytes(), args.pins.read_bytes())
    except (ValueError, OSError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
