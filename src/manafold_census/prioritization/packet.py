"""Deterministic bounded review-packet construction for M6-03 planning.

This pure builder is shared by atomic publication and independent
validation: the validator rederives the exact packet bytes from validated
inputs and requires the persisted packet to match wire-for-wire.
"""

from __future__ import annotations

from ..canonical import JSONValue
from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    NON_AUTHORITY_STATEMENTS,
    RANKING_POLICY_ID,
    RANKING_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
    REVIEW_QUESTIONS,
)
from .analyze import select_greedy_review_packet
from .assessment import (
    MechanicalOverlapClusterV1,
    OpportunityAssessmentV1,
)
from .input import LoadedPrioritizationInputsV1
from .worklist import (
    RankedWorklistEntryV1,
    ReviewPacketEntryV1,
    ReviewPacketV1,
)


def _example_surface(
    surface_id: str,
    loaded: LoadedPrioritizationInputsV1,
) -> dict[str, JSONValue]:
    surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
    surface = surfaces_by_id[surface_id]
    return {
        "surface_id": surface.surface_id,
        "oracle_id": surface.oracle_id,
        "source_card_id": surface.source_card_id,
        "source_record_sha256": surface.source_record_sha256,
        "face_index": surface.face_index,
        "line_index": surface.line_index,
        "raw_text": surface.raw_text,
    }


def build_review_packet(
    loaded: LoadedPrioritizationInputsV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    clusters: tuple[MechanicalOverlapClusterV1, ...],
    worklist: tuple[RankedWorklistEntryV1, ...],
) -> ReviewPacketV1:
    """Derive the bounded review packet from validated planning inputs."""

    assessments_by_id = {item.opportunity_id: item for item in assessments}
    cluster_by_opportunity: dict[str, str] = {}
    for cluster in clusters:
        for opportunity_id in cluster.member_opportunity_ids:
            cluster_by_opportunity[opportunity_id] = cluster.cluster_id
    groups_by_id = {item.group_id: item for item in loaded.groups}
    selected_ids, reason, marginals = select_greedy_review_packet(
        worklist, assessments_by_id, limit=REVIEW_PACKET_LIMIT
    )
    del marginals
    entries: list[ReviewPacketEntryV1] = []
    covered: set[str] = set()
    for index, opportunity_id in enumerate(selected_ids, start=1):
        assessment = assessments_by_id[opportunity_id]
        group = groups_by_id[assessment.candidate_group_id]
        new_oracles = set(assessment.member_oracle_ids) - covered
        covered |= set(assessment.member_oracle_ids)
        examples = tuple(
            _example_surface(surface_id, loaded)
            for surface_id in assessment.representative_surface_ids
        )
        entries.append(
            ReviewPacketEntryV1(
                selection_index=index,
                opportunity_id=assessment.opportunity_id,
                candidate_group_id=assessment.candidate_group_id,
                grouping_lens=assessment.grouping_lens,
                group_key=group.group_key,
                group_key_digest=group.group_key_digest,
                distinct_oracle_count=assessment.distinct_oracle_count,
                occurrence_count=assessment.occurrence_count,
                member_surface_count=assessment.member_surface_count,
                distinct_raw_text_count=assessment.distinct_raw_text_count,
                marginal_oracle_count=len(new_oracles),
                cumulative_oracle_count=len(covered),
                mechanical_overlap_cluster_id=(cluster_by_opportunity[opportunity_id]),
                representative_surface_ids=(assessment.representative_surface_ids),
                example_surfaces=examples,
            )
        )
    denominator = len(loaded.inventory_inputs.selected_oracle_ids)
    return ReviewPacketV1(
        ranking_policy_id=RANKING_POLICY_ID,
        ranking_policy_version=RANKING_POLICY_VERSION,
        assessment_policy_id=ASSESSMENT_POLICY_ID,
        assessment_policy_version=ASSESSMENT_POLICY_VERSION,
        review_budget=REVIEW_PACKET_LIMIT,
        selected_count=len(entries),
        stopping_reason=reason,
        oracle_union_count=len(covered),
        oracle_denominator_count=denominator,
        marginal_coverage_sequence=tuple(
            item.marginal_oracle_count for item in entries
        ),
        entries=tuple(entries),
        review_questions=REVIEW_QUESTIONS,
        source_lock_digest=loaded.inventory_inputs.source_lock_digest,
        m1_manifest_sha256=loaded.inventory_inputs.m1_manifest_sha256,
        m3_manifest_sha256=loaded.inventory_inputs.m3_manifest_sha256,
        parent_m4_manifest_sha256=(loaded.inventory_inputs.parent_m4_manifest_sha256),
        parent_census_release_id=(loaded.inventory_inputs.parent_census_release_id),
        m6_02_manifest_sha256=loaded.m6_02_manifest_sha256,
        m6_02_selected_identity_set_digest=(loaded.m6_02_selected_identity_set_digest),
        m4_active_family_ids=loaded.m4_active_family_ids,
        non_authority_statements=NON_AUTHORITY_STATEMENTS,
    )


__all__ = ["build_review_packet"]
