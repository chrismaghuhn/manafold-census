"""Validation of active Requirement-to-Capability mappings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..semantic.identity import reviewed_claim_digest_for, wire_digest_for
from ..semantic.kind_payloads import payload_to_wire
from ..semantic.model import RequirementV1, ResolutionStateV1, ReviewStatusV1
from .admissibility import SourceRequirementAdmissibilityV1
from .binding import (
    BindingStateV1,
    ParameterBindingV1,
    _contains_unknown,
    validate_binding_against_requirement,
)
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .dimensions import CapabilityDimensionV1, DimensionDomainKindV1, dimension_spec_for
from .link import (
    CompositionContextV1,
    LinkAdmissibilityBasisV1,
    LinkRelationV1,
    M4RequirementAdmissibilityV1,
    RequirementCapabilityLinkV1,
)
from .model import NucleusKindV1
from .review import (
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    ReviewDecisionV1,
)


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


def _validate_dimension_domain(
    dimension: CapabilityDimensionV1,
    binding: ParameterBindingV1,
) -> None:
    if binding.state is not BindingStateV1.KNOWN:
        return
    value = binding.value
    domain_kind = dimension.domain_kind
    if domain_kind is DimensionDomainKindV1.ANY_TYPED_VALUE:
        return
    if domain_kind is DimensionDomainKindV1.M2_ENUM_SUBSET:
        allowed = dimension.allowed_enum_values
        if not isinstance(value, str) or value not in allowed:
            raise ValueError("binding value is outside the Capability dimension domain")
        return
    allowed_shapes = {shape.value for shape in dimension.allowed_shapes}
    if not isinstance(value, dict) or value.get("shape") not in allowed_shapes:
        raise ValueError("binding value is outside the Capability dimension domain")


def _requirement_value(
    requirement: RequirementV1,
    path_key: object,
) -> tuple[object, JSONValue]:
    spec = dimension_spec_for(path_key)
    if (spec.family, spec.kind) != (requirement.family, requirement.kind):
        raise ValueError("Capability exclusion does not apply to this Requirement")
    field = spec.parameter_path.removeprefix("/parameters/")
    parameters = payload_to_wire(
        requirement.family, requirement.kind, requirement.parameters
    )
    if field not in parameters:
        raise ValueError("registered Capability path is absent from Requirement")
    return getattr(requirement.parameters, field), parameters[field]


def _validate_exclusions(
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
) -> None:
    for exclusion in capability.claim.exclusions:
        try:
            actual_typed, actual_wire = _requirement_value(
                requirement, exclusion.path_key
            )
        except ValueError as error:
            if str(error) == "Capability exclusion does not apply to this Requirement":
                continue
            raise
        if _contains_unknown(actual_typed):
            raise ValueError("active link cannot validate an unknown excluded value")
        if actual_wire is None:
            continue
        if exclusion.domain_kind is DimensionDomainKindV1.M2_ENUM_SUBSET:
            if actual_wire in exclusion.excluded_enum_values:
                raise ValueError("Requirement value matches a Capability exclusion")
        elif exclusion.domain_kind is DimensionDomainKindV1.M2_SHAPE_SUBSET:
            shapes = {shape.value for shape in exclusion.excluded_shapes}
            if isinstance(actual_wire, dict) and actual_wire.get("shape") in shapes:
                raise ValueError("Requirement value matches a Capability exclusion")


def _validate_active_bindings(
    link: RequirementCapabilityLinkV1,
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
) -> None:
    declared = {
        dimension.path_key: dimension for dimension in capability.claim.dimensions
    }
    bound = {binding.path_key for binding in link.parameter_bindings}
    if not bound.issubset(declared):
        raise ValueError("link binding is not declared by the Capability claim")
    for binding in link.parameter_bindings:
        validate_binding_against_requirement(requirement, binding)
        if binding.state is BindingStateV1.UNKNOWN:
            raise ValueError("active link cannot contain UNKNOWN binding")
        _validate_dimension_domain(declared[binding.path_key], binding)
    required = {
        path_key for path_key, dimension in declared.items() if dimension.required
    }
    if not required.issubset(bound) or any(
        binding.state is BindingStateV1.NOT_APPLICABLE and binding.path_key in required
        for binding in link.parameter_bindings
    ):
        raise ValueError("active link is missing a required dimension binding")
    _validate_exclusions(requirement, capability)


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
    if (
        link.relation is LinkRelationV1.DIRECT
        and capability.claim.family_key.operation_anchor
        != ((requirement.family, requirement.kind),)
    ):
        raise ValueError("DIRECT link operation anchor does not match Requirement")

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
    values = tuple(links)
    if any(not isinstance(link, RequirementCapabilityLinkV1) for link in values):
        raise TypeError("links must contain RequirementCapabilityLinkV1 values")
    active = tuple(link for link in values if link.review_ref is not None)
    groups: dict[str, list[RequirementCapabilityLinkV1]] = {}
    for link in active:
        groups.setdefault(link.requirement_id, []).append(link)
    for group in groups.values():
        direct = [link for link in group if link.relation is LinkRelationV1.DIRECT]
        members = [
            link for link in group if link.relation is LinkRelationV1.COMPOSITION_MEMBER
        ]
        if len(direct) > 1:
            raise ValueError("multiple active DIRECT links")
        if direct and members:
            raise ValueError("DIRECT and COMPOSITION_MEMBER links cannot coexist")
        contexts = {
            canonical_json_bytes(
                cast(CompositionContextV1, link.composition_context).to_wire()
            )
            for link in members
        }
        if len(contexts) > 1:
            raise ValueError(
                "multiple COMPOSITION_MEMBER links require the same composition context"
            )
        component_keys = [
            cast(CompositionContextV1, link.composition_context).component_key
            for link in members
        ]
        if len(component_keys) != len(set(component_keys)):
            raise ValueError("duplicate active composition component")
