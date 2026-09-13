"""Digest-bound negative Requirement authority records for M3 closure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, sha256_bytes
from ..semantic.evidence import SourceRecordRefV1
from ..semantic.primitives import _require_enum, _require_object

AUTHORITY_SCHEMA = "census.negative-requirement-authority.v1"
SCOPE_SCHEMA = "census.m3-negative-authority-scope.v1"
SCOPE_ID = "census.m3-semantic-requirement-applicability"
SCOPE_VERSION = "v1"
SCOPE_DIGEST_DOMAIN = "census.m3-negative-authority-scope.v1"
RECORD_ID_DOMAIN = "census.m3-negative-authority-record-id.v1"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RECORD_ID_PATTERN = re.compile(r"^nra_[0-9a-f]{64}$")
_ALLOWED_SOURCE_FIELDS = frozenset({"face.oracle_text", "keywords", "oracle_text"})


class NegativeAuthorityDecisionV1(StrEnum):
    NO_REQUIREMENTS_APPLICABLE = "NO_REQUIREMENTS_APPLICABLE"


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class NegativeAuthorityScopeV1:
    """Closed semantic applicability scope for one negative decision."""

    source_fields: tuple[str, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {
        "scope_schema",
        "scope_id",
        "scope_version",
        "analysis_schema",
        "m2_requirement_schema",
        "m2_bundle_schema",
        "source_fields",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source_fields, tuple | list):
            raise TypeError("source_fields must be a tuple or list")
        fields = tuple(self.source_fields)
        if not fields:
            raise ValueError("source_fields must be non-empty")
        if any(
            not isinstance(field, str) or field not in _ALLOWED_SOURCE_FIELDS
            for field in fields
        ):
            raise ValueError("source_fields contains an unsupported field")
        if fields != tuple(sorted(set(fields))):
            raise ValueError("source_fields must be sorted and unique")
        object.__setattr__(self, "source_fields", fields)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "scope_schema": SCOPE_SCHEMA,
            "scope_id": SCOPE_ID,
            "scope_version": SCOPE_VERSION,
            "analysis_schema": "census.card-analysis.v1",
            "m2_requirement_schema": "census.semantic-requirement.v1",
            "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
            "source_fields": list(self.source_fields),
        }

    @classmethod
    def from_wire(cls, value: object) -> NegativeAuthorityScopeV1:
        document = _require_object(value, cls._WIRE_KEYS, "negative authority scope")
        expected = {
            "scope_schema": SCOPE_SCHEMA,
            "scope_id": SCOPE_ID,
            "scope_version": SCOPE_VERSION,
            "analysis_schema": "census.card-analysis.v1",
            "m2_requirement_schema": "census.semantic-requirement.v1",
            "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
        }
        for field, expected_value in expected.items():
            if document[field] != expected_value:
                raise ValueError(f"{field} does not match the frozen scope")
        raw_fields = document["source_fields"]
        if not isinstance(raw_fields, list):
            raise TypeError("source_fields must be a JSON array")
        return cls(tuple(cast(str, field) for field in raw_fields))


def negative_authority_scope_digest(scope: NegativeAuthorityScopeV1) -> str:
    if not isinstance(scope, NegativeAuthorityScopeV1):
        raise TypeError("scope must be NegativeAuthorityScopeV1")
    return domain_digest(SCOPE_DIGEST_DOMAIN, scope.to_wire())


@dataclass(frozen=True, slots=True)
class NegativeRequirementAuthorityRecordV1:
    """One explicit, source-bound negative semantic applicability decision."""

    authority_id: str
    authority_version: str
    record_id: str
    source: SourceRecordRefV1
    scope: NegativeAuthorityScopeV1
    decision: NegativeAuthorityDecisionV1
    record_sha256: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_id",
        "authority_version",
        "record_id",
        "source",
        "scope",
        "decision",
        "record_sha256",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authority_id",
            _require_text("authority_id", self.authority_id),
        )
        object.__setattr__(
            self,
            "authority_version",
            _require_text("authority_version", self.authority_version),
        )
        object.__setattr__(
            self,
            "record_id",
            _require_text("record_id", self.record_id),
        )
        if _RECORD_ID_PATTERN.fullmatch(self.record_id) is None:
            raise ValueError("record_id must use the nra_ SHA-256 form")
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        if not isinstance(self.scope, NegativeAuthorityScopeV1):
            raise TypeError("scope must be NegativeAuthorityScopeV1")
        decision = _require_enum(
            "decision",
            self.decision,
            NegativeAuthorityDecisionV1,
        )
        object.__setattr__(self, "decision", decision)
        object.__setattr__(
            self,
            "record_sha256",
            _require_digest("record_sha256", self.record_sha256),
        )
        if self.record_id != self.record_id_for_parts(
            self.authority_id,
            self.authority_version,
            self.source,
            self.scope,
            decision,
        ):
            raise ValueError("record_id does not match the authority payload")
        if self.record_sha256 != negative_authority_record_sha256(self):
            raise ValueError("record_sha256 does not match the authority record")

    @classmethod
    def _identity_payload(
        cls,
        authority_id: str,
        authority_version: str,
        source: SourceRecordRefV1,
        scope: NegativeAuthorityScopeV1,
        decision: NegativeAuthorityDecisionV1,
    ) -> dict[str, JSONValue]:
        return {
            "schema": AUTHORITY_SCHEMA,
            "authority_id": authority_id,
            "authority_version": authority_version,
            "source": source.to_wire(),
            "scope": scope.to_wire(),
            "decision": decision.value,
        }

    @classmethod
    def record_id_for_parts(
        cls,
        authority_id: str,
        authority_version: str,
        source: SourceRecordRefV1,
        scope: NegativeAuthorityScopeV1,
        decision: NegativeAuthorityDecisionV1,
    ) -> str:
        return "nra_" + domain_digest(
            RECORD_ID_DOMAIN,
            cls._identity_payload(
                authority_id,
                authority_version,
                source,
                scope,
                decision,
            ),
        )

    @classmethod
    def create(
        cls,
        *,
        authority_id: str,
        authority_version: str,
        source: SourceRecordRefV1,
        scope: NegativeAuthorityScopeV1,
    ) -> NegativeRequirementAuthorityRecordV1:
        decision = NegativeAuthorityDecisionV1.NO_REQUIREMENTS_APPLICABLE
        record_id = cls.record_id_for_parts(
            authority_id,
            authority_version,
            source,
            scope,
            decision,
        )
        payload = cls._identity_payload(
            authority_id,
            authority_version,
            source,
            scope,
            decision,
        )
        record_sha256 = sha256_bytes(
            canonical_json_bytes({**payload, "record_id": record_id})
        )
        return cls(
            authority_id=authority_id,
            authority_version=authority_version,
            record_id=record_id,
            source=source,
            scope=scope,
            decision=decision,
            record_sha256=record_sha256,
        )

    @property
    def scope_digest(self) -> str:
        return negative_authority_scope_digest(self.scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": AUTHORITY_SCHEMA,
            "authority_id": self.authority_id,
            "authority_version": self.authority_version,
            "record_id": self.record_id,
            "source": self.source.to_wire(),
            "scope": self.scope.to_wire(),
            "decision": self.decision.value,
            "record_sha256": self.record_sha256,
        }

    @classmethod
    def from_wire(
        cls,
        value: object,
    ) -> NegativeRequirementAuthorityRecordV1:
        document = _require_object(
            value,
            cls._WIRE_KEYS,
            "NegativeRequirementAuthorityRecordV1",
        )
        if document["schema"] != AUTHORITY_SCHEMA:
            raise ValueError(f"schema must be {AUTHORITY_SCHEMA}")
        return cls(
            authority_id=cast(str, document["authority_id"]),
            authority_version=cast(str, document["authority_version"]),
            record_id=cast(str, document["record_id"]),
            source=SourceRecordRefV1.from_wire(document["source"]),
            scope=NegativeAuthorityScopeV1.from_wire(document["scope"]),
            decision=_require_enum(
                "decision",
                document["decision"],
                NegativeAuthorityDecisionV1,
            ),
            record_sha256=cast(str, document["record_sha256"]),
        )


def negative_authority_record_sha256(
    record: NegativeRequirementAuthorityRecordV1,
) -> str:
    if not isinstance(record, NegativeRequirementAuthorityRecordV1):
        raise TypeError("record must be NegativeRequirementAuthorityRecordV1")
    payload = record._identity_payload(
        record.authority_id,
        record.authority_version,
        record.source,
        record.scope,
        record.decision,
    )
    return sha256_bytes(
        canonical_json_bytes({**payload, "record_id": record.record_id})
    )


def validate_negative_requirement_authority(
    record: NegativeRequirementAuthorityRecordV1,
    expected_source: SourceRecordRefV1,
) -> None:
    if not isinstance(record, NegativeRequirementAuthorityRecordV1):
        raise TypeError("record must be NegativeRequirementAuthorityRecordV1")
    if not isinstance(expected_source, SourceRecordRefV1):
        raise TypeError("expected_source must be SourceRecordRefV1")
    if record.source != expected_source:
        raise ValueError("negative authority source does not match card source")
    if record.decision is not NegativeAuthorityDecisionV1.NO_REQUIREMENTS_APPLICABLE:
        raise ValueError("negative authority decision is unsupported")


def load_negative_requirement_authority(
    path: str | Path,
    expected_source: SourceRecordRefV1,
) -> NegativeRequirementAuthorityRecordV1:
    try:
        document = json.loads(Path(path).read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("negative authority artifact is not valid JSON") from error
    from ..validation import validate_document

    validate_document(document, "negative-requirement-authority.v1.schema.json")
    record = NegativeRequirementAuthorityRecordV1.from_wire(document)
    validate_negative_requirement_authority(record, expected_source)
    return record


__all__ = [
    "AUTHORITY_SCHEMA",
    "NegativeAuthorityDecisionV1",
    "NegativeAuthorityScopeV1",
    "NegativeRequirementAuthorityRecordV1",
    "SCOPE_SCHEMA",
    "load_negative_requirement_authority",
    "negative_authority_record_sha256",
    "negative_authority_scope_digest",
    "validate_negative_requirement_authority",
]
