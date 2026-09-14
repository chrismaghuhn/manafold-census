"""Code-owned M2 dimension paths, typed domains, and bindings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, ClassVar, NamedTuple, cast

from ..canonical import JSONValue
from ..semantic.kinds import (
    PAYLOAD_OPTIONAL_KEYS,
    PAYLOAD_REQUIRED_KEYS,
    RequirementFamilyV1,
    RequirementKindV1,
    family_for_kind,
    validate_kind_family,
)
from ..semantic.primitives import (
    CharacteristicRefV1,
    CostOperationV1,
    DurationV1,
    EntityRefV1,
    ModificationOperationV1,
    ParameterValueV1,
    QuantityV1,
    SemanticDescriptorV1,
    SemanticShapeV1,
    SubjectKindV1,
    UnknownReasonV1,
    ZoneRefV1,
    _require_bool,
    _require_enum,
    _require_object,
    _require_text,
    _validate_json_wire,
)
from .model import ExclusionV1  # noqa: F401


class DimensionKindV1(StrEnum):
    ENTITY_REF = "ENTITY_REF"
    QUANTITY = "QUANTITY"
    ZONE_REF = "ZONE_REF"
    CHARACTERISTIC_REF = "CHARACTERISTIC_REF"
    PARAMETER_VALUE = "PARAMETER_VALUE"
    SEMANTIC_DESCRIPTOR = "SEMANTIC_DESCRIPTOR"
    DURATION = "DURATION"
    M2_ENUM = "M2_ENUM"
    BOOLEAN = "BOOLEAN"
    RELATIONSHIP_ORDINAL = "RELATIONSHIP_ORDINAL"


class DimensionDomainKindV1(StrEnum):
    ANY_TYPED_VALUE = "ANY_TYPED_VALUE"
    M2_ENUM_SUBSET = "M2_ENUM_SUBSET"
    M2_SHAPE_SUBSET = "M2_SHAPE_SUBSET"


class BindingStateV1(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class UnknownPolicyV1(StrEnum):
    EXPLICIT_BUT_NOT_ACTIVE = "EXPLICIT_BUT_NOT_ACTIVE"


_UNTRAVERSED_FIELDS = frozenset(
    {"alternatives", "characteristics", "expansion_state", "keyword", "keyword_index"}
)
_M2_PATH_NAMES = (  # noqa: SIM905 - explicit closed registry order
    "DRAW_CARDS_DRAWER DRAW_CARDS_QUANTITY "
    "MOVE_BETWEEN_ZONES_SUBJECT MOVE_BETWEEN_ZONES_FROM_ZONE "
    "MOVE_BETWEEN_ZONES_TO_ZONE MOVE_BETWEEN_ZONES_QUANTITY "
    "MOVE_BETWEEN_ZONES_CAUSE CREATE_OBJECT_OBJECT_CLASS "
    "CREATE_OBJECT_QUANTITY CREATE_OBJECT_DURATION SELECT_CHOOSER "
    "SELECT_SUBJECT_KIND SELECT_QUANTITY SELECT_RESTRICTION SELECT_TARGETING "
    "MODIFY_CHARACTERISTIC_SUBJECT MODIFY_CHARACTERISTIC_CHARACTERISTIC "
    "MODIFY_CHARACTERISTIC_OPERATION MODIFY_CHARACTERISTIC_VALUE "
    "APPLY_CONTINUOUS_EFFECT_SUBJECT APPLY_CONTINUOUS_EFFECT_DURATION "
    "APPLY_CONTINUOUS_EFFECT_EFFECT SEARCH_ZONE_SEARCHER SEARCH_ZONE_ZONE "
    "SEARCH_ZONE_SELECTION SEARCH_ZONE_DESTINATION SEARCH_ZONE_REVEAL "
    "DEAL_DAMAGE_SOURCE DEAL_DAMAGE_RECIPIENT DEAL_DAMAGE_AMOUNT "
    "CREATE_DELAYED_EFFECT_DELAY CREATE_DELAYED_EFFECT_EFFECT "
    "TRIGGER_FROM_EVENT_EVENT TRIGGER_FROM_EVENT_CONTROLLER "
    "TRIGGER_FROM_EVENT_CONDITION REPLACE_EVENT_EVENT "
    "REPLACE_EVENT_REPLACEMENT PAY_COST_PAYER PAY_COST_COST "
    "MODIFY_COST_SUBJECT MODIFY_COST_COST MODIFY_COST_OPERATION "
    "CHOOSE_MODE_CHOOSER CHOOSE_MODE_MINIMUM CHOOSE_MODE_MAXIMUM "
    "CONDITIONAL_EFFECT_CONDITION CONDITIONAL_EFFECT_THEN_EFFECT "
    "CONDITIONAL_EFFECT_ELSE_EFFECT KEYWORD_REFERENCE_EXPANSION"
).split(" ")


class M2DimensionPathV1(StrEnum):
    locals().update({name: name for name in _M2_PATH_NAMES})

    @classmethod
    def from_wire(cls, value: object) -> M2DimensionPathV1:
        if not isinstance(value, str):
            raise TypeError("M2 dimension path must be a string")
        try:
            return cls(value)
        except ValueError as error:
            raise ValueError("unknown M2 dimension path") from error


class DimensionPathSpecV1(NamedTuple):
    path_key: M2DimensionPathV1
    family: RequirementFamilyV1
    kind: RequirementKindV1
    parameter_path: str
    value_type: type[Any]
    dimension_kind: DimensionKindV1
    optional: bool
    enum_values: tuple[str, ...] = ()


type _EnumType = type[StrEnum] | None
type _FieldSpec = tuple[type[Any], DimensionKindV1, _EnumType]


def _field_group(
    names: str, value_type: type[Any], dimension_kind: DimensionKindV1
) -> dict[str, _FieldSpec]:
    return {name: (value_type, dimension_kind, None) for name in names.split(" ")}


_FIELD_SPECS: Mapping[str, _FieldSpec] = MappingProxyType(
    _field_group(
        "subject drawer chooser searcher source recipient controller payer",
        EntityRefV1,
        DimensionKindV1.ENTITY_REF,
    )
    | _field_group(
        "from_zone to_zone zone destination", ZoneRefV1, DimensionKindV1.ZONE_REF
    )
    | _field_group(
        "quantity minimum maximum amount", QuantityV1, DimensionKindV1.QUANTITY
    )
    | _field_group(
        "cause restriction selection effect delay event condition replacement cost "
        "then_effect else_effect expansion",
        SemanticDescriptorV1,
        DimensionKindV1.SEMANTIC_DESCRIPTOR,
    )
    | _field_group("duration", DurationV1, DimensionKindV1.DURATION)
    | _field_group(
        "object_class value", ParameterValueV1, DimensionKindV1.PARAMETER_VALUE
    )
    | _field_group(
        "characteristic", CharacteristicRefV1, DimensionKindV1.CHARACTERISTIC_REF
    )
    | _field_group("targeting reveal", bool, DimensionKindV1.BOOLEAN)
    | {"subject_kind": (SubjectKindV1, DimensionKindV1.M2_ENUM, SubjectKindV1)}
)


def _enum_field_spec(enum_type: type[StrEnum]) -> _FieldSpec:
    return enum_type, DimensionKindV1.M2_ENUM, enum_type


_OPERATION_SPECS: Mapping[RequirementKindV1, _FieldSpec] = MappingProxyType(
    {
        RequirementKindV1.MODIFY_CHARACTERISTIC: _enum_field_spec(
            ModificationOperationV1
        ),
        RequirementKindV1.MODIFY_COST: _enum_field_spec(CostOperationV1),
    }
)


def _field_spec(kind: RequirementKindV1, field: str) -> _FieldSpec:
    if field == "operation":
        override = _OPERATION_SPECS.get(kind)
        if override is not None:
            return override
    try:
        return _FIELD_SPECS[field]
    except KeyError as error:
        raise RuntimeError(
            f"unregistered M2 dimension field: {kind.value}.{field}"
        ) from error


def _build_registry() -> Mapping[M2DimensionPathV1, DimensionPathSpecV1]:
    result: dict[M2DimensionPathV1, DimensionPathSpecV1] = {}
    for kind in RequirementKindV1:
        if kind is RequirementKindV1.UNRESOLVED:
            continue
        family = family_for_kind(kind)
        fields = (
            PAYLOAD_REQUIRED_KEYS[kind] | PAYLOAD_OPTIONAL_KEYS[kind]
        ) - _UNTRAVERSED_FIELDS
        for field in sorted(fields):
            path_key = M2DimensionPathV1[f"{kind.name}_{field.upper()}"]
            value_type, dimension_kind, enum_type = _field_spec(kind, field)
            result[path_key] = DimensionPathSpecV1(
                path_key=path_key,
                family=family,
                kind=kind,
                parameter_path=f"/parameters/{field}",
                value_type=value_type,
                dimension_kind=dimension_kind,
                optional=field in PAYLOAD_OPTIONAL_KEYS[kind],
                enum_values=()
                if enum_type is None
                else tuple(str(member.value) for member in enum_type),
            )
    if set(result) != set(M2DimensionPathV1):
        raise RuntimeError("M2 dimension path registry is incomplete")
    return MappingProxyType(result)


M2_DIMENSION_PATH_REGISTRY = _build_registry()


def _path_key(value: object) -> M2DimensionPathV1:
    if isinstance(value, M2DimensionPathV1):
        return value
    return M2DimensionPathV1.from_wire(value)


def dimension_spec_for(path_key: object) -> DimensionPathSpecV1:
    return M2_DIMENSION_PATH_REGISTRY[_path_key(path_key)]


def registered_paths_for(
    family: RequirementFamilyV1, kind: RequirementKindV1
) -> tuple[M2DimensionPathV1, ...]:
    validate_kind_family(family, kind)
    return tuple(
        path
        for path, spec in sorted(
            M2_DIMENSION_PATH_REGISTRY.items(), key=lambda item: item[0].value
        )
        if spec.family is family and spec.kind is kind
    )


def _values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


def _strings(value: object, field: str) -> tuple[str, ...]:
    values = tuple(_require_text(field, item) for item in _values(value, field))
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(sorted(values))


def _shapes(value: object, field: str) -> tuple[SemanticShapeV1, ...]:
    values = tuple(
        _require_enum(field, item, SemanticShapeV1) for item in _values(value, field)
    )
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _domain_wire(
    prefix: str,
    kind: DimensionDomainKindV1,
    enum_values: tuple[str, ...],
    shapes: tuple[SemanticShapeV1, ...],
) -> dict[str, JSONValue]:
    return {
        "kind": kind.value,
        f"{prefix}_enum_values": list(enum_values),
        f"{prefix}_shapes": [shape.value for shape in shapes],
    }


def _parse_domain(
    value: object, prefix: str
) -> tuple[DimensionDomainKindV1, tuple[str, ...], tuple[SemanticShapeV1, ...]]:
    enum_field = f"{prefix}_enum_values"
    shape_field = f"{prefix}_shapes"
    domain = _require_object(
        value, {"kind", enum_field, shape_field}, f"{prefix} domain"
    )
    return (
        _require_enum("domain_kind", domain["kind"], DimensionDomainKindV1),
        _strings(domain[enum_field], enum_field),
        _shapes(domain[shape_field], shape_field),
    )


def _validate_domain(
    path_key: M2DimensionPathV1,
    domain_kind: DimensionDomainKindV1,
    enum_values: tuple[str, ...],
    shapes: tuple[SemanticShapeV1, ...],
    field: str,
) -> None:
    spec = dimension_spec_for(path_key)
    if domain_kind is DimensionDomainKindV1.ANY_TYPED_VALUE:
        if enum_values or shapes:
            raise ValueError(f"{field} ANY_TYPED_VALUE must have empty subsets")
        return
    if domain_kind is DimensionDomainKindV1.M2_ENUM_SUBSET:
        if shapes:
            raise ValueError(f"{field} enum subset cannot contain shapes")
        if not spec.enum_values or not set(enum_values).issubset(spec.enum_values):
            raise ValueError(f"{field} contains a value outside the registered M2 enum")
        return
    if enum_values:
        raise ValueError(f"{field} shape subset cannot contain enum values")
    if spec.value_type is not SemanticDescriptorV1:
        raise ValueError(f"{field} shape subset requires a SemanticDescriptorV1 path")


@dataclass(frozen=True, slots=True)
class CapabilityDimensionV1:
    path_key: M2DimensionPathV1
    dimension_kind: DimensionKindV1
    required: bool
    domain_kind: DimensionDomainKindV1
    allowed_enum_values: tuple[str, ...] = ()
    allowed_shapes: tuple[SemanticShapeV1, ...] = ()
    unknown_policy: UnknownPolicyV1 = UnknownPolicyV1.EXPLICIT_BUT_NOT_ACTIVE

    _WIRE_KEYS: ClassVar[set[str]] = {
        "path_key",
        "dimension_kind",
        "required",
        "domain",
        "unknown_policy",
    }  # noqa: E501

    def __post_init__(self) -> None:
        path_key = _path_key(self.path_key)
        dimension_kind = _require_enum(
            "dimension_kind", self.dimension_kind, DimensionKindV1
        )
        if dimension_spec_for(path_key).dimension_kind is not dimension_kind:
            raise ValueError("dimension_kind does not match the registered M2 path")
        required = _require_bool("required", self.required)
        domain_kind = _require_enum(
            "domain_kind", self.domain_kind, DimensionDomainKindV1
        )
        enum_values = _strings(self.allowed_enum_values, "allowed_enum_values")
        shapes = _shapes(self.allowed_shapes, "allowed_shapes")
        unknown_policy = _require_enum(
            "unknown_policy", self.unknown_policy, UnknownPolicyV1
        )
        _validate_domain(path_key, domain_kind, enum_values, shapes, "dimension domain")
        object.__setattr__(self, "path_key", path_key)
        object.__setattr__(self, "dimension_kind", dimension_kind)
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "domain_kind", domain_kind)
        object.__setattr__(self, "allowed_enum_values", enum_values)
        object.__setattr__(self, "allowed_shapes", shapes)
        object.__setattr__(self, "unknown_policy", unknown_policy)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "path_key": self.path_key.value,
            "dimension_kind": self.dimension_kind.value,
            "required": self.required,
            "domain": _domain_wire(
                "allowed",
                self.domain_kind,
                self.allowed_enum_values,
                self.allowed_shapes,
            ),
            "unknown_policy": self.unknown_policy.value,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityDimensionV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability dimension")
        domain_kind, enum_values, shapes = _parse_domain(document["domain"], "allowed")
        result = cls(
            path_key=_path_key(document["path_key"]),
            dimension_kind=_require_enum(
                "dimension_kind", document["dimension_kind"], DimensionKindV1
            ),
            required=_require_bool("required", document["required"]),
            domain_kind=domain_kind,
            allowed_enum_values=enum_values,
            allowed_shapes=shapes,
            unknown_policy=_require_enum(
                "unknown_policy", document["unknown_policy"], UnknownPolicyV1
            ),
        )
        if result.to_wire() != document:
            raise ValueError("capability dimension wire is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class ParameterBindingV1:
    path_key: M2DimensionPathV1
    state: BindingStateV1
    value: JSONValue | None
    reason: str | None
    m2_unknown_path: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {"path_key", "binding"}

    def __post_init__(self) -> None:
        path_key = _path_key(self.path_key)
        state = _require_enum("state", self.state, BindingStateV1)
        if self.value is not None:
            _validate_json_wire(self.value, "binding.value")
        spec = dimension_spec_for(path_key)
        reason = self.reason
        unknown_path = self.m2_unknown_path
        if state is BindingStateV1.KNOWN:
            if self.value is None:
                raise ValueError("KNOWN binding requires a value")
            if reason is not None or unknown_path is not None:
                raise ValueError("KNOWN binding cannot contain unknown metadata")
        elif state is BindingStateV1.UNKNOWN:
            if self.value is not None:
                raise ValueError("UNKNOWN binding cannot contain a value")
            reason_value = _require_enum("reason", reason, UnknownReasonV1)
            unknown_path = _require_text("m2_unknown_path", unknown_path)
            if unknown_path != spec.parameter_path:
                raise ValueError("m2_unknown_path does not match the registered path")
            reason = reason_value.value
        else:
            if not spec.optional:
                raise ValueError("NOT_APPLICABLE requires an optional M2 path")
            if self.value is not None or reason is not None or unknown_path is not None:
                raise ValueError(
                    "NOT_APPLICABLE binding must have no value or metadata"
                )

        object.__setattr__(self, "path_key", path_key)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "m2_unknown_path", unknown_path)

    @classmethod
    def known(cls, path_key: object, value: JSONValue) -> ParameterBindingV1:
        return cls(_path_key(path_key), BindingStateV1.KNOWN, value, None, None)

    @classmethod
    def unknown(
        cls, path_key: M2DimensionPathV1, reason: str, unknown_path: str
    ) -> ParameterBindingV1:
        return cls(path_key, BindingStateV1.UNKNOWN, None, reason, unknown_path)

    @classmethod
    def not_applicable(cls, path_key: object) -> ParameterBindingV1:
        return cls(_path_key(path_key), BindingStateV1.NOT_APPLICABLE, None, None, None)

    def to_wire(self) -> dict[str, JSONValue]:
        binding: dict[str, JSONValue] = {"state": self.state.value}
        if self.state is BindingStateV1.KNOWN:
            binding["value"] = cast(JSONValue, self.value)
        elif self.state is BindingStateV1.UNKNOWN:
            binding.update(
                {
                    "reason": cast(str, self.reason),
                    "m2_unknown_path": cast(str, self.m2_unknown_path),
                }
            )
        return {"path_key": self.path_key.value, "binding": binding}

    @classmethod
    def from_wire(cls, value: object) -> ParameterBindingV1:
        document = _require_object(value, cls._WIRE_KEYS, "parameter binding")
        path_key = _path_key(document["path_key"])
        binding = document["binding"]
        if not isinstance(binding, dict):
            raise TypeError("binding must be an object")
        state = _require_enum("binding.state", binding.get("state"), BindingStateV1)
        if state is BindingStateV1.KNOWN:
            inner = _require_object(binding, {"state", "value"}, "known binding")
            result = cls(path_key, state, cast(JSONValue, inner["value"]), None, None)
        elif state is BindingStateV1.UNKNOWN:
            inner = _require_object(
                binding, {"state", "reason", "m2_unknown_path"}, "unknown binding"
            )
            result = cls(
                path_key,
                state,
                None,
                cast(str, inner["reason"]),
                cast(str, inner["m2_unknown_path"]),
            )
        else:
            _require_object(binding, {"state"}, "not-applicable binding")
            result = cls(path_key, state, None, None, None)
        if result.to_wire() != document:
            raise ValueError("parameter binding wire is not canonical")
        return result
