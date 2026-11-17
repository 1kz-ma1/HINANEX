"""D-only S1-P3 what-if comparison over one active fictional drill.

This is an in-memory operator workbench, not a shared D→B contract. It changes
only the *requested synthetic conditions*, never facility attributes or source
meaning; no real facilities, user data, persistence, network or safety claims.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json

from src.hinanex.drill_session import Session
from src.hinanex.s1_synthetic_narrowing import (
    CONDITIONS, NarrowRequest, SyntheticReference,
)
from src.hinanex.s1_synthetic_comparison import (
    ComparisonRow, ConditionCheck, compare_synthetic_conditions,
)
from src.hinanex.s1_synthetic_review_choice import (
    ExplicitReviewChoice, ReviewChoiceResult, choose_synthetic_for_review,
)


@dataclass(frozen=True)
class WhatIfRequest:
    """Two explicitly chosen nonempty synthetic constraint sets."""

    expected_generation: int
    region_code: str
    hazard: str
    before: tuple[str, ...]
    after: tuple[str, ...]
    review_choice: ExplicitReviewChoice | None = None

    def __post_init__(self) -> None:
        # Delegate format and duplicate checks to existing D S1 request rules.
        NarrowRequest(self.expected_generation, self.region_code, self.hazard, self.before)
        NarrowRequest(self.expected_generation, self.region_code, self.hazard, self.after)
        if not self.before or not self.after:
            raise ValueError("both what-if condition sets must be explicit and nonempty")
        if self.review_choice is not None and not isinstance(
            self.review_choice, ExplicitReviewChoice
        ):
            raise TypeError("review_choice must be an explicit synthetic review action")


@dataclass(frozen=True)
class WhatIfRow:
    record_id: str
    before_status: str
    after_status: str
    before_reason_code: str
    after_reason_code: str
    before_checks: tuple[ConditionCheck, ...]
    after_checks: tuple[ConditionCheck, ...]
    before_missing: tuple[str, ...]
    after_missing: tuple[str, ...]
    before_failed: tuple[str, ...]
    after_failed: tuple[str, ...]


@dataclass(frozen=True)
class WhatIfResult:
    """No positive conclusions are valid outside the current synthetic session."""

    status: str
    reason_code: str
    generation: int
    before_conditions: tuple[str, ...] = ()
    after_conditions: tuple[str, ...] = ()
    rows: tuple[WhatIfRow, ...] = ()
    newly_matching_synthetic_ids: tuple[str, ...] = ()
    no_longer_matching_synthetic_ids: tuple[str, ...] = ()
    unknown_after_synthetic_ids: tuple[str, ...] = ()
    review: ReviewChoiceResult | None = None
    synthetic_only: bool = True
    official_acceptance: bool = False
    live_data_verified: bool = False
    facility_safety_verified: bool = False
    route_safety_verified: bool = False
    release_approved: bool = False

    def __post_init__(self) -> None:
        if self.synthetic_only is not True or any(x is not False for x in (
            self.official_acceptance, self.live_data_verified,
            self.facility_safety_verified, self.route_safety_verified,
            self.release_approved,
        )):
            raise ValueError("what-if cannot authorize real-world safety or publication")
        if self.status == "BLOCKED" and any((
            self.before_conditions, self.after_conditions, self.rows,
            self.newly_matching_synthetic_ids, self.no_longer_matching_synthetic_ids,
            self.unknown_after_synthetic_ids, self.review,
        )):
            raise ValueError("blocked what-if must not disclose stale results")


def _row(before: ComparisonRow, after: ComparisonRow) -> WhatIfRow:
    if before.record_id != after.record_id:
        raise ValueError("what-if source order or identity changed")
    return WhatIfRow(
        record_id=before.record_id,
        before_status=before.status, after_status=after.status,
        before_reason_code=before.reason_code, after_reason_code=after.reason_code,
        before_checks=before.checks, after_checks=after.checks,
        before_missing=before.missing, after_missing=after.missing,
        before_failed=before.failed, after_failed=after.failed,
    )


def compare_what_if(
    state: Session,
    request: WhatIfRequest,
    records: tuple[SyntheticReference, ...],
    now: datetime,
) -> WhatIfResult:
    """Recompute both variants from current S0/P0/P1; optionally review after.

    Does not cache or accept previous comparisons. A blocked/expired context
    removes *all* rows, IDs and previous review output.
    """
    if not isinstance(request, WhatIfRequest):
        raise TypeError("WhatIfRequest is required")
    prior = NarrowRequest(
        request.expected_generation, request.region_code,
        request.hazard, request.before,
    )
    changed = NarrowRequest(
        request.expected_generation, request.region_code,
        request.hazard, request.after,
    )
    before = compare_synthetic_conditions(state, prior, records, now)
    after = compare_synthetic_conditions(state, changed, records, now)
    if before.status != "EVALUATED_SYNTHETIC_ONLY" or after.status != "EVALUATED_SYNTHETIC_ONLY":
        return WhatIfResult("BLOCKED", after.reason_code if after.status == "BLOCKED"
                            else before.reason_code, after.generation)
    if (before.generation != after.generation or
            len(before.rows) != len(after.rows)):
        raise ValueError("inconsistent synthetic comparisons")

    rows = tuple(_row(x, y) for x, y in zip(before.rows, after.rows, strict=True))
    review = None
    if request.review_choice is not None:
        review = choose_synthetic_for_review(
            state, changed, records, request.review_choice, now,
        )
        # A rejected user selection remains a rejected, empty review, never
        # becomes an inferred or default selected facility.
    return WhatIfResult(
        status="EVALUATED_SYNTHETIC_ONLY",
        reason_code="CONSTRAINT_CHANGE_IS_NOT_REAL_WORLD_ELIGIBILITY",
        generation=after.generation,
        before_conditions=before.required_conditions,
        after_conditions=after.required_conditions,
        rows=rows,
        newly_matching_synthetic_ids=tuple(
            row.record_id for row in rows
            if row.before_status != "MATCHED_SYNTHETIC"
            and row.after_status == "MATCHED_SYNTHETIC"
        ),
        no_longer_matching_synthetic_ids=tuple(
            row.record_id for row in rows
            if row.before_status == "MATCHED_SYNTHETIC"
            and row.after_status != "MATCHED_SYNTHETIC"
        ),
        unknown_after_synthetic_ids=tuple(
            row.record_id for row in rows if row.after_status == "UNKNOWN"
        ),
        review=review,
    )


def what_if_as_json(result: WhatIfResult) -> str:
    if not isinstance(result, WhatIfResult):
        raise TypeError("WhatIfResult is required")
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)
