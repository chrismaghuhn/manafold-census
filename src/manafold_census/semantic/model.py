"""Immutable M2 Requirement lifecycle values and root model."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any, ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from .evidence import (
    EvidenceV1,
    ExternalReviewEvidenceV1,
    RulesCitationEvidenceV1,
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
    _require_digest,
    _require_identifier_text,
    evidence_from_wire,
    evidence_sort_key,
    evidence_to_wire,
)
from .kind_payloads import KindPayloadV1, payload_from_wire, payload_to_wire
from .kinds import RequirementFamilyV1, RequirementKindV1, validate_kind_family
from .primitives import (
    SemanticDescriptorV1,
    UnknownValueV1,
    _require_enum,
    _require_object,
    _validate_json_wire,
    _WireModel,
)

REQUIREMENT_SCHEMA = "census.semantic-requirement.v1"
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_UNKNOWN_PATH_PATTERN = re.compile(r"^/(?:kind|parameters(?:[./].*)?)$")
_STRUCTURAL_EVIDENCE_TYPES = (
    StructuralRecordEvidenceV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
)


class DerivationMethodV1(StrEnum):
    HUMAN_AUTHORED = "HUMAN_AUTHORED"
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    PARSER = "PARSER"
    HEURISTIC = "HEURISTIC"
    MODEL = "MODEL"
    IMPORTED_ANNOTATION = "IMPORTED_ANNOTATION"


class ReviewStatusV1(StrEnum):
    PROPOSED = "PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ResolutionStateV1(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"


class ResolutionReasonV1(StrEnum):
    NONE = "NONE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"
    CONFLICTING_INTERPRETATIONS = "CONFLICTING_INTERPRETATIONS"
    UNKNOWN_SEMANTICS = "UNKNOWN_SEMANTICS"


def _wire_list(value: object, field: str) -> list[object]:
    _validate_json_wire(value, field)
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a JSON array")
    return value


def _tuple_values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


def _normalize_evidence(
    source: SourceRecordRefV1, value: object
) -> tuple[EvidenceV1, ...]:
    values = _tuple_values(value, "evidence")
    if not values:
        raise ValueError("evidence must be non-empty")
    allowed = _STRUCTURAL_EVIDENCE_TYPES + (
        RulesCitationEvidenceV1,
        ExternalReviewEvidenceV1,
    )
    if any(not isinstance(item, allowed) for item in values):
        raise TypeError("evidence contains an unsupported value")
    evidence = cast(tuple[EvidenceV1, ...], values)
    if not any(isinstance(item, _STRUCTURAL_EVIDENCE_TYPES) for item in evidence):
        raise ValueError("evidence must contain structural evidence")
    if any(
        isinstance(item, _STRUCTURAL_EVIDENCE_TYPES) and item.source != source
        for item in evidence
    ):
        raise ValueError("structural evidence source does not match requirement")
    wires = [canonical_json_bytes(evidence_to_wire(item)) for item in evidence]
    if len(wires) != len(set(wires)):
        raise ValueError("evidence must not contain duplicates")
    return tuple(sorted(evidence, key=evidence_sort_key))


@dataclass(frozen=True, slots=True)
class DerivationV1:
    method: DerivationMethodV1
    producer_id: str
    producer_version: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "method",
        "producer_id",
        "producer_version",
    }

    def __post_init__(self) -> None:
        values = (
            ("method", _require_enum("method", self.method, DerivationMethodV1)),
            ("producer_id", _require_identifier_text("producer_id", self.producer_id)),
            (
                "producer_version",
                _require_identifier_text("producer_version", self.producer_version),
            ),
        )
        for name, value in values:
            object.__setattr__(self, name, value)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "method": self.method.value,
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
        }

    @classmethod
    def from_wire(cls, value: object) -> DerivationV1:
        document = _require_object(value, cls._WIRE_KEYS, "derivation")
        return cls(
            _require_enum("method", document["method"], DerivationMethodV1),
            cast(str, document["producer_id"]),
            cast(str, document["producer_version"]),
        )


@dataclass(frozen=True, slots=True)
class ProvenanceV1:
    derivations: tuple[DerivationV1, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {"derivations"}

    def __post_init__(self) -> None:
        values = _tuple_values(self.derivations, "derivations")
        if not values:
            raise ValueError("derivations must be non-empty")
        if any(not isinstance(item, DerivationV1) for item in values):
            raise TypeError("derivations must contain DerivationV1 values")
        derivations = cast(tuple[DerivationV1, ...], values)
        keys = [canonical_json_bytes(item.to_wire()) for item in derivations]
        if len(keys) != len(set(keys)):
            raise ValueError("derivations must not contain duplicates")
        ordered = tuple(
            sorted(
                derivations,
                key=lambda item: (
                    item.method.value,
                    item.producer_id,
                    item.producer_version,
                ),
            )
        )
        object.__setattr__(self, "derivations", ordered)

    def to_wire(self) -> dict[str, JSONValue]:
        return {"derivations": [item.to_wire() for item in self.derivations]}

    @classmethod
    def from_wire(cls, value: object) -> ProvenanceV1:
        document = _require_object(value, cls._WIRE_KEYS, "provenance")
        derivations = tuple(
            DerivationV1.from_wire(item)
            for item in _wire_list(document["derivations"], "derivations")
        )
        return cls(derivations)


@dataclass(frozen=True, slots=True)
class ReviewV1:
    status: ReviewStatusV1
    reviewed_by: str | None
    reviewed_claim_digest: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "status",
        "reviewed_by",
        "reviewed_claim_digest",
    }

    def __post_init__(self) -> None:
        status = _require_enum("status", self.status, ReviewStatusV1)
        object.__setattr__(self, "status", status)
        if self.reviewed_by is not None:
            object.__setattr__(
                self,
                "reviewed_by",
                _require_identifier_text("reviewed_by", self.reviewed_by),
            )
        if self.reviewed_claim_digest is not None:
            object.__setattr__(
                self,
                "reviewed_claim_digest",
                _require_digest("reviewed_claim_digest", self.reviewed_claim_digest),
            )
        terminal = status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED)
        if terminal:
            if self.reviewed_by is None or self.reviewed_claim_digest is None:
                raise ValueError("terminal review requires reviewer and digest")
        elif self.reviewed_by is not None or self.reviewed_claim_digest is not None:
            raise ValueError("non-terminal review requires null metadata")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_claim_digest": self.reviewed_claim_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> ReviewV1:
        document = _require_object(value, cls._WIRE_KEYS, "review")
        return cls(
            _require_enum("status", document["status"], ReviewStatusV1),
            cast(str | None, document["reviewed_by"]),
            cast(str | None, document["reviewed_claim_digest"]),
        )


@dataclass(frozen=True, slots=True)
class ResolutionV1:
    state: ResolutionStateV1
    reason: ResolutionReasonV1
    unknown_paths: tuple[str, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {"state", "reason", "unknown_paths"}

    def __post_init__(self) -> None:
        state = _require_enum("state", self.state, ResolutionStateV1)
        reason = _require_enum("reason", self.reason, ResolutionReasonV1)
        paths = _tuple_values(self.unknown_paths, "unknown_paths")
        if any(not isinstance(path, str) for path in paths):
            raise TypeError("unknown_paths must contain strings")
        normalized_paths = tuple(
            _require_identifier_text("unknown_path", path) for path in paths
        )
        if any(
            _UNKNOWN_PATH_PATTERN.fullmatch(path) is None for path in normalized_paths
        ):
            raise ValueError("unknown_paths must target /kind or /parameters")
        if state is ResolutionStateV1.COMPLETE:
            if reason is not ResolutionReasonV1.NONE or normalized_paths:
                raise ValueError("COMPLETE resolution requires NONE and no paths")
        elif reason is ResolutionReasonV1.NONE or not normalized_paths:
            raise ValueError(
                "partial or unresolved resolution requires reason and paths"
            )
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "unknown_paths", normalized_paths)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "state": self.state.value,
            "reason": self.reason.value,
            "unknown_paths": list(self.unknown_paths),
        }

    @classmethod
    def from_wire(cls, value: object) -> ResolutionV1:
        document = _require_object(value, cls._WIRE_KEYS, "resolution")
        return cls(
            _require_enum("state", document["state"], ResolutionStateV1),
            _require_enum("reason", document["reason"], ResolutionReasonV1),
            tuple(
                cast(str, item)
                for item in _wire_list(document["unknown_paths"], "unknown_paths")
            ),
        )


def _semantic_flags(value: object) -> tuple[bool, bool]:
    unknown = isinstance(value, UnknownValueV1)
    escape = False
    if isinstance(value, SemanticDescriptorV1):
        escape = value.shape.value == "unknown" or (
            value.label is not None
            and value.subject is None
            and value.object_ref is None
            and value.value is None
            and not value.children
        )
    if isinstance(value, _WireModel):
        children = [
            _semantic_flags(getattr(value, item.name))
            for item in fields(cast(Any, value))
        ]
    elif isinstance(value, tuple | list):
        children = [_semantic_flags(item) for item in value]
    else:
        children = []
    return (
        unknown or any(item[0] for item in children),
        escape or any(item[1] for item in children),
    )


def _validate_resolution(
    kind: RequirementKindV1,
    parameters: KindPayloadV1,
    resolution: ResolutionV1,
) -> None:
    has_unknown, has_escape = _semantic_flags(parameters)
    if resolution.state is ResolutionStateV1.COMPLETE:
        if kind is RequirementKindV1.UNRESOLVED or has_unknown or has_escape:
            raise ValueError("COMPLETE resolution contains unresolved meaning")
    elif resolution.state is ResolutionStateV1.PARTIAL:
        if kind is RequirementKindV1.UNRESOLVED or not (
            has_unknown or resolution.unknown_paths
        ):
            raise ValueError("PARTIAL resolution requires a known unresolved dimension")
    elif not (
        kind is RequirementKindV1.UNRESOLVED
        or (
            resolution.reason is ResolutionReasonV1.CONFLICTING_INTERPRETATIONS
            and resolution.unknown_paths
        )
    ):
        raise ValueError("UNRESOLVED resolution requires unresolved kind or conflict")


@dataclass(frozen=True, slots=True)
class RequirementV1:
    requirement_id: str
    source: SourceRecordRefV1
    family: RequirementFamilyV1
    kind: RequirementKindV1
    parameters: KindPayloadV1
    evidence: tuple[EvidenceV1, ...]
    provenance: ProvenanceV1
    review: ReviewV1
    resolution: ResolutionV1

    SCHEMA: ClassVar[str] = REQUIREMENT_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "requirement_id",
        "source",
        "family",
        "kind",
        "parameters",
        "evidence",
        "provenance",
        "review",
        "resolution",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        family = _require_enum("family", self.family, RequirementFamilyV1)
        kind = _require_enum("kind", self.kind, RequirementKindV1)
        validate_kind_family(family, kind)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "kind", kind)
        payload_to_wire(family, kind, self.parameters)

        object.__setattr__(
            self, "evidence", _normalize_evidence(self.source, self.evidence)
        )
        if not isinstance(self.provenance, ProvenanceV1):
            raise TypeError("provenance must be ProvenanceV1")
        if not isinstance(self.review, ReviewV1):
            raise TypeError("review must be ReviewV1")
        if not isinstance(self.resolution, ResolutionV1):
            raise TypeError("resolution must be ResolutionV1")
        _validate_resolution(kind, self.parameters, self.resolution)

        from .identity import requirement_id_for, reviewed_claim_digest_for

        expected_id = requirement_id_for(self)
        actual_id = self.requirement_id
        if (
            not isinstance(actual_id, str)
            or _REQUIREMENT_ID_PATTERN.fullmatch(actual_id) is None
        ):
            raise ValueError("requirement_id must match the srq_ SHA-256 form")
        if actual_id != expected_id:
            raise ValueError("requirement_id does not match the identity payload")
        if self.review.status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED):
            expected_review = reviewed_claim_digest_for(self)
            if self.review.reviewed_claim_digest != expected_review:
                raise ValueError("reviewed_claim_digest is stale or incorrect")

    @classmethod
    def create(
        cls,
        *,
        source: SourceRecordRefV1,
        family: RequirementFamilyV1,
        kind: RequirementKindV1,
        parameters: KindPayloadV1,
        evidence: tuple[EvidenceV1, ...],
        provenance: ProvenanceV1,
        review: ReviewV1,
        resolution: ResolutionV1,
    ) -> RequirementV1:
        family_value = _require_enum("family", family, RequirementFamilyV1)
        kind_value = _require_enum("kind", kind, RequirementKindV1)
        validate_kind_family(family_value, kind_value)
        payload_to_wire(family_value, kind_value, parameters)
        from .identity import _requirement_id_for_parts

        requirement_id = _requirement_id_for_parts(
            source, family_value, kind_value, parameters
        )
        return cls(
            requirement_id,
            source,
            family_value,
            kind_value,
            parameters,
            evidence,
            provenance,
            review,
            resolution,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": REQUIREMENT_SCHEMA,
            "requirement_id": self.requirement_id,
            "source": self.source.to_wire(),
            "family": self.family.value,
            "kind": self.kind.value,
            "parameters": payload_to_wire(self.family, self.kind, self.parameters),
            "evidence": [evidence_to_wire(item) for item in self.evidence],
            "provenance": self.provenance.to_wire(),
            "review": self.review.to_wire(),
            "resolution": self.resolution.to_wire(),
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementV1:
        document = _require_object(value, cls._WIRE_KEYS, "RequirementV1")
        if document["schema"] != REQUIREMENT_SCHEMA:
            raise ValueError("schema must be census.semantic-requirement.v1")
        source = SourceRecordRefV1.from_wire(document["source"])
        family = _require_enum("family", document["family"], RequirementFamilyV1)
        kind = _require_enum("kind", document["kind"], RequirementKindV1)
        parameters = payload_from_wire(family, kind, document["parameters"])
        evidence = tuple(
            evidence_from_wire(item)
            for item in _wire_list(document["evidence"], "evidence")
        )
        return cls(
            cast(str, document["requirement_id"]),
            source,
            family,
            kind,
            parameters,
            evidence,
            ProvenanceV1.from_wire(document["provenance"]),
            ReviewV1.from_wire(document["review"]),
            ResolutionV1.from_wire(document["resolution"]),
        )


__all__ = [
    "DerivationMethodV1",
    "DerivationV1",
    "ProvenanceV1",
    "RequirementV1",
    "ResolutionReasonV1",
    "ResolutionStateV1",
    "ResolutionV1",
    "ReviewStatusV1",
    "ReviewV1",
]
