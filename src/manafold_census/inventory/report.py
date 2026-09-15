"""Deterministic summaries and reviewer-facing worklist projections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping

from ..canonical import JSONValue
from .grouping import shape_text_for_surface
from .input import LoadedInventoryInputsV1
from .model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    GroupingLensV1,
    InventoryReportV1,
    RecurrenceStatusV1,
    SourceSurfaceV1,
)


def _surface_example(
    surface: SourceSurfaceV1,
    *,
    include_shape: bool,
) -> dict[str, JSONValue]:
    return {
        "surface_id": surface.surface_id,
        "card_name": surface.card_name,
        "oracle_id": surface.oracle_id,
        "source_card_id": surface.source_card_id,
        "source_record_sha256": surface.source_record_sha256,
        "face_index": surface.face_index,
        "line_index": surface.line_index,
        "raw_text": surface.raw_text,
        "shape_text": shape_text_for_surface(surface) if include_shape else None,
    }


def _group_summary(
    group: CandidateGroupV1,
    surfaces: Mapping[str, SourceSurfaceV1],
) -> dict[str, JSONValue]:
    return {
        "group_id": group.group_id,
        "grouping_lens": group.grouping_lens.value,
        "grouping_policy_id": group.grouping_policy_id,
        "grouping_policy_version": group.grouping_policy_version,
        "group_key": group.group_key,
        "group_key_digest": group.group_key_digest,
        "surface_occurrence_count": group.surface_occurrence_count,
        "distinct_oracle_identity_count": group.distinct_oracle_identity_count,
        "recurrence_status": group.recurrence_status.value,
        "representatives": [
            _surface_example(
                surfaces[surface_id],
                include_shape=group.grouping_lens.value.endswith("_SHAPE"),
            )
            for surface_id in group.representative_surface_ids
        ],
    }


def _lens_summary(
    lens: GroupingLensV1,
    groups: Iterable[CandidateGroupV1],
) -> dict[str, JSONValue]:
    selected = tuple(item for item in groups if item.grouping_lens is lens)
    recurring = tuple(
        item
        for item in selected
        if item.recurrence_status is RecurrenceStatusV1.RECURRING
    )
    singleton = tuple(
        item
        for item in selected
        if item.recurrence_status is RecurrenceStatusV1.SINGLETON
    )
    return {
        "grouping_lens": lens.value,
        "candidate_group_count": len(selected),
        "recurring_group_count": len(recurring),
        "singleton_group_count": len(singleton),
        "surface_occurrence_count": sum(
            item.surface_occurrence_count for item in selected
        ),
        "distinct_oracle_ids_in_any_group": len(
            {member.oracle_id for item in selected for member in item.members}
        ),
    }


def _ranked(
    groups: Iterable[CandidateGroupV1],
    surfaces: Mapping[str, SourceSurfaceV1],
    *,
    limit: int,
) -> tuple[dict[str, JSONValue], ...]:
    recurring = (
        item
        for item in groups
        if item.recurrence_status is RecurrenceStatusV1.RECURRING
    )
    ordered = sorted(
        recurring,
        key=lambda item: (
            -item.distinct_oracle_identity_count,
            -item.surface_occurrence_count,
            item.grouping_lens.value,
            item.group_id,
        ),
    )
    return tuple(_group_summary(item, surfaces) for item in ordered[:limit])


def build_report(
    inputs: LoadedInventoryInputsV1,
    surfaces: Iterable[SourceSurfaceV1],
    groups: Iterable[CandidateGroupV1],
    opportunities: Iterable[CapabilityOpportunityV1],
) -> InventoryReportV1:
    """Build the compact deterministic report for one validated input set."""

    surface_values = tuple(surfaces)
    group_values = tuple(groups)
    opportunity_values = tuple(opportunities)
    surfaces_by_id = {item.surface_id: item for item in surface_values}
    recurring_ids = {
        member.oracle_id
        for group in group_values
        if group.recurrence_status is RecurrenceStatusV1.RECURRING
        for member in group.members
    }
    singleton_ids = {
        member.oracle_id
        for group in group_values
        if group.recurrence_status is RecurrenceStatusV1.SINGLETON
        for member in group.members
    }
    size_distribution = Counter(
        str(group.distinct_oracle_identity_count) for group in group_values
    )
    lens_summaries = tuple(_lens_summary(lens, group_values) for lens in GroupingLensV1)
    ability_groups = (
        item
        for item in group_values
        if item.grouping_lens.value.startswith("ABILITY_LINE")
    )
    notes = (
        "Candidate grouping is non-authoritative planning data.",
        "Capability Opportunity count is NOT Capability count.",
        "This inventory creates no Requirement, Capability, mapping, or M4 authority.",
    )
    return InventoryReportV1(
        source_lock_digest=inputs.source_lock_digest,
        m1_manifest_sha256=inputs.m1_manifest_sha256,
        m3_manifest_sha256=inputs.m3_manifest_sha256,
        parent_m4_manifest_sha256=inputs.parent_m4_manifest_sha256,
        parent_census_release_id=inputs.parent_census_release_id,
        selected_identity_count=len(inputs.selected_oracle_ids),
        total_surface_count=len(surface_values),
        candidate_group_count=len(group_values),
        recurring_group_count=sum(
            group.recurrence_status is RecurrenceStatusV1.RECURRING
            for group in group_values
        ),
        singleton_group_count=sum(
            group.recurrence_status is RecurrenceStatusV1.SINGLETON
            for group in group_values
        ),
        oracle_ids_in_recurring_groups=len(recurring_ids),
        oracle_ids_only_in_singleton_groups=len(singleton_ids - recurring_ids),
        opportunity_count=len(opportunity_values),
        lens_summaries=lens_summaries,
        largest_recurring_groups=_ranked(group_values, surfaces_by_id, limit=20),
        highest_frequency_ability_line_groups=_ranked(
            ability_groups, surfaces_by_id, limit=20
        ),
        group_size_distribution=tuple(sorted(size_distribution.items())),
        notes=notes,
    )


def worklist_sort_key(group: CandidateGroupV1) -> tuple[int, int, str, str]:
    """Return the frozen deterministic reviewer-worklist ordering."""

    return (
        -group.distinct_oracle_identity_count,
        -group.surface_occurrence_count,
        group.grouping_lens.value,
        group.group_id,
    )


__all__ = ["build_report", "worklist_sort_key"]
