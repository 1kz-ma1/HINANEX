"""S1-P2 explicit synthetic-review choice; unknown must never imply eligibility."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import NarrowRequest, SyntheticReference
from src.hinanex.s1_synthetic_comparison import CONDITION_FALSE, CONDITION_UNKNOWN
from src.hinanex.s1_synthetic_review_choice import (
    ExplicitReviewChoice, ReviewChoiceResult, choose_synthetic_for_review,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
T5 = T0 + timedelta(minutes=5)
T30 = T0 + timedelta(minutes=30)


def active():
    fixture = SyntheticFixture(
        fixture_id="synthetic:p2-review", region_code="13123", hazard="flood",
        observed_at=T0, expires_at=T30, source_authorization=SYNTHETIC_ONLY,
    )
    return reduce_session(Session(), Event(
        Action.START_DRILL, 0, region_code="13123", fixture=fixture,
    ), T0)


def fact(name="synthetic:one", pet=True, step=True, **kwargs):
    params = dict(
        record_id=name, fixture_id="synthetic:p2-review", region_code="13123",
        hazard="flood", observed_at=T0, expires_at=T30,
        conditions=(("pet_support", pet), ("step_free", step)),
    )
    params.update(kwargs)
    return SyntheticReference(**params)


def request(gen=1):
    return NarrowRequest(gen, "13123", "flood", ("pet_support", "step_free"))


def choice(name="synthetic:one", gen=1, explicit=True):
    return ExplicitReviewChoice(name, gen, explicit)


def select(records, *, state=None, req=None, picked=None, now=T5):
    return choose_synthetic_for_review(
        active() if state is None else state,
        request() if req is None else req,
        tuple(records),
        choice() if picked is None else picked,
        now,
    )


class S1ExplicitReviewChoiceTests(unittest.TestCase):
    def test_explicit_fictional_match_can_be_selected_only_for_review(self):
        result = select((fact(),))
        self.assertEqual(result.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(result.comparison_status, "MATCHED_SYNTHETIC")
        self.assertEqual(result.selected_record_id, "synthetic:one")
        self.assertEqual(result.reason_code, "EXPLICIT_FICTIONAL_REVIEW_SELECTION")

    def test_unknown_attribute_remains_unknown_when_selected(self):
        result = select((fact(step=None),))
        self.assertEqual(result.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(result.comparison_status, "UNKNOWN")
        self.assertEqual(result.comparison_reason_code, "SYNTHETIC_CONDITION_UNVERIFIED")
        self.assertEqual(result.missing, ("step_free",))
        self.assertEqual(result.checks[1].assessment, CONDITION_UNKNOWN)
        self.assertFalse(result.facility_safety_verified)

    def test_fictional_nonmatch_can_be_reviewed_without_approval(self):
        result = select((fact(pet=False),))
        self.assertEqual(result.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(result.comparison_status, "NOT_MATCHED_SYNTHETIC")
        self.assertEqual(result.failed, ("pet_support",))
        self.assertEqual(result.checks[0].assessment, CONDITION_FALSE)

    def test_missing_and_failed_remain_distinct(self):
        result = select((fact(pet=False, step=None),))
        self.assertEqual(result.comparison_status, "UNKNOWN")
        self.assertEqual(result.missing, ("step_free",))
        self.assertEqual(result.failed, ("pet_support",))
        self.assertEqual([x.assessment for x in result.checks],
                         [CONDITION_FALSE, CONDITION_UNKNOWN])

    def test_no_explicit_user_action_returns_empty_blocked_state(self):
        result = select((fact(),), picked=choice(explicit=False))
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "EXPLICIT_USER_SELECTION_REQUIRED")
        self.assertIsNone(result.selected_record_id)
        self.assertEqual(result.checks, ())

    def test_not_in_current_comparison_returns_blocked(self):
        result = select((fact(),), picked=choice(name="synthetic:not-present"))
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "RECORD_NOT_IN_CURRENT_COMPARISON")
        self.assertIsNone(result.comparison_status)

    def test_out_of_scope_record_cannot_be_selected_even_for_review(self):
        result = select((fact(region_code="15100"),))
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason_code, "RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE")
        self.assertEqual(result.checks, ())

    def test_wrong_hazard_or_fixture_cannot_be_selected(self):
        for extra in (
            {"hazard": "landslide"},
            {"fixture_id": "synthetic:another"},
        ):
            with self.subTest(extra=extra):
                out = select((fact(**extra),))
                self.assertEqual(out.reason_code, "RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE")
                self.assertIsNone(out.selected_record_id)

    def test_expired_and_future_facts_cannot_be_selected(self):
        for extra in (
            {"expires_at": T5},
            {"observed_at": T5 + timedelta(seconds=1)},
        ):
            with self.subTest(extra=extra):
                out = select((fact(**extra),))
                self.assertEqual(out.status, "BLOCKED")
                self.assertIsNone(out.selected_record_id)

    def test_expired_session_blocks_at_exact_boundary(self):
        out = select((fact(),), now=T30)
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")
        self.assertEqual(out.checks, ())

    def test_normal_state_does_not_claim_selection(self):
        out = select((fact(),), state=Session())
        self.assertEqual(out.status, "BLOCKED")
        self.assertIsNone(out.selected_record_id)

    def test_stale_selected_generation_refused(self):
        out = select((fact(),), picked=choice(gen=0))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "STALE_REVIEW_CHOICE")

    def test_stale_request_generation_refused_even_if_choice_current(self):
        out = select((fact(),), req=request(gen=0))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "STALE_S0_GENERATION")

    def test_stopped_or_failed_session_has_no_persistent_selection(self):
        orig = active()
        first = select((fact(),), state=orig)
        self.assertEqual(first.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        for act in (Action.STOP_DRILL, Action.SOURCE_FAILED, Action.RESET):
            with self.subTest(action=act):
                state = reduce_session(orig, Event(act, 1), T5)
                latest = select((fact(),), state=state, picked=choice(gen=2))
                self.assertEqual(latest.status, "BLOCKED")
                self.assertIsNone(latest.selected_record_id)

    def test_region_change_invalidates_prior_user_choice(self):
        state = reduce_session(active(), Event(Action.SELECT_REGION, 1, region_code="15100"), T5)
        out = select((fact(),), state=state, picked=choice(gen=2))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.checks, ())

    def test_selection_does_not_change_input_order_or_core(self):
        records = (fact("synthetic:b", step=None), fact("synthetic:one"))
        picked = select(records)
        self.assertEqual(picked.selected_record_id, "synthetic:one")
        self.assertEqual(picked.comparison_status, "MATCHED_SYNTHETIC")
        self.assertEqual(records[0].record_id, "synthetic:b")

    def test_empty_comparison_cannot_be_selected(self):
        out = select(())
        self.assertEqual(out.reason_code, "RECORD_NOT_IN_CURRENT_COMPARISON")
        self.assertEqual(out.status, "BLOCKED")

    def test_bad_choice_types_rejected_before_processing(self):
        with self.assertRaises(ValueError):
            ExplicitReviewChoice("", 1, True)
        with self.assertRaises(ValueError):
            ExplicitReviewChoice("synthetic:one", True, True)
        with self.assertRaises(ValueError):
            ExplicitReviewChoice("synthetic:one", 1, "yes")
        with self.assertRaises(TypeError):
            choose_synthetic_for_review(active(), request(), (fact(),), {}, T5)

    def test_non_synthetic_inputs_rejected_upstream(self):
        with self.assertRaises(ValueError):
            fact(name="real-facility")
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            fact(source_authorization="OFFICIAL_APPROVED")

    def test_duplicate_ids_fail_instead_of_choosing_first(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            select((fact(), fact()))

    def test_result_cannot_be_mutated_or_grant_real_world_safety(self):
        out = select((fact(),))
        self.assertIs(out.synthetic_only, True)
        self.assertIs(out.review_only, True)
        self.assertTrue(all(x is False for x in (
            out.official_acceptance, out.live_data_verified,
            out.facility_safety_verified, out.route_safety_verified,
            out.release_approved,
        )))
        with self.assertRaises(FrozenInstanceError):
            out.comparison_status = "ELIGIBLE"
        with self.assertRaisesRegex(ValueError, "real-world approval"):
            ReviewChoiceResult(
                "REVIEW_SELECTED_SYNTHETIC_ONLY", "fake", 1,
                official_acceptance=True,
            )

    def test_blocked_result_rejects_retained_previous_selection(self):
        with self.assertRaisesRegex(ValueError, "blocked"):
            ReviewChoiceResult(
                "BLOCKED", "STALE", 2,
                selected_record_id="synthetic:one",
            )

    def test_repeat_call_is_deterministic_without_storage(self):
        state = active()
        records = (fact(step=None),)
        first = select(records, state=state)
        second = select(records, state=state)
        self.assertEqual(first, second)
        self.assertEqual(first.generation, 1)


if __name__ == "__main__":
    unittest.main()
