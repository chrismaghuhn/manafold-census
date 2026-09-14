"""Closed M4 review authority records and non-cyclic review identities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.primitives import (
    _require_enum,
    _require_object,
    _require_text,
)
from .model import CapabilityRefV1

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVIEW_ID_PATTERN = re.compile(r"^mrv_[0-9a-f]{64}$")
_LINK_ID_PATTERN = re.compile(r"^rcl_[0-9a-f]{64}$")
_MAPPING_DECISION_ID_PATTERN = re.compile(r"^rmd_[0-9a-f]{64}$")
_EVOLUTION_ID_PATTERN = re.compile(r"^cev_[0-9a-f]{64}$")

REVIEW_RECORD_DOMAIN = "census.capability-review-record.v1"
REVIEW_RECORD_PREFIX = "mrv_"
CAPABILITY_REVIEW_SCHEMA = "census.capability-review.v1"


class ReviewSubjectKindV1(StrEnum):
    CAPABILITY_DEFINITION = "CAPABILITY_DEFINITION"
    CAPABILITY_LINK = "CAPABILITY_LINK"
    MAPPING_DECISION = "MAPPING_DECISION"
    EVOLUTION = "EVOLUTION"


class ReviewDecisionV1(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class GeneralizationBasisV1(StrEnum):
    MULTI_SOURCE_REUSE = "MULTI_SOURCE_REUSE"
    SINGLE_OBSERVATION_GENERALIZATION = "SINGLE_OBSERVATION_GENERALIZATION"


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _digest_identifier(field: str, value: object, pattern: re.Pattern[str]) -> str:
    text = _require_text(field, value)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} must use its closed digest identity form")
    return text


def _subject_document(
    value: object,
    keys: set[str],
    label: str,
    kind: ReviewSubjectKindV1,
) -> dict[str, object]:
    document = _require_object(value, keys, label)
    if document["type"] != kind.value:
        raise ValueError(f"subject type must be {kind.value}")
    return document


@dataclass(frozen=True, slots=True)
class CapabilityDefinitionReviewSubjectV1:
    capability_family_id: str
    capability_version: int
    claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "type",
        "capability_family_id",
        "capability_version",
        "claim_digest",
    }
    KIND: ClassVar[ReviewSubjectKindV1] = ReviewSubjectKindV1.CAPABILITY_DEFINITION

    @property
    def capability_ref(self) -> CapabilityRefV1:
        return CapabilityRefV1(
            self.capability_family_id,
            self.capability_version,
            self.claim_digest,
        )

    def __post_init__(self) -> None:
        reference = CapabilityRefV1(
            self.capability_family_id,
            self.capability_version,
            self.claim_digest,
        )
        object.__setattr__(self, "capability_family_id", reference.capability_family_id)
        object.__setattr__(self, "capability_version", reference.capability_version)
        object.__setattr__(self, "claim_digest", reference.claim_digest)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "type": self.KIND.value,
            "capability_family_id": self.capability_family_id,
            "capability_version": self.capability_version,
            "claim_digest": self.claim_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityDefinitionReviewSubjectV1:
        document = _subject_document(
            value,
            cls._WIRE_KEYS,
            "capability definition review subject",
            cls.KIND,
        )
        result = cls(
            cast(str, document["capability_family_id"]),
            cast(int, document["capability_version"]),
            cast(str, document["claim_digest"]),
        )
        return result


@dataclass(frozen=True, slots=True)
class CapabilityLinkReviewSubjectV1:
    link_id: str
    link_claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {"type", "link_id", "link_claim_digest"}
    KIND: ClassVar[ReviewSubjectKindV1] = ReviewSubjectKindV1.CAPABILITY_LINK

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "link_id",
            _digest_identifier("link_id", self.link_id, _LINK_ID_PATTERN),
        )
        object.__setattr__(
            self,
            "link_claim_digest",
            _digest("link_claim_digest", self.link_claim_digest),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "type": self.KIND.value,
            "link_id": self.link_id,
            "link_claim_digest": self.link_claim_digest,
        }


@dataclass(frozen=True, slots=True)
class MappingDecisionReviewSubjectV1:
    mapping_decision_id: str
    mapping_decision_claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "type",
        "mapping_decision_id",
        "mapping_decision_claim_digest",
    }
    KIND: ClassVar[ReviewSubjectKindV1] = ReviewSubjectKindV1.MAPPING_DECISION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mapping_decision_id",
            _digest_identifier(
                "mapping_decision_id",
                self.mapping_decision_id,
                _MAPPING_DECISION_ID_PATTERN,
            ),
        )
        object.__setattr__(
            self,
            "mapping_decision_claim_digest",
            _digest(
                "mapping_decision_claim_digest",
                self.mapping_decision_claim_digest,
            ),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "type": self.KIND.value,
            "mapping_decision_id": self.mapping_decision_id,
            "mapping_decision_claim_digest": self.mapping_decision_claim_digest,
        }


@dataclass(frozen=True, slots=True)
class EvolutionReviewSubjectV1:
    event_id: str
    evolution_claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {"type", "event_id", "evolution_claim_digest"}
    KIND: ClassVar[ReviewSubjectKindV1] = ReviewSubjectKindV1.EVOLUTION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            _digest_identifier("event_id", self.event_id, _EVOLUTION_ID_PATTERN),
        )
        object.__setattr__(
            self,
            "evolution_claim_digest",
            _digest("evolution_claim_digest", self.evolution_claim_digest),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "type": self.KIND.value,
            "event_id": self.event_id,
            "evolution_claim_digest": self.evolution_claim_digest,
        }


type ReviewSubjectV1 = (
    CapabilityDefinitionReviewSubjectV1
    | CapabilityLinkReviewSubjectV1
    | MappingDecisionReviewSubjectV1
    | EvolutionReviewSubjectV1
)


def _require_subject(value: object) -> ReviewSubjectV1:
    if not isinstance(
        value,
        CapabilityDefinitionReviewSubjectV1
        | CapabilityLinkReviewSubjectV1
        | MappingDecisionReviewSubjectV1
        | EvolutionReviewSubjectV1,
    ):
        raise TypeError("subject must be a typed review subject")
    return value


def review_subject_from_wire(value: object) -> ReviewSubjectV1:
    if not isinstance(value, dict):
        raise TypeError("typed review subject must be an object")
    kind = _require_enum("subject type", value.get("type"), ReviewSubjectKindV1)
    if kind is ReviewSubjectKindV1.CAPABILITY_DEFINITION:
        return CapabilityDefinitionReviewSubjectV1.from_wire(value)
    if kind is ReviewSubjectKindV1.CAPABILITY_LINK:
        document = _subject_document(
            value,
            CapabilityLinkReviewSubjectV1._WIRE_KEYS,
            "Capability link review subject",
            kind,
        )
        return CapabilityLinkReviewSubjectV1(
            cast(str, document["link_id"]),
            cast(str, document["link_claim_digest"]),
        )
    if kind is ReviewSubjectKindV1.MAPPING_DECISION:
        document = _subject_document(
            value,
            MappingDecisionReviewSubjectV1._WIRE_KEYS,
            "mapping decision review subject",
            kind,
        )
        return MappingDecisionReviewSubjectV1(
            cast(str, document["mapping_decision_id"]),
            cast(str, document["mapping_decision_claim_digest"]),
        )
    document = _subject_document(
        value, EvolutionReviewSubjectV1._WIRE_KEYS, "evolution review subject", kind
    )
    return EvolutionReviewSubjectV1(
        cast(str, document["event_id"]),
        cast(str, document["evolution_claim_digest"]),
    )


def _review_claim_payload_values(
    *,
    authority_id: str,
    authority_version: str,
    subject: ReviewSubjectV1,
    decision: ReviewDecisionV1,
    reviewer_id: str,
    generalization_basis: GeneralizationBasisV1 | None,
) -> dict[str, JSONValue]:
    return {
        "review_schema": CAPABILITY_REVIEW_SCHEMA,
        "authority_id": authority_id,
        "authority_version": authority_version,
        "subject": subject.to_wire(),
        "decision": decision.value,
        "reviewer_id": reviewer_id,
        "generalization_basis": (
            None if generalization_basis is None else generalization_basis.value
        ),
    }


@dataclass(frozen=True, slots=True)
class CapabilityReviewRecordV1:
    authority_id: str
    authority_version: str
    record_id: str
    subject: ReviewSubjectV1
    decision: ReviewDecisionV1
    reviewer_id: str
    generalization_basis: GeneralizationBasisV1 | None
    review_digest: str

    REVIEW_SCHEMA: ClassVar[str] = CAPABILITY_REVIEW_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_id",
        "authority_version",
        "record_id",
        "subject",
        "decision",
        "reviewer_id",
        "generalization_basis",
        "review_digest",
    }

    def __post_init__(self) -> None:
        authority_id = _require_text("authority_id", self.authority_id)
        authority_version = _require_text("authority_version", self.authority_version)
        subject = _require_subject(self.subject)
        decision = _require_enum("decision", self.decision, ReviewDecisionV1)
        reviewer_id = _require_text("reviewer_id", self.reviewer_id)
        basis = (
            None
            if self.generalization_basis is None
            else _require_enum(
                "generalization_basis",
                self.generalization_basis,
                GeneralizationBasisV1,
            )
        )
        if subject.KIND is not ReviewSubjectKindV1.CAPABILITY_DEFINITION:
            if basis is not None:
                raise ValueError(
                    "generalization_basis must be null for this review subject"
                )
        elif decision is ReviewDecisionV1.ACCEPTED and basis is None:
            raise ValueError("accepted definition review requires generalization_basis")

        record_id = _digest_identifier("record_id", self.record_id, _REVIEW_ID_PATTERN)
        review_digest = _digest("review_digest", self.review_digest)
        expected_digest = domain_digest(
            REVIEW_RECORD_DOMAIN,
            _review_claim_payload_values(
                authority_id=authority_id,
                authority_version=authority_version,
                subject=subject,
                decision=decision,
                reviewer_id=reviewer_id,
                generalization_basis=basis,
            ),
        )
        expected_record_id = REVIEW_RECORD_PREFIX + expected_digest
        if record_id != expected_record_id:
            raise ValueError("record_id does not match review_digest")
        if review_digest != expected_digest:
            raise ValueError("review_digest does not match the review claim")

        object.__setattr__(self, "authority_id", authority_id)
        object.__setattr__(self, "authority_version", authority_version)
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "reviewer_id", reviewer_id)
        object.__setattr__(self, "generalization_basis", basis)
        object.__setattr__(self, "review_digest", review_digest)

    @classmethod
    def create(
        cls,
        *,
        authority_id: str,
        authority_version: str,
        subject: ReviewSubjectV1,
        decision: ReviewDecisionV1,
        reviewer_id: str,
        generalization_basis: GeneralizationBasisV1 | None,
    ) -> CapabilityReviewRecordV1:
        authority_id_value = _require_text("authority_id", authority_id)
        authority_version_value = _require_text("authority_version", authority_version)
        subject = _require_subject(subject)
        decision_value = _require_enum("decision", decision, ReviewDecisionV1)
        reviewer_id_value = _require_text("reviewer_id", reviewer_id)
        basis_value = (
            None
            if generalization_basis is None
            else _require_enum(
                "generalization_basis",
                generalization_basis,
                GeneralizationBasisV1,
            )
        )
        digest = domain_digest(
            REVIEW_RECORD_DOMAIN,
            _review_claim_payload_values(
                authority_id=authority_id_value,
                authority_version=authority_version_value,
                subject=subject,
                decision=decision_value,
                reviewer_id=reviewer_id_value,
                generalization_basis=basis_value,
            ),
        )
        return cls(
            authority_id=authority_id_value,
            authority_version=authority_version_value,
            record_id=REVIEW_RECORD_PREFIX + digest,
            subject=subject,
            decision=decision_value,
            reviewer_id=reviewer_id_value,
            generalization_basis=basis_value,
            review_digest=digest,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.REVIEW_SCHEMA,
            "authority_id": self.authority_id,
            "authority_version": self.authority_version,
            "record_id": self.record_id,
            "subject": self.subject.to_wire(),
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
            "generalization_basis": (
                None
                if self.generalization_basis is None
                else self.generalization_basis.value
            ),
            "review_digest": self.review_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityReviewRecordV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability review record")
        schema = _require_text("schema", document["schema"])
        if schema != cls.REVIEW_SCHEMA:
            raise ValueError(f"schema must be {cls.REVIEW_SCHEMA}")
        raw_basis = document["generalization_basis"]
        result = cls(
            authority_id=cast(str, document["authority_id"]),
            authority_version=cast(str, document["authority_version"]),
            record_id=cast(str, document["record_id"]),
            subject=review_subject_from_wire(document["subject"]),
            decision=_require_enum("decision", document["decision"], ReviewDecisionV1),
            reviewer_id=cast(str, document["reviewer_id"]),
            generalization_basis=(
                None
                if raw_basis is None
                else _require_enum(
                    "generalization_basis",
                    raw_basis,
                    GeneralizationBasisV1,
                )
            ),
            review_digest=cast(str, document["review_digest"]),
        )
        if result.to_wire() != document:
            raise ValueError("capability review record is not canonical")
        return result


def review_claim_payload(record: CapabilityReviewRecordV1) -> dict[str, JSONValue]:
    if not isinstance(record, CapabilityReviewRecordV1):
        raise TypeError("record must be CapabilityReviewRecordV1")
    return _review_claim_payload_values(
        authority_id=record.authority_id,
        authority_version=record.authority_version,
        subject=record.subject,
        decision=record.decision,
        reviewer_id=record.reviewer_id,
        generalization_basis=record.generalization_basis,
    )


def review_digest_for(record: CapabilityReviewRecordV1) -> str:
    return domain_digest(REVIEW_RECORD_DOMAIN, review_claim_payload(record))


def review_record_id_for(record: CapabilityReviewRecordV1) -> str:
    return REVIEW_RECORD_PREFIX + review_digest_for(record)
