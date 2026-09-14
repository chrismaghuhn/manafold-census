from __future__ import annotations

import json
from pathlib import Path

import pytest
from capability_fixtures import draw_family_key
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from manafold_census.capability.claim import CapabilityClaimV1
from manafold_census.capability.definition import (
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    CapabilityProvenanceV1,
    CapabilityRequirementProvenanceV1,
    can_receive_active_link,
    validate_active_definition,
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
from manafold_census.capability.review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityReviewRecordV1,
    GeneralizationBasisV1,
    ReviewDecisionV1,
)

ZERO_DIGEST = "0" * 64
M3_MANIFEST_SHA256 = "a" * 64
CANDIDATE_ID = "ccg_" + "c" * 64
REQUIREMENT_ID = "srq_" + "d" * 64
REQUIREMENT_WIRE_DIGEST = "e" * 64


def _draw_claim(*, registry_version: str = "1") -> CapabilityClaimV1:
    return CapabilityClaimV1(
        family_key=draw_family_key(),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version=registry_version,
        dimensions=(
            CapabilityDimensionV1(
                path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                dimension_kind=DimensionKindV1.QUANTITY,
                required=True,
                domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=None,
    )


def _provenance(
    *,
    candidate_cluster_ids: tuple[str, ...] = (CANDIDATE_ID,),
    requirement_refs: tuple[CapabilityRequirementProvenanceV1, ...] = (),
) -> CapabilityProvenanceV1:
    return CapabilityProvenanceV1(
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        candidate_cluster_ids=candidate_cluster_ids,
        requirement_refs=requirement_refs,
    )


def _definition(
    *,
    display_name: str = "Draw cards",
    lifecycle: CapabilityLifecycleStateV1 = CapabilityLifecycleStateV1.PROPOSED,
    claim: CapabilityClaimV1 | None = None,
    provenance: CapabilityProvenanceV1 | None = None,
    review_ref: str | None = None,
) -> CapabilityDefinitionV1:
    actual_claim = claim or _draw_claim()
    return CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(actual_claim.family_key),
        capability_version=actual_claim.capability_version,
        claim_digest=capability_claim_digest_for(actual_claim),
        claim=actual_claim,
        display_name=display_name,
        lifecycle=lifecycle,
        provenance=provenance or _provenance(),
        review_ref=review_ref,
    )


def _definition_review(
    definition: CapabilityDefinitionV1,
    *,
    decision: ReviewDecisionV1 = ReviewDecisionV1.ACCEPTED,
    basis: GeneralizationBasisV1 | None = GeneralizationBasisV1.MULTI_SOURCE_REUSE,
) -> CapabilityReviewRecordV1:
    return CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityDefinitionReviewSubjectV1(
            capability_family_id=definition.capability_family_id,
            capability_version=definition.capability_version,
            claim_digest=definition.claim_digest,
        ),
        decision=decision,
        reviewer_id="maintainer:test",
        generalization_basis=basis,
    )


