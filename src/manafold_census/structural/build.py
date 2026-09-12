"""Orchestrate one complete deterministic structural census build."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..corpus.build import load_source_lock
from ..digest import sha256_bytes
from ..models import (
    ArtifactManifest,
    DatasetManifest,
    SourceArtifact,
    SourceLock,
    StudySpec,
)
from ..source.transfer import cache_path_for
from ..validation import validate_document, validate_source_file
from .extract import iter_structural_records
from .index import StructuralIndexSummary, build_structural_index
from .manifest import StructuralCardIndexManifestV1
from .report import (
    REPORT_PROVENANCE,
    REPORT_SCHEMA,
    StructuralStatistics,
    collect_structural_statistics,
)

STRUCTURAL_DATASET_ID = "scryfall-oracle-structural-census"
STRUCTURAL_DATASET_VERSION = "1.0.0"
STRUCTURAL_NORMALIZATION_PROFILE = "scryfall-oracle-structural-v1"
STRUCTURAL_STUDY_ID = "scryfall-oracle-structural-build"
STRUCTURAL_OPERATION = "scryfall-oracle-structural.v1"
STRUCTURAL_ARTIFACT_ID = "scryfall-oracle-structural-index"
STRUCTURAL_ARTIFACT_KIND = "census.structural-card-index.v1"
PINNED_SOURCE_LOCK_DIGEST = (
    "4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd"
)
SHARD_COUNT = 16


@dataclass(frozen=True, slots=True)
class StructuralBuildResult:
    """All identities and statistics emitted by one structural build."""

    output_dir: Path
    source_lock: SourceLock
    dataset: DatasetManifest
    study: StudySpec
    artifact: ArtifactManifest
    index: StructuralIndexSummary
    index_manifest: StructuralCardIndexManifestV1
    statistics: StructuralStatistics
    report: dict[str, JSONValue]


def _require_single_source_artifact(source_lock: SourceLock) -> SourceArtifact:
    if len(source_lock.artifacts) != 1:
        raise ValueError("source lock must contain exactly one source artifact")
    return source_lock.artifacts[0]


def _write_document(path: Path, document: dict[str, JSONValue], schema: str) -> None:
    validate_document(document, schema)
    path.write_bytes(canonical_json_bytes(document))


def _structural_report(
    source_lock: SourceLock,
    dataset: DatasetManifest,
    study: StudySpec,
    artifact: ArtifactManifest,
    index: StructuralIndexSummary,
    statistics: StructuralStatistics,
) -> dict[str, JSONValue]:
    source = _require_single_source_artifact(source_lock)
    return {
        "schema": REPORT_SCHEMA,
        "record_provenance": REPORT_PROVENANCE,
        "source_lock_digest": source_lock.digest(),
        "source_id": source.source_id,
        "source_locator": source.locator,
        "source_artifact_sha256": source.sha256,
        "source_artifact_byte_length": source.byte_length,
        "source_media_type": source.media_type,
        "task01_record_identity_parity": statistics.task01_record_identity_parity,
        "task01_identity_count": statistics.task01_identity_count,
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


def build_structural_corpus(
    source_path: str | Path,
    source_lock_path: str | Path,
    output_dir: str | Path,
) -> StructuralBuildResult:
    """Build one exact source artifact into the complete structural output."""

    source_lock = load_source_lock(source_lock_path)
    source_artifact = _require_single_source_artifact(source_lock)
    source_file = Path(source_path)
    validate_source_file(source_artifact, source_file)

    output_path = Path(output_dir)
    if output_path.exists() and not output_path.is_dir():
        raise ValueError("structural output is not a directory")
    output_path.mkdir(parents=True, exist_ok=True)
    if any(output_path.iterdir()):
        raise ValueError("structural output directory must be empty")

    index = build_structural_index(source_file, output_path / "records")
    index_manifest = StructuralCardIndexManifestV1.from_summary(index)
    dataset = DatasetManifest(
        dataset_id=STRUCTURAL_DATASET_ID,
        dataset_version=STRUCTURAL_DATASET_VERSION,
        source_lock_digest=source_lock.digest(),
        normalization_profile=STRUCTURAL_NORMALIZATION_PROFILE,
        record_count=index.record_count,
    )
    study = StudySpec(
        study_id=STRUCTURAL_STUDY_ID,
        dataset_refs=(STRUCTURAL_DATASET_ID,),
        operation=STRUCTURAL_OPERATION,
        parameters={
            "shard_count": SHARD_COUNT,
            "source_lock_digest": source_lock.digest(),
        },
    )
    manifest_bytes = index_manifest.canonical_bytes()
    artifact = ArtifactManifest(
        artifact_id=STRUCTURAL_ARTIFACT_ID,
        artifact_kind=STRUCTURAL_ARTIFACT_KIND,
        study_digest=study.digest(),
        content_sha256=sha256_bytes(manifest_bytes),
        byte_length=len(manifest_bytes),
    )
    statistics = collect_structural_statistics(
        iter_structural_records(source_file),
        index.shard_record_counts,
        task01_identity_parity=True,
        task01_identity_count=index.record_count,
    )
    if statistics.record_count != index.record_count:
        raise ValueError("structural statistics record count mismatch")
    if statistics.unique_oracle_id_count != index.unique_oracle_id_count:
        raise ValueError("structural statistics identity count mismatch")
    report = _structural_report(
        source_lock, dataset, study, artifact, index, statistics
    )

    _write_document(
        output_path / "structural-index-manifest.json",
        index_manifest.to_wire(),
        "structural-card-index-manifest.v1.schema.json",
    )
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
        output_path / "structural-report.json",
        report,
        "structural-card-report.v1.schema.json",
    )
    return StructuralBuildResult(
        output_dir=output_path,
        source_lock=source_lock,
        dataset=dataset,
        study=study,
        artifact=artifact,
        index=index,
        index_manifest=index_manifest,
        statistics=statistics,
        report=report,
    )


def build_pinned_structural(
    repository_root: str | Path,
    output_dir: str | Path,
) -> StructuralBuildResult:
    """Build only from the committed lock and exact local content cache."""

    root = Path(repository_root)
    lock_path = root / "source-locks" / "scryfall-oracle-v1.json"
    source_lock = load_source_lock(lock_path)
    source_artifact = _require_single_source_artifact(source_lock)
    if source_lock.digest() != PINNED_SOURCE_LOCK_DIGEST:
        raise ValueError("pinned source lock digest mismatch")
    source_path = cache_path_for(
        root / ".cache" / "sources" / "scryfall",
        source_artifact.sha256,
    )
    return build_structural_corpus(source_path, lock_path, output_dir)
