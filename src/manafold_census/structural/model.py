"""Immutable typed models for M1 structural source facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import MAX_INTEGER, MIN_INTEGER, JSONValue
from ..corpus.index import RecordIndexEntry

_CARD_SCHEMA = "census.structural-card.v1"


def _require_wire_object(
    value: object, expected_keys: set[str], label: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    actual_keys = set(value)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(actual_keys - expected_keys)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing properties: {missing}")
        if unexpected:
            details.append(f"unexpected properties: {unexpected}")
        raise ValueError(f"{label} has {'; '.join(details)}")
    return cast(dict[str, object], value)


def _require_schema(document: dict[str, object], expected: str) -> None:
    if document["schema"] != expected:
        raise ValueError(f"schema must be {expected}")


def _require_source_string(
    field: str, value: object, *, non_empty: bool = False
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if non_empty and value == "":
        raise ValueError(f"{field} must be non-empty")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field} must be valid UTF-8") from error
    return value


def _optional_source_string(field: str, value: object) -> str | None:
    if value is None:
        return None
    return _require_source_string(field, value)


def _optional_string_array(field: str, value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple):
        raise TypeError(f"{field} must be an array or null")
    items: list[str] = []
    for index, item in enumerate(value):
        items.append(_require_source_string(f"{field}[{index}]", item))
    return tuple(items)


def _optional_integer_array(field: str, value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple):
        raise TypeError(f"{field} must be an array or null")
    items: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise TypeError(f"{field}[{index}] must be an integer")
        if item < MIN_INTEGER or item > MAX_INTEGER:
            raise ValueError(f"{field}[{index}] is outside the signed 64-bit range")
        items.append(item)
    return tuple(items)


def _require_face_index(value: object) -> int:
    if type(value) is not int:
        raise TypeError("face_index must be an integer")
    if value < 0 or value > MAX_INTEGER:
        raise ValueError("face_index is outside the signed 64-bit range")
    return value


@dataclass(frozen=True, slots=True)
class StructuralRelatedPartV1:
    """One raw source relationship from the parent all_parts array."""

    component: str
    id: str
    name: str
    object_kind: str
    type_line: str
    uri: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "component",
        "id",
        "name",
        "object",
        "type_line",
        "uri",
    }

    def __post_init__(self) -> None:
        for field in ("component", "id", "name", "object_kind", "type_line", "uri"):
            value = getattr(self, field)
            object.__setattr__(self, field, _require_source_string(field, value))

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "component": self.component,
            "id": self.id,
            "name": self.name,
            "object": self.object_kind,
            "type_line": self.type_line,
            "uri": self.uri,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralRelatedPartV1:
        document = _require_wire_object(value, cls._WIRE_KEYS, "related part")
        return cls(
            component=cast(str, document["component"]),
            id=cast(str, document["id"]),
            name=cast(str, document["name"]),
            object_kind=cast(str, document["object"]),
            type_line=cast(str, document["type_line"]),
            uri=cast(str, document["uri"]),
        )


@dataclass(frozen=True, slots=True)
class StructuralFaceV1:
    """One source face retained in its exact source-array position."""

    face_index: int
    name: str
    mana_cost: str | None
    type_line: str | None
    oracle_text: str | None
    colors: tuple[str, ...] | None
    color_indicator: tuple[str, ...] | None
    power: str | None
    toughness: str | None
    loyalty: str | None
    defense: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "face_index",
        "name",
        "mana_cost",
        "type_line",
        "oracle_text",
        "colors",
        "color_indicator",
        "power",
        "toughness",
        "loyalty",
        "defense",
    }

    def __post_init__(self) -> None:
        object.__setattr__(self, "face_index", _require_face_index(self.face_index))
        object.__setattr__(
            self, "name", _require_source_string("name", self.name, non_empty=True)
        )
        for field in (
            "mana_cost",
            "type_line",
            "oracle_text",
            "power",
            "toughness",
            "loyalty",
            "defense",
        ):
            object.__setattr__(
                self,
                field,
                _optional_source_string(field, getattr(self, field)),
            )
        object.__setattr__(
            self, "colors", _optional_string_array("colors", self.colors)
        )
        object.__setattr__(
            self,
            "color_indicator",
            _optional_string_array("color_indicator", self.color_indicator),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "face_index": self.face_index,
            "name": self.name,
            "mana_cost": self.mana_cost,
            "type_line": self.type_line,
            "oracle_text": self.oracle_text,
            "colors": list(self.colors) if self.colors is not None else None,
            "color_indicator": (
                list(self.color_indicator) if self.color_indicator is not None else None
            ),
            "power": self.power,
            "toughness": self.toughness,
            "loyalty": self.loyalty,
            "defense": self.defense,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralFaceV1:
        document = _require_wire_object(value, cls._WIRE_KEYS, "structural face")
        return cls(
            face_index=cast(int, document["face_index"]),
            name=cast(str, document["name"]),
            mana_cost=cast(str | None, document["mana_cost"]),
            type_line=cast(str | None, document["type_line"]),
            oracle_text=cast(str | None, document["oracle_text"]),
            colors=_optional_string_array("colors", document["colors"]),
            color_indicator=_optional_string_array(
                "color_indicator", document["color_indicator"]
            ),
            power=cast(str | None, document["power"]),
            toughness=cast(str | None, document["toughness"]),
            loyalty=cast(str | None, document["loyalty"]),
            defense=cast(str | None, document["defense"]),
        )


@dataclass(frozen=True, slots=True)
class StructuralCardRecordV1:
    """One immutable structural source-fact projection."""

    oracle_id: str
    source_card_id: str
    source_record_sha256: str
    name: str
    layout: str
    mana_cost: str | None
    type_line: str | None
    oracle_text: str | None
    colors: tuple[str, ...] | None
    color_identity: tuple[str, ...] | None
    color_indicator: tuple[str, ...] | None
    keywords: tuple[str, ...] | None
    produced_mana: tuple[str, ...] | None
    power: str | None
    toughness: str | None
    loyalty: str | None
    defense: str | None
    hand_modifier: str | None
    life_modifier: str | None
    attraction_lights: tuple[int, ...] | None
    faces: tuple[StructuralFaceV1, ...] | None
    all_parts: tuple[StructuralRelatedPartV1, ...] | None

    SCHEMA: ClassVar[str] = _CARD_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "oracle_id",
        "source_card_id",
        "source_record_sha256",
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

    def __post_init__(self) -> None:
        identity = RecordIndexEntry.from_wire(
            {
                "oracle_id": self.oracle_id,
                "source_card_id": self.source_card_id,
                "name": self.name,
                "source_record_sha256": self.source_record_sha256,
            }
        )
        object.__setattr__(self, "oracle_id", identity.oracle_id)
        object.__setattr__(self, "source_card_id", identity.source_card_id)
        object.__setattr__(self, "name", identity.name)
        object.__setattr__(self, "source_record_sha256", identity.source_record_sha256)
        object.__setattr__(
            self,
            "layout",
            _require_source_string("layout", self.layout, non_empty=True),
        )
        for field in (
            "mana_cost",
            "type_line",
            "oracle_text",
            "power",
            "toughness",
            "loyalty",
            "defense",
            "hand_modifier",
            "life_modifier",
        ):
            object.__setattr__(
                self,
                field,
                _optional_source_string(field, getattr(self, field)),
            )
        for field in (
            "colors",
            "color_identity",
            "color_indicator",
            "keywords",
            "produced_mana",
        ):
            object.__setattr__(
                self,
                field,
                _optional_string_array(field, getattr(self, field)),
            )
        object.__setattr__(
            self,
            "attraction_lights",
            _optional_integer_array("attraction_lights", self.attraction_lights),
        )
        if self.faces is None:
            normalized_faces: tuple[StructuralFaceV1, ...] | None = None
        else:
            if not isinstance(self.faces, list | tuple):
                raise TypeError("faces must be an array or null")
            if not self.faces:
                raise ValueError("faces must not be empty")
            if any(not isinstance(face, StructuralFaceV1) for face in self.faces):
                raise TypeError("faces must contain StructuralFaceV1 values")
            normalized_faces = tuple(self.faces)
        object.__setattr__(self, "faces", normalized_faces)
        if self.all_parts is None:
            normalized_parts: tuple[StructuralRelatedPartV1, ...] | None = None
        else:
            if not isinstance(self.all_parts, list | tuple):
                raise TypeError("all_parts must be an array or null")
            if any(
                not isinstance(part, StructuralRelatedPartV1) for part in self.all_parts
            ):
                raise TypeError("all_parts must contain StructuralRelatedPartV1 values")
            normalized_parts = tuple(self.all_parts)
        object.__setattr__(self, "all_parts", normalized_parts)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "source_record_sha256": self.source_record_sha256,
            "name": self.name,
            "layout": self.layout,
            "mana_cost": self.mana_cost,
            "type_line": self.type_line,
            "oracle_text": self.oracle_text,
            "colors": list(self.colors) if self.colors is not None else None,
            "color_identity": (
                list(self.color_identity) if self.color_identity is not None else None
            ),
            "color_indicator": (
                list(self.color_indicator) if self.color_indicator is not None else None
            ),
            "keywords": list(self.keywords) if self.keywords is not None else None,
            "produced_mana": (
                list(self.produced_mana) if self.produced_mana is not None else None
            ),
            "power": self.power,
            "toughness": self.toughness,
            "loyalty": self.loyalty,
            "defense": self.defense,
            "hand_modifier": self.hand_modifier,
            "life_modifier": self.life_modifier,
            "attraction_lights": (
                list(self.attraction_lights)
                if self.attraction_lights is not None
                else None
            ),
            "faces": (
                [face.to_wire() for face in self.faces]
                if self.faces is not None
                else None
            ),
            "all_parts": (
                [part.to_wire() for part in self.all_parts]
                if self.all_parts is not None
                else None
            ),
        }

    def task01_identity(self) -> RecordIndexEntry:
        return RecordIndexEntry(
            oracle_id=self.oracle_id,
            source_card_id=self.source_card_id,
            name=self.name,
            source_record_sha256=self.source_record_sha256,
        )

    @classmethod
    def from_wire(cls, value: object) -> StructuralCardRecordV1:
        document = _require_wire_object(value, cls._WIRE_KEYS, "structural card")
        _require_schema(document, cls.SCHEMA)
        raw_faces = document["faces"]
        faces: list[StructuralFaceV1] | None = None
        if raw_faces is not None:
            if not isinstance(raw_faces, list):
                raise TypeError("faces must be an array or null")
            faces = [StructuralFaceV1.from_wire(face) for face in raw_faces]
        raw_parts = document["all_parts"]
        parts: list[StructuralRelatedPartV1] | None = None
        if raw_parts is not None:
            if not isinstance(raw_parts, list):
                raise TypeError("all_parts must be an array or null")
            parts = [StructuralRelatedPartV1.from_wire(part) for part in raw_parts]
        return cls(
            oracle_id=cast(str, document["oracle_id"]),
            source_card_id=cast(str, document["source_card_id"]),
            source_record_sha256=cast(str, document["source_record_sha256"]),
            name=cast(str, document["name"]),
            layout=cast(str, document["layout"]),
            mana_cost=cast(str | None, document["mana_cost"]),
            type_line=cast(str | None, document["type_line"]),
            oracle_text=cast(str | None, document["oracle_text"]),
            colors=_optional_string_array("colors", document["colors"]),
            color_identity=_optional_string_array(
                "color_identity", document["color_identity"]
            ),
            color_indicator=_optional_string_array(
                "color_indicator", document["color_indicator"]
            ),
            keywords=_optional_string_array("keywords", document["keywords"]),
            produced_mana=_optional_string_array(
                "produced_mana", document["produced_mana"]
            ),
            power=cast(str | None, document["power"]),
            toughness=cast(str | None, document["toughness"]),
            loyalty=cast(str | None, document["loyalty"]),
            defense=cast(str | None, document["defense"]),
            hand_modifier=cast(str | None, document["hand_modifier"]),
            life_modifier=cast(str | None, document["life_modifier"]),
            attraction_lights=_optional_integer_array(
                "attraction_lights", document["attraction_lights"]
            ),
            faces=tuple(faces) if faces is not None else None,
            all_parts=tuple(parts) if parts is not None else None,
        )
