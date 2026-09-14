"""M4 link validation, cardinality, and preserved mapping decisions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.identity import wire_digest_for
from ..semantic.model import RequirementV1
from ..semantic.primitives import _require_enum, _require_object
from .link import (
    _LINK_ID_PATTERN,
    _REQUIREMENT_ID_PATTERN,
    _REVIEW_ID_PATTERN,
    _digest,
    _identifier,
    _values,
)
from .review import (
    CapabilityReviewRecordV1,
    MappingDecisionReviewSubjectV1,
    ReviewDecisionV1,
)

MAPPING_DECISION_SCHEMA = "census.requirement-mapping-decision.v1"
MAPPING_DECISION_DOMAIN = "census.requirement-mapping-decision.v1"
MAPPING_DECISION_PREFIX = "rmd_"


def _requirement(value: object) -> RequirementV1:
    if not isinstance(value, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    return value


class MappingDispositionV1(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    OUTLIER = "OUTLIER"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class MappingReasonV1(StrEnum):
    NO_REVIEWED_CAPABILITY = "NO_REVIEWED_CAPABILITY"
    M2_REVIEW_NOT_TERMINAL = "M2_REVIEW_NOT_TERMINAL"
    M4_ADMISSIBILITY_REVIEW_PENDING = "M4_ADMISSIBILITY_REVIEW_PENDING"
    M2_RESOLUTION_INCOMPLETE = "M2_RESOLUTION_INCOMPLETE"
    MULTIPLE_PLAUSIBLE_CAPABILITIES = "MULTIPLE_PLAUSIBLE_CAPABILITIES"
    NO_REUSABLE_GENERALIZATION = "NO_REUSABLE_GENERALIZATION"
    SPECIAL_CASE = "SPECIAL_CASE"
    EXPLICIT_REVIEW_CONFLICT = "EXPLICIT_REVIEW_CONFLICT"


_REASON_MATRIX: dict[MappingDispositionV1, frozenset[MappingReasonV1]] = {
    MappingDispositionV1.UNMAPPED: frozenset(
        {
            MappingReasonV1.NO_REVIEWED_CAPABILITY,
            MappingReasonV1.SPECIAL_CASE,
        }
    ),
    MappingDispositionV1.AMBIGUOUS: frozenset(
        {
            MappingReasonV1.MULTIPLE_PLAUSIBLE_CAPABILITIES,
            MappingReasonV1.EXPLICIT_REVIEW_CONFLICT,
        }
    ),
    MappingDispositionV1.OUTLIER: frozenset(
        {
            MappingReasonV1.NO_REUSABLE_GENERALIZATION,
            MappingReasonV1.SPECIAL_CASE,
        }
    ),
    MappingDispositionV1.INSUFFICIENT_EVIDENCE: frozenset(
        {
            MappingReasonV1.M2_REVIEW_NOT_TERMINAL,
            MappingReasonV1.M4_ADMISSIBILITY_REVIEW_PENDING,
            MappingReasonV1.M2_RESOLUTION_INCOMPLETE,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class RequirementMappingDecisionV1:
    m3_analysis_manifest_sha256: str
    requirement_id: str
    requirement_wire_digest: str
    disposition: MappingDispositionV1
    active_link_ids: tuple[str, ...]
    candidate_link_claims: tuple[str, ...]
    reason: MappingReasonV1 | None
    review_ref: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "m3_analysis_manifest_sha256",
        "requirement_id",
        "requirement_wire_digest",
        "disposition",
        "active_link_ids",
        "candidate_link_claims",
        "reason",
        "review_ref",
    }

    def __post_init__(self) -> None:
        manifest = _digest(
            "m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256
        )
        requirement_id = _identifier(
            "requirement_id", self.requirement_id, _REQUIREMENT_ID_PATTERN
        )
        wire_digest = _digest("requirement_wire_digest", self.requirement_wire_digest)
        disposition = _require_enum(
            "disposition", self.disposition, MappingDispositionV1
        )
        active = tuple(
            _identifier("active_link_id", item, _LINK_ID_PATTERN)
            for item in _values(self.active_link_ids, "active_link_ids")
        )
        candidate_claims = tuple(
            _digest("candidate_link_claim", item)
            for item in _values(self.candidate_link_claims, "candidate_link_claims")
        )
        if len(active) != len(set(active)) or len(candidate_claims) != len(
            set(candidate_claims)
        ):
            raise ValueError("mapping decision contains duplicate link references")
        reason = (
            None
            if self.reason is None
            else _require_enum("reason", self.reason, MappingReasonV1)
        )
        review_ref = self.review_ref
        if review_ref is not None:
            review_ref = _identifier("review_ref", review_ref, _REVIEW_ID_PATTERN)
        if disposition is MappingDispositionV1.MAPPED:
            if not active or reason is not None:
                raise ValueError(
                    "MAPPED decision requires active links and null reason"
                )
        else:
            if active:
                raise ValueError(
                    "active_link_ids must be empty for a non-MAPPED decision"
                )
            if reason is None:
                raise ValueError("non-MAPPED decision requires a reason")
            if reason not in _REASON_MATRIX[disposition]:
                raise ValueError("reason is not allowed for this mapping disposition")
        if (
            disposition
            in (
                MappingDispositionV1.AMBIGUOUS,
                MappingDispositionV1.OUTLIER,
            )
            and review_ref is None
        ):
            raise ValueError(
                "AMBIGUOUS and OUTLIER decisions require an accepted review"
            )
        object.__setattr__(self, "m3_analysis_manifest_sha256", manifest)
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "requirement_wire_digest", wire_digest)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "active_link_ids", tuple(sorted(active)))
        object.__setattr__(
            self, "candidate_link_claims", tuple(sorted(candidate_claims))
        )
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "review_ref", review_ref)

    @classmethod
    def for_requirement(
        cls,
        requirement: RequirementV1,
        m3_analysis_manifest_sha256: str,
        disposition: MappingDispositionV1,
        reason: MappingReasonV1 | None,
        *,
        active_link_ids: Sequence[str] = (),
        candidate_link_claims: Sequence[str] = (),
        review_ref: str | None = None,
    ) -> RequirementMappingDecisionV1:
        requirement = _requirement(requirement)
        return cls(
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            requirement_id=requirement.requirement_id,
            requirement_wire_digest=wire_digest_for(requirement),
            disposition=disposition,
            active_link_ids=tuple(active_link_ids),
            candidate_link_claims=tuple(candidate_link_claims),
            reason=reason,
            review_ref=review_ref,
        )

    def validate_against_requirement(self, requirement: RequirementV1) -> None:
        requirement = _requirement(requirement)
        if self.requirement_id != requirement.requirement_id:
            raise ValueError("mapping decision Requirement ID does not match")
        if self.requirement_wire_digest != wire_digest_for(requirement):
            raise ValueError("mapping decision Requirement wire digest does not match")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": MAPPING_DECISION_SCHEMA,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
            "disposition": self.disposition.value,
            "active_link_ids": list(self.active_link_ids),
            "candidate_link_claims": list(self.candidate_link_claims),
            "reason": None if self.reason is None else self.reason.value,
            "review_ref": self.review_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementMappingDecisionV1:
        document = _require_object(
            value, cls._WIRE_KEYS, "Requirement mapping decision"
        )
        if document["schema"] != MAPPING_DECISION_SCHEMA:
            raise ValueError(f"schema must be {MAPPING_DECISION_SCHEMA}")
        raw_active = document["active_link_ids"]
        raw_claims = document["candidate_link_claims"]
        if not isinstance(raw_active, list) or not isinstance(raw_claims, list):
            raise TypeError("mapping link collections must be JSON arrays")
        raw_reason = document["reason"]
        result = cls(
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            requirement_id=cast(str, document["requirement_id"]),
            requirement_wire_digest=cast(str, document["requirement_wire_digest"]),
            disposition=_require_enum(
                "disposition", document["disposition"], MappingDispositionV1
            ),
            active_link_ids=tuple(cast(str, item) for item in raw_active),
            candidate_link_claims=tuple(cast(str, item) for item in raw_claims),
            reason=(
                None
                if raw_reason is None
                else _require_enum("reason", raw_reason, MappingReasonV1)
            ),
            review_ref=cast(str | None, document["review_ref"]),
        )
        if result.to_wire() != document:
            raise ValueError("Requirement mapping decision wire is not canonical")
        return result


def mapping_decision(
    requirement: RequirementV1,
    disposition: MappingDispositionV1,
    reason: MappingReasonV1 | None,
    *,
    m3_analysis_manifest_sha256: str,
    active_link_ids: Sequence[str] = (),
    candidate_link_claims: Sequence[str] = (),
    review_ref: str | None = None,
) -> RequirementMappingDecisionV1:
    return RequirementMappingDecisionV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256,
        disposition,
        reason,
        active_link_ids=active_link_ids,
        candidate_link_claims=candidate_link_claims,
        review_ref=review_ref,
    )


def mapping_decision_claim_payload(
    decision: RequirementMappingDecisionV1,
) -> dict[str, JSONValue]:
    if not isinstance(decision, RequirementMappingDecisionV1):
        raise TypeError("decision must be RequirementMappingDecisionV1")
    wire = decision.to_wire()
    wire.pop("review_ref")
    return wire


def mapping_decision_claim_digest_for(decision: RequirementMappingDecisionV1) -> str:
    return domain_digest(
        MAPPING_DECISION_DOMAIN, mapping_decision_claim_payload(decision)
    )


def mapping_decision_id_for(decision: RequirementMappingDecisionV1) -> str:
    return MAPPING_DECISION_PREFIX + mapping_decision_claim_digest_for(decision)


def validate_mapping_decision(
    decision: RequirementMappingDecisionV1,
    reviews: Sequence[CapabilityReviewRecordV1],
) -> None:
    if not isinstance(decision, RequirementMappingDecisionV1):
        raise TypeError("decision must be RequirementMappingDecisionV1")
    if decision.review_ref is None:
        if decision.disposition in (
            MappingDispositionV1.AMBIGUOUS,
            MappingDispositionV1.OUTLIER,
        ):
            raise ValueError("mapping decision requires an accepted review")
        return
    records = tuple(reviews)
    if any(not isinstance(record, CapabilityReviewRecordV1) for record in records):
        raise TypeError("reviews must contain CapabilityReviewRecordV1 values")
    subject = MappingDecisionReviewSubjectV1(
        mapping_decision_id_for(decision),
        mapping_decision_claim_digest_for(decision),
    )
    matching = tuple(record for record in records if record.subject == subject)
    if any(record.decision is ReviewDecisionV1.ACCEPTED for record in matching) and any(
        record.decision is ReviewDecisionV1.REJECTED for record in matching
    ):
        raise ValueError("conflicting accepted and rejected mapping reviews")
    referenced = tuple(
        record for record in matching if record.record_id == decision.review_ref
    )
    if len(referenced) != 1 or referenced[0].decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError("mapping decision requires an exact accepted review")
