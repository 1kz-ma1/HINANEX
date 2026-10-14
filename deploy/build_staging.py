"""Build the public HINANEX staging bundle for Render Static Site."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

# Support direct execution as python deploy/build_staging.py as well as imports.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))
from deploy.publish_gsi_staging import (GSI_DEMO_TILES, build_official_reference_tile)

REQUIRED_EXPORTS = {
    "edogawa.json": "13123",
    "niigata.json": "15100",
    "nagoya.json": "23100",
}
REQUIRED_TOP_LEVEL = (
    "region",
    "datasets",
    "assessments",
    "capabilities",
    "gaps",
    "recommendations",
    "meta",
)


class StagingBuildError(RuntimeError):
    """Raised when the staging bundle cannot be built safely."""


def _load_region_export(path: Path, expected_region_code: str) -> dict[str, Any]:
    if not path.is_file():
        raise StagingBuildError(f"Required RegionExport is missing: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StagingBuildError(f"Invalid RegionExport JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise StagingBuildError(f"RegionExport must be a JSON object: {path}")

    missing = [key for key in REQUIRED_TOP_LEVEL if key not in payload]
    if missing:
        raise StagingBuildError(
            f"RegionExport is missing required top-level fields {missing}: {path}"
        )

    region = payload.get("region")
    if not isinstance(region, dict) or region.get("code") != expected_region_code:
        actual = region.get("code") if isinstance(region, dict) else None
        raise StagingBuildError(
            "RegionExport filename/region mismatch: "
            f"{path.name} expected {expected_region_code}, got {actual}"
        )

    for key in ("datasets", "assessments", "capabilities", "gaps", "recommendations"):
        if not isinstance(payload.get(key), list):
            raise StagingBuildError(f"RegionExport.{key} must be an array: {path}")

    if not isinstance(payload.get("meta"), dict):
        raise StagingBuildError(f"RegionExport.meta must be an object: {path}")

    return payload


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise StagingBuildError(f"Required static directory is missing: {source}")
    shutil.copytree(source, destination)


def build_bundle(
    root: Path,
    output_dir: Path,
    *,
    run_pipeline: bool = True,
    publish_official_gsi: bool | None = None,
    gsi_opener=None,
) -> Path:
    """Generate runtime RegionExports and assemble the static staging bundle."""

    root = root.resolve()
    output_dir = output_dir.resolve()
    pipeline_dir = root / "pipeline"
    runtime_output = pipeline_dir / "data" / "output"
    staging_template = root / "deploy" / "staging-index.html"

    if run_pipeline:
        try:
            subprocess.run(
                [sys.executable, "run_all_workflows.py"],
                cwd=pipeline_dir,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise StagingBuildError("D Pipeline failed; staging deploy is aborted.") from exc

    exports: dict[str, dict[str, Any]] = {}
    for filename, region_code in REQUIRED_EXPORTS.items():
        exports[filename] = _load_region_export(
            runtime_output / filename,
            region_code,
        )

    if not staging_template.is_file():
        raise StagingBuildError(f"Staging landing page is missing: {staging_template}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    _copy_tree(root / "frontend", output_dir / "frontend")
    _copy_tree(root / "gis" / "gis", output_dir / "gis" / "gis")

    published_output = output_dir / "pipeline" / "data" / "output"
    published_output.mkdir(parents=True)
    for filename in REQUIRED_EXPORTS:
        shutil.copy2(runtime_output / filename, published_output / filename)

    # Render's normal build performs current official GSI acquisition and
    # independent C→D→E verification. Offline/skip-pipeline test builds remain
    # deterministic unless explicitly opting in with an injected opener.
    if publish_official_gsi is None:
        publish_official_gsi = run_pipeline
    gsi_publication = {"status": "NOT_REQUESTED", "verified_tiles": []}
    if publish_official_gsi:
        gsi_publication = {"status": "BLOCKED_UNVERIFIED_SOURCE", "verified_tiles": []}
        for region_code, z, x, y in GSI_DEMO_TILES:
            try:
                kwargs = {"opener": gsi_opener} if gsi_opener is not None else {}
                verified = build_official_reference_tile(
                    published_output / "gsi_verified_tiles",
                    region_code=region_code, z=z, x=x, y=y, **kwargs,
                )
                gsi_publication["verified_tiles"].append(verified)
            except (ValueError, OSError, HTTPError, URLError) as exc:
                # Keep D and C presentations available. Crucially, do not
                # publish any GSI JSON if the C or HTTPS audit failed.
                print("GSI OFFICIAL REFERENCE BLOCKED (not an empty source tile): " +
                      type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        if gsi_publication["verified_tiles"]:
            gsi_publication["status"] = "PARTIAL_VERIFIED_REFERENCE_ONLY"

    evidence_source = root / "validation" / "demo" / "2019_edogawa_evidence_cases.json"
    if not evidence_source.is_file():
        raise StagingBuildError("Required C presentation evidence manifest is missing")
    try:
        evidence_data = json.loads(evidence_source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StagingBuildError("Invalid C presentation evidence manifest") from exc
    if not (
        isinstance(evidence_data, dict)
        and evidence_data.get("schema_id") == "hinanex.c.midterm_explanation_cases.v0.1"
        and evidence_data.get("historical_replay_executed") is False
        and evidence_data.get("historical_prediction_approved") is False
        and evidence_data.get("human_c_approved") is False
        and evidence_data.get("approved_actual_building_pairs") == 0
        and evidence_data.get("prediction_denominator") is None
        and isinstance(evidence_data.get("cases"), list)
        and [c.get("id") for c in evidence_data["cases"] if isinstance(c, dict)] == ["trace", "abstain", "negative"]
        and all(c.get("real_prediction_finding") is None for c in evidence_data["cases"] if isinstance(c, dict))
    ):
        raise StagingBuildError("C presentation evidence must remain unapproved and non-predictive")

    published_evidence = output_dir / "evidence" / "2019_edogawa_evidence_cases.json"
    published_evidence.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(evidence_source, published_evidence)

    manifest = runtime_output / "manifest.json"
    if manifest.is_file():
        shutil.copy2(manifest, published_output / "manifest.json")

    shutil.copy2(staging_template, output_dir / "index.html")

    build_meta = {
        "gsi_reference_publication": gsi_publication,
        "regions": {
            filename: {
                "region_code": payload["region"]["code"],
                "region_name": payload["region"].get("name"),
            }
            for filename, payload in exports.items()
        },
        "paths": {
            "frontend": "/frontend/",
            "gis": "/gis/gis/",
            "region_exports": "/pipeline/data/output/",
            "historical_evidence": "/evidence/2019_edogawa_evidence_cases.json",
        },
    }
    (output_dir / "_staging.json").write_text(
        json.dumps(build_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("HINANEX staging bundle ready")
    print(f"publish path: {output_dir}")
    for filename in REQUIRED_EXPORTS:
        print(f"RegionExport: {published_output / filename}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-gsi",
        action="store_true",
        help="Explicitly omit official GSI publication (D-only staging)",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Use existing pipeline/data/output files instead of regenerating them.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override the staging publish directory.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = args.output or (root / "deploy" / "dist")
    build_bundle(
        root, output, run_pipeline=not args.skip_pipeline,
        publish_official_gsi=not (args.skip_pipeline or args.skip_gsi),
    )


if __name__ == "__main__":
    main()
