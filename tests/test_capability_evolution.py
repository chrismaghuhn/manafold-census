from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from manafold_census.capability.admissibility import (
    SourceRequirementAdmissibilityV1,
)
from manafold_census.capability.claim import (
    CapabilityClaimV1,
    CompositionClaimV1,
    CompositionComponentV1,
)
from manafold_census.capability.definition import (
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    CapabilityProvenanceV1,
)
from manafold_census.capability.evolution import (
    CapabilityEvolutionV1,
    CapabilityRelationKindV1,
    CapabilityRelationV1,
    EvolutionOperationV1,
    addition_event,
    composes_edge,
    evolution_claim_digest_for,
    merge_event,
    requires_edge,
    retirement_event,
    sort_capability_relations,
    specializes_edge,
    split_event,
    supersession_event,
    validate_capability_edges,
    validate_evolution_history,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.link import (
    CompositionContextV1,
    RequirementCapabilityLinkV1,
)
from manafold_census.capability.link_build import composition_member_link
from manafold_census.capability.link_validation import (
    validate_active_link,
    validate_active_links,
)
from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    CapabilityRefV1,
    NucleusKindV1,
)
from manafold_census.capability.review import (
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    EvolutionReviewSubjectV1,
    ReviewDecisionV1,
)
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.kind_payloads import (
    DealDamageParametersV1,
    DrawCardsParametersV1,
)
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

REVIEW_REF = "mrv_" + "0" * 64
M3_MANIFEST_SHA256 = "d" * 64


def _claim(
    *,
    kind: RequirementKindV1,
    version: int = 1,
    family_key: CapabilityFamilyKeyV1 | None = None,
    composition: CompositionClaimV1 | None = None,
) -> CapabilityClaimV1:
    anchor = family_key or CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.ATOMIC,
        ((RequirementFamilyV1.EFFECT, kind),),
    )
    return CapabilityClaimV1(
        family_key=anchor,
        capability_version=version,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version="1",
        dimensions=(),
        exclusions=(),
        composition=composition,
    )


def _definition(
    claim: CapabilityClaimV1,
    *,
    display_name: str = "Synthetic capability",
    lifecycle: CapabilityLifecycleStateV1 = CapabilityLifecycleStateV1.ACTIVE,
) -> CapabilityDefinitionV1:
    return CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name=display_name,
        lifecycle=lifecycle,
        provenance=CapabilityProvenanceV1(
            "a" * 64,
            ("ccg_" + "b" * 64,),
            (),
        ),
        review_ref="mrv_" + "c" * 64,
    )


def active_draw_capability(*, version: int = 1) -> CapabilityDefinitionV1:
    return _definition(
        _claim(kind=RequirementKindV1.DRAW_CARDS, version=version),
        display_name=f"Draw cards v{version}",
    )


def active_damage_capability() -> CapabilityDefinitionV1:
    return _definition(
        _claim(kind=RequirementKindV1.DEAL_DAMAGE),
        display_name="Deal damage",
    )


def composite_capability() -> CapabilityDefinitionV1:
    draw = active_draw_capability()
    damage = active_damage_capability()
    key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    claim = _claim(
        kind=RequirementKindV1.DRAW_CARDS,
        family_key=key,
        composition=CompositionClaimV1(
            (
                CompositionComponentV1("draw", draw.capability_ref, True, 0),
                CompositionComponentV1("damage", damage.capability_ref, True, 1),
            )
        ),
    )
    return _definition(claim, display_name="Draw and damage")


def optional_composite_capability() -> CapabilityDefinitionV1:
    draw = active_draw_capability()
    damage = active_damage_capability()
    key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    claim = _claim(
        kind=RequirementKindV1.DRAW_CARDS,
        family_key=key,
        composition=CompositionClaimV1(
            (
                CompositionComponentV1("draw", draw.capability_ref, True, 0),
                CompositionComponentV1("damage", damage.capability_ref, False, 1),
            )
        ),
    )
    return _definition(claim, display_name="Draw and optionally damage")


