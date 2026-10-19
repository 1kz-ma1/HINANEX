"""D read-only comparison of TWO already generated, independent RegionExport sets.

This tool never fetches, regenerates, overwrites, merges or approves any data.
It must not be used to bypass A/C source-version, facility identity or safety review.
Run at the pipeline root with two existing private output snapshots.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from src.hinanex.integration import (
    EXPECTED_REGIONS,
    assert_valid_region_export,
    read_region_export,
)


class ReplayComparisonError(ValueError):
    """The input is incomplete, ambiguous or insufficiently independent."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _digest_object(obj: object) -> str:
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _check_input_dirs(before: Path, after: Path, report: Path | None) -> None:
    for directory in (before, after):
        if directory.is_symlink() or not directory.is_dir():
            raise ReplayComparisonError("Inputs must be existing non-symlink directories")
        if directory.resolve() == Path.cwd().resolve():
            raise ReplayComparisonError("Use separate output snapshot directories, not the repository root")
    if before.resolve() == after.resolve():
        raise ReplayComparisonError("Two independent snapshot directories are required")
    if before.resolve() in after.resolve().parents or after.resolve() in before.resolve().parents:
        raise ReplayComparisonError("Nested snapshot directories are prohibited")
    if report is not None:
        if report.exists() or report.is_symlink():
            raise ReplayComparisonError("Refusing to overwrite an existing comparison report")
        resolved = report.resolve()
        for directory in (before, after):
            if directory.resolve() == resolved or directory.resolve() in resolved.parents:
                raise ReplayComparisonError("Comparison report must stay outside both snapshots")
        # Forbid recording outputs inside the tracked D project tree.
        pipeline_dir = Path(__file__).resolve().parent
        if resolved == pipeline_dir or pipeline_dir in resolved.parents:
            raise ReplayComparisonError("Comparison report must stay outside the pipeline checkout")


def _load_set(directory: Path) -> dict[str, tuple[object, Path]]:
    exports = {}
    for key in EXPECTED_REGIONS:
        source = directory / f"{key}.json"
        if source.is_symlink() or not source.is_file():
            raise ReplayComparisonError(f"{key}: missing or symlinked input RegionExport")
        try:
            export = read_region_export(source)
            assert_valid_region_export(export, region_key=key)
        except (OSError, ValueError) as exc:
            raise ReplayComparisonError(f"{key}: RegionExport contract validation failed: {exc}") from exc
        exports[key] = (export, source)
    return exports


def _one_summary(export: object, source: Path) -> dict:
    dataset = next((d for d in export.datasets if d.requirement_code == "shelter_location"), None)
    if dataset is None:
        raise ReplayComparisonError("Formal shelter_location dataset missing")
    ids = []
    missing_coords = 0
    for record in dataset.records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"]:
            raise ReplayComparisonError("Location records require nonempty original identifiers")
        ids.append(record["id"])
        if record.get("latitude") is None or record.get("longitude") is None:
            missing_coords += 1
    if len(ids) != len(set(ids)):
        raise ReplayComparisonError("Duplicate location record identifiers")
    evidence = [e.model_dump(mode="json") for ds in export.datasets for e in ds.evidence]
    if not evidence:
        raise ReplayComparisonError("RegionExport contains no source Evidence")
    caps = {c.capability_code: c.status.value for c in export.capabilities}
    if len(caps) != len(export.capabilities):
        raise ReplayComparisonError("Duplicate Capability codes")
    metrics = Counter()
    for item in export.assessments:
        for category in (item.data_quality, item.application_readiness):
            for metric in vars(category).values():
                score = metric.score
                metrics["null" if score is None else "zero" if score == 0 else "positive"] += 1
    scenarios = {}
    for scenario in export.scenarios:
        counts = Counter(item.status.value for item in scenario.facility_results)
        joins = Counter(item.fact.join_status.value for item in scenario.facility_results)
        scenarios[scenario.scenario_id] = {
            "capability_status": scenario.status.value,
            "facility_status_counts": dict(sorted(counts.items())),
            "join_status_counts": dict(sorted(joins.items())),
            "record_count": len(scenario.facility_results),
        }
    return {
        "artifact_sha256": _sha256(source),
        "region_code": export.region.code,
        "schema_version": export.meta.schema_version,
        "location_records": len(ids),
        "location_record_ids_sha256": _digest_object(sorted(ids)),
        "missing_location_coordinates": missing_coords,
        "source_evidence_count": len(evidence),
        "source_evidence_metadata_sha256": _digest_object(sorted(evidence, key=lambda e: json.dumps(e, sort_keys=True))),
        "assessment_metric_scores": dict(sorted(metrics.items())),
        "capability_statuses": dict(sorted(caps.items())),
        "gap_count": len(export.gaps),
        "recommendation_count": len(export.recommendations),
        "scenarios": dict(sorted(scenarios.items())),
        "generated_at": export.meta.generated_at.isoformat(),
    }


def compare_replays(before: Path, after: Path, report: Path | None = None) -> dict:
    before, after = Path(before), Path(after)
    _check_input_dirs(before, after, report)
    earlier = _load_set(before)
    later = _load_set(after)
    regions = {}
    for key in EXPECTED_REGIONS:
        old = _one_summary(*earlier[key])
        new = _one_summary(*later[key])
        if old["region_code"] != new["region_code"]:
            raise ReplayComparisonError(f"{key}: source region identity changed")
        checks = {}
        for field in ("schema_version", "location_records", "location_record_ids_sha256",
                      "missing_location_coordinates", "source_evidence_count", "source_evidence_metadata_sha256",
                      "assessment_metric_scores", "capability_statuses", "gap_count", "recommendation_count",
                      "scenarios", "artifact_sha256"):
            if old[field] != new[field]:
                checks[field] = {"before": old[field], "after": new[field]}
        regions[key] = {"before": old, "after": new, "observed_changes": checks}
    return {
        "status": "UNREVIEWED_REQUIRES_INDEPENDENT_C_AUDIT",
        "data_promotion_authorized": False,
        "human_source_review_verified": False,
        "raw_original_source_sha256_verified_by_this_tool": False,
        "executed_pipeline_or_network": False,
        "region_count": len(regions),
        "regions": regions,
        "limitations": [
            "Export artifact SHA256 is NOT original publisher source SHA256",
            "Source Evidence fields are metadata; raw-row and source-version checks require independent C review",
            "Numeric counts and status changes are observations, never hazard or safety approvals",
            "This read-only report never certifies A/C human signoffs or authorizes data deployment",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="Already generated earlier private D output directory")
    parser.add_argument("--after", type=Path, required=True, help="Already generated later private D output directory")
    parser.add_argument("--report", type=Path, required=True, help="Fresh JSON report path outside Git and both snapshots")
    args = parser.parse_args()
    try:
        result = compare_replays(args.before, args.after, args.report)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except (ReplayComparisonError, OSError, ValueError) as exc:
        parser.exit(2, f"D replay comparison blocked (NO DATA PROMOTION): {exc}\n")
    print(json.dumps({"status": result["status"],
                      "changed_regions": [k for k, v in result["regions"].items() if v["observed_changes"]],
                      "data_promotion_authorized": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())