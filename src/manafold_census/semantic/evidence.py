"""Immutable M1 source references and the closed M2 evidence union."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast
from uuid import UUID

from ..canonical import JSONValue
from ..digest import domain_digest
from .primitives import (
    _require_int,
    _require_object,
    _require_text,
)

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SCHEMA = "census.structural-card.v1"
EVIDENCE_DIGEST_DOMAIN = "census.semantic-evidence.v1"


def _source_fields(value: str) -> frozenset[str]:
    return frozenset(value.split())


M1_FACE_FIELDS = _source_fields(
    "name mana_cost type_line oracle_text colors color_indicator "
    "power toughness loyalty defense"
)
M1_TOP_LEVEL_FIELDS = M1_FACE_FIELDS | _source_fields(
    "layout color_identity keywords produced_mana hand_modifier life_modifier "
    "attraction_lights faces all_parts"
)
M1_TEXT_FACE_FIELDS = M1_FACE_FIELDS - {"colors", "color_indicator"}
M1_TEXT_PARENT_FIELDS = M1_TEXT_FACE_FIELDS | {
    "layout",
    "hand_modifier",
    "life_modifier",
}


class EvidenceKindV1(StrEnum):
    STRUCTURAL_RECORD = "STRUCTURAL_RECORD"
    STRUCTURAL_FACE = "STRUCTURAL_FACE"
    STRUCTURAL_FIELD = "STRUCTURAL_FIELD"
    STRUCTURAL_KEYWORD = "STRUCTURAL_KEYWORD"
    RULES_CITATION = "RULES_CITATION"
    EXTERNAL_REVIEW = "EXTERNAL_REVIEW"


def _require_uuid(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _UUID_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase canonical UUID")
    try:
        if str(UUID(text)) != text:
            raise ValueError(f"{field} must be a lowercase canonical UUID")
    except ValueError as error:
        raise ValueError(f"{field} must be a lowercase canonical UUID") from error
    return text


def _require_digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _require_identifier_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_source_string(field: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    value.encode("utf-8")
    return value


def _optional_digest(field: str, value: object) -> str | None:
    return None if value is None else _require_digest(field, value)


@dataclass(frozen=True, slots=True)
class SourceRecordRefV1:
    record_schema: str
    source_lock_digest: str
    oracle_id: str
    source_card_id: str
    source_record_sha256: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "record_schema",
        "source_lock_digest",
        "oracle_id",
        "source_card_id",
        "source_record_sha256",
    }

    def __post_init__(self) -> None:
        if self.record_schema != _SOURCE_SCHEMA:
            raise ValueError(f"record_schema must be {_SOURCE_SCHEMA}")
        object.__setattr__(
            self,
            "source_lock_digest",
            _require_digest("source_lock_digest", self.source_lock_digest),
        )
        object.__setattr__(
            self, "oracle_id", _require_uuid("oracle_id", self.oracle_id)
        )
        object.__setattr__(
            self, "source_card_id", _require_uuid("source_card_id", self.source_card_id)
        )
        object.__setattr__(
            self,
            "source_record_sha256",
            _require_digest("source_record_sha256", self.source_record_sha256),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "record_schema": self.record_schema,
            "source_lock_digest": self.source_lock_digest,
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "source_record_sha256": self.source_record_sha256,
        }

    @classmethod
    def from_wire(cls, value: object) -> SourceRecordRefV1:
        document = _require_object(value, cls._WIRE_KEYS, "source record reference")
        return cls(
            record_schema=cast(str, document["record_schema"]),
            source_lock_digest=cast(str, document["source_lock_digest"]),
            oracle_id=cast(str, document["oracle_id"]),
            source_card_id=cast(str, document["source_card_id"]),
            source_record_sha256=cast(str, document["source_record_sha256"]),
        )


class _Evidence:
    KIND: ClassVar[EvidenceKindV1]

    @property
    def kind(self) -> EvidenceKindV1:
        return self.KIND

    @classmethod
    def from_wire(cls, value: object) -> _Evidence:
        raise NotImplementedError

    def to_wire(self) -> dict[str, JSONValue]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StructuralRecordEvidenceV1(_Evidence):
    source: SourceRecordRefV1
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.STRUCTURAL_RECORD
    _WIRE_KEYS: ClassVar[set[str]] = {"kind", "source"}

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")

    def to_wire(self) -> dict[str, JSONValue]:
        return {"kind": self.KIND.value, "source": self.source.to_wire()}

    @classmethod
    def from_wire(cls, value: object) -> StructuralRecordEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "structural record evidence")
        _require_kind(document, cls.KIND)
        return cls(SourceRecordRefV1.from_wire(document["source"]))


@dataclass(frozen=True, slots=True)
class StructuralFaceEvidenceV1(_Evidence):
    source: SourceRecordRefV1
    face_index: int
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.STRUCTURAL_FACE
    _WIRE_KEYS: ClassVar[set[str]] = {"kind", "source", "face_index"}

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        object.__setattr__(
            self,
            "face_index",
            _require_int("face_index", self.face_index, nonnegative=True),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "kind": self.KIND.value,
            "source": self.source.to_wire(),
            "face_index": self.face_index,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralFaceEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "structural face evidence")
        _require_kind(document, cls.KIND)
        return cls(
            SourceRecordRefV1.from_wire(document["source"]),
            _require_int("face_index", document["face_index"], nonnegative=True),
        )


@dataclass(frozen=True, slots=True)
class StructuralFieldEvidenceV1(_Evidence):
    source: SourceRecordRefV1
    field: str
    face_index: int | None
    fragment: str | None
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.STRUCTURAL_FIELD
    _WIRE_KEYS: ClassVar[set[str]] = {
        "kind",
        "source",
        "field",
        "face_index",
        "fragment",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        field = _require_text("field", self.field)
        if field not in M1_TOP_LEVEL_FIELDS:
            raise ValueError("field is not a controlled M1 field")
        if self.face_index is not None:
            object.__setattr__(
                self,
                "face_index",
                _require_int("face_index", self.face_index, nonnegative=True),
            )
            if field not in M1_FACE_FIELDS:
                raise ValueError("face_index is not allowed for this field")
        object.__setattr__(self, "field", field)
        if self.fragment is not None:
            text_fields = (
                M1_TEXT_FACE_FIELDS
                if self.face_index is not None
                else M1_TEXT_PARENT_FIELDS
            )
            if field not in text_fields:
                raise ValueError("fragment is allowed only for textual fields")
            object.__setattr__(
                self, "fragment", _require_text("fragment", self.fragment)
            )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "kind": self.KIND.value,
            "source": self.source.to_wire(),
            "field": self.field,
            "face_index": self.face_index,
            "fragment": self.fragment,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralFieldEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "structural field evidence")
        _require_kind(document, cls.KIND)
        return cls(
            SourceRecordRefV1.from_wire(document["source"]),
            cast(str, document["field"]),
            None
            if document["face_index"] is None
            else _require_int("face_index", document["face_index"], nonnegative=True),
            None if document["fragment"] is None else cast(str, document["fragment"]),
        )


@dataclass(frozen=True, slots=True)
class StructuralKeywordEvidenceV1(_Evidence):
    source: SourceRecordRefV1
    keyword_index: int
    keyword_value: str
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.STRUCTURAL_KEYWORD
    _WIRE_KEYS: ClassVar[set[str]] = {
        "kind",
        "source",
        "keyword_index",
        "keyword_value",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        object.__setattr__(
            self,
            "keyword_index",
            _require_int("keyword_index", self.keyword_index, nonnegative=True),
        )
        object.__setattr__(
            self,
            "keyword_value",
            _require_source_string("keyword_value", self.keyword_value),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "kind": self.KIND.value,
            "source": self.source.to_wire(),
            "keyword_index": self.keyword_index,
            "keyword_value": self.keyword_value,
        }

    @classmethod
    def from_wire(cls, value: object) -> StructuralKeywordEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "structural keyword evidence")
        _require_kind(document, cls.KIND)
        return cls(
            SourceRecordRefV1.from_wire(document["source"]),
            _require_int("keyword_index", document["keyword_index"], nonnegative=True),
            cast(str, document["keyword_value"]),
        )


@dataclass(frozen=True, slots=True)
class RulesCitationEvidenceV1(_Evidence):
    ruleset_id: str
    ruleset_version: str
    rule_id: str
    rules_artifact_sha256: str | None
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.RULES_CITATION
    _WIRE_KEYS: ClassVar[set[str]] = {
        "kind",
        "ruleset_id",
        "ruleset_version",
        "rule_id",
        "rules_artifact_sha256",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ruleset_id",
            _require_identifier_text("ruleset_id", self.ruleset_id),
        )
        object.__setattr__(
            self,
            "ruleset_version",
            _require_identifier_text("ruleset_version", self.ruleset_version),
        )
        object.__setattr__(
            self, "rule_id", _require_identifier_text("rule_id", self.rule_id)
        )
        object.__setattr__(
            self,
            "rules_artifact_sha256",
            _optional_digest("rules_artifact_sha256", self.rules_artifact_sha256),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "kind": self.KIND.value,
            "ruleset_id": self.ruleset_id,
            "ruleset_version": self.ruleset_version,
            "rule_id": self.rule_id,
            "rules_artifact_sha256": self.rules_artifact_sha256,
        }

    @classmethod
    def from_wire(cls, value: object) -> RulesCitationEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "rules citation evidence")
        _require_kind(document, cls.KIND)
        return cls(
            cast(str, document["ruleset_id"]),
            cast(str, document["ruleset_version"]),
            cast(str, document["rule_id"]),
            None
            if document["rules_artifact_sha256"] is None
            else cast(str, document["rules_artifact_sha256"]),
        )


@dataclass(frozen=True, slots=True)
class ExternalReviewEvidenceV1(_Evidence):
    authority_id: str
    authority_version: str
    record_id: str
    record_sha256: str
    KIND: ClassVar[EvidenceKindV1] = EvidenceKindV1.EXTERNAL_REVIEW
    _WIRE_KEYS: ClassVar[set[str]] = {
        "kind",
        "authority_id",
        "authority_version",
        "record_id",
        "record_sha256",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authority_id",
            _require_identifier_text("authority_id", self.authority_id),
        )
        object.__setattr__(
            self,
            "authority_version",
            _require_identifier_text("authority_version", self.authority_version),
        )
        object.__setattr__(
            self, "record_id", _require_identifier_text("record_id", self.record_id)
        )
        object.__setattr__(
            self, "record_sha256", _require_digest("record_sha256", self.record_sha256)
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "kind": self.KIND.value,
            "authority_id": self.authority_id,
            "authority_version": self.authority_version,
            "record_id": self.record_id,
            "record_sha256": self.record_sha256,
        }

    @classmethod
    def from_wire(cls, value: object) -> ExternalReviewEvidenceV1:
        document = _require_object(value, cls._WIRE_KEYS, "external review evidence")
        _require_kind(document, cls.KIND)
        return cls(
            cast(str, document["authority_id"]),
            cast(str, document["authority_version"]),
            cast(str, document["record_id"]),
            cast(str, document["record_sha256"]),
        )


type EvidenceV1 = (
    StructuralRecordEvidenceV1
    | StructuralFaceEvidenceV1
    | StructuralFieldEvidenceV1
    | StructuralKeywordEvidenceV1
    | RulesCitationEvidenceV1
    | ExternalReviewEvidenceV1
)


def _require_kind(document: dict[str, object], expected: EvidenceKindV1) -> None:
    if document["kind"] != expected.value:
        raise ValueError(f"kind must be {expected.value}")


_EVIDENCE_TYPES: dict[str, type[_Evidence]] = {
    EvidenceKindV1.STRUCTURAL_RECORD.value: StructuralRecordEvidenceV1,
    EvidenceKindV1.STRUCTURAL_FACE.value: StructuralFaceEvidenceV1,
    EvidenceKindV1.STRUCTURAL_FIELD.value: StructuralFieldEvidenceV1,
    EvidenceKindV1.STRUCTURAL_KEYWORD.value: StructuralKeywordEvidenceV1,
    EvidenceKindV1.RULES_CITATION.value: RulesCitationEvidenceV1,
    EvidenceKindV1.EXTERNAL_REVIEW.value: ExternalReviewEvidenceV1,
}


def evidence_to_wire(value: EvidenceV1) -> dict[str, JSONValue]:
    if not isinstance(value, _Evidence):
        raise TypeError("value must be an EvidenceV1")
    return value.to_wire()


def evidence_from_wire(value: object) -> EvidenceV1:
    if not isinstance(value, dict):
        raise TypeError("evidence must be an object")
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in _EVIDENCE_TYPES:
        raise ValueError("kind is not a supported evidence kind")
    evidence_type = _EVIDENCE_TYPES[kind]
    return cast(EvidenceV1, evidence_type.from_wire(value))


def evidence_sort_key(value: EvidenceV1) -> str:
    return domain_digest(EVIDENCE_DIGEST_DOMAIN, evidence_to_wire(value))
