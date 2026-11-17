"""Offline S1-P4 sequence preview: fixed fictional records, no B API."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from datetime import timedelta

from preview_s1_synthetic_what_if import T0, sample_state
from src.hinanex.s1_synthetic_walkthrough import (
    IntentKind, WalkthroughIntent, WalkthroughState,
    apply_walkthrough_intent, project_walkthrough,
)


def sample_walkthrough(scenario: str = "normal") -> dict:
    """Reproduce a multi-step sequence without any network, storage or live time."""
    if scenario not in ("normal", "stale", "expired", "stopped"):
        raise ValueError("only fixed fictional scenarios are accepted")
    _, records = sample_state()
    initial_state, _ = sample_state()
    fixture = initial_state.fixture
    state = WalkthroughState()
    events = []
    frames = []

    def apply(kind, at, *, explicit=False, conditions=(), record_id=None,
              fixture_input=None, region=None, stale_revision=None):
        nonlocal state
        command = WalkthroughIntent(
            kind, state.session.generation,
            state.revision if stale_revision is None else stale_revision,
            explicit, conditions, record_id, region, fixture_input,
        )
        output = apply_walkthrough_intent(state, command, records, at)
        state = output.state
        events.append({
            "kind": kind.value, "status": output.status,
            "reason_code": output.reason_code,
            "generation": state.session.generation, "revision": state.revision,
        })

    def frame(at):
        p = project_walkthrough(state, records, at)
        frames.append(asdict(p))

    at = T0 + timedelta(minutes=5)
    apply(IntentKind.START, T0, explicit=True, conditions=("pet_support",),
          fixture_input=fixture, region="13123")
    frame(at)
    old_revision = state.revision
    apply(IntentKind.SET_CONDITIONS, at, explicit=True,
          conditions=("step_free",))
    frame(at)

    if scenario == "stale":
        apply(IntentKind.REVIEW, at, explicit=True,
              record_id="synthetic:a", stale_revision=old_revision)
        frame(at)
    if scenario == "expired":
        expire_at = T0 + timedelta(minutes=30)
        frame(expire_at)
        apply(IntentKind.REVIEW, expire_at, explicit=True,
              record_id="synthetic:e")
        frame(expire_at)
    else:
        apply(IntentKind.REVIEW, at, explicit=True, record_id="synthetic:e")
        frame(at)
        if scenario == "stopped":
            apply(IntentKind.STOP, at)
            frame(at)

    return {
        "schema_id": "hinanex.d.s1.synthetic_walkthrough_preview.internal.v0.1",
        "scenario": scenario,
        "synthetic_only": True, "official_acceptance": False,
        "live_data_verified": False, "facility_safety_verified": False,
        "route_safety_verified": False, "release_approved": False,
        "events": events, "frames": frames,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fixed fictional S1-P4 interaction sequence")
    parser.add_argument("--scenario", choices=("normal", "stale", "expired", "stopped"),
                        default="normal")
    args = parser.parse_args(argv)
    print(json.dumps(sample_walkthrough(args.scenario), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
