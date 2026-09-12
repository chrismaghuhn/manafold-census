import pytest

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
    payload_from_wire,
    payload_to_wire,
)
from manafold_census.semantic.kinds import (
    KIND_FAMILY,
    PAYLOAD_OPTIONAL_KEYS,
    PAYLOAD_REQUIRED_KEYS,
    RequirementFamilyV1,
    RequirementKindV1,
    family_for_kind,
    validate_kind_family,
)
from manafold_census.semantic.primitives import (
    CharacteristicAssignmentV1,
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


def _entity(role: EntityRoleV1) -> EntityRefV1:
    return EntityRefV1(role, MultiplicityV1.ONE, None)


def _descriptor(shape: SemanticShapeV1) -> SemanticDescriptorV1:
    return SemanticDescriptorV1(shape, None, None, None, None, ())


def _quantity() -> QuantityV1:
    return QuantityV1(QuantityModeV1.EXACT, 1)


def test_v1_family_and_kind_vocabularies_are_exact() -> None:
    assert set(RequirementFamilyV1) == {
        RequirementFamilyV1.EFFECT,
        RequirementFamilyV1.EVENT,
        RequirementFamilyV1.CHOICE,
        RequirementFamilyV1.COST,
        RequirementFamilyV1.CONTROL,
        RequirementFamilyV1.REFERENCE,
        RequirementFamilyV1.UNKNOWN,
    }
    assert set(RequirementKindV1) == {
        RequirementKindV1.MOVE_BETWEEN_ZONES,
        RequirementKindV1.CREATE_OBJECT,
        RequirementKindV1.SELECT,
        RequirementKindV1.MODIFY_CHARACTERISTIC,
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT,
        RequirementKindV1.SEARCH_ZONE,
        RequirementKindV1.DRAW_CARDS,
        RequirementKindV1.DEAL_DAMAGE,
        RequirementKindV1.CREATE_DELAYED_EFFECT,
        RequirementKindV1.TRIGGER_FROM_EVENT,
        RequirementKindV1.REPLACE_EVENT,
        RequirementKindV1.PAY_COST,
        RequirementKindV1.MODIFY_COST,
        RequirementKindV1.CHOOSE_MODE,
        RequirementKindV1.CONDITIONAL_EFFECT,
        RequirementKindV1.KEYWORD_REFERENCE,
        RequirementKindV1.UNRESOLVED,
    }
    assert set(KIND_FAMILY) == set(RequirementKindV1)


def test_every_kind_maps_to_one_closed_family() -> None:
    for kind in RequirementKindV1:
        family = family_for_kind(kind)
        assert KIND_FAMILY[kind] == family
        validate_kind_family(family, kind)

    with pytest.raises(ValueError, match="family"):
        validate_kind_family(RequirementFamilyV1.COST, RequirementKindV1.DRAW_CARDS)


def test_payload_key_registry_is_closed_and_matches_design() -> None:
    required = {
        RequirementKindV1.MOVE_BETWEEN_ZONES: {
            "subject",
            "from_zone",
            "to_zone",
            "quantity",
        },
        RequirementKindV1.CREATE_OBJECT: {
            "object_class",
            "quantity",
            "characteristics",
        },
        RequirementKindV1.SELECT: {
            "chooser",
            "subject_kind",
            "quantity",
            "restriction",
        },
        RequirementKindV1.MODIFY_CHARACTERISTIC: {
            "subject",
            "characteristic",
            "operation",
            "value",
        },
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT: {"subject", "duration", "effect"},
        RequirementKindV1.SEARCH_ZONE: {"searcher", "zone", "selection"},
        RequirementKindV1.DRAW_CARDS: {"drawer", "quantity"},
        RequirementKindV1.DEAL_DAMAGE: {"source", "recipient", "amount"},
        RequirementKindV1.CREATE_DELAYED_EFFECT: {"delay", "effect"},
        RequirementKindV1.TRIGGER_FROM_EVENT: {"event", "controller"},
        RequirementKindV1.REPLACE_EVENT: {"event", "replacement"},
        RequirementKindV1.PAY_COST: {"payer", "cost"},
        RequirementKindV1.MODIFY_COST: {"subject", "cost", "operation"},
        RequirementKindV1.CHOOSE_MODE: {
            "chooser",
            "minimum",
            "maximum",
            "alternatives",
        },
        RequirementKindV1.CONDITIONAL_EFFECT: {"condition", "then_effect"},
        RequirementKindV1.KEYWORD_REFERENCE: {
            "keyword",
            "keyword_index",
            "expansion_state",
        },
        RequirementKindV1.UNRESOLVED: {
            "observed_field",
            "observed_shape",
            "question",
            "candidate_kinds",
        },
    }
    optional = {
        RequirementKindV1.MOVE_BETWEEN_ZONES: {"cause"},
        RequirementKindV1.CREATE_OBJECT: {"duration"},
        RequirementKindV1.SELECT: {"targeting"},
        RequirementKindV1.MODIFY_CHARACTERISTIC: set(),
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT: set(),
        RequirementKindV1.SEARCH_ZONE: {"destination", "reveal"},
        RequirementKindV1.DRAW_CARDS: set(),
        RequirementKindV1.DEAL_DAMAGE: set(),
        RequirementKindV1.CREATE_DELAYED_EFFECT: set(),
        RequirementKindV1.TRIGGER_FROM_EVENT: {"condition"},
        RequirementKindV1.REPLACE_EVENT: set(),
        RequirementKindV1.PAY_COST: set(),
        RequirementKindV1.MODIFY_COST: set(),
        RequirementKindV1.CHOOSE_MODE: set(),
        RequirementKindV1.CONDITIONAL_EFFECT: {"else_effect"},
        RequirementKindV1.KEYWORD_REFERENCE: {"expansion"},
        RequirementKindV1.UNRESOLVED: {"fragment"},
    }
    assert dict(PAYLOAD_REQUIRED_KEYS) == {
        key: frozenset(value) for key, value in required.items()
    }
    assert dict(PAYLOAD_OPTIONAL_KEYS) == {
        key: frozenset(value) for key, value in optional.items()
    }
    assert set(PAYLOAD_REQUIRED_KEYS) == set(RequirementKindV1)
    assert set(PAYLOAD_OPTIONAL_KEYS) == set(RequirementKindV1)


def test_representative_payloads_round_trip_through_typed_dispatch() -> None:
    move = MoveBetweenZonesParametersV1(
        subject=_entity(EntityRoleV1.TARGET),
        from_zone=ZoneRefV1(ZoneNameV1.BATTLEFIELD, None),
        to_zone=ZoneRefV1(ZoneNameV1.GRAVEYARD, None),
        quantity=_quantity(),
        cause=None,
    )
    create = CreateObjectParametersV1(
        object_class=ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
        quantity=_quantity(),
        characteristics=(),
        duration=None,
    )
    draw = DrawCardsParametersV1(
        drawer=_entity(EntityRoleV1.CONTROLLER),
        quantity=_quantity(),
    )
    delayed = CreateDelayedEffectParametersV1(
        delay=_descriptor(SemanticShapeV1.DURATION),
        effect=_descriptor(SemanticShapeV1.EFFECT),
    )
    unresolved = UnresolvedParametersV1(
        observed_field="oracle_text",
        observed_shape=SemanticShapeV1.UNKNOWN,
        question="which typed shape applies",
        candidate_kinds=(RequirementKindV1.DRAW_CARDS,),
        fragment="raw fragment",
    )

    values = (
        (RequirementFamilyV1.EFFECT, RequirementKindV1.MOVE_BETWEEN_ZONES, move),
        (RequirementFamilyV1.EFFECT, RequirementKindV1.CREATE_OBJECT, create),
        (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS, draw),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.CREATE_DELAYED_EFFECT,
            delayed,
        ),
        (RequirementFamilyV1.UNKNOWN, RequirementKindV1.UNRESOLVED, unresolved),
    )

    for family, kind, payload in values:
        wire = payload_to_wire(family, kind, payload)
        assert payload_from_wire(family, kind, wire) == payload


