"""Versioned M4 Capability definitions, provenance, and lifecycle gates."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, cast

from ..canonical import JSONValue
from ..semantic.identity import wire_digest_for
from ..semantic.primitives import (
    _require_enum,
    _require_int,
    _require_object,
    _require_text,
)
from .claim import CapabilityClaimV1
from .identity import (
    capability_claim_digest_for,
    capability_family_id_for,
    capability_ref_for,
)
from .model import CapabilityRefV1
from .review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityReviewRecordV1,
    ReviewDecisionV1,
)

if TYPE_CHECKING:
    from ..semantic.model import RequirementV1

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CAPABILITY_FAMILY_ID_PATTERN = re.compile(r"^capfam_[0-9a-f]{64}$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_CANDIDATE_ID_PATTERN = re.compile(r"^ccg_[0-9a-f]{64}$")
_REVIEW_ID_PATTERN = re.compile(r"^mrv_[0-9a-f]{64}$")

CAPABILITY_DEFINITION_SCHEMA = "census.capability-definition.v1"


class CapabilityLifecycleStateV1(StrEnum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _identifier_with_digest(field: str, value: object, pattern: re.Pattern[str]) -> str:
    text = _require_text(field, value)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} must use its closed digest identity form")
    return text


def _values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class CapabilityRequirementProvenanceV1:
    requirement_id: str
    requirement_wire_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "requirement_id",
        "requirement_wire_digest",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requirement_id",
            _identifier_with_digest(
                "requirement_id", self.requirement_id, _REQUIREMENT_ID_PATTERN
            ),
        )
        object.__setattr__(
            self,
            "requirement_wire_digest",
            _digest("requirement_wire_digest", self.requirement_wire_digest),
        )

    @classmethod
    def from_requirement(
        cls, requirement: RequirementV1
    ) -> CapabilityRequirementProvenanceV1:
        from ..semantic.model import RequirementV1 as RequirementModel

        if not isinstance(requirement, RequirementModel):
            raise TypeError("requirement must be RequirementV1")
        return cls(requirement.requirement_id, wire_digest_for(requirement))

    def validate_against_requirement(self, requirement: RequirementV1) -> None:
        expected = self.from_requirement(requirement)
        if self != expected:
            raise ValueError(
                "Requirement provenance wire digest does not match the exact "
                "Requirement wire"
            )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityRequirementProvenanceV1:
        document = _require_object(
            value,
            cls._WIRE_KEYS,
            "Capability Requirement provenance",
        )
        result = cls(
            cast(str, document["requirement_id"]),
            cast(str, document["requirement_wire_digest"]),
        )
        if result.to_wire() != document:
            raise ValueError("Capability Requirement provenance is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityProvenanceV1:
    m3_analysis_manifest_sha256: str
    candidate_cluster_ids: tuple[str, ...]
    requirement_refs: tuple[CapabilityRequirementProvenanceV1, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {
        "m3_analysis_manifest_sha256",
        "candidate_cluster_ids",
        "requirement_refs",
    }

    def __post_init__(self) -> None:
        manifest_sha256 = _digest(
            "m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256
        )
        candidates = tuple(
            _identifier_with_digest("candidate_cluster_id", item, _CANDIDATE_ID_PATTERN)
            for item in _values(self.candidate_cluster_ids, "candidate_cluster_ids")
        )
        if len(candidates) != len(set(candidates)):
            raise ValueError("duplicate candidate cluster")
        requirement_refs = _values(self.requirement_refs, "requirement_refs")
        if any(
            not isinstance(item, CapabilityRequirementProvenanceV1)
            for item in requirement_refs
        ):
            raise TypeError(
                "requirement_refs must contain CapabilityRequirementProvenanceV1 values"
            )
        typed_refs = cast(
            tuple[CapabilityRequirementProvenanceV1, ...], requirement_refs
        )
        requirement_ids = [item.requirement_id for item in typed_refs]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("duplicate Requirement provenance")
        if not candidates and not typed_refs:
            raise ValueError("provenance requires a non-empty combined basis")

        object.__setattr__(self, "m3_analysis_manifest_sha256", manifest_sha256)
        object.__setattr__(self, "candidate_cluster_ids", tuple(sorted(candidates)))
        object.__setattr__(
            self,
            "requirement_refs",
            tuple(sorted(typed_refs, key=lambda item: item.requirement_id)),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "candidate_cluster_ids": list(self.candidate_cluster_ids),
            "requirement_refs": [item.to_wire() for item in self.requirement_refs],
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityProvenanceV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability provenance")
        raw_candidates = document["candidate_cluster_ids"]
        raw_requirements = document["requirement_refs"]
        if not isinstance(raw_candidates, list):
            raise TypeError("candidate_cluster_ids must be a JSON array")
        if not isinstance(raw_requirements, list):
            raise TypeError("requirement_refs must be a JSON array")
        result = cls(
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            candidate_cluster_ids=tuple(cast(str, item) for item in raw_candidates),
            requirement_refs=tuple(
                CapabilityRequirementProvenanceV1.from_wire(item)
                for item in raw_requirements
            ),
        )
        if result.to_wire() != document:
            raise ValueError("Capability provenance is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityDefinitionV1:
    capability_family_id: str
    capability_version: int
    claim_digest: str
    claim: CapabilityClaimV1
    display_name: str
    lifecycle: CapabilityLifecycleStateV1
    provenance: CapabilityProvenanceV1
    review_ref: str | None

    SCHEMA: ClassVar[str] = CAPABILITY_DEFINITION_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "capability_family_id",
        "capability_version",
        "claim_digest",
        "claim",
        "display_name",
        "lifecycle",
        "provenance",
        "review_ref",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.claim, CapabilityClaimV1):
            raise TypeError("claim must be CapabilityClaimV1")
        expected_family_id = capability_family_id_for(self.claim.family_key)
        expected_claim_digest = capability_claim_digest_for(self.claim)
        family_id = _identifier_with_digest(
            "capability_family_id",
            self.capability_family_id,
            _CAPABILITY_FAMILY_ID_PATTERN,
        )
        if family_id != expected_family_id:
            raise ValueError("capability_family_id does not match claim family key")
        version = _require_int("capability_version", self.capability_version)
        if version < 1:
            raise ValueError("capability_version must be at least one")
        if version != self.claim.capability_version:
            raise ValueError("capability_version does not match claim")
        claim_digest = _digest("claim_digest", self.claim_digest)
        if claim_digest != expected_claim_digest:
            raise ValueError("claim_digest does not match claim")
        display_name = _require_text("display_name", self.display_name)
        if not display_name.strip():
            raise ValueError("display_name must contain non-whitespace text")
        lifecycle = _require_enum(
            "lifecycle", self.lifecycle, CapabilityLifecycleStateV1
        )
        if not isinstance(self.provenance, CapabilityProvenanceV1):
            raise TypeError("provenance must be CapabilityProvenanceV1")
        review_ref = self.review_ref
        if review_ref is not None:
            review_ref = _identifier_with_digest(
                "review_ref", review_ref, _REVIEW_ID_PATTERN
            )

        object.__setattr__(self, "capability_family_id", family_id)
        object.__setattr__(self, "capability_version", version)
        object.__setattr__(self, "claim_digest", claim_digest)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "lifecycle", lifecycle)
        object.__setattr__(self, "review_ref", review_ref)

    @property
    def capability_ref(self) -> CapabilityRefV1:
        return capability_ref_for(self.claim)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "capability_family_id": self.capability_family_id,
            "capability_version": self.capability_version,
            "claim_digest": self.claim_digest,
            "claim": self.claim.to_wire(),
            "display_name": self.display_name,
            "lifecycle": self.lifecycle.value,
            "provenance": self.provenance.to_wire(),
            "review_ref": self.review_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityDefinitionV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability definition")
        schema = _require_text("schema", document["schema"])
        if schema != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        result = cls(
            capability_family_id=cast(str, document["capability_family_id"]),
            capability_version=cast(int, document["capability_version"]),
            claim_digest=cast(str, document["claim_digest"]),
            claim=CapabilityClaimV1.from_wire(document["claim"]),
            display_name=cast(str, document["display_name"]),
            lifecycle=_require_enum(
                "lifecycle", document["lifecycle"], CapabilityLifecycleStateV1
            ),
            provenance=CapabilityProvenanceV1.from_wire(document["provenance"]),
            review_ref=cast(str | None, document["review_ref"]),
        )
        if result.to_wire() != document:
            raise ValueError("Capability definition wire is not canonical")
        return result


def validate_provenance_against_m3(
    provenance: CapabilityProvenanceV1,
    selected_m3_manifest_sha256: str,
    selected_requirements: Sequence[RequirementV1],
) -> None:
    """Bind typed provenance references to one selected M3 Requirement set."""

    from ..semantic.model import RequirementV1 as RequirementModel

    if not isinstance(provenance, CapabilityProvenanceV1):
        raise TypeError("provenance must be CapabilityProvenanceV1")
    selected_manifest = _digest(
        "selected_m3_manifest_sha256", selected_m3_manifest_sha256
    )
    if provenance.m3_analysis_manifest_sha256 != selected_manifest:
        raise ValueError(
            "Capability provenance does not match the selected M3 manifest"
        )

    requirements = tuple(selected_requirements)
    if any(not isinstance(item, RequirementModel) for item in requirements):
        raise TypeError("selected_requirements must contain RequirementV1 values")
    by_id: dict[str, RequirementV1] = {}
    for requirement in requirements:
        if requirement.requirement_id in by_id:
            raise ValueError("duplicate selected Requirement identity")
        by_id[requirement.requirement_id] = requirement

    for reference in provenance.requirement_refs:
        matched_requirement = by_id.get(reference.requirement_id)
        if matched_requirement is None:
            raise ValueError(
                "Capability provenance Requirement is not present in the selected M3 "
                "set"
            )
        reference.validate_against_requirement(matched_requirement)


def can_receive_active_link(definition: CapabilityDefinitionV1) -> bool:
    if not isinstance(definition, CapabilityDefinitionV1):
        raise TypeError("definition must be CapabilityDefinitionV1")
    return definition.lifecycle is CapabilityLifecycleStateV1.ACTIVE


def validate_active_definition(
    definition: CapabilityDefinitionV1,
    reviews: Sequence[CapabilityReviewRecordV1],
    selected_m3_manifest_sha256: str | None = None,
    selected_requirements: Sequence[RequirementV1] | None = None,
) -> None:
    if not isinstance(definition, CapabilityDefinitionV1):
        raise TypeError("definition must be CapabilityDefinitionV1")
    if definition.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
        raise ValueError(
            "active definition requires accepted review and ACTIVE lifecycle"
        )

    if (
        capability_family_id_for(definition.claim.family_key)
        != definition.capability_family_id
    ):
        raise ValueError("active definition has a stale capability_family_id")
    if capability_claim_digest_for(definition.claim) != definition.claim_digest:
        raise ValueError("active definition has a stale claim_digest")
    CapabilityProvenanceV1.from_wire(definition.provenance.to_wire())

    if definition.review_ref is None:
        raise ValueError("active definition requires accepted review")
    records = tuple(reviews)
    if any(not isinstance(record, CapabilityReviewRecordV1) for record in records):
        raise TypeError("reviews must contain CapabilityReviewRecordV1 values")
    subject = CapabilityDefinitionReviewSubjectV1(
        capability_family_id=definition.capability_family_id,
        capability_version=definition.capability_version,
        claim_digest=definition.claim_digest,
    )
    matching = tuple(record for record in records if record.subject == subject)
    if any(record.decision is ReviewDecisionV1.ACCEPTED for record in matching) and any(
        record.decision is ReviewDecisionV1.REJECTED for record in matching
    ):
        raise ValueError(
            "conflicting accepted and rejected reviews; active definition requires "
            "accepted review"
        )

    referenced = tuple(
        record for record in records if record.record_id == definition.review_ref
    )
    if len(referenced) != 1:
        raise ValueError("active definition requires accepted review")
    review = referenced[0]
    if review.subject != subject:
        raise ValueError("review must bind the exact Capability definition")
    if review.decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError("active definition requires accepted review")
    if review.generalization_basis is None:
        raise ValueError("active definition requires generalization_basis")
    if selected_m3_manifest_sha256 is None or selected_requirements is None:
        raise ValueError("active definition requires selected M3 input")
    validate_provenance_against_m3(
        definition.provenance,
        selected_m3_manifest_sha256,
        selected_requirements,
    )


__all__ = [
    "CAPABILITY_DEFINITION_SCHEMA",
    "CapabilityDefinitionV1",
    "CapabilityLifecycleStateV1",
    "CapabilityProvenanceV1",
    "CapabilityRequirementProvenanceV1",
    "can_receive_active_link",
    "validate_provenance_against_m3",
    "validate_active_definition",
]
