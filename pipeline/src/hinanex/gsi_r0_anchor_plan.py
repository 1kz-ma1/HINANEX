"""R0 candidate *tile* plan from a user-supplied, cited non-shelter anchor.

A reference coordinate must be explicitly provided with its source URL; no
geocoding, location inference, user GPS, HTTP, or official-tile retrieval.
The source URL is a citation claim, NOT cryptographic provenance validation.
Output is exactly the plan accepted by gsi_r0_pilot_batch (Draft PR #390).
"""
from __future__ import annotations

import argparse
import json
from math import asinh, floor, isfinite, pi, radians, tan
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from src.hinanex.gsi_r0_pilot_batch import PLAN_SCHEMA, _validate_pilots

_DMS = re.compile(r"([0-9]{1,3}):([0-9]{1,2}):([0-9]{1,2})\Z")
_WEB_MERCATOR_MAX_LAT = 85.0511287798
_Z = 10
_N = 1 << _Z


class AnchorPlanInvalid(ValueError):
    pass


def dms_degrees(dms: str, *, longitude: bool) -> float:
    """Parse explicit positive east-longitude / north-latitude D:M:S."""
    if not isinstance(dms, str) or (match := _DMS.fullmatch(dms)) is None:
        raise AnchorPlanInvalid("EXPLICIT_DMS_DEGREES_MINUTES_SECONDS_REQUIRED")
    degrees, minutes, seconds = map(int, match.groups())
    limit = 180 if longitude else 90
    if (degrees > limit or minutes >= 60 or seconds >= 60
            or (degrees == limit and (minutes != 0 or seconds != 0))):
        raise AnchorPlanInvalid("DMS_OUT_OF_GEOGRAPHIC_RANGE")
    result = degrees + minutes / 60 + seconds / 3600
    if not longitude and result >= _WEB_MERCATOR_MAX_LAT:
        raise AnchorPlanInvalid("LATITUDE_OUTSIDE_WEB_MERCATOR")
    return result


def anchor_tile(*, east_longitude_dms: str, north_latitude_dms: str) -> dict:
    """A mathematical z10 tile calculation, never a facility geocoding claim."""
    lon = dms_degrees(east_longitude_dms, longitude=True)
    lat = dms_degrees(north_latitude_dms, longitude=False)
    if not (isfinite(lon) and isfinite(lat)):
        raise AnchorPlanInvalid("ANCHOR_COORDINATE_NOT_FINITE")
    x = floor((lon + 180.0) / 360.0 * _N)
    y = floor((1 - asinh(tan(radians(lat))) / pi) / 2 * _N)
    if not (0 <= x < _N and 0 <= y < _N):
        raise AnchorPlanInvalid("ANCHOR_OUTSIDE_Z10_TILE_RANGE")
    return {"z": _Z, "x": x, "y": y}


