"""Ranked worklist and bounded review-packet models for M6-03."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..inventory._common import (
    GROUP_ID,
    OPPORTUNITY_ID,
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
    REVIEW_QUESTIONS,
    PlanningNoiseV1,
    StoppingReasonV1,
)


@dataclass(frozen=True, slots=True)
class RankedWorklistEntryV1:
    rank: int
    opportunity_id: str
    candidate_group_id: str
    grouping_lens: GroupingLensV1
    distinct_oracle_count: int
    distinct_raw_text_count: int
    occurrence_count: int
    planning_noise: PlanningNoiseV1
    mechanical_overlap_cluster_id: str
    is_overlap_representative: bool
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-ranked-worklist-entry.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "rank",
        "opportunity_id",
        "candidate_group_id",
        "grouping_lens",
        "distinct_oracle_count",
        "distinct_raw_text_count",
        "occurrence_count",
        "planning_noise",
        "mechanical_overlap_cluster_id",
        "is_overlap_representative",
    }

    def __post_init__(self) -> None:
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError("rank must be a positive integer")
        if OPPORTUNITY_ID.fullmatch(self.opportunity_id) is None:
            raise ValueError("opportunity_id must have the m6opp_ form")
        if GROUP_ID.fullmatch(self.candidate_group_id) is None:
            raise ValueError("candidate_group_id must have the m6grp_ form")
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        nonnegative("distinct_oracle_count", self.distinct_oracle_count)
        nonnegative("distinct_raw_text_count", self.distinct_raw_text_count)
        nonnegative("occurrence_count", self.occurrence_count)
        object.__setattr__(
            self,
            "planning_noise",
            enum_value("planning_noise", self.planning_noise, PlanningNoiseV1),
        )
        text(
            "mechanical_overlap_cluster_id",
            self.mechanical_overlap_cluster_id,
        )
        if type(self.is_overlap_representative) is not bool:
            raise TypeError("is_overlap_representative must be a boolean")
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "rank": self.rank,
            "opportunity_id": self.opportunity_id,
            "candidate_group_id": self.candidate_group_id,
            "grouping_lens": self.grouping_lens.value,
            "distinct_oracle_count": self.distinct_oracle_count,
            "distinct_raw_text_count": self.distinct_raw_text_count,
            "occurrence_count": self.occurrence_count,
            "planning_noise": self.planning_noise.value,
            "mechanical_overlap_cluster_id": self.mechanical_overlap_cluster_id,
            "is_overlap_representative": self.is_overlap_representative,
        }

    @classmethod
    def from_wire(cls, value: object) -> RankedWorklistEntryV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "ranked worklist entry")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        if type(document["is_overlap_representative"]) is not bool:
            raise TypeError("is_overlap_representative must be a boolean")
        return cls(
            rank=cast(int, document["rank"]),
            opportunity_id=cast(str, document["opportunity_id"]),
            candidate_group_id=cast(str, document["candidate_group_id"]),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            distinct_oracle_count=cast(int, document["distinct_oracle_count"]),
            distinct_raw_text_count=cast(int, document["distinct_raw_text_count"]),
            occurrence_count=cast(int, document["occurrence_count"]),
            planning_noise=cast(PlanningNoiseV1, document["planning_noise"]),
            mechanical_overlap_cluster_id=cast(
                str, document["mechanical_overlap_cluster_id"]
            ),
            is_overlap_representative=cast(bool, document["is_overlap_representative"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class ReviewPacketEntryV1:
    selection_index: int
    opportunity_id: str
    candidate_group_id: str
    grouping_lens: GroupingLensV1
    group_key: str | None
    group_key_digest: str
    distinct_oracle_count: int
    occurrence_count: int
    member_surface_count: int
    distinct_raw_text_count: int
    marginal_oracle_count: int
    cumulative_oracle_count: int
    mechanical_overlap_cluster_id: str
    representative_surface_ids: tuple[str, ...]
    example_surfaces: tuple[dict[str, JSONValue], ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-review-packet-entry.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "selection_index",
        "opportunity_id",
        "candidate_group_id",
        "grouping_lens",
        "group_key",
        "group_key_digest",
        "distinct_oracle_count",
        "occurrence_count",
        "member_surface_count",
        "distinct_raw_text_count",
        "marginal_oracle_count",
        "cumulative_oracle_count",
        "mechanical_overlap_cluster_id",
        "representative_surface_ids",
        "example_surfaces",
    }

    def __post_init__(self) -> None:
        if type(self.selection_index) is not int or self.selection_index < 1:
            raise ValueError("selection_index must be a positive integer")
        if OPPORTUNITY_ID.fullmatch(self.opportunity_id) is None:
            raise ValueError("opportunity_id must have the m6opp_ form")
        if GROUP_ID.fullmatch(self.candidate_group_id) is None:
            raise ValueError("candidate_group_id must have the m6grp_ form")
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        group_key = self.group_key
        if group_key is not None:
            text("group_key", group_key, non_empty=False)
        digest("group_key_digest", self.group_key_digest)
        nonnegative("distinct_oracle_count", self.distinct_oracle_count)
        nonnegative("occurrence_count", self.occurrence_count)
        nonnegative("member_surface_count", self.member_surface_count)
        nonnegative("distinct_raw_text_count", self.distinct_raw_text_count)
        nonnegative("marginal_oracle_count", self.marginal_oracle_count)
        nonnegative("cumulative_oracle_count", self.cumulative_oracle_count)
        text(
            "mechanical_overlap_cluster_id",
            self.mechanical_overlap_cluster_id,
        )
        representatives = tuple(self.representative_surface_ids)
        if not representatives or len(representatives) > 3:
            raise ValueError("representative_surface_ids must contain 1-3 IDs")
        object.__setattr__(self, "representative_surface_ids", representatives)
        examples = tuple(self.example_surfaces)
        if any(not isinstance(item, dict) for item in examples):
            raise TypeError("example_surfaces must contain objects")
        object.__setattr__(self, "example_surfaces", examples)
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        group_key: JSONValue = self.group_key
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "selection_index": self.selection_index,
            "opportunity_id": self.opportunity_id,
            "candidate_group_id": self.candidate_group_id,
            "grouping_lens": self.grouping_lens.value,
            "group_key": group_key,
            "group_key_digest": self.group_key_digest,
            "distinct_oracle_count": self.distinct_oracle_count,
            "occurrence_count": self.occurrence_count,
            "member_surface_count": self.member_surface_count,
            "distinct_raw_text_count": self.distinct_raw_text_count,
            "marginal_oracle_count": self.marginal_oracle_count,
            "cumulative_oracle_count": self.cumulative_oracle_count,
            "mechanical_overlap_cluster_id": self.mechanical_overlap_cluster_id,
            "representative_surface_ids": list(self.representative_surface_ids),
            "example_surfaces": list(self.example_surfaces),
        }

    @classmethod
    def from_wire(cls, value: object) -> ReviewPacketEntryV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "review packet entry")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        if not isinstance(document["representative_surface_ids"], list):
            raise TypeError("representative_surface_ids must be an array")
        if not isinstance(document["example_surfaces"], list):
            raise TypeError("example_surfaces must be an array")
        raw_key = document["group_key"]
        if raw_key is not None and not isinstance(raw_key, str):
            raise TypeError("group_key must be a string or null")
        return cls(
            selection_index=cast(int, document["selection_index"]),
            opportunity_id=cast(str, document["opportunity_id"]),
            candidate_group_id=cast(str, document["candidate_group_id"]),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            group_key=cast(str | None, document["group_key"]),
            group_key_digest=cast(str, document["group_key_digest"]),
            distinct_oracle_count=cast(int, document["distinct_oracle_count"]),
            occurrence_count=cast(int, document["occurrence_count"]),
            member_surface_count=cast(int, document["member_surface_count"]),
            distinct_raw_text_count=cast(int, document["distinct_raw_text_count"]),
            marginal_oracle_count=cast(int, document["marginal_oracle_count"]),
            cumulative_oracle_count=cast(int, document["cumulative_oracle_count"]),
            mechanical_overlap_cluster_id=cast(
                str, document["mechanical_overlap_cluster_id"]
            ),
            representative_surface_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["representative_surface_ids"])
            ),
            example_surfaces=tuple(
                cast(dict[str, JSONValue], item)
                for item in cast(list[object], document["example_surfaces"])
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class ReviewPacketV1:
    ranking_policy_id: str
    ranking_policy_version: str
    assessment_policy_id: str
    assessment_policy_version: str
    review_budget: int
    selected_count: int
    stopping_reason: StoppingReasonV1
    oracle_union_count: int
    oracle_denominator_count: int
    marginal_coverage_sequence: tuple[int, ...]
    entries: tuple[ReviewPacketEntryV1, ...]
    review_questions: tuple[str, ...]
    source_lock_digest: str
    m1_manifest_sha256: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    m6_02_manifest_sha256: str
    m6_02_selected_identity_set_digest: str
    m4_active_family_ids: tuple[str, ...]
    non_authority_statements: tuple[str, ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-review-packet.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "ranking_policy_id",
        "ranking_policy_version",
        "assessment_policy_id",
        "assessment_policy_version",
        "review_budget",
        "selected_count",
        "stopping_reason",
        "oracle_union_count",
        "oracle_denominator_count",
        "marginal_coverage_sequence",
        "entries",
        "review_questions",
        "source_lock_digest",
        "m1_manifest_sha256",
        "m3_manifest_sha256",
        "parent_m4_manifest_sha256",
        "parent_census_release_id",
        "m6_02_manifest_sha256",
        "m6_02_selected_identity_set_digest",
        "m4_active_family_ids",
        "non_authority_statements",
    }

    def __post_init__(self) -> None:
        text("ranking_policy_id", self.ranking_policy_id)
        text("ranking_policy_version", self.ranking_policy_version)
        text("assessment_policy_id", self.assessment_policy_id)
        text("assessment_policy_version", self.assessment_policy_version)
        nonnegative("review_budget", self.review_budget)
        entries = tuple(self.entries)
        if any(not isinstance(item, ReviewPacketEntryV1) for item in entries):
            raise TypeError("entries must contain ReviewPacketEntryV1 values")
        if nonnegative("selected_count", self.selected_count) != len(entries):
            raise ValueError("selected_count does not match entries")
        if tuple(item.selection_index for item in entries) != tuple(
            range(1, len(entries) + 1)
        ):
            raise ValueError("entries must carry dense 1-based selection_index")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self,
            "stopping_reason",
            enum_value("stopping_reason", self.stopping_reason, StoppingReasonV1),
        )
        nonnegative("oracle_union_count", self.oracle_union_count)
        nonnegative("oracle_denominator_count", self.oracle_denominator_count)
        sequence = tuple(self.marginal_coverage_sequence)
        if any(type(item) is not int or item < 0 for item in sequence):
            raise ValueError("marginal_coverage_sequence must hold non-negatives")
        if sequence != tuple(item.marginal_oracle_count for item in entries):
            raise ValueError("marginal_coverage_sequence does not match entries")
        object.__setattr__(self, "marginal_coverage_sequence", sequence)
        questions = tuple(self.review_questions)
        if tuple(questions) != REVIEW_QUESTIONS:
            raise ValueError("review_questions must equal the frozen question set")
        object.__setattr__(self, "review_questions", questions)
        digest("source_lock_digest", self.source_lock_digest)
        digest("m1_manifest_sha256", self.m1_manifest_sha256)
        digest("m3_manifest_sha256", self.m3_manifest_sha256)
        digest("parent_m4_manifest_sha256", self.parent_m4_manifest_sha256)
        text("parent_census_release_id", self.parent_census_release_id)
        digest("m6_02_manifest_sha256", self.m6_02_manifest_sha256)
        digest(
            "m6_02_selected_identity_set_digest",
            self.m6_02_selected_identity_set_digest,
        )
        families = tuple(self.m4_active_family_ids)
        if families != tuple(sorted(set(families))):
            raise ValueError("m4_active_family_ids must be sorted and unique")
        object.__setattr__(self, "m4_active_family_ids", families)
        statements = tuple(self.non_authority_statements)
        object.__setattr__(self, "non_authority_statements", statements)
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "ranking_policy_id": self.ranking_policy_id,
            "ranking_policy_version": self.ranking_policy_version,
            "assessment_policy_id": self.assessment_policy_id,
            "assessment_policy_version": self.assessment_policy_version,
            "review_budget": self.review_budget,
            "selected_count": self.selected_count,
            "stopping_reason": self.stopping_reason.value,
            "oracle_union_count": self.oracle_union_count,
            "oracle_denominator_count": self.oracle_denominator_count,
            "marginal_coverage_sequence": list(self.marginal_coverage_sequence),
            "entries": [item.to_wire() for item in self.entries],
            "review_questions": list(self.review_questions),
            "source_lock_digest": self.source_lock_digest,
            "m1_manifest_sha256": self.m1_manifest_sha256,
            "m3_manifest_sha256": self.m3_manifest_sha256,
            "parent_m4_manifest_sha256": self.parent_m4_manifest_sha256,
            "parent_census_release_id": self.parent_census_release_id,
            "m6_02_manifest_sha256": self.m6_02_manifest_sha256,
            "m6_02_selected_identity_set_digest": (
                self.m6_02_selected_identity_set_digest
            ),
            "m4_active_family_ids": list(self.m4_active_family_ids),
            "non_authority_statements": list(self.non_authority_statements),
        }

    @classmethod
    def from_wire(cls, value: object) -> ReviewPacketV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "review packet")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        for field in (
            "marginal_coverage_sequence",
            "entries",
            "review_questions",
            "m4_active_family_ids",
            "non_authority_statements",
        ):
            if not isinstance(document[field], list):
                raise TypeError(f"{field} must be an array")
        return cls(
            ranking_policy_id=cast(str, document["ranking_policy_id"]),
            ranking_policy_version=cast(str, document["ranking_policy_version"]),
            assessment_policy_id=cast(str, document["assessment_policy_id"]),
            assessment_policy_version=cast(str, document["assessment_policy_version"]),
            review_budget=cast(int, document["review_budget"]),
            selected_count=cast(int, document["selected_count"]),
            stopping_reason=cast(StoppingReasonV1, document["stopping_reason"]),
            oracle_union_count=cast(int, document["oracle_union_count"]),
            oracle_denominator_count=cast(int, document["oracle_denominator_count"]),
            marginal_coverage_sequence=tuple(
                cast(int, item)
                for item in cast(list[object], document["marginal_coverage_sequence"])
            ),
            entries=tuple(
                ReviewPacketEntryV1.from_wire(item)
                for item in cast(list[object], document["entries"])
            ),
            review_questions=tuple(
                cast(str, item)
                for item in cast(list[object], document["review_questions"])
            ),
            source_lock_digest=cast(str, document["source_lock_digest"]),
            m1_manifest_sha256=cast(str, document["m1_manifest_sha256"]),
            m3_manifest_sha256=cast(str, document["m3_manifest_sha256"]),
            parent_m4_manifest_sha256=cast(str, document["parent_m4_manifest_sha256"]),
            parent_census_release_id=cast(str, document["parent_census_release_id"]),
            m6_02_manifest_sha256=cast(str, document["m6_02_manifest_sha256"]),
            m6_02_selected_identity_set_digest=cast(
                str, document["m6_02_selected_identity_set_digest"]
            ),
            m4_active_family_ids=tuple(
                cast(str, item)
                for item in cast(list[object], document["m4_active_family_ids"])
            ),
            non_authority_statements=tuple(
                cast(str, item)
                for item in cast(list[object], document["non_authority_statements"])
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = [
    "RankedWorklistEntryV1",
    "ReviewPacketEntryV1",
    "ReviewPacketV1",
]
