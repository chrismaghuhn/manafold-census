import pytest

from manafold_census.semantic.kind_payloads import (
    CreateDelayedEffectParametersV1,
    CreateObjectParametersV1,
    DrawCardsParametersV1,
    MoveBetweenZonesParametersV1,
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
    EntityRefV1,
    EntityRoleV1,
    MultiplicityV1,
    ParameterValueTypeV1,
    ParameterValueV1,
    QuantityModeV1,
    QuantityV1,
    SemanticDescriptorV1,
    SemanticShapeV1,
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
    assert len(RequirementKindV1) == 17
    assert set(KIND_FAMILY) == set(RequirementKindV1)


def test_every_kind_maps_to_one_closed_family() -> None:
    for kind in RequirementKindV1:
        family = family_for_kind(kind)
        assert KIND_FAMILY[kind] == family
        validate_kind_family(family, kind)

    with pytest.raises(ValueError, match="family"):
        validate_kind_family(RequirementFamilyV1.COST, RequirementKindV1.DRAW_CARDS)


def test_payload_key_registry_is_closed_and_matches_design() -> None:
    assert PAYLOAD_REQUIRED_KEYS[RequirementKindV1.MOVE_BETWEEN_ZONES] == {
        "subject",
        "from_zone",
        "to_zone",
        "quantity",
    }
    assert PAYLOAD_OPTIONAL_KEYS[RequirementKindV1.MOVE_BETWEEN_ZONES] == {"cause"}
    assert PAYLOAD_REQUIRED_KEYS[RequirementKindV1.UNRESOLVED] == {
        "observed_field",
        "observed_shape",
        "question",
        "candidate_kinds",
    }
    assert PAYLOAD_OPTIONAL_KEYS[RequirementKindV1.UNRESOLVED] == {"fragment"}
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
        observed_shape="outlier",
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


def test_unresolved_payload_preserves_explicit_unknown_reason() -> None:
    payload = UnresolvedParametersV1(
        observed_field="keywords",
        observed_shape="keyword",
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
