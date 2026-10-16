"""Compare two separately verified Edogawa source snapshots; NO site approval.

Requires two complete raw archives made by the existing allowlisted C capture:
  python validation/validation/compare_edogawa_source_snapshots.py \
    --before /outside-git/capture-old --after /outside-git/capture-new \
    --report /outside-git/source-changes-UNREVIEWED.json

This is intentionally an operator-only, read-only C review aid, not a
source freshness claim, source replacement, site join, D status update,
or network downloader. The original files and report remain outside Git.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from archive_edogawa_official_sources import SOURCES, SnapshotFailure, verify_snapshot
from validate_edogawa_official_archive import (
    ContentPreflightFailure, validate,
)


class ComparisonFailure(ValueError):
    """Independent source review cannot safely proceed."""


def _load_verified(folder: Path):
    try:
        verify_snapshot(folder)  # rejects tampered/missing bytes, forged approvals
        preflight = validate(folder)  # rejects 200-OK wrong-content documents
        manifest = json.loads(
            (folder / "snapshot_manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError, SnapshotFailure, ContentPreflightFailure) as exc:
        raise ComparisonFailure(
            "Source snapshot integrity/content preflight failed; no approval"
        ) from exc
    items = {item["source_key"]: item for item in manifest["source_items"]}
    return manifest, preflight, items


def compare(before: Path, after: Path):
    """Report precise byte deltas without interpreting official policy meaning.

    The unreviewed HTTP metadata is copied as a *hint* only, not a certified
    effective/publication date. Data source sets and UTC timestamps are already
    checked by verify_snapshot; the comparison cannot weaken those guards.
    """
    before, after = Path(before), Path(after)
    if before.resolve() == after.resolve():
        raise ComparisonFailure("Two independent source directories are required")
    original, old_content, old = _load_verified(before)
    current, new_content, new = _load_verified(after)

    old_time = datetime.fromisoformat(original["captured_at_utc"])
    new_time = datetime.fromisoformat(current["captured_at_utc"])
    if new_time <= old_time:
        raise ComparisonFailure("After snapshot must have a later UTC capture time")

    sources = []
    for key in SOURCES:  # same allowlist, no inferred or silently added sources
        earlier, later = old[key], new[key]
        changed = earlier["sha256"] != later["sha256"]
        sources.append({
            "source_key": key,
            "requested_url": earlier["requested_url"],
            "raw_bytes_changed": changed,
            "previous_sha256": earlier["sha256"],
            "current_sha256": later["sha256"],
            "previous_byte_size": earlier["byte_size"],
            "current_byte_size": later["byte_size"],
            "previous_http_last_modified_unverified": earlier.get("http_last_modified"),
            "current_http_last_modified_unverified": later.get("http_last_modified"),
            "previous_http_etag_unverified": earlier.get("http_etag"),
            "current_http_etag_unverified": later.get("http_etag"),
            "official_publication_or_effective_date": None,
            "human_source_revision_review_required": changed,
            "same_physical_facility_approved": False,
        })

    changed = [item["source_key"] for item in sources
               if item["raw_bytes_changed"]]
    return {
        "status": ("SOURCE_BYTES_CHANGED_REVIEW_REQUIRED" if changed else
                   "BYTE_IDENTICAL_SNAPSHOTS_REVIEW_PENDING"),
        "previous_captured_at_utc": original["captured_at_utc"],
        "current_captured_at_utc": current["captured_at_utc"],
        "official_source_count": len(SOURCES),
        "changed_source_count": len(changed),
        "changed_source_keys": changed,
        "sources": sources,
        "content_shape_comparison": {
            "previous_water_rows": old_content["official_water_rows"],
            "current_water_rows": new_content["official_water_rows"],
            "previous_location_csv_rows": old_content["location_csv_rows"],
            "current_location_csv_rows": new_content["location_csv_rows"],
        },
        "byte_comparison_does_not_prove_publication_date_or_source_authenticity": True,
        "source_revision_human_review_completed": False,
        "physical_site_identity_human_review_completed": False,
        "approved_cross_source_pairs": 0,
        "flood_scenario_classifications_added": 0,
        "live_opening_or_safety_evaluated": False,
        "gsi_flood_designation_inferred_from_municipal_water_source": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        parser.error("Report already exists: refusing to overwrite")
    report_path = args.report.resolve()
    for folder in (args.before, args.after):
        if report_path.is_relative_to(folder.resolve()):
            parser.error("Comparison report must be stored outside original archives")
    try:
        report = compare(args.before, args.after)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (ComparisonFailure, OSError, ValueError) as exc:
        parser.exit(2, "C source comparison blocked (NO APPROVAL): " + str(exc) + "\n")
    print(json.dumps({
        "status": report["status"],
        "changed_sources": report["changed_source_count"],
        "c_identity_approvals": 0,
        "flood_classifications_added": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
