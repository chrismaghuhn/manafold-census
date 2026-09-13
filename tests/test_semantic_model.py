from dataclasses import FrozenInstanceError

import pytest

from manafold_census.semantic.evidence import (
    ExternalReviewEvidenceV1,
    RulesCitationEvidenceV1,
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
)
from manafold_census.semantic.kind_payloads import (
    ApplyContinuousEffectParametersV1,
    DrawCardsParametersV1,
    KeywordReferenceParametersV1,
    ModifyCharacteristicParametersV1,
    ModifyCostParametersV1,
    MoveBetweenZonesParametersV1,
    PayCostParametersV1,
    SelectParametersV1,
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
    CharacteristicNameV1,
    CharacteristicRefV1,
    CostOperationV1,
    DurationKindV1,
    DurationV1,
    EntityRefV1,
    EntityRoleV1,
    ExpansionStateV1,
    ModificationOperationV1,
    MultiplicityV1,
    ParameterValueTypeV1,
    ParameterValueV1,
    QuantityModeV1,
    QuantityV1,
    SemanticDescriptorV1,
    SemanticShapeV1,
    SubjectKindV1,
    UnknownReasonV1,
    UnknownValueV1,
    ZoneNameV1,
    ZoneRefV1,
)

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"


def _source() -> SourceRecordRefV1:
    return SourceRecordRefV1(
        "census.structural-card.v1",
        "a" * 64,
        ORACLE_ID,
        SOURCE_CARD_ID,
        "b" * 64,
    )


def _derivation(
    method: DerivationMethodV1 = DerivationMethodV1.PARSER,
    producer_id: str = "parser",
    producer_version: str = "1",
) -> DerivationV1:
    return DerivationV1(method, producer_id, producer_version)


def _provenance(*derivations: DerivationV1) -> ProvenanceV1:
    return ProvenanceV1(derivations or (_derivation(),))


def _entity(
    role: EntityRoleV1 = EntityRoleV1.SOURCE,
    multiplicity: MultiplicityV1 = MultiplicityV1.ONE,
) -> EntityRefV1:
    return EntityRefV1(role, multiplicity, None)


def _descriptor(
    shape: SemanticShapeV1 = SemanticShapeV1.EFFECT,
) -> SemanticDescriptorV1:
    return SemanticDescriptorV1(shape, None, _entity(), None, None, ())


def _proposal() -> RequirementV1:
    source = _source()
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        ),
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, None),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()
        ),
    )


def _requirement(
    family: RequirementFamilyV1,
    kind: RequirementKindV1,
    parameters: object,
    resolution: ResolutionV1 | None = None,
) -> RequirementV1:
    source = _source()
    return RequirementV1.create(
        source=source,
        family=family,
        kind=kind,
        parameters=parameters,  # type: ignore[arg-type]
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, None),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=resolution
        or ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()),
    )


