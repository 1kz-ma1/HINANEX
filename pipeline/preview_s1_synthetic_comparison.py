"""Offline, deterministic S1-P1 comparison sample. Absolutely no real facilities."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import NarrowRequest, SyntheticReference
from src.hinanex.s1_synthetic_comparison import (
    compare_synthetic_conditions, comparison_as_json,
)


def synthetic_preview() -> str:
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)
    expiry = now + timedelta(minutes=30)
    fixture = SyntheticFixture(
        fixture_id="synthetic:s1-comparison-preview", region_code="13123",
        hazard="flood", observed_at=now, expires_at=expiry,
        source_authorization=SYNTHETIC_ONLY,
    )
    session = reduce_session(Session(), Event(
        action=Action.START_DRILL, expected_generation=0,
        region_code="13123", fixture=fixture,
    ), now)
    request = NarrowRequest(
        expected_generation=session.generation,
        region_code="13123", hazard="flood",
        required_conditions=("pet_support", "step_free"),
    )
    fictional = [
        ("synthetic:example-a", True, True),
        ("synthetic:example-b", False, True),
        ("synthetic:example-c", None, True),
        ("synthetic:example-d", False, None),
    ]
    records = tuple(
        SyntheticReference(
            record_id=record_id, fixture_id=fixture.fixture_id,
            region_code=fixture.region_code, hazard=fixture.hazard,
            observed_at=now, expires_at=expiry,
            conditions=(("pet_support", pet), ("step_free", step)),
        )
        for record_id, pet, step in fictional
    )
    report = compare_synthetic_conditions(
        session, request, records, now + timedelta(minutes=5),
    )
    return comparison_as_json(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic-only S1 comparison preview")
    parser.add_argument("--json", action="store_true", help="print internal example JSON")
    parser.parse_args(argv)
    print(synthetic_preview())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