def test_every_payload_class_round_trips_through_typed_dispatch() -> None:
    target = _entity(EntityRoleV1.TARGET)
    descriptor = _descriptor(SemanticShapeV1.EFFECT)
    characteristic = CharacteristicRefV1(CharacteristicNameV1.POWER, None)
    assignment = CharacteristicAssignmentV1(
        characteristic=characteristic,
        value=ParameterValueV1(ParameterValueTypeV1.INTEGER, 3),
    )
    values = (
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MOVE_BETWEEN_ZONES,
            MoveBetweenZonesParametersV1(
                target,
                ZoneRefV1(ZoneNameV1.BATTLEFIELD, None),
                ZoneRefV1(ZoneNameV1.GRAVEYARD, None),
                _quantity(),
                None,
            ),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.CREATE_OBJECT,
            CreateObjectParametersV1(
                ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
                _quantity(),
                (assignment,),
                DurationV1(DurationKindV1.PERMANENT, None),
            ),
        ),
        (
            RequirementFamilyV1.CHOICE,
            RequirementKindV1.SELECT,
            SelectParametersV1(
                _entity(EntityRoleV1.CHOOSER),
                SubjectKindV1.OBJECT,
                _quantity(),
                descriptor,
                False,
            ),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.MODIFY_CHARACTERISTIC,
            ModifyCharacteristicParametersV1(
                target,
                characteristic,
                ModificationOperationV1.SET,
                ParameterValueV1(ParameterValueTypeV1.INTEGER, 2),
            ),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.APPLY_CONTINUOUS_EFFECT,
            ApplyContinuousEffectParametersV1(
                target,
                DurationV1(DurationKindV1.PERMANENT, None),
                descriptor,
            ),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.SEARCH_ZONE,
            SearchZoneParametersV1(
                _entity(EntityRoleV1.SOURCE),
                ZoneRefV1(ZoneNameV1.LIBRARY, None),
                descriptor,
                ZoneRefV1(ZoneNameV1.HAND, None),
                True,
            ),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            DrawCardsParametersV1(_entity(EntityRoleV1.CONTROLLER), _quantity()),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DEAL_DAMAGE,
            DealDamageParametersV1(_entity(EntityRoleV1.SOURCE), target, _quantity()),
        ),
        (
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.CREATE_DELAYED_EFFECT,
            CreateDelayedEffectParametersV1(
                _descriptor(SemanticShapeV1.DURATION), descriptor
            ),
        ),
        (
            RequirementFamilyV1.EVENT,
            RequirementKindV1.TRIGGER_FROM_EVENT,
            TriggerFromEventParametersV1(
                _descriptor(SemanticShapeV1.EVENT),
                _entity(EntityRoleV1.CONTROLLER),
                None,
            ),
        ),
        (
            RequirementFamilyV1.EVENT,
            RequirementKindV1.REPLACE_EVENT,
            ReplaceEventParametersV1(_descriptor(SemanticShapeV1.EVENT), descriptor),
        ),
        (
            RequirementFamilyV1.COST,
            RequirementKindV1.PAY_COST,
            PayCostParametersV1(
                _entity(EntityRoleV1.PAYER), _descriptor(SemanticShapeV1.COST)
            ),
        ),
        (
            RequirementFamilyV1.COST,
            RequirementKindV1.MODIFY_COST,
            ModifyCostParametersV1(
                target,
                _descriptor(SemanticShapeV1.COST),
                CostOperationV1.DECREASE,
            ),
        ),
        (
            RequirementFamilyV1.CHOICE,
            RequirementKindV1.CHOOSE_MODE,
            ChooseModeParametersV1(
                _entity(EntityRoleV1.CHOOSER), _quantity(), _quantity(), (descriptor,)
            ),
        ),
        (
            RequirementFamilyV1.CONTROL,
            RequirementKindV1.CONDITIONAL_EFFECT,
            ConditionalEffectParametersV1(
                _descriptor(SemanticShapeV1.CONDITION), descriptor, None
            ),
        ),
        (
            RequirementFamilyV1.REFERENCE,
            RequirementKindV1.KEYWORD_REFERENCE,
            KeywordReferenceParametersV1(
                "Flying", 0, ExpansionStateV1.UNEXPANDED, None
            ),
        ),
        (
            RequirementFamilyV1.UNKNOWN,
            RequirementKindV1.UNRESOLVED,
            UnresolvedParametersV1(
                "oracle_text",
                SemanticShapeV1.UNKNOWN,
                "review",
                (RequirementKindV1.DRAW_CARDS,),
                None,
            ),
        ),
    )
    assert len(values) == 17
    for family, kind, payload in values:
        assert (
            payload_from_wire(family, kind, payload_to_wire(family, kind, payload))
            == payload
        )


