from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter
from src.hinanex.adapters.nagoya_shelter import NagoyaShelterAdapter
from src.hinanex.adapters.niigata_shelter import NiigataShelterAdapter
from src.hinanex.integration import EXPECTED_REGIONS
from src.hinanex.version import CONTRACT_SCHEMA_VERSION, PROJECT_RELEASE


FORMAL_REQUIREMENT_CODE = "shelter_location"
SHELTER_CAPABILITY_CODE = "shelter_discovery"

ADAPTER_SOURCE_PAGES: dict[str, str] = {
    EdogawaShelterAdapter.REGION_CODE: EdogawaShelterAdapter.SOURCE_PAGE_URL,
    NiigataShelterAdapter.REGION_CODE: NiigataShelterAdapter.SOURCE_PAGE_URL,
    NagoyaShelterAdapter.REGION_CODE: NagoyaShelterAdapter.SOURCE_PAGE_URL,
}


def load_json(path: str | Path) -> dict:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8"))


def _canonical_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def _expected_region_codes() -> dict[str, str]:
    return {
        region_name: region_code
        for region_code, region_name in EXPECTED_REGIONS.values()
    }


def validate_a_handoff(payload: dict) -> list[str]:
    """Validate the A handoff assumptions that D currently supports."""

    errors: list[str] = []

    if payload.get("project") != "HINANEX":
        errors.append("handoff.project must be HINANEX")

    contract = payload.get("contract")
    if not isinstance(contract, dict):
        return [*errors, "handoff.contract must be an object"]

    if contract.get("region_export_schema_version") != CONTRACT_SCHEMA_VERSION:
        errors.append(
            "A/D RegionExport schema mismatch: "
            f"A={contract.get('region_export_schema_version')}, "
            f"D={CONTRACT_SCHEMA_VERSION}"
        )

    if contract.get("project_release") != PROJECT_RELEASE:
        errors.append(
            "A/D project release mismatch: "
            f"A={contract.get('project_release')}, D={PROJECT_RELEASE}"
        )

    actual_region_codes = contract.get("region_codes")
    if actual_region_codes != _expected_region_codes():
        errors.append(
            "A/D region codes mismatch: "
            f"A={actual_region_codes}, D={_expected_region_codes()}"
        )

    formal_codes = contract.get("current_formal_requirement_codes")
    if not isinstance(formal_codes, list):
        errors.append("current_formal_requirement_codes must be an array")
        formal_code_set: set[str] = set()
    else:
        formal_code_set = {code for code in formal_codes if isinstance(code, str)}

    expected_formal_codes = {FORMAL_REQUIREMENT_CODE}
    if formal_code_set != expected_formal_codes:
        errors.append(
            "A/D formal requirement codes mismatch: "
            f"A={sorted(formal_code_set)}, D={sorted(expected_formal_codes)}"
        )

    evidence_manifest = payload.get("evidence_manifest")
    if not isinstance(evidence_manifest, list):
        return [*errors, "evidence_manifest must be an array"]

    unexpected_formal_codes = sorted(
        {
            item.get("requirement_code")
            for item in evidence_manifest
            if isinstance(item, dict)
            and item.get("requirement_code") is not None
            and item.get("requirement_code") not in expected_formal_codes
        }
    )
    if unexpected_formal_codes:
        errors.append(
            "A handoff contains requirement_code values not implemented by D: "
            + ", ".join(unexpected_formal_codes)
        )

    expected_by_code = {
        region_code: region_name
        for region_code, region_name in EXPECTED_REGIONS.values()
    }

    for region_code, region_name in expected_by_code.items():
        matching = [
            item
            for item in evidence_manifest
            if isinstance(item, dict)
            and item.get("region_code") == region_code
            and item.get("region_name") == region_name
            and item.get("requirement_code") == FORMAL_REQUIREMENT_CODE
        ]

        if not matching:
            errors.append(
                f"A handoff has no {FORMAL_REQUIREMENT_CODE} evidence for "
                f"{region_code}:{region_name}"
            )
            continue

        expected_source = _canonical_url(ADAPTER_SOURCE_PAGES[region_code])
        matching_sources = {
            _canonical_url(item.get("source_url"))
            for item in matching
        }

        if expected_source not in matching_sources:
            errors.append(
                f"A/D official source mismatch for {region_code}:{region_name}: "
                f"D adapter page={ADAPTER_SOURCE_PAGES[region_code]}"
            )

    return errors


