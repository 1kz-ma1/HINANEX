"""S1-P2 in-memory synthetic *review selection*, never real shelter selection.

A user may explicitly focus one in-scope fictional comparison row, including
UNKNOWN. No eligibility, opening, safety, ranking, route, persistence or UI API.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.hinanex.drill_session import Session
from src.hinanex.s1_synthetic_comparison import (
    CONDITION_NOT_EVALUATED, ConditionCheck, compare_synthetic_conditions,
)
from src.hinanex.s1_synthetic_narrowing import NarrowRequest, SyntheticReference


@dataclass(frozen=True)
class ExplicitReviewChoice:
    """Only an explicit per-operation in-memory action is accepted."""

    selected_record_id: str
    expected_generation: int
    explicit_user_action: bool

    def __post_init__(self) -> None:
        if not isinstance(self.selected_record_id, str) or not self.selected_record_id:
            raise ValueError("a selected synthetic record_id is required")
        if type(self.expected_generation) is not int or self.expected_generation < 0:
            raise ValueError("expected_generation must be a nonnegative integer")
        if type(self.explicit_user_action) is not bool:
            raise ValueError("explicit_user_action must be an actual boolean")


@dataclass(frozen=True)
class ReviewChoiceResult:
    status: str
    reason_code: str
    generation: int
    selected_record_id: str | None = None
    comparison_status: str | None = None
    comparison_reason_code: str | None = None
    checks: tuple[ConditionCheck, ...] = ()
    missing: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    synthetic_only: bool = True
    review_only: bool = True
    official_acceptance: bool = False
    live_data_verified: bool = False
    facility_safety_verified: bool = False
    route_safety_verified: bool = False
    release_approved: bool = False

    def __post_init__(self) -> None:
        if self.synthetic_only is not True or self.review_only is not True:
            raise ValueError("selection must remain explicitly synthetic review only")
        if any(x is not False for x in (
            self.official_acceptance, self.live_data_verified,
            self.facility_safety_verified, self.route_safety_verified,
            self.release_approved,
        )):
            raise ValueError("review choice cannot imply real-world approval")
        if self.status == "BLOCKED" and (
            self.selected_record_id is not None
            or self.comparison_status is not None
            or self.comparison_reason_code is not None
            or self.checks or self.missing or self.failed
        ):
            raise ValueError("blocked review cannot retain old selection data")


def choose_synthetic_for_review(
    state: Session,
    request: NarrowRequest,
    records: tuple[SyntheticReference, ...],
    choice: ExplicitReviewChoice,
    now,
) -> ReviewChoiceResult:
    """Choose one *current synthetic* row for review, never reuse cached reports.

    Intentional: UNKNOWN/NOT_MATCHED records may be inspected by the human;
    the exact original assessment is preserved rather than promoted to match.
    Out-of-scope or expired rows cannot be chosen, including for review.
    """
    if not isinstance(choice, ExplicitReviewChoice):
        raise TypeError("an explicit review choice object is required")

    # Every invocation rechecks S0/generation/expiry and S1 conditions.
    comparison = compare_synthetic_conditions(state, request, records, now)
    if comparison.status != "EVALUATED_SYNTHETIC_ONLY":
        return ReviewChoiceResult(
            "BLOCKED", comparison.reason_code, comparison.generation,
        )
    if choice.expected_generation != comparison.generation:
        return ReviewChoiceResult(
            "BLOCKED", "STALE_REVIEW_CHOICE", comparison.generation,
        )
    if not choice.explicit_user_action:
        return ReviewChoiceResult(
            "BLOCKED", "EXPLICIT_USER_SELECTION_REQUIRED", comparison.generation,
        )
    selected = next(
        (row for row in comparison.rows if row.record_id == choice.selected_record_id),
        None,
    )
    if selected is None:
        return ReviewChoiceResult(
            "BLOCKED", "RECORD_NOT_IN_CURRENT_COMPARISON", comparison.generation,
        )
    if any(c.assessment == CONDITION_NOT_EVALUATED for c in selected.checks):
        return ReviewChoiceResult(
            "BLOCKED", "RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE", comparison.generation,
        )

    # Selection signals *only* intent to view a fictional record and keeps
    # its UNKNOWN/NOT_MATCHED/MATCHED_SYNTHETIC assessment unchanged.
    return ReviewChoiceResult(
        "REVIEW_SELECTED_SYNTHETIC_ONLY", "EXPLICIT_FICTIONAL_REVIEW_SELECTION",
        comparison.generation, selected.record_id,
        selected.status, selected.reason_code,
        selected.checks, selected.missing, selected.failed,
    )
