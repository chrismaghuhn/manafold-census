"""Build and validate the generated Task-01 corpus artifact set."""

from __future__ import annotations

import filecmp
import gzip
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import REPRODUCTION_DOMAIN, domain_digest, measure_file
from ..models import (
    ArtifactManifest,
    DatasetManifest,
    SourceArtifact,
    SourceLock,
    StudySpec,
)
from ..validation import validate_document, validate_source_file
from .index import IndexSummary, build_record_index, inspect_record_index

DATASET_ID = "scryfall-oracle-corpus"
DATASET_VERSION = "1.0.0"
NORMALIZATION_PROFILE = "scryfall-oracle-record-index.v1"
STUDY_ID = "scryfall-oracle-record-index-build"
OPERATION = "scryfall-oracle-record-index.v1"
ARTIFACT_ID = "scryfall-oracle-record-index"
ARTIFACT_KIND = "census.oracle-record-index.v1"
REPORT_SCHEMA = "census.oracle-corpus-report.v1"
REPORT_PROVENANCE = "SOURCE_FACT"
SHARD_COUNT = 16


@dataclass(frozen=True, slots=True)
class BuildResult:
    """All deterministic values emitted by one corpus build."""

    output_dir: Path
    source_lock: SourceLock
    dataset: DatasetManifest
    study: StudySpec
    artifact: ArtifactManifest
    index: IndexSummary
    report: dict[str, JSONValue]


def load_source_lock(path: str | Path) -> SourceLock:
    """Load and validate one generic source lock from a repository file."""

    lock_path = Path(path)
    with lock_path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    validate_document(document, "source-lock.v1.schema.json")
    lock = SourceLock.from_wire(document)
    if len(lock.artifacts) != 1:
        raise ValueError("Task 01 requires exactly one locked source artifact")
    return lock


def _write_document(path: Path, document: dict[str, JSONValue], schema: str) -> None:
    validate_document(document, schema)
    path.write_bytes(canonical_json_bytes(document))


def _report_for(
    source_lock: SourceLock,
    dataset: DatasetManifest,
    study: StudySpec,
    artifact: ArtifactManifest,
    index: IndexSummary,
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
        "dataset_manifest_digest": dataset.digest(),
        "study_digest": study.digest(),
        "artifact_manifest_digest": artifact.digest(),
        "record_count": index.record_count,
        "unique_oracle_id_count": index.unique_oracle_id_count,
        "duplicate_oracle_id_count": index.duplicate_oracle_id_count,
        "shard_count": SHARD_COUNT,
        "shard_record_counts": cast(JSONValue, index.shard_record_counts),
        "aggregate_index_digest": index.aggregate_digest,
    }


def build_corpus(
    source_path: str | Path,
    source_lock_path: str | Path,
    output_dir: str | Path,
) -> BuildResult:
    """Build a complete deterministic corpus from one pinned source file."""

    source_lock = load_source_lock(source_lock_path)
    source_artifact = source_lock.artifacts[0]
    source_file = Path(source_path)
    validate_source_file(source_artifact, source_file)

    output_path = Path(output_dir)
    if output_path.exists() and not output_path.is_dir():
        raise ValueError("corpus output is not a directory")
    output_path.mkdir(parents=True, exist_ok=True)
    if any(output_path.iterdir()):
        raise ValueError("corpus output directory must be empty")

    index = build_record_index(source_file, output_path / "records")
    dataset = DatasetManifest(
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        source_lock_digest=source_lock.digest(),
        normalization_profile=NORMALIZATION_PROFILE,
        record_count=index.record_count,
    )
    study = StudySpec(
        study_id=STUDY_ID,
        dataset_refs=(DATASET_ID,),
        operation=OPERATION,
        parameters={
            "shard_count": SHARD_COUNT,
            "source_lock_digest": source_lock.digest(),
        },
    )
    artifact = ArtifactManifest(
        artifact_id=ARTIFACT_ID,
        artifact_kind=ARTIFACT_KIND,
        study_digest=study.digest(),
        content_sha256=index.aggregate_digest,
        byte_length=index.total_byte_length,
    )
    report = _report_for(source_lock, dataset, study, artifact, index)

    _write_document(
        output_path / "dataset-manifest.json",
        dataset.to_wire(),
        "dataset-manifest.v1.schema.json",
    )
    _write_document(
        output_path / "study-spec.json",
        study.to_wire(),
        "study-spec.v1.schema.json",
    )
    _write_document(
        output_path / "artifact-manifest.json",
        artifact.to_wire(),
        "artifact-manifest.v1.schema.json",
    )
    _write_document(
        output_path / "corpus-report.json",
        report,
        "oracle-corpus-report.v1.schema.json",
    )
    return BuildResult(
        output_dir=output_path,
        source_lock=source_lock,
        dataset=dataset,
        study=study,
        artifact=artifact,
        index=index,
        report=report,
    )


def _file_map(directory: Path) -> dict[str, Path]:
    return {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }


def _directory_digest(directory: Path) -> str:
    entries: list[dict[str, JSONValue]] = []
    for relative_path, path in sorted(_file_map(directory).items()):
        data = path.read_bytes()
        entries.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_length": len(data),
            }
        )
    return domain_digest(REPRODUCTION_DOMAIN, cast(JSONValue, entries))


def _synthetic_records() -> tuple[dict[str, JSONValue], ...]:
    return (
        {
            "object": "card",
            "oracle_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
            "id": "ffffffff-ffff-4fff-8fff-fffffffffff0",
            "name": "Synthetic F",
        },
        {
            "object": "card",
            "oracle_id": "00000000-0000-4000-8000-000000000000",
            "id": "00000000-0000-4000-8000-000000000001",
            "name": "Synthetic Zero",
        },
    )


