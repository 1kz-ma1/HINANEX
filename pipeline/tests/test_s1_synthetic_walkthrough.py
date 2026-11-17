"""P4 synthetic interaction reducer, command revision and fail-closed projection."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from src.hinanex.drill_session import (
    Mode, Session, SyntheticFixture, SYNTHETIC_ONLY,
)
from src.hinanex.s1_synthetic_narrowing import SyntheticReference
from src.hinanex.s1_synthetic_walkthrough import (
    IntentKind, WalkthroughIntent, WalkthroughState, WalkthroughProjection,
    apply_walkthrough_intent, project_walkthrough,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
T5 = T0 + timedelta(minutes=5)
T30 = T0 + timedelta(minutes=30)
FIXTURE = SyntheticFixture(
    "synthetic:p4-session", "13123", "flood", T0, T30, SYNTHETIC_ONLY,
)


def record(id="a", pet=True, step=True, **overrides):
    kwargs = dict(
        record_id=f"synthetic:{id}", fixture_id=FIXTURE.fixture_id,
        region_code="13123", hazard="flood", observed_at=T0,
        expires_at=T30,
        conditions=(("pet_support", pet), ("step_free", step)),
    )
    kwargs.update(overrides)
    return SyntheticReference(**kwargs)


ROWS = (record("a"), record("b", step=False), record("c", pet=False),
        record("d", pet=None), record("e", pet=False, step=None))


def action(kind, state, *, explicit=False, conditions=(),
           record_id=None, region=None, fixture=None, gen=None, rev=None):
    return WalkthroughIntent(
        kind, state.session.generation if gen is None else gen,
        state.revision if rev is None else rev, explicit,
        conditions, record_id, region, fixture,
    )


def run(state, kind, *, at=T5, records=ROWS, **kwargs):
    return apply_walkthrough_intent(state, action(kind, state, **kwargs), records, at)


def begin():
    current = WalkthroughState()
    t = run(current, IntentKind.START, at=T0, explicit=True,
            conditions=("pet_support",), fixture=FIXTURE, region="13123")
    assert t.status == "APPLIED_SYNTHETIC_ONLY"
    return t.state


class SyntheticWalkthroughP4Tests(unittest.TestCase):
    def test_start_requires_explicit_fixture_and_sets_fresh_state(self):
        s = begin()
        self.assertEqual(s.session.mode, Mode.DRILL)
        self.assertEqual((s.session.generation, s.revision), (1, 1))
        self.assertEqual(s.conditions, ("pet_support",))
        self.assertEqual(s.previous_conditions, ("pet_support",))
        self.assertIsNone(s.selected_record_id)

    def test_first_projection_has_no_change_and_no_implicit_review(self):
        p = project_walkthrough(begin(), ROWS, T5)
        self.assertEqual(p.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(p.result.newly_matching_synthetic_ids, ())
        self.assertEqual(p.result.no_longer_matching_synthetic_ids, ())
        self.assertIsNone(p.result.review)

    def test_change_conditions_projects_real_p3_diffs_and_reason_checks(self):
        s = run(begin(), IntentKind.SET_CONDITIONS, explicit=True,
                conditions=("step_free",)).state
        self.assertEqual(s.revision, 2)
        self.assertEqual(s.previous_conditions, ("pet_support",))
        self.assertEqual(s.conditions, ("step_free",))
        p = project_walkthrough(s, ROWS, T5)
        self.assertEqual(p.result.newly_matching_synthetic_ids,
                         ("synthetic:c", "synthetic:d"))
        self.assertEqual(p.result.no_longer_matching_synthetic_ids, ("synthetic:b",))
        self.assertEqual(p.result.unknown_after_synthetic_ids, ("synthetic:e",))
        self.assertEqual(p.result.rows[-1].after_missing, ("step_free",))

    def test_select_unknown_is_explicit_and_preserved(self):
        s = run(begin(), IntentKind.SET_CONDITIONS, explicit=True,
                conditions=("step_free",)).state
        chosen = run(s, IntentKind.REVIEW, explicit=True,
                     record_id="synthetic:e")
        self.assertEqual(chosen.status, "APPLIED_SYNTHETIC_ONLY")
        self.assertEqual(chosen.state.selected_record_id, "synthetic:e")
        p = project_walkthrough(chosen.state, ROWS, T5)
        self.assertEqual(p.result.review.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(p.result.review.comparison_status, "UNKNOWN")
        self.assertEqual(p.result.review.missing, ("step_free",))
        self.assertFalse(p.result.review.facility_safety_verified)

    def test_nonmatch_may_be_inspected_but_is_not_approved(self):
        s = begin()
        result = run(s, IntentKind.REVIEW, explicit=True,
                     record_id="synthetic:c")
        self.assertEqual(result.state.selected_record_id, "synthetic:c")
        p = project_walkthrough(result.state, ROWS, T5)
        self.assertEqual(p.result.review.comparison_status, "NOT_MATCHED_SYNTHETIC")
        self.assertEqual(p.result.review.failed, ("pet_support",))
        self.assertFalse(p.result.review.official_acceptance)

    def test_changing_conditions_clears_previous_review_even_if_same(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        self.assertEqual(s.selected_record_id, "synthetic:a")
        changed = run(s, IntentKind.SET_CONDITIONS, explicit=True,
                      conditions=("step_free",)).state
        self.assertIsNone(changed.selected_record_id)
        self.assertIsNone(project_walkthrough(changed, ROWS, T5).result.review)
        same = run(changed, IntentKind.SET_CONDITIONS, explicit=True,
                   conditions=("step_free",)).state
        self.assertIsNone(same.selected_record_id)
        self.assertEqual(same.revision, changed.revision + 1)

    def test_old_review_callback_same_generation_rejected_by_revision(self):
        s = begin()
        stale = action(IntentKind.REVIEW, s, explicit=True,
                       record_id="synthetic:a")
        s2 = run(s, IntentKind.SET_CONDITIONS, explicit=True,
                 conditions=("step_free",)).state
        out = apply_walkthrough_intent(s2, stale, ROWS, T5)
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "STALE_WALKTHROUGH_ACTION")
        self.assertIs(out.state, s2)
        self.assertIsNone(out.state.selected_record_id)

    def test_old_filter_callback_same_generation_does_not_overwrite_newer(self):
        s = begin()
        old = action(IntentKind.SET_CONDITIONS, s, explicit=True,
                     conditions=("pet_support", "step_free"))
        latest = run(s, IntentKind.SET_CONDITIONS, explicit=True,
                     conditions=("step_free",)).state
        out = apply_walkthrough_intent(latest, old, ROWS, T5)
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.state.conditions, ("step_free",))

    def test_old_start_callback_after_stop_cannot_restart(self):
        s = begin()
        delayed = action(IntentKind.START, s, explicit=True, conditions=("step_free",),
                         fixture=FIXTURE, region="13123")
        stopped = run(s, IntentKind.STOP).state
        out = apply_walkthrough_intent(stopped, delayed, ROWS, T5)
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.state.session.mode, Mode.NORMAL)

    def test_unknown_id_review_clears_earlier_selection(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        out = run(s, IntentKind.REVIEW, explicit=True,
                  record_id="synthetic:missing")
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "RECORD_NOT_IN_CURRENT_COMPARISON")
        self.assertIsNone(out.state.selected_record_id)
        self.assertEqual(out.state.revision, s.revision + 1)

    def test_outside_fixture_id_review_refused(self):
        rows = ROWS + (record("other", fixture_id="synthetic:different"),)
        out = run(begin(), IntentKind.REVIEW, records=rows, explicit=True,
                  record_id="synthetic:other")
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "RECORD_OUTSIDE_VALID_SYNTHETIC_SCOPE")
        self.assertIsNone(out.state.selected_record_id)

    def test_clear_review_keeps_same_comparison_but_removes_focus(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        clear = run(s, IntentKind.CLEAR_REVIEW)
        self.assertEqual(clear.status, "APPLIED_SYNTHETIC_ONLY")
        self.assertIsNone(clear.state.selected_record_id)
        self.assertEqual(clear.state.conditions, s.conditions)
        self.assertIsNone(project_walkthrough(clear.state, ROWS, T5).result.review)

    def test_stop_clears_every_synthetic_choice_and_projection(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        out = run(s, IntentKind.STOP)
        self.assertEqual(out.state.session.mode, Mode.NORMAL)
        self.assertEqual(out.state.conditions, ())
        self.assertEqual(out.state.previous_conditions, ())
        self.assertIsNone(out.state.selected_record_id)
        p = project_walkthrough(out.state, ROWS, T5)
        self.assertEqual(p.status, "BLOCKED")
        self.assertIsNone(p.result)

    def test_region_change_clears_results_and_retains_selected_region_only(self):
        s = begin()
        out = run(s, IntentKind.SELECT_REGION, explicit=True, region="15100")
        self.assertEqual(out.state.session.selected_region, "15100")
        self.assertEqual(out.state.session.mode, Mode.NORMAL)
        self.assertEqual(out.state.conditions, ())
        self.assertIsNone(project_walkthrough(out.state, ROWS, T5).result)

    def test_source_failed_clears_fictional_comparison_and_selection(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        out = run(s, IntentKind.SOURCE_FAILED)
        self.assertEqual(out.state.session.reason, "SOURCE_FAILED_DRILL_CLEARED")
        self.assertEqual(out.state.conditions, ())
        self.assertIsNone(out.state.selected_record_id)

    def test_reset_clears_all_session_and_drill_fields(self):
        s = begin()
        out = run(s, IntentKind.RESET)
        self.assertEqual(out.state.session.mode, Mode.NORMAL)
        self.assertIsNone(out.state.session.selected_region)
        self.assertEqual(out.state.conditions, ())
        self.assertGreater(out.state.revision, s.revision)

    def test_expiry_without_tick_blocks_projection_and_hides_old_review(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        blocked = project_walkthrough(s, ROWS, T30)
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertIsNone(blocked.result)
        self.assertEqual(blocked.reason_code, "DRILL_EXPIRED_OR_NOT_YET_VALID")

    def test_command_after_expiry_advances_generation_and_purges_memory(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        old = action(IntentKind.REVIEW, s, explicit=True,
                     record_id="synthetic:a")
        res = apply_walkthrough_intent(s, old, ROWS, T30)
        self.assertEqual(res.status, "BLOCKED")
        self.assertEqual(res.reason_code, "STALE_WALKTHROUGH_ACTION")
        self.assertEqual(res.state.session.generation, s.session.generation + 1)
        self.assertEqual(res.state.revision, s.revision + 1)
        self.assertIsNone(res.state.selected_record_id)
        self.assertEqual(res.state.conditions, ())
        self.assertIsNone(project_walkthrough(res.state, ROWS, T30).result)

    def test_expired_fixture_cannot_be_restarted_from_valid_revision(self):
        initial = WalkthroughState()
        out = run(initial, IntentKind.START, at=T30, explicit=True,
                  conditions=("pet_support",), fixture=FIXTURE, region="13123")
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "DRILL_INPUT_INVALID_OR_EXPIRED")
        self.assertEqual(out.state.session.mode, Mode.NORMAL)
        self.assertEqual(out.state.conditions, ())

    def test_non_drill_set_or_review_blocked(self):
        state = WalkthroughState()
        change = run(state, IntentKind.SET_CONDITIONS, explicit=True,
                     conditions=("step_free",))
        self.assertEqual(change.status, "BLOCKED")
        self.assertIs(change.state, state)
        review = run(state, IntentKind.REVIEW, explicit=True,
                     record_id="synthetic:a")
        self.assertEqual(review.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")

    def test_restarting_after_stop_does_not_reuse_old_selection(self):
        s = run(begin(), IntentKind.REVIEW, explicit=True,
                record_id="synthetic:a").state
        stopped = run(s, IntentKind.STOP).state
        restarted = run(
            stopped, IntentKind.START, explicit=True, conditions=("step_free",),
            fixture=FIXTURE, region="13123",
        ).state
        self.assertIsNone(restarted.selected_record_id)
        self.assertEqual(restarted.previous_conditions, ("step_free",))
        self.assertIsNone(project_walkthrough(restarted, ROWS, T5).result.review)

    def test_invalid_condition_and_duplicate_rejected(self):
        s = begin()
        for values in (("pet_support", "pet_support"), ("occupancy",), ()):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    run(s, IntentKind.SET_CONDITIONS, explicit=True, conditions=values)

    def test_invalid_user_actions_and_type_validation_fail_closed(self):
        s = begin()
        with self.assertRaises(ValueError):
            action(IntentKind.REVIEW, s, record_id="synthetic:a")
        with self.assertRaises(ValueError):
            action(IntentKind.REVIEW, s, explicit=True, record_id="real:123")
        with self.assertRaises(ValueError):
            action(IntentKind.START, s, explicit=True,
                   fixture=FIXTURE, conditions=("pet_support",), region="15100")
        with self.assertRaises(ValueError):
            action(IntentKind.SET_CONDITIONS, s, explicit=True,
                   conditions=["step_free"])
        with self.assertRaises(ValueError):
            WalkthroughIntent(IntentKind.STOP, True, 0)
        with self.assertRaises(ValueError):
            WalkthroughIntent(IntentKind.STOP, 1, True)

    def test_duplicate_record_ids_are_rejected_not_silently_matched(self):
        s = begin()
        with self.assertRaises(ValueError):
            project_walkthrough(s, ROWS + (ROWS[0],), T5)
        with self.assertRaises(ValueError):
            run(s, IntentKind.REVIEW, records=ROWS + (ROWS[0],),
                explicit=True, record_id="synthetic:a")

    def test_no_real_world_record_can_be_used(self):
        s = begin()
        with self.assertRaises(ValueError):
            record("real", source_authorization="OFFICIAL")
        with self.assertRaises(ValueError):
            run(s, IntentKind.REVIEW, records=list(ROWS),
                explicit=True, record_id="synthetic:a")

    def test_immutability_and_real_world_flags_cannot_be_forged(self):
        p = project_walkthrough(begin(), ROWS, T5)
        self.assertTrue(p.synthetic_only)
        self.assertTrue(all(x is False for x in (
            p.official_acceptance, p.live_data_verified,
            p.facility_safety_verified, p.route_safety_verified,
            p.release_approved,
        )))
        with self.assertRaises(FrozenInstanceError):
            p.revision = 9
        with self.assertRaises(FrozenInstanceError):
            p.result.rows = ()
        with self.assertRaisesRegex(ValueError, "real-world"):
            replace(p, facility_safety_verified=True)
        with self.assertRaisesRegex(ValueError, "blocked"):
            WalkthroughProjection("BLOCKED", "STALE", 1, 1, p.result)

    def test_repeated_projection_recomputes_without_mutating_state(self):
        s = begin()
        a = project_walkthrough(s, ROWS, T5)
        b = project_walkthrough(s, ROWS, T5)
        self.assertEqual(a, b)
        self.assertEqual(s.revision, 1)
        self.assertEqual(s.session.generation, 1)

    def test_snapshot_changes_from_active_to_blocked_at_exact_boundary(self):
        s = begin()
        self.assertEqual(project_walkthrough(s, ROWS, T30-timedelta(microseconds=1)).status,
                         "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(project_walkthrough(s, ROWS, T30).status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
