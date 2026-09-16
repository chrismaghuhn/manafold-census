"""Compact non-authoritative M6-03 prioritization report model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..inventory._common import (
    authority,
    census_release_id,
    digest,
    enum_value,
    nonnegative,
    object_with_keys,
    pair_wire,
    pairs,
    text,
)
from ._common import AUTHORITY_SCOPE, StoppingReasonV1


@dataclass(frozen=True, slots=True)
class PrioritizationReportV1:
    source_lock_digest: str
    m1_manifest_sha256: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    m6_02_manifest_sha256: str
    m6_02_selected_identity_set_digest: str
    assessment_policy_id: str
    assessment_policy_version: str
    ranking_policy_id: str
    ranking_policy_version: str
    input_opportunity_count: int
    non_noise_opportunity_count: int
    planning_noise_opportunity_count: int
    mechanical_overlap_cluster_count: int
    full_ranked_worklist_count: int
    review_packet_limit: int
    review_packet_count: int
    review_packet_oracle_union_count: int
    review_packet_oracle_denominator_count: int
    stopping_reason: StoppingReasonV1
    marginal_coverage_sequence: tuple[int, ...]
    noise_by_class: tuple[tuple[str, int], ...]
    top_review_entries: tuple[dict[str, JSONValue], ...]
    notes: tuple[str, ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-prioritization-report.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "source_lock_digest",
        "m1_manifest_sha256",
        "m3_manifest_sha256",
        "parent_m4_manifest_sha256",
        "parent_census_release_id",
        "m6_02_manifest_sha256",
        "m6_02_selected_identity_set_digest",
        "assessment_policy_id",
        "assessment_policy_version",
        "ranking_policy_id",
        "ranking_policy_version",
        "input_opportunity_count",
        "non_noise_opportunity_count",
        "planning_noise_opportunity_count",
        "mechanical_overlap_cluster_count",
        "full_ranked_worklist_count",
        "review_packet_limit",
        "review_packet_count",
        "review_packet_oracle_union_count",
        "review_packet_oracle_denominator_count",
        "stopping_reason",
        "marginal_coverage_sequence",
        "noise_by_class",
        "top_review_entries",
        "notes",
    }

    def __post_init__(self) -> None:
        digest("source_lock_digest", self.source_lock_digest)
        digest("m1_manifest_sha256", self.m1_manifest_sha256)
        digest("m3_manifest_sha256", self.m3_manifest_sha256)
        digest("parent_m4_manifest_sha256", self.parent_m4_manifest_sha256)
        census_release_id("parent_census_release_id", self.parent_census_release_id)
        digest("m6_02_manifest_sha256", self.m6_02_manifest_sha256)
        digest(
            "m6_02_selected_identity_set_digest",
            self.m6_02_selected_identity_set_digest,
        )
        text("assessment_policy_id", self.assessment_policy_id)
        text("assessment_policy_version", self.assessment_policy_version)
        text("ranking_policy_id", self.ranking_policy_id)
        text("ranking_policy_version", self.ranking_policy_version)
        for field in (
            "input_opportunity_count",
            "non_noise_opportunity_count",
            "planning_noise_opportunity_count",
            "mechanical_overlap_cluster_count",
            "full_ranked_worklist_count",
            "review_packet_limit",
            "review_packet_count",
            "review_packet_oracle_union_count",
            "review_packet_oracle_denominator_count",
        ):
            nonnegative(field, getattr(self, field))
        if self.input_opportunity_count != (
            self.non_noise_opportunity_count + self.planning_noise_opportunity_count
        ):
            raise ValueError("noise partition does not sum to inputs")
        if self.review_packet_count > self.review_packet_limit:
            raise ValueError("review packet exceeds its planning budget")
        object.__setattr__(
            self,
            "stopping_reason",
            enum_value("stopping_reason", self.stopping_reason, StoppingReasonV1),
        )
        sequence = tuple(self.marginal_coverage_sequence)
        if any(type(item) is not int or item < 0 for item in sequence):
            raise ValueError("marginal_coverage_sequence holds non-negatives")
        object.__setattr__(self, "marginal_coverage_sequence", sequence)
        object.__setattr__(self, "noise_by_class", tuple(self.noise_by_class))
        entries = tuple(self.top_review_entries)
        if any(not isinstance(item, dict) for item in entries):
            raise TypeError("top_review_entries must contain objects")
        object.__setattr__(self, "top_review_entries", entries)
        object.__setattr__(
            self,
            "notes",
            tuple(text("notes[]", item, non_empty=False) for item in self.notes),
        )
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "source_lock_digest": self.source_lock_digest,
            "m1_manifest_sha256": self.m1_manifest_sha256,
            "m3_manifest_sha256": self.m3_manifest_sha256,
            "parent_m4_manifest_sha256": self.parent_m4_manifest_sha256,
            "parent_census_release_id": self.parent_census_release_id,
            "m6_02_manifest_sha256": self.m6_02_manifest_sha256,
            "m6_02_selected_identity_set_digest": (
                self.m6_02_selected_identity_set_digest
            ),
            "assessment_policy_id": self.assessment_policy_id,
            "assessment_policy_version": self.assessment_policy_version,
            "ranking_policy_id": self.ranking_policy_id,
            "ranking_policy_version": self.ranking_policy_version,
            "input_opportunity_count": self.input_opportunity_count,
            "non_noise_opportunity_count": self.non_noise_opportunity_count,
            "planning_noise_opportunity_count": (self.planning_noise_opportunity_count),
            "mechanical_overlap_cluster_count": (self.mechanical_overlap_cluster_count),
            "full_ranked_worklist_count": self.full_ranked_worklist_count,
            "review_packet_limit": self.review_packet_limit,
            "review_packet_count": self.review_packet_count,
            "review_packet_oracle_union_count": (self.review_packet_oracle_union_count),
            "review_packet_oracle_denominator_count": (
                self.review_packet_oracle_denominator_count
            ),
            "stopping_reason": self.stopping_reason.value,
            "marginal_coverage_sequence": list(self.marginal_coverage_sequence),
            "noise_by_class": pair_wire(self.noise_by_class),
            "top_review_entries": list(self.top_review_entries),
            "notes": list(self.notes),
        }

    @classmethod
    def from_wire(cls, value: object) -> PrioritizationReportV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "prioritization report")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        for field in ("marginal_coverage_sequence", "top_review_entries", "notes"):
            if not isinstance(document[field], list):
                raise TypeError(f"{field} must be an array")
        return cls(
            source_lock_digest=cast(str, document["source_lock_digest"]),
            m1_manifest_sha256=cast(str, document["m1_manifest_sha256"]),
            m3_manifest_sha256=cast(str, document["m3_manifest_sha256"]),
            parent_m4_manifest_sha256=cast(str, document["parent_m4_manifest_sha256"]),
            parent_census_release_id=cast(str, document["parent_census_release_id"]),
            m6_02_manifest_sha256=cast(str, document["m6_02_manifest_sha256"]),
            m6_02_selected_identity_set_digest=cast(
                str, document["m6_02_selected_identity_set_digest"]
            ),
            assessment_policy_id=cast(str, document["assessment_policy_id"]),
            assessment_policy_version=cast(str, document["assessment_policy_version"]),
            ranking_policy_id=cast(str, document["ranking_policy_id"]),
            ranking_policy_version=cast(str, document["ranking_policy_version"]),
            input_opportunity_count=cast(int, document["input_opportunity_count"]),
            non_noise_opportunity_count=cast(
                int, document["non_noise_opportunity_count"]
            ),
            planning_noise_opportunity_count=cast(
                int, document["planning_noise_opportunity_count"]
            ),
            mechanical_overlap_cluster_count=cast(
                int, document["mechanical_overlap_cluster_count"]
            ),
            full_ranked_worklist_count=cast(
                int, document["full_ranked_worklist_count"]
            ),
            review_packet_limit=cast(int, document["review_packet_limit"]),
            review_packet_count=cast(int, document["review_packet_count"]),
            review_packet_oracle_union_count=cast(
                int, document["review_packet_oracle_union_count"]
            ),
            review_packet_oracle_denominator_count=cast(
                int, document["review_packet_oracle_denominator_count"]
            ),
            stopping_reason=cast(StoppingReasonV1, document["stopping_reason"]),
            marginal_coverage_sequence=tuple(
                cast(int, item)
                for item in cast(list[object], document["marginal_coverage_sequence"])
            ),
            noise_by_class=pairs("noise_by_class", document["noise_by_class"]),
            top_review_entries=tuple(
                cast(dict[str, JSONValue], item)
                for item in cast(list[object], document["top_review_entries"])
            ),
            notes=tuple(
                cast(str, item) for item in cast(list[object], document["notes"])
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = ["PrioritizationReportV1"]
