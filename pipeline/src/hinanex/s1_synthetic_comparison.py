"""S1-P1 private synthetic comparison matrix, not a public shelter comparison API.

Transforms *freshly recomputed* S1-P0 fictional decisions into explainable,
ordered condition checks. Does not infer, rank, persist, or publish real data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json

from src.hinanex.drill_session import Session
from src.hinanex.s1_synthetic_narrowing import (
    DECISION_MATCH, DECISION_NOT_MATCHED, DECISION_UNKNOWN,
    NarrowRequest, SyntheticReference, narrow_synthetic_references,
)

SCHEMA = "hinanex.d.s1.synthetic_comparison.internal.v0.1"
CONDITION_TRUE = "EXPLICIT_SYNTHETIC_TRUE"
CONDITION_FALSE = "EXPLICIT_SYNTHETIC_FALSE"
CONDITION_UNKNOWN = "UNVERIFIED"
CONDITION_NOT_EVALUATED = "NOT_EVALUATED"
SKIP_REASONS = frozenset(("OUT_OF_SYNTHETIC_SCOPE", "STALE_OR_FUTURE_SYNTHETIC_FACT"))


@dataclass(frozen=True)
class ConditionCheck:
    condition: str
    assessment: str


@dataclass(frozen=True)
class ComparisonRow:
    record_id: str
    status: str
    reason_code: str
    checks: tuple[ConditionCheck, ...]
    missing: tuple[str, ...]
    failed: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonTotals:
    matched_synthetic: int = 0
    not_matched_synthetic: int = 0
    unknown: int = 0


@dataclass(frozen=True)
class SyntheticComparison:
    """An ephemeral internal report. Never treat a synthetic match as shelter safety."""

    status: str
    reason_code: str
    generation: int
    evaluated_at: str
    expires_at: str | None
    required_conditions: tuple[str, ...]
    rows: tuple[ComparisonRow, ...]
    totals: ComparisonTotals
    schema_id: str = SCHEMA
    synthetic_only: bool = True
    official_acceptance: bool = False
    live_data_verified: bool = False
    facility_safety_verified: bool = False
    route_safety_verified: bool = False
    release_approved: bool = False

    def __post_init__(self) -> None:
        if (self.schema_id != SCHEMA or self.synthetic_only is not True
                or any(value is not False for value in (
                    self.official_acceptance, self.live_data_verified,
                    self.facility_safety_verified, self.route_safety_verified,
                    self.release_approved,
                ))):
            raise ValueError("synthetic comparison cannot authorize a real-world claim")


def compare_synthetic_conditions(
    state: Session,
    request: NarrowRequest,
    records: tuple[SyntheticReference, ...],
    now: datetime,
) -> SyntheticComparison:
    """Recompute S1-P0 against the *current* S0 state, then explain every comparison.

    Do not accept old NarrowReport or cached decisions from callers. A blocked
    context returns empty rows and condition set, never resurrecting old output.
    """
    core = narrow_synthetic_references(state, request, records, now)
    evaluated_at = now.isoformat()

    if core.status != "EVALUATED_SYNTHETIC_ONLY":
        return SyntheticComparison(
            status="BLOCKED", reason_code=core.reason_code, generation=core.generation,
            evaluated_at=evaluated_at, expires_at=None, required_conditions=(),
            rows=(), totals=ComparisonTotals(),
        )

    rows: list[ComparisonRow] = []
    for record, decision in zip(records, core.decisions, strict=True):
        not_evaluated = decision.reason_code in SKIP_REASONS
        facts = dict(record.conditions) if not not_evaluated else {}
        checks = tuple(ConditionCheck(
            condition=condition,
            assessment=(
                CONDITION_NOT_EVALUATED if not_evaluated
                else CONDITION_TRUE if facts.get(condition) is True
                else CONDITION_FALSE if facts.get(condition) is False
                else CONDITION_UNKNOWN
            ),
        ) for condition in request.required_conditions)
        rows.append(ComparisonRow(
            record_id=decision.record_id, status=decision.status,
            reason_code=decision.reason_code, checks=checks,
            missing=decision.missing if not_evaluated is False else (),
            failed=decision.failed if not_evaluated is False else (),
        ))
    totals = ComparisonTotals(
        matched_synthetic=sum(row.status == DECISION_MATCH for row in rows),
        not_matched_synthetic=sum(row.status == DECISION_NOT_MATCHED for row in rows),
        unknown=sum(row.status == DECISION_UNKNOWN for row in rows),
    )
    return SyntheticComparison(
        status=core.status, reason_code=core.reason_code, generation=core.generation,
        evaluated_at=evaluated_at, expires_at=state.fixture.expires_at.isoformat(),
        required_conditions=request.required_conditions,
        rows=tuple(rows), totals=totals,
    )


def comparison_as_dict(report: SyntheticComparison) -> dict:
    """Pure, explicitly internal JSON-friendly serialization; no storage or network."""
    if not isinstance(report, SyntheticComparison):
        raise TypeError("internal SyntheticComparison expected")
    return asdict(report)


def comparison_as_json(report: SyntheticComparison) -> str:
    """For offline reproducible test output only. Not a D→B API or public JSON."""
    return json.dumps(comparison_as_dict(report), ensure_ascii=False, indent=2)
