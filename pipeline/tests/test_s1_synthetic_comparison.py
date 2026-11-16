"""S1-P1 synthetic-only comparison: deterministic result and safe failure tests."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import (
    NarrowRequest, SyntheticReference, DECISION_MATCH, DECISION_UNKNOWN,
)
from preview_s1_synthetic_comparison import synthetic_preview
from src.hinanex.s1_synthetic_comparison import (
    ComparisonTotals, CONDITION_TRUE, CONDITION_FALSE, CONDITION_UNKNOWN,
    CONDITION_NOT_EVALUATED, compare_synthetic_conditions,
    comparison_as_dict, comparison_as_json,
)

T0 = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)
T5 = T0 + timedelta(minutes=5)
T30 = T0 + timedelta(minutes=30)


def start():
    fixture = SyntheticFixture(
        fixture_id="synthetic:comparison-fixture", region_code="13123",
        hazard="flood", observed_at=T0, expires_at=T30,
        source_authorization=SYNTHETIC_ONLY,
    )
    return reduce_session(Session(), Event(
        Action.START_DRILL, 0, region_code="13123", fixture=fixture,
    ), T0)


def item(key="synthetic:alpha", pet=True, step=True, **kwargs):
    v = dict(
        record_id=key, fixture_id="synthetic:comparison-fixture",
        region_code="13123", hazard="flood", observed_at=T0,
        expires_at=T30, conditions=(("pet_support", pet), ("step_free", step)),
    )
    v.update(kwargs)
    return SyntheticReference(**v)


def query(*conditions, generation=1):
    return NarrowRequest(
        expected_generation=generation, region_code="13123",
        hazard="flood", required_conditions=conditions or ("pet_support", "step_free"),
    )


def run(records, *, session=None, conditions=None, now=T5):
    return compare_synthetic_conditions(
        start() if session is None else session,
        query(*(conditions if conditions is not None else ("pet_support", "step_free"))),
        tuple(records), now,
    )


class S1SyntheticComparisonTests(unittest.TestCase):
    def test_multi_condition_matrix_and_totals(self):
        records = (
            item(), item("synthetic:beta", pet=False),
            item("synthetic:gamma", pet=None),
            item("synthetic:delta", step=None),
            item("synthetic:epsilon", pet=False, step=None),
        )
        result = run(records)
        self.assertEqual(result.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(result.reason_code, "NOT_REAL_WORLD_ELIGIBILITY")
        self.assertEqual(result.totals, ComparisonTotals(1, 1, 3))
        self.assertEqual(tuple(row.record_id for row in result.rows),
                         tuple(r.record_id for r in records))
        self.assertEqual(result.rows[0].status, DECISION_MATCH)
        self.assertEqual(tuple(c.assessment for c in result.rows[0].checks),
                         (CONDITION_TRUE, CONDITION_TRUE))

    def test_known_negative_is_only_fictional_non_match(self):
        row = run((item(pet=False),)).rows[0]
        self.assertEqual(row.status, "NOT_MATCHED_SYNTHETIC")
        self.assertEqual(row.failed, ("pet_support",))
        self.assertEqual(row.missing, ())
        self.assertEqual(tuple(c.assessment for c in row.checks),
                         (CONDITION_FALSE, CONDITION_TRUE))

    def test_missing_and_negative_is_unknown_with_explanation(self):
        row = run((item(pet=False, step=None),)).rows[0]
        self.assertEqual(row.status, DECISION_UNKNOWN)
        self.assertEqual(row.missing, ("step_free",))
        self.assertEqual(row.failed, ("pet_support",))
        self.assertEqual(tuple(c.assessment for c in row.checks),
                         (CONDITION_FALSE, CONDITION_UNKNOWN))
        self.assertEqual(row.reason_code, "SYNTHETIC_CONDITION_UNVERIFIED")

    def test_absent_attribute_is_not_automatic_false(self):
        row = run((item(conditions=(("pet_support", True),)),)).rows[0]
        self.assertEqual(row.status, "UNKNOWN")
        self.assertEqual(row.missing, ("step_free",))
        self.assertEqual(tuple(c.assessment for c in row.checks),
                         (CONDITION_TRUE, CONDITION_UNKNOWN))

    def test_out_of_scope_region_does_not_leak_facts(self):
        row = run((item(region_code="15100"),)).rows[0]
        self.assertEqual(row.status, "UNKNOWN")
        self.assertEqual(row.reason_code, "OUT_OF_SYNTHETIC_SCOPE")
        self.assertEqual(tuple(c.assessment for c in row.checks),
                         (CONDITION_NOT_EVALUATED, CONDITION_NOT_EVALUATED))
        self.assertEqual(row.failed, ())
        self.assertEqual(row.missing, ())

    def test_other_hazard_and_fixture_never_match(self):
        records = (
            item("synthetic:other-hazard", hazard="landslide"),
            item("synthetic:other-fixture", fixture_id="synthetic:other-fixture"),
        )
        out = run(records)
        self.assertEqual(out.totals, ComparisonTotals(0, 0, 2))
        self.assertTrue(all(x.reason_code == "OUT_OF_SYNTHETIC_SCOPE" for x in out.rows))

    def test_expired_reference_shows_not_evaluated_not_stale_match(self):
        row = run((item(expires_at=T5),)).rows[0]
        self.assertEqual(row.status, "UNKNOWN")
        self.assertEqual(row.reason_code, "STALE_OR_FUTURE_SYNTHETIC_FACT")
        self.assertTrue(all(x.assessment == CONDITION_NOT_EVALUATED for x in row.checks))

    def test_future_reference_is_not_treated_as_available(self):
        row = run((item(observed_at=T5+timedelta(seconds=1)),)).rows[0]
        self.assertEqual(row.reason_code, "STALE_OR_FUTURE_SYNTHETIC_FACT")
        self.assertEqual(row.status, "UNKNOWN")

    def test_expiry_at_exact_boundary_blocks_whole_matrix(self):
        result = run((item(),), now=T30)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")
        self.assertEqual(result.rows, ())
        self.assertEqual(result.required_conditions, ())
        self.assertEqual(result.expires_at, None)
        self.assertEqual(result.totals, ComparisonTotals())

    def test_normal_state_blocks_without_reusing_old_results(self):
        result = run((item(),), session=Session())
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.rows, ())
        self.assertEqual(result.totals, ComparisonTotals())

    def test_stop_and_source_failure_revoke_every_match(self):
        original = start()
        for action in (Action.STOP_DRILL, Action.SOURCE_FAILED, Action.RESET):
            with self.subTest(action=action):
                state = reduce_session(original, Event(action, 1), T5)
                out = run((item(),), session=state)
                self.assertEqual(out.status, "BLOCKED")
                self.assertEqual(out.rows, ())

    def test_region_change_clears_comparison_and_old_generation(self):
        original = start()
        changed = reduce_session(original, Event(
            Action.SELECT_REGION, 1, region_code="15100",
        ), T5)
        report = run((item(),), session=changed)
        self.assertEqual(report.rows, ())
        self.assertEqual(report.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")

    def test_stale_generation_blocks_without_projecting_rows(self):
        report = compare_synthetic_conditions(
            start(), query("pet_support", generation=0), (item(),), T5,
        )
        self.assertEqual(report.reason_code, "STALE_S0_GENERATION")
        self.assertEqual(report.rows, ())
        self.assertEqual(report.required_conditions, ())

    def test_no_condition_never_auto_selects_everything(self):
        result = compare_synthetic_conditions(
            start(), NarrowRequest(1, "13123", "flood", ()), (item(),), T5,
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "EXPLICIT_CONDITION_REQUIRED")

    def test_single_constraint_recomputes_different_matrix(self):
        references = (item(), item("synthetic:beta", step=False))
        report = run(references, conditions=("pet_support",))
        self.assertEqual(report.totals, ComparisonTotals(2, 0, 0))
        self.assertEqual(report.required_conditions, ("pet_support",))
        self.assertEqual([len(row.checks) for row in report.rows], [1, 1])

    def test_zero_records_is_not_successful_shelter_discovery(self):
        out = run(())
        self.assertEqual(out.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(out.totals, ComparisonTotals())
        self.assertEqual(out.rows, ())
        self.assertFalse(out.facility_safety_verified)

    def test_serialization_is_exact_and_only_fictional_fields(self):
        report = run((item(),))
        data = comparison_as_dict(report)
        self.assertEqual(data["schema_id"], "hinanex.d.s1.synthetic_comparison.internal.v0.1")
        self.assertEqual(data["required_conditions"], ("pet_support", "step_free"))
        self.assertEqual(data["expires_at"], T30.isoformat())
        self.assertEqual(data["evaluated_at"], T5.isoformat())
        self.assertEqual(data["rows"][0]["checks"][0]["assessment"], CONDITION_TRUE)
        self.assertEqual(json.loads(comparison_as_json(report))["rows"][0]["record_id"],
                         "synthetic:alpha")
        self.assertFalse(set(data["rows"][0]) & {
            "facility_name", "address", "latitude", "longitude",
            "official_designation", "route_url", "current_open_status",
        })

    def test_no_official_live_route_facility_or_release_assertions(self):
        out = run((item(),))
        self.assertTrue(out.synthetic_only)
        for field in (
            out.official_acceptance, out.live_data_verified,
            out.facility_safety_verified, out.route_safety_verified,
            out.release_approved,
        ):
            self.assertIs(field, False)
        self.assertEqual(out.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(out.reason_code, "NOT_REAL_WORLD_ELIGIBILITY")

    def test_immutable_rows_and_determinism_without_input_mutation(self):
        original = (item("synthetic:z", pet=False), item("synthetic:a"))
        first = run(original)
        second = run(original)
        self.assertEqual(first, second)
        self.assertEqual(first.rows[0].record_id, "synthetic:z")
        self.assertEqual(original[0].record_id, "synthetic:z")
        with self.assertRaises(FrozenInstanceError):
            first.rows[0].status = DECISION_MATCH

    def test_duplicate_ids_and_bad_source_are_rejected_upstream(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run((item(), item()))
        with self.assertRaises(ValueError):
            item(source_authorization="OFFICIAL")
        with self.assertRaises(ValueError):
            item(key="real:facility")

    def test_offline_preview_renders_actual_fixed_comparison(self):
        first = synthetic_preview()
        second = synthetic_preview()
        self.assertEqual(first, second)
        result = json.loads(first)
        self.assertEqual(result["totals"], {
            "matched_synthetic": 1, "not_matched_synthetic": 1, "unknown": 2,
        })
        self.assertEqual(
            [row["record_id"] for row in result["rows"]],
            ["synthetic:example-a", "synthetic:example-b",
             "synthetic:example-c", "synthetic:example-d"],
        )
        self.assertFalse(result["official_acceptance"])
        self.assertFalse(result["release_approved"])

    def test_local_comparison_is_not_cross_page_cache(self):
        state = start()
        result = compare_synthetic_conditions(state, query("pet_support"), (item(),), T5)
        self.assertEqual(result.totals.matched_synthetic, 1)
        # Calling *again* against a later S0 state is required: old result
        # is never accepted as an argument to the comparison function.
        ended = reduce_session(state, Event(Action.STOP_DRILL, 1), T5)
        latest = compare_synthetic_conditions(
            ended, query("pet_support", generation=2), (item(),), T5,
        )
        self.assertEqual(latest.status, "BLOCKED")
        self.assertEqual(latest.rows, ())


if __name__ == "__main__":
    unittest.main()
