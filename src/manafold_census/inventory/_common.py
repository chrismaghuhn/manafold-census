"""Shared strict helpers and closed vocabularies for M6-02 artifacts."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import cast

from ..canonical import JSONValue

AUTHORITY_SCOPE = "NON_AUTHORITATIVE"
GROUPING_POLICY_ID = "m6-02.surface-grouping"
GROUPING_POLICY_VERSION = "1"
SHAPE_POLICY_ID = "m6-02.lexical-shape"
SHAPE_POLICY_VERSION = "1"

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_CENSUS_RELEASE = re.compile(r"^censusrel_[0-9a-f]{64}$")
SURFACE_ID = re.compile(r"^m6surf_[0-9a-f]{64}$")
GROUP_ID = re.compile(r"^m6grp_[0-9a-f]{64}$")
OPPORTUNITY_ID = re.compile(r"^m6opp_[0-9a-f]{64}$")


class SurfaceScopeV1(StrEnum):
    CARD_TEXT = "CARD_TEXT"
    FACE_TEXT = "FACE_TEXT"
    ABILITY_LINE = "ABILITY_LINE"


class GroupingLensV1(StrEnum):
    CARD_TEXT_EXACT = "CARD_TEXT_EXACT"
    FACE_TEXT_EXACT = "FACE_TEXT_EXACT"
    ABILITY_LINE_EXACT = "ABILITY_LINE_EXACT"
    CARD_TEXT_SHAPE = "CARD_TEXT_SHAPE"
    FACE_TEXT_SHAPE = "FACE_TEXT_SHAPE"
    ABILITY_LINE_SHAPE = "ABILITY_LINE_SHAPE"


class RecurrenceStatusV1(StrEnum):
    RECURRING = "RECURRING"
    SINGLETON = "SINGLETON"


class PlanningStatusV1(StrEnum):
    UNASSESSED = "UNASSESSED"


def object_with_keys(
    value: object, expected: set[str], label: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing properties: {missing}")
        if unexpected:
            details.append(f"unexpected properties: {unexpected}")
        raise ValueError(f"{label} has {'; '.join(details)}")
    return cast(dict[str, object], value)


def text(field: str, value: object, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if non_empty and value == "":
        raise ValueError(f"{field} must be non-empty")
    value.encode("utf-8")
    return value


def optional_text(field: str, value: object) -> str | None:
    return None if value is None else text(field, value, non_empty=False)


def digest(field: str, value: object) -> str:
    result = text(field, value)
    if _DIGEST.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return result


def uuid(field: str, value: object) -> str:
    result = text(field, value)
    if _UUID.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase UUID")
    return result


def census_release_id(field: str, value: object) -> str:
    result = text(field, value)
    if _CENSUS_RELEASE.fullmatch(result) is None:
        raise ValueError(f"{field} must have the censusrel_ form")
    return result


def nonnegative(field: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def optional_nonnegative(field: str, value: object) -> int | None:
    return None if value is None else nonnegative(field, value)


def strings(field: str, value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise TypeError(f"{field} must be an array or null")
    return tuple(
        text(f"{field}[{index}]", item, non_empty=False)
        for index, item in enumerate(value)
    )


def authority(value: object) -> str:
    result = text("authority_scope", value)
    if result != AUTHORITY_SCOPE:
        raise ValueError(f"authority_scope must be {AUTHORITY_SCOPE}")
    return result


def enum_value(field: str, value: object, enum_type: type[StrEnum]) -> StrEnum:
    if not isinstance(value, str):
        raise ValueError(f"{field} is not a supported value")
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} is not a supported value") from error


def pairs(field: str, value: object) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be an array")
    result: list[tuple[str, int]] = []
    for index, item in enumerate(value):
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"{field}[{index}] must be a two-item array")
        result.append(
            (
                text(f"{field}[{index}][0]", item[0], non_empty=False),
                nonnegative(f"{field}[{index}][1]", item[1]),
            )
        )
    normalized = tuple(result)
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{field} must be sorted")
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError(f"{field} must have unique keys")
    return normalized


def pair_wire(value: tuple[tuple[str, int], ...]) -> list[JSONValue]:
    return cast(list[JSONValue], [[key, count] for key, count in value])
