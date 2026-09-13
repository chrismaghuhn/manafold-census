import pytest

from manafold_census.semantic.bundle import (
    RelationshipTypeV1,
    RequirementBundleV1,
    RequirementRelationshipV1,
    bundle_digest_for,
)
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.kind_payloads import (
    DrawCardsParametersV1,
    PayCostParametersV1,
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
    SemanticDescriptorV1,
    SemanticShapeV1,
)
from manafold_census.validation import validate_document

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"


def _source(lock: str = "a") -> SourceRecordRefV1:
    return SourceRecordRefV1(
        "census.structural-card.v1",
        lock * 64,
        ORACLE_ID,
        SOURCE_CARD_ID,
        "b" * 64,
    )


def _entity(role: EntityRoleV1 = EntityRoleV1.SOURCE) -> EntityRefV1:
    return EntityRefV1(role, MultiplicityV1.ONE, None)


def _descriptor() -> SemanticDescriptorV1:
    return SemanticDescriptorV1(SemanticShapeV1.EFFECT, None, _entity(), None, None, ())


def _provenance() -> ProvenanceV1:
    return ProvenanceV1((DerivationV1(DerivationMethodV1.PARSER, "parser", "1"),))


def _requirement(
    source: SourceRecordRefV1,
    kind: RequirementKindV1,
    parameters: object,
    *,
    evidence_field: str = "oracle_text",
) -> RequirementV1:
    family = (
        RequirementFamilyV1.EFFECT
        if kind is RequirementKindV1.DRAW_CARDS
        else RequirementFamilyV1.COST
    )
    return RequirementV1.create(
        source=source,
        family=family,
        kind=kind,
        parameters=parameters,  # type: ignore[arg-type]
        evidence=(StructuralFieldEvidenceV1(source, evidence_field, None, None),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()
        ),
    )


def _draw(
    source: SourceRecordRefV1, evidence_field: str = "oracle_text"
) -> RequirementV1:
    return _requirement(
        source,
        RequirementKindV1.DRAW_CARDS,
        DrawCardsParametersV1(_entity(), QuantityV1(QuantityModeV1.EXACT, 2)),
        evidence_field=evidence_field,
    )


def _cost(source: SourceRecordRefV1) -> RequirementV1:
    return _requirement(
        source,
        RequirementKindV1.PAY_COST,
        PayCostParametersV1(_entity(EntityRoleV1.PAYER), _descriptor()),
    )


def _bundle(
    source: SourceRecordRefV1,
    requirements: tuple[RequirementV1, ...],
    relationships: tuple[RequirementRelationshipV1, ...] = (),
) -> RequirementBundleV1:
    return RequirementBundleV1(source, requirements, relationships)


def test_relationship_vocabulary_and_wire_round_trip() -> None:
    source = _source()
    first = _draw(source)
    second = _cost(source)
    relationship = RequirementRelationshipV1(
        RelationshipTypeV1.SEQUENCE_BEFORE,
        first.requirement_id,
        second.requirement_id,
        0,
    )

    assert {item.value for item in RelationshipTypeV1} == {
        "PARENT_OF",
        "ALTERNATIVE_OF",
        "CONDITION_OF",
        "COST_OF",
        "SEQUENCE_BEFORE",
        "CONFLICTS_WITH",
        "SUPERSEDES",
    }
    assert RequirementRelationshipV1.from_wire(relationship.to_wire()) == relationship


def test_empty_relationship_bundle_round_trips_and_hashes() -> None:
    source = _source()
    requirements = tuple(
        sorted((_draw(source), _cost(source)), key=lambda item: item.requirement_id)
    )
    bundle = _bundle(source, requirements)

    assert set(bundle.to_wire()) == {
        "schema",
        "source",
        "requirements",
        "relationships",
    }
    assert RequirementBundleV1.from_wire(bundle.to_wire()) == bundle
    assert bundle_digest_for(bundle) == bundle_digest_for(bundle)
    validate_document(bundle.to_wire(), "semantic-requirement-bundle.v1.schema.json")


