"""Independent validation for M6-03 non-authoritative output trees."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, measure_file
from ..inventory._common import authority
from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
    PlanningNoiseV1,
)
from .analyze import (
    assessment_sort_key,
    build_assessments,
    classify_planning_noise,
    cluster_mechanical_overlaps,
    distinct_raw_text_count,
    rank_worklist,
    select_greedy_review_packet,
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
from .input import LoadedPrioritizationInputsV1
from .manifest import PrioritizationManifestV1
from .packet import build_review_packet
from .report import build_report
from .report_model import PrioritizationReportV1
from .worklist import (
    RankedWorklistEntryV1,
    ReviewPacketV1,
)

EXPECTED_FILES = frozenset(
    {
        "manifest.json",
        "opportunity-assessments.jsonl",
        "mechanical-overlap-clusters.jsonl",
        "ranked-worklist.jsonl",
        "review-packet.json",
        "report.json",
    }
)


class PrioritizationValidationError(ValueError):
    """Raised when a prioritization tree is not canonical or closed."""


class _WireValue(Protocol):
    def to_wire(self) -> dict[str, JSONValue]: ...


@dataclass(frozen=True, slots=True)
class PrioritizationValidationResultV1:
    output_directory: Path
    manifest: PrioritizationManifestV1
    report: PrioritizationReportV1
    assessments: tuple[OpportunityAssessmentV1, ...]
    clusters: tuple[MechanicalOverlapClusterV1, ...]
    worklist: tuple[RankedWorklistEntryV1, ...]
    packet: ReviewPacketV1
    output_tree_digest: str


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PrioritizationValidationError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict) or raw != canonical_json_bytes(value):
        raise PrioritizationValidationError(f"{label} is not canonical JSON")
    return cast(dict[str, object], value)


def _read_jsonl[WireT: _WireValue](
    path: Path,
    parser: Callable[[object], WireT],
    label: str,
) -> tuple[WireT, ...]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PrioritizationValidationError(f"{label} cannot be read") from error
    values: list[WireT] = []
    for line_number, line in enumerate(raw.splitlines(keepends=True), start=1):
        if not line.endswith(b"\n"):
            raise PrioritizationValidationError(
                f"{label} line {line_number} is missing final LF"
            )
        try:
            document = json.loads(line)
            value = parser(document)
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise PrioritizationValidationError(
                f"{label} line {line_number} is invalid"
            ) from error
        if line != canonical_json_bytes(cast(JSONValue, value.to_wire())) + b"\n":
            raise PrioritizationValidationError(
                f"{label} line {line_number} is not canonical JSONL"
            )
        values.append(value)
    return tuple(values)


def _file_set(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }


def _tree_digest(root: Path) -> str:
    entries: list[dict[str, JSONValue]] = []
    for relative_path in sorted(_file_set(root)):
        measurement = measure_file(root / relative_path)
        entries.append(
            {
                "path": relative_path,
                "sha256": measurement.sha256,
                "byte_length": measurement.byte_length,
            }
        )
    return domain_digest(
        "census.m6-03-prioritization-tree.v1",
        cast(JSONValue, entries),
    )


def _descriptor_counts(
    root: Path,
    manifest: PrioritizationManifestV1,
    counts: dict[str, int],
) -> None:
    descriptor_paths = {item.relative_path for item in manifest.file_descriptors}
    expected_paths = EXPECTED_FILES - {"manifest.json"}
    if descriptor_paths != expected_paths:
        raise PrioritizationValidationError("manifest descriptor file set mismatch")
    for descriptor in manifest.file_descriptors:
        path = root / descriptor.relative_path
        if not path.is_file():
            raise PrioritizationValidationError(
                f"missing descriptor file: {descriptor.relative_path}"
            )
        measurement = measure_file(path)
        if (
            descriptor.sha256 != measurement.sha256
            or descriptor.byte_length != measurement.byte_length
        ):
            raise PrioritizationValidationError(
                f"stale descriptor: {descriptor.relative_path}"
            )
        if descriptor.record_count != counts[descriptor.relative_path]:
            raise PrioritizationValidationError(
                f"stale record count: {descriptor.relative_path}"
            )


def _check_semantic_fields(assessments: tuple[OpportunityAssessmentV1, ...]) -> None:
    for assessment in assessments:
        for field in (
            "semantic_impact",
            "semantic_uncertainty",
            "existing_capability_reuse",
            "new_capability_family",
            "contract_fit",
            "m7_fit",
            "semantic_disposition",
        ):
            if getattr(assessment, field) != "UNASSESSED":
                raise PrioritizationValidationError(
                    "semantic planning field is not UNASSESSED"
                )
        authority(assessment.authority_scope)


def _check_worklist_order(
    worklist: tuple[RankedWorklistEntryV1, ...],
    assessments: tuple[OpportunityAssessmentV1, ...],
    clusters: tuple[MechanicalOverlapClusterV1, ...],
) -> None:
    expected = rank_worklist(assessments, clusters)
    if tuple(item.to_wire() for item in worklist) != tuple(
        item.to_wire() for item in expected
    ):
        raise PrioritizationValidationError("ranked worklist order is stale")
    if tuple(item.rank for item in worklist) != tuple(range(1, len(worklist) + 1)):
        raise PrioritizationValidationError("ranked worklist ranks are not dense")


def _check_packet_coverage(
    packet: ReviewPacketV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    worklist: tuple[RankedWorklistEntryV1, ...],
) -> None:
    assessments_by_id = {item.opportunity_id: item for item in assessments}
    selected, reason, marginals = select_greedy_review_packet(
        worklist, assessments_by_id, limit=REVIEW_PACKET_LIMIT
    )
    if tuple(item.opportunity_id for item in packet.entries) != selected:
        raise PrioritizationValidationError("review packet selection is stale")
    if packet.stopping_reason != reason:
        raise PrioritizationValidationError("review packet stopping reason is stale")
    if packet.marginal_coverage_sequence != marginals:
        raise PrioritizationValidationError("review packet marginals are stale")
    covered: set[str] = set()
    cumulative = 0
    for entry, expected_marginal in zip(packet.entries, marginals, strict=True):
        assessment = assessments_by_id[entry.opportunity_id]
        fresh = len(set(assessment.member_oracle_ids) - covered)
        if entry.marginal_oracle_count != fresh or fresh != expected_marginal:
            raise PrioritizationValidationError("review packet marginal is stale")
        covered |= set(assessment.member_oracle_ids)
        cumulative = len(covered)
        if entry.cumulative_oracle_count != cumulative:
            raise PrioritizationValidationError("review packet cumulative is stale")
    if packet.oracle_union_count != len(covered):
        raise PrioritizationValidationError("review packet union is stale")


def validate_prioritization(
    output_directory: str | Path,
) -> PrioritizationValidationResultV1:
    """Validate one complete canonical prioritization tree."""

    root = Path(output_directory)
    if not root.is_dir():
        raise PrioritizationValidationError("prioritization output missing")
    if _file_set(root) != EXPECTED_FILES:
        raise PrioritizationValidationError("prioritization file set mismatch")

    manifest_document = _read_object(root / "manifest.json", "manifest")
    try:
        manifest = PrioritizationManifestV1.from_wire(manifest_document)
    except (TypeError, ValueError) as error:
        raise PrioritizationValidationError("manifest is invalid") from error

    assessments = _read_jsonl(
        root / "opportunity-assessments.jsonl",
        OpportunityAssessmentV1.from_wire,
        "opportunity-assessments.jsonl",
    )
    clusters = _read_jsonl(
        root / "mechanical-overlap-clusters.jsonl",
        MechanicalOverlapClusterV1.from_wire,
        "mechanical-overlap-clusters.jsonl",
    )
    worklist = _read_jsonl(
        root / "ranked-worklist.jsonl",
        RankedWorklistEntryV1.from_wire,
        "ranked-worklist.jsonl",
    )
    packet_document = _read_object(root / "review-packet.json", "review packet")
    try:
        packet = ReviewPacketV1.from_wire(packet_document)
    except (TypeError, ValueError) as error:
        raise PrioritizationValidationError("review packet is invalid") from error
    report_document = _read_object(root / "report.json", "report")
    try:
        report = PrioritizationReportV1.from_wire(report_document)
    except (TypeError, ValueError) as error:
        raise PrioritizationValidationError("report is invalid") from error

    _check_semantic_fields(assessments)
    assessment_ids = [item.opportunity_id for item in assessments]
    if len(set(assessment_ids)) != len(assessment_ids):
        raise PrioritizationValidationError("duplicate assessed Opportunity")
    if sorted(assessment_ids) != assessment_ids:
        raise PrioritizationValidationError("assessments are not canonically ordered")
    _check_worklist_order(worklist, assessments, clusters)
    _check_packet_coverage(packet, assessments, worklist)

    from .binding import check_frozen_constants

    check_frozen_constants(manifest, assessments, packet, report)

    if manifest.input_opportunity_count != len(assessments):
        raise PrioritizationValidationError("manifest input count is stale")
    if manifest.full_ranked_worklist_count != len(worklist):
        raise PrioritizationValidationError("manifest worklist count is stale")
    if manifest.mechanical_overlap_cluster_count != len(clusters):
        raise PrioritizationValidationError("manifest cluster count is stale")
    if manifest.review_packet_count != len(packet.entries):
        raise PrioritizationValidationError("manifest packet count is stale")
    if manifest.review_packet_oracle_union_count != packet.oracle_union_count:
        raise PrioritizationValidationError("manifest union count is stale")
    if manifest.stopping_reason != packet.stopping_reason:
        raise PrioritizationValidationError("manifest stopping reason is stale")
    if (
        report.input_opportunity_count != len(assessments)
        or report.full_ranked_worklist_count != len(worklist)
        or report.mechanical_overlap_cluster_count != len(clusters)
        or report.review_packet_count != len(packet.entries)
        or report.stopping_reason != packet.stopping_reason
    ):
        raise PrioritizationValidationError("report aggregates are stale")

    _descriptor_counts(
        root,
        manifest,
        {
            "opportunity-assessments.jsonl": len(assessments),
            "mechanical-overlap-clusters.jsonl": len(clusters),
            "ranked-worklist.jsonl": len(worklist),
            "review-packet.json": 1,
            "report.json": 1,
        },
    )
    return PrioritizationValidationResultV1(
        output_directory=root,
        manifest=manifest,
        report=report,
        assessments=assessments,
        clusters=clusters,
        worklist=worklist,
        packet=packet,
        output_tree_digest=_tree_digest(root),
    )


def validate_prioritization_against_inputs(
    output_directory: str | Path,
    loaded: LoadedPrioritizationInputsV1,
) -> PrioritizationValidationResultV1:
    """Validate internal artifacts and bind them to explicit parent inputs."""

    result = validate_prioritization(output_directory)
    surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
    expected_assessments = build_assessments(
        loaded.groups, loaded.opportunities, surfaces_by_id
    )
    if tuple(item.to_wire() for item in result.assessments) != tuple(
        item.to_wire() for item in expected_assessments
    ):
        raise PrioritizationValidationError("assessments do not match M6-02 inputs")
    expected_clusters = cluster_mechanical_overlaps(expected_assessments)
    if tuple(item.to_wire() for item in result.clusters) != tuple(
        item.to_wire() for item in expected_clusters
    ):
        raise PrioritizationValidationError("overlap clusters are stale")
    for assessment in result.assessments:
        member_ids = assessment.member_surface_ids
        if assessment.member_surface_set_digest != surface_set_digest(member_ids):
            raise PrioritizationValidationError("surface-set digest is stale")
        raw_texts = tuple(
            surfaces_by_id[surface_id].raw_text for surface_id in member_ids
        )
        if assessment.planning_noise != classify_planning_noise(raw_texts):
            raise PrioritizationValidationError("planning-noise class is stale")
        if assessment.distinct_raw_text_count != distinct_raw_text_count(raw_texts):
            raise PrioritizationValidationError("distinct raw-text count is stale")
        expected_id = opportunity_assessment_id(
            opportunity_id=assessment.opportunity_id,
            assessment_policy_id=ASSESSMENT_POLICY_ID,
            assessment_policy_version=ASSESSMENT_POLICY_VERSION,
            grouping_lens=assessment.grouping_lens.value,
            member_surface_set_digest=assessment.member_surface_set_digest,
            distinct_oracle_count=assessment.distinct_oracle_count,
            distinct_raw_text_count=assessment.distinct_raw_text_count,
            occurrence_count=assessment.occurrence_count,
            planning_noise=assessment.planning_noise.value,
        )
        if assessment.assessment_id != expected_id:
            raise PrioritizationValidationError("assessment identity is stale")
    for cluster in result.clusters:
        if cluster.cluster_id != overlap_cluster_id(cluster.member_surface_ids):
            raise PrioritizationValidationError("overlap cluster identity is stale")
    expected_keys = tuple(assessment_sort_key(item) for item in expected_assessments)
    actual_keys = tuple(assessment_sort_key(item) for item in result.assessments)
    if actual_keys != expected_keys:
        raise PrioritizationValidationError("ranking keys are stale")

    manifest = result.manifest
    expected_binding = (
        loaded.inventory_inputs.source_lock_digest,
        loaded.inventory_inputs.source_lock_file_sha256,
        loaded.inventory_inputs.m1_manifest_sha256,
        loaded.inventory_inputs.m1_structural_aggregate_digest,
        loaded.inventory_inputs.m3_manifest_sha256,
        loaded.inventory_inputs.parent_m4_manifest_sha256,
        loaded.inventory_inputs.parent_census_release_id,
        loaded.m6_02_manifest_sha256,
        loaded.m6_02_selected_identity_set_digest,
        loaded.m6_02_opportunity_count,
    )
    actual_binding = (
        manifest.source_lock_digest,
        manifest.source_lock_file_sha256,
        manifest.m1_manifest_sha256,
        manifest.m1_structural_aggregate_digest,
        manifest.m3_manifest_sha256,
        manifest.parent_m4_manifest_sha256,
        manifest.parent_census_release_id,
        manifest.m6_02_manifest_sha256,
        manifest.m6_02_selected_identity_set_digest,
        manifest.m6_02_opportunity_count,
    )
    if actual_binding != expected_binding:
        raise PrioritizationValidationError("manifest is not bound to inputs")
    if len(loaded.opportunities) != manifest.m6_02_opportunity_count:
        raise PrioritizationValidationError("M6-02 Opportunity count drifted")
    packet = result.packet
    if packet.m4_active_family_ids != loaded.m4_active_family_ids:
        raise PrioritizationValidationError("M4 family context is stale")
    if packet.oracle_denominator_count != len(
        loaded.inventory_inputs.selected_oracle_ids
    ):
        raise PrioritizationValidationError("packet denominator is stale")
    noise_values = {item.planning_noise for item in result.assessments}
    if PlanningNoiseV1.NONE not in noise_values and result.packet.entries:
        raise PrioritizationValidationError("packet without non-noise basis")
    for entry in packet.entries:
        assessment = next(
            item
            for item in result.assessments
            if item.opportunity_id == entry.opportunity_id
        )
        if assessment.planning_noise is not PlanningNoiseV1.NONE:
            raise PrioritizationValidationError("noise entered the review packet")

    expected_worklist = rank_worklist(expected_assessments, expected_clusters)
    if tuple(item.to_wire() for item in result.worklist) != tuple(
        item.to_wire() for item in expected_worklist
    ):
        raise PrioritizationValidationError("ranked worklist does not match inputs")
    expected_packet = build_review_packet(
        loaded, expected_assessments, expected_clusters, expected_worklist
    )
    if result.packet.to_wire() != expected_packet.to_wire():
        raise PrioritizationValidationError(
            "review packet does not match validated inputs"
        )
    groups_by_id = {item.group_id: item for item in loaded.groups}
    expected_report = build_report(
        loaded,
        expected_assessments,
        expected_clusters,
        expected_worklist,
        expected_packet,
        groups_by_id,
    )
    if result.report.to_wire() != expected_report.to_wire():
        raise PrioritizationValidationError("report does not match validated inputs")

    from .binding import check_parent_bindings

    check_parent_bindings(result.packet, result.report, loaded)
    return result


__all__ = [
    "EXPECTED_FILES",
    "PrioritizationValidationError",
    "PrioritizationValidationResultV1",
    "validate_prioritization",
    "validate_prioritization_against_inputs",
]
