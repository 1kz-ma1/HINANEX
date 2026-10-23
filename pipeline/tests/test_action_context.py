"""Offline synthetic-only tests for the evacuation-action context foundation."""
import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from src.hinanex.action_context import (
    ActionKind, ActionSession, DrillFixture, HazardKind, PreEventContext,
    SessionMode, replace_preparation, review_action_context, start_drill,
    stop_drill,
)


class ActionContextTests(unittest.TestCase):
    def fixture(self, hazard=HazardKind.FLOOD, region="13123"):
        return DrillFixture(
            fixture_id="synthetic_flood_1", region_code=region, hazard=hazard,
            simulated_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
        )

    def test_normal_has_no_assessed_or_recommended_option(self):
        review = review_action_context(ActionSession())
        self.assertEqual(review.mode, SessionMode.NORMAL)
        self.assertIsNone(review.hazard)
        self.assertIsNone(review.fixture_id)
        self.assertFalse(review.synthetic)
        self.assertFalse(review.official_event_verified)
        self.assertFalse(review.published_for_disaster_use)
        self.assertEqual(len(review.options), len(ActionKind))
        self.assertTrue(all(x.status == "UNKNOWN" for x in review.options))
        self.assertEqual(review.unverified_profile_fields, ())

    def test_drill_never_claims_actual_disaster_even_with_full_profile(self):
        p = PreEventContext(
            region_code="13123", occupied_floor=3, upper_floor_access=True,
        )
        s = start_drill(p, self.fixture())
        review = review_action_context(s)
        self.assertTrue(review.synthetic)
        self.assertEqual(review.reason_codes[0], "SIMULATED_NOT_CURRENT")
        self.assertEqual(review.fixture_id, "synthetic_flood_1")
        self.assertEqual(review.hazard, HazardKind.FLOOD)
        self.assertFalse(review.official_event_verified)
        self.assertTrue(all(item.status == "UNKNOWN" for item in review.options))
        self.assertIn("house_collapse_zone", review.options[2].evidence_to_check)

    def test_other_hazard_never_inherits_flood_only_evidence_categories(self):
        landslide = review_action_context(start_drill(
            PreEventContext(), self.fixture(HazardKind.LANDSLIDE)
        ))
        self.assertIn("landslide_hazard_area", landslide.options[1].evidence_to_check)
        self.assertNotIn("house_collapse_zone", landslide.options[1].evidence_to_check)
        self.assertTrue(all(x.status == "UNKNOWN" for x in landslide.options))

    def test_every_hazard_is_unknown(self):
        for kind in HazardKind:
            with self.subTest(kind=kind):
                review = review_action_context(start_drill(
                    PreEventContext(), self.fixture(kind)
                ))
                self.assertEqual(review.hazard, kind)
                self.assertEqual(len(review.options), 4)
                self.assertTrue(all(x.status == "UNKNOWN" for x in review.options))

    def test_normal_cannot_carry_drill(self):
        with self.assertRaises(ValidationError):
            ActionSession(mode=SessionMode.NORMAL, drill=self.fixture())

    def test_drill_requires_fixture(self):
        with self.assertRaises(ValidationError):
            ActionSession(mode=SessionMode.DRILL)

    def test_fake_live_and_fake_official_fixture_rejected(self):
        with self.assertRaises(ValidationError):
            ActionSession(mode="LIVE")
        with self.assertRaises(ValidationError):
            self.fixture().model_copy(update={"fixture_kind": "OFFICIAL"})  # model_copy bypasses validation
        # Validate externally supplied objects, not internal model_copy.
        payload = self.fixture().model_dump()
        payload["fixture_kind"] = "OFFICIAL"
        with self.assertRaises(ValidationError):
            DrillFixture.model_validate(payload)

    def test_timestamp_must_be_timezone_aware(self):
        with self.assertRaises(ValidationError):
            DrillFixture(
                fixture_id="sample", region_code="13123", hazard=HazardKind.FLOOD,
                simulated_at=datetime(2026, 10, 23),
            )

    def test_profile_unknown_is_not_false_or_zero(self):
        profile = PreEventContext()
        self.assertIsNone(profile.occupied_floor)
        self.assertIsNone(profile.upper_floor_access)
        with self.assertRaises(ValidationError):
            PreEventContext(occupied_floor=0)
        with self.assertRaises(ValidationError):
            PreEventContext(region_code="1312")
        with self.assertRaises(ValidationError):
            PreEventContext(upper_floor_access="false")

    def test_personal_location_health_freeform_fields_forbidden(self):
        for values in [
            {"latitude": 35.7}, {"street_address": "example"},
            {"health_conditions": "example"}, {"is_safe_at_home": True},
        ]:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    PreEventContext.model_validate(values)

    def test_cross_region_old_building_information_blocked(self):
        with self.assertRaisesRegex(ValidationError, "cross-region"):
            start_drill(
                PreEventContext(region_code="13123", occupied_floor=2),
                self.fixture(region="15100"),
            )
        other_region = start_drill(
            PreEventContext(region_code="13123"), self.fixture(region="15100")
        )
        self.assertEqual(
            review_action_context(other_region).region_code, "15100"
        )

    def test_stop_discards_hazard_and_fixture_not_profile(self):
        session = start_drill(
            PreEventContext(region_code="13123", occupied_floor=3),
            self.fixture(),
        )
        stopped = stop_drill(session)
        self.assertEqual(stopped.mode, SessionMode.NORMAL)
        self.assertIsNone(stopped.drill)
        self.assertEqual(stopped.prepared.occupied_floor, 3)
        self.assertIsNone(review_action_context(stopped).hazard)

    def test_new_preparation_invalidates_old_drill(self):
        session = start_drill(PreEventContext(), self.fixture())
        changed = replace_preparation(
            session, PreEventContext(region_code="23100", revision=1)
        )
        self.assertEqual(changed.mode, SessionMode.NORMAL)
        self.assertIsNone(changed.drill)
        self.assertEqual(review_action_context(changed).region_code, "23100")

    def test_no_real_profile_values_in_review_payload(self):
        session = start_drill(
            PreEventContext(region_code="13123", occupied_floor=99),
            self.fixture(),
        )
        payload = review_action_context(session).model_dump_json()
        self.assertNotIn('"occupied_floor":99', payload)
        self.assertIn('"unverified_profile_fields"', payload)
        self.assertIn('"official_event_verified":false', payload)
        self.assertIn('"status":"UNKNOWN"', payload)

    def test_strict_rejects_extra_or_wrong_enums_and_option_promotion(self):
        with self.assertRaises(ValidationError):
            ActionSession.model_validate({"mode": "DRILL", "untrusted": 1})
        with self.assertRaises(ValidationError):
            DrillFixture.model_validate({
                **self.fixture().model_dump(), "hazard": "made_up_hazard",
            })
        review = review_action_context(ActionSession())
        promoted = review.options[0].model_dump()
        promoted["status"] = "CANDIDATE"
        from src.hinanex.action_context import ActionReviewItem
        with self.assertRaises(ValidationError):
            ActionReviewItem.model_validate(promoted)


if __name__ == "__main__":
    unittest.main()
