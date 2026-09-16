"""Two-run parity and path-free evidence for M6-03 prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ._common import AUTHORITY_SCOPE, NON_AUTHORITY_STATEMENTS
from .build import (
    PrioritizationBuildResultV1,
    build_prioritization_from_loaded_inputs,
    compare_directories,
)
from .input import PrioritizationInputsV1, load_prioritization_inputs
from .validate import validate_prioritization_against_inputs


@dataclass(frozen=True, slots=True)
class PrioritizationReproductionResultV1:
    input_opportunity_count: int
    output_tree_digest: str
    fileset_parity: bool
    byte_parity: bool
    evidence_json: Path
    evidence_markdown: Path


def _evidence_document(
    first: PrioritizationBuildResultV1,
    second: PrioritizationBuildResultV1,
    *,
    fileset_parity: bool,
    byte_parity: bool,
) -> dict[str, JSONValue]:
    report = first.report.to_wire()
    packet = first.packet.to_wire()
    return {
        "schema": "census.m6-03-prioritization-evidence.v1",
        "authority_scope": AUTHORITY_SCOPE,
        "source_lock_digest": first.manifest.source_lock_digest,
        "m1_manifest_sha256": first.manifest.m1_manifest_sha256,
        "m3_manifest_sha256": first.manifest.m3_manifest_sha256,
        "parent_m4_manifest_sha256": first.manifest.parent_m4_manifest_sha256,
        "parent_census_release_id": first.manifest.parent_census_release_id,
        "m6_02_manifest_sha256": first.manifest.m6_02_manifest_sha256,
        "m6_02_selected_identity_set_digest": (
            first.manifest.m6_02_selected_identity_set_digest
        ),
        "m6_02_opportunity_count": first.manifest.m6_02_opportunity_count,
        "assessment_policy_id": first.manifest.assessment_policy_id,
        "assessment_policy_version": first.manifest.assessment_policy_version,
        "ranking_policy_id": first.manifest.ranking_policy_id,
        "ranking_policy_version": first.manifest.ranking_policy_version,
        "run_a": {
            "relative_output": "run-a",
            "output_tree_digest": first.output_tree_digest,
            "file_count": len(
                [item for item in first.output_directory.rglob("*") if item.is_file()]
            ),
        },
        "run_b": {
            "relative_output": "run-b",
            "output_tree_digest": second.output_tree_digest,
            "file_count": len(
                [item for item in second.output_directory.rglob("*") if item.is_file()]
            ),
        },
        "run_a_run_b_fileset_parity": fileset_parity,
        "run_a_run_b_byte_parity": byte_parity,
        "path_free_manifest": True,
        "offline_regeneration": True,
        "observed_prioritization": {
            "input_opportunity_count": first.manifest.input_opportunity_count,
            "non_noise_opportunity_count": (first.manifest.non_noise_opportunity_count),
            "planning_noise_opportunity_count": (
                first.manifest.planning_noise_opportunity_count
            ),
            "mechanical_overlap_cluster_count": (
                first.manifest.mechanical_overlap_cluster_count
            ),
            "full_ranked_worklist_count": (first.manifest.full_ranked_worklist_count),
            "review_packet_count": first.manifest.review_packet_count,
            "review_packet_oracle_union_count": (
                first.manifest.review_packet_oracle_union_count
            ),
            "review_packet_oracle_denominator_count": (
                first.manifest.review_packet_oracle_denominator_count
            ),
            "stopping_reason": first.manifest.stopping_reason.value,
            "marginal_coverage_sequence": packet["marginal_coverage_sequence"],
            "noise_by_class": report["noise_by_class"],
        },
        "non_authority_statement": list(NON_AUTHORITY_STATEMENTS),
    }


def _write_evidence(
    document: dict[str, JSONValue],
    evidence_json: Path,
    evidence_markdown: Path,
) -> None:
    evidence_json.parent.mkdir(parents=True, exist_ok=True)
    evidence_markdown.parent.mkdir(parents=True, exist_ok=True)
    evidence_json.write_bytes(canonical_json_bytes(document))
    observed = cast(dict[str, JSONValue], document["observed_prioritization"])
    markdown = "\n".join(
        [
            "# M6-03 Capability-Opportunity Ranking Evidence",
            "",
            "This evidence records two deterministic, offline prioritization builds.",
            "",
            "Capability Opportunity != Capability.",
            "Opportunity assessment != semantic review.",
            "Ranking != authority.",
            "Mechanical overlap != semantic equivalence.",
            "Marginal Oracle coverage != semantic breadth.",
            "M6-03 creates no Requirement, Capability, mapping, or M4 authority.",
            "",
            "## Input identities",
            "",
            f"- SourceLock digest: {document['source_lock_digest']}",
            f"- M1 manifest SHA-256: {document['m1_manifest_sha256']}",
            f"- M3 manifest SHA-256: {document['m3_manifest_sha256']}",
            f"- Parent M4 manifest SHA-256: {document['parent_m4_manifest_sha256']}",
            f"- Parent Census release ID: {document['parent_census_release_id']}",
            f"- M6-02 manifest SHA-256: {document['m6_02_manifest_sha256']}",
            "- M6-02 selected identity-set digest: "
            f"{document['m6_02_selected_identity_set_digest']}",
            f"- M6-02 Opportunity count: {document['m6_02_opportunity_count']}",
            f"- Assessment policy: {document['assessment_policy_id']} "
            f"v{document['assessment_policy_version']}",
            f"- Ranking policy: {document['ranking_policy_id']} "
            f"v{document['ranking_policy_version']}",
            "",
            "## Population and observed prioritization",
            "",
            f"- Input Opportunities: {observed['input_opportunity_count']}",
            f"- Non-noise Opportunities: {observed['non_noise_opportunity_count']}",
            f"- Planning-noise Opportunities: "
            f"{observed['planning_noise_opportunity_count']}",
            f"- Mechanical-overlap clusters: "
            f"{observed['mechanical_overlap_cluster_count']}",
            f"- Full ranked worklist: {observed['full_ranked_worklist_count']}",
            f"- Review packet (limit 25): {observed['review_packet_count']}",
            "- Review-packet Oracle union coverage: "
            f"{observed['review_packet_oracle_union_count']} / "
            f"{observed['review_packet_oracle_denominator_count']}",
            f"- Stopping reason: {observed['stopping_reason']}",
            f"- Marginal coverage sequence: {observed['marginal_coverage_sequence']}",
            f"- Noise by class: {observed['noise_by_class']}",
            "",
            "## Parity gates",
            "",
            "- RUN_A_RUN_B_FILESET_PARITY: "
            f"{str(document['run_a_run_b_fileset_parity']).upper()}",
            "- RUN_A_RUN_B_BYTE_PARITY: "
            f"{str(document['run_a_run_b_byte_parity']).upper()}",
            f"- PATH_FREE_MANIFEST: {str(document['path_free_manifest']).upper()}",
            f"- OFFLINE_REGENERATION: {str(document['offline_regeneration']).upper()}",
            "",
            "Capability Opportunity count is NOT Capability count.",
            "No Requirement, Capability, mapping, or M4 authority is created.",
            "",
        ]
    )
    evidence_markdown.write_text(markdown, encoding="utf-8", newline="\n")


def reproduce_prioritization(
    inputs: PrioritizationInputsV1,
    output_root: str | Path,
    evidence_json: str | Path,
    evidence_markdown: str | Path,
) -> PrioritizationReproductionResultV1:
    """Build, validate, compare, and evidence two explicit prioritizations."""

    root = Path(output_root)
    first_path = root / "run-a"
    second_path = root / "run-b"
    evidence_json_path = Path(evidence_json)
    evidence_markdown_path = Path(evidence_markdown)
    if first_path.exists() or second_path.exists():
        raise ValueError("M6-03 reproduction output directories must be fresh")
    loaded = load_prioritization_inputs(inputs)
    root.mkdir(parents=True, exist_ok=True)
    first = build_prioritization_from_loaded_inputs(loaded, first_path)
    second = build_prioritization_from_loaded_inputs(loaded, second_path)
    first_validation = validate_prioritization_against_inputs(first_path, loaded)
    second_validation = validate_prioritization_against_inputs(second_path, loaded)
    fileset_parity, byte_parity = compare_directories(first_path, second_path)
    if not fileset_parity or not byte_parity:
        raise ValueError("M6-03 A/B prioritization parity failed")
    document = _evidence_document(
        first,
        second,
        fileset_parity=fileset_parity,
        byte_parity=byte_parity,
    )
    _write_evidence(
        document,
        evidence_json_path,
        evidence_markdown_path,
    )
    if first_validation.output_tree_digest != first.output_tree_digest:
        raise ValueError("RUN_A validation digest changed")
    if second_validation.output_tree_digest != second.output_tree_digest:
        raise ValueError("RUN_B validation digest changed")
    return PrioritizationReproductionResultV1(
        input_opportunity_count=first.manifest.input_opportunity_count,
        output_tree_digest=first.output_tree_digest,
        fileset_parity=fileset_parity,
        byte_parity=byte_parity,
        evidence_json=evidence_json_path,
        evidence_markdown=evidence_markdown_path,
    )


__all__ = [
    "PrioritizationReproductionResultV1",
    "reproduce_prioritization",
]