def validate_region_exports_against_handoff(
    handoff: dict,
    exports: dict[str, dict],
) -> list[str]:
    """Cross-check D RegionExport traceability against the committed A handoff.

    Existing RegionExport semantic validation remains authoritative. This check
    only verifies the A -> D integration seam and intentionally does not copy
    A's discovery_status into D assessments.
    """

    errors = validate_a_handoff(handoff)
    if errors:
        return errors

    evidence_manifest = handoff["evidence_manifest"]
    handoff_schema = handoff["contract"]["region_export_schema_version"]

    for region_key, (region_code, region_name) in EXPECTED_REGIONS.items():
        export = exports.get(region_key)
        if not isinstance(export, dict):
            errors.append(f"missing RegionExport for {region_key}")
            continue

        region = export.get("region") or {}
        if (
            region.get("code") != region_code
            or region.get("name") != region_name
        ):
            errors.append(
                f"{region_key}: region identity mismatch in RegionExport"
            )

        meta = export.get("meta") or {}
        if meta.get("schema_version") != handoff_schema:
            errors.append(
                f"{region_key}: RegionExport schema does not match A handoff"
            )

        a_evidence = [
            item
            for item in evidence_manifest
            if isinstance(item, dict)
            and item.get("region_code") == region_code
            and item.get("requirement_code") == FORMAL_REQUIREMENT_CODE
        ]
        if not a_evidence:
            errors.append(
                f"{region_key}: A has no formal shelter_location evidence"
            )

        datasets = [
            item
            for item in export.get("datasets", [])
            if isinstance(item, dict)
            and item.get("requirement_code") == FORMAL_REQUIREMENT_CODE
        ]
        if len(datasets) != 1:
            errors.append(
                f"{region_key}: expected exactly one shelter_location dataset, "
                f"got {len(datasets)}"
            )
        elif not datasets[0].get("evidence"):
            errors.append(
                f"{region_key}: shelter_location dataset has no D evidence"
            )

        assessments = [
            item
            for item in export.get("assessments", [])
            if isinstance(item, dict)
            and item.get("requirement_code") == FORMAL_REQUIREMENT_CODE
        ]
        if len(assessments) != 1:
            errors.append(
                f"{region_key}: expected exactly one shelter_location assessment, "
                f"got {len(assessments)}"
            )

        capabilities = [
            item
            for item in export.get("capabilities", [])
            if isinstance(item, dict)
            and item.get("capability_code") == SHELTER_CAPABILITY_CODE
        ]
        if len(capabilities) != 1:
            errors.append(
                f"{region_key}: expected exactly one shelter_discovery capability, "
                f"got {len(capabilities)}"
            )
        else:
            dependencies = capabilities[0].get("dependency_results") or []
            if not any(
                isinstance(item, dict)
                and item.get("requirement_code") == FORMAL_REQUIREMENT_CODE
                for item in dependencies
            ):
                errors.append(
                    f"{region_key}: shelter_discovery does not depend on "
                    "shelter_location"
                )

    return errors


def assert_a_d_integration(
    handoff: dict,
    exports: dict[str, dict],
) -> None:
    errors = validate_region_exports_against_handoff(handoff, exports)
    if errors:
        detail = "\n  - ".join(errors)
        raise ValueError(f"A-D integration validation failed:\n  - {detail}")
