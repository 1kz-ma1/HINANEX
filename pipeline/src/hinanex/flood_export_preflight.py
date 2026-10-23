"""Offline, read-only RegionExport consistency preflight for the flood UI.

This is NOT an A/C official-source approval, a signed attestation, an update
check, or a publication authorization. It never edits RegionExport or source.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

from src.hinanex.models.assessment import CapabilityStatus
from src.hinanex.models.export import RegionExport
from src.hinanex.models.scenario import FacilityScenarioStatus
from src.hinanex.scenario_selection import SelectionResult, select_flood_scenario


REQUIRED_PINS = frozenset({
    "region_code", "export_sha256", "scenario_evaluated_at",
    "source_urls_by_facility", "review_reference",
})


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json_bytes(content: bytes) -> Any:
    if not isinstance(content, bytes) or not content:
        raise ValueError("nonempty JSON bytes required")
    return json.loads(content.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)


def select_from_region_export(
    export: RegionExport,
    *,
    region_code: str,
    expected_evaluated_at: datetime,
    source_urls_by_facility: dict[str, str],
) -> SelectionResult:
    """Reuse #302's selector; refuse any unapproved positive/negative status.

    As of 2026-10-23 all three region flood semantics are UNKNOWN.
    Lifting this guard requires independent A/C evidence, a reviewed D
    semantics change, and a separate authorization decision.
    """
    if export.region.code != region_code:
        raise ValueError("RegionExport region does not match supplied region")
    locations = [d for d in export.datasets if d.requirement_code == "shelter_location"]
    scenarios = [s for s in export.scenarios if s.scenario_id == "flood_shelter_selection"]
    if len(locations) != 1 or len(scenarios) != 1:
        raise ValueError("exactly one shelter_location and one flood scenario required")
    location, scenario = locations[0], scenarios[0]
    if (location.region_name != export.region.name or
            scenario.region_name != export.region.name):
        raise ValueError("RegionExport region names differ from source records")
    if (scenario.status != CapabilityStatus.UNKNOWN or
            any(item.status != FacilityScenarioStatus.UNKNOWN
                for item in scenario.facility_results)):
        raise ValueError("non-UNKNOWN flood interpretation lacks approval under current policy")
    return select_flood_scenario(
        scenario, location, region_code=region_code, hazard="flood",
        expected_evaluated_at=expected_evaluated_at,
        source_urls_by_facility=source_urls_by_facility,
    )


def audit_export_bytes(export_bytes: bytes, pin_bytes: bytes) -> dict[str, Any]:
    """Check a separately supplied pin manifest against a saved exported JSON.

    Passing means snapshot integrity/shape consistency ONLY. Supplying one's
    own self-generated pins is not independent evidence; human/source
    acceptance must be separately documented and checked.
    """
    pins = _parse_json_bytes(pin_bytes)
    if not isinstance(pins, dict) or pins.keys() != REQUIRED_PINS:
        raise ValueError("pin manifest has missing or unexpected fields")
    region = pins["region_code"]
    digest = pins["export_sha256"]
    reference = pins["review_reference"]
    urls = pins["source_urls_by_facility"]
    if (not isinstance(region, str) or not region.strip() or
            not isinstance(reference, str) or not reference.strip()):
        raise ValueError("pin region_code and review_reference must be nonempty text")
    if (not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None or
            sha256(export_bytes).hexdigest() != digest):
        raise ValueError("RegionExport bytes do not match expected snapshot SHA256")
    if (not isinstance(urls, dict) or
            any(not isinstance(k, str) or not isinstance(v, str)
                for k, v in urls.items())):
        raise ValueError("source_urls_by_facility must be a string map")
    stamp = pins["scenario_evaluated_at"]
    if not isinstance(stamp, str):
        raise ValueError("scenario_evaluated_at must be an ISO-8601 timestamp")
    try:
        evaluated_at = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise ValueError("invalid scenario_evaluated_at") from exc
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("scenario_evaluated_at must be timezone-aware")

    export = RegionExport.model_validate(_parse_json_bytes(export_bytes))
    selected = select_from_region_export(
        export, region_code=region, expected_evaluated_at=evaluated_at,
        source_urls_by_facility=urls,
    )
    return {
        "result": "SNAPSHOT_CONSISTENCY_ONLY",
        "region_code": region,
        "total_count": selected.total_count,
        "unknown_count": selected.unknown_count,
        "candidate_count": selected.candidate_count,
        "excluded_count": selected.excluded_count,
        "result_kind": selected.result_kind,
        "review_reference": reference,
        "official_source_acceptance": "NOT_ESTABLISHED",
        "official_source_freshness": "NOT_ESTABLISHED",
        "location_approval": "NOT_ESTABLISHED",
        "evacuation_safety": "NOT_ESTABLISHED",
        "publication_authorized": False,
    }
