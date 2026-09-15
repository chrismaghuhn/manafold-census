"""Two-run parity and path-free evidence for M6-02 inventories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from .build import (
    InventoryBuildResultV1,
    build_inventory_from_loaded_inputs,
    compare_directories,
)
from .input import InventoryInputsV1, load_inventory_inputs
from .model import AUTHORITY_SCOPE
from .validate import validate_inventory_against_inputs


@dataclass(frozen=True, slots=True)
class InventoryReproductionResultV1:
    selected_identity_count: int
    selected_identity_set_digest: str
    output_tree_digest: str
    fileset_parity: bool
    byte_parity: bool
    evidence_json: Path
    evidence_markdown: Path


def _evidence_document(
    first: InventoryBuildResultV1,
    second: InventoryBuildResultV1,
    *,
    fileset_parity: bool,
    byte_parity: bool,
) -> dict[str, JSONValue]:
    report = first.report.to_wire()
    return {
        "schema": "census.m6-02-inventory-evidence.v1",
        "authority_scope": AUTHORITY_SCOPE,
        "source_lock_digest": first.manifest.source_lock_digest,
        "m1_manifest_sha256": first.manifest.m1_manifest_sha256,
        "m3_manifest_sha256": first.manifest.m3_manifest_sha256,
        "parent_m4_manifest_sha256": first.manifest.parent_m4_manifest_sha256,
        "parent_census_release_id": first.manifest.parent_census_release_id,
        "selected_unresolved_oracle_identity_count": (
            first.manifest.selected_identity_count
        ),
        "selected_identity_set_digest": first.manifest.selected_identity_set_digest,
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
        "observed_inventory": {
            "total_surfaces": first.report.total_surface_count,
            "candidate_group_count": first.report.candidate_group_count,
            "recurring_group_count": first.report.recurring_group_count,
            "singleton_group_count": first.report.singleton_group_count,
            "capability_opportunity_count": first.report.opportunity_count,
            "oracle_ids_in_recurring_groups": (
                first.report.oracle_ids_in_recurring_groups
            ),
            "oracle_ids_only_in_singleton_groups": (
                first.report.oracle_ids_only_in_singleton_groups
            ),
            "largest_recurring_groups": report["largest_recurring_groups"],
            "highest_frequency_ability_line_groups": report[
                "highest_frequency_ability_line_groups"
            ],
            "group_size_distribution": report["group_size_distribution"],
        },
        "non_authority_statement": report["notes"],
    }


def _write_evidence(
    document: dict[str, JSONValue],
    evidence_json: Path,
    evidence_markdown: Path,
) -> None:
    evidence_json.parent.mkdir(parents=True, exist_ok=True)
    evidence_markdown.parent.mkdir(parents=True, exist_ok=True)
    evidence_json.write_bytes(canonical_json_bytes(document))
    observed = cast(dict[str, JSONValue], document["observed_inventory"])
    markdown = "\n".join(
        [
            "# M6-02 Unresolved-Pattern Inventory Evidence",
            "",
            "This evidence records two deterministic, offline inventory builds.",
            "",
            "## Input identities",
            "",
            f"- SourceLock digest: {document['source_lock_digest']}",
            f"- M1 manifest SHA-256: {document['m1_manifest_sha256']}",
            f"- M3 manifest SHA-256: {document['m3_manifest_sha256']}",
            f"- Parent M4 manifest SHA-256: {document['parent_m4_manifest_sha256']}",
            f"- Parent Census release ID: {document['parent_census_release_id']}",
            "",
            "## Population and observed inventory",
            "",
            "- Selected unresolved Oracle identities: "
            f"{document['selected_unresolved_oracle_identity_count']}",
            "- Selected identity-set digest: "
            f"{document['selected_identity_set_digest']}",
            f"- Total surfaces: {observed['total_surfaces']}",
            f"- Candidate groups: {observed['candidate_group_count']}",
            f"- Recurring groups: {observed['recurring_group_count']}",
            f"- Singleton groups: {observed['singleton_group_count']}",
            f"- Capability Opportunities: {observed['capability_opportunity_count']}",
            "- Oracle IDs in recurring groups: "
            f"{observed['oracle_ids_in_recurring_groups']}",
            "- Oracle IDs only in singleton groups: "
            f"{observed['oracle_ids_only_in_singleton_groups']}",
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
            "Candidate grouping is non-authoritative.",
            "Capability Opportunity count is NOT Capability count.",
            "No Requirement, Capability, mapping, or M4 authority is created.",
            "",
        ]
    )
    evidence_markdown.write_text(markdown, encoding="utf-8", newline="\n")


def reproduce_inventory(
    inputs: InventoryInputsV1,
    output_root: str | Path,
    evidence_json: str | Path,
    evidence_markdown: str | Path,
) -> InventoryReproductionResultV1:
    """Build, validate, compare, and evidence two explicit inventory runs."""

    root = Path(output_root)
    first_path = root / "run-a"
    second_path = root / "run-b"
    evidence_json_path = Path(evidence_json)
    evidence_markdown_path = Path(evidence_markdown)
    if first_path.exists() or second_path.exists():
        raise ValueError("M6-02 reproduction output directories must be fresh")
    loaded = load_inventory_inputs(inputs)
    root.mkdir(parents=True, exist_ok=True)
    first = build_inventory_from_loaded_inputs(loaded, first_path)
    second = build_inventory_from_loaded_inputs(loaded, second_path)
    first_validation = validate_inventory_against_inputs(first_path, loaded)
    second_validation = validate_inventory_against_inputs(second_path, loaded)
    fileset_parity, byte_parity = compare_directories(first_path, second_path)
    if not fileset_parity or not byte_parity:
        raise ValueError("M6-02 A/B inventory parity failed")
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
    return InventoryReproductionResultV1(
        selected_identity_count=first.manifest.selected_identity_count,
        selected_identity_set_digest=first.manifest.selected_identity_set_digest,
        output_tree_digest=first.output_tree_digest,
        fileset_parity=fileset_parity,
        byte_parity=byte_parity,
        evidence_json=evidence_json_path,
        evidence_markdown=evidence_markdown_path,
    )


__all__ = [
    "InventoryReproductionResultV1",
    "reproduce_inventory",
]
