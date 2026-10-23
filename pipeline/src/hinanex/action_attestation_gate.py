"""Offline *cryptographic* checks for untrusted evidence claims.

This verifier does not certify official source truth, human independence,
disaster safety, suitability or authorization for public release.
"""
from __future__ import annotations

import base64
import binascii
import json
from enum import Enum
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.hinanex.action_evidence_claims import SourceClaim

_DOMAIN = b"HINANEX/EVIDENCE-RECEIPT/ED25519/V1\0"
_ID = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"


def _b64(value: str, length: int) -> bytes:
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid base64") from exc
    if len(result) != length or base64.b64encode(result).decode("ascii") != value:
        raise ValueError("invalid base64 length or encoding")
    return result


class Role(str, Enum):
    PROVENANCE = "PROVENANCE"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"


class Verdict(str, Enum):
    PASS = "PASS"
    REJECTED = "REJECTED"
    NOT_REVIEWED = "NOT_REVIEWED"


class PinnedKey(BaseModel):
    """Loaded only by a trusted operator, NEVER from uploaded receipts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    key_id: str = Field(pattern=_ID)
    principal_id: str = Field(pattern=_ID)
    role: Role
    public_key_b64: str

    @model_validator(mode="after")
    def validate_key(self) -> "PinnedKey":
        Ed25519PublicKey.from_public_bytes(_b64(self.public_key_b64, 32))
        return self


class OperatorTrust(BaseModel):
    """Container shape; does NOT authenticate who supplied this registry."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    keys: tuple[PinnedKey, ...] = ()

    @model_validator(mode="after")
    def unique_signers(self) -> "OperatorTrust":
        if len({k.key_id for k in self.keys}) != len(self.keys):
            raise ValueError("duplicate key ID")
        ids: dict[str, Role] = {}
        for key in self.keys:
            other = ids.get(key.principal_id)
            if other is not None and other != key.role:
                raise ValueError("same principal cannot attest both roles")
            ids[key.principal_id] = key.role
        return self


class OperatorRevocations(BaseModel):
    """MUST come from authenticated operator storage, not attacker input."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    revoked_key_ids: tuple[str, ...] = ()
    revoked_receipt_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_window(self) -> "OperatorRevocations":
        if self.expires_at <= self.checked_at:
            raise ValueError("invalid revocation window")
        if len(set(self.revoked_key_ids)) != len(self.revoked_key_ids):
            raise ValueError("duplicate revoked key")
        if len(set(self.revoked_receipt_ids)) != len(self.revoked_receipt_ids):
            raise ValueError("duplicate revoked receipt")
        return self


class AttestedClaim(BaseModel):
    """Signed snapshot and scope, not evidence that the source is official."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal["RECEIPT_V1"] = "RECEIPT_V1"
    role: Role
    source_id: str
    source_url: str
    raw_sha256: str
    region_code: str
    hazard: str
    category: str
    coverage_kind: str
    coverage_ref: str
    observed_at: AwareDatetime
    retrieved_at: AwareDatetime
    asserted_valid_until: AwareDatetime | None
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    verdict: Verdict

    @model_validator(mode="after")
    def valid_range(self) -> "AttestedClaim":
        if self.expires_at <= self.issued_at:
            raise ValueError("receipt expiry must follow issuance")
        return self


class SignedReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    receipt_id: str = Field(pattern=_ID)
    key_id: str = Field(pattern=_ID)
    claim: AttestedClaim
    signature_b64: str

    def signed_bytes(self) -> bytes:
        """Receipt and key IDs are signed to prevent revocation bypass."""
        obj = {
            "receipt_id": self.receipt_id, "key_id": self.key_id,
            "claim": self.claim.model_dump(mode="json"),
        }
        return _DOMAIN + json.dumps(
            obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
        ).encode("utf-8")


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str
    status: Literal["BLOCKED", "SIGNATURES_VALID_ONLY"]
    reasons: tuple[str, ...]
    signatures_valid: bool
    official_source_authenticated: Literal[False] = False
    independent_human_review_proven: Literal[False] = False
    eligible_for_action_decision: Literal[False] = False
    published_for_disaster_use: Literal[False] = False


