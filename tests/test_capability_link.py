from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from capability_fixtures import draw_family_key
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from manafold_census.capability.admissibility import (
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
)
from manafold_census.capability.binding import ParameterBindingV1
from manafold_census.capability.claim import CapabilityClaimV1
from manafold_census.capability.definition import (
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    CapabilityProvenanceV1,
)
from manafold_census.capability.dimensions import (
    CapabilityDimensionV1,
    DimensionDomainKindV1,
    DimensionKindV1,
    M2DimensionPathV1,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.link import (
    LINK_ID_DOMAIN,
    LINK_ID_PREFIX,
    LinkAdmissibilityBasisV1,
    LinkRelationV1,
    M4RequirementAdmissibilityV1,
    RequirementCapabilityLinkV1,
    direct_link,
)
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    RequirementMappingDecisionV1,
    mapping_decision,
    mapping_decision_claim_digest_for,
    mapping_decision_id_for,
    validate_active_link,
    validate_active_links,
    validate_mapping_candidates,
    validate_mapping_decision,
)
from manafold_census.capability.review import (
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    MappingDecisionReviewSubjectV1,
    ReviewDecisionV1,
)
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.identity import reviewed_claim_digest_for, wire_digest_for
from manafold_census.semantic.kind_payloads import DrawCardsParametersV1
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
from manafold_census.semantic.model import (
    DerivationMethodV1,
    DerivationV1,
    ProvenanceV1,
    RequirementV1,
    ResolutionReasonV1,
    ResolutionStateV1,
    ResolutionV1,
    ReviewStatusV1,
    ReviewV1,
)
from manafold_census.semantic.primitives import (
    EntityRefV1,
    EntityRoleV1,
    MultiplicityV1,
    QuantityModeV1,
    QuantityV1,
)

M3_MANIFEST_SHA256 = "a" * 64
ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"


def _requirement(
    *,
    status: ReviewStatusV1 = ReviewStatusV1.PROPOSED,
    resolution: ResolutionV1 | None = None,
    source_record_sha256: str = "2" * 64,
) -> RequirementV1:
    source = SourceRecordRefV1(
        "census.structural-card.v1",
        "1" * 64,
        ORACLE_ID,
        SOURCE_CARD_ID,
        source_record_sha256,
    )
    parameters = DrawCardsParametersV1(
        EntityRefV1(EntityRoleV1.CONTROLLER, MultiplicityV1.ONE, None),
        QuantityV1(QuantityModeV1.EXACT, 2),
    )
    actual_resolution = resolution or ResolutionV1(
        ResolutionStateV1.COMPLETE,
        ResolutionReasonV1.NONE,
        (),
    )
    proposal = RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=parameters,
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "task5-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=actual_resolution,
    )
    if status is ReviewStatusV1.PROPOSED:
        return proposal
    return RequirementV1.create(
        source=source,
        family=proposal.family,
        kind=proposal.kind,
        parameters=proposal.parameters,
        evidence=proposal.evidence,
        provenance=proposal.provenance,
        review=ReviewV1(
            status,
            "maintainer:test"
            if status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED)
            else None,
            reviewed_claim_digest_for(proposal)
            if status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED)
            else None,
        ),
        resolution=proposal.resolution,
    )


def _claim(*, required: bool = True) -> CapabilityClaimV1:
    return CapabilityClaimV1(
        family_key=draw_family_key(),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version="1",
        dimensions=(
            CapabilityDimensionV1(
                M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                DimensionKindV1.QUANTITY,
                required,
                DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=None,
    )


def _capability(*, required: bool = True) -> CapabilityDefinitionV1:
    claim = _claim(required=required)
    return CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name="Draw cards",
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        provenance=CapabilityProvenanceV1("b" * 64, ("ccg_" + "c" * 64,), ()),
        review_ref="mrv_" + "d" * 64,
    )


def _sra(requirement: RequirementV1) -> SourceRequirementAdmissibilityV1:
    return SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )


