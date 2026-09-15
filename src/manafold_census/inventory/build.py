"""Atomic M6-02 inventory publication and reproducibility helpers."""

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
from ._common import (
    GROUPING_POLICY_ID,
    GROUPING_POLICY_VERSION,
    SHAPE_POLICY_ID,
    SHAPE_POLICY_VERSION,
)
from .grouping import build_capability_opportunities, group_surfaces
from .identity import selected_identity_set_digest
from .input import (
    InventoryInputsV1,
    LoadedInventoryInputsV1,
    load_inventory_inputs,
)
from .model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    FileDescriptorV1,
    InventoryManifestV1,
    InventoryReportV1,
    SourceSurfaceV1,
    WorklistEntryV1,
)
from .projection import project_surfaces
from .report import build_report, worklist_sort_key

INVENTORY_TREE_DOMAIN = "census.m6-02-inventory-tree.v1"


@dataclass(frozen=True, slots=True)
class InventoryBuildResultV1:
    output_directory: Path
    manifest: InventoryManifestV1
    report: InventoryReportV1
    surfaces: tuple[SourceSurfaceV1, ...]
    groups: tuple[CandidateGroupV1, ...]
    opportunities: tuple[CapabilityOpportunityV1, ...]
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
        INVENTORY_TREE_DOMAIN,
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


def _lens_counts(groups: Iterable[CandidateGroupV1]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for group in groups:
        key = group.grouping_lens.value
        counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(counts.items()))


def _write_tree(
    staging: Path,
    inputs: LoadedInventoryInputsV1,
    surfaces: tuple[SourceSurfaceV1, ...],
    groups: tuple[CandidateGroupV1, ...],
    opportunities: tuple[CapabilityOpportunityV1, ...],
) -> InventoryManifestV1:
    report = build_report(inputs, surfaces, groups, opportunities)
    _write_jsonl(staging, "surfaces.jsonl", surfaces)
    _write_jsonl(staging, "candidate-groups.jsonl", groups)
    _write_jsonl(staging, "capability-opportunities.jsonl", opportunities)
    worklist = tuple(
        WorklistEntryV1(
            group_id=group.group_id,
            grouping_lens=group.grouping_lens,
            distinct_oracle_identity_count=group.distinct_oracle_identity_count,
            surface_occurrence_count=group.surface_occurrence_count,
            recurrence_status=group.recurrence_status,
        )
        for group in sorted(groups, key=worklist_sort_key)
    )
    _write_jsonl(staging, "worklist.jsonl", worklist)
    (staging / "inventory-report.json").write_bytes(
        canonical_json_bytes(report.to_wire())
    )
    descriptors = (
        _descriptor(staging, "candidate-groups.jsonl", len(groups)),
        _descriptor(
            staging,
            "capability-opportunities.jsonl",
            len(opportunities),
        ),
        _descriptor(staging, "inventory-report.json", 1),
        _descriptor(staging, "surfaces.jsonl", len(surfaces)),
        _descriptor(staging, "worklist.jsonl", len(worklist)),
    )
    return InventoryManifestV1(
        inventory_version="1",
        grouping_policy_id=GROUPING_POLICY_ID,
        grouping_policy_version=GROUPING_POLICY_VERSION,
        shape_policy_id=SHAPE_POLICY_ID,
        shape_policy_version=SHAPE_POLICY_VERSION,
        source_lock_digest=inputs.source_lock_digest,
        source_lock_file_sha256=inputs.source_lock_file_sha256,
        m1_manifest_sha256=inputs.m1_manifest_sha256,
        m1_structural_aggregate_digest=inputs.m1_structural_aggregate_digest,
        m3_manifest_sha256=inputs.m3_manifest_sha256,
        parent_m4_manifest_sha256=inputs.parent_m4_manifest_sha256,
        parent_census_release_id=inputs.parent_census_release_id,
        selected_identity_count=len(inputs.selected_oracle_ids),
        selected_identity_set_digest=selected_identity_set_digest(
            inputs.selected_oracle_ids
        ),
        total_surface_count=len(surfaces),
        lens_group_counts=_lens_counts(groups),
        candidate_group_count=len(groups),
        opportunity_count=len(opportunities),
        file_descriptors=descriptors,
    )


def _write_manifest(root: Path, manifest: InventoryManifestV1) -> None:
    (root / "inventory-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )


def build_inventory_from_loaded_inputs(
    inputs: LoadedInventoryInputsV1,
    output_directory: str | Path,
) -> InventoryBuildResultV1:
    """Build and atomically publish one inventory from already loaded inputs."""

    output_path = Path(output_directory)
    if output_path.exists():
        raise ValueError("inventory output directory must not already exist")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_path.name}-",
            dir=str(output_path.parent),
        )
    )
    surfaces: tuple[SourceSurfaceV1, ...] = ()
    groups: tuple[CandidateGroupV1, ...] = ()
    opportunities: tuple[CapabilityOpportunityV1, ...] = ()
    try:
        surfaces = project_surfaces(inputs.selected_records)
        groups = group_surfaces(surfaces)
        opportunities = build_capability_opportunities(groups)
        manifest = _write_tree(
            staging,
            inputs,
            surfaces,
            groups,
            opportunities,
        )
        _write_manifest(staging, manifest)
        from .validate import validate_inventory

        validate_inventory(
            staging, expected_selected_count=len(inputs.selected_oracle_ids)
        )
        os.replace(staging, output_path)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    tree_digest = directory_digest(output_path)
    report = InventoryReportV1.from_wire(
        json.loads((output_path / "inventory-report.json").read_bytes())
    )
    return InventoryBuildResultV1(
        output_directory=output_path,
        manifest=manifest,
        report=report,
        surfaces=surfaces,
        groups=groups,
        opportunities=opportunities,
        output_tree_digest=tree_digest,
    )


def build_inventory(
    inputs: InventoryInputsV1,
    output_directory: str | Path,
) -> InventoryBuildResultV1:
    """Load explicit parent inputs, build, validate, and publish an inventory."""

    return build_inventory_from_loaded_inputs(
        load_inventory_inputs(inputs),
        output_directory,
    )


def compare_directories(
    first: str | Path,
    second: str | Path,
) -> tuple[bool, bool]:
    """Return exact file-set and byte parity for two inventory trees."""

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
    "INVENTORY_TREE_DOMAIN",
    "InventoryBuildResultV1",
    "build_inventory",
    "build_inventory_from_loaded_inputs",
    "compare_directories",
    "directory_digest",
]