def _same_source(claim: AttestedClaim, source: SourceClaim) -> bool:
    return all((
        claim.source_id == source.source_id,
        claim.source_url == source.source_url,
        claim.raw_sha256 == source.raw_sha256,
        claim.region_code == source.region_code,
        claim.hazard == source.hazard.value,
        claim.category == source.category,
        claim.coverage_kind == source.coverage_kind.value,
        claim.coverage_ref == source.coverage_ref,
        claim.observed_at == source.observed_at,
        claim.retrieved_at == source.retrieved_at,
        claim.asserted_valid_until == source.asserted_valid_until,
    ))


def verify_attestations(
    source: SourceClaim,
    receipts: tuple[SignedReceipt, ...],
    *,
    trust: OperatorTrust,
    revocations: OperatorRevocations | None,
    as_of: AwareDatetime,
) -> GateResult:
    """Fail closed for signature/scope/time/revocation failure.

    Trust roots and revocations MUST be injected from a separately authenticated
    operator channel. Even fully valid signatures cannot approve disaster use.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    errors: list[str] = []
    registry = {key.key_id: key for key in trust.keys}
    if revocations is None:
        errors.append("REVOCATION_UNAVAILABLE")
    elif revocations.checked_at > as_of or revocations.expires_at <= as_of:
        errors.append("REVOCATION_STALE")
    if source.asserted_valid_until is None:
        errors.append("SOURCE_EXPIRY_UNKNOWN")
    elif source.asserted_valid_until <= as_of:
        errors.append("SOURCE_EXPIRED")
    if source.retrieved_at > as_of or source.observed_at > as_of:
        errors.append("SOURCE_FROM_FUTURE")
    seen_ids: set[str] = set()
    seen_roles: set[Role] = set()
    seen_people: set[str] = set()
    for receipt in receipts:
        if receipt.receipt_id in seen_ids:
            errors.append("DUPLICATE_RECEIPT")
        seen_ids.add(receipt.receipt_id)
        assertion = receipt.claim
        if assertion.role in seen_roles:
            errors.append("DUPLICATE_ROLE")
        seen_roles.add(assertion.role)
        if not _same_source(assertion, source):
            errors.append("SOURCE_SCOPE_MISMATCH")
        if assertion.issued_at > as_of or assertion.issued_at < source.retrieved_at:
            errors.append("INVALID_ISSUED_AT")
        if assertion.expires_at <= as_of:
            errors.append("RECEIPT_EXPIRED")
        if assertion.verdict is not Verdict.PASS:
            errors.append("REVIEW_NOT_PASS")
        if revocations and receipt.key_id in revocations.revoked_key_ids:
            errors.append("KEY_REVOKED")
        if revocations and receipt.receipt_id in revocations.revoked_receipt_ids:
            errors.append("RECEIPT_REVOKED")
        signer = registry.get(receipt.key_id)
        if signer is None:
            errors.append("UNPINNED_SIGNER")
            continue
        if signer.role is not assertion.role:
            errors.append("ROLE_MISMATCH")
        if signer.principal_id in seen_people:
            errors.append("NOT_INDEPENDENT_PRINCIPALS")
        seen_people.add(signer.principal_id)
        try:
            signature = _b64(receipt.signature_b64, 64)
            Ed25519PublicKey.from_public_bytes(_b64(signer.public_key_b64, 32)).verify(
                signature, receipt.signed_bytes()
            )
        except (ValueError, InvalidSignature):
            errors.append("INVALID_SIGNATURE")
    for role in Role:
        if role not in seen_roles:
            errors.append("MISSING_" + role.value)
    if errors:
        return GateResult(
            source_id=source.source_id, status="BLOCKED",
            signatures_valid=False, reasons=tuple(dict.fromkeys(errors)),
        )
    return GateResult(
        source_id=source.source_id, status="SIGNATURES_VALID_ONLY",
        signatures_valid=True, reasons=("NO_AUTHORITATIVE_SOURCE_APPROVAL",),
    )
