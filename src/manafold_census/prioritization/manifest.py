"""Prioritization manifest and file-descriptor models."""

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
    text,
)
from ..inventory.manifest import FileDescriptorV1
from ._common import AUTHORITY_SCOPE, StoppingReasonV1


@dataclass(frozen=True, slots=True)
class PrioritizationManifestV1:
    prioritization_version: str
    assessment_policy_id: str
    assessment_policy_version: str
    ranking_policy_id: str
    ranking_policy_version: str
    review_budget: int
    source_lock_digest: str
    source_lock_file_sha256: str
    m1_manifest_sha256: str
    m1_structural_aggregate_digest: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    m6_02_manifest_sha256: str
    m6_02_selected_identity_set_digest: str
    m6_02_opportunity_count: int
    input_opportunity_count: int
    non_noise_opportunity_count: int
    planning_noise_opportunity_count: int
    mechanical_overlap_cluster_count: int
    full_ranked_worklist_count: int
    review_packet_count: int
    review_packet_oracle_union_count: int
    review_packet_oracle_denominator_count: int
    stopping_reason: StoppingReasonV1
    file_descriptors: tuple[FileDescriptorV1, ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-03-prioritization-manifest.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "prioritization_version",
        "assessment_policy_id",
        "assessment_policy_version",
        "ranking_policy_id",
        "ranking_policy_version",
        "review_budget",
        "source_lock_digest",
        "source_lock_file_sha256",
        "m1_manifest_sha256",
        "m1_structural_aggregate_digest",
        "m3_manifest_sha256",
        "parent_m4_manifest_sha256",
        "parent_census_release_id",
        "m6_02_manifest_sha256",
        "m6_02_selected_identity_set_digest",
        "m6_02_opportunity_count",
        "input_opportunity_count",
        "non_noise_opportunity_count",
        "planning_noise_opportunity_count",
        "mechanical_overlap_cluster_count",
        "full_ranked_worklist_count",
        "review_packet_count",
        "review_packet_oracle_union_count",
        "review_packet_oracle_denominator_count",
        "stopping_reason",
        "file_descriptors",
    }

    def __post_init__(self) -> None:
        text("prioritization_version", self.prioritization_version)
        text("assessment_policy_id", self.assessment_policy_id)
        text("assessment_policy_version", self.assessment_policy_version)
        text("ranking_policy_id", self.ranking_policy_id)
        text("ranking_policy_version", self.ranking_policy_version)
        nonnegative("review_budget", self.review_budget)
        digest("source_lock_digest", self.source_lock_digest)
        digest("source_lock_file_sha256", self.source_lock_file_sha256)
        digest("m1_manifest_sha256", self.m1_manifest_sha256)
        digest(
            "m1_structural_aggregate_digest",
            self.m1_structural_aggregate_digest,
        )
        digest("m3_manifest_sha256", self.m3_manifest_sha256)
        digest("parent_m4_manifest_sha256", self.parent_m4_manifest_sha256)
        census_release_id("parent_census_release_id", self.parent_census_release_id)
        digest("m6_02_manifest_sha256", self.m6_02_manifest_sha256)
        digest(
            "m6_02_selected_identity_set_digest",
            self.m6_02_selected_identity_set_digest,
        )
        nonnegative("m6_02_opportunity_count", self.m6_02_opportunity_count)
        nonnegative("input_opportunity_count", self.input_opportunity_count)
        nonnegative("non_noise_opportunity_count", self.non_noise_opportunity_count)
        nonnegative(
            "planning_noise_opportunity_count",
            self.planning_noise_opportunity_count,
        )
        if self.input_opportunity_count != (
            self.non_noise_opportunity_count + self.planning_noise_opportunity_count
        ):
            raise ValueError("noise partition does not sum to inputs")
        nonnegative(
            "mechanical_overlap_cluster_count",
            self.mechanical_overlap_cluster_count,
        )
        nonnegative("full_ranked_worklist_count", self.full_ranked_worklist_count)
        if self.full_ranked_worklist_count != self.input_opportunity_count:
            raise ValueError("full worklist must cover every input Opportunity")
        nonnegative("review_packet_count", self.review_packet_count)
        if self.review_packet_count > self.review_budget:
            raise ValueError("review packet exceeds its planning budget")
        nonnegative(
            "review_packet_oracle_union_count",
            self.review_packet_oracle_union_count,
        )
        nonnegative(
            "review_packet_oracle_denominator_count",
            self.review_packet_oracle_denominator_count,
        )
        object.__setattr__(
            self,
            "stopping_reason",
            enum_value("stopping_reason", self.stopping_reason, StoppingReasonV1),
        )
        descriptors = tuple(self.file_descriptors)
        if descriptors != tuple(
            sorted(descriptors, key=lambda item: item.relative_path)
        ):
            raise ValueError("file_descriptors must be sorted")
        if len({item.relative_path for item in descriptors}) != len(descriptors):
            raise ValueError("file_descriptors must be unique")
        if any(not isinstance(item, FileDescriptorV1) for item in descriptors):
            raise TypeError("file_descriptors must contain FileDescriptorV1 values")
        object.__setattr__(self, "file_descriptors", descriptors)
        authority(self.authority_scope)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "authority_scope": self.authority_scope,
            "prioritization_version": self.prioritization_version,
            "assessment_policy_id": self.assessment_policy_id,
            "assessment_policy_version": self.assessment_policy_version,
            "ranking_policy_id": self.ranking_policy_id,
            "ranking_policy_version": self.ranking_policy_version,
            "review_budget": self.review_budget,
            "source_lock_digest": self.source_lock_digest,
            "source_lock_file_sha256": self.source_lock_file_sha256,
            "m1_manifest_sha256": self.m1_manifest_sha256,
            "m1_structural_aggregate_digest": self.m1_structural_aggregate_digest,
            "m3_manifest_sha256": self.m3_manifest_sha256,
            "parent_m4_manifest_sha256": self.parent_m4_manifest_sha256,
            "parent_census_release_id": self.parent_census_release_id,
            "m6_02_manifest_sha256": self.m6_02_manifest_sha256,
            "m6_02_selected_identity_set_digest": (
                self.m6_02_selected_identity_set_digest
            ),
            "m6_02_opportunity_count": self.m6_02_opportunity_count,
            "input_opportunity_count": self.input_opportunity_count,
            "non_noise_opportunity_count": self.non_noise_opportunity_count,
            "planning_noise_opportunity_count": (self.planning_noise_opportunity_count),
            "mechanical_overlap_cluster_count": (self.mechanical_overlap_cluster_count),
            "full_ranked_worklist_count": self.full_ranked_worklist_count,
            "review_packet_count": self.review_packet_count,
            "review_packet_oracle_union_count": (self.review_packet_oracle_union_count),
            "review_packet_oracle_denominator_count": (
                self.review_packet_oracle_denominator_count
            ),
            "stopping_reason": self.stopping_reason.value,
            "file_descriptors": [item.to_wire() for item in self.file_descriptors],
        }

    @classmethod
    def from_wire(cls, value: object) -> PrioritizationManifestV1:
        from ._common import StoppingReasonV1 as _Reason

        document = object_with_keys(value, cls._WIRE_KEYS, "prioritization manifest")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_descriptors = document["file_descriptors"]
        if not isinstance(raw_descriptors, list):
            raise TypeError("file_descriptors must be an array")
        return cls(
            prioritization_version=cast(str, document["prioritization_version"]),
            assessment_policy_id=cast(str, document["assessment_policy_id"]),
            assessment_policy_version=cast(str, document["assessment_policy_version"]),
            ranking_policy_id=cast(str, document["ranking_policy_id"]),
            ranking_policy_version=cast(str, document["ranking_policy_version"]),
            review_budget=cast(int, document["review_budget"]),
            source_lock_digest=cast(str, document["source_lock_digest"]),
            source_lock_file_sha256=cast(str, document["source_lock_file_sha256"]),
            m1_manifest_sha256=cast(str, document["m1_manifest_sha256"]),
            m1_structural_aggregate_digest=cast(
                str, document["m1_structural_aggregate_digest"]
            ),
            m3_manifest_sha256=cast(str, document["m3_manifest_sha256"]),
            parent_m4_manifest_sha256=cast(str, document["parent_m4_manifest_sha256"]),
            parent_census_release_id=cast(str, document["parent_census_release_id"]),
            m6_02_manifest_sha256=cast(str, document["m6_02_manifest_sha256"]),
            m6_02_selected_identity_set_digest=cast(
                str, document["m6_02_selected_identity_set_digest"]
            ),
            m6_02_opportunity_count=cast(int, document["m6_02_opportunity_count"]),
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
            review_packet_count=cast(int, document["review_packet_count"]),
            review_packet_oracle_union_count=cast(
                int, document["review_packet_oracle_union_count"]
            ),
            review_packet_oracle_denominator_count=cast(
                int, document["review_packet_oracle_denominator_count"]
            ),
            stopping_reason=cast(_Reason, document["stopping_reason"]),
            file_descriptors=tuple(
                FileDescriptorV1.from_wire(item) for item in raw_descriptors
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = ["PrioritizationManifestV1"]
