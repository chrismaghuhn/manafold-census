"""M4 link validation, cardinality, and preserved mapping decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from ..semantic.identity import reviewed_claim_digest_for, wire_digest_for
from ..semantic.model import RequirementV1, ResolutionStateV1, ReviewStatusV1
from ..semantic.primitives import _require_enum, _require_object
from .admissibility import SourceRequirementAdmissibilityV1
from .binding import BindingStateV1, validate_binding_against_requirement
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .link import (
    _LINK_ID_PATTERN,
    _REQUIREMENT_ID_PATTERN,
    _REVIEW_ID_PATTERN,
    CompositionContextV1,
    LinkAdmissibilityBasisV1,
    LinkRelationV1,
    M4RequirementAdmissibilityV1,
    RequirementCapabilityLinkV1,
    _digest,
    _identifier,
    _values,
)
from .model import NucleusKindV1
from .review import (
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    MappingDecisionReviewSubjectV1,
    ReviewDecisionV1,
)

MAPPING_DECISION_SCHEMA = "census.requirement-mapping-decision.v1"
MAPPING_DECISION_DOMAIN = "census.requirement-mapping-decision.v1"
MAPPING_DECISION_PREFIX = "rmd_"


class MappingDispositionV1(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    OUTLIER = "OUTLIER"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class MappingReasonV1(StrEnum):
    NO_REVIEWED_CAPABILITY = "NO_REVIEWED_CAPABILITY"
    M2_REVIEW_NOT_TERMINAL = "M2_REVIEW_NOT_TERMINAL"
    M4_ADMISSIBILITY_REVIEW_PENDING = "M4_ADMISSIBILITY_REVIEW_PENDING"
    M2_RESOLUTION_INCOMPLETE = "M2_RESOLUTION_INCOMPLETE"
    MULTIPLE_PLAUSIBLE_CAPABILITIES = "MULTIPLE_PLAUSIBLE_CAPABILITIES"
    NO_REUSABLE_GENERALIZATION = "NO_REUSABLE_GENERALIZATION"
    SPECIAL_CASE = "SPECIAL_CASE"
    EXPLICIT_REVIEW_CONFLICT = "EXPLICIT_REVIEW_CONFLICT"


def _requirement(value: object) -> RequirementV1:
    if not isinstance(value, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    return value


def _require_capability(value: object) -> CapabilityDefinitionV1:
    if not isinstance(value, CapabilityDefinitionV1):
        raise TypeError("capability must be CapabilityDefinitionV1")
    return value


def _validate_link_review(
    link: RequirementCapabilityLinkV1,
    reviews: Sequence[CapabilityReviewRecordV1],
) -> None:
    if link.review_ref is None:
        raise ValueError("active link requires accepted review")
    records = tuple(reviews)
    if any(not isinstance(record, CapabilityReviewRecordV1) for record in records):
        raise TypeError("reviews must contain CapabilityReviewRecordV1 values")
    subject = CapabilityLinkReviewSubjectV1(link.link_id, link.link_claim_digest)
    matching = tuple(record for record in records if record.subject == subject)
    if any(record.decision is ReviewDecisionV1.ACCEPTED for record in matching) and any(
        record.decision is ReviewDecisionV1.REJECTED for record in matching
    ):
        raise ValueError("conflicting accepted and rejected link reviews")
    referenced = tuple(
        record for record in matching if record.record_id == link.review_ref
    )
    if len(referenced) != 1 or referenced[0].decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError("active link requires an exact accepted review")


def _validate_active_bindings(
    link: RequirementCapabilityLinkV1,
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
) -> None:
    declared = {dimension.path_key for dimension in capability.claim.dimensions}
    bound = {binding.path_key for binding in link.parameter_bindings}
    if not bound.issubset(declared):
        raise ValueError("link binding is not declared by the Capability claim")
    for binding in link.parameter_bindings:
        validate_binding_against_requirement(requirement, binding)
        if binding.state is BindingStateV1.UNKNOWN:
            raise ValueError("active link cannot contain UNKNOWN binding")
    required = {
        dimension.path_key
        for dimension in capability.claim.dimensions
        if dimension.required
    }
    if not required.issubset(bound):
        raise ValueError("active link is missing a required dimension binding")
    if any(
        binding.state is BindingStateV1.NOT_APPLICABLE and binding.path_key in required
        for binding in link.parameter_bindings
    ):
        raise ValueError("active link is missing a required dimension binding")


def validate_active_link(
    link: RequirementCapabilityLinkV1,
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
    *,
    reviews: Sequence[CapabilityReviewRecordV1],
    admissibility_record: SourceRequirementAdmissibilityV1 | None = None,
) -> None:
    if not isinstance(link, RequirementCapabilityLinkV1):
        raise TypeError("link must be RequirementCapabilityLinkV1")
    requirement = _requirement(requirement)
    capability = _require_capability(capability)
    if capability.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
        raise ValueError("active link requires an ACTIVE Capability")
    if link.capability != capability.capability_ref:
        raise ValueError("link Capability reference does not match Capability")
    if link.requirement_id != requirement.requirement_id:
        raise ValueError("link Requirement ID does not match")
    if link.requirement_wire_digest != wire_digest_for(requirement):
        raise ValueError("Requirement wire digest does not match")
    if (
        link.relation is LinkRelationV1.DIRECT
        and capability.claim.family_key.nucleus_kind is not NucleusKindV1.ATOMIC
    ):
        raise ValueError("DIRECT link requires an atomic Capability")

    if requirement.review.status is ReviewStatusV1.ACCEPTED:
        if requirement.resolution.state is not ResolutionStateV1.COMPLETE:
            raise ValueError("M2 ACCEPTED requirement is not complete")
        expected_review_digest = reviewed_claim_digest_for(requirement)
        if link.requirement_reviewed_claim_digest != expected_review_digest:
            raise ValueError("Requirement reviewed claim digest does not match")
        if link.m4_requirement_admissibility is None or (
            link.m4_requirement_admissibility.basis
            is not LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE
        ):
            raise ValueError("M2 ACCEPTED requirement requires terminal admissibility")
        if admissibility_record is not None:
            raise ValueError("M2 terminal route cannot contain an SRA record")
    elif requirement.review.status in (
        ReviewStatusV1.PROPOSED,
        ReviewStatusV1.IN_REVIEW,
    ):
        if requirement.resolution.state is not ResolutionStateV1.COMPLETE:
            raise ValueError("Requirement is not admissible for active link")
        expected_review_digest = reviewed_claim_digest_for(requirement)
        if link.requirement_reviewed_claim_digest != expected_review_digest:
            raise ValueError("Requirement reviewed claim digest does not match")
        if link.m4_requirement_admissibility is None or (
            link.m4_requirement_admissibility.basis
            is not LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY
        ):
            raise ValueError("active link requires SOURCE_REQUIREMENT_ADMISSIBILITY")
        if not isinstance(admissibility_record, SourceRequirementAdmissibilityV1):
            raise ValueError("active link requires an accepted exact SRA record")
        M4RequirementAdmissibilityV1.source(admissibility_record)
        admissibility_record.validate_m3_manifest(link.m3_analysis_manifest_sha256)
        admissibility_record.validate_against_requirement(requirement)
        if (
            link.m4_requirement_admissibility.record_id
            != admissibility_record.record_id
            or link.m4_requirement_admissibility.review_digest
            != admissibility_record.review_digest
        ):
            raise ValueError("link SRA reference does not match the exact SRA record")
    else:
        raise ValueError("M2 REJECTED requirement is not admissible")

    _validate_active_bindings(link, requirement, capability)
    _validate_link_review(link, reviews)


@dataclass(frozen=True, slots=True)
class MappingCandidateValidationV1:
    is_ambiguous: bool


def validate_mapping_candidates(
    links: Sequence[RequirementCapabilityLinkV1],
) -> MappingCandidateValidationV1:
    groups: dict[tuple[str, bytes], set[str]] = {}
    for link in links:
        if not isinstance(link, RequirementCapabilityLinkV1):
            raise TypeError("links must contain RequirementCapabilityLinkV1 values")
        context = (
            b""
            if link.composition_context is None
            else canonical_json_bytes(link.composition_context.to_wire())
        )
        groups.setdefault((link.requirement_id, context), set()).add(link.link_id)
    return MappingCandidateValidationV1(any(len(ids) > 1 for ids in groups.values()))


def validate_active_links(links: Sequence[RequirementCapabilityLinkV1]) -> None:
    active = [
        link
        for link in links
        if isinstance(link, RequirementCapabilityLinkV1) and link.review_ref is not None
    ]
    if len(active) != sum(
        isinstance(link, RequirementCapabilityLinkV1) for link in links
    ):
        raise TypeError("links must contain RequirementCapabilityLinkV1 values")
    groups: dict[tuple[str, bytes], list[RequirementCapabilityLinkV1]] = {}
    for link in active:
        context = (
            b""
            if link.composition_context is None
            else canonical_json_bytes(link.composition_context.to_wire())
        )
        groups.setdefault((link.requirement_id, context), []).append(link)
    for group in groups.values():
        direct = [link for link in group if link.relation is LinkRelationV1.DIRECT]
        members = [
            link for link in group if link.relation is LinkRelationV1.COMPOSITION_MEMBER
        ]
        if len(direct) > 1:
            raise ValueError("multiple active DIRECT links")
        if direct and members:
            raise ValueError("DIRECT and COMPOSITION_MEMBER links cannot coexist")
        component_keys = [
            cast(CompositionContextV1, link.composition_context).component_key
            for link in members
        ]
        if len(component_keys) != len(set(component_keys)):
            raise ValueError("duplicate active composition component")


@dataclass(frozen=True, slots=True)
class RequirementMappingDecisionV1:
    m3_analysis_manifest_sha256: str
    requirement_id: str
    requirement_wire_digest: str
    disposition: MappingDispositionV1
    active_link_ids: tuple[str, ...]
    candidate_link_claims: tuple[str, ...]
    reason: MappingReasonV1 | None
    review_ref: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "m3_analysis_manifest_sha256",
        "requirement_id",
        "requirement_wire_digest",
        "disposition",
        "active_link_ids",
        "candidate_link_claims",
        "reason",
        "review_ref",
    }

    def __post_init__(self) -> None:
        manifest = _digest(
            "m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256
        )
        requirement_id = _identifier(
            "requirement_id", self.requirement_id, _REQUIREMENT_ID_PATTERN
        )
        wire_digest = _digest("requirement_wire_digest", self.requirement_wire_digest)
        disposition = _require_enum(
            "disposition", self.disposition, MappingDispositionV1
        )
        active = tuple(
            _identifier("active_link_id", item, _LINK_ID_PATTERN)
            for item in _values(self.active_link_ids, "active_link_ids")
        )
        candidate_claims = tuple(
            _digest("candidate_link_claim", item)
            for item in _values(self.candidate_link_claims, "candidate_link_claims")
        )
        if len(active) != len(set(active)) or len(candidate_claims) != len(
            set(candidate_claims)
        ):
            raise ValueError("mapping decision contains duplicate link references")
        reason = (
            None
            if self.reason is None
            else _require_enum("reason", self.reason, MappingReasonV1)
        )
        review_ref = self.review_ref
        if review_ref is not None:
            review_ref = _identifier("review_ref", review_ref, _REVIEW_ID_PATTERN)
        if disposition is MappingDispositionV1.MAPPED:
            if not active or reason is not None:
                raise ValueError(
                    "MAPPED decision requires active links and null reason"
                )
        else:
            if active:
                raise ValueError(
                    "active_link_ids must be empty for a non-MAPPED decision"
                )
            if reason is None:
                raise ValueError("non-MAPPED decision requires a reason")
        if (
            disposition
            in (
                MappingDispositionV1.AMBIGUOUS,
                MappingDispositionV1.OUTLIER,
            )
            and review_ref is None
        ):
            raise ValueError(
                "AMBIGUOUS and OUTLIER decisions require an accepted review"
            )
        object.__setattr__(self, "m3_analysis_manifest_sha256", manifest)
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "requirement_wire_digest", wire_digest)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "active_link_ids", tuple(sorted(active)))
        object.__setattr__(
            self, "candidate_link_claims", tuple(sorted(candidate_claims))
        )
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "review_ref", review_ref)

    @classmethod
    def for_requirement(
        cls,
        requirement: RequirementV1,
        m3_analysis_manifest_sha256: str,
        disposition: MappingDispositionV1,
        reason: MappingReasonV1 | None,
        *,
        active_link_ids: Sequence[str] = (),
        candidate_link_claims: Sequence[str] = (),
        review_ref: str | None = None,
    ) -> RequirementMappingDecisionV1:
        requirement = _requirement(requirement)
        return cls(
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            requirement_id=requirement.requirement_id,
            requirement_wire_digest=wire_digest_for(requirement),
            disposition=disposition,
            active_link_ids=tuple(active_link_ids),
            candidate_link_claims=tuple(candidate_link_claims),
            reason=reason,
            review_ref=review_ref,
        )

    def validate_against_requirement(self, requirement: RequirementV1) -> None:
        requirement = _requirement(requirement)
        if self.requirement_id != requirement.requirement_id:
            raise ValueError("mapping decision Requirement ID does not match")
        if self.requirement_wire_digest != wire_digest_for(requirement):
            raise ValueError("mapping decision Requirement wire digest does not match")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": MAPPING_DECISION_SCHEMA,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
            "disposition": self.disposition.value,
            "active_link_ids": list(self.active_link_ids),
            "candidate_link_claims": list(self.candidate_link_claims),
            "reason": None if self.reason is None else self.reason.value,
            "review_ref": self.review_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementMappingDecisionV1:
        document = _require_object(
            value, cls._WIRE_KEYS, "Requirement mapping decision"
        )
        if document["schema"] != MAPPING_DECISION_SCHEMA:
            raise ValueError(f"schema must be {MAPPING_DECISION_SCHEMA}")
        raw_active = document["active_link_ids"]
        raw_claims = document["candidate_link_claims"]
        if not isinstance(raw_active, list) or not isinstance(raw_claims, list):
            raise TypeError("mapping link collections must be JSON arrays")
        raw_reason = document["reason"]
        result = cls(
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            requirement_id=cast(str, document["requirement_id"]),
            requirement_wire_digest=cast(str, document["requirement_wire_digest"]),
            disposition=_require_enum(
                "disposition", document["disposition"], MappingDispositionV1
            ),
            active_link_ids=tuple(cast(str, item) for item in raw_active),
            candidate_link_claims=tuple(cast(str, item) for item in raw_claims),
            reason=(
                None
                if raw_reason is None
                else _require_enum("reason", raw_reason, MappingReasonV1)
            ),
            review_ref=cast(str | None, document["review_ref"]),
        )
        if result.to_wire() != document:
            raise ValueError("Requirement mapping decision wire is not canonical")
        return result


def mapping_decision(
    requirement: RequirementV1,
    disposition: MappingDispositionV1,
    reason: MappingReasonV1 | None,
    *,
    m3_analysis_manifest_sha256: str = "a" * 64,
    active_link_ids: Sequence[str] = (),
    candidate_link_claims: Sequence[str] = (),
    review_ref: str | None = None,
) -> RequirementMappingDecisionV1:
    return RequirementMappingDecisionV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256,
        disposition,
        reason,
        active_link_ids=active_link_ids,
        candidate_link_claims=candidate_link_claims,
        review_ref=review_ref,
    )


def mapping_decision_claim_payload(
    decision: RequirementMappingDecisionV1,
) -> dict[str, JSONValue]:
    if not isinstance(decision, RequirementMappingDecisionV1):
        raise TypeError("decision must be RequirementMappingDecisionV1")
    wire = decision.to_wire()
    wire.pop("review_ref")
    return wire


def mapping_decision_claim_digest_for(decision: RequirementMappingDecisionV1) -> str:
    return domain_digest(
        MAPPING_DECISION_DOMAIN, mapping_decision_claim_payload(decision)
    )


def mapping_decision_id_for(decision: RequirementMappingDecisionV1) -> str:
    return MAPPING_DECISION_PREFIX + mapping_decision_claim_digest_for(decision)


def validate_mapping_decision(
    decision: RequirementMappingDecisionV1,
    reviews: Sequence[CapabilityReviewRecordV1],
) -> None:
    if not isinstance(decision, RequirementMappingDecisionV1):
        raise TypeError("decision must be RequirementMappingDecisionV1")
    if decision.review_ref is None:
        if decision.disposition in (
            MappingDispositionV1.AMBIGUOUS,
            MappingDispositionV1.OUTLIER,
        ):
            raise ValueError("mapping decision requires an accepted review")
        return
    records = tuple(reviews)
    if any(not isinstance(record, CapabilityReviewRecordV1) for record in records):
        raise TypeError("reviews must contain CapabilityReviewRecordV1 values")
    subject = MappingDecisionReviewSubjectV1(
        mapping_decision_id_for(decision),
        mapping_decision_claim_digest_for(decision),
    )
    matching = tuple(record for record in records if record.subject == subject)
    if any(record.decision is ReviewDecisionV1.ACCEPTED for record in matching) and any(
        record.decision is ReviewDecisionV1.REJECTED for record in matching
    ):
        raise ValueError("conflicting accepted and rejected mapping reviews")
    referenced = tuple(
        record for record in matching if record.record_id == decision.review_ref
    )
    if len(referenced) != 1 or referenced[0].decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError("mapping decision requires an exact accepted review")
