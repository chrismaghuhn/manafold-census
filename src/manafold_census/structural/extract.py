"""Stream pinned source records into structural source-fact models."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from ..canonical import MAX_INTEGER, MIN_INTEGER
from ..corpus.index import CorpusIndexError, RecordIndexEntry, parse_source_record
from .model import (
    StructuralCardRecordV1,
    StructuralFaceV1,
    StructuralRelatedPartV1,
)

_FACE_STRING_FIELDS = (
    "mana_cost",
    "type_line",
    "oracle_text",
    "power",
    "toughness",
    "loyalty",
    "defense",
)
_FACE_ARRAY_FIELDS = ("colors", "color_indicator")
_RELATED_PART_FIELDS = ("component", "id", "name", "object", "type_line", "uri")


class StructuralExtractionError(ValueError):
    """Raised when a raw source record cannot satisfy the M1 shape contract."""


def _location(line_number: int, field: str) -> str:
    return f"source line {line_number} field {field}"


def _required_string(
    document: dict[str, object],
    field: str,
    line_number: int,
    *,
    non_empty: bool,
    display_field: str | None = None,
) -> str:
    location = _location(line_number, display_field or field)
    if field not in document:
        raise StructuralExtractionError(f"{location} is missing")
    value = document[field]
    if value is None:
        raise StructuralExtractionError(f"{location} has explicit source null")
    if not isinstance(value, str):
        raise StructuralExtractionError(f"{location} must be a string")
    if non_empty and value == "":
        raise StructuralExtractionError(f"{location} must be non-empty")
    return value


def _optional_string(
    document: dict[str, object], field: str, line_number: int
) -> str | None:
    if field not in document:
        return None
    return _required_string(document, field, line_number, non_empty=False)


def _optional_string_array(
    document: dict[str, object], field: str, line_number: int
) -> list[str] | None:
    if field not in document:
        return None
    location = _location(line_number, field)
    value = document[field]
    if value is None:
        raise StructuralExtractionError(f"{location} has explicit source null")
    if not isinstance(value, list):
        raise StructuralExtractionError(f"{location} must be an array")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise StructuralExtractionError(f"{location}[{index}] must be a string")
        result.append(item)
    return result


def _optional_integer_array(
    document: dict[str, object], field: str, line_number: int
) -> list[int] | None:
    if field not in document:
        return None
    location = _location(line_number, field)
    value = document[field]
    if value is None:
        raise StructuralExtractionError(f"{location} has explicit source null")
    if not isinstance(value, list):
        raise StructuralExtractionError(f"{location} must be an array")
    result: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise StructuralExtractionError(f"{location}[{index}] must be an integer")
        if item < MIN_INTEGER or item > MAX_INTEGER:
            raise StructuralExtractionError(
                f"{location}[{index}] is outside the signed 64-bit range"
            )
        result.append(item)
    return result


def _string_tuple(values: list[str] | None) -> tuple[str, ...] | None:
    return tuple(values) if values is not None else None


def _integer_tuple(values: list[int] | None) -> tuple[int, ...] | None:
    return tuple(values) if values is not None else None


def _face_from_source(
    value: object, face_index: int, line_number: int
) -> StructuralFaceV1:
    if not isinstance(value, dict):
        raise StructuralExtractionError(
            f"source line {line_number} card_faces[{face_index}] must be an object"
        )
    name = _required_string(value, "name", line_number, non_empty=True)
    strings = {
        field: _optional_string(value, field, line_number)
        for field in _FACE_STRING_FIELDS
    }
    arrays = {
        field: _optional_string_array(value, field, line_number)
        for field in _FACE_ARRAY_FIELDS
    }
    return StructuralFaceV1(
        face_index=face_index,
        name=name,
        mana_cost=strings["mana_cost"],
        type_line=strings["type_line"],
        oracle_text=strings["oracle_text"],
        colors=_string_tuple(arrays["colors"]),
        color_indicator=_string_tuple(arrays["color_indicator"]),
        power=strings["power"],
        toughness=strings["toughness"],
        loyalty=strings["loyalty"],
        defense=strings["defense"],
    )


def _faces_from_source(
    document: dict[str, object], line_number: int
) -> list[StructuralFaceV1] | None:
    if "card_faces" not in document:
        return None
    value = document["card_faces"]
    location = _location(line_number, "card_faces")
    if value is None:
        raise StructuralExtractionError(f"{location} has explicit source null")
    if not isinstance(value, list):
        raise StructuralExtractionError(f"{location} must be an array")
    if not value:
        raise StructuralExtractionError(f"{location} must not be empty")
    return [
        _face_from_source(face, face_index, line_number)
        for face_index, face in enumerate(value)
    ]


def _related_parts_from_source(
    document: dict[str, object], line_number: int
) -> list[StructuralRelatedPartV1] | None:
    if "all_parts" not in document:
        return None
    value = document["all_parts"]
    location = _location(line_number, "all_parts")
    if value is None:
        raise StructuralExtractionError(f"{location} has explicit source null")
    if not isinstance(value, list):
        raise StructuralExtractionError(f"{location} must be an array")
    result: list[StructuralRelatedPartV1] = []
    for index, raw_part in enumerate(value):
        if not isinstance(raw_part, dict):
            raise StructuralExtractionError(f"{location}[{index}] must be an object")
        fields = {
            field: _required_string(
                raw_part,
                field,
                line_number,
                non_empty=False,
                display_field=f"all_parts[{index}].{field}",
            )
            for field in _RELATED_PART_FIELDS
        }
        result.append(
            StructuralRelatedPartV1(
                component=fields["component"],
                id=fields["id"],
                name=fields["name"],
                object_kind=fields["object"],
                type_line=fields["type_line"],
                uri=fields["uri"],
            )
        )
    return result


def _parse_source_document(
    raw_line: bytes, line_number: int
) -> tuple[RecordIndexEntry, dict[str, object]]:
    try:
        identity = parse_source_record(raw_line, line_number)
    except CorpusIndexError as error:
        raise StructuralExtractionError(str(error)) from error
    try:
        document = json.loads(raw_line)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StructuralExtractionError(
            f"source record line {line_number} is invalid JSON"
        ) from error
    if not isinstance(document, dict):
        raise StructuralExtractionError(
            f"source record line {line_number} must be an object"
        )
    return identity, cast(dict[str, object], document)


def parse_structural_source_record(
    raw_line: bytes, line_number: int
) -> StructuralCardRecordV1:
    """Project one exact source JSONL line into an immutable structural record."""

    identity, document = _parse_source_document(raw_line, line_number)
    layout = _required_string(document, "layout", line_number, non_empty=True)
    faces = _faces_from_source(document, line_number)
    all_parts = _related_parts_from_source(document, line_number)
    return StructuralCardRecordV1(
        oracle_id=identity.oracle_id,
        source_card_id=identity.source_card_id,
        source_record_sha256=identity.source_record_sha256,
        name=identity.name,
        layout=layout,
        mana_cost=_optional_string(document, "mana_cost", line_number),
        type_line=_optional_string(document, "type_line", line_number),
        oracle_text=_optional_string(document, "oracle_text", line_number),
        colors=_string_tuple(_optional_string_array(document, "colors", line_number)),
        color_identity=_string_tuple(
            _optional_string_array(document, "color_identity", line_number)
        ),
        color_indicator=_string_tuple(
            _optional_string_array(document, "color_indicator", line_number)
        ),
        keywords=_string_tuple(
            _optional_string_array(document, "keywords", line_number)
        ),
        produced_mana=_string_tuple(
            _optional_string_array(document, "produced_mana", line_number)
        ),
        power=_optional_string(document, "power", line_number),
        toughness=_optional_string(document, "toughness", line_number),
        loyalty=_optional_string(document, "loyalty", line_number),
        defense=_optional_string(document, "defense", line_number),
        hand_modifier=_optional_string(document, "hand_modifier", line_number),
        life_modifier=_optional_string(document, "life_modifier", line_number),
        attraction_lights=_integer_tuple(
            _optional_integer_array(document, "attraction_lights", line_number)
        ),
        faces=tuple(faces) if faces is not None else None,
        all_parts=tuple(all_parts) if all_parts is not None else None,
    )


def iter_structural_records(
    source_path: str | Path,
) -> Iterator[StructuralCardRecordV1]:
    """Yield structural records from one gzip JSONL source stream."""

    try:
        with gzip.open(source_path, "rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                yield parse_structural_source_record(raw_line, line_number)
    except StructuralExtractionError:
        raise
    except (EOFError, OSError) as error:
        raise StructuralExtractionError(
            f"source gzip JSONL could not be read: {error}"
        ) from error