def second_composite_capability() -> CapabilityDefinitionV1:
    first = composite_capability()
    claim = replace(first.claim, capability_version=2)
    return _definition(claim, display_name="Draw and damage v2")


def mismatched_composite_capability() -> CapabilityDefinitionV1:
    draw = active_draw_capability()
    other_draw = active_draw_capability(version=2)
    key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    claim = _claim(
        kind=RequirementKindV1.DRAW_CARDS,
        family_key=key,
        composition=CompositionClaimV1(
            (
                CompositionComponentV1("first", draw.capability_ref, True, 0),
                CompositionComponentV1("second", other_draw.capability_ref, True, 1),
            )
        ),
    )
    return _definition(claim, display_name="Mismatched composite")


def _evolution_review(
    event: CapabilityEvolutionV1,
    *,
    decision: ReviewDecisionV1 = ReviewDecisionV1.ACCEPTED,
) -> CapabilityReviewRecordV1:
    return CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=EvolutionReviewSubjectV1(
            event.event_id,
            evolution_claim_digest_for(event),
        ),
        decision=decision,
        reviewer_id="maintainer:test",
        generalization_basis=None,
    )


def _requirement(
    *,
    kind: RequirementKindV1,
    source_record_sha256: str,
) -> RequirementV1:
    source = SourceRecordRefV1(
        "census.structural-card.v1",
        "1" * 64,
        "abcdefab-abcd-4abc-8abc-abcdefabcdef",
        "abcdefab-abcd-4abc-8abc-abcdefabcdea",
        source_record_sha256,
    )
    if kind is RequirementKindV1.DRAW_CARDS:
        parameters = DrawCardsParametersV1(
            EntityRefV1(EntityRoleV1.CONTROLLER, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        )
    else:
        parameters = DealDamageParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            EntityRefV1(EntityRoleV1.TARGET, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        )
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=kind,
        parameters=parameters,
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "synthetic"),),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "task6-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.NONE,
            (),
        ),
    )


def _active_member_link(
    requirement: RequirementV1,
    component: CapabilityDefinitionV1,
    composite: CapabilityDefinitionV1,
    component_key: str,
) -> RequirementCapabilityLinkV1:
    admissibility = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )
    proposal = composition_member_link(
        requirement=requirement,
        capability=component,
        m3_manifest_sha256=M3_MANIFEST_SHA256,
        composition_context=CompositionContextV1(
            composite.capability_ref,
            component_key,
        ),
        admissibility=admissibility,
    )
    review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityLinkReviewSubjectV1(
            proposal.link_id,
            proposal.link_claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=None,
    )
    return replace(proposal, review_ref=review.record_id)


def test_composes_edges_are_directional_and_acyclic() -> None:
    composite = composite_capability()
    component = active_draw_capability()
    edge = composes_edge(composite, component)

    assert edge.from_capability == composite.capability_ref
    assert edge.to_capability == component.capability_ref
    assert edge.relation_kind is CapabilityRelationKindV1.COMPOSES
    validate_capability_edges((edge,))


def test_claim_nucleus_kind_and_composition_are_intrinsically_coupled() -> None:
    component = active_draw_capability()
    atomic_composition = CompositionClaimV1(
        (CompositionComponentV1("draw", component.capability_ref, True, 0),)
    )

    with pytest.raises(ValueError, match="ATOMIC.*composition"):
        _claim(kind=RequirementKindV1.DRAW_CARDS, composition=atomic_composition)

    composite_key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    with pytest.raises(ValueError, match="COMPOSITE.*composition"):
        _claim(kind=RequirementKindV1.DRAW_CARDS, family_key=composite_key)


