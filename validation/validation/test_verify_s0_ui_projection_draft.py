"""C regression for review-only S0 UI projection. No B adapter or release approval."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import verify_s0_ui_projection_draft as c
from src.hinanex.drill_session import (
    Action, Event, Session, SyntheticFixture, SYNTHETIC_ONLY, reduce_session,
    DRILL_NOTICE, NORMAL_NOTICE,
)

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)


def active():
    fixture = SyntheticFixture(
        fixture_id="synthetic:ui-review", region_code="13123", hazard="flood",
        observed_at=T0, expires_at=T0+timedelta(minutes=30),
        source_authorization=SYNTHETIC_ONLY,
    )
    return reduce_session(Session(), Event(
        action=Action.START_DRILL, expected_generation=0,
        region_code="13123", fixture=fixture,
    ), T0)


class S0UiDraftPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(c.MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_proposal_schema_is_exactly_scoped_and_marked_not_adopted(self):
        schema = c.load_proposal_schema()
        self.assertEqual(set(schema["required"]), c.FIELDS)
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("NOT ADOPTED", schema["title"])
        props = schema["properties"]
        self.assertIs(props["review_only"]["const"], True)
        self.assertIs(props["live_data_verified"]["const"], False)
        self.assertEqual(schema["allOf"][0]["then"]["properties"]["notice"]["const"], NORMAL_NOTICE)
        self.assertEqual(schema["allOf"][1]["then"]["properties"]["notice"]["const"], DRILL_NOTICE)

    def test_all_24_synthetic_cases_match_expected(self):
        rows = c.check_manifest(self.manifest)
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(r["matches_expected"] for r in rows))
        self.assertEqual({r["actual"]["status"] for r in rows}, set(c.STATES))
        self.assertEqual(len(rows), len({r["id"] for r in rows}))

    def test_real_s0_drill_is_not_live_and_has_bounded_window(self):
        state = active()
        p = c.project_for_review(state, T0)
        self.assertEqual(p["mode"], "DRILL")
        self.assertEqual(p["notice"], DRILL_NOTICE)
        self.assertEqual(p["source_authorization"], SYNTHETIC_ONLY)
        self.assertFalse(p["live_data_verified"])
        self.assertEqual(p["observed_at"], T0.isoformat())
        self.assertEqual(p["expires_at"], (T0+timedelta(minutes=30)).isoformat())
        self.assertEqual(c.inspect(p, state, render_at=T0, active_generation=1)["status"], "PASS")

    def test_expiration_at_exact_boundary_fails_without_an_s0_tick(self):
        state = active()
        p = c.project_for_review(state, T0)
        self.assertEqual(c.inspect(p, state, render_at=T0+timedelta(minutes=30),
                                   active_generation=1),
                         c.decision("FAIL", "EXPIRED_DRILL"))
        self.assertEqual(c.project_for_review(state, T0+timedelta(minutes=30))["mode"], "NORMAL")
        self.assertIsNone(c.project_for_review(state, T0+timedelta(minutes=30))["fixture_id"])

    def test_normal_never_claims_live_or_exposes_preferred_region(self):
        state=reduce_session(Session(), Event(action=Action.SET_PREFERRED_REGION,
            expected_generation=0, region_code="13123", explicit_consent=True), T0)
        p = c.project_for_review(state, T0)
        self.assertEqual(p["mode"], "NORMAL")
        self.assertEqual(p["notice"], NORMAL_NOTICE)
        self.assertIsNone(p["fixture_id"])
        self.assertIsNone(p["observed_at"])
        self.assertNotIn("preferred_region", p)
        self.assertFalse({"facility_open", "facility_safety", "route_passability", "latitude", "longitude"} & set(p))
        self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=1)["status"], "PASS")

    def test_live_forgery_fails_closed(self):
        state=active()
        p=c.project_for_review(state,T0)
        p["live_data_verified"]=True
        self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=1),
                         c.decision("FAIL","FALSE_LIVE_ASSERTION"))

    def test_notice_source_and_hazard_tampering_fail(self):
        state=active()
        for key,value,code in (
            ("notice","現在の避難所は安全です","DRILL_NOTICE_MISMATCH"),
            ("source_authorization","OFFICIAL","NON_SYNTHETIC_SOURCE"),
            ("hazard","landslide","S0_VIEW_PROVENANCE_MISMATCH"),
        ):
            with self.subTest(key=key):
                p=c.project_for_review(state,T0)
                p[key]=value
                self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=1)["code"],code)

    def test_unknown_claim_and_missing_field_are_distinct(self):
        state=active()
        extra=c.project_for_review(state,T0)
        extra["facility_open"]=True
        self.assertEqual(c.inspect(extra,state,render_at=T0,active_generation=1),
                         c.decision("FAIL","UNREVIEWED_DISPLAY_FIELD"))
        missing=c.project_for_review(state,T0)
        missing.pop("notice")
        self.assertEqual(c.inspect(missing,state,render_at=T0,active_generation=1),
                         c.decision("BLOCKED","MISSING_DISPLAY_FIELD"))

    def test_generation_mismatch_fails_even_with_matching_fixture(self):
        state=active()
        p=c.project_for_review(state,T0)
        self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=0),
                         c.decision("FAIL","STALE_CONTEXT_GENERATION"))
        p["generation"]=0
        self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=0),
                         c.decision("FAIL","STALE_CONTEXT_GENERATION"))

    def test_full_replay_uses_real_s0_for_region_changes_and_errors(self):
        rows={r["id"]:r for r in c.check_manifest(self.manifest)}
        for key in ("region_change_clears_fixture","source_failure_clears_fixture","stop_clears_fixture",
                    "future_fixture_start_denied","mismatched_fixture_start_denied"):
            self.assertEqual(rows[key]["actual"],c.decision("PASS","CONSISTENT_REVIEW_PROJECTION"))
        self.assertEqual(rows["stale_generation_after_region_change"]["actual"]["code"],
                         "STALE_CONTEXT_GENERATION")

    def test_timestamp_must_have_timezone_and_issued_not_future(self):
        state=active()
        p=c.project_for_review(state,T0)
        p["expires_at"]="2026-11-13T00:30:00"
        self.assertEqual(c.inspect(p,state,render_at=T0,active_generation=1)["code"],"INVALID_TIMESTAMP")
        p=c.project_for_review(state,T0)
        self.assertEqual(c.inspect(p,state,render_at=T0-timedelta(seconds=1),
                                   active_generation=1)["code"],"FUTURE_ISSUE")

    def test_wrong_expectation_must_fail_cli_regression(self):
        bad=copy.deepcopy(self.manifest)
        bad["cases"][0]["expected"]={"status":"PASS","code":"SILENTLY_APPROVED"}
        self.assertFalse(all(r["matches_expected"] for r in c.check_manifest(bad)))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"altered.json"
            path.write_text(json.dumps(bad),encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(c.main(["--manifest",str(path)]),1)

    def test_non_synthetic_or_duplicate_cases_are_rejected(self):
        bad=copy.deepcopy(self.manifest)
        bad["synthetic_only"]=False
        with self.assertRaises(ValueError):
            c.check_manifest(bad)
        bad=copy.deepcopy(self.manifest)
        bad["cases"].append(copy.deepcopy(bad["cases"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            c.check_manifest(bad)

    def test_output_never_promotes_proposal_to_release_or_device_pass(self):
        s=StringIO()
        with redirect_stdout(s):
            self.assertEqual(c.main(["--json"]),0)
        result=json.loads(s.getvalue())
        self.assertEqual(result["regression"],"PASS")
        self.assertIs(result["contract_adopted"],False)
        self.assertIs(result["public_release_approved"],False)
        self.assertIs(result["official_acceptance"],False)
        self.assertEqual(result["device_qa"],"NOT_RUN")
        self.assertGreater(result["counts"]["FAIL"],0)
        self.assertGreater(result["counts"]["BLOCKED"],0)
        self.assertGreater(result["counts"]["NOT_RUN"],0)


if __name__=="__main__":
    unittest.main()
