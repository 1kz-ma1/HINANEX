import json
from datetime import datetime, timezone
from pathlib import Path

from src.hinanex.models.export import RegionExport
from src.hinanex.models.scenario import FacilityScenarioStatus, ScenarioJoinStatus
from src.hinanex.models.integration import (
    CapabilityManifestItem,
    RegionManifestItem,
    SourceManifestItem,
    ValidationManifest,
)
from src.hinanex.output import write_model_json
from src.hinanex.version import CONTRACT_SCHEMA_VERSION

EXPECTED_REGIONS: dict[str, tuple[str, str]] = {
    "edogawa": ("13123", "東京都江戸川区"),
    "niigata": ("15100", "新潟県新潟市"),
    "nagoya": ("23100", "愛知県名古屋市"),
}


def read_region_export(path: str | Path) -> RegionExport:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return RegionExport.model_validate(payload)


def validate_region_export(
    export: RegionExport,
    *,
    region_key: str | None = None,
) -> list[str]:
    """Return semantic contract errors that Pydantic alone cannot detect."""

    errors: list[str] = []

    if export.meta.schema_version != CONTRACT_SCHEMA_VERSION:
        errors.append(
            "schema_version mismatch: "
            f"expected={CONTRACT_SCHEMA_VERSION}, actual={export.meta.schema_version}"
        )

    if region_key is not None:
        expected = EXPECTED_REGIONS.get(region_key)
        if expected is None:
            errors.append(f"unknown region key: {region_key}")
        else:
            expected_code, expected_name = expected
            if export.region.code != expected_code or export.region.name != expected_name:
                errors.append(
                    "region identity mismatch: "
                    f"expected={expected_code}:{expected_name}, "
                    f"actual={export.region.code}:{export.region.name}"
                )

    nested = [
        *export.datasets,
        *export.assessments,
        *export.capabilities,
        *export.scenarios,
    ]
    for model in nested:
        if (
            model.region_code != export.region.code
            or model.region_name != export.region.name
        ):
            errors.append(
                f"nested region mismatch: {model.__class__.__name__} "
                f"{model.region_code}:{model.region_name}"
            )

    if export.meta.dataset_count != len(export.datasets):
        errors.append("meta.dataset_count does not match datasets length")
    if export.meta.assessment_count != len(export.assessments):
        errors.append("meta.assessment_count does not match assessments length")
    if export.meta.capability_count != len(export.capabilities):
        errors.append("meta.capability_count does not match capabilities length")
    if export.meta.gap_count != len(export.gaps):
        errors.append("meta.gap_count does not match gaps length")
    if export.meta.recommendation_count != len(export.recommendations):
        errors.append(
            "meta.recommendation_count does not match recommendations length"
        )

    evidence_count = sum(len(dataset.evidence) for dataset in export.datasets)
    if export.meta.evidence_count != evidence_count:
        errors.append("meta.evidence_count does not match dataset evidence count")

    requirement_codes = {dataset.requirement_code for dataset in export.datasets}
    assessment_requirement_codes = {
        assessment.requirement_code for assessment in export.assessments
    }

    missing_assessments = requirement_codes - assessment_requirement_codes
    if missing_assessments:
        errors.append(
            "dataset without assessment: " + ", ".join(sorted(missing_assessments))
        )

    for capability in export.capabilities:
        for dependency in capability.dependency_results:
            if dependency.requirement_code not in assessment_requirement_codes:
                errors.append(
                    "capability dependency without assessment: "
                    f"{capability.capability_code} -> {dependency.requirement_code}"
                )

    capability_codes = {
        capability.capability_code for capability in export.capabilities
    }
    # Investigation gaps can legitimately reference a requirement that has an
    # assessment (e.g. NOT_FOUND) but no normalized dataset. Do not require a
    # Dataset in that case.
    known_requirement_codes = requirement_codes | assessment_requirement_codes

    for gap in export.gaps:
        if gap.capability_code not in capability_codes:
            errors.append(
                f"gap references unknown capability: {gap.capability_code}"
            )
        if gap.requirement_code not in known_requirement_codes:
            errors.append(
                f"gap references unknown requirement: {gap.requirement_code}"
            )

    for recommendation in export.recommendations:
        if recommendation.capability_code not in capability_codes:
            errors.append(
                "recommendation references unknown capability: "
                f"{recommendation.capability_code}"
            )
        if recommendation.requirement_code not in known_requirement_codes:
            errors.append(
                "recommendation references unknown requirement: "
                f"{recommendation.requirement_code}"
            )


    # Scenario is an OPTIONAL additive extension. Existing location-only exports
    # remain valid. Every present result must trace to the formal location data.
    location_records = {
        record["id"]: record
        for dataset in export.datasets
        if dataset.requirement_code == "shelter_location"
        for record in dataset.records
        if isinstance(record, dict) and "id" in record
    }
    seen_scenarios: set[str] = set()
    for scenario in export.scenarios:
        if scenario.scenario_id in seen_scenarios:
            errors.append(f"duplicate scenario: {scenario.scenario_id}")
        seen_scenarios.add(scenario.scenario_id)
        if scenario.scenario_id != "flood_shelter_selection":
            errors.append(f"unsupported scenario: {scenario.scenario_id}")
        if scenario.requirement_assessment.requirement_code != "shelter_hazard_applicability":
            errors.append("scenario requirement_code mismatch")
        if scenario.requirement_assessment.record_count != len(scenario.facility_results):
            errors.append("scenario requirement record_count mismatch")
        facility_ids = [item.facility_id for item in scenario.facility_results]
        if len(set(facility_ids)) != len(facility_ids):
            errors.append("scenario contains duplicate facility IDs")
        if set(facility_ids) != set(location_records):
            errors.append("scenario does not trace exactly to shelter_location records")
        direct = 0
        raw_values = 0
        decided = 0
        for item in scenario.facility_results:
            fact = item.fact
            if fact.facility_id != item.facility_id:
                errors.append("scenario fact/result facility ID mismatch")
            if not fact.source_url.startswith(("https://", "http://")):
                errors.append("scenario official source URL missing")
            if fact.join_status == ScenarioJoinStatus.DIRECT_SAME_SOURCE:
                direct += 1
                if not fact.source_record_trace:
                    errors.append("same-source scenario fact missing raw-row trace")
            if fact.official_status_raw is not None:
                raw_values += 1
            if fact.usable_floor_raw is not None:
                # This is a trace field, not permission to upgrade a flood
                # outcome. Keep the original municipality marker unchanged.
                if fact.usable_floor_raw != fact.official_status_raw:
                    errors.append("scenario floor raw differs from official source raw")
                if (fact.hazard_scope_raw == "災害種別_洪水"
                        and item.status != FacilityScenarioStatus.UNKNOWN):
                    errors.append("Niigata floor restriction was classified without semantic acceptance")
            if item.status != FacilityScenarioStatus.UNKNOWN:
                decided += 1
                if fact.join_status != ScenarioJoinStatus.DIRECT_SAME_SOURCE:
                    errors.append("unverified join classified as scenario decision")
                if fact.hazard_scope_raw != "災害種別_洪水":
                    errors.append("combined/non-flood scope classified as flood-only decision")
                if fact.official_status_raw is None:
                    errors.append("missing raw value classified as scenario decision")
            if item.status == FacilityScenarioStatus.CANDIDATE and (
                fact.latitude is None or fact.longitude is None
            ):
                errors.append("scenario candidate lacks usable coordinates")
            source_location = location_records.get(item.facility_id)
            if source_location is not None:
                if (
                    fact.latitude != source_location.get("latitude")
                    or fact.longitude != source_location.get("longitude")
                ):
                    errors.append("scenario facts disagree with official location coordinates")
            # Until A obtains an official mapping for the city's ODS flood
            # column (Issue #48), a non-UNKNOWN result would invent meaning.
            if (fact.hazard_scope_raw == "災害種別_洪水"
                    and item.status != FacilityScenarioStatus.UNKNOWN):
                errors.append("Niigata ODS flood status requires official semantic acceptance")
        summary = scenario.requirement_assessment
        if summary.directly_joined_count != direct:
            errors.append("scenario directly_joined_count mismatch")
        if summary.raw_value_count != raw_values:
            errors.append("scenario raw_value_count mismatch")
        if decided == 0 and scenario.status.value != "UNKNOWN":
            errors.append("undecidable scenario must be UNKNOWN")
        if decided == len(scenario.facility_results) and decided > 0 and scenario.status.value != "FULL":
            errors.append("fully decided scenario must be FULL")
        if 0 < decided < len(scenario.facility_results) and scenario.status.value != "DEGRADED":
            errors.append("partly decided scenario must be DEGRADED")

    return errors


