from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from manafold_census.canonical import MAX_INTEGER, MIN_INTEGER
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


def _entity(role: EntityRoleV1 = EntityRoleV1.SOURCE) -> EntityRefV1:
    return EntityRefV1(
        role=role,
        multiplicity=MultiplicityV1.ONE,
        ordinal=None,
    )


def _unknown() -> UnknownValueV1:
    return UnknownValueV1(
        reason=UnknownReasonV1.UNKNOWN_SEMANTICS,
        hint="review this value",
    )


def test_all_slotted_post_init_models_construct_and_round_trip() -> None:
    descriptor = SemanticDescriptorV1(
        shape=SemanticShapeV1.EFFECT,
        label="effect context",
        subject=None,
        object_ref=None,
        value=None,
        children=(),
    )
    values = (
        ZoneRefV1(ZoneNameV1.UNKNOWN, "custom zone"),
        QuantityV1(QuantityModeV1.EXACT, 2),
        CharacteristicRefV1(CharacteristicNameV1.OTHER, "custom characteristic"),
        ParameterValueV1(ParameterValueTypeV1.DESCRIPTOR, descriptor),
        descriptor,
        DurationV1(DurationKindV1.DELAYED, descriptor),
    )

    for value in values:
        assert type(value).from_wire(value.to_wire()) == value


@pytest.mark.parametrize(
    ("enum_type", "expected"),
    [
        (
            EntityRoleV1,
            {
                "source",
                "target",
                "chosen",
                "affected",
                "created",
                "event_subject",
                "controller",
                "owner",
                "payer",
                "chooser",
                "unknown",
            },
        ),
        (MultiplicityV1, {"one", "many", "each", "unknown"}),
        (
            ZoneNameV1,
            {
                "library",
                "hand",
                "battlefield",
                "graveyard",
                "exile",
                "stack",
                "command",
                "outside_game",
                "unknown",
            },
        ),
        (QuantityModeV1, {"exact", "all", "each", "symbolic", "unknown"}),
        (
            CharacteristicNameV1,
            {
                "power",
                "toughness",
                "color",
                "type",
                "subtype",
                "ability",
                "controller",
                "owner",
                "zone",
                "cost",
                "base",
                "other",
            },
        ),
        (ParameterValueTypeV1, {"text", "integer", "boolean", "descriptor", "unknown"}),
        (
            SemanticShapeV1,
            {
                "event",
                "condition",
                "restriction",
                "effect",
                "replacement",
                "duration",
                "cost",
                "alternative",
                "unknown",
            },
        ),
        (SubjectKindV1, {"object", "player", "card", "zone", "ability", "unknown"}),
        (
            ModificationOperationV1,
            {"set", "add", "subtract", "grant", "remove", "change", "unknown"},
        ),
        (CostOperationV1, {"increase", "decrease", "alternative", "unknown"}),
        (ExpansionStateV1, {"unexpanded", "expanded", "unknown"}),
        (
            DurationKindV1,
            {"until_end_of_turn", "this_turn", "permanent", "delayed", "unknown"},
        ),
        (
            UnknownReasonV1,
            {
                "INSUFFICIENT_EVIDENCE",
                "AMBIGUOUS_SOURCE",
                "UNSUPPORTED_SHAPE",
                "CONFLICTING_INTERPRETATIONS",
                "UNKNOWN_SEMANTICS",
            },
        ),
    ],
)
def test_every_primitive_enum_value_is_closed(
    enum_type: type, expected: set[str]
) -> None:
    assert {member.value for member in enum_type} == expected


def test_entity_reference_round_trips_and_is_immutable() -> None:
    entity = _entity(EntityRoleV1.TARGET)

    assert EntityRefV1.from_wire(entity.to_wire()) == entity
    with pytest.raises(FrozenInstanceError):
        entity.role = EntityRoleV1.SOURCE  # type: ignore[misc]


