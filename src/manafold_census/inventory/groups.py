"""Candidate-group, Opportunity, and worklist models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ._common import (
    AUTHORITY_SCOPE,
    GROUP_ID,
    OPPORTUNITY_ID,
    GroupingLensV1,
    PlanningStatusV1,
    RecurrenceStatusV1,
    authority,
    digest,
    enum_value,
    nonnegative,
    object_with_keys,
    optional_text,
    text,
)
from .surface import StructuralSummaryV1, SurfaceMemberV1


def member_sort_key(
    item: SurfaceMemberV1,
) -> tuple[str, str, int, int, str]:
    return (
        item.oracle_id,
        item.source_card_id,
        item.face_index if item.face_index is not None else -1,
        item.line_index if item.line_index is not None else -1,
        item.surface_id,
    )


@dataclass(frozen=True, slots=True)
class CandidateGroupV1:
    group_id: str
    grouping_lens: GroupingLensV1
    grouping_policy_id: str
    grouping_policy_version: str
    group_key: str | None
    group_key_digest: str
    member_count: int
    surface_occurrence_count: int
    distinct_oracle_identity_count: int
    recurrence_status: RecurrenceStatusV1
    members: tuple[SurfaceMemberV1, ...]
    representative_surface_ids: tuple[str, ...]
    structural_summary: StructuralSummaryV1
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-candidate-group.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "group_id",
        "grouping_lens",
        "grouping_policy_id",
        "grouping_policy_version",
        "group_key",
        "group_key_digest",
        "member_count",
        "surface_occurrence_count",
        "distinct_oracle_identity_count",
        "recurrence_status",
        "members",
        "representative_surface_ids",
        "structural_summary",
    }

    def __post_init__(self) -> None:
        if GROUP_ID.fullmatch(self.group_id) is None:
            raise ValueError("group_id must have the m6grp_ SHA-256 form")
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        text("grouping_policy_id", self.grouping_policy_id)
        text("grouping_policy_version", self.grouping_policy_version)
        optional_text("group_key", self.group_key)
        digest("group_key_digest", self.group_key_digest)
        members = tuple(self.members)
        if any(not isinstance(item, SurfaceMemberV1) for item in members):
            raise TypeError("members must contain SurfaceMemberV1 values")
        if members != tuple(sorted(members, key=member_sort_key)):
            raise ValueError("members must be canonically ordered")
        object.__setattr__(self, "members", members)
        member_count = nonnegative("member_count", self.member_count)
        occurrence_count = nonnegative(
            "surface_occurrence_count", self.surface_occurrence_count
        )
        if member_count != len(members) or occurrence_count != len(members):
            raise ValueError("member and occurrence counts must equal members")
        identity_count = len({item.oracle_id for item in members})
        if (
            nonnegative(
                "distinct_oracle_identity_count",
                self.distinct_oracle_identity_count,
            )
            != identity_count
        ):
            raise ValueError("distinct Oracle count does not match members")
        recurrence = enum_value(
            "recurrence_status", self.recurrence_status, RecurrenceStatusV1
        )
        expected = (
            RecurrenceStatusV1.RECURRING
            if identity_count >= 2
            else RecurrenceStatusV1.SINGLETON
        )
        if recurrence is not expected:
            raise ValueError("recurrence_status does not match members")
        object.__setattr__(self, "recurrence_status", recurrence)
        representatives = tuple(self.representative_surface_ids)
        if not representatives or len(representatives) > 3:
            raise ValueError("representative_surface_ids must contain one to three IDs")
        member_ids = {item.surface_id for item in members}
        if (
            len(set(representatives)) != len(representatives)
            or not set(representatives) <= member_ids
        ):
            raise ValueError("representative_surface_ids must reference members")
        object.__setattr__(self, "representative_surface_ids", representatives)
        if not isinstance(self.structural_summary, StructuralSummaryV1):
            raise TypeError("structural_summary must be StructuralSummaryV1")
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "group_id": self.group_id,
            "grouping_lens": self.grouping_lens.value,
            "grouping_policy_id": self.grouping_policy_id,
            "grouping_policy_version": self.grouping_policy_version,
            "group_key": self.group_key,
            "group_key_digest": self.group_key_digest,
            "member_count": self.member_count,
            "surface_occurrence_count": self.surface_occurrence_count,
            "distinct_oracle_identity_count": self.distinct_oracle_identity_count,
            "recurrence_status": self.recurrence_status.value,
            "members": [item.to_wire() for item in self.members],
            "representative_surface_ids": list(self.representative_surface_ids),
            "structural_summary": self.structural_summary.to_wire(),
        }

    @classmethod
    def from_wire(cls, value: object) -> CandidateGroupV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "candidate group")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_members = document["members"]
        raw_representatives = document["representative_surface_ids"]
        if not isinstance(raw_members, list) or not isinstance(
            raw_representatives, list
        ):
            raise TypeError("group members and representatives must be arrays")
        return cls(
            group_id=cast(str, document["group_id"]),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            grouping_policy_id=cast(str, document["grouping_policy_id"]),
            grouping_policy_version=cast(str, document["grouping_policy_version"]),
            group_key=cast(str | None, document["group_key"]),
            group_key_digest=cast(str, document["group_key_digest"]),
            member_count=cast(int, document["member_count"]),
            surface_occurrence_count=cast(int, document["surface_occurrence_count"]),
            distinct_oracle_identity_count=cast(
                int, document["distinct_oracle_identity_count"]
            ),
            recurrence_status=cast(RecurrenceStatusV1, document["recurrence_status"]),
            members=tuple(SurfaceMemberV1.from_wire(item) for item in raw_members),
            representative_surface_ids=tuple(
                cast(str, item) for item in raw_representatives
            ),
            structural_summary=StructuralSummaryV1.from_wire(
                document["structural_summary"]
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class CapabilityOpportunityV1:
    opportunity_id: str
    candidate_group_ids: tuple[str, ...]
    grouping_lens: GroupingLensV1
    grouping_policy_id: str
    grouping_policy_version: str
    planning_status: PlanningStatusV1
    surface_occurrence_count: int
    distinct_oracle_identity_count: int
    representative_surface_ids: tuple[str, ...]
    structural_summary: StructuralSummaryV1
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-capability-opportunity.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "opportunity_id",
        "candidate_group_ids",
        "grouping_lens",
        "grouping_policy_id",
        "grouping_policy_version",
        "planning_status",
        "surface_occurrence_count",
        "distinct_oracle_identity_count",
        "representative_surface_ids",
        "structural_summary",
    }

    def __post_init__(self) -> None:
        if OPPORTUNITY_ID.fullmatch(self.opportunity_id) is None:
            raise ValueError("opportunity_id must have the m6opp_ SHA-256 form")
        group_ids = tuple(self.candidate_group_ids)
        if not group_ids or group_ids != tuple(sorted(set(group_ids))):
            raise ValueError("candidate_group_ids must be sorted and unique")
        if any(GROUP_ID.fullmatch(item) is None for item in group_ids):
            raise ValueError("candidate_group_ids must have the m6grp_ form")
        object.__setattr__(self, "candidate_group_ids", group_ids)
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        text("grouping_policy_id", self.grouping_policy_id)
        text("grouping_policy_version", self.grouping_policy_version)
        object.__setattr__(
            self,
            "planning_status",
            enum_value("planning_status", self.planning_status, PlanningStatusV1),
        )
        nonnegative("surface_occurrence_count", self.surface_occurrence_count)
        identity_count = nonnegative(
            "distinct_oracle_identity_count",
            self.distinct_oracle_identity_count,
        )
        if identity_count < 2:
            raise ValueError("Opportunities require recurring groups")
        representatives = tuple(self.representative_surface_ids)
        if not representatives or len(set(representatives)) != len(representatives):
            raise ValueError("representative_surface_ids must be unique and non-empty")
        object.__setattr__(self, "representative_surface_ids", representatives)
        if not isinstance(self.structural_summary, StructuralSummaryV1):
            raise TypeError("structural_summary must be StructuralSummaryV1")
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "opportunity_id": self.opportunity_id,
            "candidate_group_ids": list(self.candidate_group_ids),
            "grouping_lens": self.grouping_lens.value,
            "grouping_policy_id": self.grouping_policy_id,
            "grouping_policy_version": self.grouping_policy_version,
            "planning_status": self.planning_status.value,
            "surface_occurrence_count": self.surface_occurrence_count,
            "distinct_oracle_identity_count": self.distinct_oracle_identity_count,
            "representative_surface_ids": list(self.representative_surface_ids),
            "structural_summary": self.structural_summary.to_wire(),
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityOpportunityV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "Capability Opportunity")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_groups = document["candidate_group_ids"]
        raw_representatives = document["representative_surface_ids"]
        if not isinstance(raw_groups, list) or not isinstance(
            raw_representatives, list
        ):
            raise TypeError("Opportunity arrays have the wrong type")
        return cls(
            opportunity_id=cast(str, document["opportunity_id"]),
            candidate_group_ids=tuple(cast(str, item) for item in raw_groups),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            grouping_policy_id=cast(str, document["grouping_policy_id"]),
            grouping_policy_version=cast(str, document["grouping_policy_version"]),
            planning_status=cast(PlanningStatusV1, document["planning_status"]),
            surface_occurrence_count=cast(int, document["surface_occurrence_count"]),
            distinct_oracle_identity_count=cast(
                int, document["distinct_oracle_identity_count"]
            ),
            representative_surface_ids=tuple(
                cast(str, item) for item in raw_representatives
            ),
            structural_summary=StructuralSummaryV1.from_wire(
                document["structural_summary"]
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


@dataclass(frozen=True, slots=True)
class WorklistEntryV1:
    group_id: str
    grouping_lens: GroupingLensV1
    distinct_oracle_identity_count: int
    surface_occurrence_count: int
    recurrence_status: RecurrenceStatusV1
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-worklist-entry.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "group_id",
        "grouping_lens",
        "distinct_oracle_identity_count",
        "surface_occurrence_count",
        "recurrence_status",
    }

    def __post_init__(self) -> None:
        if GROUP_ID.fullmatch(self.group_id) is None:
            raise ValueError("group_id must have the m6grp_ SHA-256 form")
        object.__setattr__(
            self,
            "grouping_lens",
            enum_value("grouping_lens", self.grouping_lens, GroupingLensV1),
        )
        object.__setattr__(
            self,
            "recurrence_status",
            enum_value("recurrence_status", self.recurrence_status, RecurrenceStatusV1),
        )
        nonnegative(
            "distinct_oracle_identity_count",
            self.distinct_oracle_identity_count,
        )
        nonnegative("surface_occurrence_count", self.surface_occurrence_count)
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "group_id": self.group_id,
            "grouping_lens": self.grouping_lens.value,
            "distinct_oracle_identity_count": self.distinct_oracle_identity_count,
            "surface_occurrence_count": self.surface_occurrence_count,
            "recurrence_status": self.recurrence_status.value,
        }

    @classmethod
    def from_wire(cls, value: object) -> WorklistEntryV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "worklist entry")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        return cls(
            group_id=cast(str, document["group_id"]),
            grouping_lens=cast(GroupingLensV1, document["grouping_lens"]),
            distinct_oracle_identity_count=cast(
                int, document["distinct_oracle_identity_count"]
            ),
            surface_occurrence_count=cast(int, document["surface_occurrence_count"]),
            recurrence_status=cast(RecurrenceStatusV1, document["recurrence_status"]),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = [
    "CandidateGroupV1",
    "CapabilityOpportunityV1",
    "WorklistEntryV1",
    "member_sort_key",
]