def test_claim_schema_repeats_nucleus_composition_coupling() -> None:
    schema = json.loads(
        (
            Path(__file__).parents[1] / "schemas" / "capability-claim.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    atomic_wire = active_draw_capability().claim.to_wire()
    atomic_wire["composition"] = {
        "components": [
            {
                "component_key": "draw",
                "capability": active_draw_capability().capability_ref.to_wire(),
                "required": True,
                "ordinal": 0,
            }
        ]
    }
    assert list(Draft202012Validator(schema).iter_errors(atomic_wire))

    composite_wire = composite_capability().claim.to_wire()
    composite_wire["composition"] = None
    assert list(Draft202012Validator(schema).iter_errors(composite_wire))


def test_self_edge_and_cycle_fail_closed() -> None:
    capability = active_draw_capability()
    self_edge = requires_edge(capability, capability)

    with pytest.raises(ValueError, match="self-edge"):
        validate_capability_edges((self_edge,))

    other = active_draw_capability(version=2)
    cycle = (
        requires_edge(capability, other),
        requires_edge(other, capability),
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_capability_edges(cycle)


@pytest.mark.parametrize(
    "kind",
    [
        CapabilityRelationKindV1.COMPOSES,
        CapabilityRelationKindV1.REQUIRES,
        CapabilityRelationKindV1.SPECIALIZES,
    ],
)
def test_each_semantic_relation_graph_is_acyclic(
    kind: CapabilityRelationKindV1,
) -> None:
    first = active_draw_capability()
    second = active_damage_capability()
    fields = (
        {"component_key": "part", "ordinal": 0, "required": True}
        if kind is CapabilityRelationKindV1.COMPOSES
        else {}
    )
    first_to_second = CapabilityRelationV1.create(
        relation_kind=kind,
        from_capability=first.capability_ref,
        to_capability=second.capability_ref,
        **fields,
    )
    second_to_first = CapabilityRelationV1.create(
        relation_kind=kind,
        from_capability=second.capability_ref,
        to_capability=first.capability_ref,
        **fields,
    )

    with pytest.raises(ValueError, match="cycle"):
        validate_capability_edges((first_to_second, second_to_first))


def test_relation_wire_identity_is_canonical_and_schema_valid() -> None:
    composite = composite_capability()
    component = active_draw_capability()
    edge = composes_edge(composite, component)

    assert CapabilityRelationV1.from_wire(edge.to_wire()) == edge
    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "schemas"
            / "capability-relations.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(edge.to_wire())


def test_relation_sorting_and_nonsemantic_fields_are_rejected() -> None:
    first = active_draw_capability()
    second = active_damage_capability()
    requires = requires_edge(first, second)
    specializes = specializes_edge(first, second)

    assert sort_capability_relations((specializes, requires)) == tuple(
        sorted((specializes, requires), key=lambda item: item.relation_kind.value)
    )
    wire = requires.to_wire()
    wire["required"] = False
    with pytest.raises(ValueError, match="null component"):
        CapabilityRelationV1.from_wire(wire)


def test_composes_edges_bind_exact_components_and_active_lifecycle() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    edges = (composes_edge(composite, draw), composes_edge(composite, damage))

    validate_capability_edges(edges, capabilities=(composite, draw, damage))

    retired_draw = replace(draw, lifecycle=CapabilityLifecycleStateV1.RETIRED)
    with pytest.raises(ValueError, match="active composite"):
        validate_capability_edges(edges, capabilities=(composite, retired_draw, damage))


def test_composes_relations_cover_optional_components_and_exact_definitions() -> None:
    composite = optional_composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    draw_edge = composes_edge(composite, draw)

    with pytest.raises(ValueError, match="component"):
        validate_capability_edges((draw_edge,), capabilities=(composite, draw))
    with pytest.raises(ValueError, match="complete|optional|component"):
        validate_capability_edges((draw_edge,), capabilities=(composite, draw, damage))

    validate_capability_edges(
        (draw_edge, composes_edge(composite, damage)),
        capabilities=(composite, draw, damage),
    )


def test_composite_operation_anchor_matches_component_nuclei() -> None:
    composite = mismatched_composite_capability()
    draw = active_draw_capability()
    other_draw = active_draw_capability(version=2)
    edges = (
        composes_edge(composite, draw),
        composes_edge(composite, other_draw),
    )

    with pytest.raises(ValueError, match="operation anchor"):
        validate_capability_edges(
            edges,
            capabilities=(composite, draw, other_draw),
        )


def test_active_composite_requires_persisted_required_component_edges() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()

    with pytest.raises(ValueError, match="component"):
        validate_capability_edges((), capabilities=(composite, draw, damage))


def test_all_semantic_relation_kinds_are_typed_and_null_relation_fields_are_exact() -> (
    None
):
    first = active_draw_capability()
    second = active_damage_capability()

    requires = requires_edge(first, second)
    specializes = specializes_edge(first, second)

    assert requires.component_key is None
    assert requires.ordinal is None
    assert requires.required is None
    assert specializes.relation_kind is CapabilityRelationKindV1.SPECIALIZES
    assert specializes.component_key is None
    assert requires.to_wire()["schema"] == "census.capability-relations.v1"


def test_split_preserves_old_references_and_requires_two_targets() -> None:
    old = active_draw_capability()
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)
    event = split_event(old, (first, second), review_ref=REVIEW_REF)

    assert event.operation is EvolutionOperationV1.SPLIT
    assert event.from_references == (old.capability_ref,)
    assert event.to_references == (first.capability_ref, second.capability_ref)

    with pytest.raises(ValueError, match="at least two"):
        split_event(old, (first,), review_ref=REVIEW_REF)


def test_evolution_event_requires_accepted_exact_review_and_schema() -> None:
    old = active_draw_capability()
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)
    draft = split_event(old, (first, second), review_ref=REVIEW_REF)
    review = _evolution_review(draft)
    event = replace(draft, review_ref=review.record_id)

    assert CapabilityEvolutionV1.from_wire(event.to_wire()) == event
    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "schemas"
            / "capability-evolution.v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(event.to_wire())
    validate_evolution_history(
        (event,),
        capabilities=(
            replace(old, lifecycle=CapabilityLifecycleStateV1.SUPERSEDED),
            first,
            second,
        ),
        reviews=(review,),
    )


def test_addition_and_retirement_have_their_exact_history_states() -> None:
    added = active_draw_capability()
    addition_draft = addition_event(added, review_ref=REVIEW_REF)
    addition_review = _evolution_review(addition_draft)
    addition = replace(addition_draft, review_ref=addition_review.record_id)
    validate_evolution_history(
        (addition,),
        capabilities=(added,),
        reviews=(addition_review,),
    )

    retired = replace(
        active_damage_capability(), lifecycle=CapabilityLifecycleStateV1.RETIRED
    )
    retirement_draft = retirement_event(retired, review_ref=REVIEW_REF)
    retirement_review = _evolution_review(retirement_draft)
    retirement = replace(retirement_draft, review_ref=retirement_review.record_id)
    validate_evolution_history(
        (retirement,),
        capabilities=(retired,),
        reviews=(retirement_review,),
    )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda old, first, second: merge_event(
                (old,), first, review_ref=REVIEW_REF
            ),
            "at least two",
        ),
    ],
)
def test_evolution_cardinality_is_exact(factory, message: str) -> None:
    old = active_draw_capability()
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)

    with pytest.raises(ValueError, match=message):
        factory(old, first, second)