def test_quantity_variants_preserve_explicit_unknown_reason() -> None:
    exact = QuantityV1(QuantityModeV1.EXACT, 2)
    all_items = QuantityV1(QuantityModeV1.ALL, None)
    each = QuantityV1(QuantityModeV1.EACH, None)
    symbolic = QuantityV1(QuantityModeV1.SYMBOLIC, "X")
    unknown = QuantityV1(QuantityModeV1.UNKNOWN, _unknown())

    for value in (exact, all_items, each, symbolic, unknown):
        assert QuantityV1.from_wire(value.to_wire()) == value

    assert unknown.to_wire() == {
        "mode": "unknown",
        "value": {"reason": "UNKNOWN_SEMANTICS", "hint": "review this value"},
    }


@pytest.mark.parametrize(
    ("mode", "value"),
    [
        (QuantityModeV1.EXACT, True),
        (QuantityModeV1.ALL, 1),
        (QuantityModeV1.EACH, "one"),
        (QuantityModeV1.SYMBOLIC, ""),
        (QuantityModeV1.UNKNOWN, None),
    ],
)
def test_quantity_rejects_wrong_value_shape(
    mode: QuantityModeV1, value: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        QuantityV1(mode, value)  # type: ignore[arg-type]


def test_duration_has_exact_v1_kinds_and_typed_payloads() -> None:
    delayed = SemanticDescriptorV1(
        shape=SemanticShapeV1.CONDITION,
        label=None,
        subject=_entity(EntityRoleV1.EVENT_SUBJECT),
        object_ref=None,
        value=None,
        children=(),
    )
    durations = (
        DurationV1(DurationKindV1.UNTIL_END_OF_TURN, None),
        DurationV1(DurationKindV1.THIS_TURN, None),
        DurationV1(DurationKindV1.PERMANENT, None),
        DurationV1(DurationKindV1.DELAYED, delayed),
        DurationV1(DurationKindV1.UNKNOWN, _unknown()),
    )

    for duration in durations:
        assert DurationV1.from_wire(duration.to_wire()) == duration

    with pytest.raises((TypeError, ValueError)):
        DurationV1(DurationKindV1.DELAYED, None)
    with pytest.raises((TypeError, ValueError)):
        DurationV1(DurationKindV1.UNKNOWN, delayed)


def test_parameter_value_round_trips_nested_descriptor_and_unknown() -> None:
    descriptor = SemanticDescriptorV1(
        shape=SemanticShapeV1.EVENT,
        label="event context",
        subject=_entity(EntityRoleV1.SOURCE),
        object_ref=None,
        value=ParameterValueV1(ParameterValueTypeV1.INTEGER, 3),
        children=(),
    )
    values = (
        ParameterValueV1(ParameterValueTypeV1.TEXT, "bounded label"),
        ParameterValueV1(ParameterValueTypeV1.INTEGER, MIN_INTEGER),
        ParameterValueV1(ParameterValueTypeV1.BOOLEAN, False),
        ParameterValueV1(ParameterValueTypeV1.DESCRIPTOR, descriptor),
        ParameterValueV1(ParameterValueTypeV1.UNKNOWN, _unknown()),
    )

    for value in values:
        assert ParameterValueV1.from_wire(value.to_wire()) == value


def test_descriptor_wire_is_fresh_and_nested_values_are_immutable() -> None:
    descriptor = SemanticDescriptorV1(
        shape=SemanticShapeV1.ALTERNATIVE,
        label="mode",
        subject=None,
        object_ref=None,
        value=None,
        children=(
            SemanticDescriptorV1(
                shape=SemanticShapeV1.EFFECT,
                label=None,
                subject=_entity(EntityRoleV1.CREATED),
                object_ref=None,
                value=None,
                children=(),
            ),
        ),
    )
    wire = descriptor.to_wire()
    wire["children"].clear()  # type: ignore[union-attr]

    assert len(descriptor.children) == 1
    assert descriptor.to_wire()["children"]


def test_zone_and_characteristic_labels_are_limited_to_explicit_fallbacks() -> None:
    assert ZoneRefV1(ZoneNameV1.UNKNOWN, "custom zone").to_wire() == {
        "zone": "unknown",
        "label": "custom zone",
    }
    assert CharacteristicRefV1(
        CharacteristicNameV1.OTHER, "custom value"
    ).to_wire() == {
        "name": "other",
        "label": "custom value",
    }

    with pytest.raises(ValueError):
        ZoneRefV1(ZoneNameV1.HAND, "not allowed")
    with pytest.raises(ValueError):
        CharacteristicRefV1(CharacteristicNameV1.COLOR, "not allowed")
    with pytest.raises(ValueError, match="explicit label"):
        CharacteristicRefV1(CharacteristicNameV1.OTHER, None)


@pytest.mark.parametrize("value", [MAX_INTEGER + 1, MIN_INTEGER - 1])
def test_integer_bounds_are_signed_64_bit(value: int) -> None:
    with pytest.raises(ValueError, match="signed 64-bit"):
        QuantityV1(QuantityModeV1.EXACT, value)


def test_unknown_wire_properties_fail_closed() -> None:
    wire = _unknown().to_wire()
    wire["extra"] = True

    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        UnknownValueV1.from_wire(wire)


def test_bounded_text_uses_unicode_codepoints_and_valid_utf8() -> None:
    def values(text: str) -> tuple[object, ...]:
        return (
            UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, text),
            ZoneRefV1(ZoneNameV1.UNKNOWN, text),
            CharacteristicRefV1(CharacteristicNameV1.OTHER, text),
            QuantityV1(QuantityModeV1.SYMBOLIC, text),
            ParameterValueV1(ParameterValueTypeV1.TEXT, text),
            SemanticDescriptorV1(SemanticShapeV1.EFFECT, text, None, None, None, ()),
        )

    for text in ("x" * 4096, "😀" * 4096):
        assert values(text)

    for text in ("x" * 4097, "😀" * 4097):
        with pytest.raises(ValueError, match="4096"):
            values(text)

    with pytest.raises(ValueError, match="UTF-8"):
        UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, "\ud800")


