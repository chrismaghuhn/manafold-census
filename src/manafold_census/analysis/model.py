"""Immutable M3 card-analysis records and their extraction outcomes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..semantic.bundle import RequirementBundleV1
from ..semantic.evidence import SourceRecordRefV1
from ..semantic.primitives import _require_enum, _require_object

CARD_ANALYSIS_SCHEMA = "census.card-analysis.v1"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_RECORD_ID_PATTERN = re.compile(r"^nra_[0-9a-f]{64}$")


class AnalysisOutcomeV1(StrEnum):
    REQUIREMENTS_PRODUCED = "REQUIREMENTS_PRODUCED"
    NO_REQUIREMENTS_APPLICABLE = "NO_REQUIREMENTS_APPLICABLE"
    UNRESOLVED_ANALYSIS = "UNRESOLVED_ANALYSIS"


def _require_identifier_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class NegativeReviewAuthorityRefV1:
    """A digest-bound reference to one explicit negative authority record."""

    authority_id: str
    authority_version: str
    record_id: str
    record_sha256: str
    scope_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "authority_id",
        "authority_version",
        "record_id",
        "record_sha256",
        "scope_digest",
    }

    def __post_init__(self) -> None:
        for field in ("authority_id", "authority_version", "record_id"):
            object.__setattr__(
                self,
                field,
                _require_identifier_text(field, getattr(self, field)),
            )
        if _AUTHORITY_RECORD_ID_PATTERN.fullmatch(self.record_id) is None:
            raise ValueError("record_id must use the nra_ SHA-256 form")
        for field in ("record_sha256", "scope_digest"):
            object.__setattr__(
                self,
                field,
                _require_digest(field, getattr(self, field)),
            )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "authority_id": self.authority_id,
            "authority_version": self.authority_version,
            "record_id": self.record_id,
            "record_sha256": self.record_sha256,
            "scope_digest": self.scope_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> NegativeReviewAuthorityRefV1:
        document = _require_object(
            value,
            cls._WIRE_KEYS,
            "negative review authority reference",
        )
        return cls(
            authority_id=cast(str, document["authority_id"]),
            authority_version=cast(str, document["authority_version"]),
            record_id=cast(str, document["record_id"]),
            record_sha256=cast(str, document["record_sha256"]),
            scope_digest=cast(str, document["scope_digest"]),
        )


def card_source_key(
    source: SourceRecordRefV1,
) -> tuple[str, str, str, str]:
    """Return the M1 identity tuple used for M3 closure."""

    if not isinstance(source, SourceRecordRefV1):
        raise TypeError("source must be SourceRecordRefV1")
    return (
        source.record_schema,
        source.oracle_id,
        source.source_card_id,
        source.source_record_sha256,
    )


@dataclass(frozen=True, slots=True)
class CardAnalysisRecordV1:
    """One explicit M3 outcome for one exact M1 source identity."""

    source: SourceRecordRefV1
    outcome: AnalysisOutcomeV1
    bundle: RequirementBundleV1 | None
    no_requirements_basis: NegativeReviewAuthorityRefV1 | None

    SCHEMA: ClassVar[str] = CARD_ANALYSIS_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "source",
        "outcome",
        "bundle",
        "no_requirements_basis",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        outcome = _require_enum("outcome", self.outcome, AnalysisOutcomeV1)
        object.__setattr__(self, "outcome", outcome)

        if self.bundle is not None:
            if not isinstance(self.bundle, RequirementBundleV1):
                raise TypeError("bundle must be RequirementBundleV1 or None")
            if self.bundle.source != self.source:
                raise ValueError("bundle source does not match card source")

        if self.no_requirements_basis is not None and not isinstance(
            self.no_requirements_basis,
            NegativeReviewAuthorityRefV1,
        ):
            raise TypeError(
                "no_requirements_basis must be NegativeReviewAuthorityRefV1 or None"
            )

        if outcome is AnalysisOutcomeV1.REQUIREMENTS_PRODUCED:
            if self.bundle is None:
                raise ValueError("REQUIREMENTS_PRODUCED requires a non-null bundle")
            if self.no_requirements_basis is not None:
                raise ValueError(
                    "REQUIREMENTS_PRODUCED cannot contain negative authority"
                )
        elif outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE:
            if self.bundle is not None:
                raise ValueError("NO_REQUIREMENTS_APPLICABLE requires a null bundle")
            if self.no_requirements_basis is None:
                raise ValueError(
                    "NO_REQUIREMENTS_APPLICABLE requires negative authority"
                )
        elif self.no_requirements_basis is not None:
            raise ValueError("UNRESOLVED_ANALYSIS cannot contain negative authority")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "source": self.source.to_wire(),
            "outcome": self.outcome.value,
            "bundle": None if self.bundle is None else self.bundle.to_wire(),
            "no_requirements_basis": (
                None
                if self.no_requirements_basis is None
                else self.no_requirements_basis.to_wire()
            ),
        }

    @classmethod
    def from_wire(cls, value: object) -> CardAnalysisRecordV1:
        document = _require_object(value, cls._WIRE_KEYS, "CardAnalysisRecordV1")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        source = SourceRecordRefV1.from_wire(document["source"])
        raw_bundle = document["bundle"]
        bundle = (
            None if raw_bundle is None else RequirementBundleV1.from_wire(raw_bundle)
        )
        raw_basis = document["no_requirements_basis"]
        basis = (
            None
            if raw_basis is None
            else NegativeReviewAuthorityRefV1.from_wire(raw_basis)
        )
        return cls(
            source=source,
            outcome=_require_enum("outcome", document["outcome"], AnalysisOutcomeV1),
            bundle=bundle,
            no_requirements_basis=basis,
        )


__all__ = [
    "AnalysisOutcomeV1",
    "CARD_ANALYSIS_SCHEMA",
    "CardAnalysisRecordV1",
    "NegativeReviewAuthorityRefV1",
    "card_source_key",
]
