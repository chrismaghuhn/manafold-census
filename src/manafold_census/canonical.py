"""Canonical JSON encoding for semantic Census values."""

from __future__ import annotations

import json

MAX_INTEGER = (1 << 63) - 1
MIN_INTEGER = -(1 << 63)

type JSONValue = None | bool | int | str | list["JSONValue"] | dict[str, "JSONValue"]


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
