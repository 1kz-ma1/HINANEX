"""Read-only, fail-closed flood scenario selection for an already evaluated snapshot.

This internal D helper does not certify official source semantics, positions,
opening status, or safety. It never interprets raw symbols or changes a status.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from datetime import datetime
from urllib.parse import urlsplit

from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.scenario import (
    FacilityScenarioStatus, ScenarioJoinStatus, ScenarioResult,
)


@dataclass(frozen=True)
class SelectionRow:
    facility_id: str
    facility_name: str
    status: FacilityScenarioStatus
    reason: str
    hazard_scope_raw: str
    official_status_raw: str | None
    source_url: str
    source_record_trace: str | None
    coordinates_present: bool


@dataclass(frozen=True)
class SelectionResult:
    """Counts describe the full snapshot, even when visible rows are filtered."""

    region_code: str
    evaluated_at: datetime
    rows: tuple[SelectionRow, ...]
    total_count: int
    candidate_count: int
    excluded_count: int
    unknown_count: int
    result_kind: str  # HAS_ROWS / NO_MATCH / NO_DATA


def _require_https(url: str) -> None:
    if not isinstance(url, str) or not url or url != url.strip():
        raise ValueError("source URL must be a nonempty HTTPS URL")
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or
            parts.username is not None or parts.password is not None or
            any(ord(character) < 32 for character in url)):
        raise ValueError("source URL must be a nonempty HTTPS URL")


def _coordinate_pair(latitude: object, longitude: object) -> bool:
    for value, minimum, maximum in ((latitude, -90, 90), (longitude, -180, 180)):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or
            not isfinite(value) or not minimum <= value <= maximum
        ):
            raise ValueError("invalid location coordinates")
    return latitude is not None and longitude is not None


def select_flood_scenario(
    scenario: ScenarioResult,
    location: NormalizedDataset,
    *,
    region_code: str,
    hazard: str,
    expected_evaluated_at: datetime,
    source_urls_by_facility: Mapping[str, str],
    include_statuses: tuple[FacilityScenarioStatus, ...] = (
        FacilityScenarioStatus.CANDIDATE,
        FacilityScenarioStatus.EXCLUDED,
        FacilityScenarioStatus.UNKNOWN,
    ),
) -> SelectionResult:
    """Validate a pinned snapshot, then filter without reclassifying any facility.

    The caller must obtain source URL pins independently from the evaluated
    rows. URL equality is *not* evidence of human source approval. The scenario
    timestamp only detects stale/mixed computations, not official freshness.
    """
    if not isinstance(region_code, str) or not region_code.strip():
        raise ValueError("region_code is required")
    if (hazard != "flood" or scenario.hazard != "flood" or
            scenario.scenario_id != "flood_shelter_selection"):
        raise ValueError("unsupported hazard or scenario")
    if (location.requirement_code != "shelter_location" or
            region_code != location.region_code or
            region_code != scenario.region_code):
        raise ValueError("region or location requirement mismatch")
    if (not isinstance(expected_evaluated_at, datetime) or
            expected_evaluated_at.tzinfo is None or
            expected_evaluated_at.utcoffset() is None or
            scenario.evaluated_at.tzinfo is None or
            scenario.evaluated_at.utcoffset() is None or
            expected_evaluated_at != scenario.evaluated_at):
        raise ValueError("scenario evaluation timestamp mismatch")
    if (not isinstance(include_statuses, tuple) or not include_statuses or
            any(not isinstance(status, FacilityScenarioStatus) for status in include_statuses) or
            len(set(include_statuses)) != len(include_statuses)):
        raise ValueError("include_statuses must contain unique known statuses")

    records = location.records
    ids = [record.get("id") for record in records]
    results = scenario.facility_results
    result_ids = [row.facility_id for row in results]
    if (any(not isinstance(facility_id, str) or not facility_id.strip() for facility_id in ids) or
            len(set(ids)) != len(ids) or
            any(not facility_id.strip() for facility_id in result_ids) or
            len(set(result_ids)) != len(result_ids) or set(ids) != set(result_ids)):
        raise ValueError("location and scenario must contain matching unique facility IDs")
    if not isinstance(source_urls_by_facility, Mapping) or set(source_urls_by_facility) != set(ids):
        raise ValueError("exact independently supplied source URL pins are required")
    assessment = scenario.requirement_assessment
    if (assessment.requirement_code != "shelter_hazard_applicability" or
            assessment.record_count != len(results) or
            assessment.directly_joined_count != sum(
                row.fact.join_status == ScenarioJoinStatus.DIRECT_SAME_SOURCE for row in results
            ) or
            assessment.raw_value_count != sum(
                row.fact.official_status_raw is not None for row in results
            )):
        raise ValueError("scenario assessment counts do not match its rows")

    location_by_id = {record["id"]: record for record in records}
    rows = []
    counts = {status: 0 for status in FacilityScenarioStatus}
    for item in results:
        fact = item.fact
        if (fact.facility_id != item.facility_id or
                not fact.facility_name.strip() or not item.reason.strip() or
                not fact.hazard_scope_raw.strip()):
            raise ValueError("invalid facility result or fact association")
        _require_https(fact.source_url)
        if source_urls_by_facility[item.facility_id] != fact.source_url:
            raise ValueError("scenario source URL differs from the pinned source")
        # An UNKNOWN from combined hazard sources must remain available for review.
        # Positive/negative classifications require a direct same-source flood
        # record; raw symbols themselves are NEVER translated here.
        if item.status != FacilityScenarioStatus.UNKNOWN and (
            fact.join_status != ScenarioJoinStatus.DIRECT_SAME_SOURCE or
            fact.hazard_scope_raw != "災害種別_洪水" or
            fact.official_status_raw is None or not fact.official_status_raw.strip() or
            not fact.source_record_trace or not fact.source_record_trace.strip()
        ):
            raise ValueError("decided status lacks a directly joined flood source")
        located = location_by_id[item.facility_id]
        fact_coordinates = _coordinate_pair(fact.latitude, fact.longitude)
        location_coordinates = _coordinate_pair(
            located.get("latitude"), located.get("longitude")
        )
        # Presence never conveys coordinate approval; only check consistency.
        if fact_coordinates != location_coordinates or (fact_coordinates and (
            fact.latitude != located["latitude"] or
            fact.longitude != located["longitude"]
        )):
            raise ValueError("scenario and location coordinates disagree")
        counts[item.status] += 1
        if item.status in include_statuses:
            rows.append(SelectionRow(
                facility_id=item.facility_id,
                facility_name=fact.facility_name,
                status=item.status,
                reason=item.reason,
                hazard_scope_raw=fact.hazard_scope_raw,
                official_status_raw=fact.official_status_raw,
                source_url=fact.source_url,
                source_record_trace=fact.source_record_trace,
                coordinates_present=fact_coordinates,
            ))
    rows.sort(key=lambda row: row.facility_id)
    return SelectionResult(
        region_code=region_code,
        evaluated_at=scenario.evaluated_at,
        rows=tuple(rows),
        total_count=len(results),
        candidate_count=counts[FacilityScenarioStatus.CANDIDATE],
        excluded_count=counts[FacilityScenarioStatus.EXCLUDED],
        unknown_count=counts[FacilityScenarioStatus.UNKNOWN],
        result_kind="NO_DATA" if not results else "HAS_ROWS" if rows else "NO_MATCH",
    )
