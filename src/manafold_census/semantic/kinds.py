"""Closed M2 Requirement family/kind vocabulary and payload key registry."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class RequirementFamilyV1(StrEnum):
    EFFECT = "effect"
    EVENT = "event"
    CHOICE = "choice"
    COST = "cost"
    CONTROL = "control"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


class RequirementKindV1(StrEnum):
    MOVE_BETWEEN_ZONES = "move_between_zones"
    CREATE_OBJECT = "create_object"
    SELECT = "select"
    MODIFY_CHARACTERISTIC = "modify_characteristic"
    APPLY_CONTINUOUS_EFFECT = "apply_continuous_effect"
    SEARCH_ZONE = "search_zone"
    DRAW_CARDS = "draw_cards"
    DEAL_DAMAGE = "deal_damage"
    CREATE_DELAYED_EFFECT = "create_delayed_effect"
    TRIGGER_FROM_EVENT = "trigger_from_event"
    REPLACE_EVENT = "replace_event"
    PAY_COST = "pay_cost"
    MODIFY_COST = "modify_cost"
    CHOOSE_MODE = "choose_mode"
    CONDITIONAL_EFFECT = "conditional_effect"
    KEYWORD_REFERENCE = "keyword_reference"
    UNRESOLVED = "unresolved"


KIND_FAMILY: Mapping[RequirementKindV1, RequirementFamilyV1] = MappingProxyType(
    {
        RequirementKindV1.MOVE_BETWEEN_ZONES: RequirementFamilyV1.EFFECT,
        RequirementKindV1.CREATE_OBJECT: RequirementFamilyV1.EFFECT,
        RequirementKindV1.SELECT: RequirementFamilyV1.CHOICE,
        RequirementKindV1.MODIFY_CHARACTERISTIC: RequirementFamilyV1.EFFECT,
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT: RequirementFamilyV1.EFFECT,
        RequirementKindV1.SEARCH_ZONE: RequirementFamilyV1.EFFECT,
        RequirementKindV1.DRAW_CARDS: RequirementFamilyV1.EFFECT,
        RequirementKindV1.DEAL_DAMAGE: RequirementFamilyV1.EFFECT,
        RequirementKindV1.CREATE_DELAYED_EFFECT: RequirementFamilyV1.EFFECT,
        RequirementKindV1.TRIGGER_FROM_EVENT: RequirementFamilyV1.EVENT,
        RequirementKindV1.REPLACE_EVENT: RequirementFamilyV1.EVENT,
        RequirementKindV1.PAY_COST: RequirementFamilyV1.COST,
        RequirementKindV1.MODIFY_COST: RequirementFamilyV1.COST,
        RequirementKindV1.CHOOSE_MODE: RequirementFamilyV1.CHOICE,
        RequirementKindV1.CONDITIONAL_EFFECT: RequirementFamilyV1.CONTROL,
        RequirementKindV1.KEYWORD_REFERENCE: RequirementFamilyV1.REFERENCE,
        RequirementKindV1.UNRESOLVED: RequirementFamilyV1.UNKNOWN,
    }
)


PAYLOAD_REQUIRED_KEYS: Mapping[RequirementKindV1, frozenset[str]] = MappingProxyType(
    {
        RequirementKindV1.MOVE_BETWEEN_ZONES: frozenset(
            {"subject", "from_zone", "to_zone", "quantity"}
        ),
        RequirementKindV1.CREATE_OBJECT: frozenset(
            {"object_class", "quantity", "characteristics"}
        ),
        RequirementKindV1.SELECT: frozenset(
            {"chooser", "subject_kind", "quantity", "restriction"}
        ),
        RequirementKindV1.MODIFY_CHARACTERISTIC: frozenset(
            {"subject", "characteristic", "operation", "value"}
        ),
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT: frozenset(
            {"subject", "duration", "effect"}
        ),
        RequirementKindV1.SEARCH_ZONE: frozenset({"searcher", "zone", "selection"}),
        RequirementKindV1.DRAW_CARDS: frozenset({"drawer", "quantity"}),
        RequirementKindV1.DEAL_DAMAGE: frozenset({"source", "recipient", "amount"}),
        RequirementKindV1.CREATE_DELAYED_EFFECT: frozenset({"delay", "effect"}),
        RequirementKindV1.TRIGGER_FROM_EVENT: frozenset({"event", "controller"}),
        RequirementKindV1.REPLACE_EVENT: frozenset({"event", "replacement"}),
        RequirementKindV1.PAY_COST: frozenset({"payer", "cost"}),
        RequirementKindV1.MODIFY_COST: frozenset({"subject", "cost", "operation"}),
        RequirementKindV1.CHOOSE_MODE: frozenset(
            {"chooser", "minimum", "maximum", "alternatives"}
        ),
        RequirementKindV1.CONDITIONAL_EFFECT: frozenset({"condition", "then_effect"}),
        RequirementKindV1.KEYWORD_REFERENCE: frozenset(
            {"keyword", "keyword_index", "expansion_state"}
        ),
        RequirementKindV1.UNRESOLVED: frozenset(
            {"observed_field", "observed_shape", "question", "candidate_kinds"}
        ),
    }
)


PAYLOAD_OPTIONAL_KEYS: Mapping[RequirementKindV1, frozenset[str]] = MappingProxyType(
    {
        RequirementKindV1.MOVE_BETWEEN_ZONES: frozenset({"cause"}),
        RequirementKindV1.CREATE_OBJECT: frozenset({"duration"}),
        RequirementKindV1.SELECT: frozenset({"targeting"}),
        RequirementKindV1.MODIFY_CHARACTERISTIC: frozenset(),
        RequirementKindV1.APPLY_CONTINUOUS_EFFECT: frozenset(),
        RequirementKindV1.SEARCH_ZONE: frozenset({"destination", "reveal"}),
        RequirementKindV1.DRAW_CARDS: frozenset(),
        RequirementKindV1.DEAL_DAMAGE: frozenset(),
        RequirementKindV1.CREATE_DELAYED_EFFECT: frozenset(),
        RequirementKindV1.TRIGGER_FROM_EVENT: frozenset({"condition"}),
        RequirementKindV1.REPLACE_EVENT: frozenset(),
        RequirementKindV1.PAY_COST: frozenset(),
        RequirementKindV1.MODIFY_COST: frozenset(),
        RequirementKindV1.CHOOSE_MODE: frozenset(),
        RequirementKindV1.CONDITIONAL_EFFECT: frozenset({"else_effect"}),
        RequirementKindV1.KEYWORD_REFERENCE: frozenset({"expansion"}),
        RequirementKindV1.UNRESOLVED: frozenset({"fragment"}),
    }
)


def _family(value: object) -> RequirementFamilyV1:
    if isinstance(value, RequirementFamilyV1):
        return value
    if isinstance(value, str):
        try:
            return RequirementFamilyV1(value)
        except ValueError as error:
            raise ValueError("unsupported Requirement family") from error
    raise TypeError("family must be a string enum value")


def _kind(value: object) -> RequirementKindV1:
    if isinstance(value, RequirementKindV1):
        return value
    if isinstance(value, str):
        try:
            return RequirementKindV1(value)
        except ValueError as error:
            raise ValueError("unsupported Requirement kind") from error
    raise TypeError("kind must be a string enum value")


def family_for_kind(kind: object) -> RequirementFamilyV1:
    return KIND_FAMILY[_kind(kind)]


def validate_kind_family(family: object, kind: object) -> None:
    family_value = _family(family)
    kind_value = _kind(kind)
    expected = KIND_FAMILY[kind_value]
    if family_value is not expected:
        raise ValueError(
            f"kind {kind_value.value} does not belong to family {family_value.value}"
        )


__all__ = [
    "KIND_FAMILY",
    "PAYLOAD_OPTIONAL_KEYS",
    "PAYLOAD_REQUIRED_KEYS",
    "RequirementFamilyV1",
    "RequirementKindV1",
    "family_for_kind",
    "validate_kind_family",
]
