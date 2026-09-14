"""Deterministic M4 Capability family identity helpers."""

from __future__ import annotations

from ..digest import domain_digest
from .claim import CapabilityClaimV1
from .model import CapabilityFamilyKeyV1, CapabilityRefV1

FAMILY_ID_DOMAIN = "census.capability-family-id.v1"
FAMILY_ID_PREFIX = "capfam_"
CLAIM_DIGEST_DOMAIN = "census.capability-claim.v1"


def capability_family_id_for(key: CapabilityFamilyKeyV1) -> str:
    """Return the stable identity of one validated Capability nucleus."""

    if not isinstance(key, CapabilityFamilyKeyV1):
        raise TypeError("key must be CapabilityFamilyKeyV1")
    return FAMILY_ID_PREFIX + domain_digest(FAMILY_ID_DOMAIN, key.to_wire())


def capability_claim_digest_for(claim: CapabilityClaimV1) -> str:
    """Return the digest of one exact typed Capability claim."""

    if not isinstance(claim, CapabilityClaimV1):
        raise TypeError("claim must be CapabilityClaimV1")
    return domain_digest(CLAIM_DIGEST_DOMAIN, claim.to_wire())


def capability_ref_for(claim: CapabilityClaimV1) -> CapabilityRefV1:
    """Return the exact family/version/claim reference for one claim."""

    if not isinstance(claim, CapabilityClaimV1):
        raise TypeError("claim must be CapabilityClaimV1")
    return CapabilityRefV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
    )


__all__ = [
    "CLAIM_DIGEST_DOMAIN",
    "FAMILY_ID_DOMAIN",
    "FAMILY_ID_PREFIX",
    "capability_claim_digest_for",
    "capability_family_id_for",
    "capability_ref_for",
]
