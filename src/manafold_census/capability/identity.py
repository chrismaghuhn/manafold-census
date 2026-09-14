"""Deterministic M4 Capability family identity helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.identity import wire_digest_for
from ..semantic.model import RequirementV1
from .claim import CapabilityClaimV1
from .model import CapabilityFamilyKeyV1, CapabilityRefV1

FAMILY_ID_DOMAIN = "census.capability-family-id.v1"
FAMILY_ID_PREFIX = "capfam_"
CLAIM_DIGEST_DOMAIN = "census.capability-claim.v1"
ADMISSIBILITY_DOMAIN = "census.source-requirement-admissibility.v1"
ADMISSIBILITY_PREFIX = "sra_"
LINK_CLAIM_DOMAIN = "census.requirement-capability-link.v1"
LINK_ID_DOMAIN = "census.requirement-capability-link-id.v1"
LINK_ID_PREFIX = "rcl_"
REQUIREMENT_SET_DOMAIN = "census.m4-requirement-set.v1"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def requirement_set_digest_for(
    m3_manifest_sha256: str,
    requirements: Sequence[RequirementV1],
) -> str:
    """Digest one exact frozen M3 snapshot and its consumed Requirement wires."""

    if (
        not isinstance(m3_manifest_sha256, str)
        or _DIGEST_PATTERN.fullmatch(m3_manifest_sha256) is None
    ):
        raise ValueError("m3_manifest_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(requirements, Sequence) or isinstance(requirements, str | bytes):
        raise TypeError("requirements must be a sequence")
    entries: list[dict[str, JSONValue]] = []
    seen: dict[str, str] = {}
    for requirement in requirements:
        if not isinstance(requirement, RequirementV1):
            raise TypeError("requirements must contain RequirementV1 values")
        requirement_id = requirement.requirement_id
        requirement_wire_digest = wire_digest_for(requirement)
        previous = seen.get(requirement_id)
        if previous is not None:
            if previous != requirement_wire_digest:
                raise ValueError("duplicate Requirement ID has a different wire digest")
            raise ValueError("requirement set contains a duplicate Requirement ID")
        seen[requirement_id] = requirement_wire_digest
        entries.append(
            {
                "requirement_id": requirement_id,
                "requirement_wire_digest": requirement_wire_digest,
            }
        )
    entries.sort(key=lambda item: cast(str, item["requirement_id"]))
    return domain_digest(
        REQUIREMENT_SET_DOMAIN,
        cast(
            JSONValue,
            {
                "m3_analysis_manifest_sha256": m3_manifest_sha256,
                "requirements": entries,
            },
        ),
    )


__all__ = [
    "CLAIM_DIGEST_DOMAIN",
    "ADMISSIBILITY_DOMAIN",
    "ADMISSIBILITY_PREFIX",
    "FAMILY_ID_DOMAIN",
    "FAMILY_ID_PREFIX",
    "LINK_CLAIM_DOMAIN",
    "LINK_ID_DOMAIN",
    "LINK_ID_PREFIX",
    "REQUIREMENT_SET_DOMAIN",
    "capability_claim_digest_for",
    "capability_family_id_for",
    "capability_ref_for",
    "requirement_set_digest_for",
]
