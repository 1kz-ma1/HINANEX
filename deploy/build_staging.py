"""Build the public HINANEX staging bundle for Render Static Site."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

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

    manifest = runtime_output / "manifest.json"
    if manifest.is_file():
        shutil.copy2(manifest, published_output / "manifest.json")

    shutil.copy2(staging_template, output_dir / "index.html")

    build_meta = {
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
    build_bundle(root, output, run_pipeline=not args.skip_pipeline)


if __name__ == "__main__":
    main()
