"""Source-preserving surface and structural-summary models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ._common import (
    AUTHORITY_SCOPE,
    SURFACE_ID,
    SurfaceScopeV1,
    authority,
    digest,
    enum_value,
    nonnegative,
    object_with_keys,
    optional_nonnegative,
    optional_text,
    pair_wire,
    pairs,
    strings,
    text,
    uuid,
)


@dataclass(frozen=True, slots=True)
class SourceSurfaceV1:
    surface_id: str
    oracle_id: str
    source_card_id: str
    source_record_sha256: str
    card_name: str
    face_name: str | None
    layout: str
    type_line: str | None
    keywords: tuple[str, ...] | None
    face_index: int | None
    line_index: int | None
    scope: SurfaceScopeV1
    raw_text: str | None
    face_count: int
    line_count: int
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-source-surface.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "surface_id",
        "oracle_id",
        "source_card_id",
        "source_record_sha256",
        "card_name",
        "face_name",
        "layout",
        "type_line",
        "keywords",
        "face_index",
        "line_index",
        "scope",
        "raw_text",
        "face_count",
        "line_count",
    }

    def __post_init__(self) -> None:
        if SURFACE_ID.fullmatch(self.surface_id) is None:
            raise ValueError("surface_id must have the m6surf_ SHA-256 form")
        uuid("oracle_id", self.oracle_id)
        uuid("source_card_id", self.source_card_id)
        digest("source_record_sha256", self.source_record_sha256)
        text("card_name", self.card_name)
        optional_text("face_name", self.face_name)
        text("layout", self.layout)
        optional_text("type_line", self.type_line)
        object.__setattr__(
            self,
            "keywords",
            strings(
                "keywords",
                list(self.keywords) if self.keywords is not None else None,
            ),
        )
        face_index = optional_nonnegative("face_index", self.face_index)
        line_index = optional_nonnegative("line_index", self.line_index)
        scope = enum_value("scope", self.scope, SurfaceScopeV1)
        if scope is SurfaceScopeV1.CARD_TEXT and (
            face_index is not None or line_index is not None
        ):
            raise ValueError("card text surfaces cannot have indexes")
        if scope is SurfaceScopeV1.FACE_TEXT and (
            face_index is None or line_index is not None
        ):
            raise ValueError("face text surfaces require only a face index")
        if scope is SurfaceScopeV1.ABILITY_LINE and line_index is None:
            raise ValueError("ability-line surfaces require a line index")
        object.__setattr__(self, "face_index", face_index)
        object.__setattr__(self, "line_index", line_index)
        object.__setattr__(self, "scope", scope)
        optional_text("raw_text", self.raw_text)
        face_count = nonnegative("face_count", self.face_count)
        line_count = nonnegative("line_count", self.line_count)
        if self.raw_text is None and line_count != 0:
            raise ValueError("null raw text requires zero line_count")
        if self.raw_text is not None and line_count != self.raw_text.count("\n") + 1:
            raise ValueError("line_count does not match raw_text")
        object.__setattr__(self, "face_count", face_count)
        object.__setattr__(self, "line_count", line_count)
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "surface_id": self.surface_id,
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "source_record_sha256": self.source_record_sha256,
            "card_name": self.card_name,
            "face_name": self.face_name,
            "layout": self.layout,
            "type_line": self.type_line,
            "keywords": list(self.keywords) if self.keywords is not None else None,
            "face_index": self.face_index,
            "line_index": self.line_index,
            "scope": self.scope.value,
            "raw_text": self.raw_text,
            "face_count": self.face_count,
            "line_count": self.line_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> SourceSurfaceV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "source surface")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        return cls(
            surface_id=cast(str, document["surface_id"]),
            oracle_id=cast(str, document["oracle_id"]),
            source_card_id=cast(str, document["source_card_id"]),
            source_record_sha256=cast(str, document["source_record_sha256"]),
            card_name=cast(str, document["card_name"]),
            face_name=cast(str | None, document["face_name"]),
            layout=cast(str, document["layout"]),
            type_line=cast(str | None, document["type_line"]),
            keywords=strings("keywords", document["keywords"]),
            face_index=cast(int | None, document["face_index"]),
            line_index=cast(int | None, document["line_index"]),
            scope=cast(SurfaceScopeV1, document["scope"]),
            raw_text=cast(str | None, document["raw_text"]),
            face_count=cast(int, document["face_count"]),
            line_count=cast(int, document["line_count"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class SurfaceMemberV1:
    surface_id: str
    oracle_id: str
    source_card_id: str
    source_record_sha256: str
    face_index: int | None
    line_index: int | None
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-surface-member.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "surface_id",
        "oracle_id",
        "source_card_id",
        "source_record_sha256",
        "face_index",
        "line_index",
    }

    def __post_init__(self) -> None:
        if SURFACE_ID.fullmatch(self.surface_id) is None:
            raise ValueError("surface_id must have the m6surf_ SHA-256 form")
        uuid("oracle_id", self.oracle_id)
        uuid("source_card_id", self.source_card_id)
        digest("source_record_sha256", self.source_record_sha256)
        object.__setattr__(
            self, "face_index", optional_nonnegative("face_index", self.face_index)
        )
        object.__setattr__(
            self, "line_index", optional_nonnegative("line_index", self.line_index)
        )
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "surface_id": self.surface_id,
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "source_record_sha256": self.source_record_sha256,
            "face_index": self.face_index,
            "line_index": self.line_index,
        }

    @classmethod
    def from_wire(cls, value: object) -> SurfaceMemberV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "surface member")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        return cls(
            surface_id=cast(str, document["surface_id"]),
            oracle_id=cast(str, document["oracle_id"]),
            source_card_id=cast(str, document["source_card_id"]),
            source_record_sha256=cast(str, document["source_record_sha256"]),
            face_index=cast(int | None, document["face_index"]),
            line_index=cast(int | None, document["line_index"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class StructuralSummaryV1:
    layout_counts: tuple[tuple[str, int], ...]
    type_line_counts: tuple[tuple[str, int], ...]
    keyword_counts: tuple[tuple[str, int], ...]
    face_count_counts: tuple[tuple[str, int], ...]
    line_count_counts: tuple[tuple[str, int], ...]
    raw_text_null_count: int
    raw_text_empty_count: int

    SCHEMA: ClassVar[str] = "census.m6-02-structural-summary.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "layout_counts",
        "type_line_counts",
        "keyword_counts",
        "face_count_counts",
        "line_count_counts",
        "raw_text_null_count",
        "raw_text_empty_count",
    }

    def __post_init__(self) -> None:
        for field in (
            "layout_counts",
            "type_line_counts",
            "keyword_counts",
            "face_count_counts",
            "line_count_counts",
        ):
            value = tuple(getattr(self, field))
            if value != tuple(sorted(value)):
                raise ValueError(f"{field} must be sorted")
            if any(
                not isinstance(key, str) or type(count) is not int or count < 0
                for key, count in value
            ):
                raise ValueError(f"{field} contains an invalid pair")
            object.__setattr__(self, field, value)
        nonnegative("raw_text_null_count", self.raw_text_null_count)
        nonnegative("raw_text_empty_count", self.raw_text_empty_count)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "layout_counts": pair_wire(self.layout_counts),
            "type_line_counts": pair_wire(self.type_line_counts),
            "keyword_counts": pair_wire(self.keyword_counts),
            "face_count_counts": pair_wire(self.face_count_counts),
            "line_count_counts": pair_wire(self.line_count_counts),
            "raw_text_null_count": self.raw_text_null_count,
            "raw_text_empty_count": self.raw_text_empty_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralSummaryV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "structural summary")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        return cls(
            layout_counts=pairs("layout_counts", document["layout_counts"]),
            type_line_counts=pairs("type_line_counts", document["type_line_counts"]),
            keyword_counts=pairs("keyword_counts", document["keyword_counts"]),
            face_count_counts=pairs("face_count_counts", document["face_count_counts"]),
            line_count_counts=pairs("line_count_counts", document["line_count_counts"]),
            raw_text_null_count=cast(int, document["raw_text_null_count"]),
            raw_text_empty_count=cast(int, document["raw_text_empty_count"]),
        )
