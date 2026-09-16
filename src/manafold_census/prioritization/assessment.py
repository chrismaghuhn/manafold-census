"""Assessment and mechanical-overlap models for M6-03 planning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..inventory._common import (
    GROUP_ID,
    OPPORTUNITY_ID,
    SURFACE_ID,
    GroupingLensV1,
    authority,
    digest,
    enum_value,
    nonnegative,
    object_with_keys,
    text,
)
from ._common import (
    AUTHORITY_SCOPE,
    UNASSESSED,
    PlanningNoiseV1,
)

_ASSESSMENT_ID = re.compile(r"^m6ass_[0-9a-f]{64}$")
_CLUSTER_ID = re.compile(r"^m6ovl_[0-9a-f]{64}$")

_SEMANTIC_FIELDS: tuple[str, ...] = (
    "semantic_impact",
    "semantic_uncertainty",
    "existing_capability_reuse",
    "new_capability_family",
    "contract_fit",
    "m7_fit",
    "semantic_disposition",
)


def _sorted_unique(field: str, values: tuple[str, ...]) -> tuple[str, ...]:
    result = tuple(values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field} must contain unique values")
    if result != tuple(sorted(result)):
        raise ValueError(f"{field} must be sorted")
    return result


@dataclass(frozen=True, slots=True)
class OpportunityAssessmentV1:
    assessment_id: str
    opportunity_id: str
    candidate_group_id: str
    grouping_lens: GroupingLensV1
    assessment_policy_id: str
    assessment_policy_version: str
    distinct_oracle_count: int
    occurrence_count: int
    member_surface_count: int
    distinct_raw_text_count: int
    planning_noise: PlanningNoiseV1
    member_surface_set_digest: str
    member_surface_ids: tuple[str, ...]
    member_oracle_ids: tuple[str, ...]
    representative_surface_ids: tuple[str, ...]
    semantic_impact: str = UNASSESSED
    semantic_uncertainty: str = UNASSESSED
    existing_capability_reuse: str = UNASSESSED
    new_capability_family: str = UNASSESSED
    contract_fit: str = UNASSESSED
    m7_fit: str = UNASSESSED
    semantic_disposition: str = UNASSESSED
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-opportunity-assessment.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "assessment_id",
        "opportunity_id",
        "candidate_group_id",
        "grouping_lens",
        "assessment_policy_id",
        "assessment_policy_version",
        "distinct_oracle_count",
        "occurrence_count",
        "member_surface_count",
        "distinct_raw_text_count",
        "planning_noise",
        "member_surface_set_digest",
        "member_surface_ids",
        "member_oracle_ids",
        "representative_surface_ids",
        "semantic_impact",
        "semantic_uncertainty",
        "existing_capability_reuse",
        "new_capability_family",
        "contract_fit",
        "m7_fit",
        "semantic_disposition",
    }

    def __post_init__(self) -> None:
        if _ASSESSMENT_ID.fullmatch(self.assessment_id) is None:
            raise ValueError("assessment_id must have the m6ass_ SHA-256 form")
        if OPPORTUNITY_ID.fullmatch(self.opportunity_id) is None:
            raise ValueError("opportunity_id must have the m6opp_ form")
        if GROUP_ID.fullmatch(self.candidate_group_id) is None:
            raise ValueError("candidate_group_id must have the m6grp_ form")
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        text("assessment_policy_id", self.assessment_policy_id)
        text("assessment_policy_version", self.assessment_policy_version)
        nonnegative("distinct_oracle_count", self.distinct_oracle_count)
        nonnegative("occurrence_count", self.occurrence_count)
        nonnegative("member_surface_count", self.member_surface_count)
        nonnegative("distinct_raw_text_count", self.distinct_raw_text_count)
        object.__setattr__(
            self,
            "planning_noise",
            enum_value("planning_noise", self.planning_noise, PlanningNoiseV1),
        )
        digest("member_surface_set_digest", self.member_surface_set_digest)
        surface_ids = _sorted_unique(
            "member_surface_ids", tuple(self.member_surface_ids)
        )
        if any(SURFACE_ID.fullmatch(item) is None for item in surface_ids):
            raise ValueError("member_surface_ids must have the m6surf_ form")
        object.__setattr__(self, "member_surface_ids", surface_ids)
        oracle_ids = _sorted_unique("member_oracle_ids", tuple(self.member_oracle_ids))
        object.__setattr__(self, "member_oracle_ids", oracle_ids)
        if self.member_surface_count != len(surface_ids):
            raise ValueError("member_surface_count does not match surface IDs")
        if self.distinct_oracle_count != len(oracle_ids):
            raise ValueError("distinct_oracle_count does not match Oracle IDs")
        if self.occurrence_count != len(surface_ids):
            raise ValueError("occurrence_count does not match surface IDs")
        representatives = tuple(self.representative_surface_ids)
        if not representatives or len(representatives) > 3:
            raise ValueError("representative_surface_ids must contain 1-3 IDs")
        if len(set(representatives)) != len(representatives):
            raise ValueError("representative_surface_ids must be unique")
        if not set(representatives) <= set(surface_ids):
            raise ValueError("representative_surface_ids must reference members")
        if representatives != tuple(sorted(representatives)):
            raise ValueError("representative_surface_ids must be sorted")
        object.__setattr__(self, "representative_surface_ids", representatives)
        for field in _SEMANTIC_FIELDS:
            value = getattr(self, field)
            if value != UNASSESSED:
                raise ValueError(f"{field} must remain UNASSESSED")
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "assessment_id": self.assessment_id,
            "opportunity_id": self.opportunity_id,
            "candidate_group_id": self.candidate_group_id,
            "grouping_lens": self.grouping_lens.value,
            "assessment_policy_id": self.assessment_policy_id,
            "assessment_policy_version": self.assessment_policy_version,
            "distinct_oracle_count": self.distinct_oracle_count,
            "occurrence_count": self.occurrence_count,
            "member_surface_count": self.member_surface_count,
            "distinct_raw_text_count": self.distinct_raw_text_count,
            "planning_noise": self.planning_noise.value,
            "member_surface_set_digest": self.member_surface_set_digest,
            "member_surface_ids": list(self.member_surface_ids),
            "member_oracle_ids": list(self.member_oracle_ids),
            "representative_surface_ids": list(self.representative_surface_ids),
            "semantic_impact": self.semantic_impact,
            "semantic_uncertainty": self.semantic_uncertainty,
            "existing_capability_reuse": self.existing_capability_reuse,
            "new_capability_family": self.new_capability_family,
            "contract_fit": self.contract_fit,
            "m7_fit": self.m7_fit,
            "semantic_disposition": self.semantic_disposition,
        }

    @classmethod
    def from_wire(cls, value: object) -> OpportunityAssessmentV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "opportunity assessment")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        for field in (
            "member_surface_ids",
            "member_oracle_ids",
            "representative_surface_ids",
        ):
            if not isinstance(document[field], list):
                raise TypeError(f"{field} must be an array")
        return cls(
            assessment_id=cast(str, document["assessment_id"]),
            opportunity_id=cast(str, document["opportunity_id"]),
            candidate_group_id=cast(str, document["candidate_group_id"]),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            assessment_policy_id=cast(str, document["assessment_policy_id"]),
            assessment_policy_version=cast(str, document["assessment_policy_version"]),
            distinct_oracle_count=cast(int, document["distinct_oracle_count"]),
            occurrence_count=cast(int, document["occurrence_count"]),
            member_surface_count=cast(int, document["member_surface_count"]),
            distinct_raw_text_count=cast(int, document["distinct_raw_text_count"]),
            planning_noise=cast(PlanningNoiseV1, document["planning_noise"]),
            member_surface_set_digest=cast(str, document["member_surface_set_digest"]),
            member_surface_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["member_surface_ids"])
            ),
            member_oracle_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["member_oracle_ids"])
            ),
            representative_surface_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["representative_surface_ids"])
            ),
            semantic_impact=cast(str, document["semantic_impact"]),
            semantic_uncertainty=cast(str, document["semantic_uncertainty"]),
            existing_capability_reuse=cast(str, document["existing_capability_reuse"]),
            new_capability_family=cast(str, document["new_capability_family"]),
            contract_fit=cast(str, document["contract_fit"]),
            m7_fit=cast(str, document["m7_fit"]),
            semantic_disposition=cast(str, document["semantic_disposition"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class MechanicalOverlapClusterV1:
    cluster_id: str
    member_surface_set_digest: str
    member_surface_ids: tuple[str, ...]
    member_opportunity_ids: tuple[str, ...]
    representative_opportunity_id: str
    member_count: int
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-mechanical-overlap-cluster.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "cluster_id",
        "member_surface_set_digest",
        "member_surface_ids",
        "member_opportunity_ids",
        "representative_opportunity_id",
        "member_count",
    }

    def __post_init__(self) -> None:
        if _CLUSTER_ID.fullmatch(self.cluster_id) is None:
            raise ValueError("cluster_id must have the m6ovl_ SHA-256 form")
        digest("member_surface_set_digest", self.member_surface_set_digest)
        surface_ids = _sorted_unique(
            "member_surface_ids", tuple(self.member_surface_ids)
        )
        if any(SURFACE_ID.fullmatch(item) is None for item in surface_ids):
            raise ValueError("member_surface_ids must have the m6surf_ form")
        object.__setattr__(self, "member_surface_ids", surface_ids)
        opportunity_ids = _sorted_unique(
            "member_opportunity_ids", tuple(self.member_opportunity_ids)
        )
        if any(OPPORTUNITY_ID.fullmatch(item) is None for item in opportunity_ids):
            raise ValueError("member_opportunity_ids must have the m6opp_ form")
        object.__setattr__(self, "member_opportunity_ids", opportunity_ids)
        text("representative_opportunity_id", self.representative_opportunity_id)
        if self.representative_opportunity_id not in set(opportunity_ids):
            raise ValueError("representative must be a cluster member")
        if nonnegative("member_count", self.member_count) != len(opportunity_ids):
            raise ValueError("member_count does not match members")
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "cluster_id": self.cluster_id,
            "member_surface_set_digest": self.member_surface_set_digest,
            "member_surface_ids": list(self.member_surface_ids),
            "member_opportunity_ids": list(self.member_opportunity_ids),
            "representative_opportunity_id": self.representative_opportunity_id,
            "member_count": self.member_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> MechanicalOverlapClusterV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "overlap cluster")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        for field in ("member_surface_ids", "member_opportunity_ids"):
            if not isinstance(document[field], list):
                raise TypeError(f"{field} must be an array")
        return cls(
            cluster_id=cast(str, document["cluster_id"]),
            member_surface_set_digest=cast(str, document["member_surface_set_digest"]),
            member_surface_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["member_surface_ids"])
            ),
            member_opportunity_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["member_opportunity_ids"])
            ),
            representative_opportunity_id=cast(
                str, document["representative_opportunity_id"]
            ),
            member_count=cast(int, document["member_count"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = [
    "MechanicalOverlapClusterV1",
    "OpportunityAssessmentV1",
]
