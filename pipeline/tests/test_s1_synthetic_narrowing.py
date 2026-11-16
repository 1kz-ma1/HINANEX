"""S1-P0 fixed synthetic condition-narrowing tests, no actual facility data."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import (
    DECISION_MATCH, DECISION_NOT_MATCHED, DECISION_UNKNOWN, NarrowRequest,
    SyntheticReference, narrow_synthetic_references,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
T5 = T0 + timedelta(minutes=5)
T30 = T0 + timedelta(minutes=30)


def drill():
    fixture = SyntheticFixture(
        fixture_id="synthetic:s1-drill-001", region_code="13123", hazard="flood",
        observed_at=T0, expires_at=T30, source_authorization=SYNTHETIC_ONLY,
    )
    return reduce_session(
        Session(),
        Event(Action.START_DRILL, 0, region_code="13123", fixture=fixture),
        T0,
    )


def reference(id="synthetic:record-a", *, pet=True, step=True, **kwargs):
    params = dict(
        record_id=id, fixture_id="synthetic:s1-drill-001",
        region_code="13123", hazard="flood", observed_at=T0, expires_at=T30,
        conditions=(("pet_support", pet), ("step_free", step)),
    )
    params.update(kwargs)
    return SyntheticReference(**params)


def request(generation=1, conditions=("pet_support", "step_free"), **kwargs):
    args = dict(expected_generation=generation, region_code="13123",
                hazard="flood", required_conditions=conditions)
    args.update(kwargs)
    return NarrowRequest(**args)


def evaluate(records, *, state=None, asked=None, now=T5):
    return narrow_synthetic_references(
        drill() if state is None else state,
        request() if asked is None else asked, tuple(records), now,
    )


class S1SyntheticNarrowingTests(unittest.TestCase):
    def test_two_conditions_intersect_only_fictional_explicit_matches(self):
        rows = (
            reference(), reference("synthetic:record-b", pet=False),
            reference("synthetic:record-c", step=False),
            reference("synthetic:record-d", pet=None),
            reference("synthetic:record-e", step=None),
            reference("synthetic:record-f", pet=False, step=None),
        )
        result = evaluate(rows)
        self.assertEqual(result.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(result.matched_synthetic_ids, ("synthetic:record-a",))
        self.assertEqual(
            [d.status for d in result.decisions],
            [DECISION_MATCH, DECISION_NOT_MATCHED, DECISION_NOT_MATCHED,
             DECISION_UNKNOWN, DECISION_UNKNOWN, DECISION_UNKNOWN],
        )
        self.assertEqual(result.decisions[-1].reason_code, "SYNTHETIC_CONDITION_UNVERIFIED")
        self.assertEqual(result.decisions[-1].missing, ("step_free",))
        self.assertEqual(result.decisions[-1].failed, ("pet_support",))

    def test_one_explicit_constraint_changes_synthetic_match_set(self):
        records = (reference(), reference("synthetic:b", step=False))
        result = evaluate(records, asked=request(conditions=("pet_support",)))
        self.assertEqual(result.matched_synthetic_ids, ("synthetic:record-a", "synthetic:b"))

    def test_unknown_is_not_excluded_or_negative(self):
        result = evaluate((reference(pet=None),))
        self.assertEqual(result.decisions[0].status, "UNKNOWN")
        self.assertEqual(result.decisions[0].reason_code, "SYNTHETIC_CONDITION_UNVERIFIED")
        self.assertEqual(result.decisions[0].failed, ())
        self.assertEqual(result.matched_synthetic_ids, ())

    def test_missing_condition_key_remains_unknown(self):
        item = reference(conditions=(("pet_support", True),))
        result = evaluate((item,))
        self.assertEqual(result.decisions[0].status, DECISION_UNKNOWN)
        self.assertEqual(result.decisions[0].missing, ("step_free",))

    def test_non_matching_region_and_hazard_are_unknown_not_negative(self):
        r1 = reference(region_code="15100")
        r2 = reference("synthetic:other-hazard", hazard="landslide")
        out = evaluate((r1, r2))
        self.assertTrue(all(x.status == DECISION_UNKNOWN for x in out.decisions))
        self.assertTrue(all(x.reason_code == "OUT_OF_SYNTHETIC_SCOPE" for x in out.decisions))

    def test_other_fixture_cannot_appear_as_match(self):
        out = evaluate((reference(fixture_id="synthetic:another-fixture"),))
        self.assertEqual(out.decisions[0].reason_code, "OUT_OF_SYNTHETIC_SCOPE")
        self.assertEqual(out.matched_synthetic_ids, ())

    def test_synthetic_fact_staleness_and_future_are_unknown(self):
        expired = reference(expires_at=T5)
        future = reference("synthetic:future", observed_at=T5+timedelta(minutes=1))
        result = evaluate((expired, future), now=T5)
        self.assertEqual([r.reason_code for r in result.decisions],
                         ["STALE_OR_FUTURE_SYNTHETIC_FACT"]*2)

    def test_s0_drill_end_exclusive_blocks_even_without_tick(self):
        out = evaluate((reference(),), now=T30)
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")
        self.assertEqual(out.decisions, ())
        self.assertEqual(out.matched_synthetic_ids, ())

    def test_s0_normal_never_looks_like_a_live_emergency(self):
        result = evaluate((reference(),), state=Session())
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")
        self.assertFalse(result.live_data_verified)

    def test_stale_generation_rejected_without_reusing_results(self):
        result = evaluate((reference(),), asked=request(generation=0))
        self.assertEqual(result.reason_code, "STALE_S0_GENERATION")
        self.assertEqual(result.decisions, ())
        old = drill()
        new = reduce_session(old, Event(Action.SELECT_REGION, 1, region_code="15100"), T5)
        result = evaluate((reference(),), state=new, asked=request(generation=1))
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.matched_synthetic_ids, ())

    def test_other_hazard_request_cannot_reuse_active_fixture(self):
        result = evaluate((reference(),), asked=request(hazard="landslide"))
        self.assertEqual(result.reason_code, "S0_CONTEXT_MISMATCH")
        self.assertEqual(result.decisions, ())

    def test_no_explicit_conditions_fail_closed(self):
        result = evaluate((reference(),), asked=request(conditions=()))
        self.assertEqual(result.reason_code, "EXPLICIT_CONDITION_REQUIRED")
        self.assertEqual(result.matched_synthetic_ids, ())

    def test_empty_records_returns_no_safety_candidates(self):
        result = evaluate(())
        self.assertEqual(result.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(result.matched_synthetic_ids, ())
        self.assertEqual(result.decisions, ())

    def test_duplicate_record_ids_rejected_without_arbitrary_first_winner(self):
        with self.assertRaisesRegex(ValueError, "duplicate test"):
            evaluate((reference(), reference()))

    def test_non_synthetic_id_and_official_claim_fail_validation(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            reference(id="real-facility-001")
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            reference(source_authorization="OFFICIAL_APPROVED")
        with self.assertRaisesRegex(ValueError, "synthetic"):
            reference(fixture_id="official:another")

    def test_bad_types_unknown_keys_duplicates_and_timezone_fail(self):
        with self.assertRaisesRegex(ValueError, "non-boolean"):
            reference(conditions=(("pet_support", 1),))
        with self.assertRaises(ValueError):
            reference(conditions=(("pet_support", True), ("pet_support", False)))
        with self.assertRaises(ValueError):
            reference(conditions=(("risk_index", True),))
        with self.assertRaises(ValueError):
            request(conditions=("pet_support", "pet_support"))
        with self.assertRaises(ValueError):
            request(conditions=("unapproved_field",))
        with self.assertRaises(ValueError):
            request(generation=True)
        with self.assertRaises(ValueError):
            reference(observed_at=T0.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            evaluate((reference(),), now=T5.replace(tzinfo=None))

    def test_output_cannot_claim_real_safety_opening_routes_or_release(self):
        result = evaluate((reference(),))
        self.assertIs(result.synthetic_only, True)
        for item in (
            result.official_acceptance, result.live_data_verified,
            result.facility_safety_verified, result.route_safety_verified,
            result.release_approved,
        ):
            self.assertIs(item, False)
        fields = set(vars(result.decisions[0]))
        self.assertFalse({"facility_name", "address", "latitude", "longitude",
                          "route_url", "currently_open", "official_designation"} & fields)
        self.assertEqual(result.decisions[0].status, "MATCHED_SYNTHETIC")

    def test_results_are_deterministic_ordered_and_do_not_mutate_inputs(self):
        state = drill()
        refs = (reference("synthetic:second", pet=False), reference("synthetic:first"))
        before = tuple(repr(x) for x in refs)
        a = narrow_synthetic_references(state, request(), refs, T5)
        b = narrow_synthetic_references(state, request(), refs, T5)
        self.assertEqual(a, b)
        self.assertEqual(before, tuple(repr(x) for x in refs))
        self.assertEqual([x.record_id for x in a.decisions],
                         ["synthetic:second", "synthetic:first"])


if __name__ == "__main__":
    unittest.main()
