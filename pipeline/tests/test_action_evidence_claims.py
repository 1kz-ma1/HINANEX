"""Synthetic-only safeguards for source metadata and unauthenticated review."""
import unittest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from src.hinanex.action_context import HazardKind, PreEventContext
from src.hinanex.action_context_multi import (
    CueAvailability, MultiHazardFixture, SyntheticCue, start_multi_hazard_drill,
)
from src.hinanex.action_evidence_claims import (
    CoverageKind, EvidenceClaimBundle, EvidenceBundleReview, ReportedOutcome,
    ReviewClaim, SourceClaim, review_evidence_claims,
)

T = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
SHA = "a" * 64


class SourceClaimsTest(unittest.TestCase):
    def source(self, **kwargs):
        values = dict(
            source_id="s1", provider_label="Synthetic example provider",
            source_url="https://example.org/source.json", raw_sha256=SHA,
            region_code="13123", hazard=HazardKind.FLOOD, category="hazard_area",
            coverage_kind=CoverageKind.MUNICIPAL_REGION, coverage_ref="13123",
            observed_at=T-timedelta(hours=3), retrieved_at=T-timedelta(hours=2),
            asserted_valid_until=T+timedelta(hours=1),
        )
        values.update(kwargs)
        return SourceClaim(**values)

    def report(self, **kwargs):
        values = dict(
            report_id="r1", reviewer_ref="unverified-reviewer",
            source_id="s1", raw_sha256=SHA, region_code="13123",
            hazard=HazardKind.FLOOD, category="hazard_area",
            coverage_kind=CoverageKind.MUNICIPAL_REGION, coverage_ref="13123",
            reviewed_at=T-timedelta(hours=1),
            reported_outcome=ReportedOutcome.PASS_REPORTED,
        )
        values.update(kwargs)
        return ReviewClaim(**values)

    def session(self, cue=True, hazards=(HazardKind.FLOOD,)):
        return start_multi_hazard_drill(
            PreEventContext(),
            MultiHazardFixture(
                fixture_id="exercise_1", region_code="13123", hazards=hazards,
                simulated_at=T,
                cues=((SyntheticCue(
                    hazard=HazardKind.FLOOD, category="hazard_area",
                    availability=CueAvailability.SYNTHETIC_PRESENT,
                    observed_at=T-timedelta(hours=4),
                    expires_at=T+timedelta(hours=2),
                ),) if cue else ()),
            ),
        )

    def result(self, sources=None, reports=None, session=None):
        bundle=EvidenceClaimBundle(
            sources=tuple([self.source()] if sources is None else sources),
            reports=tuple([self.report()] if reports is None else reports),
        )
        return review_evidence_claims(session or self.session(), bundle)

    def reasons(self, **kwargs):
        return self.result(**kwargs).links[0].reason_codes

    def test_even_matching_pass_is_untrusted(self):
        out=self.result()
        self.assertIn("REPORTED_PASS_UNAUTHENTICATED",out.links[0].reason_codes)
        self.assertIn("AUTHORITATIVE_ACCEPTANCE_NOT_ESTABLISHED",out.links[0].reason_codes)
        self.assertFalse(out.links[0].review_authenticated)
        self.assertFalse(out.links[0].eligible_for_action_decision)
        self.assertFalse(out.independent_review_authenticated)
        self.assertFalse(out.published_for_disaster_use)
        self.assertTrue(all(item.status=="UNKNOWN" for sub in out.actions.action_reviews for item in sub.options))

    def test_missing_rejected_and_unreviewed_are_distinct(self):
        self.assertIn("NO_INDEPENDENT_REVIEW_REPORT",self.reasons(reports=[]))
        self.assertIn("REPORTED_REJECTION",self.reasons(reports=[
            self.report(reported_outcome=ReportedOutcome.REJECTED_REPORTED)]))
        self.assertIn("NOT_REVIEWED",self.reasons(reports=[
            self.report(reported_outcome=ReportedOutcome.NOT_REVIEWED)]))

    def test_hash_region_and_hazard_mismatch(self):
        self.assertIn("REVIEW_IDENTITY_MISMATCH",self.reasons(reports=[
            self.report(raw_sha256="b"*64)]))
        self.assertIn("REGION_MISMATCH",self.reasons(sources=[
            self.source(region_code="15100",coverage_ref="15100")]))
        self.assertIn("HAZARD_MISMATCH",self.reasons(sources=[
            self.source(hazard=HazardKind.LANDSLIDE)]))

    def test_tile_is_not_municipal_coverage(self):
        reasons=self.reasons(sources=[self.source(
            coverage_kind=CoverageKind.GSI_TILE,coverage_ref="10/908/402")])
        self.assertIn("TILE_COVERAGE_NOT_VERIFIED_AT_LOCATION",reasons)
        self.assertIn("REVIEW_IDENTITY_MISMATCH",reasons)

    def test_expired_missing_expiry_and_future(self):
        self.assertIn("SOURCE_CLAIM_EXPIRED",self.reasons(sources=[
            self.source(asserted_valid_until=T-timedelta(minutes=1))]))
        self.assertIn("SOURCE_VALIDITY_UNASSERTED",self.reasons(sources=[
            self.source(asserted_valid_until=None)]))
        self.assertIn("SOURCE_FROM_FUTURE",self.reasons(sources=[
            self.source(observed_at=T+timedelta(minutes=1),
                        retrieved_at=T+timedelta(minutes=2))]))
        self.assertIn("REVIEW_FROM_FUTURE",self.reasons(reports=[
            self.report(reviewed_at=T+timedelta(minutes=1))]))

    def test_missing_drill_cue_blocks_claim(self):
        self.assertIn("NO_MATCHING_DRILL_CUE",self.reasons(session=self.session(cue=False)))

    def test_wrong_category_is_not_accepted(self):
        self.assertIn("CATEGORY_MISMATCH",self.reasons(sources=[
            self.source(category="nonexistent_category")]))

    def test_invalid_source_shape_and_semantics(self):
        with self.assertRaisesRegex(ValidationError,"municipal coverage"):
            self.source(coverage_ref="99999")
        with self.assertRaises(ValidationError):
            self.source(raw_sha256="fake")
        with self.assertRaises(ValidationError):
            self.source(retrieved_at=T-timedelta(hours=5))
        with self.assertRaises(ValidationError):
            self.source(asserted_valid_until=T-timedelta(hours=4))

    def test_duplicate_sources_reports_and_dangling(self):
        with self.assertRaisesRegex(ValidationError,"duplicate source"):
            EvidenceClaimBundle(sources=(self.source(),self.source()))
        with self.assertRaisesRegex(ValidationError,"multiple reports"):
            EvidenceClaimBundle(sources=(self.source(),),reports=(
                self.report(),self.report(report_id="r2")))
        with self.assertRaisesRegex(ValidationError,"unattached"):
            EvidenceClaimBundle(reports=(self.report(),))

    def test_fake_official_or_live_state_rejected(self):
        data=self.source().model_dump()
        data["claim_kind"]="OFFICIAL_APPROVED"
        with self.assertRaises(ValidationError):
            SourceClaim.model_validate(data)
        claim=self.report().model_dump()
        claim["reported_outcome"]="VERIFIED"
        with self.assertRaises(ValidationError):
            ReviewClaim.model_validate(claim)
        out=self.result().model_dump()
        out["published_for_disaster_use"]=True
        with self.assertRaises(ValidationError):
            EvidenceBundleReview.model_validate(out)

    def test_insecure_urls_and_credentials(self):
        for url in ("http://example.org", "https://u:p@example.org/",
                    "https://example.org/#fragment","https://example.org:80/",
                    "https://example.org/a b"):
            with self.subTest(url=url),self.assertRaises(ValidationError):
                self.source(source_url=url)

    def test_empty_sources_never_imply_no_hazards(self):
        out=self.result(sources=[],reports=[])
        self.assertEqual(out.links,())
        self.assertFalse(out.published_for_disaster_use)
        self.assertTrue(all(item.status=="UNKNOWN" for sub in out.actions.action_reviews for item in sub.options))

    def test_consistent_order_and_no_profile_floor_leak(self):
        session=start_multi_hazard_drill(
            PreEventContext(region_code="13123",occupied_floor=137),
            self.session().fixture,
        )
        sources=[self.source(),self.source(source_id="s2",category="available_time")]
        reports=[self.report(),self.report(report_id="r2",source_id="s2",
                                           category="available_time")]
        a=self.result(sources=sources,reports=reports,session=session)
        b=self.result(sources=list(reversed(sources)),reports=list(reversed(reports)),session=session)
        self.assertEqual(a.model_dump(),b.model_dump())
        self.assertNotIn('"occupied_floor":137',a.model_dump_json())


if __name__=="__main__":
    unittest.main()
