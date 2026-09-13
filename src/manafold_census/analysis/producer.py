"""Algorithm-independent M3 producer contracts and proposal validation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Protocol, cast

from ..canonical import (
    FrozenJSONValue,
    JSONValue,
    freeze_json,
    thaw_json,
)
from ..digest import domain_digest
from ..semantic.bundle import RequirementRelationshipV1
from ..semantic.model import (
    DerivationMethodV1,
    RequirementV1,
    ReviewStatusV1,
)
from ..semantic.primitives import _require_enum, _require_object
from ..semantic.validate import validate_requirement_against_structural_record
from ..structural.model import StructuralCardRecordV1
from .patterns import PatternSourceFieldV1

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProducerContractError(ValueError):
    """Raised when a producer emits a value outside the M3 contract."""


class ProducerExecutionError(RuntimeError):
    """Raised when a producer execution fails rather than finding no match."""


class ProducerResultStatusV1(StrEnum):
    EMITTED = "EMITTED"
    NO_MATCH = "NO_MATCH"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"


@dataclass(frozen=True, slots=True)
class ProducerFindingV1:
    candidate_index: int | None
    pattern_id: str | None
    pattern_version: str | None
    pattern_digest: str | None
    source_field: PatternSourceFieldV1 | None
    face_index: int | None
    exact_fragment: str | None
    clause_ordinal: int | None
    parser_span: tuple[int, int] | None

    def __post_init__(self) -> None:
        for field, value in (
            ("candidate_index", self.candidate_index),
            ("face_index", self.face_index),
            ("clause_ordinal", self.clause_ordinal),
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{field} must be a non-negative integer")
        pattern_fields = (self.pattern_id, self.pattern_version, self.pattern_digest)
        if any(item is not None for item in pattern_fields) and not all(
            item is not None for item in pattern_fields
        ):
            raise ValueError("pattern identity fields must be all present or null")
        if self.pattern_id is not None:
            _require_text("pattern_id", self.pattern_id)
            _require_text("pattern_version", self.pattern_version)
            _require_digest("pattern_digest", self.pattern_digest)
        if self.source_field is not None:
            object.__setattr__(
                self,
                "source_field",
                _require_enum("source_field", self.source_field, PatternSourceFieldV1),
            )
        if (
            self.face_index is not None
            and self.source_field is not PatternSourceFieldV1.ORACLE_TEXT
        ):
            raise ValueError("face_index requires oracle_text source_field")
        if self.exact_fragment is not None:
            _require_text("exact_fragment", self.exact_fragment)
            if self.source_field is not PatternSourceFieldV1.ORACLE_TEXT:
                raise ValueError("exact_fragment requires oracle_text source_field")
        if self.parser_span is not None:
            if (
                not isinstance(self.parser_span, tuple | list)
                or len(self.parser_span) != 2
            ):
                raise ValueError("parser_span must contain two offsets")
            start, end = self.parser_span
            if (
                any(type(value) is not int for value in (start, end))
                or start < 0
                or end < start
            ):
                raise ValueError("parser_span offsets are invalid")
            object.__setattr__(self, "parser_span", (start, end))


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
class ImmutableRegistrySnapshotV1:
    """Immutable registry bytes carried into a producer invocation."""

    registry_kind: str
    registry_schema: str
    digest_domain: str
    digest: str
    wire: FrozenJSONValue

    def __post_init__(self) -> None:
        for field in ("registry_kind", "registry_schema", "digest_domain"):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        object.__setattr__(self, "digest", _require_digest("digest", self.digest))
        wire = (
            thaw_json(cast(FrozenJSONValue, self.wire))
            if isinstance(self.wire, Mapping | tuple)
            else self.wire
        )
        frozen = freeze_json(wire)
        object.__setattr__(self, "wire", frozen)
        expected = domain_digest(self.digest_domain, thaw_json(frozen))
        if self.digest != expected:
            raise ValueError("registry snapshot digest does not match wire")

    @classmethod
    def from_wire(
        cls,
        registry_kind: str,
        registry_schema: str,
        digest_domain: str,
        wire: object,
    ) -> ImmutableRegistrySnapshotV1:
        frozen = freeze_json(wire)
        digest = domain_digest(digest_domain, thaw_json(frozen))
        return cls(
            registry_kind=registry_kind,
            registry_schema=registry_schema,
            digest_domain=digest_domain,
            digest=digest,
            wire=frozen,
        )

    def to_wire(self) -> JSONValue:
        return thaw_json(self.wire)


@dataclass(frozen=True, slots=True)
class ProducerContextV1:
    source_lock_digest: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    producer_registry: ImmutableRegistrySnapshotV1
    pattern_registry: ImmutableRegistrySnapshotV1 | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_lock_digest",
            _require_digest("source_lock_digest", self.source_lock_digest),
        )
        for field in ("m2_requirement_schema", "m2_bundle_schema"):
            object.__setattr__(
                self,
                field,
                _require_text(field, getattr(self, field)),
            )
        if not isinstance(self.producer_registry, ImmutableRegistrySnapshotV1):
            raise TypeError("producer_registry must be an immutable snapshot")
        if self.pattern_registry is not None and not isinstance(
            self.pattern_registry,
            ImmutableRegistrySnapshotV1,
        ):
            raise TypeError("pattern_registry must be an immutable snapshot or None")

    @property
    def producer_registry_digest(self) -> str:
        return self.producer_registry.digest

    @property
    def pattern_registry_digest(self) -> str | None:
        return None if self.pattern_registry is None else self.pattern_registry.digest


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
    findings: tuple[ProducerFindingV1, ...] = ()

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
        if not isinstance(self.findings, tuple | list):
            raise TypeError("findings must be a tuple or list")
        findings = tuple(self.findings)
        if any(not isinstance(item, ProducerFindingV1) for item in findings):
            raise TypeError("findings must contain ProducerFindingV1 values")
        object.__setattr__(self, "findings", findings)
        if status is ProducerResultStatusV1.EMITTED:
            if not candidates:
                raise ProducerContractError("EMITTED requires a candidate")
            if self.unresolved_reason is not None:
                raise ProducerContractError("EMITTED cannot be unresolved")
            indexes = [item.candidate_index for item in findings]
            if any(index is None or index >= len(candidates) for index in indexes):
                raise ProducerContractError("finding candidate_index is out of range")
            if len(indexes) != len(set(indexes)):
                raise ProducerContractError(
                    "findings contain duplicate candidate_index"
                )
        elif status is ProducerResultStatusV1.NO_MATCH:
            if (
                candidates
                or relationships
                or findings
                or self.unresolved_reason is not None
            ):
                raise ProducerContractError("NO_MATCH must contain no proposals")
        elif status is ProducerResultStatusV1.UNSUPPORTED_SHAPE:
            if candidates or relationships or findings:
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
        findings: Sequence[ProducerFindingV1] = (),
    ) -> ProducerResultV1:
        return cls(
            ProducerResultStatusV1.EMITTED,
            tuple(candidates),
            tuple(relationship_proposals),
            None,
            findings=tuple(findings),
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

    descriptor = getattr(producer, "descriptor", None)
    if not isinstance(descriptor, ProducerDescriptorV1):
        raise ProducerContractError("producer must expose ProducerDescriptorV1")
    if not isinstance(context, ProducerContextV1):
        raise ProducerContractError("producer context must be ProducerContextV1")
    if descriptor.pattern_registry_digest is not None:
        if context.pattern_registry is None:
            raise ProducerContractError(
                "producer declares pattern_registry_digest but context has no "
                "pattern_registry snapshot"
            )
        if descriptor.pattern_registry_digest != context.pattern_registry.digest:
            raise ProducerContractError(
                "producer pattern_registry_digest does not match context snapshot"
            )

    try:
        result = producer.produce(record, context)
    except ProducerExecutionError:
        raise
    except Exception as error:
        raise ProducerExecutionError("producer failed") from error
    if not isinstance(result, ProducerResultV1):
        raise ProducerExecutionError("producer returned an invalid result")
    if result.relationship_proposals and not descriptor.supports_relationships:
        raise ProducerContractError(
            "producer descriptor supports_relationships=false but emitted "
            "relationship proposals"
        )
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
    "ProducerFindingV1",
    "ProducerResultStatusV1",
    "ProducerResultV1",
    "ImmutableRegistrySnapshotV1",
    "RelationshipProposalV1",
    "execute_producer",
    "validate_producer_candidate",
]
