"""Offline S1-P3 what-if playground. Absolutely fictional, no UI or persistence."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import CONDITIONS, SyntheticReference
from src.hinanex.s1_synthetic_review_choice import ExplicitReviewChoice
from src.hinanex.s1_synthetic_what_if import (
    WhatIfRequest, compare_what_if, what_if_as_json,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
EXPIRES = T0 + timedelta(minutes=30)


def _conditions(value: str) -> tuple[str, ...]:
    items = tuple(part.strip() for part in value.split(","))
    if not items or any(x not in CONDITIONS for x in items) or len(set(items)) != len(items):
        raise argparse.ArgumentTypeError(
            "choose one or both fictional conditions: pet_support,step_free"
        )
    return items


def sample_state() -> tuple[Session, tuple[SyntheticReference, ...]]:
    fixture = SyntheticFixture(
        fixture_id="synthetic:whatif-preview", region_code="13123",
        hazard="flood", observed_at=T0, expires_at=EXPIRES,
        source_authorization=SYNTHETIC_ONLY,
    )
    state = reduce_session(Session(), Event(
        Action.START_DRILL, 0, region_code="13123", fixture=fixture,
    ), T0)
    invented_facts = (
        ("synthetic:a", True, True),
        ("synthetic:b", True, False),
        ("synthetic:c", False, True),
        ("synthetic:d", None, True),
        ("synthetic:e", False, None),
    )
    records = tuple(SyntheticReference(
        record_id=ident, fixture_id=fixture.fixture_id,
        region_code=fixture.region_code, hazard=fixture.hazard,
        observed_at=T0, expires_at=EXPIRES,
        conditions=(("pet_support", pet), ("step_free", step)),
    ) for ident, pet, step in invented_facts)
    return state, records


def preview(*, before: tuple[str, ...] = ("pet_support",),
            after: tuple[str, ...] = ("step_free",),
            select: str | None = None,
            minutes: int = 5, stop: bool = False) -> str:
    if type(minutes) is not int or minutes < 0 or minutes > 1440:
        raise ValueError("minutes must be an integer from 0 to 1440")
    state, records = sample_state()
    now = T0 + timedelta(minutes=minutes)
    if stop:
        state = reduce_session(state, Event(Action.STOP_DRILL, state.generation), now)
    explicit = (ExplicitReviewChoice(select, state.generation, True)
                if select is not None else None)
    request = WhatIfRequest(
        expected_generation=state.generation, region_code="13123",
        hazard="flood", before=before, after=after, review_choice=explicit,
    )
    return what_if_as_json(compare_what_if(state, request, records, now))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline fictional S0/S1 condition what-if, never actual shelter guidance",
    )
    parser.add_argument("--before", type=_conditions, default=("pet_support",))
    parser.add_argument("--after", type=_conditions, default=("step_free",))
    parser.add_argument("--select", choices=[f"synthetic:{x}" for x in "abcde"],
                        help="explicitly review one fictional record using the AFTER conditions")
    parser.add_argument("--minutes", type=int, default=5,
                        help="minutes after fixed synthetic start (30 or later is expired)")
    parser.add_argument("--stop", action="store_true",
                        help="simulate leaving drill before comparing; all results blocked")
    args = parser.parse_args(argv)
    try:
        result = preview(
            before=args.before, after=args.after, select=args.select,
            minutes=args.minutes, stop=args.stop,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