def test_supersession_rejects_same_family_version() -> None:
    old = active_draw_capability()
    same_version = active_draw_capability()

    with pytest.raises(ValueError, match="same version"):
        supersession_event(old, same_version, review_ref=REVIEW_REF)


def test_evolution_rejects_stale_endpoint_claim_digest() -> None:
    old = active_draw_capability()
    target = active_draw_capability(version=2)
    valid_event = split_event(
        old,
        (target, active_draw_capability(version=3)),
        review_ref=REVIEW_REF,
    )
    stale = CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.SPLIT,
        from_references=valid_event.from_references,
        to_references=(
            CapabilityRefV1(
                target.capability_family_id,
                target.capability_version,
                "f" * 64,
            ),
            valid_event.to_references[1],
        ),
        review_ref=REVIEW_REF,
    )
    review = _evolution_review(stale)

    with pytest.raises(ValueError, match="exact claim digest"):
        validate_evolution_history(
            (stale,),
            capabilities=(old, target),
            reviews=(review,),
        )


def test_rejected_or_conflicting_evolution_review_cannot_publish_history() -> None:
    old = active_draw_capability()
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)
    draft = split_event(old, (first, second), review_ref=REVIEW_REF)
    accepted = _evolution_review(draft)
    event = replace(draft, review_ref=accepted.record_id)
    rejected = _evolution_review(draft, decision=ReviewDecisionV1.REJECTED)

    with pytest.raises(ValueError, match="conflicting"):
        validate_evolution_history(
            (event,),
            capabilities=(
                replace(old, lifecycle=CapabilityLifecycleStateV1.SUPERSEDED),
                first,
                second,
            ),
            reviews=(accepted, rejected),
        )


