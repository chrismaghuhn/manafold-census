from datetime import datetime
from pathlib import Path

import pytest

from manafold_census.canonical import (
    MAX_INTEGER,
    MIN_INTEGER,
    canonical_json_bytes,
)


def test_canonical_json_bytes_sorts_object_keys() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_canonical_json_bytes_sorts_nested_object_keys() -> None:
    value = {"outer": {"z": [3, {"b": False, "a": None}], "a": "x"}}
    assert canonical_json_bytes(value) == (
        b'{"outer":{"a":"x","z":[3,{"a":null,"b":false}]}}'
    )


def test_canonical_json_bytes_has_exact_utf8_bytes_without_newline() -> None:
    assert canonical_json_bytes({"text": "Grüße", "ok": True}) == (
        b'{"ok":true,"text":"Gr\xc3\xbc\xc3\x9fe"}'
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (1.5, "float"),
        ({"values": {1, 2}}, "set"),
        ({1: "not-a-string-key"}, "string keys"),
        (("tuple",), "tuple"),
        (Path("relative.txt"), "Path"),
        (datetime(2026, 9, 12), "datetime"),
    ],
)
def test_canonical_json_bytes_rejects_non_contract_values(
    value: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        canonical_json_bytes(value)  # type: ignore[arg-type]


def test_canonical_json_bytes_accepts_signed_64_bit_integers() -> None:
    assert canonical_json_bytes({"min": MIN_INTEGER, "max": MAX_INTEGER}) == (
        b'{"max":9223372036854775807,"min":-9223372036854775808}'
    )


@pytest.mark.parametrize("value", [MIN_INTEGER - 1, MAX_INTEGER + 1])
def test_canonical_json_bytes_rejects_integers_outside_signed_64_bit_range(
    value: int,
) -> None:
    with pytest.raises(ValueError, match="64-bit"):
        canonical_json_bytes(value)


def test_canonical_json_bytes_does_not_unicode_normalize_strings() -> None:
    composed = "é"
    decomposed = "e\u0301"
    assert canonical_json_bytes(composed) != canonical_json_bytes(decomposed)
