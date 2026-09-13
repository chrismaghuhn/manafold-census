import json

import pytest

from manafold_census.resources import project_data_root
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
    ChooseModeParametersV1,
    ConditionalEffectParametersV1,
    CreateDelayedEffectParametersV1,
    CreateObjectParametersV1,
    DealDamageParametersV1,
    DrawCardsParametersV1,
    KeywordReferenceParametersV1,
    ModifyCharacteristicParametersV1,
    ModifyCostParametersV1,
    MoveBetweenZonesParametersV1,
    PayCostParametersV1,
    ReplaceEventParametersV1,
    SearchZoneParametersV1,
    SelectParametersV1,
    TriggerFromEventParametersV1,
    UnresolvedParametersV1,
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
from manafold_census.validation import SchemaValidationError, validate_document

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
SOURCE_LOCK_DIGEST = "a" * 64
SOURCE_RECORD_SHA256 = "b" * 64


def _source() -> SourceRecordRefV1:
    return SourceRecordRefV1(
        "census.structural-card.v1",
        SOURCE_LOCK_DIGEST,
        ORACLE_ID,
        SOURCE_CARD_ID,
        SOURCE_RECORD_SHA256,
    )


def _entity(role: EntityRoleV1 = EntityRoleV1.SOURCE) -> EntityRefV1:
    return EntityRefV1(role, MultiplicityV1.ONE, None)


def _descriptor(
    shape: SemanticShapeV1 = SemanticShapeV1.EFFECT,
) -> SemanticDescriptorV1:
    return SemanticDescriptorV1(shape, None, _entity(), None, None, ())


def _text_value(value: str = "token") -> ParameterValueV1:
    return ParameterValueV1(ParameterValueTypeV1.TEXT, value)


def _provenance() -> ProvenanceV1:
    return ProvenanceV1((DerivationV1(DerivationMethodV1.PARSER, "parser", "1"),))


def _complete() -> ResolutionV1:
    return ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ())


