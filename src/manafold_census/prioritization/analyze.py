"""Deterministic mechanical analysis, overlap control, and ranking."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping

from ..inventory.model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    SourceSurfaceV1,
)
from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
    PlanningNoiseV1,
    StoppingReasonV1,
    lens_rank,
)
from .assessment import (
    MechanicalOverlapClusterV1,
    OpportunityAssessmentV1,
)
from .identity import (
    opportunity_assessment_id,
    overlap_cluster_id,
    surface_set_digest,
)
from .worklist import RankedWorklistEntryV1


def classify_planning_noise(
    raw_texts: Iterable[str | None],
) -> PlanningNoiseV1:
    """Classify planning noise from raw source-surface content only."""

    values = tuple(raw_texts)
    if not values:
        return PlanningNoiseV1.NONE
    if all(item is None for item in values):
        return PlanningNoiseV1.ALL_NULL
    if all(item is not None and item.strip() == "" for item in values):
        return PlanningNoiseV1.ALL_EMPTY_OR_WHITESPACE
    if all(item is None or item.strip() == "" for item in values):
        return PlanningNoiseV1.NULL_OR_EMPTY_ONLY
    return PlanningNoiseV1.NONE


def distinct_raw_text_count(
    raw_texts: Iterable[str | None],
) -> int:
    return len(set(raw_texts))


def build_assessments(
    groups: Iterable[CandidateGroupV1],
    opportunities: Iterable[CapabilityOpportunityV1],
    surfaces_by_id: Mapping[str, SourceSurfaceV1],
) -> tuple[OpportunityAssessmentV1, ...]:
    """Derive one planning assessment per recurring M6-02 Opportunity."""

    groups_by_id = {group.group_id: group for group in groups}
    assessments: list[OpportunityAssessmentV1] = []
    for opportunity in opportunities:
        if len(opportunity.candidate_group_ids) != 1:
            raise ValueError("M6-03 expects one group per M6-02 Opportunity")
        group = groups_by_id.get(opportunity.candidate_group_ids[0])
        if group is None:
            raise ValueError("Opportunity references an unknown group")
        if group.grouping_lens is not opportunity.grouping_lens:
            raise ValueError("Opportunity lens does not match its group")
        member_surface_ids = tuple(
            sorted(member.surface_id for member in group.members)
        )
        member_oracle_ids = tuple(
            sorted({member.oracle_id for member in group.members})
        )
        try:
            member_surfaces = tuple(
                surfaces_by_id[surface_id] for surface_id in member_surface_ids
            )
        except KeyError as error:
            raise ValueError("group references an unknown surface") from error
        raw_texts = tuple(item.raw_text for item in member_surfaces)
        noise = classify_planning_noise(raw_texts)
        raw_count = distinct_raw_text_count(raw_texts)
        set_digest = surface_set_digest(member_surface_ids)
        representatives = member_surface_ids[:3]
        assessments.append(
            OpportunityAssessmentV1(
                assessment_id=opportunity_assessment_id(
                    opportunity_id=opportunity.opportunity_id,
                    assessment_policy_id=ASSESSMENT_POLICY_ID,
                    assessment_policy_version=ASSESSMENT_POLICY_VERSION,
                    grouping_lens=opportunity.grouping_lens.value,
                    member_surface_set_digest=set_digest,
                    distinct_oracle_count=len(member_oracle_ids),
                    distinct_raw_text_count=raw_count,
                    occurrence_count=len(member_surface_ids),
                    planning_noise=noise.value,
                ),
                opportunity_id=opportunity.opportunity_id,
                candidate_group_id=group.group_id,
                grouping_lens=opportunity.grouping_lens,
                assessment_policy_id=ASSESSMENT_POLICY_ID,
                assessment_policy_version=ASSESSMENT_POLICY_VERSION,
                distinct_oracle_count=len(member_oracle_ids),
                occurrence_count=len(member_surface_ids),
                member_surface_count=len(member_surface_ids),
                distinct_raw_text_count=raw_count,
                planning_noise=noise,
                member_surface_set_digest=set_digest,
                member_surface_ids=member_surface_ids,
                member_oracle_ids=member_oracle_ids,
                representative_surface_ids=representatives,
            )
        )
    return tuple(sorted(assessments, key=lambda item: item.opportunity_id))


def cluster_mechanical_overlaps(
    assessments: Iterable[OpportunityAssessmentV1],
) -> tuple[MechanicalOverlapClusterV1, ...]:
    """Group Opportunities sharing the exact same underlying surface-ID set."""

    assessment_values = tuple(assessments)
    by_digest: dict[str, list[OpportunityAssessmentV1]] = {}
    for assessment in assessment_values:
        by_digest.setdefault(assessment.member_surface_set_digest, []).append(
            assessment
        )
    clusters: list[MechanicalOverlapClusterV1] = []
    for set_digest, members in by_digest.items():
        surface_ids = members[0].member_surface_ids
        if any(item.member_surface_ids != surface_ids for item in members):
            raise ValueError("surface-set digest collision across ID sets")
        ordered = sorted(
            members,
            key=lambda item: (
                lens_rank(item.grouping_lens.value),
                item.opportunity_id,
            ),
        )
        representative = ordered[0].opportunity_id
        member_ids = tuple(sorted(item.opportunity_id for item in members))
        clusters.append(
            MechanicalOverlapClusterV1(
                cluster_id=overlap_cluster_id(surface_ids),
                member_surface_set_digest=set_digest,
                member_surface_ids=surface_ids,
                member_opportunity_ids=member_ids,
                representative_opportunity_id=representative,
                member_count=len(member_ids),
            )
        )
    return tuple(sorted(clusters, key=lambda item: item.cluster_id))


def assessment_sort_key(
    assessment: OpportunityAssessmentV1,
) -> tuple[int, int, int, int, int, str]:
    """Return the frozen full-worklist ordering key for one assessment."""

    return (
        0 if assessment.planning_noise is PlanningNoiseV1.NONE else 1,
        -assessment.distinct_oracle_count,
        assessment.distinct_raw_text_count,
        -assessment.occurrence_count,
        lens_rank(assessment.grouping_lens.value),
        assessment.opportunity_id,
    )


def rank_worklist(
    assessments: Iterable[OpportunityAssessmentV1],
    clusters: Iterable[MechanicalOverlapClusterV1],
) -> tuple[RankedWorklistEntryV1, ...]:
    """Emit the complete ordered planning worklist for every Opportunity."""

    cluster_by_opportunity: dict[str, MechanicalOverlapClusterV1] = {}
    for cluster in clusters:
        for opportunity_id in cluster.member_opportunity_ids:
            if opportunity_id in cluster_by_opportunity:
                raise ValueError("Opportunity belongs to two overlap clusters")
            cluster_by_opportunity[opportunity_id] = cluster
    ordered = sorted(assessments, key=assessment_sort_key)
    entries: list[RankedWorklistEntryV1] = []
    for rank, assessment in enumerate(ordered, start=1):
        matched = cluster_by_opportunity.get(assessment.opportunity_id)
        if matched is None:
            raise ValueError("assessment lacks a mechanical-overlap cluster")
        entries.append(
            RankedWorklistEntryV1(
                rank=rank,
                opportunity_id=assessment.opportunity_id,
                candidate_group_id=assessment.candidate_group_id,
                grouping_lens=assessment.grouping_lens,
                distinct_oracle_count=assessment.distinct_oracle_count,
                distinct_raw_text_count=assessment.distinct_raw_text_count,
                occurrence_count=assessment.occurrence_count,
                planning_noise=assessment.planning_noise,
                mechanical_overlap_cluster_id=matched.cluster_id,
                is_overlap_representative=(
                    matched.representative_opportunity_id == assessment.opportunity_id
                ),
            )
        )
    return tuple(entries)


def select_greedy_review_packet(
    ranked: Iterable[RankedWorklistEntryV1],
    assessments_by_id: Mapping[str, OpportunityAssessmentV1],
    *,
    limit: int = REVIEW_PACKET_LIMIT,
) -> tuple[tuple[str, ...], StoppingReasonV1, tuple[int, ...]]:
    """Select bounded review IDs by greedy marginal Oracle coverage."""

    eligible = tuple(
        item
        for item in ranked
        if item.planning_noise is PlanningNoiseV1.NONE
        and item.is_overlap_representative
    )
    covered: set[str] = set()
    selected: list[str] = []
    marginals: list[int] = []
    remaining = list(eligible)
    while remaining and len(selected) < limit:
        best: RankedWorklistEntryV1 | None = None
        best_marginal = -1
        best_key: tuple[int, int, int, int, int, str] | None = None
        for candidate in remaining:
            assessment = assessments_by_id[candidate.opportunity_id]
            marginal = len(set(assessment.member_oracle_ids) - covered)
            key = (
                -marginal,
                -candidate.distinct_oracle_count,
                candidate.distinct_raw_text_count,
                -candidate.occurrence_count,
                lens_rank(candidate.grouping_lens.value),
                candidate.opportunity_id,
            )
            if best_key is None or key < best_key:
                best_key = key
                best = candidate
                best_marginal = marginal
        if best is None or best_marginal <= 0:
            break
        selected.append(best.opportunity_id)
        marginals.append(best_marginal)
        covered |= set(assessments_by_id[best.opportunity_id].member_oracle_ids)
        remaining = [item for item in remaining if item != best]
    if len(selected) >= limit:
        reason = StoppingReasonV1.REVIEW_BUDGET_REACHED
    else:
        reason = StoppingReasonV1.NO_ADDITIONAL_ORACLE_COVERAGE
    if not selected and reason is StoppingReasonV1.REVIEW_BUDGET_REACHED:
        reason = StoppingReasonV1.NO_ADDITIONAL_ORACLE_COVERAGE
    return tuple(selected), reason, tuple(marginals)


def noise_counts(
    assessments: Iterable[OpportunityAssessmentV1],
) -> Counter[str]:
    return Counter(item.planning_noise.value for item in assessments)


__all__ = [
    "assessment_sort_key",
    "build_assessments",
    "classify_planning_noise",
    "cluster_mechanical_overlaps",
    "distinct_raw_text_count",
    "noise_counts",
    "rank_worklist",
    "select_greedy_review_packet",
]
