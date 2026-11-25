"""Synthetic S0 safety tests; no municipal data, endpoints or personal information."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.hinanex.drill_session import (
    Action, DRILL_NOTICE, Event, Mode, NORMAL_NOTICE, SYNTHETIC_ONLY,
    Session, StaleSessionError, SyntheticFixture, reduce_session, safe_view,
)

T0 = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def fixture(region="13123", start=T0, minutes=30):
    return SyntheticFixture(
        fixture_id="synthetic:demo-001", region_code=region,
        hazard="flood", observed_at=start,
        expires_at=start + timedelta(minutes=minutes),
        source_authorization=SYNTHETIC_ONLY,
    )


def act(state, action, *, now=T0, **kwargs):
    return reduce_session(state, Event(
        action=action, expected_generation=state.generation, **kwargs
    ), now)


class DrillSessionTests(unittest.TestCase):
    def test_normal_is_not_live_and_has_no_source(self):
        view = safe_view(Session(), T0)
        self.assertEqual(view.mode, Mode.NORMAL)
        self.assertFalse(view.live_data_verified)
        self.assertEqual(view.notice, NORMAL_NOTICE)
        self.assertIsNone(view.fixture_id)
        self.assertIsNone(view.hazard)

    def test_explicit_drill_start_is_synthetic_only(self):
        s = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        v = safe_view(s, T0)
        self.assertEqual(v.mode, Mode.DRILL)
        self.assertEqual(v.notice, DRILL_NOTICE)
        self.assertFalse(v.live_data_verified)
        self.assertEqual(v.fixture_id, "synthetic:demo-001")
        self.assertEqual(v.source_authorization, SYNTHETIC_ONLY)

    def test_drill_requires_explicit_region_and_fixture(self):
        s = act(Session(), Action.START_DRILL)
        self.assertEqual(s.mode, Mode.NORMAL)
        self.assertIsNone(s.fixture)
        self.assertEqual(s.reason, "DRILL_INPUT_MISSING")

    def test_drill_rejects_mismatched_region_and_clears_previous(self):
        active = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        after = act(active, Action.START_DRILL, fixture=fixture("15100"), region_code="13123")
        self.assertEqual(after.mode, Mode.NORMAL)
        self.assertIsNone(after.fixture)
        self.assertEqual(after.reason, "DRILL_INPUT_INVALID_OR_EXPIRED")

    def test_expired_fixture_fails_closed_not_accepted_as_live(self):
        s = act(Session(), Action.START_DRILL, now=T0+timedelta(minutes=30),
                fixture=fixture(), region_code="13123")
        self.assertEqual(s.mode, Mode.NORMAL)
        self.assertIsNone(s.fixture)
        self.assertEqual(s.reason, "DRILL_INPUT_INVALID_OR_EXPIRED")

    def test_future_observation_does_not_become_current_event(self):
        future = fixture(start=T0 + timedelta(minutes=10))
        s = act(Session(), Action.START_DRILL, fixture=future, region_code="13123")
        self.assertEqual(s.mode, Mode.NORMAL)
        self.assertEqual(s.reason, "DRILL_INPUT_INVALID_OR_EXPIRED")

    def test_expiry_view_hides_data_without_a_tick(self):
        active = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        view = safe_view(active, T0 + timedelta(minutes=30))
        self.assertEqual(view.mode, Mode.NORMAL)
        self.assertIsNone(view.fixture_id)
        self.assertEqual(view.reason, "DRILL_EXPIRED_OR_NOT_YET_VALID")

    def test_any_next_event_clears_expired_drill(self):
        active = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        after = act(active, Action.CLEAR_PREFERRED_REGION, now=T0+timedelta(hours=1))
        self.assertEqual(after.mode, Mode.NORMAL)
        self.assertIsNone(after.fixture)

    def test_region_change_clears_all_old_fixture_and_preserves_preference(self):
        s = act(Session(), Action.SET_PREFERRED_REGION, region_code="13123", explicit_consent=True)
        s = act(s, Action.START_DRILL, fixture=fixture(), region_code="13123")
        s = act(s, Action.SELECT_REGION, region_code="15100")
        self.assertEqual(s.selected_region, "15100")
        self.assertEqual(s.preferred_region, "13123")
        self.assertEqual(s.mode, Mode.NORMAL)
        self.assertIsNone(s.fixture)

    def test_same_region_explicit_reselection_clears_previous_fixture(self):
        s = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        s = act(s, Action.SELECT_REGION, region_code="13123")
        self.assertIsNone(s.fixture)

    def test_source_failure_does_not_reuse_old_drill(self):
        s = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        s = act(s, Action.SOURCE_FAILED)
        self.assertEqual(s.reason, "SOURCE_FAILED_DRILL_CLEARED")
        self.assertEqual(s.mode, Mode.NORMAL)
        self.assertIsNone(s.fixture)

    def test_stop_clears_fixture_retaining_selected_region(self):
        s = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        s = act(s, Action.STOP_DRILL)
        self.assertEqual(s.selected_region, "13123")
        self.assertIsNone(s.fixture)
        self.assertEqual(s.mode, Mode.NORMAL)

    def test_preference_requires_explicit_consent_and_is_in_memory_only(self):
        s = act(Session(), Action.SET_PREFERRED_REGION, region_code="13123", explicit_consent=False)
        self.assertIsNone(s.preferred_region)
        self.assertEqual(s.reason, "PREPARATION_NOT_CONSENTED")
        s = act(s, Action.SET_PREFERRED_REGION, region_code="13123", explicit_consent=True)
        self.assertEqual(s.preferred_region, "13123")
        s = act(s, Action.CLEAR_PREFERRED_REGION)
        self.assertIsNone(s.preferred_region)

    def test_reset_drops_all_region_preference_and_fixture(self):
        s = act(Session(), Action.SET_PREFERRED_REGION, region_code="13123", explicit_consent=True)
        s = act(s, Action.START_DRILL, fixture=fixture(), region_code="13123")
        new = act(s, Action.RESET)
        self.assertEqual(new.mode, Mode.NORMAL)
        self.assertIsNone(new.selected_region)
        self.assertIsNone(new.preferred_region)
        self.assertIsNone(new.fixture)
        self.assertGreater(new.generation, s.generation)

    def test_stale_async_response_cannot_restore_old_fixture(self):
        s = act(Session(), Action.START_DRILL, fixture=fixture(), region_code="13123")
        old_version = s.generation
        s = act(s, Action.SELECT_REGION, region_code="15100")
        with self.assertRaises(StaleSessionError):
            reduce_session(s, Event(
                action=Action.START_DRILL, expected_generation=old_version,
                fixture=fixture(), region_code="13123"
            ), T0)
        self.assertEqual(s.selected_region, "15100")
        self.assertIsNone(s.fixture)

    def test_fixture_requires_explicit_synthetic_auth_not_official_claim(self):
        with self.assertRaisesRegex(ValueError, "only explicitly synthetic"):
            replace(fixture(), source_authorization="OFFICIAL_APPROVED")
        with self.assertRaisesRegex(ValueError, "only explicitly synthetic"):
            replace(fixture(), source_authorization="")

    def test_invalid_region_hazard_fixture_and_expiry_fail(self):
        for code in ("", "Tokyo", "1312", "131230", "../../1"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                fixture(region=code)
        with self.assertRaises(ValueError):
            replace(fixture(), hazard="hazard;unsafe")
        with self.assertRaises(ValueError):
            replace(fixture(), fixture_id="../unsafe?asset")
        with self.assertRaisesRegex(ValueError, "expires_at"):
            fixture(minutes=0)

    def test_naive_time_rejected_at_both_input_and_runtime(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            fixture(start=T0.replace(tzinfo=None))
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            safe_view(Session(), datetime(2026, 11, 13))

    def test_manual_state_cannot_be_normal_with_drill_fixture(self):
        with self.assertRaises(ValueError):
            Session(mode=Mode.NORMAL, fixture=fixture())
        with self.assertRaises(ValueError):
            Session(mode=Mode.DRILL, selected_region="15100", fixture=fixture())

    def test_no_implicit_geolocation_or_storage_side_effects(self):
        state = Session()
        state = act(state, Action.SELECT_REGION, region_code="13123")
        self.assertEqual(state.selected_region, "13123")
        self.assertIsNone(state.preferred_region)
        self.assertIsNone(state.fixture)
        self.assertFalse(safe_view(state, T0).live_data_verified)


if __name__ == "__main__":
    unittest.main()
