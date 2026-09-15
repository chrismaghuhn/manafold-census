"""Explicit, read-only parent-input loading for the M6-02 inventory."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..analysis.manifest import AnalysisManifestV1
from ..analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1
from ..analysis.validate import validate_analysis_closure
from ..canonical import JSONValue, canonical_json_bytes
from ..capability.manifest import M4OntologyManifestV1
from ..digest import sha256_bytes
from ..models import SourceLock
from ..structural.index import (
    SHARD_NAMES,
    StructuralIndexSummary,
    inspect_structural_index,
)
from ..structural.manifest import StructuralCardIndexManifestV1
from ..structural.model import StructuralCardRecordV1
from ..validation import validate_document
from ._common import census_release_id

CENSUS_0_1_RELEASE_ID = (
    "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
)
CENSUS_0_1_SOURCE_LOCK_DIGEST = (
    "4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd"
)
CENSUS_0_1_M1_MANIFEST_SHA256 = (
    "bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b"
)
CENSUS_0_1_M1_AGGREGATE_DIGEST = (
    "eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb"
)
CENSUS_0_1_M3_MANIFEST_SHA256 = (
    "f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f"
)
CENSUS_0_1_M4_MANIFEST_SHA256 = (
    "575634d352d95f5db9f5d96e7fb66ad4cc21560d49354ec90460adcf5e0019b4"
)


class InventoryInputError(ValueError):
    """Raised when explicit M6-02 parent inputs do not close."""


@dataclass(frozen=True, slots=True)
class InventoryInputsV1:
    source_lock_path: Path
    structural_output_directory: Path
    analysis_output_directory: Path
    m4_output_directory: Path
    parent_census_release_id: str
    expected_selected_count: int | None = 38_735

    def __post_init__(self) -> None:
        for field in (
            "source_lock_path",
            "structural_output_directory",
            "analysis_output_directory",
            "m4_output_directory",
        ):
            if not isinstance(getattr(self, field), Path):
                raise TypeError(f"{field} must be a pathlib.Path")
        census_release_id("parent_census_release_id", self.parent_census_release_id)
        if self.parent_census_release_id != CENSUS_0_1_RELEASE_ID:
            raise ValueError("M6-02 requires the Census 0.1 parent release")
        if self.expected_selected_count is not None and (
            type(self.expected_selected_count) is not int
            or self.expected_selected_count < 0
        ):
            raise ValueError("expected_selected_count must be non-negative or null")


@dataclass(frozen=True, slots=True)
class LoadedInventoryInputsV1:
    source_lock_digest: str
    source_lock_file_sha256: str
    m1_manifest_sha256: str
    m1_structural_aggregate_digest: str
    m3_manifest_sha256: str
    parent_m4_manifest_sha256: str
    parent_census_release_id: str
    m1_record_count: int
    m3_record_count: int
    selected_records: tuple[StructuralCardRecordV1, ...]
    selected_oracle_ids: tuple[str, ...]


def _read_canonical_object(
    path: Path, schema: str, label: str
) -> tuple[dict[str, object], bytes]:
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InventoryInputError(f"{label} cannot be read as JSON") from error
    if not isinstance(document, dict) or raw != canonical_json_bytes(document):
        raise InventoryInputError(f"{label} is not canonical JSON")
    try:
        validate_document(document, schema)
    except (OSError, TypeError, ValueError) as error:
        raise InventoryInputError(f"{label} is invalid") from error
    return cast(dict[str, object], document), raw


def _read_structural_records(
    output_directory: Path,
    persisted: StructuralCardIndexManifestV1,
) -> tuple[tuple[StructuralCardRecordV1, ...], StructuralIndexSummary]:
    records_root = output_directory / "records"
    if not records_root.is_dir():
        raise InventoryInputError("M1 structural records directory is missing")
    records: list[StructuralCardRecordV1] = []
    seen: set[str] = set()
    for shard in SHARD_NAMES:
        path = records_root / f"{shard}.jsonl"
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise InventoryInputError(f"M1 shard {shard} cannot be read") from error
        previous: str | None = None
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise InventoryInputError(f"M1 shard {shard} is missing final LF")
            try:
                record = StructuralCardRecordV1.from_wire(json.loads(line))
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as error:
                raise InventoryInputError(
                    f"M1 shard {shard} contains an invalid record"
                ) from error
            if line != canonical_json_bytes(record.to_wire()) + b"\n":
                raise InventoryInputError(f"M1 shard {shard} is not canonical JSONL")
            if record.oracle_id[0] != shard:
                raise InventoryInputError(f"M1 record is in the wrong shard {shard}")
            if previous is not None and record.oracle_id <= previous:
                raise InventoryInputError(f"M1 shard {shard} is not ordered")
            if record.oracle_id in seen:
                raise InventoryInputError("M1 contains a duplicate Oracle identity")
            seen.add(record.oracle_id)
            previous = record.oracle_id
            records.append(record)
    summary = inspect_structural_index(records_root)
    if StructuralCardIndexManifestV1.from_summary(summary) != persisted:
        raise InventoryInputError("M1 structural manifest does not match records")
    return tuple(records), summary


def _validate_m4_files(
    output_directory: Path,
    manifest: M4OntologyManifestV1,
) -> None:
    descriptors = (
        manifest.capability_file,
        manifest.review_file,
        manifest.relation_file,
        manifest.admissibility_file,
        manifest.evolution_file,
        *manifest.link_shards,
        *manifest.mapping_decision_shards,
    )
    expected = {"m4-ontology-manifest.json"} | {
        item.relative_path for item in descriptors
    }
    actual = {
        path.relative_to(output_directory).as_posix()
        for path in output_directory.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise InventoryInputError("M4 snapshot file set does not match its manifest")
    for descriptor in descriptors:
        path = output_directory / descriptor.relative_path
        raw = path.read_bytes()
        if sha256_bytes(raw) != descriptor.sha256:
            raise InventoryInputError(
                f"M4 descriptor digest mismatch: {descriptor.relative_path}"
            )
        if len(raw) != descriptor.byte_length:
            raise InventoryInputError(
                f"M4 descriptor byte length mismatch: {descriptor.relative_path}"
            )
        lines = raw.splitlines(keepends=True)
        if len(lines) != descriptor.record_count:
            raise InventoryInputError(
                f"M4 descriptor record count mismatch: {descriptor.relative_path}"
            )
        for line in lines:
            if not line.endswith(b"\n"):
                raise InventoryInputError(
                    f"M4 JSONL line is missing final LF: {descriptor.relative_path}"
                )
            try:
                document = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InventoryInputError(
                    f"M4 JSONL is not valid JSON: {descriptor.relative_path}"
                ) from error
            if line != canonical_json_bytes(cast(JSONValue, document)) + b"\n":
                raise InventoryInputError(
                    f"M4 JSONL is not canonical: {descriptor.relative_path}"
                )


def select_unresolved_records(
    structural_records: Iterable[StructuralCardRecordV1],
    analysis_records: Iterable[CardAnalysisRecordV1],
    *,
    expected_count: int | None = None,
) -> tuple[StructuralCardRecordV1, ...]:
    """Select exactly the M3 UNRESOLVED_ANALYSIS population by identity."""

    structural_by_id: dict[str, StructuralCardRecordV1] = {}
    for structural_record in structural_records:
        if not isinstance(structural_record, StructuralCardRecordV1):
            raise InventoryInputError("M1 records contain an unsupported value")
        if structural_record.oracle_id in structural_by_id:
            raise InventoryInputError("M1 contains a duplicate Oracle identity")
        structural_by_id[structural_record.oracle_id] = structural_record
    analysis_by_id: dict[str, CardAnalysisRecordV1] = {}
    for analysis_record in analysis_records:
        if not isinstance(analysis_record, CardAnalysisRecordV1):
            raise InventoryInputError("M3 records contain an unsupported value")
        oracle_id = analysis_record.source.oracle_id
        if oracle_id in analysis_by_id:
            raise InventoryInputError("M3 contains a duplicate Oracle identity")
        analysis_by_id[oracle_id] = analysis_record
    if set(structural_by_id) != set(analysis_by_id):
        raise InventoryInputError("M1/M3 Oracle identity sets differ")
    selected: list[StructuralCardRecordV1] = []
    for oracle_id in sorted(analysis_by_id):
        analysis = analysis_by_id[oracle_id]
        structural = structural_by_id[oracle_id]
        if (
            analysis.source.source_card_id != structural.source_card_id
            or analysis.source.source_record_sha256 != structural.source_record_sha256
        ):
            raise InventoryInputError(f"M1/M3 source identity mismatch: {oracle_id}")
        if analysis.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS:
            selected.append(structural)
    if expected_count is not None and len(selected) != expected_count:
        raise InventoryInputError(
            "selected unresolved population count mismatch: "
            f"expected={expected_count} actual={len(selected)}"
        )
    return tuple(selected)


def load_inventory_inputs(
    inputs: InventoryInputsV1,
) -> LoadedInventoryInputsV1:
    """Load and close the explicit M1/M3/M4 parent inputs without mutation."""

    if not isinstance(inputs, InventoryInputsV1):
        raise TypeError("inputs must be InventoryInputsV1")
    for path in (
        inputs.source_lock_path,
        inputs.structural_output_directory,
        inputs.analysis_output_directory,
        inputs.m4_output_directory,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    source_document, source_raw = _read_canonical_object(
        inputs.source_lock_path,
        "source-lock.v1.schema.json",
        "source lock",
    )
    source_lock = SourceLock.from_wire(source_document)
    if len(source_lock.artifacts) != 1:
        raise InventoryInputError("source lock must contain exactly one artifact")
    source_lock_digest = source_lock.digest()
    source_lock_file_sha256 = sha256_bytes(source_raw)
    if source_lock_digest != CENSUS_0_1_SOURCE_LOCK_DIGEST:
        raise InventoryInputError("source lock is not the Census 0.1 source lock")

    m1_document, m1_raw = _read_canonical_object(
        inputs.structural_output_directory / "structural-index-manifest.json",
        "structural-card-index-manifest.v1.schema.json",
        "M1 structural manifest",
    )
    m1_manifest = StructuralCardIndexManifestV1.from_wire(m1_document)
    structural_records, m1_summary = _read_structural_records(
        inputs.structural_output_directory,
        m1_manifest,
    )
    m1_manifest_sha256 = sha256_bytes(m1_raw)
    if m1_manifest_sha256 != CENSUS_0_1_M1_MANIFEST_SHA256:
        raise InventoryInputError("M1 manifest is not the Census 0.1 manifest")
    if m1_manifest.aggregate_digest != CENSUS_0_1_M1_AGGREGATE_DIGEST:
        raise InventoryInputError("M1 aggregate is not the Census 0.1 aggregate")

    m3_document, m3_raw = _read_canonical_object(
        inputs.analysis_output_directory / "analysis-manifest.json",
        "analysis-manifest.v1.schema.json",
        "M3 analysis manifest",
    )
    m3_manifest = AnalysisManifestV1.from_wire(m3_document)
    m3_manifest_sha256 = sha256_bytes(m3_raw)
    if m3_manifest_sha256 != CENSUS_0_1_M3_MANIFEST_SHA256:
        raise InventoryInputError("M3 manifest is not the Census 0.1 manifest")

    m4_document, m4_raw = _read_canonical_object(
        inputs.m4_output_directory / "m4-ontology-manifest.json",
        "capability-ontology-manifest.v1.schema.json",
        "M4 ontology manifest",
    )
    m4_manifest = M4OntologyManifestV1.from_wire(m4_document)
    parent_m4_manifest_sha256 = sha256_bytes(m4_raw)
    if parent_m4_manifest_sha256 != CENSUS_0_1_M4_MANIFEST_SHA256:
        raise InventoryInputError("M4 manifest is not the Census 0.1 manifest")
    if m4_manifest.digest() != parent_m4_manifest_sha256:
        raise InventoryInputError("M4 manifest digest does not match bytes")
    _validate_m4_files(inputs.m4_output_directory, m4_manifest)
    if m4_manifest.m3_analysis_manifest_sha256 != m3_manifest_sha256:
        raise InventoryInputError("M4 manifest is bound to a different M3 manifest")

    try:
        validated_records, _traces = validate_analysis_closure(
            inputs.structural_output_directory,
            inputs.analysis_output_directory,
            inputs.source_lock_path,
        )
    except (OSError, TypeError, ValueError) as error:
        raise InventoryInputError("M1/M3 closure validation failed") from error
    analysis_records = tuple(
        cast(CardAnalysisRecordV1, value) for value in validated_records.values
    )
    if len(structural_records) != m1_summary.record_count:
        raise InventoryInputError("M1 record count does not match its manifest")
    if len(analysis_records) != m3_manifest.record_count:
        raise InventoryInputError("M3 record count does not match its manifest")
    if m3_manifest.source_lock_digest != source_lock_digest:
        raise InventoryInputError("M3 source lock digest mismatch")

    selected = select_unresolved_records(
        structural_records,
        analysis_records,
        expected_count=inputs.expected_selected_count,
    )
    selected_ids = tuple(item.oracle_id for item in selected)
    return LoadedInventoryInputsV1(
        source_lock_digest=source_lock_digest,
        source_lock_file_sha256=source_lock_file_sha256,
        m1_manifest_sha256=m1_manifest_sha256,
        m1_structural_aggregate_digest=m1_manifest.aggregate_digest,
        m3_manifest_sha256=m3_manifest_sha256,
        parent_m4_manifest_sha256=parent_m4_manifest_sha256,
        parent_census_release_id=inputs.parent_census_release_id,
        m1_record_count=len(structural_records),
        m3_record_count=len(analysis_records),
        selected_records=tuple(selected),
        selected_oracle_ids=selected_ids,
    )


__all__ = [
    "CENSUS_0_1_M1_AGGREGATE_DIGEST",
    "CENSUS_0_1_M1_MANIFEST_SHA256",
    "CENSUS_0_1_M3_MANIFEST_SHA256",
    "CENSUS_0_1_M4_MANIFEST_SHA256",
    "CENSUS_0_1_RELEASE_ID",
    "CENSUS_0_1_SOURCE_LOCK_DIGEST",
    "InventoryInputError",
    "InventoryInputsV1",
    "LoadedInventoryInputsV1",
    "load_inventory_inputs",
    "select_unresolved_records",
]
