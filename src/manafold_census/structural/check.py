"""Independent fail-closed validation of a structural census output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from ..models import ArtifactManifest, DatasetManifest, SourceLock, StudySpec
from ..source.transfer import cache_path_for
from ..validation import validate_document, validate_source_file
from .extract import StructuralExtractionError, iter_structural_records
from .index import (
    SHARD_NAMES,
    StructuralIndexError,
    StructuralIndexSummary,
    inspect_structural_index,
)
from .manifest import StructuralCardIndexManifestV1
from .model import StructuralCardRecordV1
from .report import (
    REPORT_PROVENANCE,
    REPORT_SCHEMA,
    StructuralStatistics,
    collect_structural_statistics,
)

PINNED_SOURCE_LOCK_DIGEST = (
    "4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd"
)
DATASET_ID = "scryfall-oracle-structural-census"
DATASET_VERSION = "1.0.0"
NORMALIZATION_PROFILE = "scryfall-oracle-structural-v1"
STUDY_ID = "scryfall-oracle-structural-build"
OPERATION = "scryfall-oracle-structural.v1"
ARTIFACT_ID = "scryfall-oracle-structural-index"
ARTIFACT_KIND = "census.structural-card-index.v1"
SHARD_COUNT = 16


class StructuralCheckError(ValueError):
    """Raised when generated structural output fails independent closure."""


def _load_source_lock(path: str | Path) -> SourceLock:
    lock_path = Path(path)
    try:
        document = json.loads(lock_path.read_bytes())
        validate_document(document, "source-lock.v1.schema.json")
        lock = SourceLock.from_wire(document)
    except (OSError, TypeError, ValueError) as error:
        raise StructuralCheckError(f"source lock is invalid: {error}") from error
    if len(lock.artifacts) != 1:
        raise StructuralCheckError(
            "source lock must contain exactly one source artifact"
        )
    return lock


def _read_canonical_document(path: Path) -> dict[str, object]:
    try:
        raw_bytes = path.read_bytes()
        document = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StructuralCheckError(f"{path.name} is not valid JSON") from error
    if not isinstance(document, dict):
        raise StructuralCheckError(f"{path.name} must contain an object")
    if raw_bytes != canonical_json_bytes(cast(JSONValue, document)):
        raise StructuralCheckError(f"{path.name} is not canonical JSON")
    return document


def _validate_structural_record_schemas(records_dir: Path) -> None:
    """Validate every actual JSONL object against the normative card schema."""

    if not records_dir.is_dir():
        raise StructuralCheckError("structural records directory does not exist")
    for path in sorted(records_dir.glob("*.jsonl")):
        try:
            stream = path.open("rb")
        except OSError as error:
            raise StructuralCheckError(
                f"could not open structural shard {path.name}"
            ) from error
        with stream:
            while raw_line := stream.readline():
                if not raw_line.endswith(b"\n"):
                    raise StructuralCheckError(f"shard {path.name} is missing final LF")
                try:
                    document = json.loads(raw_line)
                    validate_document(document, "structural-card.v1.schema.json")
                except (TypeError, ValueError, UnicodeDecodeError) as error:
                    raise StructuralCheckError(str(error)) from error


def _read_actual_records(
    records_dir: Path,
) -> tuple[StructuralIndexSummary, dict[str, StructuralCardRecordV1]]:
    _validate_structural_record_schemas(records_dir)
    try:
        index = inspect_structural_index(records_dir)
    except StructuralIndexError as error:
        raise StructuralCheckError(str(error)) from error
    records: dict[str, StructuralCardRecordV1] = {}
    for shard in SHARD_NAMES:
        path = records_dir / f"{shard}.jsonl"
        try:
            stream = path.open("rb")
        except OSError as error:
            raise StructuralCheckError(f"shard {shard} could not be opened") from error
        with stream:
            while raw_line := stream.readline():
                if not raw_line.endswith(b"\n"):
                    raise StructuralCheckError(f"shard {shard} is missing final LF")
                try:
                    document = json.loads(raw_line)
                    record = StructuralCardRecordV1.from_wire(document)
                except (TypeError, ValueError, UnicodeDecodeError) as error:
                    raise StructuralCheckError(
                        f"shard {shard} contains an invalid structural record"
                    ) from error
                if raw_line != canonical_json_bytes(record.to_wire()) + b"\n":
                    raise StructuralCheckError(
                        f"shard {shard} contains noncanonical JSONL"
                    )
                if record.oracle_id in records:
                    raise StructuralCheckError(
                        f"duplicate structural oracle_id: {record.oracle_id}"
                    )
                records[record.oracle_id] = record
    return index, records


def _read_expected_records(
    source_path: Path,
) -> dict[str, StructuralCardRecordV1]:
    expected: dict[str, StructuralCardRecordV1] = {}
    try:
        records = iter_structural_records(source_path)
        for record in records:
            if record.oracle_id in expected:
                raise StructuralCheckError(
                    f"duplicate source oracle_id: {record.oracle_id}"
                )
            expected[record.oracle_id] = record
    except StructuralCheckError:
        raise
    except StructuralExtractionError as error:
        raise StructuralCheckError(str(error)) from error
    return expected


def _validate_output_file_set(output_path: Path) -> None:
    if not output_path.is_dir():
        raise StructuralCheckError("structural output directory does not exist")
    expected = {
        "records",
        "structural-index-manifest.json",
        "dataset-manifest.json",
        "study-spec.json",
        "artifact-manifest.json",
        "structural-report.json",
    }
    actual = {path.name for path in output_path.iterdir()}
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unexpected:
        raise StructuralCheckError(f"unexpected output file: {unexpected[0]}")
    if missing:
        raise StructuralCheckError(f"missing output file: {missing[0]}")


def _require_fixed_lifecycle_identities(
    dataset: DatasetManifest,
    study: StudySpec,
    artifact: ArtifactManifest,
    source_lock: SourceLock,
    index: StructuralIndexSummary,
) -> None:
    if dataset.dataset_id != DATASET_ID:
        raise StructuralCheckError("dataset id mismatch")
    if dataset.dataset_version != DATASET_VERSION:
        raise StructuralCheckError("dataset version mismatch")
    if dataset.normalization_profile != NORMALIZATION_PROFILE:
        raise StructuralCheckError("normalization profile mismatch")
    if dataset.source_lock_digest != source_lock.digest():
        raise StructuralCheckError("dataset source lock digest mismatch")
    if dataset.record_count != index.record_count:
        raise StructuralCheckError("dataset record count mismatch")
    if study.study_id != STUDY_ID or study.operation != OPERATION:
        raise StructuralCheckError("study identity mismatch")
    if study.dataset_refs != (DATASET_ID,):
        raise StructuralCheckError("study dataset reference mismatch")
    if study.to_wire()["parameters"] != {
        "shard_count": SHARD_COUNT,
        "source_lock_digest": source_lock.digest(),
    }:
        raise StructuralCheckError("study parameters mismatch")
    if artifact.artifact_id != ARTIFACT_ID:
        raise StructuralCheckError("artifact id mismatch")
    if artifact.artifact_kind != ARTIFACT_KIND:
        raise StructuralCheckError("artifact kind mismatch")
    if artifact.study_digest != study.digest():
        raise StructuralCheckError("artifact study digest mismatch")


def _expected_report(
    source_lock: SourceLock,
    dataset: DatasetManifest,
    study: StudySpec,
    artifact: ArtifactManifest,
    index: StructuralIndexSummary,
    statistics: StructuralStatistics,
) -> dict[str, JSONValue]:
    source = source_lock.artifacts[0]
    return {
        "schema": REPORT_SCHEMA,
        "record_provenance": REPORT_PROVENANCE,
        "source_lock_digest": source_lock.digest(),
        "source_id": source.source_id,
        "source_locator": source.locator,
        "source_artifact_sha256": source.sha256,
        "source_artifact_byte_length": source.byte_length,
        "source_media_type": source.media_type,
        "task01_record_identity_parity": True,
        "task01_identity_count": statistics.record_count,
        "structural_record_count": statistics.record_count,
        "unique_oracle_id_count": statistics.unique_oracle_id_count,
        "duplicate_oracle_id_count": statistics.duplicate_oracle_id_count,
        "missing_oracle_id_count": 0,
        "extra_oracle_id_count": 0,
        "cards_with_faces": statistics.cards_with_faces,
        "cards_without_faces": statistics.cards_without_faces,
        "total_face_count": statistics.total_face_count,
        "max_face_count": statistics.max_face_count,
        "face_count_distribution": dict(statistics.face_count_distribution),
        "layout_counts": dict(statistics.layout_counts),
        "top_level_field_presence": dict(statistics.top_level_field_presence),
        "face_field_presence": dict(statistics.face_field_presence),
        "shard_count": SHARD_COUNT,
        "shard_record_counts": cast(JSONValue, index.shard_record_counts),
        "structural_index_aggregate_digest": index.aggregate_digest,
        "structural_index_manifest_sha256": artifact.content_sha256,
        "structural_index_manifest_byte_length": artifact.byte_length,
        "dataset_manifest_digest": dataset.digest(),
        "study_digest": study.digest(),
        "artifact_manifest_digest": artifact.digest(),
    }


def validate_structural_output(
    output_dir: str | Path,
    source_path: str | Path,
    source_lock_path: str | Path,
) -> str:
    """Reconstruct and validate all structural output facts independently."""

    output_path = Path(output_dir)
    source_file = Path(source_path)
    source_lock = _load_source_lock(source_lock_path)
    source_artifact = source_lock.artifacts[0]
    try:
        validate_source_file(source_artifact, source_file)
    except (OSError, ValueError) as error:
        raise StructuralCheckError(str(error)) from error
    _validate_output_file_set(output_path)

    index, actual_records = _read_actual_records(output_path / "records")
    expected_records = _read_expected_records(source_file)
    missing = sorted(set(expected_records) - set(actual_records))
    extra = sorted(set(actual_records) - set(expected_records))
    if missing:
        raise StructuralCheckError(f"missing structural oracle_id: {missing[0]}")
    if extra:
        raise StructuralCheckError(f"extra structural oracle_id: {extra[0]}")
    if len(actual_records) != len(expected_records):
        raise StructuralCheckError("structural record counts do not match")
    for oracle_id, expected in expected_records.items():
        actual = actual_records[oracle_id]
        if actual.task01_identity() != expected.task01_identity():
            raise StructuralCheckError(f"Task-01 identity parity mismatch: {oracle_id}")
        if actual != expected:
            raise StructuralCheckError(f"structural projection mismatch: {oracle_id}")

    dataset_document = _read_canonical_document(output_path / "dataset-manifest.json")
    study_document = _read_canonical_document(output_path / "study-spec.json")
    artifact_document = _read_canonical_document(output_path / "artifact-manifest.json")
    index_manifest_document = _read_canonical_document(
        output_path / "structural-index-manifest.json"
    )
    report_document = _read_canonical_document(output_path / "structural-report.json")
    try:
        validate_document(dataset_document, "dataset-manifest.v1.schema.json")
        validate_document(study_document, "study-spec.v1.schema.json")
        validate_document(artifact_document, "artifact-manifest.v1.schema.json")
        validate_document(
            index_manifest_document,
            "structural-card-index-manifest.v1.schema.json",
        )
        validate_document(report_document, "structural-card-report.v1.schema.json")
        dataset = DatasetManifest.from_wire(dataset_document)
        study = StudySpec.from_wire(study_document)
        artifact = ArtifactManifest.from_wire(artifact_document)
        index_manifest = StructuralCardIndexManifestV1.from_wire(
            index_manifest_document
        )
    except (TypeError, ValueError) as error:
        raise StructuralCheckError(str(error)) from error

    expected_manifest = StructuralCardIndexManifestV1.from_summary(index)
    if index_manifest != expected_manifest:
        raise StructuralCheckError("structural index manifest mismatch")
    manifest_bytes = canonical_json_bytes(cast(JSONValue, index_manifest_document))
    if artifact.content_sha256 != sha256_bytes(manifest_bytes):
        raise StructuralCheckError("ArtifactManifest content byte digest mismatch")
    if artifact.byte_length != len(manifest_bytes):
        raise StructuralCheckError("ArtifactManifest content byte length mismatch")
    _require_fixed_lifecycle_identities(dataset, study, artifact, source_lock, index)

    statistics = collect_structural_statistics(
        expected_records.values(),
        index.shard_record_counts,
        task01_identity_parity=True,
        task01_identity_count=len(expected_records),
    )
    expected_report = _expected_report(
        source_lock, dataset, study, artifact, index, statistics
    )
    if cast(JSONValue, report_document) != expected_report:
        raise StructuralCheckError("structural report does not match reconstruction")
    return index.aggregate_digest


def validate_pinned_structural_output(
    repository_root: str | Path,
    output_dir: str | Path,
) -> str:
    """Validate output against the frozen lock and exact local cache bytes."""

    root = Path(repository_root)
    lock_path = root / "source-locks" / "scryfall-oracle-v1.json"
    source_lock = _load_source_lock(lock_path)
    if source_lock.digest() != PINNED_SOURCE_LOCK_DIGEST:
        raise StructuralCheckError("pinned source lock digest mismatch")
    source_path = cache_path_for(
        root / ".cache" / "sources" / "scryfall",
        source_lock.artifacts[0].sha256,
    )
    return validate_structural_output(output_dir, source_path, lock_path)