def test_characteristics_are_canonicalized_and_duplicates_fail() -> None:
    red = CharacteristicAssignmentV1(
        CharacteristicRefV1(CharacteristicNameV1.COLOR, None),
        ParameterValueV1(ParameterValueTypeV1.TEXT, "red"),
    )
    power = CharacteristicAssignmentV1(
        CharacteristicRefV1(CharacteristicNameV1.POWER, None),
        ParameterValueV1(ParameterValueTypeV1.INTEGER, 3),
    )
    first = CreateObjectParametersV1(
        ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
        _quantity(),
        (red, power),
        None,
    )
    second = CreateObjectParametersV1(
        ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
        _quantity(),
        (power, red),
        None,
    )
    assert first.to_wire() == second.to_wire()
    with pytest.raises(ValueError, match="duplicates"):
        CreateObjectParametersV1(
            ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
            _quantity(),
            (red, red),
            None,
        )


def test_payload_from_wire_rejects_tuple_arrays() -> None:
    payload = CreateObjectParametersV1(
        ParameterValueV1(ParameterValueTypeV1.TEXT, "object"),
        _quantity(),
        (),
        None,
    )
    wire = payload_to_wire(
        RequirementFamilyV1.EFFECT, RequirementKindV1.CREATE_OBJECT, payload
    )
    wire["characteristics"] = ()
    with pytest.raises(TypeError, match="JSON array|tuple|unsupported"):
        payload_from_wire(
            RequirementFamilyV1.EFFECT, RequirementKindV1.CREATE_OBJECT, wire
        )


