"""Exact and conservative lexical-shape grouping lenses."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence

from ._common import (
    GROUPING_POLICY_ID,
    GROUPING_POLICY_VERSION,
    SHAPE_POLICY_ID,
    SHAPE_POLICY_VERSION,
    GroupingLensV1,
    PlanningStatusV1,
    RecurrenceStatusV1,
)
from .identity import (
    candidate_group_id,
    capability_opportunity_id,
    group_key_digest,
)
from .model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    SourceSurfaceV1,
    StructuralSummaryV1,
    SurfaceMemberV1,
)

ALL_GROUPING_LENSES: tuple[GroupingLensV1, ...] = (
    GroupingLensV1.CARD_TEXT_EXACT,
    GroupingLensV1.FACE_TEXT_EXACT,
    GroupingLensV1.ABILITY_LINE_EXACT,
    GroupingLensV1.CARD_TEXT_SHAPE,
    GroupingLensV1.FACE_TEXT_SHAPE,
    GroupingLensV1.ABILITY_LINE_SHAPE,
)

_MANA_PAYLOAD = re.compile(r"\{(?!SOURCE_NAME\}|NUMBER\}|MANA_SYMBOL\})[^{}\r\n]*\}")
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])")
_WHITESPACE = re.compile(r"\s+")


def shape_text(raw_text: str | None, card_name: str) -> str | None:
    """Apply only the documented mechanical lexical-shape transforms."""

    if raw_text is None:
        return None
    name_pattern = re.compile(rf"(?<!\w){re.escape(card_name)}(?!\w)")
    value = name_pattern.sub("{SOURCE_NAME}", raw_text)
    value = _MANA_PAYLOAD.sub("{MANA_SYMBOL}", value)
    value = _NUMBER.sub("{NUMBER}", value)
    return _WHITESPACE.sub(" ", value).strip()


def _scope_for_lens(lens: GroupingLensV1) -> str:
    if lens.value.startswith("CARD_TEXT"):
        return "CARD_TEXT"
    if lens.value.startswith("FACE_TEXT"):
        return "FACE_TEXT"
    return "ABILITY_LINE"


def _is_shape_lens(lens: GroupingLensV1) -> bool:
    return lens.value.endswith("_SHAPE")


def _policy_for_lens(lens: GroupingLensV1) -> tuple[str, str]:
    return (
        (SHAPE_POLICY_ID, SHAPE_POLICY_VERSION)
        if _is_shape_lens(lens)
        else (GROUPING_POLICY_ID, GROUPING_POLICY_VERSION)
    )


def _surface_key(surface: SourceSurfaceV1, lens: GroupingLensV1) -> str | None:
    if _is_shape_lens(lens):
        return shape_text(surface.raw_text, surface.card_name)
    return surface.raw_text


def _member(surface: SourceSurfaceV1) -> SurfaceMemberV1:
    return SurfaceMemberV1(
        surface_id=surface.surface_id,
        oracle_id=surface.oracle_id,
        source_card_id=surface.source_card_id,
        source_record_sha256=surface.source_record_sha256,
        face_index=surface.face_index,
        line_index=surface.line_index,
    )


def _counts(values: Iterable[str | None]) -> tuple[tuple[str, int], ...]:
    counter: Counter[str] = Counter(
        "<NULL>" if value is None else value for value in values
    )
    return tuple(sorted(counter.items()))


def _summary(surfaces: Sequence[SourceSurfaceV1]) -> StructuralSummaryV1:
    keyword_values: list[str] = []
    for surface in surfaces:
        if surface.keywords is not None:
            keyword_values.extend(surface.keywords)
    return StructuralSummaryV1(
        layout_counts=_counts(item.layout for item in surfaces),
        type_line_counts=_counts(item.type_line for item in surfaces),
        keyword_counts=_counts(keyword_values),
        face_count_counts=_counts(str(item.face_count) for item in surfaces),
        line_count_counts=_counts(str(item.line_count) for item in surfaces),
        raw_text_null_count=sum(item.raw_text is None for item in surfaces),
        raw_text_empty_count=sum(item.raw_text == "" for item in surfaces),
    )


def _group(
    lens: GroupingLensV1,
    policy_id: str,
    policy_version: str,
    group_key: str | None,
    surfaces: Sequence[SourceSurfaceV1],
) -> CandidateGroupV1:
    ordered = tuple(
        sorted(
            surfaces,
            key=lambda item: (
                item.oracle_id,
                item.source_card_id,
                item.face_index if item.face_index is not None else -1,
                item.line_index if item.line_index is not None else -1,
                item.surface_id,
            ),
        )
    )
    members = tuple(_member(item) for item in ordered)
    group_id = candidate_group_id(
        lens=lens.value,
        policy_id=policy_id,
        policy_version=policy_version,
        group_key=group_key,
    )
    distinct_count = len({item.oracle_id for item in ordered})
    return CandidateGroupV1(
        group_id=group_id,
        grouping_lens=lens,
        grouping_policy_id=policy_id,
        grouping_policy_version=policy_version,
        group_key=group_key,
        group_key_digest=group_key_digest(
            lens=lens.value,
            policy_id=policy_id,
            policy_version=policy_version,
            group_key=group_key,
        ),
        member_count=len(members),
        surface_occurrence_count=len(members),
        distinct_oracle_identity_count=distinct_count,
        recurrence_status=(
            RecurrenceStatusV1.RECURRING
            if distinct_count >= 2
            else RecurrenceStatusV1.SINGLETON
        ),
        members=members,
        representative_surface_ids=tuple(item.surface_id for item in ordered[:3]),
        structural_summary=_summary(ordered),
    )


def group_surfaces(
    surfaces: Iterable[SourceSurfaceV1],
    lenses: Sequence[GroupingLensV1] = ALL_GROUPING_LENSES,
) -> tuple[CandidateGroupV1, ...]:
    """Group source surfaces through every requested overlapping lens."""

    source_surfaces = tuple(surfaces)
    if any(not isinstance(item, SourceSurfaceV1) for item in source_surfaces):
        raise TypeError("surfaces must contain SourceSurfaceV1 values")
    result: list[CandidateGroupV1] = []
    for lens in lenses:
        policy_id, policy_version = _policy_for_lens(lens)
        by_key: dict[str | None, list[SourceSurfaceV1]] = defaultdict(list)
        expected_scope = _scope_for_lens(lens)
        for surface in source_surfaces:
            if surface.scope.value != expected_scope:
                continue
            by_key[_surface_key(surface, lens)].append(surface)
        result.extend(
            _group(lens, policy_id, policy_version, key, values)
            for key, values in by_key.items()
        )
    return tuple(
        sorted(
            result,
            key=lambda item: (item.grouping_lens.value, item.group_id),
        )
    )


def build_capability_opportunities(
    groups: Iterable[CandidateGroupV1],
) -> tuple[CapabilityOpportunityV1, ...]:
    """Create one UNASSESSED Opportunity for every recurring candidate group."""

    opportunities: list[CapabilityOpportunityV1] = []
    for group in groups:
        if group.recurrence_status is not RecurrenceStatusV1.RECURRING:
            continue
        opportunities.append(
            CapabilityOpportunityV1(
                opportunity_id=capability_opportunity_id(
                    candidate_group_ids=(group.group_id,),
                    policy_id=group.grouping_policy_id,
                    policy_version=group.grouping_policy_version,
                ),
                candidate_group_ids=(group.group_id,),
                grouping_lens=group.grouping_lens,
                grouping_policy_id=group.grouping_policy_id,
                grouping_policy_version=group.grouping_policy_version,
                planning_status=PlanningStatusV1.UNASSESSED,
                surface_occurrence_count=group.surface_occurrence_count,
                distinct_oracle_identity_count=group.distinct_oracle_identity_count,
                representative_surface_ids=group.representative_surface_ids,
                structural_summary=group.structural_summary,
            )
        )
    return tuple(sorted(opportunities, key=lambda item: item.opportunity_id))


__all__ = [
    "ALL_GROUPING_LENSES",
    "build_capability_opportunities",
    "group_surfaces",
    "shape_text",
]
