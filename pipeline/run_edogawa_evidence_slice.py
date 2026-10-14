"""Produce a standalone current-D Edogawa RegionExport from a pinned official archive.

This is a ONE-REGION replay of the existing D evaluation functions, not a new
hazard join or a substitute for the complete three-region D acceptance suite.
Never changes data/output or the running frontend. Raw/outputs stay outside Git.

python pipeline/run_edogawa_evidence_slice.py \
  --archive-dir /external/official-YYYYMMDD/raw-unreviewed \
  --output-dir /external/current-d-edogawa
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter
from src.hinanex.evaluation.shelter_location import assess_shelter_location
from src.hinanex.evaluation.capability import assess_shelter_discovery
from src.hinanex.evaluation.gap import analyze_capability_gap
from src.hinanex.export import build_region_export
from src.hinanex.flood_scenario import evaluate_flood_scenario
from src.hinanex.integration import assert_valid_region_export
from src.hinanex.models.scenario import FacilityScenarioStatus, ScenarioJoinStatus
from src.hinanex.output import write_model_json
from src.hinanex.scenario_sources import EDOGAWA_HAZARD_SOURCE, edogawa_facts


class EdogawaReplayError(ValueError):
    pass


def _source_item(manifest, key, expected_url):
    if not isinstance(manifest, dict):
        raise EdogawaReplayError("Missing official archive manifest object")
    items = manifest.get("source_items")
    if not isinstance(items, list) or len(items) != 7:
        raise EdogawaReplayError("Expected a 7-source official evidence archive")
    found = [x for x in items if isinstance(x, dict) and x.get("source_key") == key]
    if len(found) != 1:
        raise EdogawaReplayError("Missing or duplicate official source entry: " + key)
    item = found[0]
    if item.get("requested_url") != expected_url:
        raise EdogawaReplayError("Original official source URL changed: " + key)
    final = item.get("final_url")
    if not isinstance(final, str) or urlsplit(final).scheme != "https":
        raise EdogawaReplayError("Original source final HTTPS URL absent: " + key)
    if urlsplit(final).hostname != urlsplit(expected_url).hostname:
        raise EdogawaReplayError("Source publisher changed: " + key)
    if type(item.get("byte_size")) is not int or type(item.get("sha256")) is not str:
        raise EdogawaReplayError("Original source size/digest not recorded: " + key)
    return item


def _pinned_input(archive_dir, manifest, key, filename, official_url):
    item = _source_item(manifest, key, official_url)
    if item.get("archive_filename") != filename:
        raise EdogawaReplayError("Unexpected archive file name: " + key)
    path = archive_dir / filename
    if path.is_symlink() or not path.is_file():
        raise EdogawaReplayError("Missing/unsafe official raw evidence: " + key)
    raw = path.read_bytes()
    if (not raw or len(raw) != item["byte_size"] or
            sha256(raw).hexdigest() != item["sha256"]):
        raise EdogawaReplayError("Official raw byte SHA256 mismatch: " + key)
    return raw


def replay(archive_dir: Path, output_dir: Path):
    archive_dir, output_dir = Path(archive_dir), Path(output_dir)
    if archive_dir.is_symlink() or not archive_dir.is_dir():
        raise EdogawaReplayError("Official archive directory missing or unsafe")
    if output_dir.is_symlink() or (output_dir.exists() and
                                    (not output_dir.is_dir() or any(output_dir.iterdir()))):
        raise EdogawaReplayError("Output directory must be new or empty")

    try:
        manifest = json.loads(
            (archive_dir / "snapshot_manifest.json").read_text(encoding="utf-8")
        )
    except (ValueError, OSError) as exc:
        raise EdogawaReplayError("Official capture manifest unreadable") from exc
    if (manifest.get("purpose") !=
            "C_EVIDENCE_ARCHIVE_ONLY_NO_C_INDEPENDENT_ACCEPTANCE" or
            manifest.get("human_c_reviewer_signed_off") is not False or
            manifest.get("flood_scenario_classifications_added") != 0):
        raise EdogawaReplayError("Source manifest purports to grant disaster approval")

    adapter = EdogawaShelterAdapter()
    location_csv = _pinned_input(
        archive_dir, manifest, "municipal_locations",
        "municipal_locations.csv", adapter.SOURCE_URL,
    )
    water_html = _pinned_input(
        archive_dir, manifest, "water_facilities",
        "water_facilities.html", EDOGAWA_HAZARD_SOURCE,
    )
    try:
        dataset = adapter.normalize(location_csv)
        assessment = assess_shelter_location(dataset)
        capability = assess_shelter_discovery([assessment])
        gap_analysis = analyze_capability_gap(capability, [assessment])
        scenario = evaluate_flood_scenario(dataset, edogawa_facts(dataset))
        export = build_region_export(
            datasets=[dataset],
            assessments=[assessment],
            capabilities=[capability],
            gap_analyses=[gap_analysis],
            scenarios=[scenario],
        )
        assert_valid_region_export(export, region_key="edogawa")
    except (KeyError, TypeError, ValueError) as exc:
        raise EdogawaReplayError("Current D Edogawa pipeline failed closed") from exc

    records = dataset.records
    results = scenario.facility_results
    if (not records or len(results) != len(records) or
            any(r.status != FacilityScenarioStatus.UNKNOWN or
                r.fact.join_status != ScenarioJoinStatus.UNVERIFIED or
                r.fact.official_status_raw is not None or
                r.fact.source_record_trace is not None
                for r in results)):
        raise EdogawaReplayError("Unreviewed cross-source hazard facts were classified")
    if (scenario.requirement_assessment.directly_joined_count != 0 or
            scenario.requirement_assessment.raw_value_count != 0 or
            scenario.status.value != "UNKNOWN"):
        raise EdogawaReplayError("Unreviewed flood scenario was upgraded")

    report = {
        "status": "CURRENT_D_EDOGAWA_EVIDENCE_PINNED_NOT_FLOOD_APPROVED",
        "region_code": "13123",
        "source_snapshot_captured_at_utc": manifest.get("captured_at_utc"),
        "official_raw_sha256": {
            "municipal_locations": sha256(location_csv).hexdigest(),
            "water_facilities": sha256(water_html).hexdigest(),
        },
        "source_archive_evidence_bytes_checked": (
            len(location_csv) + len(water_html)
        ),
        "d_location_count": len(records),
        "d_unique_location_ids": len({r["id"] for r in records}),
        "d_scenario_count": len(export.scenarios),
        "d_scenario_facility_status_counts": dict(Counter(
            r.status.value for r in results
        )),
        "d_scenario_join_counts": dict(Counter(
            r.fact.join_status.value for r in results
        )),
        "source_water_html_is_unjoined_evidence": True,
        "d_shelter_discovery_status": capability.status.value,
        "d_flood_scenario_status": scenario.status.value,
        "c_human_independent_site_identity_accepted": False,
        "approved_cross_source_pairs": 0,
        "new_flood_candidates_or_exclusions": 0,
        "not_full_three_region_pipeline_or_deployment": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_model_json(export, output_dir / "edogawa_current_D_UNREVIEWED.json")
    (output_dir / "edogawa_D_source_trace_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = replay(args.archive_dir, args.output_dir)
    except (EdogawaReplayError, OSError) as exc:
        parser.exit(2, "Edogawa D replay rejected: " + str(exc) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