@pytest.mark.parametrize(
    "build",
    [
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            DrawCardsParametersV1(
                _entity(EntityRoleV1.UNKNOWN), QuantityV1(QuantityModeV1.EXACT, 2)
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            DrawCardsParametersV1(
                _entity(multiplicity=MultiplicityV1.UNKNOWN),
                QuantityV1(QuantityModeV1.EXACT, 2),
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MOVE_BETWEEN_ZONES,
            MoveBetweenZonesParametersV1(
                _entity(),
                ZoneRefV1(ZoneNameV1.UNKNOWN, "custom"),
                ZoneRefV1(ZoneNameV1.HAND, None),
                QuantityV1(QuantityModeV1.EXACT, 1),
                None,
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.CHOICE,
            RequirementKindV1.SELECT,
            SelectParametersV1(
                _entity(),
                SubjectKindV1.UNKNOWN,
                QuantityV1(QuantityModeV1.EXACT, 1),
                _descriptor(SemanticShapeV1.RESTRICTION),
                None,
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MODIFY_CHARACTERISTIC,
            ModifyCharacteristicParametersV1(
                _entity(),
                CharacteristicRefV1(CharacteristicNameV1.POWER, None),
                ModificationOperationV1.UNKNOWN,
                ParameterValueV1(ParameterValueTypeV1.INTEGER, 3),
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.COST,
            RequirementKindV1.MODIFY_COST,
            ModifyCostParametersV1(
                _entity(), _descriptor(SemanticShapeV1.COST), CostOperationV1.UNKNOWN
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1("Flying", 0, ExpansionStateV1.UNKNOWN, None),
        ),
        lambda: _requirement(
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1(
                "Flying", 0, ExpansionStateV1.UNEXPANDED, None
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.COST,
            RequirementKindV1.PAY_COST,
            PayCostParametersV1(
                _entity(),
                SemanticDescriptorV1(
                    SemanticShapeV1.UNKNOWN, None, None, None, None, ()
                ),
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            DrawCardsParametersV1(
                _entity(),
                QuantityV1(
                    QuantityModeV1.UNKNOWN,
                    UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None),
                ),
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MODIFY_CHARACTERISTIC,
            ModifyCharacteristicParametersV1(
                _entity(),
                CharacteristicRefV1(CharacteristicNameV1.POWER, None),
                ModificationOperationV1.SET,
                ParameterValueV1(
                    ParameterValueTypeV1.UNKNOWN,
                    UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None),
                ),
            ),
        ),
        lambda: _requirement(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.APPLY_CONTINUOUS_EFFECT,
            ApplyContinuousEffectParametersV1(
                _entity(),
                DurationV1(
                    DurationKindV1.UNKNOWN,
                    UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None),
                ),
                _descriptor(),
            ),
        ),
    ],
)
def test_complete_rejects_every_semantic_unknown_sentinel(build: object) -> None:
    with pytest.raises(ValueError, match="COMPLETE|unresolved"):
        build()  # type: ignore[operator]


def test_keyword_complete_requires_expanded_typed_expansion() -> None:
    expanded = _requirement(
        RequirementFamilyV1.REFERENCE,
        RequirementKindV1.KEYWORD_REFERENCE,
        KeywordReferenceParametersV1(
            "Flying", 0, ExpansionStateV1.EXPANDED, _descriptor()
        ),
    )
    assert expanded.resolution.state is ResolutionStateV1.COMPLETE

    with pytest.raises(ValueError, match="COMPLETE|unresolved"):
        _requirement(
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1(
                "Flying",
                0,
                ExpansionStateV1.EXPANDED,
                SemanticDescriptorV1(
                    SemanticShapeV1.EFFECT, "only prose", None, None, None, ()
                ),
            ),
        )

    for state in (ExpansionStateV1.UNEXPANDED, ExpansionStateV1.UNKNOWN):
        partial = _requirement(
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1("Flying", 0, state, None),
            ResolutionV1(
                ResolutionStateV1.PARTIAL,
                ResolutionReasonV1.UNKNOWN_SEMANTICS,
                ("/parameters.expansion_state",),
            ),
        )
        assert partial.resolution.state is ResolutionStateV1.PARTIAL


def test_derivation_and_provenance_are_typed_sorted_and_immutable() -> None:
    provenance = _provenance(
        _derivation(DerivationMethodV1.HUMAN_AUTHORED, "human", "1"),
        _derivation(DerivationMethodV1.PARSER, "parser", "1"),
    )

    assert [entry.method for entry in provenance.derivations] == [
        DerivationMethodV1.HUMAN_AUTHORED,
        DerivationMethodV1.PARSER,
    ]
    assert ProvenanceV1.from_wire(provenance.to_wire()) == provenance
    with pytest.raises(FrozenInstanceError):
        provenance.derivations = ()  # type: ignore[misc]


def test_derivation_duplicates_and_invalid_wire_fail_closed() -> None:
    duplicate = _derivation()
    with pytest.raises(ValueError, match="duplicate"):
        ProvenanceV1((duplicate, duplicate))

    wire = _provenance().to_wire()
    wire["extra"] = True
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        ProvenanceV1.from_wire(wire)


def test_review_and_resolution_have_exact_wire_shapes() -> None:
    review = ReviewV1(ReviewStatusV1.IN_REVIEW, None, None)
    resolution = ResolutionV1(
        ResolutionStateV1.PARTIAL,
        ResolutionReasonV1.AMBIGUOUS_SOURCE,
        ("/parameters.subject",),
    )

    assert set(review.to_wire()) == {
        "status",
        "reviewed_by",
        "reviewed_claim_digest",
    }
    assert set(resolution.to_wire()) == {"state", "reason", "unknown_paths"}
    assert ReviewV1.from_wire(review.to_wire()) == review
    assert ResolutionV1.from_wire(resolution.to_wire()) == resolution


def test_identifier_text_and_resolution_paths_are_not_context_bounded() -> None:
    long_identifier = "p" * 4097
    long_path = "/parameters." + "x" * 4097

    derivation = DerivationV1(
        DerivationMethodV1.PARSER, long_identifier, long_identifier
    )
    review = ReviewV1(ReviewStatusV1.ACCEPTED, long_identifier, "a" * 64)
    resolution = ResolutionV1(
        ResolutionStateV1.PARTIAL,
        ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
        (long_path,),
    )

    assert derivation.producer_id == long_identifier
    assert review.reviewed_by == long_identifier
    assert resolution.unknown_paths == (long_path,)


def test_requirement_constructor_and_wire_are_defensive() -> None:
    requirement = _proposal()
    wire = requirement.to_wire()
    wire["evidence"].clear()  # type: ignore[union-attr]
    assert requirement.evidence
    assert requirement.to_wire()["evidence"]

    with pytest.raises(FrozenInstanceError):
        requirement.family = RequirementFamilyV1.UNKNOWN  # type: ignore[misc]


def test_requirement_accepts_closed_evidence_union_and_rejects_duplicates() -> None:
    source = _source()
    evidence = (
        StructuralRecordEvidenceV1(source),
        StructuralFaceEvidenceV1(source, 0),
        StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),
        StructuralKeywordEvidenceV1(source, 0, "Flying"),
        RulesCitationEvidenceV1("rules", "v1", "701.5", None),
        ExternalReviewEvidenceV1("authority", "v1", "record", "c" * 64),
    )
    requirement = RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        ),
        evidence=evidence,
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()
        ),
    )
    assert len(requirement.evidence) == 6

    with pytest.raises(ValueError, match="duplicates"):
        RequirementV1.create(
            source=source,
            family=requirement.family,
            kind=requirement.kind,
            parameters=requirement.parameters,
            evidence=(evidence[0], evidence[0]),
            provenance=requirement.provenance,
            review=requirement.review,
            resolution=requirement.resolution,
        )


def test_resolution_state_rejects_inconsistent_paths_and_reasons() -> None:
    with pytest.raises(ValueError, match="unknown_paths|COMPLETE"):
        ResolutionV1(
            ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.NONE,
            ("/parameters",),
        )
    with pytest.raises(ValueError, match="reason|PARTIAL"):
        ResolutionV1(
            ResolutionStateV1.PARTIAL, ResolutionReasonV1.NONE, ("/parameters",)
        )


@pytest.mark.parametrize("path", ["/x", "/review", "/evidence", "/unrelated"])
def test_resolution_paths_are_scoped_to_kind_or_parameters(path: str) -> None:
    with pytest.raises(ValueError, match="kind|parameters|path"):
        ResolutionV1(
            ResolutionStateV1.PARTIAL,
            ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
            (path,),
        )

    for valid_path in ("/kind", "/parameters", "/parameters.quantity.value"):
        resolution = ResolutionV1(
            ResolutionStateV1.PARTIAL,
            ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
            (valid_path,),
        )
        assert resolution.unknown_paths == (valid_path,)
