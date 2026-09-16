"""Deterministic summaries for the M6-03 prioritization."""

from __future__ import annotations

from collections.abc import Mapping

from ..canonical import JSONValue
from ..inventory.model import CandidateGroupV1
from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    NON_AUTHORITY_STATEMENTS,
    RANKING_POLICY_ID,
    RANKING_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
)
from .analyze import noise_counts
from .assessment import (
    MechanicalOverlapClusterV1,
    OpportunityAssessmentV1,
)
from .input import LoadedPrioritizationInputsV1
from .report_model import PrioritizationReportV1
from .worklist import RankedWorklistEntryV1, ReviewPacketV1


def build_report(
    loaded: LoadedPrioritizationInputsV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    clusters: tuple[MechanicalOverlapClusterV1, ...],
    worklist: tuple[RankedWorklistEntryV1, ...],
    packet: ReviewPacketV1,
    groups_by_id: Mapping[str, CandidateGroupV1],
) -> PrioritizationReportV1:
    """Build the compact deterministic report for one validated input set."""

    del groups_by_id
    counts = noise_counts(assessments)
    noise_partition = tuple(
        sorted(counts.items()),
    )
    top_entries: list[dict[str, JSONValue]] = []
    for entry in packet.entries:
        top_entries.append(
            {
                "selection_index": entry.selection_index,
                "opportunity_id": entry.opportunity_id,
                "candidate_group_id": entry.candidate_group_id,
                "grouping_lens": entry.grouping_lens.value,
                "distinct_oracle_count": entry.distinct_oracle_count,
                "marginal_oracle_count": entry.marginal_oracle_count,
                "cumulative_oracle_count": entry.cumulative_oracle_count,
            }
        )
    oracle_union = packet.oracle_union_count
    return PrioritizationReportV1(
        source_lock_digest=loaded.inventory_inputs.source_lock_digest,
        m1_manifest_sha256=loaded.inventory_inputs.m1_manifest_sha256,
        m3_manifest_sha256=loaded.inventory_inputs.m3_manifest_sha256,
        parent_m4_manifest_sha256=(loaded.inventory_inputs.parent_m4_manifest_sha256),
        parent_census_release_id=(loaded.inventory_inputs.parent_census_release_id),
        m6_02_manifest_sha256=loaded.m6_02_manifest_sha256,
        m6_02_selected_identity_set_digest=(loaded.m6_02_selected_identity_set_digest),
        assessment_policy_id=ASSESSMENT_POLICY_ID,
        assessment_policy_version=ASSESSMENT_POLICY_VERSION,
        ranking_policy_id=RANKING_POLICY_ID,
        ranking_policy_version=RANKING_POLICY_VERSION,
        input_opportunity_count=len(assessments),
        non_noise_opportunity_count=sum(
            1 for item in assessments if item.planning_noise.value == "NONE"
        ),
        planning_noise_opportunity_count=sum(
            1 for item in assessments if item.planning_noise.value != "NONE"
        ),
        mechanical_overlap_cluster_count=len(clusters),
        full_ranked_worklist_count=len(worklist),
        review_packet_limit=REVIEW_PACKET_LIMIT,
        review_packet_count=len(packet.entries),
        review_packet_oracle_union_count=oracle_union,
        review_packet_oracle_denominator_count=packet.oracle_denominator_count,
        stopping_reason=packet.stopping_reason,
        marginal_coverage_sequence=packet.marginal_coverage_sequence,
        noise_by_class=noise_partition,
        top_review_entries=tuple(top_entries),
        notes=NON_AUTHORITY_STATEMENTS,
    )


__all__ = ["build_report"]
