"""M4 SOURCE_REQUIREMENT_ADMISSIBILITY authority records."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.identity import reviewed_claim_digest_for, wire_digest_for
from ..semantic.model import RequirementV1, ResolutionStateV1, ReviewStatusV1
from ..semantic.primitives import _require_enum, _require_object, _require_text
from .identity import ADMISSIBILITY_DOMAIN, ADMISSIBILITY_PREFIX

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_RECORD_ID_PATTERN = re.compile(r"^sra_[0-9a-f]{64}$")
ADMISSIBILITY_SCHEMA = "census.source-requirement-admissibility.v1"


class AdmissibilityDecisionV1(StrEnum):
    ACCEPTED_FOR_CAPABILITY_MAPPING = "ACCEPTED_FOR_CAPABILITY_MAPPING"
    REJECTED_FOR_CAPABILITY_MAPPING = "REJECTED_FOR_CAPABILITY_MAPPING"


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _require_identifier(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _REQUIREMENT_ID_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must use the srq_ digest identity form")
    return text


def _require_record_id(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _RECORD_ID_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must use the sra_ digest identity form")
    return text


def _require_requirement(value: object) -> RequirementV1:
    if not isinstance(value, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    return value


def _accepted_requirement_state(
    status: ReviewStatusV1,
    resolution: ResolutionStateV1,
) -> None:
    if status not in (ReviewStatusV1.PROPOSED, ReviewStatusV1.IN_REVIEW):
        raise ValueError("Requirement is not admissible for Capability mapping")
    if resolution is not ResolutionStateV1.COMPLETE:
        raise ValueError("Requirement is not admissible for Capability mapping")


def _claim_payload_values(
    *,
    authority_id: str,
    authority_version: str,
    m3_analysis_manifest_sha256: str,
    requirement_id: str,
    requirement_wire_digest: str,
    m2_review_status_observed: ReviewStatusV1,
    m2_resolution_state_observed: ResolutionStateV1,
    m2_reviewed_claim_digest: str,
    decision: AdmissibilityDecisionV1,
    reviewer_id: str,
) -> dict[str, JSONValue]:
    return {
        "schema": ADMISSIBILITY_SCHEMA,
        "authority_id": authority_id,
        "authority_version": authority_version,
        "m3_analysis_manifest_sha256": m3_analysis_manifest_sha256,
        "requirement_id": requirement_id,
        "requirement_wire_digest": requirement_wire_digest,
        "m2_review_status_observed": m2_review_status_observed.value,
        "m2_resolution_state_observed": m2_resolution_state_observed.value,
        "m2_reviewed_claim_digest": m2_reviewed_claim_digest,
        "decision": decision.value,
        "reviewer_id": reviewer_id,
    }


@dataclass(frozen=True, slots=True)
class SourceRequirementAdmissibilityV1:
    authority_id: str
    authority_version: str
    record_id: str
    review_digest: str
    m3_analysis_manifest_sha256: str
    requirement_id: str
    requirement_wire_digest: str
    m2_review_status_observed: ReviewStatusV1
    m2_resolution_state_observed: ResolutionStateV1
    m2_reviewed_claim_digest: str
    decision: AdmissibilityDecisionV1
    reviewer_id: str

    SCHEMA: ClassVar[str] = ADMISSIBILITY_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_id",
        "authority_version",
        "record_id",
        "review_digest",
        "m3_analysis_manifest_sha256",
        "requirement_id",
        "requirement_wire_digest",
        "m2_review_status_observed",
        "m2_resolution_state_observed",
        "m2_reviewed_claim_digest",
        "decision",
        "reviewer_id",
    }

    def __post_init__(self) -> None:
        authority_id = _require_text("authority_id", self.authority_id)
        authority_version = _require_text("authority_version", self.authority_version)
        record_id = _require_record_id("record_id", self.record_id)
        review_digest = _digest("review_digest", self.review_digest)
        manifest_sha256 = _digest(
            "m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256
        )
        requirement_id = _require_identifier("requirement_id", self.requirement_id)
        requirement_wire_digest = _digest(
            "requirement_wire_digest", self.requirement_wire_digest
        )
        status = _require_enum(
            "m2_review_status_observed", self.m2_review_status_observed, ReviewStatusV1
        )
        resolution = _require_enum(
            "m2_resolution_state_observed",
            self.m2_resolution_state_observed,
            ResolutionStateV1,
        )
        reviewed_claim_digest = _digest(
            "m2_reviewed_claim_digest", self.m2_reviewed_claim_digest
        )
        decision = _require_enum("decision", self.decision, AdmissibilityDecisionV1)
        reviewer_id = _require_text("reviewer_id", self.reviewer_id)
        if decision is AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING:
            _accepted_requirement_state(status, resolution)

        expected_digest = domain_digest(
            ADMISSIBILITY_DOMAIN,
            _claim_payload_values(
                authority_id=authority_id,
                authority_version=authority_version,
                m3_analysis_manifest_sha256=manifest_sha256,
                requirement_id=requirement_id,
                requirement_wire_digest=requirement_wire_digest,
                m2_review_status_observed=status,
                m2_resolution_state_observed=resolution,
                m2_reviewed_claim_digest=reviewed_claim_digest,
                decision=decision,
                reviewer_id=reviewer_id,
            ),
        )
        if record_id != ADMISSIBILITY_PREFIX + expected_digest:
            raise ValueError("record_id does not match review_digest")
        if review_digest != expected_digest:
            raise ValueError("review_digest does not match the admissibility claim")

        object.__setattr__(self, "authority_id", authority_id)
        object.__setattr__(self, "authority_version", authority_version)
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "review_digest", review_digest)
        object.__setattr__(self, "m3_analysis_manifest_sha256", manifest_sha256)
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "requirement_wire_digest", requirement_wire_digest)
        object.__setattr__(self, "m2_review_status_observed", status)
        object.__setattr__(self, "m2_resolution_state_observed", resolution)
        object.__setattr__(self, "m2_reviewed_claim_digest", reviewed_claim_digest)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "reviewer_id", reviewer_id)

    @classmethod
    def for_requirement(
        cls,
        requirement: RequirementV1,
        *,
        m3_analysis_manifest_sha256: str,
        authority_id: str,
        authority_version: str,
        reviewer_id: str,
        decision: AdmissibilityDecisionV1 = (
            AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING
        ),
    ) -> SourceRequirementAdmissibilityV1:
        requirement = _require_requirement(requirement)
        return cls._from_requirement_values(
            requirement,
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            authority_id=authority_id,
            authority_version=authority_version,
            reviewer_id=reviewer_id,
            decision=decision,
        )

    @classmethod
    def create(
        cls,
        requirement: RequirementV1,
        *,
        m3_analysis_manifest_sha256: str,
        authority_id: str,
        authority_version: str,
        reviewer_id: str,
        decision: AdmissibilityDecisionV1 = (
            AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING
        ),
    ) -> SourceRequirementAdmissibilityV1:
        return cls.for_requirement(
            requirement,
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            authority_id=authority_id,
            authority_version=authority_version,
            reviewer_id=reviewer_id,
            decision=decision,
        )

    @classmethod
    def _from_requirement_values(
        cls,
        requirement: RequirementV1,
        *,
        m3_analysis_manifest_sha256: str,
        authority_id: str,
        authority_version: str,
        reviewer_id: str,
        decision: AdmissibilityDecisionV1,
    ) -> SourceRequirementAdmissibilityV1:
        status = requirement.review.status
        resolution = requirement.resolution.state
        decision_value = _require_enum("decision", decision, AdmissibilityDecisionV1)
        if decision_value is AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING:
            _accepted_requirement_state(status, resolution)
        authority_id_value = _require_text("authority_id", authority_id)
        authority_version_value = _require_text("authority_version", authority_version)
        manifest_value = _digest(
            "m3_analysis_manifest_sha256", m3_analysis_manifest_sha256
        )
        reviewer_id_value = _require_text("reviewer_id", reviewer_id)
        wire_digest = wire_digest_for(requirement)
        reviewed_digest = reviewed_claim_digest_for(requirement)
        digest = domain_digest(
            ADMISSIBILITY_DOMAIN,
            _claim_payload_values(
                authority_id=authority_id_value,
                authority_version=authority_version_value,
                m3_analysis_manifest_sha256=manifest_value,
                requirement_id=requirement.requirement_id,
                requirement_wire_digest=wire_digest,
                m2_review_status_observed=status,
                m2_resolution_state_observed=resolution,
                m2_reviewed_claim_digest=reviewed_digest,
                decision=decision_value,
                reviewer_id=reviewer_id_value,
            ),
        )
        return cls(
            authority_id=authority_id_value,
            authority_version=authority_version_value,
            record_id=ADMISSIBILITY_PREFIX + digest,
            review_digest=digest,
            m3_analysis_manifest_sha256=manifest_value,
            requirement_id=requirement.requirement_id,
            requirement_wire_digest=wire_digest,
            m2_review_status_observed=status,
            m2_resolution_state_observed=resolution,
            m2_reviewed_claim_digest=reviewed_digest,
            decision=decision_value,
            reviewer_id=reviewer_id_value,
        )

    def validate_m3_manifest(self, selected_m3_manifest_sha256: str) -> None:
        selected = _digest("selected_m3_manifest_sha256", selected_m3_manifest_sha256)
        if self.m3_analysis_manifest_sha256 != selected:
            raise ValueError(
                "admissibility record does not match the selected M3 manifest"
            )

    def validate_against_requirement(self, requirement: RequirementV1) -> None:
        requirement = _require_requirement(requirement)
        if self.requirement_id != requirement.requirement_id:
            raise ValueError("admissibility Requirement ID does not match")
        expected_wire_digest = wire_digest_for(requirement)
        if self.requirement_wire_digest != expected_wire_digest:
            raise ValueError("Requirement wire digest does not match")
        expected_review_digest = reviewed_claim_digest_for(requirement)
        if self.m2_reviewed_claim_digest != expected_review_digest:
            raise ValueError("Requirement reviewed claim digest does not match")
        if self.m2_review_status_observed is not requirement.review.status:
            raise ValueError("observed M2 review status does not match Requirement")
        if self.m2_resolution_state_observed is not requirement.resolution.state:
            raise ValueError("observed M2 resolution state does not match Requirement")
        if self.decision is AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING:
            _accepted_requirement_state(
                requirement.review.status, requirement.resolution.state
            )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_id": self.authority_id,
            "authority_version": self.authority_version,
            "record_id": self.record_id,
            "review_digest": self.review_digest,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
            "m2_review_status_observed": self.m2_review_status_observed.value,
            "m2_resolution_state_observed": self.m2_resolution_state_observed.value,
            "m2_reviewed_claim_digest": self.m2_reviewed_claim_digest,
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
        }

    @classmethod
    def from_wire(cls, value: object) -> SourceRequirementAdmissibilityV1:
        document = _require_object(
            value, cls._WIRE_KEYS, "source Requirement admissibility"
        )
        schema = _require_text("schema", document["schema"])
        if schema != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        result = cls(
            authority_id=cast(str, document["authority_id"]),
            authority_version=cast(str, document["authority_version"]),
            record_id=cast(str, document["record_id"]),
            review_digest=cast(str, document["review_digest"]),
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            requirement_id=cast(str, document["requirement_id"]),
            requirement_wire_digest=cast(str, document["requirement_wire_digest"]),
            m2_review_status_observed=_require_enum(
                "m2_review_status_observed",
                document["m2_review_status_observed"],
                ReviewStatusV1,
            ),
            m2_resolution_state_observed=_require_enum(
                "m2_resolution_state_observed",
                document["m2_resolution_state_observed"],
                ResolutionStateV1,
            ),
            m2_reviewed_claim_digest=cast(str, document["m2_reviewed_claim_digest"]),
            decision=_require_enum(
                "decision", document["decision"], AdmissibilityDecisionV1
            ),
            reviewer_id=cast(str, document["reviewer_id"]),
        )
        if result.to_wire() != document:
            raise ValueError("source Requirement admissibility wire is not canonical")
        return result


def admissibility_claim_payload(
    record: SourceRequirementAdmissibilityV1,
) -> dict[str, JSONValue]:
    if not isinstance(record, SourceRequirementAdmissibilityV1):
        raise TypeError("record must be SourceRequirementAdmissibilityV1")
    return _claim_payload_values(
        authority_id=record.authority_id,
        authority_version=record.authority_version,
        m3_analysis_manifest_sha256=record.m3_analysis_manifest_sha256,
        requirement_id=record.requirement_id,
        requirement_wire_digest=record.requirement_wire_digest,
        m2_review_status_observed=record.m2_review_status_observed,
        m2_resolution_state_observed=record.m2_resolution_state_observed,
        m2_reviewed_claim_digest=record.m2_reviewed_claim_digest,
        decision=record.decision,
        reviewer_id=record.reviewer_id,
    )


def admissibility_review_digest_for(
    record: SourceRequirementAdmissibilityV1,
) -> str:
    return domain_digest(ADMISSIBILITY_DOMAIN, admissibility_claim_payload(record))


def admissibility_record_id_for(record: SourceRequirementAdmissibilityV1) -> str:
    return ADMISSIBILITY_PREFIX + admissibility_review_digest_for(record)


def active_admissibility_for(
    requirement: RequirementV1,
    records: Sequence[SourceRequirementAdmissibilityV1],
) -> bool:
    requirement = _require_requirement(requirement)
    if (
        requirement.review.status
        not in (
            ReviewStatusV1.PROPOSED,
            ReviewStatusV1.IN_REVIEW,
        )
        or requirement.resolution.state is not ResolutionStateV1.COMPLETE
    ):
        return False

    matching: list[SourceRequirementAdmissibilityV1] = []
    for record in records:
        if not isinstance(record, SourceRequirementAdmissibilityV1):
            raise TypeError(
                "records must contain SourceRequirementAdmissibilityV1 values"
            )
        if record.requirement_id == requirement.requirement_id:
            record.validate_against_requirement(requirement)
            matching.append(record)
    accepted = [
        record
        for record in matching
        if record.decision is AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING
    ]
    rejected = [
        record
        for record in matching
        if record.decision is AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING
    ]
    if accepted and rejected:
        raise ValueError("conflicting admissibility decisions")
    if len(accepted) > 1:
        raise ValueError("duplicate admissibility decisions")
    return len(accepted) == 1


__all__ = [
    "ADMISSIBILITY_DOMAIN",
    "ADMISSIBILITY_PREFIX",
    "ADMISSIBILITY_SCHEMA",
    "AdmissibilityDecisionV1",
    "SourceRequirementAdmissibilityV1",
    "active_admissibility_for",
    "admissibility_claim_payload",
    "admissibility_record_id_for",
    "admissibility_review_digest_for",
]