def test_modal_parent_and_symmetric_alternative_relationships_canonicalize() -> None:
    source = _source()
    parent = _draw(source)
    branch = _cost(source)
    first, second = sorted((parent.requirement_id, branch.requirement_id))
    alternative = RequirementRelationshipV1(
        RelationshipTypeV1.ALTERNATIVE_OF, second, first, None
    )
    parent_edge = RequirementRelationshipV1(
        RelationshipTypeV1.PARENT_OF, parent.requirement_id, branch.requirement_id, 0
    )
    bundle = _bundle(
        source,
        tuple(sorted((parent, branch), key=lambda item: item.requirement_id)),
        (alternative, parent_edge),
    )

    assert (alternative.from_requirement_id, alternative.to_requirement_id) == (
        first,
        second,
    )
    assert (
        bundle.relationships[0].relationship_type is RelationshipTypeV1.ALTERNATIVE_OF
    )

    wire = alternative.to_wire()
    wire["from"], wire["to"] = wire["to"], wire["from"]
    with pytest.raises(ValueError, match="canonical"):
        RequirementRelationshipV1.from_wire(wire)


def test_all_relationship_types_validate_with_required_ordinal_rules() -> None:
    source = _source()
    requirements = tuple(
        sorted((_draw(source), _cost(source)), key=lambda item: item.requirement_id)
    )
    first, second = (item.requirement_id for item in requirements)
    relationships = (
        RequirementRelationshipV1(RelationshipTypeV1.PARENT_OF, first, second, None),
        RequirementRelationshipV1(RelationshipTypeV1.CONDITION_OF, first, second, None),
        RequirementRelationshipV1(RelationshipTypeV1.COST_OF, first, second, None),
        RequirementRelationshipV1(RelationshipTypeV1.SEQUENCE_BEFORE, first, second, 0),
        RequirementRelationshipV1(
            RelationshipTypeV1.CONFLICTS_WITH, first, second, None
        ),
        RequirementRelationshipV1(RelationshipTypeV1.SUPERSEDES, first, second, None),
        RequirementRelationshipV1(
            RelationshipTypeV1.ALTERNATIVE_OF, first, second, None
        ),
    )

    bundle = _bundle(source, requirements, relationships)
    assert len(bundle.relationships) == 7
    validate_document(bundle.to_wire(), "semantic-requirement-bundle.v1.schema.json")


def test_bundle_rejects_cross_source_unsorted_duplicate_and_missing_edges() -> None:
    source = _source()
    other_source = _source("c")
    first = _draw(source)
    second = _cost(source)
    ordered = tuple(sorted((first, second), key=lambda item: item.requirement_id))

    with pytest.raises(ValueError, match="source"):
        _bundle(source, (first, _cost(other_source)))
    with pytest.raises(ValueError, match="sorted"):
        _bundle(source, tuple(reversed(ordered)))
    with pytest.raises(ValueError, match="duplicate"):
        _bundle(source, (first, first))
    missing = RequirementRelationshipV1(
        RelationshipTypeV1.PARENT_OF, first.requirement_id, "srq_" + "f" * 64, None
    )
    with pytest.raises(ValueError, match="endpoint"):
        _bundle(source, ordered, (missing,))


def test_bundle_rejects_exact_duplicate_relationship_edges() -> None:
    source = _source()
    first = _draw(source)
    second = _cost(source)
    requirements = tuple(sorted((first, second), key=lambda item: item.requirement_id))
    edge = RequirementRelationshipV1(
        RelationshipTypeV1.PARENT_OF,
        first.requirement_id,
        second.requirement_id,
        None,
    )

    with pytest.raises(ValueError, match="duplicate"):
        _bundle(source, requirements, (edge, edge))


def test_bundle_rejects_reverse_symmetric_duplicate_after_canonicalization() -> None:
    source = _source()
    first = _draw(source)
    second = _cost(source)
    requirements = tuple(sorted((first, second), key=lambda item: item.requirement_id))
    forward = RequirementRelationshipV1(
        RelationshipTypeV1.ALTERNATIVE_OF,
        first.requirement_id,
        second.requirement_id,
        None,
    )
    reverse = RequirementRelationshipV1(
        RelationshipTypeV1.ALTERNATIVE_OF,
        second.requirement_id,
        first.requirement_id,
        None,
    )

    assert forward == reverse
    with pytest.raises(ValueError, match="duplicate"):
        _bundle(source, requirements, (forward, reverse))


