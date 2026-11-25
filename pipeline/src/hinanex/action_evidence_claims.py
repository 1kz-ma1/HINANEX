"""Untrusted source/report claims for synthetic evacuation-action reviews.

A matching URL, hash and claimed audit cannot authorize an evacuation action.
No network, live hazard data, GIS join, source approval or persistence here.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from src.hinanex.action_context import HazardKind
from src.hinanex.action_context_multi import (
    CueAvailability, MultiHazardActionReview, MultiHazardDrill,
    _evidence_categories, review_multi_hazard_drill,
)

_ID = r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$"
_DIGEST = r"^[0-9a-f]{64}$"
_SCOPE = r"^[a-zA-Z0-9][a-zA-Z0-9_./:-]{0,127}$"


class CoverageKind(str, Enum):
    MUNICIPAL_REGION = "MUNICIPAL_REGION"
    GSI_TILE = "GSI_TILE"


class ReportedOutcome(str, Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    PASS_REPORTED = "PASS_REPORTED"
    REJECTED_REPORTED = "REJECTED_REPORTED"


class SourceClaim(BaseModel):
    """Caller-supplied metadata, never independently verified provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    claim_kind: Literal["UNVERIFIED_SOURCE_METADATA"] = "UNVERIFIED_SOURCE_METADATA"
    source_id: str = Field(pattern=_ID)
    provider_label: str = Field(min_length=1, max_length=128)
    source_url: str
    raw_sha256: str = Field(pattern=_DIGEST)
    region_code: str = Field(pattern=r"^[0-9]{5}$")
    hazard: HazardKind
    category: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    coverage_kind: CoverageKind
    coverage_ref: str = Field(pattern=_SCOPE)
    observed_at: AwareDatetime
    retrieved_at: AwareDatetime
    asserted_valid_until: AwareDatetime | None = None

    @field_validator("source_url")
    @classmethod
    def https_only(cls, value: str) -> str:
        if any(ch.isspace() for ch in value) or "\\" in value:
            raise ValueError("invalid characters in URL")
        url = urlsplit(value)
        if (url.scheme != "https" or not url.hostname or url.username is not None
                or url.password is not None or url.fragment):
            raise ValueError("source URL must be HTTPS without credentials/fragment")
        try:
            if url.port not in (None, 443):
                raise ValueError("invalid source URL port")
        except ValueError as exc:
            raise ValueError("invalid source URL port") from exc
        return value

    @model_validator(mode="after")
    def check_scope_and_time(self) -> "SourceClaim":
        if self.retrieved_at < self.observed_at:
            raise ValueError("retrieved_at before observed_at")
        if (self.asserted_valid_until is not None
                and self.asserted_valid_until <= self.observed_at):
            raise ValueError("valid_until must follow observed_at")
        if (self.coverage_kind is CoverageKind.MUNICIPAL_REGION
                and self.coverage_ref != self.region_code):
            raise ValueError("municipal coverage must match region")
        return self


