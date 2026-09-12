"""Canonical JSON encoding for semantic Census values."""

from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import cast

MAX_INTEGER = (1 << 63) - 1
MIN_INTEGER = -(1 << 63)

type JSONValue = None | bool | int | str | list["JSONValue"] | dict[str, "JSONValue"]
type FrozenJSONValue = (
    None
    | bool
    | int
    | str
    | tuple["FrozenJSONValue", ...]
    | Mapping[str, "FrozenJSONValue"]
)


def _validate_json_value(value: object, path: str) -> None:
    if value is None or isinstance(value, bool):
        return

    if isinstance(value, int):
        if value < MIN_INTEGER or value > MAX_INTEGER:
            raise ValueError(f"{path}: integer is outside the signed 64-bit range")
        return

    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError(f"{path}: string is not valid UTF-8") from error
        return

    if isinstance(value, float):
        raise TypeError(f"{path}: float values are forbidden")

    if isinstance(value, set | frozenset):
        raise TypeError(f"{path}: set values are forbidden")

    if isinstance(value, tuple):
        raise TypeError(f"{path}: tuple values are forbidden; convert through a model")

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise TypeError(f"{path}: object string keys are required")
        for key in sorted(value):
            _validate_json_value(value[key], f"{path}.{key}")
        return

    raise TypeError(f"{path}: unsupported value type {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    """Return the explicit canonical UTF-8 JSON representation of ``value``.

    The accepted semantic values are null, booleans, signed 64-bit integers,
    strings, lists, and objects with string keys. Objects are sorted by their
    Unicode code-point key order. Output has no insignificant whitespace, no
    BOM, and no trailing newline. Strings are encoded as supplied; this
    function does not perform Unicode normalization.
    """

    _validate_json_value(value, "$")
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return encoded.encode("utf-8")


def freeze_json(value: object) -> FrozenJSONValue:
    """Copy restricted JSON into a recursively immutable representation."""

    _validate_json_value(value, "$")
    return _freeze_json_value(value)


def _freeze_json_value(value: object) -> FrozenJSONValue:
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    if isinstance(value, dict):
        frozen = {key: _freeze_json_value(item) for key, item in value.items()}
        return MappingProxyType(frozen)
    return cast(FrozenJSONValue, value)


def thaw_json(value: FrozenJSONValue) -> JSONValue:
    """Convert an immutable JSON model value back to explicit wire JSON."""

    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return value
