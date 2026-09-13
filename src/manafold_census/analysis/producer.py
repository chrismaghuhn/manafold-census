"""Algorithm-independent M3 producer contracts and proposal validation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Protocol, cast

from ..canonical import JSONValue
from ..semantic.bundle import RequirementRelationshipV1
from ..semantic.model import (
    DerivationMethodV1,
    RequirementV1,
    ReviewStatusV1,
)
from ..semantic.primitives import _require_enum, _require_object
from ..semantic.validate import validate_requirement_against_structural_record
from ..structural.model import StructuralCardRecordV1

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProducerContractError(ValueError):
    """Raised when a producer emits a value outside the M3 contract."""


class ProducerExecutionError(RuntimeError):
    """Raised when a producer execution fails rather than finding no match."""


class ProducerResultStatusV1(StrEnum):
    EMITTED = "EMITTED"
    NO_MATCH = "NO_MATCH"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"


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
class ProducerDescriptorV1:
    producer_id: str
    producer_version: str
    derivation_method: DerivationMethodV1
    input_schema: str
    input_fields: tuple[str, ...]
    pattern_registry_digest: str | None
    deterministic: bool
    supports_relationships: bool

    _WIRE_KEYS: ClassVar[set[str]] = {
        "producer_id",
        "producer_version",
        "derivation_method",
        "input_schema",
        "input_fields",
        "pattern_registry_digest",
        "deterministic",
        "supports_relationships",
    }

    def __post_init__(self) -> None:
        for field in (
            "producer_id",
            "producer_version",
            "input_schema",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        object.__setattr__(
            self,
            "derivation_method",
            _require_enum(
                "derivation_method",
                self.derivation_method,
                DerivationMethodV1,
            ),
        )
        if not isinstance(self.input_fields, tuple | list):
            raise TypeError("input_fields must be a tuple or list")
        fields = tuple(_require_text("input_field", item) for item in self.input_fields)
        if fields != tuple(sorted(set(fields))):
            raise ValueError("input_fields must be sorted and unique")
        object.__setattr__(self, "input_fields", fields)
        if self.pattern_registry_digest is not None:
            object.__setattr__(
                self,
                "pattern_registry_digest",
                _require_digest(
                    "pattern_registry_digest",
                    self.pattern_registry_digest,
                ),
            )
        if type(self.deterministic) is not bool:
            raise TypeError("deterministic must be a boolean")
        if type(self.supports_relationships) is not bool:
            raise TypeError("supports_relationships must be a boolean")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
            "derivation_method": self.derivation_method.value,
            "input_schema": self.input_schema,
            "input_fields": list(self.input_fields),
            "pattern_registry_digest": self.pattern_registry_digest,
            "deterministic": self.deterministic,
            "supports_relationships": self.supports_relationships,
        }

    @classmethod
    def from_wire(cls, value: object) -> ProducerDescriptorV1:
        document = _require_object(value, cls._WIRE_KEYS, "producer descriptor")
        raw_fields = document["input_fields"]
        if not isinstance(raw_fields, list):
            raise TypeError("input_fields must be a JSON array")
        raw_digest = document["pattern_registry_digest"]
        return cls(
            producer_id=cast(str, document["producer_id"]),
            producer_version=cast(str, document["producer_version"]),
            derivation_method=_require_enum(
                "derivation_method",
                document["derivation_method"],
                DerivationMethodV1,
            ),
            input_schema=cast(str, document["input_schema"]),
            input_fields=tuple(cast(str, item) for item in raw_fields),
            pattern_registry_digest=(
                None if raw_digest is None else cast(str, raw_digest)
            ),
            deterministic=cast(bool, document["deterministic"]),
            supports_relationships=cast(bool, document["supports_relationships"]),
        )


@dataclass(frozen=True, slots=True)
class ProducerContextV1:
    source_lock_digest: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    producer_registry_digest: str
    pattern_registry_digest: str | None

    def __post_init__(self) -> None:
        for field in (
            "source_lock_digest",
            "producer_registry_digest",
        ):
            object.__setattr__(
                self,
                field,
                _require_digest(field, getattr(self, field)),
            )
        for field in ("m2_requirement_schema", "m2_bundle_schema"):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.pattern_registry_digest is not None:
            object.__setattr__(
                self,
                "pattern_registry_digest",
                _require_digest(
                    "pattern_registry_digest",
                    self.pattern_registry_digest,
                ),
            )


@dataclass(frozen=True, slots=True)
class RelationshipProposalV1:
    relationship: RequirementRelationshipV1

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, RequirementRelationshipV1):
            raise TypeError("relationship must be RequirementRelationshipV1")

    def to_wire(self) -> dict[str, JSONValue]:
        return self.relationship.to_wire()


@dataclass(frozen=True, slots=True)
class ProducerResultV1:
    status: ProducerResultStatusV1
    candidates: tuple[RequirementV1, ...]
    relationship_proposals: tuple[RelationshipProposalV1, ...]
    unresolved_reason: str | None
    negative_authority: None = None

    def __post_init__(self) -> None:
        status = _require_enum("status", self.status, ProducerResultStatusV1)
        object.__setattr__(self, "status", status)
        if not isinstance(self.candidates, tuple | list):
            raise TypeError("candidates must be a tuple or list")
        candidates = tuple(self.candidates)
        if any(not isinstance(item, RequirementV1) for item in candidates):
            raise TypeError("candidates must contain RequirementV1 values")
        object.__setattr__(self, "candidates", candidates)
        if not isinstance(self.relationship_proposals, tuple | list):
            raise TypeError("relationship_proposals must be a tuple or list")
        relationships = tuple(self.relationship_proposals)
        if any(not isinstance(item, RelationshipProposalV1) for item in relationships):
            raise TypeError(
                "relationship_proposals must contain RelationshipProposalV1 values"
            )
        object.__setattr__(self, "relationship_proposals", relationships)
        if self.unresolved_reason is not None:
            object.__setattr__(
                self,
                "unresolved_reason",
                _require_text("unresolved_reason", self.unresolved_reason),
            )
        if self.negative_authority is not None:
            raise ProducerContractError(
                "normal producers cannot emit negative authority"
            )
        if status is ProducerResultStatusV1.EMITTED:
            if not candidates:
                raise ProducerContractError("EMITTED requires a candidate")
            if self.unresolved_reason is not None:
                raise ProducerContractError("EMITTED cannot be unresolved")
        elif status is ProducerResultStatusV1.NO_MATCH:
            if candidates or relationships or self.unresolved_reason is not None:
                raise ProducerContractError("NO_MATCH must contain no proposals")
        elif status is ProducerResultStatusV1.UNSUPPORTED_SHAPE:
            if candidates or relationships:
                raise ProducerContractError(
                    "UNSUPPORTED_SHAPE must contain no proposals"
                )
            if self.unresolved_reason is None:
                raise ProducerContractError(
                    "UNSUPPORTED_SHAPE requires unresolved_reason"
                )

    @classmethod
    def emitted(
        cls,
        candidates: Sequence[RequirementV1],
        relationship_proposals: Sequence[RelationshipProposalV1] = (),
    ) -> ProducerResultV1:
        return cls(
            ProducerResultStatusV1.EMITTED,
            tuple(candidates),
            tuple(relationship_proposals),
            None,
        )

    @classmethod
    def no_match(cls) -> ProducerResultV1:
        return cls(ProducerResultStatusV1.NO_MATCH, (), (), None)

    @classmethod
    def unsupported_shape(cls, reason: str) -> ProducerResultV1:
        return cls(
            ProducerResultStatusV1.UNSUPPORTED_SHAPE,
            (),
            (),
            reason,
        )


class CandidateProducerV1(Protocol):
    descriptor: ProducerDescriptorV1

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1: ...


def execute_producer(
    producer: CandidateProducerV1,
    record: StructuralCardRecordV1,
    context: ProducerContextV1,
) -> ProducerResultV1:
    """Execute one producer without converting exceptions into no-match."""

    try:
        result = producer.produce(record, context)
    except ProducerExecutionError:
        raise
    except Exception as error:
        raise ProducerExecutionError("producer failed") from error
    if not isinstance(result, ProducerResultV1):
        raise ProducerExecutionError("producer returned an invalid result")
    return result


def validate_producer_candidate(
    candidate: RequirementV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None:
    if not isinstance(candidate, RequirementV1):
        raise TypeError("candidate must be RequirementV1")
    if candidate.review.status is not ReviewStatusV1.PROPOSED:
        raise ProducerContractError("producer candidates must be PROPOSED")
    if (
        candidate.review.reviewed_by is not None
        or candidate.review.reviewed_claim_digest is not None
    ):
        raise ProducerContractError(
            "producer candidates cannot contain review metadata"
        )
    try:
        validate_requirement_against_structural_record(
            candidate,
            record,
            expected_source_lock_digest,
        )
    except (TypeError, ValueError) as error:
        raise ProducerContractError(str(error)) from error


__all__ = [
    "CandidateProducerV1",
    "ProducerContextV1",
    "ProducerContractError",
    "ProducerDescriptorV1",
    "ProducerExecutionError",
    "ProducerResultStatusV1",
    "ProducerResultV1",
    "RelationshipProposalV1",
    "execute_producer",
    "validate_producer_candidate",
]