def _validate_definition_schema(document: dict[str, object]) -> None:
    root = Path(__file__).parents[1]
    definition = json.loads(
        (root / "schemas" / "capability-definition.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    claim = json.loads(
        (root / "schemas" / "capability-claim.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    claim_id = claim["$id"]
    assert isinstance(claim_id, str)
    registry = Registry().with_resource(
        claim_id,
        Resource.from_contents(claim, default_specification=DRAFT202012),
    )
    Draft202012Validator(definition, registry=registry).validate(document)


def test_proposed_definition_cannot_be_active() -> None:
    definition = _definition()

    assert definition.lifecycle is CapabilityLifecycleStateV1.PROPOSED
    with pytest.raises(ValueError, match="active definition requires accepted review"):
        validate_active_definition(definition, reviews=())


def test_same_claim_can_change_display_name_without_claim_digest_change() -> None:
    first = _definition(display_name="Draw cards")
    second = _definition(display_name="Card draw")

    assert first.claim_digest == second.claim_digest
    assert first.capability_family_id == second.capability_family_id
    assert first.to_wire()["display_name"] != second.to_wire()["display_name"]


@pytest.mark.parametrize(
    "lifecycle",
    [CapabilityLifecycleStateV1.SUPERSEDED, CapabilityLifecycleStateV1.RETIRED],
)
def test_historical_definitions_cannot_receive_new_active_links(
    lifecycle: CapabilityLifecycleStateV1,
) -> None:
    definition = _definition(lifecycle=lifecycle)

    assert can_receive_active_link(definition) is False


def test_proposed_definition_can_receive_no_active_link() -> None:
    assert can_receive_active_link(_definition()) is False


def test_definition_round_trip_is_canonical_and_schema_valid() -> None:
    definition = _definition(
        provenance=_provenance(
            candidate_cluster_ids=(),
            requirement_refs=(
                CapabilityRequirementProvenanceV1(
                    REQUIREMENT_ID,
                    REQUIREMENT_WIRE_DIGEST,
                ),
            ),
        )
    )

    assert CapabilityDefinitionV1.from_wire(definition.to_wire()) == definition
    _validate_definition_schema(definition.to_wire())


def test_provenance_collections_are_canonical_and_unique() -> None:
    second_candidate = "ccg_" + "b" * 64
    second_requirement = CapabilityRequirementProvenanceV1(
        "srq_" + "b" * 64,
        "f" * 64,
    )
    provenance = CapabilityProvenanceV1(
        M3_MANIFEST_SHA256,
        (CANDIDATE_ID, second_candidate),
        (second_requirement,),
    )

    assert provenance.candidate_cluster_ids == tuple(
        sorted((CANDIDATE_ID, second_candidate))
    )
    assert provenance.requirement_refs == (second_requirement,)

    with pytest.raises(ValueError, match="duplicate candidate"):
        CapabilityProvenanceV1(M3_MANIFEST_SHA256, (CANDIDATE_ID, CANDIDATE_ID), ())

    with pytest.raises(ValueError, match="duplicate Requirement"):
        CapabilityProvenanceV1(
            M3_MANIFEST_SHA256,
            (),
            (second_requirement, second_requirement),
        )

    with pytest.raises(ValueError, match="combined basis"):
        CapabilityProvenanceV1(M3_MANIFEST_SHA256, (), ())


def test_definition_rejects_stale_identity_fields() -> None:
    definition = _definition()

    with pytest.raises(ValueError, match="capability_family_id"):
        CapabilityDefinitionV1(
            capability_family_id="capfam_" + "f" * 64,
            capability_version=definition.capability_version,
            claim_digest=definition.claim_digest,
            claim=definition.claim,
            display_name=definition.display_name,
            lifecycle=definition.lifecycle,
            provenance=definition.provenance,
            review_ref=None,
        )

    with pytest.raises(ValueError, match="claim_digest"):
        CapabilityDefinitionV1(
            capability_family_id=definition.capability_family_id,
            capability_version=definition.capability_version,
            claim_digest=ZERO_DIGEST,
            claim=definition.claim,
            display_name=definition.display_name,
            lifecycle=definition.lifecycle,
            provenance=definition.provenance,
            review_ref=None,
        )


def test_definition_wire_rejects_unknown_fields_and_noncanonical_provenance() -> None:
    wire = _definition().to_wire()
    wire["unexpected"] = True

    with pytest.raises(ValueError, match="unexpected properties"):
        CapabilityDefinitionV1.from_wire(wire)

    unsorted = _definition(
        provenance=_provenance(candidate_cluster_ids=(CANDIDATE_ID, "ccg_" + "b" * 64))
    ).to_wire()
    unsorted_provenance = unsorted["provenance"]
    assert isinstance(unsorted_provenance, dict)
    unsorted_provenance["candidate_cluster_ids"] = list(
        reversed(unsorted_provenance["candidate_cluster_ids"])
    )

    with pytest.raises(ValueError, match="canonical"):
        CapabilityDefinitionV1.from_wire(unsorted)


def test_active_definition_requires_an_exact_accepted_review() -> None:
    proposed = _definition()
    accepted_review = _definition_review(proposed)
    active = _definition(
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        review_ref=accepted_review.record_id,
    )

    validate_active_definition(active, reviews=(accepted_review,))

    with pytest.raises(ValueError, match="accepted review"):
        validate_active_definition(active, reviews=())

    rejected_review = _definition_review(
        active,
        decision=ReviewDecisionV1.REJECTED,
        basis=None,
    )
    with pytest.raises(ValueError, match="accepted review"):
        validate_active_definition(
            active,
            reviews=(accepted_review, rejected_review),
        )


def test_active_definition_review_subject_must_bind_the_exact_claim() -> None:
    definition = _definition(lifecycle=CapabilityLifecycleStateV1.ACTIVE)
    wrong_review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityDefinitionReviewSubjectV1(
            capability_family_id=definition.capability_family_id,
            capability_version=definition.capability_version,
            claim_digest="f" * 64,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )
    active = _definition(
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        review_ref=wrong_review.record_id,
    )

    with pytest.raises(ValueError, match="exact Capability"):
        validate_active_definition(active, reviews=(wrong_review,))
