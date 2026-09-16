"""Explicit, read-only parent-input loading for M6-03 prioritization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..digest import sha256_bytes
from ..inventory._common import census_release_id
from ..inventory.input import (
    InventoryInputsV1,
    LoadedInventoryInputsV1,
    load_inventory_inputs,
)
from ..inventory.model import (
    CandidateGroupV1,
    CapabilityOpportunityV1,
    SourceSurfaceV1,
)
from ..inventory.validate import (
    InventoryValidationError,
    validate_inventory_against_inputs,
)


class PrioritizationInputError(ValueError):
    """Raised when explicit M6-03 parent inputs do not close."""


@dataclass(frozen=True, slots=True)
class PrioritizationInputsV1:
    m6_02_output_directory: Path
    source_lock_path: Path
    structural_output_directory: Path
    analysis_output_directory: Path
    m4_output_directory: Path
    parent_census_release_id: str
    expected_opportunity_count: int | None = 10_732

    def __post_init__(self) -> None:
        for field in (
            "m6_02_output_directory",
            "source_lock_path",
            "structural_output_directory",
            "analysis_output_directory",
            "m4_output_directory",
        ):
            if not isinstance(getattr(self, field), Path):
                raise TypeError(f"{field} must be a pathlib.Path")
        census_release_id("parent_census_release_id", self.parent_census_release_id)
        if self.expected_opportunity_count is not None and (
            type(self.expected_opportunity_count) is not int
            or self.expected_opportunity_count < 0
        ):
            raise ValueError("expected_opportunity_count must be non-negative or null")


@dataclass(frozen=True, slots=True)
class LoadedPrioritizationInputsV1:
    inventory_inputs: LoadedInventoryInputsV1
    m6_02_manifest_sha256: str
    m6_02_opportunity_count: int
    m6_02_selected_identity_set_digest: str
    surfaces: tuple[SourceSurfaceV1, ...]
    groups: tuple[CandidateGroupV1, ...]
    opportunities: tuple[CapabilityOpportunityV1, ...]
    m4_active_family_ids: tuple[str, ...]


def _read_active_m4_families(m4_output_directory: Path) -> tuple[str, ...]:
    path = m4_output_directory / "capabilities.jsonl"
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PrioritizationInputError("M4 capabilities file cannot be read") from error
    families: set[str] = set()
    for line_number, line in enumerate(raw.splitlines(keepends=True), start=1):
        if not line.endswith(b"\n"):
            raise PrioritizationInputError(
                f"M4 capabilities line {line_number} is missing final LF"
            )
        try:
            document = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PrioritizationInputError(
                f"M4 capabilities line {line_number} is invalid"
            ) from error
        if not isinstance(document, dict):
            raise PrioritizationInputError("M4 capability record must be an object")
        if document.get("lifecycle") != "ACTIVE":
            continue
        family_id = document.get("capability_family_id")
        if not isinstance(family_id, str) or not family_id:
            raise PrioritizationInputError("M4 ACTIVE record lacks a family ID")
        families.add(family_id)
    return tuple(sorted(families))


def load_prioritization_inputs(
    inputs: PrioritizationInputsV1,
) -> LoadedPrioritizationInputsV1:
    """Load and close M6-02 plus M1/M3/M4 parents without mutation."""

    if not isinstance(inputs, PrioritizationInputsV1):
        raise TypeError("inputs must be PrioritizationInputsV1")
    for path in (
        inputs.m6_02_output_directory,
        inputs.source_lock_path,
        inputs.structural_output_directory,
        inputs.analysis_output_directory,
        inputs.m4_output_directory,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    inventory_inputs = InventoryInputsV1(
        source_lock_path=inputs.source_lock_path,
        structural_output_directory=inputs.structural_output_directory,
        analysis_output_directory=inputs.analysis_output_directory,
        m4_output_directory=inputs.m4_output_directory,
        parent_census_release_id=inputs.parent_census_release_id,
    )
    try:
        loaded_inventory = load_inventory_inputs(inventory_inputs)
    except (OSError, TypeError, ValueError) as error:
        raise PrioritizationInputError(
            "M6-03 parent M1/M3/M4 closure failed"
        ) from error
    try:
        validated = validate_inventory_against_inputs(
            inputs.m6_02_output_directory, loaded_inventory
        )
    except (InventoryValidationError, OSError, TypeError, ValueError) as error:
        raise PrioritizationInputError(
            "M6-02 parent output is not bound to explicit inputs"
        ) from error

    if inputs.expected_opportunity_count is not None and (
        len(validated.opportunities) != inputs.expected_opportunity_count
    ):
        raise PrioritizationInputError(
            "M6-02 parent Opportunity count mismatch: "
            f"expected={inputs.expected_opportunity_count} "
            f"actual={len(validated.opportunities)}"
        )
    manifest_path = inputs.m6_02_output_directory / "inventory-manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise PrioritizationInputError("M6-02 manifest cannot be read") from error
    families = _read_active_m4_families(inputs.m4_output_directory)
    return LoadedPrioritizationInputsV1(
        inventory_inputs=loaded_inventory,
        m6_02_manifest_sha256=sha256_bytes(manifest_bytes),
        m6_02_opportunity_count=len(validated.opportunities),
        m6_02_selected_identity_set_digest=(
            validated.manifest.selected_identity_set_digest
        ),
        surfaces=validated.surfaces,
        groups=validated.groups,
        opportunities=validated.opportunities,
        m4_active_family_ids=families,
    )


__all__ = [
    "LoadedPrioritizationInputsV1",
    "PrioritizationInputError",
    "PrioritizationInputsV1",
    "load_prioritization_inputs",
]
