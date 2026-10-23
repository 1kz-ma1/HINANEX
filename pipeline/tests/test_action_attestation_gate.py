"""Offline ephemeral Ed25519 tests; no real person/official keys."""
import base64
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import ValidationError

from src.hinanex.action_context import HazardKind
from src.hinanex.action_evidence_claims import CoverageKind, SourceClaim
from src.hinanex.action_attestation_gate import (
    AttestedClaim, GateResult, OperatorRevocations, OperatorTrust, PinnedKey,
    Role, SignedReceipt, Verdict, verify_attestations,
)

NOW = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


def b64(value):
    return base64.b64encode(value).decode("ascii")


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceClaim(
            source_id="source1", provider_label="Synthetic test",
            source_url="https://example.org/d.json", raw_sha256="a"*64,
            region_code="13123", hazard=HazardKind.FLOOD,
            category="hazard_area", coverage_kind=CoverageKind.MUNICIPAL_REGION,
            coverage_ref="13123", observed_at=NOW-timedelta(hours=3),
            retrieved_at=NOW-timedelta(hours=2),
            asserted_valid_until=NOW+timedelta(hours=3),
        )
        self.private = [Ed25519PrivateKey.generate() for _ in Role]
        self.trust = OperatorTrust(keys=tuple(
            PinnedKey(key_id="k"+str(i), principal_id="p"+str(i), role=role,
                      public_key_b64=b64(key.public_key().public_bytes(
                          Encoding.Raw, PublicFormat.Raw)))
            for i, (key, role) in enumerate(zip(self.private, Role))
        ))
        self.revocations=OperatorRevocations(
            checked_at=NOW-timedelta(minutes=1),
            expires_at=NOW+timedelta(minutes=15),
        )

    def receipt(self, i, **updates):
        role=list(Role)[i]
        fields=dict(
            role=role, source_id=self.source.source_id,
            source_url=self.source.source_url, raw_sha256=self.source.raw_sha256,
            region_code=self.source.region_code, hazard=self.source.hazard.value,
            category=self.source.category,
            coverage_kind=self.source.coverage_kind.value,
            coverage_ref=self.source.coverage_ref,
            observed_at=self.source.observed_at, retrieved_at=self.source.retrieved_at,
            asserted_valid_until=self.source.asserted_valid_until,
            issued_at=NOW-timedelta(hours=1),
            expires_at=NOW+timedelta(hours=1), verdict=Verdict.PASS,
        )
        fields.update(updates)
        placeholder=SignedReceipt(
            receipt_id="r"+str(i), key_id="k"+str(i),
            claim=AttestedClaim(**fields), signature_b64=b64(b"0"*64),
        )
        return SignedReceipt(
            receipt_id=placeholder.receipt_id, key_id=placeholder.key_id,
            claim=placeholder.claim,
            signature_b64=b64(self.private[i].sign(placeholder.signed_bytes())),
        )

    def verify(self, receipts=None, **kwargs):
        return verify_attestations(
            kwargs.get("source", self.source),
            tuple(self.receipt(i) for i in range(2)) if receipts is None else tuple(receipts),
            trust=kwargs.get("trust", self.trust),
            revocations=kwargs.get("revocations", self.revocations),
            as_of=kwargs.get("as_of", NOW),
        )

    def must_block(self, reason, receipts=None, **kwargs):
        result=self.verify(receipts, **kwargs)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn(reason, result.reasons)
        self.assertFalse(result.eligible_for_action_decision)
        self.assertFalse(result.published_for_disaster_use)

    def test_matching_signatures_do_not_authorize_unsafe_action(self):
        r=self.verify()
        self.assertEqual(r.status, "SIGNATURES_VALID_ONLY")
        self.assertTrue(r.signatures_valid)
        self.assertFalse(r.independent_human_review_proven)
        self.assertFalse(r.official_source_authenticated)
        self.assertFalse(r.eligible_for_action_decision)
        self.assertFalse(r.published_for_disaster_use)

    def test_modifying_content_or_receipt_id_breaks_signature(self):
        r=self.receipt(0).model_dump()
        r["claim"]["hazard"]="landslide"
        self.must_block("INVALID_SIGNATURE", [SignedReceipt.model_validate(r),self.receipt(1)])
        r=self.receipt(0).model_dump()
        r["receipt_id"]="changed"
        self.must_block("INVALID_SIGNATURE", [SignedReceipt.model_validate(r),self.receipt(1)])

    def test_missing_role_duplicate_and_fake_key(self):
        self.must_block("MISSING_INDEPENDENT_REVIEW", [self.receipt(0)])
        self.must_block("DUPLICATE_ROLE", [self.receipt(0),self.receipt(0)])
        self.must_block("UNPINNED_SIGNER", trust=OperatorTrust())

    def test_key_revocation_and_receipt_revocation(self):
        self.must_block("KEY_REVOKED", revocations=OperatorRevocations(
            checked_at=NOW, expires_at=NOW+timedelta(minutes=5),
            revoked_key_ids=("k1",),
        ))
        self.must_block("RECEIPT_REVOKED", revocations=OperatorRevocations(
            checked_at=NOW, expires_at=NOW+timedelta(minutes=5),
            revoked_receipt_ids=("r0",),
        ))

    def test_absent_or_stale_revocations_fail_closed(self):
        self.must_block("REVOCATION_UNAVAILABLE", revocations=None)
        self.must_block("REVOCATION_STALE", revocations=OperatorRevocations(
            checked_at=NOW-timedelta(hours=1),expires_at=NOW,
        ))

    def test_mismatched_scope_digest_and_hazard(self):
        for f in (
            {"raw_sha256":"b"*64}, {"region_code":"15100"},
            {"hazard":"landslide"}, {"coverage_ref":"tile001"},
            {"source_url":"https://example.org/else"},
        ):
            with self.subTest(f=f):
                self.must_block("SOURCE_SCOPE_MISMATCH",
                                [self.receipt(0,**f),self.receipt(1)])

    def test_expired_receipt_and_source(self):
        self.must_block("RECEIPT_EXPIRED", [
            self.receipt(0,expires_at=NOW),self.receipt(1)])
        self.must_block("SOURCE_EXPIRED", as_of=NOW+timedelta(hours=4))

    def test_unapproved_and_issued_future(self):
        self.must_block("REVIEW_NOT_PASS", [
            self.receipt(0,verdict=Verdict.REJECTED),self.receipt(1)])
        self.must_block("INVALID_ISSUED_AT", [
            self.receipt(0,issued_at=NOW+timedelta(minutes=1),
                         expires_at=NOW+timedelta(hours=1)),
            self.receipt(1),
        ])

    def test_unique_operator_principals_and_bad_key(self):
        with self.assertRaisesRegex(ValidationError,"same principal"):
            OperatorTrust(keys=(
                self.trust.keys[0],
                self.trust.keys[1].model_copy(update={"principal_id":"p0"}),
            ))
        with self.assertRaises(ValidationError):
            PinnedKey(key_id="bad",principal_id="test",
                      role=Role.PROVENANCE,public_key_b64=b64(b"invalid"))

    def test_result_cannot_promote_to_disaster_use(self):
        v=self.verify().model_dump()
        v["eligible_for_action_decision"]=True
        with self.assertRaises(ValidationError):
            GateResult.model_validate(v)

    def test_naive_clock_and_stale_snapshot(self):
        with self.assertRaises(ValueError):
            self.verify(as_of=datetime(2026,10,23,10))
        self.must_block("REVOCATION_STALE", revocations=OperatorRevocations(
            checked_at=NOW+timedelta(minutes=1),
            expires_at=NOW+timedelta(minutes=2),
        ))


if __name__=="__main__":
    unittest.main()