def test_bundle_rejects_self_edges_bad_ordinals_and_arbitrary_relationships() -> None:
    source = _source()
    first = _draw(source)
    requirements = (first,)

    with pytest.raises(ValueError, match="self"):
        _bundle(
            source,
            requirements,
            (
                RequirementRelationshipV1(
                    RelationshipTypeV1.PARENT_OF,
                    first.requirement_id,
                    first.requirement_id,
                    None,
                ),
            ),
        )
    with pytest.raises((TypeError, ValueError), match="ordinal"):
        RequirementRelationshipV1(
            RelationshipTypeV1.SEQUENCE_BEFORE,
            first.requirement_id,
            "srq_" + "f" * 64,
            None,
        )
    with pytest.raises((TypeError, ValueError), match="non-negative|ordinal"):
        RequirementRelationshipV1(
            RelationshipTypeV1.PARENT_OF,
            first.requirement_id,
            "srq_" + "f" * 64,
            -1,
        )
    wire = _bundle(source, requirements).to_wire()
    wire["relationships"] = [
        {
            "type": "CAPABILITY_EDGE",
            "from": first.requirement_id,
            "to": first.requirement_id,
            "ordinal": None,
        }
    ]
    with pytest.raises((TypeError, ValueError), match="relationship|type"):
        RequirementBundleV1.from_wire(wire)


def test_parent_and_supersedes_cycles_are_rejected() -> None:
    source = _source()
    first = _draw(source)
    second = _cost(source)
    requirements = tuple(sorted((first, second), key=lambda item: item.requirement_id))
    first_id, second_id = (item.requirement_id for item in requirements)

    for relationship_type in (
        RelationshipTypeV1.PARENT_OF,
        RelationshipTypeV1.SUPERSEDES,
    ):
        edges = (
            RequirementRelationshipV1(relationship_type, first_id, second_id, None),
            RequirementRelationshipV1(relationship_type, second_id, first_id, None),
        )
        with pytest.raises(ValueError, match="cycle"):
            _bundle(source, requirements, edges)


def test_coalescing_watchpoint_reconciles_duplicate_claims() -> None:
    source = _source()
    first = _draw(source, "oracle_text")
    second = _draw(source, "type_line")
    requirements = tuple(sorted((first, second), key=lambda item: item.requirement_id))

    assert first.requirement_id == second.requirement_id
    with pytest.raises(ValueError, match="duplicate"):
        _bundle(source, requirements)

    reconciled = RequirementV1.create(
        source=source,
        family=first.family,
        kind=first.kind,
        parameters=first.parameters,
        evidence=first.evidence + second.evidence,
        provenance=first.provenance,
        review=first.review,
        resolution=first.resolution,
    )
    valid = _bundle(source, (reconciled,))
    assert len(valid.requirements) == 1


def test_supersedes_edge_does_not_mutate_endpoint_review_status() -> None:
    source = _source()
    first = _draw(source)
    second = _cost(source)
    requirements = tuple(sorted((first, second), key=lambda item: item.requirement_id))
    edge = RequirementRelationshipV1(
        RelationshipTypeV1.SUPERSEDES,
        second.requirement_id,
        first.requirement_id,
        None,
    )

    bundle = _bundle(source, requirements, (edge,))
    assert {item.review.status for item in bundle.requirements} == {
        ReviewStatusV1.PROPOSED
    }


def test_bundle_wire_rejects_unknown_root_and_nested_properties() -> None:
    source = _source()
    requirement = _draw(source)
    bundle = _bundle(source, (requirement,))
    wire = bundle.to_wire()
    wire["extra"] = True
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        RequirementBundleV1.from_wire(wire)

    wire = bundle.to_wire()
    wire["relationships"] = [
        {
            "type": "PARENT_OF",
            "from": requirement.requirement_id,
            "to": requirement.requirement_id,
            "ordinal": None,
            "extra": True,
        }
    ]
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        RequirementBundleV1.from_wire(wire)
