"""Independent validation for M6-02 non-authoritative output trees."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import measure_file
from .grouping import build_capability_opportunities, group_surfaces
from .identity import selected_identity_set_digest, source_surface_id
from .input import LoadedInventoryInputsV1
from .model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    InventoryManifestV1,
    InventoryReportV1,
    SourceSurfaceV1,
    WorklistEntryV1,
)
from .report import build_report, worklist_sort_key

EXPECTED_FILES = frozenset(
    {
        "inventory-manifest.json",
        "inventory-report.json",
        "surfaces.jsonl",
        "candidate-groups.jsonl",
        "capability-opportunities.jsonl",
        "worklist.jsonl",
    }
)


class InventoryValidationError(ValueError):
    """Raised when an inventory tree is not canonical or closed."""


class _WireValue(Protocol):
    def to_wire(self) -> dict[str, JSONValue]: ...


@dataclass(frozen=True, slots=True)
class InventoryValidationResultV1:
    output_directory: Path
    manifest: InventoryManifestV1
    report: InventoryReportV1
    surfaces: tuple[SourceSurfaceV1, ...]
    groups: tuple[CandidateGroupV1, ...]
    opportunities: tuple[CapabilityOpportunityV1, ...]
    worklist: tuple[WorklistEntryV1, ...]
    output_tree_digest: str


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InventoryValidationError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict) or raw != canonical_json_bytes(value):
        raise InventoryValidationError(f"{label} is not canonical JSON")
    return cast(dict[str, object], value)


def _read_jsonl[WireT: _WireValue](
    path: Path,
    parser: Callable[[object], WireT],
    label: str,
) -> tuple[WireT, ...]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise InventoryValidationError(f"{label} cannot be read") from error
    values: list[WireT] = []
    for line_number, line in enumerate(raw.splitlines(keepends=True), start=1):
        if not line.endswith(b"\n"):
            raise InventoryValidationError(
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
            raise InventoryValidationError(
                f"{label} line {line_number} is invalid"
            ) from error
        if line != canonical_json_bytes(cast(JSONValue, value.to_wire())) + b"\n":
            raise InventoryValidationError(
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
    from ..digest import domain_digest

    return domain_digest(
        "census.m6-02-inventory-tree.v1",
        cast(JSONValue, entries),
    )


def _validate_surface_ids(surfaces: tuple[SourceSurfaceV1, ...]) -> None:
    ids: set[str] = set()
    for surface in surfaces:
        if surface.surface_id in ids:
            raise InventoryValidationError("duplicate surface_id")
        ids.add(surface.surface_id)
        expected = source_surface_id(
            oracle_id=surface.oracle_id,
            source_card_id=surface.source_card_id,
            source_record_sha256=surface.source_record_sha256,
            scope=surface.scope.value,
            face_index=surface.face_index,
            line_index=surface.line_index,
            raw_text=surface.raw_text,
        )
        if surface.surface_id != expected:
            raise InventoryValidationError("surface identity digest mismatch")


def _descriptor_counts(
    root: Path,
    manifest: InventoryManifestV1,
    counts: dict[str, int],
) -> None:
    descriptor_paths = {item.relative_path for item in manifest.file_descriptors}
    expected_paths = EXPECTED_FILES - {"inventory-manifest.json"}
    if descriptor_paths != expected_paths:
        raise InventoryValidationError("manifest descriptor file set mismatch")
    for descriptor in manifest.file_descriptors:
        path = root / descriptor.relative_path
        if not path.is_file():
            raise InventoryValidationError(
                f"missing descriptor file: {descriptor.relative_path}"
            )
        measurement = measure_file(path)
        if (
            descriptor.sha256 != measurement.sha256
            or descriptor.byte_length != measurement.byte_length
        ):
            raise InventoryValidationError(
                f"stale descriptor: {descriptor.relative_path}"
            )
        if descriptor.record_count != counts[descriptor.relative_path]:
            raise InventoryValidationError(
                f"stale record count: {descriptor.relative_path}"
            )


def validate_inventory(
    output_directory: str | Path,
    *,
    expected_selected_count: int | None = None,
    expected_surfaces: tuple[SourceSurfaceV1, ...] | None = None,
) -> InventoryValidationResultV1:
    """Validate one complete canonical inventory tree without external inputs."""

    root = Path(output_directory)
    if not root.is_dir():
        raise InventoryValidationError("inventory output directory does not exist")
    if _file_set(root) != EXPECTED_FILES:
        raise InventoryValidationError("inventory output file set mismatch")

    manifest_document = _read_object(
        root / "inventory-manifest.json", "inventory manifest"
    )
    try:
        manifest = InventoryManifestV1.from_wire(manifest_document)
    except (TypeError, ValueError) as error:
        raise InventoryValidationError("inventory manifest is invalid") from error

    surfaces = _read_jsonl(
        root / "surfaces.jsonl",
        SourceSurfaceV1.from_wire,
        "surfaces.jsonl",
    )
    groups = _read_jsonl(
        root / "candidate-groups.jsonl",
        CandidateGroupV1.from_wire,
        "candidate-groups.jsonl",
    )
    opportunities = _read_jsonl(
        root / "capability-opportunities.jsonl",
        CapabilityOpportunityV1.from_wire,
        "capability-opportunities.jsonl",
    )
    worklist = _read_jsonl(
        root / "worklist.jsonl",
        WorklistEntryV1.from_wire,
        "worklist.jsonl",
    )
    report_document = _read_object(root / "inventory-report.json", "inventory report")
    try:
        report = InventoryReportV1.from_wire(report_document)
    except (TypeError, ValueError) as error:
        raise InventoryValidationError("inventory report is invalid") from error

    _validate_surface_ids(surfaces)
    reconstruction_surfaces = surfaces
    if expected_surfaces is not None:
        if surfaces != expected_surfaces:
            raise InventoryValidationError(
                "persisted surfaces do not match source surface projection"
            )
        reconstruction_surfaces = expected_surfaces
    selected_ids = tuple(sorted({item.oracle_id for item in surfaces}))
    if manifest.selected_identity_count != len(selected_ids):
        raise InventoryValidationError(
            "selected identity count does not match surfaces"
        )
    if manifest.selected_identity_set_digest != selected_identity_set_digest(
        selected_ids
    ):
        raise InventoryValidationError("selected identity set digest mismatch")
    if (
        expected_selected_count is not None
        and len(selected_ids) != expected_selected_count
    ):
        raise InventoryValidationError(
            "selected identity count does not match expected population"
        )

    expected_groups = group_surfaces(reconstruction_surfaces)
    if tuple(item.to_wire() for item in groups) != tuple(
        item.to_wire() for item in expected_groups
    ):
        raise InventoryValidationError("candidate groups do not match surfaces")
    expected_opportunities = build_capability_opportunities(groups)
    if tuple(item.to_wire() for item in opportunities) != tuple(
        item.to_wire() for item in expected_opportunities
    ):
        raise InventoryValidationError(
            "Capability Opportunities do not match candidate groups"
        )
    expected_worklist = tuple(
        WorklistEntryV1(
            group_id=group.group_id,
            grouping_lens=group.grouping_lens,
            distinct_oracle_identity_count=group.distinct_oracle_identity_count,
            surface_occurrence_count=group.surface_occurrence_count,
            recurrence_status=group.recurrence_status,
        )
        for group in sorted(groups, key=worklist_sort_key)
    )
    if tuple(item.to_wire() for item in worklist) != tuple(
        item.to_wire() for item in expected_worklist
    ):
        raise InventoryValidationError("worklist does not match candidate groups")

    lens_counts: dict[str, int] = {}
    for group in groups:
        lens_counts[group.grouping_lens.value] = (
            lens_counts.get(group.grouping_lens.value, 0) + 1
        )
    if manifest.lens_group_counts != tuple(sorted(lens_counts.items())):
        raise InventoryValidationError("manifest lens counts are stale")
    if manifest.total_surface_count != len(surfaces):
        raise InventoryValidationError("manifest surface count is stale")
    if manifest.candidate_group_count != len(groups):
        raise InventoryValidationError("manifest group count is stale")
    if manifest.opportunity_count != len(opportunities):
        raise InventoryValidationError("manifest Opportunity count is stale")

    report_inputs = LoadedInventoryInputsV1(
        source_lock_digest=manifest.source_lock_digest,
        source_lock_file_sha256=manifest.source_lock_file_sha256,
        m1_manifest_sha256=manifest.m1_manifest_sha256,
        m1_structural_aggregate_digest=manifest.m1_structural_aggregate_digest,
        m3_manifest_sha256=manifest.m3_manifest_sha256,
        parent_m4_manifest_sha256=manifest.parent_m4_manifest_sha256,
        parent_census_release_id=manifest.parent_census_release_id,
        m1_record_count=0,
        m3_record_count=0,
        selected_records=(),
        selected_oracle_ids=tuple(
            sorted({item.oracle_id for item in reconstruction_surfaces})
        ),
    )
    expected_report = build_report(report_inputs, surfaces, groups, opportunities)
    if report.to_wire() != expected_report.to_wire():
        raise InventoryValidationError("inventory report does not match artifacts")

    _descriptor_counts(
        root,
        manifest,
        {
            "surfaces.jsonl": len(surfaces),
            "candidate-groups.jsonl": len(groups),
            "capability-opportunities.jsonl": len(opportunities),
            "worklist.jsonl": len(worklist),
            "inventory-report.json": 1,
        },
    )
    return InventoryValidationResultV1(
        output_directory=root,
        manifest=manifest,
        report=report,
        surfaces=surfaces,
        groups=groups,
        opportunities=opportunities,
        worklist=worklist,
        output_tree_digest=_tree_digest(root),
    )


def validate_inventory_against_inputs(
    output_directory: str | Path,
    inputs: LoadedInventoryInputsV1,
) -> InventoryValidationResultV1:
    """Validate internal artifacts and bind them to explicit parent inputs."""

    from .projection import project_surfaces

    expected_surfaces = project_surfaces(inputs.selected_records)
    result = validate_inventory(
        output_directory,
        expected_selected_count=len(inputs.selected_oracle_ids),
        expected_surfaces=expected_surfaces,
    )
    manifest = result.manifest
    expected = (
        inputs.source_lock_digest,
        inputs.source_lock_file_sha256,
        inputs.m1_manifest_sha256,
        inputs.m1_structural_aggregate_digest,
        inputs.m3_manifest_sha256,
        inputs.parent_m4_manifest_sha256,
        inputs.parent_census_release_id,
        len(inputs.selected_oracle_ids),
        selected_identity_set_digest(inputs.selected_oracle_ids),
    )
    actual = (
        manifest.source_lock_digest,
        manifest.source_lock_file_sha256,
        manifest.m1_manifest_sha256,
        manifest.m1_structural_aggregate_digest,
        manifest.m3_manifest_sha256,
        manifest.parent_m4_manifest_sha256,
        manifest.parent_census_release_id,
        manifest.selected_identity_count,
        manifest.selected_identity_set_digest,
    )
    if actual != expected:
        raise InventoryValidationError("inventory manifest is not bound to inputs")
    actual_ids = tuple(sorted({item.oracle_id for item in result.surfaces}))
    if actual_ids != tuple(sorted(inputs.selected_oracle_ids)):
        raise InventoryValidationError(
            "inventory selected identities differ from inputs"
        )
    return result


__all__ = [
    "EXPECTED_FILES",
    "InventoryValidationError",
    "InventoryValidationResultV1",
    "validate_inventory",
    "validate_inventory_against_inputs",
]