def _proposal(
    family: RequirementFamilyV1,
    kind: RequirementKindV1,
    parameters: object,
    *,
    evidence: tuple[object, ...] | None = None,
    resolution: ResolutionV1 | None = None,
) -> RequirementV1:
    source = _source()
    return RequirementV1.create(
        source=source,
        family=family,
        kind=kind,
        parameters=parameters,  # type: ignore[arg-type]
        evidence=evidence
        or (StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=resolution or _complete(),
    )


def _requirements() -> dict[str, RequirementV1]:
    descriptor = _descriptor()
    return {
        "move_between_zones": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MOVE_BETWEEN_ZONES,
            MoveBetweenZonesParametersV1(
                _entity(),
                ZoneRefV1(ZoneNameV1.LIBRARY, None),
                ZoneRefV1(ZoneNameV1.HAND, None),
                QuantityV1(QuantityModeV1.EXACT, 1),
                None,
            ),
        ),
        "create_object": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.CREATE_OBJECT,
            CreateObjectParametersV1(
                _text_value(), QuantityV1(QuantityModeV1.EXACT, 1), (), None
            ),
        ),
        "select": _proposal(
            RequirementFamilyV1.CHOICE,
            RequirementKindV1.SELECT,
            SelectParametersV1(
                _entity(EntityRoleV1.CHOOSER),
                SubjectKindV1.OBJECT,
                QuantityV1(QuantityModeV1.EXACT, 1),
                descriptor,
                None,
            ),
        ),
        "modify_characteristic": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MODIFY_CHARACTERISTIC,
            ModifyCharacteristicParametersV1(
                _entity(),
                CharacteristicRefV1(CharacteristicNameV1.POWER, None),
                ModificationOperationV1.SET,
                ParameterValueV1(ParameterValueTypeV1.INTEGER, 3),
            ),
        ),
        "apply_continuous_effect": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.APPLY_CONTINUOUS_EFFECT,
            ApplyContinuousEffectParametersV1(
                _entity(), DurationV1(DurationKindV1.PERMANENT, None), descriptor
            ),
        ),
        "search_zone": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.SEARCH_ZONE,
            SearchZoneParametersV1(
                _entity(),
                ZoneRefV1(ZoneNameV1.LIBRARY, None),
                descriptor,
                None,
                None,
            ),
        ),
        "draw_cards": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            DrawCardsParametersV1(_entity(), QuantityV1(QuantityModeV1.EXACT, 2)),
        ),
        "deal_damage": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DEAL_DAMAGE,
            DealDamageParametersV1(
                _entity(),
                _entity(EntityRoleV1.TARGET),
                QuantityV1(QuantityModeV1.EXACT, 1),
            ),
        ),
        "create_delayed_effect": _proposal(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.CREATE_DELAYED_EFFECT,
            CreateDelayedEffectParametersV1(descriptor, descriptor),
        ),
        "trigger_from_event": _proposal(
            RequirementFamilyV1.EVENT,
            RequirementKindV1.TRIGGER_FROM_EVENT,
            TriggerFromEventParametersV1(
                descriptor, _entity(EntityRoleV1.CONTROLLER), None
            ),
        ),
        "replace_event": _proposal(
            RequirementFamilyV1.EVENT,
            RequirementKindV1.REPLACE_EVENT,
            ReplaceEventParametersV1(descriptor, descriptor),
        ),
        "pay_cost": _proposal(
            RequirementFamilyV1.COST,
            RequirementKindV1.PAY_COST,
            PayCostParametersV1(_entity(EntityRoleV1.PAYER), descriptor),
        ),
        "modify_cost": _proposal(
            RequirementFamilyV1.COST,
            RequirementKindV1.MODIFY_COST,
            ModifyCostParametersV1(_entity(), descriptor, CostOperationV1.DECREASE),
        ),
        "choose_mode": _proposal(
            RequirementFamilyV1.CHOICE,
            RequirementKindV1.CHOOSE_MODE,
            ChooseModeParametersV1(
                _entity(EntityRoleV1.CHOOSER),
                QuantityV1(QuantityModeV1.EXACT, 1),
                QuantityV1(QuantityModeV1.EXACT, 2),
                (descriptor,),
            ),
        ),
        "conditional_effect": _proposal(
            RequirementFamilyV1.CONTROL,
            RequirementKindV1.CONDITIONAL_EFFECT,
            ConditionalEffectParametersV1(descriptor, descriptor, None),
        ),
        "keyword_reference": _proposal(
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1(
                "Flying", 0, ExpansionStateV1.UNEXPANDED, None
            ),
        ),
        "unresolved": _proposal(
            RequirementFamilyV1.UNKNOWN,
            RequirementKindV1.UNRESOLVED,
            UnresolvedParametersV1(
                "oracle_text",
                SemanticShapeV1.UNKNOWN,
                "What does this text require?",
                (),
                None,
            ),
            resolution=ResolutionV1(
                ResolutionStateV1.UNRESOLVED,
                ResolutionReasonV1.UNSUPPORTED_SHAPE,
                ("/parameters",),
            ),
        ),
    }


def test_requirement_schema_is_present_and_is_not_the_bundle_schema() -> None:
    root = project_data_root()
    schema_path = root / "schemas" / "semantic-requirement.v1.schema.json"
    assert schema_path.is_file()
    assert not (
        root / "schemas" / "semantic-requirement-bundle.v1.schema.json"
    ).exists()

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert (
        schema["$id"]
        == "https://manafold-census.invalid/schemas/semantic-requirement.v1.schema.json"
    )
    assert schema["additionalProperties"] is False


def test_every_kind_branch_matches_the_immutable_model() -> None:
    requirements = _requirements()

    assert {requirement.kind.value for requirement in requirements.values()} == {
        kind.value for kind in RequirementKindV1
    }
    for requirement in requirements.values():
        validate_document(requirement.to_wire(), "semantic-requirement.v1.schema.json")
        assert RequirementV1.from_wire(requirement.to_wire()) == requirement


def test_partial_and_unresolved_requirement_wires_validate() -> None:
    partial = _proposal(
        RequirementFamilyV1.EFFECT,
        RequirementKindV1.DRAW_CARDS,
        DrawCardsParametersV1(
            _entity(),
            QuantityV1(
                QuantityModeV1.UNKNOWN,
                UnknownValueV1(UnknownReasonV1.INSUFFICIENT_EVIDENCE, "quantity"),
            ),
        ),
        resolution=ResolutionV1(
            ResolutionStateV1.PARTIAL,
            ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
            ("/parameters.quantity.value",),
        ),
    )

    validate_document(partial.to_wire(), "semantic-requirement.v1.schema.json")
    validate_document(
        _requirements()["unresolved"].to_wire(),
        "semantic-requirement.v1.schema.json",
    )


