"""Closed, typed payload variants for every M2 Requirement kind."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from .kinds import RequirementKindV1
from .primitives import (
    CharacteristicAssignmentV1,
    CharacteristicRefV1,
    CostOperationV1,
    DurationV1,
    EntityRefV1,
    ExpansionStateV1,
    ModificationOperationV1,
    ParameterValueV1,
    QuantityV1,
    SemanticDescriptorV1,
    SemanticShapeV1,
    SubjectKindV1,
    ZoneRefV1,
    _enum_parser,
    _instance_parser,
    _optional_parser,
    _Parser,
    _require_bool,
    _require_int,
    _require_object,
    _require_text,
    _tuple_parser,
    _WireModel,
)


def _text_parser(field: str) -> _Parser:
    return lambda value: _require_text(field, value)


M1_SOURCE_FIELDS = frozenset(
    {
        "record",
        "name",
        "layout",
        "mana_cost",
        "type_line",
        "oracle_text",
        "colors",
        "color_identity",
        "color_indicator",
        "keywords",
        "produced_mana",
        "power",
        "toughness",
        "loyalty",
        "defense",
        "hand_modifier",
        "life_modifier",
        "attraction_lights",
        "faces",
        "all_parts",
    }
)


def _source_field(value: object) -> str:
    text = _require_text("observed_field", value)
    if text not in M1_SOURCE_FIELDS:
        raise ValueError("observed_field is not a controlled M1 source field")
    return text


class _Payload(_WireModel):
    _WIRE_KEYS: ClassVar[set[str]]

    @classmethod
    def _document(cls, value: object, label: str) -> dict[str, object]:
        return _require_object(value, cls._WIRE_KEYS, label)


@dataclass(frozen=True, slots=True)
class MoveBetweenZonesParametersV1(_Payload):
    subject: EntityRefV1
    from_zone: ZoneRefV1
    to_zone: ZoneRefV1
    quantity: QuantityV1
    cause: SemanticDescriptorV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "subject",
        "from_zone",
        "to_zone",
        "quantity",
        "cause",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "subject": _instance_parser(EntityRefV1),
        "from_zone": _instance_parser(ZoneRefV1),
        "to_zone": _instance_parser(ZoneRefV1),
        "quantity": _instance_parser(QuantityV1),
        "cause": _optional_parser(_instance_parser(SemanticDescriptorV1)),
    }


@dataclass(frozen=True, slots=True)
class CreateObjectParametersV1(_Payload):
    object_class: ParameterValueV1
    quantity: QuantityV1
    characteristics: tuple[CharacteristicAssignmentV1, ...]
    duration: DurationV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "object_class",
        "quantity",
        "characteristics",
        "duration",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "object_class": _instance_parser(ParameterValueV1),
        "quantity": _instance_parser(QuantityV1),
        "characteristics": _tuple_parser(
            _instance_parser(CharacteristicAssignmentV1), "characteristics"
        ),
        "duration": _optional_parser(_instance_parser(DurationV1)),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        encoded = [
            canonical_json_bytes(item.to_wire()) for item in self.characteristics
        ]
        if len(encoded) != len(set(encoded)):
            raise ValueError("characteristics must not contain duplicates")
        ordered = tuple(
            item
            for _, item in sorted(
                zip(encoded, self.characteristics, strict=True),
                key=lambda pair: pair[0],
            )
        )
        object.__setattr__(self, "characteristics", ordered)


@dataclass(frozen=True, slots=True)
class SelectParametersV1(_Payload):
    chooser: EntityRefV1
    subject_kind: SubjectKindV1
    quantity: QuantityV1
    restriction: SemanticDescriptorV1
    targeting: bool | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "chooser",
        "subject_kind",
        "quantity",
        "restriction",
        "targeting",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "chooser": _instance_parser(EntityRefV1),
        "subject_kind": _enum_parser(SubjectKindV1),
        "quantity": _instance_parser(QuantityV1),
        "restriction": _instance_parser(SemanticDescriptorV1),
        "targeting": _optional_parser(
            lambda value: value
            if type(value) is bool
            else _require_bool("targeting", value)
        ),
    }


@dataclass(frozen=True, slots=True)
class ModifyCharacteristicParametersV1(_Payload):
    subject: EntityRefV1
    characteristic: CharacteristicRefV1
    operation: ModificationOperationV1
    value: ParameterValueV1
    _WIRE_KEYS: ClassVar[set[str]] = {"subject", "characteristic", "operation", "value"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "subject": _instance_parser(EntityRefV1),
        "characteristic": _instance_parser(CharacteristicRefV1),
        "operation": _enum_parser(ModificationOperationV1),
        "value": _instance_parser(ParameterValueV1),
    }


@dataclass(frozen=True, slots=True)
class ApplyContinuousEffectParametersV1(_Payload):
    subject: EntityRefV1
    duration: DurationV1
    effect: SemanticDescriptorV1
    _WIRE_KEYS: ClassVar[set[str]] = {"subject", "duration", "effect"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "subject": _instance_parser(EntityRefV1),
        "duration": _instance_parser(DurationV1),
        "effect": _instance_parser(SemanticDescriptorV1),
    }


@dataclass(frozen=True, slots=True)
class SearchZoneParametersV1(_Payload):
    searcher: EntityRefV1
    zone: ZoneRefV1
    selection: SemanticDescriptorV1
    destination: ZoneRefV1 | None
    reveal: bool | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "searcher",
        "zone",
        "selection",
        "destination",
        "reveal",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "searcher": _instance_parser(EntityRefV1),
        "zone": _instance_parser(ZoneRefV1),
        "selection": _instance_parser(SemanticDescriptorV1),
        "destination": _optional_parser(_instance_parser(ZoneRefV1)),
        "reveal": _optional_parser(
            lambda value: value
            if type(value) is bool
            else _require_bool("reveal", value)
        ),
    }


@dataclass(frozen=True, slots=True)
class DrawCardsParametersV1(_Payload):
    drawer: EntityRefV1
    quantity: QuantityV1
    _WIRE_KEYS: ClassVar[set[str]] = {"drawer", "quantity"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "drawer": _instance_parser(EntityRefV1),
        "quantity": _instance_parser(QuantityV1),
    }


@dataclass(frozen=True, slots=True)
class DealDamageParametersV1(_Payload):
    source: EntityRefV1
    recipient: EntityRefV1
    amount: QuantityV1
    _WIRE_KEYS: ClassVar[set[str]] = {"source", "recipient", "amount"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "source": _instance_parser(EntityRefV1),
        "recipient": _instance_parser(EntityRefV1),
        "amount": _instance_parser(QuantityV1),
    }


@dataclass(frozen=True, slots=True)
class CreateDelayedEffectParametersV1(_Payload):
    delay: SemanticDescriptorV1
    effect: SemanticDescriptorV1
    _WIRE_KEYS: ClassVar[set[str]] = {"delay", "effect"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "delay": _instance_parser(SemanticDescriptorV1),
        "effect": _instance_parser(SemanticDescriptorV1),
    }


@dataclass(frozen=True, slots=True)
class TriggerFromEventParametersV1(_Payload):
    event: SemanticDescriptorV1
    controller: EntityRefV1
    condition: SemanticDescriptorV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {"event", "controller", "condition"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "event": _instance_parser(SemanticDescriptorV1),
        "controller": _instance_parser(EntityRefV1),
        "condition": _optional_parser(_instance_parser(SemanticDescriptorV1)),
    }


@dataclass(frozen=True, slots=True)
class ReplaceEventParametersV1(_Payload):
    event: SemanticDescriptorV1
    replacement: SemanticDescriptorV1
    _WIRE_KEYS: ClassVar[set[str]] = {"event", "replacement"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "event": _instance_parser(SemanticDescriptorV1),
        "replacement": _instance_parser(SemanticDescriptorV1),
    }


@dataclass(frozen=True, slots=True)
class PayCostParametersV1(_Payload):
    payer: EntityRefV1
    cost: SemanticDescriptorV1
    _WIRE_KEYS: ClassVar[set[str]] = {"payer", "cost"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "payer": _instance_parser(EntityRefV1),
        "cost": _instance_parser(SemanticDescriptorV1),
    }


@dataclass(frozen=True, slots=True)
class ModifyCostParametersV1(_Payload):
    subject: EntityRefV1
    cost: SemanticDescriptorV1
    operation: CostOperationV1
    _WIRE_KEYS: ClassVar[set[str]] = {"subject", "cost", "operation"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "subject": _instance_parser(EntityRefV1),
        "cost": _instance_parser(SemanticDescriptorV1),
        "operation": _enum_parser(CostOperationV1),
    }


@dataclass(frozen=True, slots=True)
class ChooseModeParametersV1(_Payload):
    chooser: EntityRefV1
    minimum: QuantityV1
    maximum: QuantityV1
    alternatives: tuple[SemanticDescriptorV1, ...]
    _WIRE_KEYS: ClassVar[set[str]] = {"chooser", "minimum", "maximum", "alternatives"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "chooser": _instance_parser(EntityRefV1),
        "minimum": _instance_parser(QuantityV1),
        "maximum": _instance_parser(QuantityV1),
        "alternatives": _tuple_parser(
            _instance_parser(SemanticDescriptorV1), "alternatives"
        ),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.alternatives:
            raise ValueError("alternatives must be non-empty")


@dataclass(frozen=True, slots=True)
class ConditionalEffectParametersV1(_Payload):
    condition: SemanticDescriptorV1
    then_effect: SemanticDescriptorV1
    else_effect: SemanticDescriptorV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {"condition", "then_effect", "else_effect"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "condition": _instance_parser(SemanticDescriptorV1),
        "then_effect": _instance_parser(SemanticDescriptorV1),
        "else_effect": _optional_parser(_instance_parser(SemanticDescriptorV1)),
    }


@dataclass(frozen=True, slots=True)
class KeywordReferenceParametersV1(_Payload):
    keyword: str
    keyword_index: int
    expansion_state: ExpansionStateV1
    expansion: SemanticDescriptorV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "keyword",
        "keyword_index",
        "expansion_state",
        "expansion",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "keyword": _text_parser("keyword"),
        "keyword_index": lambda value: _require_int(
            "keyword_index", value, nonnegative=True
        ),
        "expansion_state": _enum_parser(ExpansionStateV1),
        "expansion": _optional_parser(_instance_parser(SemanticDescriptorV1)),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.expansion_state is ExpansionStateV1.EXPANDED and self.expansion is None:
            raise ValueError("expanded keyword requires expansion")
        if (
            self.expansion_state is not ExpansionStateV1.EXPANDED
            and self.expansion is not None
        ):
            raise ValueError("unexpanded keyword cannot contain expansion")


@dataclass(frozen=True, slots=True)
class UnresolvedParametersV1(_Payload):
    observed_field: str
    observed_shape: SemanticShapeV1
    question: str
    candidate_kinds: tuple[RequirementKindV1, ...]
    fragment: str | None
    _WIRE_KEYS: ClassVar[set[str]] = {
        "observed_field",
        "observed_shape",
        "question",
        "candidate_kinds",
        "fragment",
    }
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "observed_field": _source_field,
        "observed_shape": _enum_parser(SemanticShapeV1),
        "question": _text_parser("question"),
        "candidate_kinds": _tuple_parser(
            _enum_parser(RequirementKindV1), "candidate_kinds"
        ),
        "fragment": _optional_parser(_text_parser("fragment")),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        ordered = tuple(sorted(set(self.candidate_kinds), key=lambda kind: kind.value))
        if ordered != self.candidate_kinds:
            raise ValueError("candidate_kinds must be unique and sorted")


type KindPayloadV1 = (
    MoveBetweenZonesParametersV1
    | CreateObjectParametersV1
    | SelectParametersV1
    | ModifyCharacteristicParametersV1
    | ApplyContinuousEffectParametersV1
    | SearchZoneParametersV1
    | DrawCardsParametersV1
    | DealDamageParametersV1
    | CreateDelayedEffectParametersV1
    | TriggerFromEventParametersV1
    | ReplaceEventParametersV1
    | PayCostParametersV1
    | ModifyCostParametersV1
    | ChooseModeParametersV1
    | ConditionalEffectParametersV1
    | KeywordReferenceParametersV1
    | UnresolvedParametersV1
)


_PAYLOAD_TYPES: dict[str, type[_Payload]] = {
    "move_between_zones": MoveBetweenZonesParametersV1,
    "create_object": CreateObjectParametersV1,
    "select": SelectParametersV1,
    "modify_characteristic": ModifyCharacteristicParametersV1,
    "apply_continuous_effect": ApplyContinuousEffectParametersV1,
    "search_zone": SearchZoneParametersV1,
    "draw_cards": DrawCardsParametersV1,
    "deal_damage": DealDamageParametersV1,
    "create_delayed_effect": CreateDelayedEffectParametersV1,
    "trigger_from_event": TriggerFromEventParametersV1,
    "replace_event": ReplaceEventParametersV1,
    "pay_cost": PayCostParametersV1,
    "modify_cost": ModifyCostParametersV1,
    "choose_mode": ChooseModeParametersV1,
    "conditional_effect": ConditionalEffectParametersV1,
    "keyword_reference": KeywordReferenceParametersV1,
    "unresolved": UnresolvedParametersV1,
}


def _kind_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("kind must be a string enum value")
    return value


def payload_to_wire(
    family: object, kind: object, payload: KindPayloadV1
) -> dict[str, JSONValue]:
    from .kinds import validate_kind_family

    validate_kind_family(family, kind)
    kind_value = _kind_text(kind)
    expected = _PAYLOAD_TYPES[kind_value]
    if not isinstance(payload, expected):
        raise TypeError(f"payload does not match kind {kind_value}")
    return payload.to_wire()


def payload_from_wire(family: object, kind: object, value: object) -> KindPayloadV1:
    from .kinds import validate_kind_family

    validate_kind_family(family, kind)
    kind_value = _kind_text(kind)
    payload_type = _PAYLOAD_TYPES.get(kind_value)
    if payload_type is None:
        raise ValueError("unsupported kind")
    return cast(KindPayloadV1, payload_type.from_wire(value))


__all__ = [
    "ApplyContinuousEffectParametersV1",
    "ChooseModeParametersV1",
    "ConditionalEffectParametersV1",
    "CreateDelayedEffectParametersV1",
    "CreateObjectParametersV1",
    "DealDamageParametersV1",
    "DrawCardsParametersV1",
    "KeywordReferenceParametersV1",
    "KindPayloadV1",
    "ModifyCharacteristicParametersV1",
    "ModifyCostParametersV1",
    "MoveBetweenZonesParametersV1",
    "PayCostParametersV1",
    "ReplaceEventParametersV1",
    "SearchZoneParametersV1",
    "SelectParametersV1",
    "TriggerFromEventParametersV1",
    "UnresolvedParametersV1",
    "payload_from_wire",
    "payload_to_wire",
]
