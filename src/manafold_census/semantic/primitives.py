"""Immutable typed atoms used by the M2 Requirement kind payloads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from enum import Enum, StrEnum
from typing import Any, ClassVar, TypeVar, cast

from ..canonical import MAX_INTEGER, MIN_INTEGER, JSONValue

_MAX_CONTEXT_BYTES = 4096
_ModelT = TypeVar("_ModelT", bound="_WireModel")
_Parser = Callable[[object], object]


class EntityRoleV1(StrEnum):
    SOURCE = "source"
    TARGET = "target"
    CHOSEN = "chosen"
    AFFECTED = "affected"
    CREATED = "created"
    EVENT_SUBJECT = "event_subject"
    CONTROLLER = "controller"
    OWNER = "owner"
    PAYER = "payer"
    CHOOSER = "chooser"
    UNKNOWN = "unknown"


class MultiplicityV1(StrEnum):
    ONE = "one"
    MANY = "many"
    EACH = "each"
    UNKNOWN = "unknown"


class ZoneNameV1(StrEnum):
    LIBRARY = "library"
    HAND = "hand"
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    EXILE = "exile"
    STACK = "stack"
    COMMAND = "command"
    OUTSIDE_GAME = "outside_game"
    UNKNOWN = "unknown"


class QuantityModeV1(StrEnum):
    EXACT = "exact"
    ALL = "all"
    EACH = "each"
    SYMBOLIC = "symbolic"
    UNKNOWN = "unknown"


class CharacteristicNameV1(StrEnum):
    POWER = "power"
    TOUGHNESS = "toughness"
    COLOR = "color"
    TYPE = "type"
    SUBTYPE = "subtype"
    ABILITY = "ability"
    CONTROLLER = "controller"
    OWNER = "owner"
    ZONE = "zone"
    COST = "cost"
    BASE = "base"
    OTHER = "other"


class ParameterValueTypeV1(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DESCRIPTOR = "descriptor"
    UNKNOWN = "unknown"


class SemanticShapeV1(StrEnum):
    EVENT = "event"
    CONDITION = "condition"
    RESTRICTION = "restriction"
    EFFECT = "effect"
    REPLACEMENT = "replacement"
    DURATION = "duration"
    COST = "cost"
    ALTERNATIVE = "alternative"
    UNKNOWN = "unknown"


class SubjectKindV1(StrEnum):
    OBJECT = "object"
    PLAYER = "player"
    CARD = "card"
    ZONE = "zone"
    ABILITY = "ability"
    UNKNOWN = "unknown"


class ModificationOperationV1(StrEnum):
    SET = "set"
    ADD = "add"
    SUBTRACT = "subtract"
    GRANT = "grant"
    REMOVE = "remove"
    CHANGE = "change"
    UNKNOWN = "unknown"


class CostOperationV1(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    ALTERNATIVE = "alternative"
    UNKNOWN = "unknown"


class ExpansionStateV1(StrEnum):
    UNEXPANDED = "unexpanded"
    EXPANDED = "expanded"
    UNKNOWN = "unknown"


class DurationKindV1(StrEnum):
    UNTIL_END_OF_TURN = "until_end_of_turn"
    THIS_TURN = "this_turn"
    PERMANENT = "permanent"
    DELAYED = "delayed"
    UNKNOWN = "unknown"


class UnknownReasonV1(StrEnum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"
    CONFLICTING_INTERPRETATIONS = "CONFLICTING_INTERPRETATIONS"
    UNKNOWN_SEMANTICS = "UNKNOWN_SEMANTICS"


def _validate_json_wire(value: object, path: str) -> None:
    if isinstance(value, Enum):
        raise TypeError(f"{path} contains an enum, not a JSON scalar")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if value < MIN_INTEGER or value > MAX_INTEGER:
            raise ValueError(f"{path} is outside the signed 64-bit range")
        return
    if isinstance(value, str):
        value.encode("utf-8")
        return
    if isinstance(value, float):
        raise TypeError(f"{path} contains a forbidden float")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_wire(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} has a non-string JSON object key")
            _validate_json_wire(item, f"{path}.{key}")
        return
    raise TypeError(f"{path} contains an unsupported non-JSON value")


def _require_object(value: object, keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    _validate_json_wire(value, label)
    actual = set(value)
    missing = sorted(keys - actual)
    unexpected = sorted(actual - keys)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing properties: {missing}")
        if unexpected:
            details.append(f"unexpected properties: {unexpected}")
        raise ValueError(f"{label} has {'; '.join(details)}")
    return cast(dict[str, object], value)


def _require_enum[T: StrEnum](field: str, value: object, enum_type: type[T]) -> T:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as error:
            raise ValueError(f"{field} has an unsupported value") from error
    raise TypeError(f"{field} must be a string enum value")


def _require_text(field: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not allow_empty and value == "":
        raise ValueError(f"{field} must be non-empty")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field} must be valid UTF-8") from error
    if len(value) > _MAX_CONTEXT_BYTES:
        raise ValueError(f"{field} exceeds {_MAX_CONTEXT_BYTES} Unicode code points")
    return value


def _optional_text_parser(field: str) -> _Parser:
    return lambda value: None if value is None else _require_text(field, value)


def _require_int(field: str, value: object, *, nonnegative: bool = False) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an integer")
    if value < MIN_INTEGER or value > MAX_INTEGER:
        raise ValueError(f"{field} is outside the signed 64-bit range")
    if nonnegative and value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _require_bool(field: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field} must be a boolean")
    return value


def _enum_parser(enum_type: type[StrEnum]) -> _Parser:
    return lambda value: _require_enum("value", value, enum_type)


def _instance_parser(model: type[_ModelT]) -> _Parser:  # noqa: UP047
    return lambda value: value if isinstance(value, model) else model.from_wire(value)


def _optional_parser(parser: _Parser) -> _Parser:
    return lambda value: None if value is None else parser(value)


def _tuple_parser(parser: _Parser, field: str) -> _Parser:
    def parse(value: object) -> tuple[object, ...]:
        if not isinstance(value, tuple | list):
            raise TypeError(f"{field} must be a tuple or list")
        return tuple(parser(item) for item in value)

    return parse


def _wire_value(value: object) -> JSONValue:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, _WireModel):
        return value.to_wire()
    if isinstance(value, tuple):
        return [_wire_value(item) for item in value]
    return cast(JSONValue, value)


class _WireModel:
    _WIRE_KEYS: ClassVar[set[str]]
    _WIRE_NAMES: ClassVar[dict[str, str]] = {}
    _PARSERS: ClassVar[dict[str, _Parser]] = {}

    def __post_init__(self) -> None:
        for field_name, parser in self._PARSERS.items():
            object.__setattr__(self, field_name, parser(getattr(self, field_name)))

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            self._WIRE_NAMES.get(field.name, field.name): _wire_value(
                getattr(self, field.name)
            )
            for field in fields(cast(Any, self))
        }

    @classmethod
    def from_wire(cls: type[_ModelT], value: object) -> _ModelT:
        document = _require_object(value, cls._WIRE_KEYS, cls.__name__)
        kwargs: dict[str, object] = {}
        for field_name, parser in cls._PARSERS.items():
            wire_name = cls._WIRE_NAMES.get(field_name, field_name)
            kwargs[field_name] = parser(document[wire_name])
        return cls(**cast(Any, kwargs))


@dataclass(frozen=True, slots=True)
class UnknownValueV1(_WireModel):
    reason: UnknownReasonV1
    hint: str | None
    _WIRE_KEYS: ClassVar[set[str]] = {"reason", "hint"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "reason": _enum_parser(UnknownReasonV1),
        "hint": _optional_text_parser("hint"),
    }


@dataclass(frozen=True, slots=True)
class EntityRefV1(_WireModel):
    role: EntityRoleV1
    multiplicity: MultiplicityV1
    ordinal: int | None
    _WIRE_KEYS: ClassVar[set[str]] = {"role", "multiplicity", "ordinal"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "role": _enum_parser(EntityRoleV1),
        "multiplicity": _enum_parser(MultiplicityV1),
        "ordinal": _optional_parser(
            lambda value: _require_int("ordinal", value, nonnegative=True)
        ),
    }


@dataclass(frozen=True, slots=True)
class ZoneRefV1(_WireModel):
    zone: ZoneNameV1
    label: str | None
    _WIRE_KEYS: ClassVar[set[str]] = {"zone", "label"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "zone": _enum_parser(ZoneNameV1),
        "label": _optional_text_parser("label"),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.label is not None and self.zone is not ZoneNameV1.UNKNOWN:
            raise ValueError("label is allowed only for unknown zones")


@dataclass(frozen=True, slots=True)
class QuantityV1(_WireModel):
    mode: QuantityModeV1
    value: int | str | UnknownValueV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {"mode", "value"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {"mode": _enum_parser(QuantityModeV1)}

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.mode is QuantityModeV1.EXACT:
            object.__setattr__(self, "value", _require_int("value", self.value))
        elif self.mode is QuantityModeV1.SYMBOLIC:
            object.__setattr__(self, "value", _require_text("value", self.value))
        elif self.mode in (QuantityModeV1.ALL, QuantityModeV1.EACH):
            if self.value is not None:
                raise ValueError(f"{self.mode.value} quantity value must be null")
        elif not isinstance(self.value, UnknownValueV1):
            raise TypeError("unknown quantity requires UnknownValueV1")

    @classmethod
    def from_wire(cls, value: object) -> QuantityV1:
        document = _require_object(value, cls._WIRE_KEYS, "quantity")
        mode = _require_enum("mode", document["mode"], QuantityModeV1)
        raw = document["value"]
        parsed = (
            UnknownValueV1.from_wire(raw)
            if mode is QuantityModeV1.UNKNOWN
            else cast(int | str | None, raw)
        )
        return cls(mode, parsed)


@dataclass(frozen=True, slots=True)
class CharacteristicRefV1(_WireModel):
    name: CharacteristicNameV1
    label: str | None
    _WIRE_KEYS: ClassVar[set[str]] = {"name", "label"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "name": _enum_parser(CharacteristicNameV1),
        "label": _optional_text_parser("label"),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.name is CharacteristicNameV1.OTHER and self.label is None:
            raise ValueError("other characteristics require an explicit label")
        if self.label is not None and self.name is not CharacteristicNameV1.OTHER:
            raise ValueError("label is allowed only for other characteristics")


@dataclass(frozen=True, slots=True)
class ParameterValueV1(_WireModel):
    value_type: ParameterValueTypeV1
    value: str | int | bool | SemanticDescriptorV1 | UnknownValueV1
    _WIRE_KEYS: ClassVar[set[str]] = {"type", "value"}
    _WIRE_NAMES: ClassVar[dict[str, str]] = {"value_type": "type"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "value_type": _enum_parser(ParameterValueTypeV1)
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        value = self.value
        if self.value_type is ParameterValueTypeV1.TEXT:
            _require_text("value", value)
        elif self.value_type is ParameterValueTypeV1.INTEGER:
            _require_int("value", value)
        elif self.value_type is ParameterValueTypeV1.BOOLEAN:
            _require_bool("value", value)
        elif self.value_type is ParameterValueTypeV1.DESCRIPTOR:
            if not isinstance(value, SemanticDescriptorV1):
                raise TypeError("descriptor value requires SemanticDescriptorV1")
        elif not isinstance(value, UnknownValueV1):
            raise TypeError("unknown value requires UnknownValueV1")

    @classmethod
    def from_wire(cls, value: object) -> ParameterValueV1:
        document = _require_object(value, cls._WIRE_KEYS, "parameter value")
        value_type = _require_enum("type", document["type"], ParameterValueTypeV1)
        raw = document["value"]
        if value_type is ParameterValueTypeV1.DESCRIPTOR:
            parsed: object = SemanticDescriptorV1.from_wire(raw)
        elif value_type is ParameterValueTypeV1.UNKNOWN:
            parsed = UnknownValueV1.from_wire(raw)
        else:
            parsed = raw
        return cls(value_type, cast(Any, parsed))


@dataclass(frozen=True, slots=True)
class SemanticDescriptorV1(_WireModel):
    shape: SemanticShapeV1
    label: str | None
    subject: EntityRefV1 | None
    object_ref: EntityRefV1 | None
    value: ParameterValueV1 | None
    children: tuple[SemanticDescriptorV1, ...]
    _WIRE_KEYS: ClassVar[set[str]] = {
        "shape",
        "label",
        "subject",
        "object",
        "value",
        "children",
    }
    _WIRE_NAMES: ClassVar[dict[str, str]] = {"object_ref": "object"}

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.children, tuple | list):
            raise TypeError("children must be a tuple or list")
        if any(not isinstance(child, SemanticDescriptorV1) for child in self.children):
            raise TypeError("children must contain SemanticDescriptorV1 values")
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True, slots=True)
class CharacteristicAssignmentV1(_WireModel):
    characteristic: CharacteristicRefV1
    value: ParameterValueV1
    _WIRE_KEYS: ClassVar[set[str]] = {"characteristic", "value"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {
        "characteristic": _instance_parser(CharacteristicRefV1),
        "value": _instance_parser(ParameterValueV1),
    }


@dataclass(frozen=True, slots=True)
class DurationV1(_WireModel):
    kind: DurationKindV1
    value: SemanticDescriptorV1 | UnknownValueV1 | None
    _WIRE_KEYS: ClassVar[set[str]] = {"kind", "value"}
    _PARSERS: ClassVar[dict[str, _Parser]] = {"kind": _enum_parser(DurationKindV1)}

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind in (
            DurationKindV1.UNTIL_END_OF_TURN,
            DurationKindV1.THIS_TURN,
            DurationKindV1.PERMANENT,
        ):
            if self.value is not None:
                raise ValueError(f"{self.kind.value} duration value must be null")
        elif self.kind is DurationKindV1.DELAYED:
            if not isinstance(self.value, SemanticDescriptorV1):
                raise TypeError("delayed duration requires SemanticDescriptorV1")
        elif not isinstance(self.value, UnknownValueV1):
            raise TypeError("unknown duration requires UnknownValueV1")

    @classmethod
    def from_wire(cls, value: object) -> DurationV1:
        document = _require_object(value, cls._WIRE_KEYS, "duration")
        kind = _require_enum("kind", document["kind"], DurationKindV1)
        raw = document["value"]
        if kind is DurationKindV1.DELAYED:
            parsed: object = SemanticDescriptorV1.from_wire(raw)
        elif kind is DurationKindV1.UNKNOWN:
            parsed = UnknownValueV1.from_wire(raw)
        else:
            parsed = None if raw is None else raw
        return cls(kind, cast(Any, parsed))


SemanticDescriptorV1._PARSERS = {
    "shape": _enum_parser(SemanticShapeV1),
    "label": _optional_text_parser("label"),
    "subject": _optional_parser(_instance_parser(EntityRefV1)),
    "object_ref": _optional_parser(_instance_parser(EntityRefV1)),
    "value": _optional_parser(_instance_parser(ParameterValueV1)),
    "children": _tuple_parser(_instance_parser(SemanticDescriptorV1), "children"),
}
