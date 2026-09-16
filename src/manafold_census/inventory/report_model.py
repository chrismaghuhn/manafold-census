"""Compact non-authoritative inventory report model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ._common import (
    AUTHORITY_SCOPE,
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
class InventoryReportV1:
    source_lock_digest: str
    m1_manifest_sha256: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    selected_identity_count: int
    total_surface_count: int
    candidate_group_count: int
    recurring_group_count: int
    singleton_group_count: int
    oracle_ids_in_recurring_groups: int
    oracle_ids_only_in_singleton_groups: int
    opportunity_count: int
    lens_summaries: tuple[dict[str, JSONValue], ...]
    largest_recurring_groups: tuple[dict[str, JSONValue], ...]
    highest_frequency_ability_line_groups: tuple[dict[str, JSONValue], ...]
    group_size_distribution: tuple[tuple[str, int], ...]
    notes: tuple[str, ...]
    authority_scope: str = AUTHORITY_SCOPE

    SCHEMA: ClassVar[str] = "census.m6-02-inventory-report.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "authority_scope",
        "source_lock_digest",
        "m1_manifest_sha256",
        "m3_manifest_sha256",
        "parent_m4_manifest_sha256",
        "parent_census_release_id",
        "selected_identity_count",
        "total_surface_count",
        "candidate_group_count",
        "recurring_group_count",
        "singleton_group_count",
        "oracle_ids_in_recurring_groups",
        "oracle_ids_only_in_singleton_groups",
        "opportunity_count",
        "lens_summaries",
        "largest_recurring_groups",
        "highest_frequency_ability_line_groups",
        "group_size_distribution",
        "notes",
    }

    def __post_init__(self) -> None:
        digest("source_lock_digest", self.source_lock_digest)
        digest("m1_manifest_sha256", self.m1_manifest_sha256)
        digest("m3_manifest_sha256", self.m3_manifest_sha256)
        digest("parent_m4_manifest_sha256", self.parent_m4_manifest_sha256)
        census_release_id("parent_census_release_id", self.parent_census_release_id)
        for field in (
            "selected_identity_count",
            "total_surface_count",
            "candidate_group_count",
            "recurring_group_count",
            "singleton_group_count",
            "oracle_ids_in_recurring_groups",
            "oracle_ids_only_in_singleton_groups",
            "opportunity_count",
        ):
            nonnegative(field, getattr(self, field))
        for field in (
            "lens_summaries",
            "largest_recurring_groups",
            "highest_frequency_ability_line_groups",
        ):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, dict) for item in values):
                raise TypeError(f"{field} must contain objects")
            object.__setattr__(self, field, values)
        object.__setattr__(
            self,
            "group_size_distribution",
            tuple(self.group_size_distribution),
        )
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
            "selected_identity_count": self.selected_identity_count,
            "total_surface_count": self.total_surface_count,
            "candidate_group_count": self.candidate_group_count,
            "recurring_group_count": self.recurring_group_count,
            "singleton_group_count": self.singleton_group_count,
            "oracle_ids_in_recurring_groups": self.oracle_ids_in_recurring_groups,
            "oracle_ids_only_in_singleton_groups": (
                self.oracle_ids_only_in_singleton_groups
            ),
            "opportunity_count": self.opportunity_count,
            "lens_summaries": list(self.lens_summaries),
            "largest_recurring_groups": list(self.largest_recurring_groups),
            "highest_frequency_ability_line_groups": list(
                self.highest_frequency_ability_line_groups
            ),
            "group_size_distribution": pair_wire(self.group_size_distribution),
            "notes": list(self.notes),
        }

    @classmethod
    def from_wire(cls, value: object) -> InventoryReportV1:
        document = object_with_keys(value, cls._WIRE_KEYS, "inventory report")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        array_fields = (
            "lens_summaries",
            "largest_recurring_groups",
            "highest_frequency_ability_line_groups",
            "notes",
        )
        for field in array_fields:
            if not isinstance(document[field], list):
                raise TypeError(f"{field} must be an array")
        return cls(
            source_lock_digest=cast(str, document["source_lock_digest"]),
            m1_manifest_sha256=cast(str, document["m1_manifest_sha256"]),
            m3_manifest_sha256=cast(str, document["m3_manifest_sha256"]),
            parent_m4_manifest_sha256=cast(str, document["parent_m4_manifest_sha256"]),
            parent_census_release_id=cast(str, document["parent_census_release_id"]),
            selected_identity_count=cast(int, document["selected_identity_count"]),
            total_surface_count=cast(int, document["total_surface_count"]),
            candidate_group_count=cast(int, document["candidate_group_count"]),
            recurring_group_count=cast(int, document["recurring_group_count"]),
            singleton_group_count=cast(int, document["singleton_group_count"]),
            oracle_ids_in_recurring_groups=cast(
                int, document["oracle_ids_in_recurring_groups"]
            ),
            oracle_ids_only_in_singleton_groups=cast(
                int, document["oracle_ids_only_in_singleton_groups"]
            ),
            opportunity_count=cast(int, document["opportunity_count"]),
            lens_summaries=tuple(
                cast(dict[str, JSONValue], item)
                for item in cast(list[object], document["lens_summaries"])
            ),
            largest_recurring_groups=tuple(
                cast(dict[str, JSONValue], item)
                for item in cast(list[object], document["largest_recurring_groups"])
            ),
            highest_frequency_ability_line_groups=tuple(
                cast(dict[str, JSONValue], item)
                for item in cast(
                    list[object],
                    document["highest_frequency_ability_line_groups"],
                )
            ),
            group_size_distribution=pairs(
                "group_size_distribution",
                document["group_size_distribution"],
            ),
            notes=tuple(
                cast(str, item) for item in cast(list[object], document["notes"])
            ),
            authority_scope=cast(str, document["authority_scope"]),
        )


__all__ = ["InventoryReportV1"]