def _write_synthetic_source(path: Path) -> None:
    with gzip.open(path, "wb") as stream:
        for record in _synthetic_records():
            stream.write(canonical_json_bytes(record) + b"\n")


def _write_synthetic_lock(source_path: Path, lock_path: Path) -> None:
    measurement = measure_file(source_path)
    lock = SourceLock(
        (
            SourceArtifact(
                source_id="11111111-1111-4111-8111-111111111111",
                locator="fixture://synthetic-oracle.jsonl.gz",
                sha256=measurement.sha256,
                byte_length=measurement.byte_length,
                media_type="application/gzip",
            ),
        )
    )
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))


def run_synthetic_reproduction() -> tuple[str, str]:
    """Build the small supported-format fixture twice and require byte parity."""

    with (
        tempfile.TemporaryDirectory(prefix="census-corpus-a-") as temp_a,
        tempfile.TemporaryDirectory(prefix="census-corpus-b-") as temp_b,
    ):
        root_a = Path(temp_a)
        root_b = Path(temp_b)
        source_path = root_a / "source.jsonl.gz"
        lock_path = root_a / "source-lock.json"
        _write_synthetic_source(source_path)
        _write_synthetic_lock(source_path, lock_path)
        output_a = root_a / "build"
        output_b = root_b / "build"
        build_corpus(source_path, lock_path, output_a)
        build_corpus(source_path, lock_path, output_b)
        files_a = _file_map(output_a)
        files_b = _file_map(output_b)
        if set(files_a) != set(files_b):
            raise RuntimeError("corpus reproduction file sets differ")
        for relative_path in sorted(files_a):
            if not filecmp.cmp(
                files_a[relative_path], files_b[relative_path], shallow=False
            ):
                raise RuntimeError(f"corpus reproduction differs: {relative_path}")
        digest_a = _directory_digest(output_a)
        digest_b = _directory_digest(output_b)
        if digest_a != digest_b:
            raise RuntimeError("corpus reproduction digests differ")
        return digest_a, digest_b


def validate_corpus_output(output_dir: str | Path) -> str:
    """Validate generated index/manifests and return the aggregate index digest."""

    output_path = Path(output_dir)
    index = inspect_record_index(output_path / "records")
    with (output_path / "dataset-manifest.json").open("r", encoding="utf-8") as stream:
        dataset_document = json.load(stream)
    with (output_path / "study-spec.json").open("r", encoding="utf-8") as stream:
        study_document = json.load(stream)
    with (output_path / "artifact-manifest.json").open("r", encoding="utf-8") as stream:
        artifact_document = json.load(stream)
    with (output_path / "corpus-report.json").open("r", encoding="utf-8") as stream:
        report_document = json.load(stream)
    validate_document(dataset_document, "dataset-manifest.v1.schema.json")
    validate_document(study_document, "study-spec.v1.schema.json")
    validate_document(artifact_document, "artifact-manifest.v1.schema.json")
    validate_document(report_document, "oracle-corpus-report.v1.schema.json")
    dataset = DatasetManifest.from_wire(dataset_document)
    study = StudySpec.from_wire(study_document)
    artifact = ArtifactManifest.from_wire(artifact_document)
    if dataset.record_count != index.record_count:
        raise ValueError("corpus dataset record count does not match index")
    if artifact.content_sha256 != index.aggregate_digest:
        raise ValueError("corpus artifact aggregate digest mismatch")
    if artifact.byte_length != index.total_byte_length:
        raise ValueError("corpus artifact byte length mismatch")
    if artifact.study_digest != study.digest():
        raise ValueError("corpus artifact study digest mismatch")
    if report_document["aggregate_index_digest"] != index.aggregate_digest:
        raise ValueError("corpus report aggregate digest mismatch")
    if report_document["record_count"] != index.record_count:
        raise ValueError("corpus report record count mismatch")
    if report_document["unique_oracle_id_count"] != index.unique_oracle_id_count:
        raise ValueError("corpus report unique Oracle ID count mismatch")
    if report_document["duplicate_oracle_id_count"] != index.duplicate_oracle_id_count:
        raise ValueError("corpus report duplicate Oracle ID count mismatch")
    if report_document["shard_count"] != SHARD_COUNT:
        raise ValueError("corpus report shard count mismatch")
    if report_document["shard_record_counts"] != index.shard_record_counts:
        raise ValueError("corpus report shard counts mismatch")
    if report_document["source_lock_digest"] != dataset.source_lock_digest:
        raise ValueError("corpus report source lock digest mismatch")
    if report_document["dataset_manifest_digest"] != dataset.digest():
        raise ValueError("corpus report dataset digest mismatch")
    if report_document["study_digest"] != study.digest():
        raise ValueError("corpus report study digest mismatch")
    if report_document["artifact_manifest_digest"] != artifact.digest():
        raise ValueError("corpus report artifact digest mismatch")
    return index.aggregate_digest


def build_pinned_corpus(
    repository_root: str | Path, output_dir: str | Path
) -> BuildResult:
    """Build from the repository's committed lock and its ignored source cache."""

    root = Path(repository_root)
    lock_path = root / "source-locks" / "scryfall-oracle-v1.json"
    lock = load_source_lock(lock_path)
    source_id = lock.artifacts[0].source_id
    source_path = root / ".cache" / "sources" / "scryfall" / f"{source_id}.jsonl.gz"
    return build_corpus(source_path, lock_path, output_dir)
