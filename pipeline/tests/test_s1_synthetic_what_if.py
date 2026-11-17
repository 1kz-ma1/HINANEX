"""S1-P3 what-if: exercise *real* S0→P0→P1→P2 on fictional records."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
)
from src.hinanex.s1_synthetic_narrowing import SyntheticReference
from src.hinanex.s1_synthetic_review_choice import ExplicitReviewChoice
from src.hinanex.s1_synthetic_what_if import (
    WhatIfRequest, WhatIfResult, compare_what_if, what_if_as_json,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
T5 = T0 + timedelta(minutes=5)
T30 = T0 + timedelta(minutes=30)


def session():
    fixture = SyntheticFixture("synthetic:whatif", "13123", "flood", T0, T30, SYNTHETIC_ONLY)
    return reduce_session(Session(), Event(
        Action.START_DRILL, 0, region_code="13123", fixture=fixture,
    ), T0)


def record(name="a", pet=True, step=True, **overrides):
    fields = dict(
        record_id=f"synthetic:{name}", fixture_id="synthetic:whatif",
        region_code="13123", hazard="flood", observed_at=T0,
        expires_at=T30, conditions=(("pet_support", pet), ("step_free", step)),
    )
    fields.update(overrides)
    return SyntheticReference(**fields)


ROWS = (
    record("a"),
    record("b", step=False),
    record("c", pet=False),
    record("d", pet=None),
    record("e", pet=False, step=None),
)
BEFORE = ("pet_support",)
AFTER = ("step_free",)


def ask(*, before=BEFORE, after=AFTER, generation=1, review=None,
        region="13123", hazard="flood"):
    return WhatIfRequest(generation, region, hazard, before, after, review)


def run(*, state=None, req=None, records=ROWS, at=T5):
    return compare_what_if(
        session() if state is None else state,
        ask() if req is None else req,
        records, at,
    )


class S1WhatIfTests(unittest.TestCase):
    def test_change_conditions_recomputes_exact_synthetic_differences(self):
        out = run()
        self.assertEqual(out.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(out.before_conditions, BEFORE)
        self.assertEqual(out.after_conditions, AFTER)
        self.assertEqual(out.newly_matching_synthetic_ids, ("synthetic:c", "synthetic:d"))
        self.assertEqual(out.no_longer_matching_synthetic_ids, ("synthetic:b",))
        self.assertEqual(out.unknown_after_synthetic_ids, ("synthetic:e",))
        self.assertEqual(
            [(r.before_status, r.after_status) for r in out.rows],
            [
                ("MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC"),
                ("MATCHED_SYNTHETIC", "NOT_MATCHED_SYNTHETIC"),
                ("NOT_MATCHED_SYNTHETIC", "MATCHED_SYNTHETIC"),
                ("UNKNOWN", "MATCHED_SYNTHETIC"),
                ("NOT_MATCHED_SYNTHETIC", "UNKNOWN"),
            ],
        )

    def test_unverified_attribute_stays_unknown_not_assumed_negative(self):
        out = run()
        row = out.rows[4]
        self.assertEqual(row.after_status, "UNKNOWN")
        self.assertEqual(row.after_missing, ("step_free",))
        self.assertEqual(row.after_failed, ())
        self.assertEqual(row.after_checks[0].assessment, "UNVERIFIED")

    def test_explanation_keeps_each_variant_condition_values(self):
        out = run()
        row = out.rows[1]
        self.assertEqual([(x.condition, x.assessment) for x in row.before_checks],
                         [("pet_support", "EXPLICIT_SYNTHETIC_TRUE")])
        self.assertEqual([(x.condition, x.assessment) for x in row.after_checks],
                         [("step_free", "EXPLICIT_SYNTHETIC_FALSE")])

    def test_tightening_constraints_removes_matches_without_ranking(self):
        out = run(req=ask(after=("pet_support", "step_free")))
        self.assertEqual(out.newly_matching_synthetic_ids, ())
        self.assertEqual(out.no_longer_matching_synthetic_ids, ("synthetic:b",))
        self.assertEqual(out.rows[1].after_failed, ("step_free",))
        self.assertFalse(out.facility_safety_verified)

    def test_same_conditions_have_no_diff_but_preserve_unknown(self):
        out = run(req=ask(after=BEFORE))
        self.assertEqual(out.newly_matching_synthetic_ids, ())
        self.assertEqual(out.no_longer_matching_synthetic_ids, ())
        self.assertEqual(out.unknown_after_synthetic_ids, ("synthetic:d",))
        self.assertEqual(
            [r.before_status for r in out.rows],
            [r.after_status for r in out.rows],
        )

    def test_optional_explicit_review_uses_current_after_variant(self):
        choice = ExplicitReviewChoice("synthetic:e", 1, True)
        out = run(req=ask(review=choice))
        self.assertIsNotNone(out.review)
        self.assertEqual(out.review.status, "REVIEW_SELECTED_SYNTHETIC_ONLY")
        self.assertEqual(out.review.selected_record_id, "synthetic:e")
        self.assertEqual(out.review.comparison_status, "UNKNOWN")
        self.assertEqual(out.review.missing, ("step_free",))
        self.assertIs(out.review.review_only, True)

    def test_absent_choice_never_selects_automatically(self):
        out = run()
        self.assertIsNone(out.review)

    def test_unconsented_choice_remains_blocked_not_promoted(self):
        out = run(req=ask(review=ExplicitReviewChoice("synthetic:a", 1, False)))
        self.assertEqual(out.review.status, "BLOCKED")
        self.assertEqual(out.review.reason_code, "EXPLICIT_USER_SELECTION_REQUIRED")
        self.assertIsNone(out.review.selected_record_id)

    def test_old_generation_review_is_rejected_with_current_comparison(self):
        out = run(req=ask(review=ExplicitReviewChoice("synthetic:a", 0, True)))
        self.assertEqual(out.status, "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(out.review.reason_code, "STALE_REVIEW_CHOICE")
        self.assertIsNone(out.review.selected_record_id)

    def test_unavailable_record_for_review_stays_blocked(self):
        out = run(req=ask(review=ExplicitReviewChoice("synthetic:missing", 1, True)))
        self.assertEqual(out.review.reason_code, "RECORD_NOT_IN_CURRENT_COMPARISON")
        self.assertIsNone(out.review.selected_record_id)

    def test_other_fixture_and_expired_synthetic_facts_never_newly_match(self):
        other = record("other", fixture_id="synthetic:else")
        stale = record("stale", expires_at=T5)
        out = run(records=ROWS + (other, stale))
        self.assertEqual(out.rows[-1].after_status, "UNKNOWN")
        self.assertEqual(out.rows[-2].after_status, "UNKNOWN")
        self.assertEqual(out.rows[-1].after_checks[0].assessment, "NOT_EVALUATED")
        self.assertEqual(out.rows[-2].after_checks[0].assessment, "NOT_EVALUATED")
        self.assertEqual(out.unknown_after_synthetic_ids[-2:],
                         ("synthetic:other", "synthetic:stale"))
        self.assertNotIn("synthetic:other", out.newly_matching_synthetic_ids)

    def test_stopped_drill_discards_all_rows_and_review(self):
        ended = reduce_session(session(), Event(Action.STOP_DRILL, 1), T5)
        out = run(state=ended, req=ask(generation=2, review=ExplicitReviewChoice("synthetic:a", 2, True)))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "ACTIVE_SYNTHETIC_DRILL_REQUIRED")
        self.assertEqual(out.rows, ())
        self.assertEqual(out.before_conditions, ())
        self.assertEqual(out.after_conditions, ())
        self.assertIsNone(out.review)
        self.assertEqual(out.newly_matching_synthetic_ids, ())

    def test_expiry_boundary_blocks_all_results_without_reducer_tick(self):
        out = run(at=T30, req=ask(review=ExplicitReviewChoice("synthetic:a", 1, True)))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.rows, ())
        self.assertIsNone(out.review)
        self.assertEqual(out.unknown_after_synthetic_ids, ())

    def test_region_change_invalidates_all_results(self):
        changed = reduce_session(session(), Event(Action.SELECT_REGION, 1, region_code="15100"), T5)
        out = run(state=changed, req=ask(generation=2))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.rows, ())

    def test_old_request_generation_blocks_all_variants(self):
        out = run(req=ask(generation=0))
        self.assertEqual(out.status, "BLOCKED")
        self.assertEqual(out.reason_code, "STALE_S0_GENERATION")
        self.assertEqual(out.rows, ())

    def test_wrong_request_region_and_hazard_block(self):
        for req in (ask(region="15100"), ask(hazard="landslide")):
            with self.subTest(req=req):
                out = run(req=req)
                self.assertEqual(out.status, "BLOCKED")
                self.assertEqual(out.reason_code, "S0_CONTEXT_MISMATCH")

    def test_no_explicit_constraints_or_unknown_fields_are_rejected(self):
        for before, after in (
            ((), AFTER), (BEFORE, ()), (BEFORE, ("population",)),
            (("pet_support", "pet_support"), AFTER),
        ):
            with self.subTest(before=before, after=after):
                with self.assertRaises(ValueError):
                    ask(before=before, after=after)

    def test_mutable_input_duplicate_records_and_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            run(records=ROWS + (ROWS[0],))
        with self.assertRaises(ValueError):
            run(records=list(ROWS))
        with self.assertRaises(ValueError):
            run(at=datetime(2026, 11, 13, 0, 5))

    def test_safe_flags_and_immutability(self):
        out = run()
        self.assertTrue(out.synthetic_only)
        self.assertTrue(all(x is False for x in (
            out.official_acceptance, out.live_data_verified,
            out.facility_safety_verified, out.route_safety_verified,
            out.release_approved,
        )))
        with self.assertRaises(FrozenInstanceError):
            out.rows[0].after_status = "SAFE"
        with self.assertRaisesRegex(ValueError, "real-world"):
            replace(out, official_acceptance=True)
        with self.assertRaisesRegex(ValueError, "blocked"):
            WhatIfResult("BLOCKED", "STALE", 2, rows=out.rows)

    def test_json_contains_fictional_data_and_no_real_shelter_fields(self):
        report = json.loads(what_if_as_json(run()))
        self.assertEqual(report["status"], "EVALUATED_SYNTHETIC_ONLY")
        self.assertEqual(report["rows"][0]["record_id"], "synthetic:a")
        self.assertFalse(report["release_approved"])
        text = json.dumps(report)
        for field in ("address", "latitude", "longitude", "safe_route", "official_name"):
            self.assertNotIn(field, text)

    def test_deterministic_and_input_unmodified(self):
        first = run()
        second = run()
        self.assertEqual(first, second)
        self.assertEqual(ROWS[1].conditions, (("pet_support", True), ("step_free", False)))


if __name__ == "__main__":
    unittest.main()
