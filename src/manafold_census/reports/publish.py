"""Atomic publication and reread of derived Census reports and indexes."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from ..analysis.model import AnalysisOutcomeV1
from ..canonical import JSONValue, canonical_json_bytes
from ..capability.mapping import MappingDispositionV1, RequirementMappingDecisionV1
from ..digest import measure_file, sha256_bytes
from ..query.indexes import DerivedIndexRowsV1, validate_index_row
from ..release.manifest import (
    BUNDLE_MANIFEST_FILENAME,
    BundleComponentDescriptorV1,
    CensusBundleManifestV1,
)
from ..release.publish import file_descriptor_matches
from ..semantic.evidence import SourceRecordRefV1
from ..validation import validate_document
from .derive import MAPPING_QUEUE_ROW_SCHEMA, UNRESOLVED_ROW_SCHEMA
from .input import validated_bundle_inputs
from .model import (
    DERIVED_FILES,
    INDEX_DATA_FILES,
    INDEX_MANIFEST_FILENAME,
    MAPPING_REVIEW_QUEUE_FILENAME,
    REPORT_FILENAME,
    REPORT_INDEX_FILENAME,
    UNRESOLVED_ANALYSIS_FILENAME,
    DerivedFileDescriptorV1,
    IndexManifestV1,
    ReportIndexV1,
)
from .report_model import CensusReportV1, DerivedCensusBuildResultV1


def _component(
    manifest: CensusBundleManifestV1, role: str
) -> BundleComponentDescriptorV1:
    for item in manifest.authoritative_components:
        if item.role == role:
            return item
    raise ValueError(f"bundle is missing component role {role}")


def _write_jsonl(path: Path, rows: Sequence[dict[str, JSONValue]]) -> int:
    path.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))
    return len(rows)


def _measured_descriptor(
    root: Path, relative_path: str, record_count: int
) -> DerivedFileDescriptorV1:
    measurement = measure_file(root / relative_path)
    return DerivedFileDescriptorV1(
        relative_path,
        measurement.sha256,
        measurement.byte_length,
        record_count,
    )


def write_derived_files(
    root: Path,
    report: CensusReportV1,
    unresolved_rows: tuple[dict[str, JSONValue], ...],
    queue_rows: tuple[dict[str, JSONValue], ...],
    index_rows: DerivedIndexRowsV1,
) -> tuple[ReportIndexV1, IndexManifestV1]:
    """Write only the fixed M5-06 files and return their descriptors."""

    (root / "reports").mkdir()
    (root / "indexes").mkdir()
    report_path = root / REPORT_FILENAME
    report_path.write_bytes(canonical_json_bytes(report.to_wire()))
    unresolved_count = _write_jsonl(
        root / UNRESOLVED_ANALYSIS_FILENAME, unresolved_rows
    )
    queue_count = _write_jsonl(root / MAPPING_REVIEW_QUEUE_FILENAME, queue_rows)
    report_index = ReportIndexV1(
        report.census_manifest_sha256,
        report.census_release_id,
        (
            _measured_descriptor(root, REPORT_FILENAME, 1),
            _measured_descriptor(root, UNRESOLVED_ANALYSIS_FILENAME, unresolved_count),
            _measured_descriptor(root, MAPPING_REVIEW_QUEUE_FILENAME, queue_count),
        ),
    )
    (root / REPORT_INDEX_FILENAME).write_bytes(
        canonical_json_bytes(report_index.to_wire())
    )

    descriptors: list[DerivedFileDescriptorV1] = []
    row_map = index_rows.by_path()
    for relative_path in INDEX_DATA_FILES:
        count = _write_jsonl(root / relative_path, row_map[relative_path])
        descriptors.append(_measured_descriptor(root, relative_path, count))
    index_manifest = IndexManifestV1(
        report.census_manifest_sha256,
        report.census_release_id,
        tuple(descriptors),
    )
    (root / INDEX_MANIFEST_FILENAME).write_bytes(
        canonical_json_bytes(index_manifest.to_wire())
    )
    return report_index, index_manifest


def _validate_unresolved_row(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "source",
        "outcome",
        "persisted_requirement_ids",
        "persisted_requirement_count",
    }:
        raise ValueError("unresolved-analysis row has invalid properties")
    if value["schema"] != UNRESOLVED_ROW_SCHEMA:
        raise ValueError("unresolved-analysis row schema is invalid")
    if value["outcome"] != AnalysisOutcomeV1.UNRESOLVED_ANALYSIS.value:
        raise ValueError("unresolved-analysis row outcome is invalid")
    ids = value["persisted_requirement_ids"]
    if not isinstance(ids, list) or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("unresolved-analysis Requirement IDs are not canonical")
    if value["persisted_requirement_count"] != len(ids):
        raise ValueError("unresolved-analysis Requirement count is stale")
    SourceRecordRefV1.from_wire(value["source"])


def _validate_mapping_queue_row(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "requirement_id",
        "requirement_wire_digest",
        "decision",
    }:
        raise ValueError("mapping review queue row has invalid properties")
    if value["schema"] != MAPPING_QUEUE_ROW_SCHEMA:
        raise ValueError("mapping review queue row schema is invalid")
    decision = RequirementMappingDecisionV1.from_wire(value["decision"])
    if decision.requirement_id != value["requirement_id"]:
        raise ValueError("mapping review queue Requirement ID is stale")
    if decision.requirement_wire_digest != value["requirement_wire_digest"]:
        raise ValueError("mapping review queue Requirement digest is stale")
    if decision.disposition is MappingDispositionV1.MAPPED:
        raise ValueError("MAPPED decisions do not belong in the review queue")


def _row_order_key(relative_path: str, value: object) -> tuple[str, ...]:
    document = cast(dict[str, object], value)
    if relative_path == UNRESOLVED_ANALYSIS_FILENAME:
        source = cast(dict[str, str], document["source"])
        return (source["oracle_id"], source["source_card_id"])
    if relative_path == MAPPING_REVIEW_QUEUE_FILENAME:
        return (cast(str, document["requirement_id"]),)
    if relative_path == "indexes/cards-by-name.jsonl":
        return (
            cast(str, document["name"]),
            cast(str, document["oracle_id"]),
            cast(str, document["source_card_id"]),
        )
    if relative_path in {
        "indexes/cards-by-oracle-id.jsonl",
        "indexes/requirements-by-card.jsonl",
    }:
        return (cast(str, document["oracle_id"]),)
    if relative_path == "indexes/links-by-requirement.jsonl":
        return (cast(str, document["requirement_id"]),)
    if relative_path == "indexes/cards-by-capability.jsonl":
        return (canonical_json_bytes(document["capability"]).decode("utf-8"),)
    raise ValueError(f"unknown derived JSONL path: {relative_path}")


def _read_jsonl_rows(
    path: Path,
    relative_path: str,
    validator: Callable[[object], None],
) -> int:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise FileNotFoundError(f"missing derived artifact: {relative_path}") from error
    keys: list[tuple[str, ...]] = []
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError(f"{relative_path} is missing a final LF")
        try:
            value = json.loads(line)
            if line != canonical_json_bytes(value) + b"\n":
                raise ValueError("noncanonical JSONL")
            validator(value)
            keys.append(_row_order_key(relative_path, value))
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(f"{relative_path} contains an invalid row") from error
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ValueError(f"{relative_path} is not canonically ordered")
    return len(keys)


def _read_model(path: Path, parser: Any, schema: str) -> Any:
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path} cannot be read as JSON") from error
    if not isinstance(document, dict) or raw != canonical_json_bytes(document):
        raise ValueError(f"{path} is not canonical JSON")
    validate_document(document, schema)
    result = parser(document)
    if raw != canonical_json_bytes(result.to_wire()):
        raise ValueError(f"{path} changed during reread")
    return result


def validate_census_derived_output(
    output_directory: str | Path,
) -> DerivedCensusBuildResultV1:
    """Reread all derived files and verify their frozen bindings."""

    root = Path(output_directory)
    manifest, _lock, _corpus, reread = validated_bundle_inputs(
        root, allowed_extra_files=DERIVED_FILES
    )
    manifest_raw = (root / BUNDLE_MANIFEST_FILENAME).read_bytes()
    manifest_sha256 = sha256_bytes(manifest_raw)

    report_index = _read_model(
        root / REPORT_INDEX_FILENAME,
        ReportIndexV1.from_wire,
        "census-report.v1.schema.json",
    )
    index_manifest = _read_model(
        root / INDEX_MANIFEST_FILENAME,
        IndexManifestV1.from_wire,
        "census-index-manifest.v1.schema.json",
    )
    for value, label in (
        (report_index, "report index"),
        (index_manifest, "index manifest"),
    ):
        if value.census_manifest_sha256 != manifest_sha256:
            raise ValueError(f"{label} is not bound to the Census manifest")
        if value.census_release_id != manifest.census_release_id:
            raise ValueError(f"{label} release identity is stale")

    report = _read_model(
        root / REPORT_FILENAME,
        CensusReportV1.from_wire,
        "census-report.v1.schema.json",
    )
    if report.census_manifest_sha256 != manifest_sha256:
        raise ValueError("report is not bound to the Census manifest")
    if report.census_release_id != manifest.census_release_id:
        raise ValueError("report release identity is stale")
    if report.source_lock_digest != manifest.source_lock_digest:
        raise ValueError("report SourceLock identity is stale")
    m3_component = _component(manifest, "m3")
    m4_raw = (root / "inputs/m4/m4-ontology-manifest.json").read_bytes()
    m4_manifest = reread.manifest
    if report.m3_analysis_manifest_sha256 != m3_component.sha256:
        raise ValueError("report M3 identity is stale")
    if report.m4_manifest_sha256 != sha256_bytes(m4_raw):
        raise ValueError("report M4 identity is stale")
    if sha256_bytes(m4_raw) != m4_manifest.digest():
        raise ValueError("M4 manifest identity is stale")
    if report.requirement_set_digest != m4_manifest.requirement_set_digest:
        raise ValueError("report Requirement-set identity is stale")

    report_validators: dict[str, Callable[[object], None]] = {
        UNRESOLVED_ANALYSIS_FILENAME: _validate_unresolved_row,
        MAPPING_REVIEW_QUEUE_FILENAME: _validate_mapping_queue_row,
    }
    for descriptor in report_index.report_descriptors:
        path = root / descriptor.relative_path
        if not file_descriptor_matches(path, descriptor.sha256, descriptor.byte_length):
            raise ValueError(f"report descriptor mismatch: {descriptor.relative_path}")
        if descriptor.relative_path == REPORT_FILENAME:
            count = 1
        else:
            count = _read_jsonl_rows(
                path,
                descriptor.relative_path,
                report_validators[descriptor.relative_path],
            )
        if count != descriptor.record_count:
            raise ValueError(
                f"report descriptor count mismatch: {descriptor.relative_path}"
            )

    for descriptor in index_manifest.index_descriptors:
        path = root / descriptor.relative_path
        if not file_descriptor_matches(path, descriptor.sha256, descriptor.byte_length):
            raise ValueError(f"index descriptor mismatch: {descriptor.relative_path}")
        count = _read_jsonl_rows(
            path,
            descriptor.relative_path,
            _index_validator(descriptor.relative_path),
        )
        if count != descriptor.record_count:
            raise ValueError(
                f"index descriptor count mismatch: {descriptor.relative_path}"
            )
    return DerivedCensusBuildResultV1(root, report, report_index, index_manifest)


def _index_validator(relative_path: str) -> Callable[[object], None]:
    def validate(value: object) -> None:
        validate_index_row(relative_path, value)

    return validate


__all__ = [
    "validate_census_derived_output",
    "write_derived_files",
]