def assert_valid_region_export(
    export: RegionExport,
    *,
    region_key: str | None = None,
) -> None:
    errors = validate_region_export(export, region_key=region_key)
    if errors:
        detail = "\n  - ".join(errors)
        raise ValueError(f"RegionExport contract validation failed:\n  - {detail}")


def build_validation_manifest(
    contracts: dict[str, tuple[str | Path, RegionExport]],
) -> ValidationManifest:
    region_items: list[RegionManifestItem] = []

    for key, (path, export) in contracts.items():
        assert_valid_region_export(export, region_key=key)

        sources = [
            SourceManifestItem(
                source_name=evidence.source_name,
                source_url=evidence.source_url,
                publisher=evidence.publisher,
                source_format=evidence.source_format,
                published_at=evidence.published_at,
                fetched_at=evidence.fetched_at,
            )
            for dataset in export.datasets
            for evidence in dataset.evidence
        ]

        capability_items: list[CapabilityManifestItem] = []
        for capability in export.capabilities:
            gap_count = sum(
                gap.capability_code == capability.capability_code
                for gap in export.gaps
            )
            recommendation_count = sum(
                recommendation.capability_code == capability.capability_code
                for recommendation in export.recommendations
            )
            capability_items.append(
                CapabilityManifestItem(
                    capability_code=capability.capability_code,
                    capability_name=capability.capability_name,
                    status=capability.status,
                    gap_count=gap_count,
                    recommendation_count=recommendation_count,
                )
            )

        region_items.append(
            RegionManifestItem(
                key=key,
                region=export.region,
                contract_path=str(path).replace("\\", "/"),
                dataset_count=len(export.datasets),
                record_count=sum(len(dataset.records) for dataset in export.datasets),
                requirement_codes=sorted(
                    {dataset.requirement_code for dataset in export.datasets}
                ),
                sources=sources,
                capabilities=capability_items,
            )
        )

    return ValidationManifest(
        generated_at=datetime.now(timezone.utc),
        all_valid=True,
        regions=region_items,
        checks=[
            f"All contracts validated against schema_version {CONTRACT_SCHEMA_VERSION}.",
            "Region identity is consistent across every nested artifact.",
            "Meta counts match the actual arrays.",
            "Every dataset has an assessment.",
            "Capability dependencies resolve to assessments.",
            "Gap/Recommendation references resolve to known requirements/capabilities.",
        ],
    )


def write_validation_manifest(
    contracts: dict[str, tuple[str | Path, RegionExport]],
    output_path: str | Path = "data/output/manifest.json",
) -> Path:
    manifest = build_validation_manifest(contracts)
    return write_model_json(manifest, output_path)