def _quantity_binding() -> ParameterBindingV1:
    return ParameterBindingV1.known(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        {"mode": "exact", "value": 2},
    )


def _link_review(link: RequirementCapabilityLinkV1) -> CapabilityReviewRecordV1:
    return CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityLinkReviewSubjectV1(link.link_id, link.link_claim_digest),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=None,
    )


def _validated_schema(name: str, document: dict[str, object]) -> None:
    schema_path = Path(__file__).parents[1] / "schemas" / name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)


def test_direct_link_binds_requirement_and_capability_claims() -> None:
    requirement = _requirement()
    capability = _capability()
    admissibility = _sra(requirement)

    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=admissibility,
    )

    assert link.relation is LinkRelationV1.DIRECT
    assert link.requirement_id == requirement.requirement_id
    assert link.requirement_wire_digest == wire_digest_for(requirement)
    assert link.capability.claim_digest == capability.claim_digest
    assert link.m4_requirement_admissibility.basis is (
        LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY
    )


def test_link_identity_and_wire_are_canonical_and_schema_valid() -> None:
    requirement = _requirement()
    link = direct_link(
        requirement=requirement,
        capability=_capability(),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(requirement),
        parameter_bindings=(_quantity_binding(),),
    )

    assert LINK_ID_DOMAIN == "census.requirement-capability-link-id.v1"
    assert LINK_ID_PREFIX == "rcl_"
    assert link.link_id.startswith("rcl_")
    assert len(link.link_claim_digest) == 64
    assert RequirementCapabilityLinkV1.from_wire(link.to_wire()) == link
    _validated_schema("requirement-capability-link.v1.schema.json", link.to_wire())


def test_active_proposed_link_requires_exact_sra_route() -> None:
    requirement = _requirement()
    capability = _capability()
    proposal = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(requirement),
        parameter_bindings=(_quantity_binding(),),
    )
    review = _link_review(proposal)
    active = replace(proposal, review_ref=review.record_id)

    validate_active_link(
        active,
        requirement,
        capability,
        reviews=(review,),
        admissibility_record=_sra(requirement),
    )

    with pytest.raises(ValueError, match="M3 manifest"):
        validate_active_link(
            active,
            requirement,
            capability,
            reviews=(review,),
            admissibility_record=SourceRequirementAdmissibilityV1.for_requirement(
                requirement,
                m3_analysis_manifest_sha256="f" * 64,
                authority_id="m4.source-requirement-admissibility",
                authority_version="1",
                reviewer_id="maintainer:test",
            ),
        )


def test_active_proposed_link_rejects_a_rejected_sra_record() -> None:
    requirement = _requirement()
    capability = _capability()
    accepted = _sra(requirement)
    proposal = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=accepted,
        parameter_bindings=(_quantity_binding(),),
    )
    rejected = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="2",
        reviewer_id="maintainer:test",
        decision=AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING,
    )
    bad = RequirementCapabilityLinkV1.create(
        m3_analysis_manifest_sha256=proposal.m3_analysis_manifest_sha256,
        requirement_id=proposal.requirement_id,
        requirement_wire_digest=proposal.requirement_wire_digest,
        requirement_reviewed_claim_digest=proposal.requirement_reviewed_claim_digest,
        capability=proposal.capability,
        relation=proposal.relation,
        parameter_bindings=proposal.parameter_bindings,
        m4_requirement_admissibility=M4RequirementAdmissibilityV1(
            LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY,
            rejected.record_id,
            rejected.review_digest,
        ),
        composition_context=proposal.composition_context,
    )
    review = _link_review(bad)

    with pytest.raises(ValueError, match="not accepted"):
        validate_active_link(
            replace(bad, review_ref=review.record_id),
            requirement,
            capability,
            reviews=(review,),
            admissibility_record=rejected,
        )


