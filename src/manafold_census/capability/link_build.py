"""Construction helpers for typed Requirement-to-Capability links."""

from __future__ import annotations

from collections.abc import Sequence

from ..semantic.identity import reviewed_claim_digest_for, wire_digest_for
from ..semantic.model import RequirementV1, ReviewStatusV1
from ..semantic.primitives import _require_enum
from .admissibility import SourceRequirementAdmissibilityV1
from .binding import ParameterBindingV1
from .definition import CapabilityDefinitionV1
from .identity import capability_ref_for
from .link import (
    CompositionContextV1,
    LinkRelationV1,
    M4RequirementAdmissibilityV1,
    RequirementCapabilityLinkV1,
)
from .model import NucleusKindV1


def _make_link(
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
    *,
    m3_manifest_sha256: str,
    relation: LinkRelationV1,
    parameter_bindings: Sequence[ParameterBindingV1],
    admissibility: SourceRequirementAdmissibilityV1 | None,
    composition_context: CompositionContextV1 | None,
    review_ref: str | None,
) -> RequirementCapabilityLinkV1:
    if not isinstance(requirement, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    if not isinstance(capability, CapabilityDefinitionV1):
        raise TypeError("capability must be CapabilityDefinitionV1")
    relation_value = _require_enum("relation", relation, LinkRelationV1)
    if relation_value is LinkRelationV1.DIRECT:
        if capability.claim.family_key.nucleus_kind is not NucleusKindV1.ATOMIC:
            raise ValueError("DIRECT link requires an atomic Capability")
        if capability.claim.family_key.operation_anchor != (
            (requirement.family, requirement.kind),
        ):
            raise ValueError("DIRECT link operation anchor does not match Requirement")
    elif composition_context is None:
        raise ValueError("COMPOSITION_MEMBER link requires composition context")
    if admissibility is not None:
        if not isinstance(admissibility, SourceRequirementAdmissibilityV1):
            raise TypeError("admissibility must be SourceRequirementAdmissibilityV1")
        admissibility.validate_m3_manifest(m3_manifest_sha256)
        admissibility.validate_against_requirement(requirement)
        link_admissibility = M4RequirementAdmissibilityV1.source(admissibility)
    elif requirement.review.status is ReviewStatusV1.ACCEPTED:
        link_admissibility = M4RequirementAdmissibilityV1.terminal()
    else:
        link_admissibility = None
    return RequirementCapabilityLinkV1.create(
        m3_analysis_manifest_sha256=m3_manifest_sha256,
        requirement_id=requirement.requirement_id,
        requirement_wire_digest=wire_digest_for(requirement),
        requirement_reviewed_claim_digest=(
            reviewed_claim_digest_for(requirement)
            if requirement.review.status is ReviewStatusV1.ACCEPTED
            or admissibility is not None
            else None
        ),
        capability=capability_ref_for(capability.claim),
        relation=relation_value,
        parameter_bindings=parameter_bindings,
        m4_requirement_admissibility=link_admissibility,
        composition_context=composition_context,
        review_ref=review_ref,
    )


def direct_link(
    *,
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
    m3_manifest_sha256: str,
    admissibility: SourceRequirementAdmissibilityV1 | None = None,
    parameter_bindings: Sequence[ParameterBindingV1] = (),
    review_ref: str | None = None,
) -> RequirementCapabilityLinkV1:
    return _make_link(
        requirement,
        capability,
        m3_manifest_sha256=m3_manifest_sha256,
        relation=LinkRelationV1.DIRECT,
        parameter_bindings=parameter_bindings,
        admissibility=admissibility,
        composition_context=None,
        review_ref=review_ref,
    )


def composition_member_link(
    *,
    requirement: RequirementV1,
    capability: CapabilityDefinitionV1,
    m3_manifest_sha256: str,
    composition_context: CompositionContextV1,
    admissibility: SourceRequirementAdmissibilityV1 | None = None,
    parameter_bindings: Sequence[ParameterBindingV1] = (),
    review_ref: str | None = None,
) -> RequirementCapabilityLinkV1:
    return _make_link(
        requirement,
        capability,
        m3_manifest_sha256=m3_manifest_sha256,
        relation=LinkRelationV1.COMPOSITION_MEMBER,
        parameter_bindings=parameter_bindings,
        admissibility=admissibility,
        composition_context=composition_context,
        review_ref=review_ref,
    )
