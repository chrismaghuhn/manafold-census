"""Deterministic identities and digest projections for M2 Requirements."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from .evidence import (
    EvidenceV1,
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
    evidence_sort_key,
    evidence_to_wire,
)
from .kind_payloads import KindPayloadV1, payload_to_wire
from .kinds import RequirementFamilyV1, RequirementKindV1, validate_kind_family

if TYPE_CHECKING:
    from .model import RequirementV1

IDENTITY_DOMAIN = "census.semantic-requirement-id.v1"
WIRE_DOMAIN = "census.semantic-requirement-wire.v1"
REVIEW_DOMAIN = "census.semantic-requirement-review.v1"
REQUIREMENT_ID_PREFIX = "srq_"

_STRUCTURAL_EVIDENCE_TYPES = (
    StructuralRecordEvidenceV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
)


def _source_identity(source: SourceRecordRefV1) -> dict[str, JSONValue]:
    return {
        "record_schema": source.record_schema,
        "oracle_id": source.oracle_id,
        "source_card_id": source.source_card_id,
        "source_record_sha256": source.source_record_sha256,
    }


def _identity_payload_for_parts(
    source: SourceRecordRefV1,
    family: RequirementFamilyV1,
    kind: RequirementKindV1,
    parameters: KindPayloadV1,
) -> dict[str, JSONValue]:
    if not isinstance(source, SourceRecordRefV1):
        raise TypeError("source must be SourceRecordRefV1")
    validate_kind_family(family, kind)
    return {
        "identity_schema": IDENTITY_DOMAIN,
        "source_identity": _source_identity(source),
        "family": family.value,
        "kind": kind.value,
        "parameters": payload_to_wire(family, kind, parameters),
    }


def _requirement_id_for_parts(
    source: SourceRecordRefV1,
    family: RequirementFamilyV1,
    kind: RequirementKindV1,
    parameters: KindPayloadV1,
) -> str:
    return REQUIREMENT_ID_PREFIX + domain_digest(
        IDENTITY_DOMAIN,
        _identity_payload_for_parts(source, family, kind, parameters),
    )


def requirement_identity_payload(requirement: RequirementV1) -> dict[str, JSONValue]:
    """Return the exact producer-neutral identity projection."""

    return _identity_payload_for_parts(
        requirement.source,
        requirement.family,
        requirement.kind,
        requirement.parameters,
    )


def requirement_id_for(requirement: RequirementV1) -> str:
    """Compute the stable source-scoped Requirement identity."""

    return _requirement_id_for_parts(
        requirement.source,
        requirement.family,
        requirement.kind,
        requirement.parameters,
    )


def evidence_digest_for(evidence: EvidenceV1) -> str:
    """Return the existing canonical digest used to order one evidence item."""

    return evidence_sort_key(evidence)


def wire_digest_for(requirement: RequirementV1) -> str:
    """Digest the complete current Requirement wire representation."""

    return domain_digest(WIRE_DOMAIN, requirement.to_wire())


def _review_evidence_wire(evidence: EvidenceV1) -> dict[str, JSONValue]:
    wire = evidence_to_wire(evidence)
    if isinstance(evidence, _STRUCTURAL_EVIDENCE_TYPES):
        source = cast(dict[str, JSONValue], wire["source"])
        source = dict(source)
        source.pop("source_lock_digest", None)
        wire["source"] = source
    return wire


def reviewed_claim_payload_for(requirement: RequirementV1) -> dict[str, JSONValue]:
    """Return the canonical claim projection bound by terminal review."""

    evidence: list[JSONValue] = [
        _review_evidence_wire(item) for item in requirement.evidence
    ]
    evidence.sort(key=canonical_json_bytes)
    return {
        "source_identity": _source_identity(requirement.source),
        "family": requirement.family.value,
        "kind": requirement.kind.value,
        "parameters": payload_to_wire(
            requirement.family, requirement.kind, requirement.parameters
        ),
        "evidence": evidence,
        "provenance": requirement.provenance.to_wire(),
        "resolution": requirement.resolution.to_wire(),
    }


def reviewed_claim_digest_for(requirement: RequirementV1) -> str:
    """Digest the exact source/evidence/provenance/resolution review claim."""

    return domain_digest(REVIEW_DOMAIN, reviewed_claim_payload_for(requirement))


__all__ = [
    "IDENTITY_DOMAIN",
    "REQUIREMENT_ID_PREFIX",
    "REVIEW_DOMAIN",
    "WIRE_DOMAIN",
    "evidence_digest_for",
    "requirement_id_for",
    "requirement_identity_payload",
    "reviewed_claim_digest_for",
    "reviewed_claim_payload_for",
    "wire_digest_for",
]