def build_candidate(
    *,
    a_x: int, a_y: int,
    b_longitude_dms: str, b_latitude_dms: str,
    b_reference_url: str,
) -> tuple[dict, dict]:
    """Return a compatible plan and a separate conservative evidence summary.

    No support for claiming B is an accepted municipality or a verified GSI
    data source. Exact A/B hazard source URLs are generated later by D #390.
    """
    if (type(a_x) is not int or type(a_y) is not int
            or not 0 <= a_x < _N or not 0 <= a_y < _N):
        raise AnchorPlanInvalid("A_TILE_MUST_BE_EXPLICIT_Z10_XY")
    if not isinstance(b_reference_url, str):
        raise AnchorPlanInvalid("REFERENCE_URL_REQUIRED")
    try:
        ref = urlsplit(b_reference_url)
    except ValueError as exc:
        raise AnchorPlanInvalid("REFERENCE_URL_INVALID") from exc
    if (ref.scheme != "https" or not ref.hostname
            or ref.username is not None or ref.password is not None
            or ref.port is not None or ref.query or ref.fragment
            or not ref.path or ref.path == "/"):
        raise AnchorPlanInvalid("REFERENCE_MUST_BE_DIRECT_HTTPS_URL")
    # This is a format check, not proof the page was actually visited.
    if not (ref.hostname.endswith(".go.jp") or ref.hostname.endswith(".lg.jp")):
        raise AnchorPlanInvalid("REFERENCE_MUST_BE_JAPANESE_PUBLIC_DOMAIN")
    b_tile = anchor_tile(
        east_longitude_dms=b_longitude_dms,
        north_latitude_dms=b_latitude_dms,
    )
    plan = {
        "schema": PLAN_SCHEMA,
        "pilots": [
            {"slot": "A", "tile": {"z": _Z, "x": a_x, "y": a_y}},
            {"slot": "B", "tile": b_tile},
        ],
    }
    _validate_pilots(plan)
    # The separate report preserves the original source citation; the D plan
    # cannot contain invented administrative fields under its strict schema.
    evidence = {
        "status": "R0_CANDIDATE_TILE_ONLY_SOURCES_NOT_ACQUIRED",
        "reference_class": "MANUAL_GEOGRAPHIC_REFERENCE_NOT_SITE_EVIDENCE",
        "reference_url_claimed": b_reference_url,
        "reference_url_content_verified_by_tool": False,
        "reference_coordinates": {
            "east_longitude_dms": b_longitude_dms,
            "north_latitude_dms": b_latitude_dms,
        },
        "a_tile": plan["pilots"][0]["tile"],
        "b_tile": plan["pilots"][1]["tile"],
        "same_tile": False,
        "gsi_skhb01_source_available": "NOT_TESTED",
        "gsi_skhb02_source_available": "NOT_TESTED",
        "official_municipal_boundary_verified": False,
        "geographic_distance_verified": False,
        "reference_is_emergency_shelter": "NOT_EVALUATED",
        "c_independent_acceptance": "NOT_GRANTED",
        "human_review": "DEFERRED_TO_HUMAN_BATCH_REVIEW",
        "publication_approval": "NOT_GRANTED",
        "note": (
            "Reference coordinate yields a z10 tile only. It is not shelter "
            "geolocation, municipality-wide coverage, actual GSI tile existence, "
            "hazard safety, or a license/publication approval."
        ),
    }
    return plan, evidence


def _output_path(value: Path) -> Path:
    if not isinstance(value, Path) or not value.is_absolute() or value.suffix != ".json":
        raise AnchorPlanInvalid("PLAN_OUTPUT_MUST_BE_ABSOLUTE_JSON_PATH")
    path = value.resolve(strict=False)
    repo_root = Path(__file__).resolve().parents[3]
    if path.is_relative_to(repo_root):
        raise AnchorPlanInvalid("PLAN_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    if not path.parent.is_dir() or path.exists() or value.is_symlink():
        raise AnchorPlanInvalid("PLAN_OUTPUT_PARENT_OR_OVERWRITE_INVALID")
    return path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a-x", type=int, required=True)
    p.add_argument("--a-y", type=int, required=True)
    p.add_argument("--b-lon-dms", required=True, help="positive east longitude D:M:S")
    p.add_argument("--b-lat-dms", required=True, help="positive north latitude D:M:S")
    p.add_argument("--b-reference-url", required=True, help="official source citation, not auto-verified")
    p.add_argument("--plan-out", type=Path, required=True, help="new file outside Git")
    args = p.parse_args()
    try:
        plan, evidence = build_candidate(
            a_x=args.a_x, a_y=args.a_y,
            b_longitude_dms=args.b_lon_dms,
            b_latitude_dms=args.b_lat_dms,
            b_reference_url=args.b_reference_url,
        )
        dest = _output_path(args.plan_out)
        with dest.open("x", encoding="utf-8") as fp:
            json.dump(plan, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    except (AnchorPlanInvalid, ValueError, OSError) as exc:
        print(f"R0_ANCHOR_PLAN_HOLD:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