def test_evolution_requires_the_old_definition_to_be_historical() -> None:
    old = active_draw_capability()
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)
    draft = split_event(old, (first, second), review_ref=REVIEW_REF)
    review = _evolution_review(draft)
    event = replace(draft, review_ref=review.record_id)

    with pytest.raises(ValueError, match="SUPERSEDED"):
        validate_evolution_history(
            (event,),
            capabilities=(old, first, second),
            reviews=(review,),
        )


def test_evolution_history_rejects_reusing_an_old_endpoint() -> None:
    old = replace(
        active_draw_capability(), lifecycle=CapabilityLifecycleStateV1.SUPERSEDED
    )
    first = active_draw_capability(version=2)
    second = active_draw_capability(version=3)
    third = active_draw_capability(version=4)
    first_draft = split_event(old, (first, second), review_ref=REVIEW_REF)
    second_draft = split_event(old, (first, third), review_ref="mrv_" + "1" * 64)
    first_review = _evolution_review(first_draft)
    second_review = _evolution_review(second_draft)
    first_event = replace(first_draft, review_ref=first_review.record_id)
    second_event = replace(second_draft, review_ref=second_review.record_id)

    with pytest.raises(ValueError, match="duplicate evolution source"):
        validate_evolution_history(
            (first_event, second_event),
            capabilities=(old, first, second, third),
            reviews=(first_review, second_review),
        )


def test_supersession_evolution_cycles_fail_closed() -> None:
    first = replace(
        active_draw_capability(), lifecycle=CapabilityLifecycleStateV1.SUPERSEDED
    )
    second = replace(
        active_damage_capability(), lifecycle=CapabilityLifecycleStateV1.SUPERSEDED
    )
    first_draft = supersession_event(first, second, review_ref=REVIEW_REF)
    second_draft = supersession_event(second, first, review_ref="mrv_" + "1" * 64)
    first_review = _evolution_review(first_draft)
    second_review = _evolution_review(second_draft)
    first_event = replace(first_draft, review_ref=first_review.record_id)
    second_event = replace(second_draft, review_ref=second_review.record_id)

    with pytest.raises(ValueError, match="cycle"):
        validate_evolution_history(
            (first_event, second_event),
            capabilities=(first, second),
            reviews=(first_review, second_review),
        )


def test_addition_and_retirement_cardinalities_are_closed() -> None:
    first = active_draw_capability()
    second = active_draw_capability(version=2)

    with pytest.raises(ValueError, match="no from"):
        CapabilityEvolutionV1.create(
            operation=EvolutionOperationV1.ADDITION,
            from_references=(first.capability_ref,),
            to_references=(second.capability_ref,),
            review_ref=REVIEW_REF,
        )
    with pytest.raises(ValueError, match="no to"):
        CapabilityEvolutionV1.create(
            operation=EvolutionOperationV1.RETIREMENT,
            from_references=(first.capability_ref,),
            to_references=(second.capability_ref,),
            review_ref=REVIEW_REF,
        )


def test_active_composition_context_must_cover_required_components() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    draw_link = _active_member_link(
        _requirement(
            kind=RequirementKindV1.DRAW_CARDS,
            source_record_sha256="2" * 64,
        ),
        draw,
        composite,
        "draw",
    )

    with pytest.raises(ValueError, match="required component"):
        validate_active_links(
            (draw_link,),
            capabilities=(composite, draw, damage),
        )