def test_unresolved_payload_preserves_explicit_unknown_reason() -> None:
    payload = UnresolvedParametersV1(
        observed_field="keywords",
        observed_shape=SemanticShapeV1.UNKNOWN,
        question="keyword expansion is not reviewed",
        candidate_kinds=(),
        fragment=None,
    )
    assert (
        payload_to_wire(
            RequirementFamilyV1.UNKNOWN,
            RequirementKindV1.UNRESOLVED,
            payload,
        )["question"]
        == "keyword expansion is not reviewed"
    )
    assert UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None).reason.value == (
        "UNKNOWN_SEMANTICS"
    )


def test_payload_dispatch_rejects_unknown_kind_and_extra_properties() -> None:
    with pytest.raises(ValueError, match="kind"):
        payload_from_wire(
            RequirementFamilyV1.EFFECT,
            "not-a-kind",  # type: ignore[arg-type]
            {},
        )

    wire = payload_to_wire(
        RequirementFamilyV1.EFFECT,
        RequirementKindV1.DRAW_CARDS,
        DrawCardsParametersV1(_entity(EntityRoleV1.SOURCE), _quantity()),
    )
    wire["extra"] = True
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        payload_from_wire(
            RequirementFamilyV1.EFFECT,
            RequirementKindV1.DRAW_CARDS,
            wire,
        )


def test_unresolved_rejects_arbitrary_shape_and_candidate_kind() -> None:
    with pytest.raises((TypeError, ValueError), match="unsupported|value"):
        UnresolvedParametersV1(
            observed_field="oracle_text",
            observed_shape="whatever",  # type: ignore[arg-type]
            question="review",
            candidate_kinds=(RequirementKindV1.DRAW_CARDS,),
            fragment=None,
        )

    with pytest.raises((TypeError, ValueError), match="unsupported|value"):
        UnresolvedParametersV1(
            observed_field="oracle_text",
            observed_shape=SemanticShapeV1.UNKNOWN,
            question="review",
            candidate_kinds=("implement_card_x",),  # type: ignore[arg-type]
            fragment=None,
        )


def test_unresolved_rejects_arbitrary_observed_field_directly() -> None:
    with pytest.raises(ValueError, match="controlled M1 source field"):
        UnresolvedParametersV1(
            observed_field="not_a_real_m1_field",
            observed_shape=SemanticShapeV1.UNKNOWN,
            question="review",
            candidate_kinds=(),
            fragment=None,
        )


def test_unresolved_rejects_arbitrary_observed_field_from_wire() -> None:
    wire = {
        "observed_field": "not_a_real_m1_field",
        "observed_shape": "unknown",
        "question": "review",
        "candidate_kinds": [],
        "fragment": None,
    }
    with pytest.raises(ValueError, match="controlled M1 source field"):
        payload_from_wire(
            RequirementFamilyV1.UNKNOWN, RequirementKindV1.UNRESOLVED, wire
        )


def test_unresolved_accepts_controlled_m1_fields() -> None:
    for field in ("record", "oracle_text"):
        payload = UnresolvedParametersV1(
            observed_field=field,
            observed_shape=SemanticShapeV1.UNKNOWN,
            question="review",
            candidate_kinds=(),
            fragment=None,
        )
        assert payload.observed_field == field