def test_active_accepted_m2_requirement_uses_terminal_route_without_sra() -> None:
    requirement = _requirement(status=ReviewStatusV1.ACCEPTED)
    capability = _capability()
    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
        parameter_bindings=(_quantity_binding(),),
    )
    review = _link_review(link)
    active = replace(link, review_ref=review.record_id)

    assert active.m4_requirement_admissibility.basis is (
        LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE
    )
    validate_active_link(active, requirement, capability, reviews=(review,))


@pytest.mark.parametrize(
    "requirement",
    [
        _requirement(status=ReviewStatusV1.REJECTED),
        _requirement(
            resolution=ResolutionV1(
                ResolutionStateV1.PARTIAL,
                ResolutionReasonV1.UNKNOWN_SEMANTICS,
                ("/parameters/quantity",),
            )
        ),
        _requirement(
            resolution=ResolutionV1(
                ResolutionStateV1.UNRESOLVED,
                ResolutionReasonV1.CONFLICTING_INTERPRETATIONS,
                ("/parameters/quantity",),
            )
        ),
    ],
)
def test_inadmissible_requirement_cannot_receive_active_link(
    requirement: RequirementV1,
) -> None:
    capability = _capability()
    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
    )
    review = _link_review(link)
    active = replace(link, review_ref=review.record_id)

    with pytest.raises(ValueError, match="not admissible"):
        validate_active_link(active, requirement, capability, reviews=(review,))


def test_stale_requirement_wire_and_capability_claim_are_rejected() -> None:
    requirement = _requirement()
    capability = _capability()
    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(requirement),
        parameter_bindings=(_quantity_binding(),),
    )
    review = _link_review(link)
    active = replace(link, review_ref=review.record_id)

    with pytest.raises(ValueError, match="Requirement wire digest"):
        validate_active_link(
            active,
            _requirement(
                resolution=ResolutionV1(
                    ResolutionStateV1.PARTIAL,
                    ResolutionReasonV1.UNKNOWN_SEMANTICS,
                    ("/parameters/quantity",),
                )
            ),
            capability,
            reviews=(review,),
            admissibility_record=_sra(requirement),
        )

    with pytest.raises(ValueError, match="Capability"):
        validate_active_link(
            active,
            requirement,
            _capability(required=False),
            reviews=(review,),
            admissibility_record=_sra(requirement),
        )


def test_required_binding_is_typed_and_unknown_binding_is_not_active() -> None:
    requirement = _requirement()
    capability = _capability()
    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(requirement),
        parameter_bindings=(),
    )
    review = _link_review(link)
    active = replace(link, review_ref=review.record_id)

    with pytest.raises(ValueError, match="required dimension"):
        validate_active_link(
            active,
            requirement,
            capability,
            reviews=(review,),
            admissibility_record=_sra(requirement),
        )


def test_capability_reuse_and_proposals_remain_visible() -> None:
    capability = _capability()
    first = _requirement(source_record_sha256="2" * 64)
    second = _requirement(source_record_sha256="3" * 64)
    first_link = direct_link(
        requirement=first,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(first),
        parameter_bindings=(_quantity_binding(),),
    )
    second_link = direct_link(
        requirement=second,
        capability=capability,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(second),
        parameter_bindings=(_quantity_binding(),),
    )

    assert first_link.capability == second_link.capability
    assert validate_mapping_candidates((first_link, second_link)).is_ambiguous is False

    alternate = direct_link(
        requirement=first,
        capability=_capability(required=False),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=_sra(first),
    )
    assert validate_mapping_candidates((first_link, alternate)).is_ambiguous is True


def test_two_active_direct_links_fail_but_proposals_remain_visible() -> None:
    requirement = _requirement(status=ReviewStatusV1.ACCEPTED)
    first = direct_link(
        requirement=requirement,
        capability=_capability(),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
    )
    second = direct_link(
        requirement=requirement,
        capability=_capability(required=False),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
    )
    first_review = _link_review(first)
    second_review = _link_review(second)

    assert validate_mapping_candidates((first, second)).is_ambiguous is True
    with pytest.raises(ValueError, match="multiple active DIRECT"):
        validate_active_links(
            (
                replace(first, review_ref=first_review.record_id),
                replace(second, review_ref=second_review.record_id),
            )
        )