class ReviewClaim(BaseModel):
    """A purported separate review, not an authenticated A/C approval."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    claim_kind: Literal["UNAUTHENTICATED_REVIEW"] = "UNAUTHENTICATED_REVIEW"
    report_id: str = Field(pattern=_ID)
    reviewer_ref: str = Field(min_length=1, max_length=128)
    source_id: str = Field(pattern=_ID)
    raw_sha256: str = Field(pattern=_DIGEST)
    region_code: str = Field(pattern=r"^[0-9]{5}$")
    hazard: HazardKind
    category: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    coverage_kind: CoverageKind
    coverage_ref: str = Field(pattern=_SCOPE)
    reviewed_at: AwareDatetime
    reported_outcome: ReportedOutcome


class EvidenceClaimBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    sources: tuple[SourceClaim, ...] = ()
    reports: tuple[ReviewClaim, ...] = ()

    @model_validator(mode="after")
    def unique_claims(self) -> "EvidenceClaimBundle":
        ids = [source.source_id for source in self.sources]
        reviewed_ids = [review.source_id for review in self.reports]
        report_ids = [review.report_id for review in self.reports]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate source ID")
        if len(reviewed_ids) != len(set(reviewed_ids)):
            raise ValueError("multiple reports on one source")
        if len(report_ids) != len(set(report_ids)):
            raise ValueError("duplicate report ID")
        if not set(reviewed_ids).issubset(set(ids)):
            raise ValueError("unattached review report")
        return self


class EvidenceLinkReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str
    hazard: HazardKind
    category: str
    report_id: str | None
    reported_outcome: ReportedOutcome | None
    reason_codes: tuple[str, ...]
    status: Literal["UNKNOWN"] = "UNKNOWN"
    review_authenticated: Literal[False] = False
    eligible_for_action_decision: Literal[False] = False


class EvidenceBundleReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: Literal["DRILL"] = "DRILL"
    synthetic: Literal[True] = True
    fixture_id: str
    independent_review_authenticated: Literal[False] = False
    published_for_disaster_use: Literal[False] = False
    actions: MultiHazardActionReview
    links: tuple[EvidenceLinkReview, ...]


def review_evidence_claims(
    drill: MultiHazardDrill, bundle: EvidenceClaimBundle,
) -> EvidenceBundleReview:
    """Check untrusted claims for consistency, never certify their contents."""
    fixture = drill.fixture
    cues = {(cue.hazard, cue.category): cue for cue in fixture.cues}
    reports = {report.source_id: report for report in bundle.reports}
    links: list[EvidenceLinkReview] = []
    for source in sorted(bundle.sources, key=lambda item: item.source_id):
        codes = []
        if source.region_code != fixture.region_code:
            codes.append("REGION_MISMATCH")
        if source.hazard not in fixture.hazards:
            codes.append("HAZARD_MISMATCH")
        else:
            valid_categories = _evidence_categories(
                source.hazard, fixture.region_code, fixture.fixture_id,
                fixture.simulated_at,
            )
            if source.category not in valid_categories:
                codes.append("CATEGORY_MISMATCH")
        cue = cues.get((source.hazard, source.category))
        if cue is None:
            codes.append("NO_MATCHING_DRILL_CUE")
        elif cue.availability is not CueAvailability.SYNTHETIC_PRESENT:
            codes.append("DRILL_CUE_UNAVAILABLE")
        elif cue.expires_at is not None and cue.expires_at <= fixture.simulated_at:
            codes.append("DRILL_CUE_EXPIRED")
        if source.observed_at > fixture.simulated_at or source.retrieved_at > fixture.simulated_at:
            codes.append("SOURCE_FROM_FUTURE")
        if source.asserted_valid_until is None:
            codes.append("SOURCE_VALIDITY_UNASSERTED")
        elif source.asserted_valid_until <= fixture.simulated_at:
            codes.append("SOURCE_CLAIM_EXPIRED")
        if source.coverage_kind is CoverageKind.GSI_TILE:
            codes.append("TILE_COVERAGE_NOT_VERIFIED_AT_LOCATION")
        report = reports.get(source.source_id)
        if report is None:
            codes.append("NO_INDEPENDENT_REVIEW_REPORT")
        elif any((
            report.raw_sha256 != source.raw_sha256,
            report.region_code != source.region_code,
            report.hazard != source.hazard,
            report.category != source.category,
            report.coverage_kind != source.coverage_kind,
            report.coverage_ref != source.coverage_ref,
        )):
            codes.append("REVIEW_IDENTITY_MISMATCH")
        elif report.reviewed_at > fixture.simulated_at:
            codes.append("REVIEW_FROM_FUTURE")
        elif report.reported_outcome is ReportedOutcome.PASS_REPORTED:
            codes.append("REPORTED_PASS_UNAUTHENTICATED")
        elif report.reported_outcome is ReportedOutcome.REJECTED_REPORTED:
            codes.append("REPORTED_REJECTION")
        else:
            codes.append("NOT_REVIEWED")
        codes.append("AUTHORITATIVE_ACCEPTANCE_NOT_ESTABLISHED")
        links.append(EvidenceLinkReview(
            source_id=source.source_id, hazard=source.hazard,
            category=source.category, report_id=report.report_id if report else None,
            reported_outcome=report.reported_outcome if report else None,
            reason_codes=tuple(codes),
        ))
    return EvidenceBundleReview(
        fixture_id=fixture.fixture_id, actions=review_multi_hazard_drill(drill),
        links=tuple(links),
    )
