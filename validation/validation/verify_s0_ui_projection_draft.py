"""C-only reference preflight for a *proposed*, non-adopted S0→UI display contract.

Calls real S0 reducer/view; does not implement the D provider, a B client, or
any transport. All examples are invented, local and synthetic only.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
S0_ROOT = ROOT / "pipeline"
if str(S0_ROOT) not in sys.path:
    sys.path.insert(0, str(S0_ROOT))
from src.hinanex.drill_session import (
    Action, DRILL_NOTICE, Event, Mode, NORMAL_NOTICE, SYNTHETIC_ONLY,
    Session, SyntheticFixture, StaleSessionError, reduce_session, safe_view,
)

SCHEMA_ID = "hinanex.s0.ui_display_projection.review.v0.1"
MANIFEST_ID = "hinanex.c.s0_ui_display_draft_preflight.v0.1"
SCHEMA_PATH = ROOT / "docs/strategy/S0_UI_DISPLAY_PROJECTION_DRAFT_V01.schema.json"
MANIFEST_PATH = ROOT / "validation/fixtures/s0_ui_display_draft_preflight_v01.json"
FIELDS = frozenset((
    "schema_id", "review_only", "synthetic_only", "mode", "generation",
    "selected_region", "fixture_id", "hazard", "source_authorization",
    "notice", "live_data_verified", "issued_at", "observed_at", "expires_at",
))
_REGION = re.compile(r"[0-9]{5}\Z")
_HAZARD = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
_FIXTURE = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z")
STATES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")


def decision(status: str, code: str) -> dict[str, str]:
    return {"status": status, "code": code}


def moment(value: str | datetime) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be explicitly timezone aware")
    return value


def iso(value: datetime) -> str:
    return value.isoformat()


def project_for_review(state: Session, issued_at: datetime) -> dict:
    """Reference-only projection from the actual S0 view, NOT a D/production API."""
    now = moment(issued_at)
    v = safe_view(state, now)
    active = v.mode == Mode.DRILL
    fixture = state.fixture if active else None
    return {
        "schema_id": SCHEMA_ID, "review_only": True, "synthetic_only": True,
        "mode": v.mode.value, "generation": v.generation,
        "selected_region": v.selected_region,
        "fixture_id": v.fixture_id, "hazard": v.hazard,
        "source_authorization": v.source_authorization,
        "notice": v.notice, "live_data_verified": v.live_data_verified,
        "issued_at": iso(now),
        "observed_at": iso(fixture.observed_at) if fixture else None,
        "expires_at": iso(fixture.expires_at) if fixture else None,
    }


def inspect(snapshot: object, state: Session, *, render_at: datetime,
            active_generation: int) -> dict[str, str]:
    """Independently inspect one proposed snapshot against the *actual* S0 state."""
    if not isinstance(snapshot, dict):
        return decision("BLOCKED", "MISSING_SNAPSHOT")
    if not FIELDS <= snapshot.keys():
        return decision("BLOCKED", "MISSING_DISPLAY_FIELD")
    if set(snapshot) != FIELDS:
        return decision("FAIL", "UNREVIEWED_DISPLAY_FIELD")
    if (snapshot["schema_id"] != SCHEMA_ID or snapshot["review_only"] is not True
            or snapshot["synthetic_only"] is not True):
        return decision("FAIL", "NOT_REVIEW_SYNTHETIC")
    if snapshot["live_data_verified"] is not False:
        return decision("FAIL", "FALSE_LIVE_ASSERTION")
    generation = snapshot["generation"]
    if (type(generation) is not int or generation < 0 or
            type(active_generation) is not int or active_generation < 0):
        return decision("BLOCKED", "INVALID_GENERATION")
    if generation != active_generation or generation != state.generation:
        return decision("FAIL", "STALE_CONTEXT_GENERATION")
    region = snapshot["selected_region"]
    if region is not None and (not isinstance(region, str) or not _REGION.fullmatch(region)):
        return decision("FAIL", "INVALID_REGION")

    mode = snapshot["mode"]
    if mode == "NORMAL":
        if any(snapshot[k] is not None for k in (
            "fixture_id", "hazard", "source_authorization", "observed_at", "expires_at",
        )):
            return decision("FAIL", "NORMAL_LEAKED_FIXTURE")
        if snapshot["notice"] != NORMAL_NOTICE:
            return decision("FAIL", "NORMAL_NOTICE_MISMATCH")
    elif mode == "DRILL":
        if snapshot["notice"] != DRILL_NOTICE:
            return decision("FAIL", "DRILL_NOTICE_MISMATCH")
        if snapshot["source_authorization"] != SYNTHETIC_ONLY:
            return decision("FAIL", "NON_SYNTHETIC_SOURCE")
        if (not isinstance(region, str) or
                not isinstance(snapshot["fixture_id"], str) or
                not _FIXTURE.fullmatch(snapshot["fixture_id"]) or
                not isinstance(snapshot["hazard"], str) or
                not _HAZARD.fullmatch(snapshot["hazard"])):
            return decision("FAIL", "INVALID_DRILL_CONTEXT")
    else:
        return decision("FAIL", "UNKNOWN_MODE")

    try:
        issued = moment(snapshot["issued_at"])
        rendered = moment(render_at)
        observed = moment(snapshot["observed_at"]) if mode == "DRILL" else None
        expires = moment(snapshot["expires_at"]) if mode == "DRILL" else None
    except (TypeError, ValueError, OverflowError):
        return decision("BLOCKED", "INVALID_TIMESTAMP")
    if issued > rendered:
        return decision("FAIL", "FUTURE_ISSUE")
    if mode == "DRILL":
        if not observed <= issued < expires:
            return decision("FAIL", "INVALID_DRILL_WINDOW")
        if rendered >= expires:
            return decision("FAIL", "EXPIRED_DRILL")

    # Unlike UI-only schema validation, this C reference has the original D
    # state. It can reject a plausible forged envelope with wrong provenance.
    expected = project_for_review(state, issued)
    if snapshot != expected:
        return decision("FAIL", "S0_VIEW_PROVENANCE_MISMATCH")
    if mode == "DRILL" and safe_view(state, rendered).mode != Mode.DRILL:
        return decision("FAIL", "EXPIRED_DRILL")
    return decision("PASS", "CONSISTENT_REVIEW_PROJECTION")


def load_proposal_schema() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if (schema.get("title") != "DRAFT ONLY S0 synthetic UI display projection (NOT ADOPTED)"
            or schema.get("additionalProperties") is not False
            or set(schema.get("properties", {})) != FIELDS
            or set(schema.get("required", ())) != FIELDS
            or schema.get("properties", {}).get("schema_id", {}).get("const") != SCHEMA_ID
            or schema.get("properties", {}).get("live_data_verified", {}).get("const") is not False
            or len(schema.get("allOf", [])) != 2):
        raise ValueError("shared proposal schema inconsistent with C independent preflight")
    return schema


def synthetic_fixture(raw: dict) -> SyntheticFixture:
    return SyntheticFixture(
        fixture_id=raw["fixture_id"], region_code=raw["region_code"],
        hazard=raw["hazard"], observed_at=moment(raw["observed_at"]),
        expires_at=moment(raw["expires_at"]),
        source_authorization=raw["source_authorization"],
    )


def run_case(case: dict, fixtures: dict) -> dict:
    if case.get("run") is False:
        return decision("NOT_RUN", "EXPLICITLY_DISABLED")
    try:
        state = Session()
        for action in case.get("events", []):
            if not isinstance(action, dict):
                return decision("BLOCKED", "INVALID_EVENT")
            fixture = synthetic_fixture(fixtures[action["fixture"]]) if action.get("fixture") else None
            ev = Event(
                action=Action(action["action"]), expected_generation=action["expected_generation"],
                region_code=action.get("region_code"), fixture=fixture,
                explicit_consent=action.get("explicit_consent", False),
            )
            state = reduce_session(state, ev, moment(action["at"]))
        emitted_at = moment(case["issued_at"])
        snapshot = project_for_review(state, emitted_at)
        snapshot.update(case.get("patch", {}))
        for name in case.get("remove", []):
            snapshot.pop(name, None)
        return inspect(snapshot, state, render_at=moment(case["render_at"]),
                       active_generation=case["active_generation"])
    except (KeyError, TypeError, ValueError, OverflowError, StaleSessionError):
        return decision("BLOCKED", "INVALID_CASE_INPUT")


def check_manifest(manifest: object) -> list[dict]:
    load_proposal_schema()
    if (not isinstance(manifest, dict) or manifest.get("schema_id") != MANIFEST_ID
            or manifest.get("synthetic_only") is not True
            or not isinstance(manifest.get("fixtures"), dict)
            or not isinstance(manifest.get("cases"), list) or not manifest["cases"]):
        raise ValueError("invalid synthetic C preflight manifest")
    results, seen = [], set()
    for case in manifest["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise ValueError("invalid/duplicate case id")
        seen.add(case["id"])
        target = case.get("expected")
        if (not isinstance(target, dict) or set(target) != {"status", "code"}
                or target.get("status") not in STATES or not isinstance(target.get("code"), str)
                or type(case.get("run", True)) is not bool):
            raise ValueError(f"invalid expected result for {case['id']}")
        actual = run_case(case, manifest["fixtures"])
        results.append({"id":case["id"],"expected":target,"actual":actual,
                        "matches_expected":actual == target})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C-only S0→UI proposal preflight, synthetic only")
    parser.add_argument("--manifest",type=Path,default=MANIFEST_PATH)
    parser.add_argument("--json",action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = check_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PREVIEW_MANIFEST_ERROR: {exc}",file=sys.stderr)
        return 2
    counts={k:sum(r["actual"]["status"]==k for r in rows) for k in STATES}
    regression="PASS" if all(r["matches_expected"] for r in rows) else "FAIL"
    output={"regression":regression,"synthetic_only":True,"contract_adopted":False,
            "official_acceptance":False,"public_release_approved":False,
            "device_qa":"NOT_RUN","counts":counts,"cases":rows}
    if args.json:
        print(json.dumps(output,ensure_ascii=False,indent=2))
    else:
        for row in rows:
            print(f'{row["id"]}: {row["actual"]["status"]}/{row["actual"]["code"]}; '
                  f'expected={row["expected"]["status"]}/{row["expected"]["code"]}; '
                  f'matches={row["matches_expected"]}')
        print(f"regression={regression} counts={counts} contract_adopted=NO device_qa=NOT_RUN")
    return 0 if regression == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
