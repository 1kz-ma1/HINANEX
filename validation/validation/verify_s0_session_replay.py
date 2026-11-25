"""C-only integration replay of the *actual* draft S0 reducer, using synthetic events.

This is an independent test consumer, not a production adapter or B/E API.
It never treats a synthetic drill result as official data or facility suitability.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "validation" / "fixtures" / "s0_c_replay_v01.json"
S0_PATH = ROOT / "pipeline"
if str(S0_PATH) not in sys.path:
    sys.path.insert(0, str(S0_PATH))

# Deliberately import S0's real implementation; never recode its reducer in C.
from src.hinanex.drill_session import (
    Action, DRILL_NOTICE, Event, Mode, NORMAL_NOTICE, SYNTHETIC_ONLY,
    Session, StaleSessionError, SyntheticFixture, reduce_session, safe_view,
)

SCHEMA = "hinanex.c.s0_real_reducer_replay.v0.1"
STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
SAFE_OUTPUT_KEYS = (
    "mode", "selected_region", "preferred_region", "fixture_id", "hazard",
    "source_authorization", "generation", "reason", "notice_kind",
    "live_data_verified",
)


def parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("time must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time must include timezone")
    return parsed


def build_fixture(spec: dict) -> SyntheticFixture:
    return SyntheticFixture(
        fixture_id=spec["fixture_id"], region_code=spec["region_code"],
        hazard=spec["hazard"], observed_at=parse_time(spec["observed_at"]),
        expires_at=parse_time(spec["expires_at"]),
        source_authorization=spec["source_authorization"],
    )


def observed_view(state: Session, now: datetime) -> tuple[dict, str | None]:
    """Return actual output and an independent C safety invariant error, if any."""
    view = safe_view(state, now)
    data = {
        "mode": view.mode.value,
        "selected_region": view.selected_region,
        "preferred_region": view.preferred_region,
        "fixture_id": view.fixture_id,
        "hazard": view.hazard,
        "source_authorization": view.source_authorization,
        "generation": view.generation,
        "reason": view.reason,
        "notice_kind": ("DRILL" if view.notice == DRILL_NOTICE else
                        "NORMAL" if view.notice == NORMAL_NOTICE else "UNRECOGNIZED"),
        "live_data_verified": view.live_data_verified,
    }
    # This checks the actual public view, NOT the D reducer's internal steps.
    if set(vars(view)) != {
        "mode", "selected_region", "preferred_region", "fixture_id", "hazard",
        "source_authorization", "generation", "reason", "notice", "live_data_verified",
    }:
        return data, "UNREVIEWED_PUBLIC_FIELDS"
    if view.live_data_verified is not False:
        return data, "LIVE_ASSERTION"
    if view.mode == Mode.NORMAL:
        if any(value is not None for value in (
            view.fixture_id, view.hazard, view.source_authorization,
        )) or view.notice != NORMAL_NOTICE:
            return data, "NORMAL_LEAKED_DRILL_DATA"
    elif view.mode == Mode.DRILL:
        fixture = state.fixture
        if (fixture is None or state.mode != Mode.DRILL or
                state.selected_region != fixture.region_code or
                view.selected_region != fixture.region_code or
                view.fixture_id != fixture.fixture_id or
                view.hazard != fixture.hazard or
                view.source_authorization != SYNTHETIC_ONLY or
                fixture.source_authorization != SYNTHETIC_ONLY or
                not (fixture.observed_at <= now < fixture.expires_at)):
            return data, "UNTRACEABLE_ACTIVE_DRILL"
        if view.notice != DRILL_NOTICE or not all(
                word in view.notice for word in ("訓練", "現在", "開設", "安全")):
            return data, "DRILL_NOTICE_MISSING"
    else:
        return data, "UNRECOGNIZED_MODE"
    return data, None


def verdict(status: str, code: str, trace: list | None = None) -> dict:
    return {"status": status, "code": code, "trace": trace if trace is not None else []}


def replay_case(case: dict, catalog: dict) -> dict:
    if case.get("run") is False:
        return verdict("NOT_RUN", "EXPLICITLY_DISABLED")
    steps = case.get("steps")
    if not isinstance(steps, list) or not steps:
        return verdict("BLOCKED", "NO_STEPS")
    state = Session()
    trace = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not isinstance(step.get("expect"), dict):
            return verdict("BLOCKED", "MISSING_EXPECTATION", trace)
        try:
            now = parse_time(step["now"])
            kind = step["kind"]
            expected_transition = step["expect"]["transition"]
            expected_view = step["expect"]["view"]
            if not isinstance(expected_view, dict) or not expected_view:
                return verdict("BLOCKED", "MISSING_EXPECTED_VIEW", trace)
            if not set(expected_view) <= set(SAFE_OUTPUT_KEYS):
                return verdict("BLOCKED", "UNREVIEWED_EXPECTATION_KEY", trace)

            transition = "VIEW"
            if kind == "EVENT":
                action = Action(step["action"])
                fixture_name = step.get("fixture")
                fixture = None
                if fixture_name is not None:
                    if fixture_name not in catalog:
                        return verdict("BLOCKED", "UNKNOWN_FIXTURE", trace)
                    fixture = build_fixture(catalog[fixture_name])
                event = Event(
                    action=action, expected_generation=step["expected_generation"],
                    region_code=step.get("region_code"), fixture=fixture,
                    explicit_consent=step.get("explicit_consent", False),
                )
                prior_state = state
                try:
                    state = reduce_session(state, event, now)
                    transition = "APPLIED"
                except StaleSessionError:
                    transition = "STALE_REJECTED"
                    if state is not prior_state:
                        return verdict("FAIL", "STALE_MUTATED_STATE", trace)
            elif kind != "VIEW":
                return verdict("BLOCKED", "UNKNOWN_STEP_KIND", trace)
            actual_view, invariant_error = observed_view(state, now)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            trace.append({"step": index, "error_type": type(exc).__name__})
            return verdict("BLOCKED", "INVALID_REPLAY_INPUT", trace)
        trace.append({
            "step": index, "transition": transition,
            "actual_view": actual_view, "expected_view": expected_view,
        })
        if invariant_error is not None:
            return verdict("FAIL", invariant_error, trace)
        if transition != expected_transition:
            return verdict("FAIL", "TRANSITION_MISMATCH", trace)
        if any(actual_view[key] != value for key, value in expected_view.items()):
            return verdict("FAIL", "OUTPUT_MISMATCH", trace)
    return verdict("PASS", "MATCHED", trace)


def check_manifest(manifest: object) -> list[dict]:
    if not isinstance(manifest, dict) or manifest.get("schema_id") != SCHEMA or manifest.get("synthetic_only") is not True:
        raise ValueError("manifest must be explicitly synthetic and versioned")
    catalog = manifest.get("fixtures")
    cases = manifest.get("cases")
    if not isinstance(catalog, dict) or not isinstance(cases, list) or not cases:
        raise ValueError("fixtures/cases must be present")
    rows, seen = [], set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("invalid case")
        case_id = case.get("id")
        expected = case.get("expected")
        if (not isinstance(case_id, str) or not case_id or case_id in seen or
                not isinstance(expected, dict) or expected.get("status") not in STATUSES or
                not isinstance(expected.get("code"), str) or
                type(case.get("run", True)) is not bool):
            raise ValueError("invalid case id, status or run flag")
        seen.add(case_id)
        actual = replay_case(case, catalog)
        rows.append({
            "id": case_id, "expected": expected, "actual": actual,
            "matches_expected": {key: actual[key] for key in ("status", "code")} == expected,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline actual-S0/C independent replay (synthetic only)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = check_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REPLAY_MANIFEST_ERROR: {exc}", file=sys.stderr)
        return 2
    counts = {status: sum(r["actual"]["status"] == status for r in rows) for status in STATUSES}
    report = {
        "schema_id": SCHEMA, "synthetic_only": True, "official_acceptance": False,
        "device_qa": "NOT_RUN", "s0_source": "actual src.hinanex.drill_session reducer",
        "regression": "PASS" if all(r["matches_expected"] for r in rows) else "FAIL",
        "counts": counts, "cases": rows,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['id']}: {row['actual']['status']}/{row['actual']['code']} "
                  f"(expected: {row['expected']['status']}/{row['expected']['code']}; "
                  f"regression: {'PASS' if row['matches_expected'] else 'FAIL'})")
        print(f"REGRESSION={report['regression']} COUNTS={counts} OFFICIAL_ACCEPTANCE=NO DEVICE_QA=NOT_RUN")
    return 0 if report["regression"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