def test_from_wire_rejects_python_tuples_for_json_arrays() -> None:
    descriptor = SemanticDescriptorV1(
        shape=SemanticShapeV1.EFFECT,
        label=None,
        subject=None,
        object_ref=None,
        value=None,
        children=(),
    )
    wire = descriptor.to_wire()
    wire["children"] = ()

    with pytest.raises(TypeError, match="JSON array|tuple|unsupported"):
        SemanticDescriptorV1.from_wire(wire)


@pytest.mark.parametrize(
    "wire",
    [
        {
            "role": EntityRoleV1.SOURCE,
            "multiplicity": "one",
            "ordinal": None,
        },
        {
            "role": "source",
            "multiplicity": "one",
            "ordinal": 1.0,
        },
        {
            "role": "source",
            "multiplicity": "one",
            "ordinal": {"not": "an integer"},
        },
        {
            1: "non-string key",
            "hint": None,
        },
        {
            "reason": "UNKNOWN_SEMANTICS",
            "hint": {"set"},
        },
        {
            "reason": "UNKNOWN_SEMANTICS",
            "hint": b"bytes",
        },
        {
            "reason": "UNKNOWN_SEMANTICS",
            "hint": Path("host-path"),
        },
    ],
)
def test_from_wire_rejects_non_json_values(wire: object) -> None:
    with pytest.raises(
        (TypeError, ValueError), match="JSON|object|integer|unsupported|forbidden"
    ):
        if "reason" in wire:  # type: ignore[operator]
            UnknownValueV1.from_wire(wire)
        else:
            EntityRefV1.from_wire(wire)


def test_from_wire_rejects_nested_python_model_objects() -> None:
    wire = SemanticDescriptorV1(
        shape=SemanticShapeV1.EFFECT,
        label=None,
        subject=None,
        object_ref=None,
        value=None,
        children=(),
    ).to_wire()
    wire["subject"] = _entity()

    with pytest.raises(TypeError, match="JSON|object|unsupported"):
        SemanticDescriptorV1.from_wire(wire)
