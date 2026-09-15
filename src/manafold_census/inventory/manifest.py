"""Inventory manifest and file-descriptor models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ._common import (
    AUTHORITY_SCOPE,
    GroupingLensV1,
    authority,
    census_release_id,
    digest,
    nonnegative,
    object_with_keys,
    pair_wire,
    pairs,
    text,
)


@dataclass(frozen=True, slots=True)
class FileDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int

    _WIRE_KEYS: ClassVar[set[str]] = {
        "relative_path",
        "sha256",
        "byte_length",
        "record_count",
    }

    def __post_init__(self) -> None:
        path = text("relative_path", self.relative_path)
        if (
            "\\" in path
            or path.startswith("/")
            or ":" in path
            or ".." in path.split("/")
        ):
            raise ValueError("relative_path must be a safe POSIX relative path")
        object.__setattr__(self, "relative_path", path)
        digest("sha256", self.sha256)
        nonnegative("byte_length", self.byte_length)
        nonnegative("record_count", self.record_count)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "record_count": self.record_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> FileDescriptorV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "file descriptor")
        return cls(
            relative_path=cast(str, document["relative_path"]),
            sha256=cast(str, document["sha256"]),
            byte_length=cast(int, document["byte_length"]),
            record_count=cast(int, document["record_count"]),
        )


@dataclass(frozen=True, slots=True)
class InventoryManifestV1:
    inventory_version: str
    grouping_policy_id: str
    grouping_policy_version: str
    shape_policy_id: str
    shape_policy_version: str
    source_lock_digest: str
    source_lock_file_sha256: str
    m1_manifest_sha256: str
    m1_structural_aggregate_digest: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    selected_identity_count: int
    selected_identity_set_digest: str
    total_surface_count: int
    lens_group_counts: tuple[tuple[str, int], ...]
    candidate_group_count: int
    opportunity_count: int
    file_descriptors: tuple[FileDescriptorV1, ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-inventory-manifest.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "inventory_version",
        "grouping_policy_id",
        "grouping_policy_version",
        "shape_policy_id",
        "shape_policy_version",
        "source_lock_digest",
        "source_lock_file_sha256",
        "m1_manifest_sha256",
        "m1_structural_aggregate_digest",
        "m3_manifest_sha256",
        "parent_m4_manifest_sha256",
        "parent_census_release_id",
        "selected_identity_count",
        "selected_identity_set_digest",
        "total_surface_count",
        "lens_group_counts",
        "candidate_group_count",
        "opportunity_count",
        "file_descriptors",
    }

    def __post_init__(self) -> None:
        text("inventory_version", self.inventory_version)
        text("grouping_policy_id", self.grouping_policy_id)
        text("grouping_policy_version", self.grouping_policy_version)
        text("shape_policy_id", self.shape_policy_id)
        text("shape_policy_version", self.shape_policy_version)
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
        nonnegative("selected_identity_count", self.selected_identity_count)
        digest("selected_identity_set_digest", self.selected_identity_set_digest)
        nonnegative("total_surface_count", self.total_surface_count)
        lens_counts = tuple(self.lens_group_counts)
        if lens_counts != tuple(sorted(lens_counts)):
            raise ValueError("lens_group_counts must be sorted")
        if len({key for key, _ in lens_counts}) != len(lens_counts):
            raise ValueError("lens_group_counts must be unique")
        if any(
            key not in {item.value for item in GroupingLensV1} for key, _ in lens_counts
        ):
            raise ValueError("lens_group_counts contains an unknown lens")
        object.__setattr__(self, "lens_group_counts", lens_counts)
        nonnegative("candidate_group_count", self.candidate_group_count)
        nonnegative("opportunity_count", self.opportunity_count)
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
            "inventory_version": self.inventory_version,
            "grouping_policy_id": self.grouping_policy_id,
            "grouping_policy_version": self.grouping_policy_version,
            "shape_policy_id": self.shape_policy_id,
            "shape_policy_version": self.shape_policy_version,
            "source_lock_digest": self.source_lock_digest,
            "source_lock_file_sha256": self.source_lock_file_sha256,
            "m1_manifest_sha256": self.m1_manifest_sha256,
            "m1_structural_aggregate_digest": self.m1_structural_aggregate_digest,
            "m3_manifest_sha256": self.m3_manifest_sha256,
            "parent_m4_manifest_sha256": self.parent_m4_manifest_sha256,
            "parent_census_release_id": self.parent_census_release_id,
            "selected_identity_count": self.selected_identity_count,
            "selected_identity_set_digest": self.selected_identity_set_digest,
            "total_surface_count": self.total_surface_count,
            "lens_group_counts": pair_wire(self.lens_group_counts),
            "candidate_group_count": self.candidate_group_count,
            "opportunity_count": self.opportunity_count,
            "file_descriptors": [item.to_wire() for item in self.file_descriptors],
        }

    @classmethod
    def from_wire(cls, value: object) -> InventoryManifestV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "inventory manifest")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_descriptors = document["file_descriptors"]
        if not isinstance(raw_descriptors, list):
            raise TypeError("file_descriptors must be an array")
        return cls(
            inventory_version=cast(str, document["inventory_version"]),
            grouping_policy_id=cast(str, document["grouping_policy_id"]),
            grouping_policy_version=cast(str, document["grouping_policy_version"]),
            shape_policy_id=cast(str, document["shape_policy_id"]),
            shape_policy_version=cast(str, document["shape_policy_version"]),
            source_lock_digest=cast(str, document["source_lock_digest"]),
            source_lock_file_sha256=cast(str, document["source_lock_file_sha256"]),
            m1_manifest_sha256=cast(str, document["m1_manifest_sha256"]),
            m1_structural_aggregate_digest=cast(
                str, document["m1_structural_aggregate_digest"]
            ),
            m3_manifest_sha256=cast(str, document["m3_manifest_sha256"]),
            parent_m4_manifest_sha256=cast(str, document["parent_m4_manifest_sha256"]),
            parent_census_release_id=cast(str, document["parent_census_release_id"]),
            selected_identity_count=cast(int, document["selected_identity_count"]),
            selected_identity_set_digest=cast(
                str, document["selected_identity_set_digest"]
            ),
            total_surface_count=cast(int, document["total_surface_count"]),
            lens_group_counts=pairs("lens_group_counts", document["lens_group_counts"]),
            candidate_group_count=cast(int, document["candidate_group_count"]),
            opportunity_count=cast(int, document["opportunity_count"]),
            file_descriptors=tuple(
                FileDescriptorV1.from_wire(item) for item in raw_descriptors
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = ["FileDescriptorV1", "InventoryManifestV1"]