@pytest.mark.parametrize(
    ("disposition", "reason"),
    [
        (MappingDispositionV1.UNMAPPED, MappingReasonV1.NO_REVIEWED_CAPABILITY),
        (
            MappingDispositionV1.AMBIGUOUS,
            MappingReasonV1.MULTIPLE_PLAUSIBLE_CAPABILITIES,
        ),
        (MappingDispositionV1.OUTLIER, MappingReasonV1.NO_REUSABLE_GENERALIZATION),
        (
            MappingDispositionV1.INSUFFICIENT_EVIDENCE,
            MappingReasonV1.M2_REVIEW_NOT_TERMINAL,
        ),
    ],
)
def test_mapping_decision_preserves_non_link_dispositions(
    disposition: MappingDispositionV1,
    reason: MappingReasonV1,
) -> None:
    decision = mapping_decision(
        _requirement(),
        disposition,
        reason,
        review_ref=(
            "mrv_" + "a" * 64
            if disposition
            in (MappingDispositionV1.AMBIGUOUS, MappingDispositionV1.OUTLIER)
            else None
        ),
    )

    assert decision.active_link_ids == ()
    assert decision.disposition is disposition
    assert decision.reason is reason
    assert RequirementMappingDecisionV1.from_wire(decision.to_wire()) == decision
    _validated_schema("requirement-mapping-decision.v1.schema.json", decision.to_wire())


def test_mapping_decision_rejects_active_links_for_non_mapped_disposition() -> None:
    requirement = _requirement(status=ReviewStatusV1.ACCEPTED)
    link = direct_link(
        requirement=requirement,
        capability=_capability(),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
    )

    with pytest.raises(ValueError, match="active_link_ids"):
        RequirementMappingDecisionV1.for_requirement(
            requirement,
            M3_MANIFEST_SHA256,
            MappingDispositionV1.UNMAPPED,
            MappingReasonV1.NO_REVIEWED_CAPABILITY,
            active_link_ids=(link.link_id,),
        )


def test_link_wire_rejects_unknown_fields_and_noncanonical_bindings() -> None:
    link = direct_link(
        requirement=_requirement(),
        capability=_capability(),
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        admissibility=None,
    )
    extra = link.to_wire()
    extra["engine"] = "forbidden"
    with pytest.raises(ValueError, match="unexpected properties"):
        RequirementCapabilityLinkV1.from_wire(extra)

    _validated_schema("requirement-capability-link.v1.schema.json", link.to_wire())


def test_mapping_schema_rejects_unknown_disposition() -> None:
    decision = mapping_decision(
        _requirement(),
        MappingDispositionV1.UNMAPPED,
        MappingReasonV1.NO_REVIEWED_CAPABILITY,
    )
    wire = decision.to_wire()
    wire["disposition"] = "MAPS_TO"

    with pytest.raises(ValidationError):
        _validated_schema("requirement-mapping-decision.v1.schema.json", wire)


def test_mapping_review_binds_the_exact_decision_claim() -> None:
    draft = mapping_decision(
        _requirement(),
        MappingDispositionV1.AMBIGUOUS,
        MappingReasonV1.MULTIPLE_PLAUSIBLE_CAPABILITIES,
        review_ref="mrv_" + "0" * 64,
    )
    review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=MappingDecisionReviewSubjectV1(
            mapping_decision_id_for(draft),
            mapping_decision_claim_digest_for(draft),
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=None,
    )
    decision = replace(draft, review_ref=review.record_id)

    assert mapping_decision_claim_digest_for(
        draft
    ) == mapping_decision_claim_digest_for(decision)
    validate_mapping_decision(decision, reviews=(review,))
