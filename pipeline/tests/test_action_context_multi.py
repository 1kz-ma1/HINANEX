"""Synthetic multi-hazard review: deterministic checks, no safety verdict."""
import unittest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from src.hinanex.action_context import HazardKind, PreEventContext, SessionMode
from src.hinanex.action_context_multi import (
    CueAvailability, CueReviewState, MultiHazardDrill, MultiHazardFixture,
    SyntheticCue, replace_multi_hazard_fixture, review_multi_hazard_drill,
    start_multi_hazard_drill, stop_multi_hazard_drill,
)

EVENT_TIME = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


class MultiHazardActionTests(unittest.TestCase):
    def fixture(self, hazards=(HazardKind.FLOOD, HazardKind.LANDSLIDE),
                cues=(), region="13123"):
        return MultiHazardFixture(
            fixture_id="synthetic_2026_flood_slopes", region_code=region,
            simulated_at=EVENT_TIME, hazards=hazards, cues=cues,
        )

    def cue(self, hazard=HazardKind.FLOOD, category="hazard_area",
            availability=CueAvailability.SYNTHETIC_PRESENT,
            observed_at=None, expires_at=None):
        return SyntheticCue(
            hazard=hazard, category=category, availability=availability,
            observed_at=observed_at or (EVENT_TIME - timedelta(hours=2))
            if availability is CueAvailability.SYNTHETIC_PRESENT else None,
            expires_at=expires_at or (EVENT_TIME + timedelta(hours=1))
            if availability is CueAvailability.SYNTHETIC_PRESENT else None,
        )

    def review(self, fixture=None, profile=None):
        return review_multi_hazard_drill(start_multi_hazard_drill(
            profile or PreEventContext(), fixture or self.fixture(),
        ))

    def cue_state(self, review, hazard, category):
        return next(
            cue.state for cue in review.cue_reviews
            if cue.hazard is hazard and cue.category == category
        )

    def test_composite_is_unknown_not_a_safe_decision(self):
        review = self.review()
        self.assertTrue(review.synthetic)
        self.assertFalse(review.official_event_verified)
        self.assertFalse(review.published_for_disaster_use)
        self.assertEqual(review.mode, "DRILL")
        self.assertEqual(len(review.action_reviews), 2)
        self.assertTrue(all(item.status == "UNKNOWN" for sub in review.action_reviews
                            for item in sub.options))
        self.assertTrue(all(item.status == "UNKNOWN" for item in review.cue_reviews))

    def test_flood_landslide_requires_independent_cross_hazard_review(self):
        codes = {c.code for c in self.review().conflict_reviews}
        self.assertIn("INDEPENDENT_HAZARD_SCOPE_CHECK_REQUIRED", codes)
        self.assertIn("HIGH_GROUND_IS_NOT_PROOF_OF_CROSS_HAZARD_SAFETY", codes)

    def test_single_hazard_cannot_claim_intersection(self):
        review = self.review(self.fixture(hazards=(HazardKind.FLOOD,)))
        self.assertEqual(review.conflict_reviews, ())
        self.assertEqual(len(review.action_reviews), 1)

    def test_flood_surge_never_combines_source_meaning(self):
        review = self.review(self.fixture(hazards=(
            HazardKind.FLOOD, HazardKind.STORM_SURGE,
        )))
        self.assertIn(
            "INUNDATION_SOURCES_REQUIRE_SEPARATE_SCOPE_REVIEW",
            {c.code for c in review.conflict_reviews},
        )

    def test_tsunami_landslide_high_ground_not_automatically_safe(self):
        review = self.review(self.fixture(hazards=(
            HazardKind.TSUNAMI, HazardKind.LANDSLIDE,
        )))
        self.assertIn(
            "HIGH_GROUND_IS_NOT_PROOF_OF_CROSS_HAZARD_SAFETY",
            {c.code for c in review.conflict_reviews},
        )
        self.assertTrue(all(x.status == "UNKNOWN" for x in review.cue_reviews))

    def test_unmentioned_category_is_not_provided_not_zero(self):
        review = self.review()
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "official_instructions"),
            CueReviewState.NOT_PROVIDED,
        )

    def test_simulated_present_remains_unverified(self):
        review = self.review(self.fixture(cues=(self.cue(),)))
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "hazard_area"),
            CueReviewState.SYNTHETIC_ONLY_UNVERIFIED,
        )

    def test_expired_synthetic_signal_never_counts_as_current(self):
        review = self.review(self.fixture(cues=(self.cue(
            expires_at=EVENT_TIME - timedelta(minutes=1),
        ),)))
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "hazard_area"),
            CueReviewState.EXPIRED_SYNTHETIC,
        )

    def test_expiration_at_exact_time_is_expired(self):
        review = self.review(self.fixture(cues=(self.cue(
            expires_at=EVENT_TIME,
        ),)))
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "hazard_area"),
            CueReviewState.EXPIRED_SYNTHETIC,
        )

    def test_unavailable_distinct_from_missing(self):
        cues = (
            self.cue(availability=CueAvailability.SOURCE_UNAVAILABLE),
            self.cue(category="movement_risk", availability=CueAvailability.EXPLICITLY_MISSING),
        )
        review = self.review(self.fixture(cues=cues))
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "hazard_area"),
            CueReviewState.SOURCE_UNAVAILABLE_IN_FIXTURE,
        )
        self.assertEqual(
            self.cue_state(review, HazardKind.FLOOD, "movement_risk"),
            CueReviewState.MISSING_IN_FIXTURE,
        )

    def test_duplicate_hazard_and_duplicate_cue_rejected(self):
        with self.assertRaisesRegex(ValidationError, "duplicate hazards"):
            self.fixture(hazards=(HazardKind.FLOOD, HazardKind.FLOOD))
        with self.assertRaisesRegex(ValidationError, "duplicate cue"):
            self.fixture(cues=(self.cue(), self.cue()))

    def test_cue_wrong_hazard_or_category_rejected(self):
        with self.assertRaisesRegex(ValidationError, "outside fixture"):
            self.fixture(hazards=(HazardKind.FLOOD,), cues=(
                self.cue(hazard=HazardKind.LANDSLIDE),
            ))
        with self.assertRaisesRegex(ValidationError, "outside declared"):
            self.fixture(cues=(self.cue(category="automatically_safe"),))

    def test_no_empty_or_six_hazards(self):
        with self.assertRaises(ValidationError):
            self.fixture(hazards=())
        with self.assertRaises(ValidationError):
            self.fixture(hazards=tuple(HazardKind)+(HazardKind.FLOOD,))

    def test_future_evidence_and_broken_time_range_rejected(self):
        with self.assertRaisesRegex(ValidationError, "after simulated event"):
            self.fixture(cues=(self.cue(observed_at=EVENT_TIME+timedelta(minutes=1),
                                        expires_at=EVENT_TIME+timedelta(hours=2)),))
        with self.assertRaisesRegex(ValidationError, "expiry must follow"):
            self.cue(observed_at=EVENT_TIME, expires_at=EVENT_TIME)
        with self.assertRaises(ValidationError):
            SyntheticCue(
                hazard=HazardKind.FLOOD, category="hazard_area",
                availability=CueAvailability.SYNTHETIC_PRESENT,
            )
        with self.assertRaises(ValidationError):
            SyntheticCue(
                hazard=HazardKind.FLOOD, category="hazard_area",
                availability=CueAvailability.EXPLICITLY_MISSING, observed_at=EVENT_TIME,
            )

    def test_no_naive_time_or_fake_official_data(self):
        with self.assertRaises(ValidationError):
            MultiHazardFixture(
                fixture_id="a", region_code="13123",
                hazards=(HazardKind.FLOOD,),
                simulated_at=datetime(2026, 10, 23, 10),
            )
        payload = self.fixture().model_dump()
        payload["fixture_kind"] = "OFFICIAL"
        with self.assertRaises(ValidationError):
            MultiHazardFixture.model_validate(payload)
        with self.assertRaises(ValidationError):
            MultiHazardDrill.model_validate({
                "mode": "LIVE", "fixture": self.fixture().model_dump(),
            })

    def test_profile_region_consistency_is_preserved(self):
        with self.assertRaisesRegex(ValidationError, "cross-region"):
            self.review(profile=PreEventContext(region_code="15100", occupied_floor=2))
        review = self.review(profile=PreEventContext(region_code="15100"))
        self.assertEqual(review.region_code, "13123")

    def test_switch_hazard_clears_previous_evidence(self):
        a = start_multi_hazard_drill(
            PreEventContext(), self.fixture(cues=(self.cue(),))
        )
        b = replace_multi_hazard_fixture(
            a, self.fixture(hazards=(HazardKind.TSUNAMI,)),
        )
        self.assertEqual(b.fixture.cues, ())
        review = review_multi_hazard_drill(b)
        self.assertEqual(review.hazards, (HazardKind.TSUNAMI,))
        self.assertNotIn(HazardKind.FLOOD, review.hazards)
        self.assertTrue(all(x.status == "UNKNOWN" for x in review.cue_reviews))

    def test_switch_region_with_old_building_is_refused(self):
        original = start_multi_hazard_drill(
            PreEventContext(region_code="13123", occupied_floor=5),
            self.fixture(),
        )
        with self.assertRaisesRegex(ValidationError, "cross-region"):
            replace_multi_hazard_fixture(original, self.fixture(region="15100"))

    def test_stop_drill_drops_all_simulated_data(self):
        session = start_multi_hazard_drill(
            PreEventContext(region_code="13123", upper_floor_access=True),
            self.fixture(cues=(self.cue(),)),
        )
        normal = stop_multi_hazard_drill(session)
        self.assertEqual(normal.mode, SessionMode.NORMAL)
        self.assertIsNone(normal.drill)
        self.assertTrue(normal.prepared.upper_floor_access)

    def test_deterministic_order_for_same_hazard_set(self):
        forward = self.review(self.fixture())
        reversed_set = self.review(self.fixture(hazards=(
            HazardKind.LANDSLIDE, HazardKind.FLOOD,
        )))
        self.assertEqual(forward.model_dump(), reversed_set.model_dump())

    def test_public_review_never_contains_profile_floor_or_coordinates(self):
        review = self.review(profile=PreEventContext(
            region_code="13123", occupied_floor=149, upper_floor_access=True,
        ))
        payload = review.model_dump_json()
        self.assertNotIn('"occupied_floor":149', payload)
        self.assertNotIn('"latitude"', payload)
        self.assertIn('"official_event_verified":false', payload)
        self.assertNotIn('"CANDIDATE"', payload)
        self.assertIn('"UNKNOWN"', payload)


if __name__ == "__main__":
    unittest.main()