def test_same_requirement_and_composite_can_cover_two_distinct_components() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    draw_link = _active_member_link(requirement, draw, composite, "draw")
    damage_link = _active_member_link(requirement, damage, composite, "damage")

    validate_active_links(
        (draw_link, damage_link),
        capabilities=(composite, draw, damage),
    )


def test_same_requirement_cannot_mix_different_composite_contexts() -> None:
    first = composite_capability()
    second = second_composite_capability()
    draw = active_draw_capability()
    requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    first_link = _active_member_link(requirement, draw, first, "draw")
    second_link = _active_member_link(requirement, draw, second, "draw")

    with pytest.raises(ValueError, match="same composition context"):
        validate_active_links(
            (first_link, second_link),
            capabilities=(first, second, draw, active_damage_capability()),
        )


def test_same_composite_component_can_be_reused_by_different_requirements() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    first_requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    second_requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="3" * 64,
    )
    first = _active_member_link(
        first_requirement,
        draw,
        composite,
        "draw",
    )
    first_damage = _active_member_link(
        first_requirement,
        damage,
        composite,
        "damage",
    )
    second = _active_member_link(
        second_requirement,
        draw,
        composite,
        "draw",
    )
    second_damage = _active_member_link(
        second_requirement,
        damage,
        composite,
        "damage",
    )

    validate_active_links(
        (first, first_damage, second, second_damage),
        capabilities=(composite, draw, damage),
    )


def test_active_composition_links_match_declared_component_references() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    draw_requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    bad_link = _active_member_link(
        draw_requirement,
        damage,
        composite,
        "draw",
    )

    with pytest.raises(ValueError, match="declared component"):
        validate_active_links(
            (bad_link,),
            capabilities=(composite, draw, damage),
        )


def test_active_composition_context_accepts_each_required_component_once() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    damage = active_damage_capability()
    requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    draw_link = _active_member_link(
        requirement,
        draw,
        composite,
        "draw",
    )
    damage_link = _active_member_link(
        requirement,
        damage,
        composite,
        "damage",
    )

    validate_active_links(
        (draw_link, damage_link),
        capabilities=(composite, draw, damage),
    )


def test_active_component_link_requires_the_selected_composite_definition() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    requirement = _requirement(
        kind=RequirementKindV1.DRAW_CARDS,
        source_record_sha256="2" * 64,
    )
    link = _active_member_link(requirement, draw, composite, "draw")
    link_review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityLinkReviewSubjectV1(
            link.link_id,
            link.link_claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=None,
    )
    admissibility = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )

    with pytest.raises(ValueError, match="composite Capability"):
        validate_active_link(
            link,
            requirement,
            draw,
            reviews=(link_review,),
            admissibility_record=admissibility,
        )


def test_empty_explicit_capability_set_cannot_validate_active_composition() -> None:
    composite = composite_capability()
    draw = active_draw_capability()
    link = _active_member_link(
        _requirement(
            kind=RequirementKindV1.DRAW_CARDS,
            source_record_sha256="2" * 64,
        ),
        draw,
        composite,
        "draw",
    )

    with pytest.raises(ValueError, match="composition .* Capability"):
        validate_active_links((link,), capabilities=())

    with pytest.raises(ValueError, match="composition .* Capability"):
        validate_active_links((link,))


def test_active_composition_link_rejects_a_retired_component_definition() -> None:
    composite = composite_capability()
    retired_draw = replace(
        active_draw_capability(), lifecycle=CapabilityLifecycleStateV1.RETIRED
    )
    link = _active_member_link(
        _requirement(
            kind=RequirementKindV1.DRAW_CARDS,
            source_record_sha256="2" * 64,
        ),
        retired_draw,
        composite,
        "draw",
    )

    with pytest.raises(ValueError, match="active"):
        validate_active_links(
            (link,),
            capabilities=(composite, retired_draw, active_damage_capability()),
        )
