"""Immutable, producer-local M3 extraction trace events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..semantic.primitives import _require_enum, _require_object
from .patterns import PatternSourceFieldV1

TRACE_SCHEMA = "census.analysis-trace.v1"
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")


class TraceDispositionV1(StrEnum):
    CANDIDATE_EMITTED = "CANDIDATE_EMITTED"
    PRODUCER_NO_MATCH = "PRODUCER_NO_MATCH"
    PRODUCER_UNSUPPORTED_SHAPE = "PRODUCER_UNSUPPORTED_SHAPE"
    CANDIDATE_RETAINED = "CANDIDATE_RETAINED"
    DISPUTED_IDENTITY_OMITTED = "DISPUTED_IDENTITY_OMITTED"


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_source_key(value: object) -> tuple[str, str, str, str]:
    if not isinstance(value, tuple | list) or len(value) != 4:
        raise ValueError("card_source_key must have four fields")
    record_schema, oracle_id, source_card_id, record_sha256 = value
    if record_schema != "census.structural-card.v1":
        raise ValueError("card_source_key record_schema is invalid")
    if not isinstance(oracle_id, str) or _UUID_PATTERN.fullmatch(oracle_id) is None:
        raise ValueError("card_source_key oracle_id is invalid")
    if (
        not isinstance(source_card_id, str)
        or _UUID_PATTERN.fullmatch(source_card_id) is None
    ):
        raise ValueError("card_source_key source_card_id is invalid")
    return (
        record_schema,
        oracle_id,
        source_card_id,
        _require_digest("source_record_sha256", record_sha256),
    )


@dataclass(frozen=True, slots=True)
class RequirementTraceEventV1:
    card_source_key: tuple[str, str, str, str]
    producer_id: str
    producer_version: str
    pattern_id: str | None
    pattern_version: str | None
    pattern_digest: str | None
    source_field: PatternSourceFieldV1 | None
    face_index: int | None
    exact_fragment: str | None
    clause_ordinal: int | None
    parser_span: tuple[int, int] | None
    candidate_requirement_id: str | None
    local_candidate_key: str | None
    disposition: TraceDispositionV1

    SCHEMA: ClassVar[str] = TRACE_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "card_source_key",
        "producer_id",
        "producer_version",
        "pattern_id",
        "pattern_version",
        "pattern_digest",
        "source_field",
        "face_index",
        "exact_fragment",
        "clause_ordinal",
        "parser_span",
        "candidate_requirement_id",
        "local_candidate_key",
        "disposition",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "card_source_key", _require_source_key(self.card_source_key)
        )
        for field in ("producer_id", "producer_version"):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        pattern_fields = (self.pattern_id, self.pattern_version, self.pattern_digest)
        if any(item is not None for item in pattern_fields) and not all(
            item is not None for item in pattern_fields
        ):
            raise ValueError("pattern identity fields must be all present or null")
        if self.pattern_id is not None:
            object.__setattr__(
                self, "pattern_id", _require_text("pattern_id", self.pattern_id)
            )
            object.__setattr__(
                self,
                "pattern_version",
                _require_text("pattern_version", self.pattern_version),
            )
            object.__setattr__(
                self,
                "pattern_digest",
                _require_digest("pattern_digest", self.pattern_digest),
            )
        if self.source_field is not None:
            object.__setattr__(
                self,
                "source_field",
                _require_enum("source_field", self.source_field, PatternSourceFieldV1),
            )
        if self.face_index is not None:
            if type(self.face_index) is not int or self.face_index < 0:
                raise ValueError("face_index must be a non-negative integer")
            if self.source_field is not PatternSourceFieldV1.ORACLE_TEXT:
                raise ValueError("face_index requires oracle_text source_field")
        if self.exact_fragment is not None:
            object.__setattr__(
                self,
                "exact_fragment",
                _require_text("exact_fragment", self.exact_fragment),
            )
            if self.source_field is not PatternSourceFieldV1.ORACLE_TEXT:
                raise ValueError("exact_fragment requires oracle_text source_field")
        if self.clause_ordinal is not None and (
            type(self.clause_ordinal) is not int or self.clause_ordinal < 0
        ):
            raise ValueError("clause_ordinal must be a non-negative integer")
        if self.parser_span is not None:
            if (
                not isinstance(self.parser_span, tuple | list)
                or len(self.parser_span) != 2
            ):
                raise ValueError("parser_span must contain two offsets")
            start, end = self.parser_span
            if (
                type(start) is not int
                or type(end) is not int
                or start < 0
                or end < start
            ):
                raise ValueError("parser_span offsets are invalid")
            object.__setattr__(self, "parser_span", (start, end))
        if self.candidate_requirement_id is not None and (
            not isinstance(self.candidate_requirement_id, str)
            or _REQUIREMENT_ID_PATTERN.fullmatch(self.candidate_requirement_id) is None
        ):
            raise ValueError("candidate_requirement_id is invalid")
        if self.local_candidate_key is not None:
            object.__setattr__(
                self,
                "local_candidate_key",
                _require_text("local_candidate_key", self.local_candidate_key),
            )
        object.__setattr__(
            self,
            "disposition",
            _require_enum("disposition", self.disposition, TraceDispositionV1),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "card_source_key": list(self.card_source_key),
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
            "pattern_id": self.pattern_id,
            "pattern_version": self.pattern_version,
            "pattern_digest": self.pattern_digest,
            "source_field": (
                None if self.source_field is None else self.source_field.value
            ),
            "face_index": self.face_index,
            "exact_fragment": self.exact_fragment,
            "clause_ordinal": self.clause_ordinal,
            "parser_span": (
                None if self.parser_span is None else list(self.parser_span)
            ),
            "candidate_requirement_id": self.candidate_requirement_id,
            "local_candidate_key": self.local_candidate_key,
            "disposition": self.disposition.value,
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementTraceEventV1:
        document = _require_object(value, cls._WIRE_KEYS, "RequirementTraceEventV1")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_span = document["parser_span"]
        parser_span: tuple[int, int] | None
        if raw_span is None:
            parser_span = None
        else:
            span = _require_span(raw_span)
            parser_span = (cast(int, span[0]), cast(int, span[1]))
        return cls(
            card_source_key=_require_source_key(document["card_source_key"]),
            producer_id=cast(str, document["producer_id"]),
            producer_version=cast(str, document["producer_version"]),
            pattern_id=(
                None
                if document["pattern_id"] is None
                else cast(str, document["pattern_id"])
            ),
            pattern_version=(
                None
                if document["pattern_version"] is None
                else cast(str, document["pattern_version"])
            ),
            pattern_digest=(
                None
                if document["pattern_digest"] is None
                else cast(str, document["pattern_digest"])
            ),
            source_field=(
                None
                if document["source_field"] is None
                else _require_enum(
                    "source_field",
                    document["source_field"],
                    PatternSourceFieldV1,
                )
            ),
            face_index=(
                None
                if document["face_index"] is None
                else cast(int, document["face_index"])
            ),
            exact_fragment=(
                None
                if document["exact_fragment"] is None
                else cast(str, document["exact_fragment"])
            ),
            clause_ordinal=(
                None
                if document["clause_ordinal"] is None
                else cast(int, document["clause_ordinal"])
            ),
            parser_span=parser_span,
            candidate_requirement_id=(
                None
                if document["candidate_requirement_id"] is None
                else cast(str, document["candidate_requirement_id"])
            ),
            local_candidate_key=(
                None
                if document["local_candidate_key"] is None
                else cast(str, document["local_candidate_key"])
            ),
            disposition=_require_enum(
                "disposition",
                document["disposition"],
                TraceDispositionV1,
            ),
        )


def _require_span(value: object) -> list[object]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("parser_span must contain two offsets")
    return value


def trace_sort_key(
    event: RequirementTraceEventV1,
) -> tuple[str, ...]:
    if not isinstance(event, RequirementTraceEventV1):
        raise TypeError("event must be RequirementTraceEventV1")
    return (
        *event.card_source_key,
        event.producer_id,
        event.producer_version,
        event.pattern_id or "",
        event.pattern_version or "",
        event.pattern_digest or "",
        "" if event.source_field is None else event.source_field.value,
        "" if event.face_index is None else str(event.face_index),
        event.exact_fragment or "",
        "" if event.clause_ordinal is None else str(event.clause_ordinal),
        event.candidate_requirement_id or "",
        event.local_candidate_key or "",
        event.disposition.value,
        "" if event.parser_span is None else str(event.parser_span[0]),
        "" if event.parser_span is None else str(event.parser_span[1]),
        canonical_json_bytes(event.to_wire()).decode("utf-8"),
    )


__all__ = [
    "RequirementTraceEventV1",
    "TRACE_SCHEMA",
    "TraceDispositionV1",
    "trace_sort_key",
]
