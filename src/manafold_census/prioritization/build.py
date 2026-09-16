"""Atomic M6-03 prioritization publication and reproducibility helpers."""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, measure_file
from ..inventory.manifest import FileDescriptorV1
from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    NON_AUTHORITY_STATEMENTS,
    RANKING_POLICY_ID,
    RANKING_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
    REVIEW_QUESTIONS,
    PlanningNoiseV1,
)
from .analyze import (
    build_assessments,
    cluster_mechanical_overlaps,
    rank_worklist,
    select_greedy_review_packet,
)
from .assessment import (
    MechanicalOverlapClusterV1,
    OpportunityAssessmentV1,
)
from .input import (
    LoadedPrioritizationInputsV1,
    PrioritizationInputsV1,
    load_prioritization_inputs,
)
from .manifest import PrioritizationManifestV1
from .report import build_report
from .report_model import PrioritizationReportV1
from .worklist import (
    RankedWorklistEntryV1,
    ReviewPacketEntryV1,
    ReviewPacketV1,
)

PRIORITIZATION_TREE_DOMAIN = "census.m6-03-prioritization-tree.v1"
PRIORITIZATION_VERSION = "1"


@dataclass(frozen=True, slots=True)
class PrioritizationBuildResultV1:
    output_directory: Path
    manifest: PrioritizationManifestV1
    report: PrioritizationReportV1
    assessments: tuple[OpportunityAssessmentV1, ...]
    clusters: tuple[MechanicalOverlapClusterV1, ...]
    worklist: tuple[RankedWorklistEntryV1, ...]
    packet: ReviewPacketV1
    output_tree_digest: str


def _file_map(directory: Path) -> dict[str, Path]:
    return {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }


def directory_digest(directory: str | Path) -> str:
    """Digest relative output names, sizes, and exact bytes."""

    root = Path(directory)
    entries: list[dict[str, JSONValue]] = []
    for relative_path, path in sorted(_file_map(root).items()):
        measurement = measure_file(path)
        entries.append(
            {
                "path": relative_path,
                "sha256": measurement.sha256,
                "byte_length": measurement.byte_length,
            }
        )
    return domain_digest(
        PRIORITIZATION_TREE_DOMAIN,
        cast(JSONValue, entries),
    )


def _write_jsonl(
    root: Path,
    relative_path: str,
    values: Iterable[object],
) -> int:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("wb") as stream:
        for value in values:
            to_wire = getattr(value, "to_wire", None)
            if to_wire is None:
                raise TypeError("JSONL values must expose to_wire")
            stream.write(canonical_json_bytes(to_wire()) + b"\n")
            count += 1
    return count