def test_all_evidence_variants_validate_in_one_requirement() -> None:
    source = _source()
    requirement = _proposal(
        RequirementFamilyV1.EFFECT,
        RequirementKindV1.DRAW_CARDS,
        DrawCardsParametersV1(_entity(), QuantityV1(QuantityModeV1.EXACT, 2)),
        evidence=(
            StructuralRecordEvidenceV1(source),
            StructuralFaceEvidenceV1(source, 0),
            StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),
            StructuralKeywordEvidenceV1(source, 0, "Flying"),
            RulesCitationEvidenceV1("rules", "v1", "701.5", None),
            ExternalReviewEvidenceV1("authority", "v1", "record", "c" * 64),
        ),
    )

    validate_document(requirement.to_wire(), "semantic-requirement.v1.schema.json")


def test_schema_rejects_unknown_properties_and_wrong_schema() -> None:
    wire = _requirements()["draw_cards"].to_wire()
    wire["extra"] = True
    with pytest.raises(SchemaValidationError, match="additional properties"):
        validate_document(wire, "semantic-requirement.v1.schema.json")

    wire = _requirements()["draw_cards"].to_wire()
    wire["schema"] = "census.semantic-requirement.v2"
    with pytest.raises(SchemaValidationError, match="schema"):
        validate_document(wire, "semantic-requirement.v1.schema.json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("oracle_id", "not-a-uuid"),
        ("source_record_sha256", "not-a-digest"),
        ("kind", "draw_cards"),
        ("family", "choice"),
    ],
)
def test_schema_rejects_invalid_source_and_kind_family_branch(
    field: str, value: str
) -> None:
    wire = _requirements()["move_between_zones"].to_wire()
    if field in {"kind", "family"}:
        wire[field] = value
    else:
        wire["source"][field] = value  # type: ignore[index]

    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")


@pytest.mark.parametrize(
    "review",
    [
        {"status": "ACCEPTED", "reviewed_by": None, "reviewed_claim_digest": None},
        {
            "status": "REJECTED",
            "reviewed_by": "reviewer",
            "reviewed_claim_digest": None,
        },
    ],
)
def test_schema_rejects_terminal_review_without_binding(
    review: dict[str, object],
) -> None:
    wire = _requirements()["draw_cards"].to_wire()
    wire["review"] = review

    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")


def test_schema_rejects_label_only_complete_descriptor() -> None:
    label_only = SemanticDescriptorV1(
        SemanticShapeV1.EFFECT, "only prose", None, None, None, ()
    )
    partial = _proposal(
        RequirementFamilyV1.COST,
        RequirementKindV1.PAY_COST,
        PayCostParametersV1(_entity(EntityRoleV1.PAYER), label_only),
        resolution=ResolutionV1(
            ResolutionStateV1.PARTIAL,
            ResolutionReasonV1.UNSUPPORTED_SHAPE,
            ("/parameters.cost",),
        ),
    )
    wire = partial.to_wire()
    wire["resolution"] = {
        "state": "COMPLETE",
        "reason": "NONE",
        "unknown_paths": [],
    }

    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")


def test_schema_rejects_unknown_enum_float_and_negative_index() -> None:
    wire = _requirements()["draw_cards"].to_wire()
    wire["family"] = "not-a-family"
    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")

    wire = _requirements()["draw_cards"].to_wire()
    wire["parameters"]["quantity"]["value"] = 1.5  # type: ignore[index]
    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")

    wire = _requirements()["draw_cards"].to_wire()
    keyword = {
        "kind": "STRUCTURAL_KEYWORD",
        "source": _source().to_wire(),
        "keyword_index": -1,
        "keyword_value": "Flying",
    }
    wire["evidence"] = [keyword]
    with pytest.raises(SchemaValidationError):
        validate_document(wire, "semantic-requirement.v1.schema.json")
