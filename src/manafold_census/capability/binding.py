"""Typed M2 parameter bindings and Requirement recomputation validation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any, ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..semantic.kind_payloads import payload_to_wire
from ..semantic.model import RequirementV1
from ..semantic.primitives import (
    UnknownReasonV1,
    UnknownValueV1,
    _require_bool,
    _require_enum,
    _require_object,
    _require_text,
    _validate_json_wire,
    _WireModel,
)
from .dimensions import M2DimensionPathV1, _path_key, dimension_spec_for


class BindingStateV1(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def _typed_known_value(path_key: M2DimensionPathV1, value: object) -> JSONValue:
    _validate_json_wire(value, "binding.value")
    spec = dimension_spec_for(path_key)
    value_type = spec.value_type
    if value_type is bool:
        parsed_value: object = _require_bool("binding.value", value)
        canonical: JSONValue = cast(bool, parsed_value)
    elif isinstance(value_type, type) and issubclass(value_type, StrEnum):
        parsed_value = _require_enum("binding.value", value, value_type)
        canonical = cast(StrEnum, parsed_value).value
    elif isinstance(value_type, type) and issubclass(value_type, _WireModel):
        parsed_value = value_type.from_wire(value)
        canonical = cast(JSONValue, parsed_value.to_wire())
    else:
        raise TypeError("registered M2 value type is not supported")
    if _contains_unknown(parsed_value):
        raise ValueError("KNOWN binding cannot contain an unknown M2 value")
    if canonical_json_bytes(canonical) != canonical_json_bytes(value):
        raise ValueError("binding value is not canonical for the registered M2 path")
    return canonical


def _contains_unknown(value: object) -> bool:
    if isinstance(value, UnknownValueV1):
        return True
    if isinstance(value, StrEnum) and value.value == "unknown":
        return True
    if isinstance(value, _WireModel):
        return any(
            _contains_unknown(getattr(value, item.name))
            for item in fields(cast(Any, value))
        )
    if isinstance(value, tuple | list):
        return any(_contains_unknown(item) for item in value)
    return False


@dataclass(frozen=True, slots=True)
class ParameterBindingV1:
    path_key: M2DimensionPathV1
    state: BindingStateV1
    value: JSONValue | None
    reason: str | None
    m2_unknown_path: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {"path_key", "binding"}

    def __post_init__(self) -> None:
        path = _path_key(self.path_key)
        state_value = _require_enum("state", self.state, BindingStateV1)
        spec = dimension_spec_for(path)
        canonical_value = self.value
        reason_value = self.reason
        unknown_path = self.m2_unknown_path
        if state_value is BindingStateV1.KNOWN:
            if self.value is None:
                raise ValueError("KNOWN binding requires a value")
            if self.reason is not None or self.m2_unknown_path is not None:
                raise ValueError("KNOWN binding cannot contain unknown metadata")
            canonical_value = _typed_known_value(path, self.value)
        elif state_value is BindingStateV1.UNKNOWN:
            if self.value is not None:
                raise ValueError("UNKNOWN binding cannot contain a value")
            reason_value = _require_enum("reason", self.reason, UnknownReasonV1).value
            unknown_path = _require_text("m2_unknown_path", self.m2_unknown_path)
            if unknown_path != spec.parameter_path:
                raise ValueError("m2_unknown_path does not match the registered path")
        elif not spec.optional:
            raise ValueError("NOT_APPLICABLE requires an optional M2 path")
        elif (
            self.value is not None
            or self.reason is not None
            or self.m2_unknown_path is not None
        ):
            raise ValueError("NOT_APPLICABLE binding must have no value or metadata")
        object.__setattr__(self, "path_key", path)
        object.__setattr__(self, "state", state_value)
        object.__setattr__(self, "value", canonical_value)
        object.__setattr__(self, "reason", reason_value)
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


def validate_binding_against_requirement(
    requirement: RequirementV1, binding: ParameterBindingV1
) -> None:
    if not isinstance(requirement, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    if not isinstance(binding, ParameterBindingV1):
        raise TypeError("binding must be ParameterBindingV1")
    spec = dimension_spec_for(binding.path_key)
    if (spec.family, spec.kind) != (requirement.family, requirement.kind):
        raise ValueError("binding path family/kind does not match Requirement")
    field = spec.parameter_path.removeprefix("/parameters/")
    parameters = payload_to_wire(
        requirement.family, requirement.kind, requirement.parameters
    )
    if field not in parameters:
        raise ValueError("registered binding path is absent from Requirement")
    actual_value = parameters[field]
    actual_typed_value = getattr(requirement.parameters, field)
    if binding.state is BindingStateV1.KNOWN:
        if _contains_unknown(actual_typed_value):
            raise ValueError("KNOWN binding cannot bind an unknown Requirement value")
        if actual_value is None:
            raise ValueError("KNOWN binding cannot represent an M2 null value")
        expected = _typed_known_value(binding.path_key, actual_value)
        if canonical_json_bytes(expected) != canonical_json_bytes(binding.value):
            raise ValueError("KNOWN binding does not match Requirement value")
    elif binding.state is BindingStateV1.UNKNOWN:
        if not _contains_unknown(actual_typed_value):
            raise ValueError("UNKNOWN binding requires an unknown M2 value")
        if binding.m2_unknown_path != spec.parameter_path:
            raise ValueError("UNKNOWN binding path does not match Requirement path")
        if binding.reason != requirement.resolution.reason.value:
            raise ValueError("UNKNOWN binding resolution reason does not match")
        if spec.parameter_path not in requirement.resolution.unknown_paths:
            raise ValueError(
                "UNKNOWN binding path is absent from Requirement resolution"
            )
    elif actual_value is not None:
        raise ValueError("NOT_APPLICABLE binding requires an actual M2 null value")


__all__ = [
    "BindingStateV1",
    "ParameterBindingV1",
    "validate_binding_against_requirement",
]