def _descriptor(root: Path, relative_path: str, record_count: int) -> FileDescriptorV1:
    measurement = measure_file(root / relative_path)
    return FileDescriptorV1(
        relative_path=relative_path,
        sha256=measurement.sha256,
        byte_length=measurement.byte_length,
        record_count=record_count,
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


def _build_packet(
    loaded: LoadedPrioritizationInputsV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    clusters: tuple[MechanicalOverlapClusterV1, ...],
    worklist: tuple[RankedWorklistEntryV1, ...],
) -> ReviewPacketV1:
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


def _write_tree(
    staging: Path,
    loaded: LoadedPrioritizationInputsV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    clusters: tuple[MechanicalOverlapClusterV1, ...],
    worklist: tuple[RankedWorklistEntryV1, ...],
    packet: ReviewPacketV1,
) -> tuple[PrioritizationManifestV1, PrioritizationReportV1]:
    groups_by_id = {item.group_id: item for item in loaded.groups}
    report = build_report(loaded, assessments, clusters, worklist, packet, groups_by_id)
    _write_jsonl(staging, "opportunity-assessments.jsonl", assessments)
    _write_jsonl(staging, "mechanical-overlap-clusters.jsonl", clusters)
    _write_jsonl(staging, "ranked-worklist.jsonl", worklist)
    (staging / "review-packet.json").write_bytes(canonical_json_bytes(packet.to_wire()))
    (staging / "report.json").write_bytes(canonical_json_bytes(report.to_wire()))
    non_noise = sum(
        1 for item in assessments if item.planning_noise is PlanningNoiseV1.NONE
    )
    descriptors = (
        _descriptor(staging, "mechanical-overlap-clusters.jsonl", len(clusters)),
        _descriptor(staging, "opportunity-assessments.jsonl", len(assessments)),
        _descriptor(staging, "ranked-worklist.jsonl", len(worklist)),
        _descriptor(staging, "report.json", 1),
        _descriptor(staging, "review-packet.json", 1),
    )
    manifest = PrioritizationManifestV1(
        prioritization_version=PRIORITIZATION_VERSION,
        assessment_policy_id=ASSESSMENT_POLICY_ID,
        assessment_policy_version=ASSESSMENT_POLICY_VERSION,
        ranking_policy_id=RANKING_POLICY_ID,
        ranking_policy_version=RANKING_POLICY_VERSION,
        review_budget=REVIEW_PACKET_LIMIT,
        source_lock_digest=loaded.inventory_inputs.source_lock_digest,
        source_lock_file_sha256=loaded.inventory_inputs.source_lock_file_sha256,
        m1_manifest_sha256=loaded.inventory_inputs.m1_manifest_sha256,
        m1_structural_aggregate_digest=(
            loaded.inventory_inputs.m1_structural_aggregate_digest
        ),
        m3_manifest_sha256=loaded.inventory_inputs.m3_manifest_sha256,
        parent_m4_manifest_sha256=(loaded.inventory_inputs.parent_m4_manifest_sha256),
        parent_census_release_id=(loaded.inventory_inputs.parent_census_release_id),
        m6_02_manifest_sha256=loaded.m6_02_manifest_sha256,
        m6_02_selected_identity_set_digest=(loaded.m6_02_selected_identity_set_digest),
        m6_02_opportunity_count=loaded.m6_02_opportunity_count,
        input_opportunity_count=len(assessments),
        non_noise_opportunity_count=non_noise,
        planning_noise_opportunity_count=len(assessments) - non_noise,
        mechanical_overlap_cluster_count=len(clusters),
        full_ranked_worklist_count=len(worklist),
        review_packet_count=len(packet.entries),
        review_packet_oracle_union_count=packet.oracle_union_count,
        review_packet_oracle_denominator_count=packet.oracle_denominator_count,
        stopping_reason=packet.stopping_reason,
        file_descriptors=descriptors,
    )
    return manifest, report


def _write_manifest(root: Path, manifest: PrioritizationManifestV1) -> None:
    (root / "manifest.json").write_bytes(canonical_json_bytes(manifest.to_wire()))


def build_prioritization_from_loaded_inputs(
    loaded: LoadedPrioritizationInputsV1,
    output_directory: str | Path,
) -> PrioritizationBuildResultV1:
    """Build and atomically publish one prioritization from loaded inputs."""

    output_path = Path(output_directory)
    if output_path.exists():
        raise ValueError("prioritization output directory must not already exist")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_path.name}-",
            dir=str(output_path.parent),
        )
    )
    try:
        surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
        assessments = build_assessments(
            loaded.groups, loaded.opportunities, surfaces_by_id
        )
        clusters = cluster_mechanical_overlaps(assessments)
        worklist = rank_worklist(assessments, clusters)
        packet = _build_packet(loaded, assessments, clusters, worklist)
        manifest, report = _write_tree(
            staging, loaded, assessments, clusters, worklist, packet
        )
        _write_manifest(staging, manifest)
        from .validate import validate_prioritization

        validate_prioritization(staging)
        validate_report_matches_inputs(staging, loaded)
        os.replace(staging, output_path)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    tree_digest = directory_digest(output_path)
    final_report = PrioritizationReportV1.from_wire(
        json.loads((output_path / "report.json").read_bytes())
    )
    return PrioritizationBuildResultV1(
        output_directory=output_path,
        manifest=manifest,
        report=final_report,
        assessments=assessments,
        clusters=clusters,
        worklist=worklist,
        packet=packet,
        output_tree_digest=tree_digest,
    )


def validate_report_matches_inputs(
    staging: Path,
    loaded: LoadedPrioritizationInputsV1,
) -> None:
    from .validate import validate_prioritization_against_inputs

    validate_prioritization_against_inputs(staging, loaded)


def build_prioritization(
    inputs: PrioritizationInputsV1,
    output_directory: str | Path,
) -> PrioritizationBuildResultV1:
    """Load explicit parent inputs, build, validate, and publish output."""

    return build_prioritization_from_loaded_inputs(
        load_prioritization_inputs(inputs),
        output_directory,
    )


def compare_directories(
    first: str | Path,
    second: str | Path,
) -> tuple[bool, bool]:
    """Return exact file-set and byte parity for two prioritization trees."""

    first_map = _file_map(Path(first))
    second_map = _file_map(Path(second))
    if set(first_map) != set(second_map):
        return False, False
    byte_parity = all(
        filecmp.cmp(first_map[path], second_map[path], shallow=False)
        for path in sorted(first_map)
    )
    return True, byte_parity


__all__ = [
    "PRIORITIZATION_TREE_DOMAIN",
    "PrioritizationBuildResultV1",
    "build_prioritization",
    "build_prioritization_from_loaded_inputs",
    "compare_directories",
    "directory_digest",
]
