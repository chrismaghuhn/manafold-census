"""Fail-closed validation of a generated Task-01 corpus output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from ..models import (
    ArtifactManifest,
    DatasetManifest,
    SourceArtifact,
    SourceLock,
    StudySpec,
)
from ..validation import validate_document
from .build import (
    ARTIFACT_ID,
    ARTIFACT_KIND,
    DATASET_ID,
    DATASET_VERSION,
    NORMALIZATION_PROFILE,
    OPERATION,
    SHARD_COUNT,
    STUDY_ID,
)
from .index import inspect_record_index
from .manifest import IndexRecordManifest


def _read_canonical_document(path: Path) -> dict[str, object]:
    raw_bytes = path.read_bytes()
    document = json.loads(raw_bytes)
    if not isinstance(document, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    if raw_bytes != canonical_json_bytes(cast(JSONValue, document)):
        raise ValueError(f"{path.name} is not canonical JSON")
    return document


def validate_corpus_output(output_dir: str | Path) -> str:
    """Validate generated index/manifests and return the aggregate index digest."""

    output_path = Path(output_dir)
    index = inspect_record_index(output_path / "records")
    dataset_document = _read_canonical_document(output_path / "dataset-manifest.json")
    study_document = _read_canonical_document(output_path / "study-spec.json")
    artifact_document = _read_canonical_document(output_path / "artifact-manifest.json")
    index_manifest_document = _read_canonical_document(
        output_path / "index-manifest.json"
    )
    report_document = _read_canonical_document(output_path / "corpus-report.json")
    validate_document(dataset_document, "dataset-manifest.v1.schema.json")
    validate_document(study_document, "study-spec.v1.schema.json")
    validate_document(artifact_document, "artifact-manifest.v1.schema.json")
    validate_document(
        index_manifest_document, "oracle-record-index-manifest.v1.schema.json"
    )
    validate_document(report_document, "oracle-corpus-report.v1.schema.json")
    dataset = DatasetManifest.from_wire(dataset_document)
    study = StudySpec.from_wire(study_document)
    artifact = ArtifactManifest.from_wire(artifact_document)
    index_manifest = IndexRecordManifest.from_wire(index_manifest_document)
    expected_index_manifest = IndexRecordManifest.from_summary(index)
    if index_manifest != expected_index_manifest:
        raise ValueError("corpus index manifest does not match index")
    index_manifest_bytes = canonical_json_bytes(
        cast(JSONValue, index_manifest_document)
    )
    if artifact.content_sha256 != sha256_bytes(index_manifest_bytes):
        raise ValueError("corpus artifact index manifest digest mismatch")
    if artifact.byte_length != len(index_manifest_bytes):
        raise ValueError("corpus artifact index manifest byte length mismatch")
    if dataset.record_count != index.record_count:
        raise ValueError("corpus dataset record count does not match index")
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
    if report_document["index_manifest_sha256"] != artifact.content_sha256:
        raise ValueError("corpus report index manifest digest mismatch")
    if report_document["index_manifest_byte_length"] != artifact.byte_length:
        raise ValueError("corpus report index manifest byte length mismatch")
    if dataset.dataset_id != DATASET_ID:
        raise ValueError("corpus dataset id mismatch")
    if dataset.dataset_version != DATASET_VERSION:
        raise ValueError("corpus dataset version mismatch")
    if dataset.normalization_profile != NORMALIZATION_PROFILE:
        raise ValueError("corpus normalization profile mismatch")
    if study.study_id != STUDY_ID or study.operation != OPERATION:
        raise ValueError("corpus study identity mismatch")
    if study.dataset_refs != (DATASET_ID,):
        raise ValueError("corpus study dataset reference mismatch")
    if study.to_wire()["parameters"] != {
        "shard_count": SHARD_COUNT,
        "source_lock_digest": dataset.source_lock_digest,
    }:
        raise ValueError("corpus study parameters mismatch")
    if artifact.artifact_id != ARTIFACT_ID or artifact.artifact_kind != ARTIFACT_KIND:
        raise ValueError("corpus artifact identity mismatch")
    source = SourceArtifact(
        source_id=cast(str, report_document["source_id"]),
        locator=cast(str, report_document["source_locator"]),
        sha256=cast(str, report_document["source_artifact_sha256"]),
        byte_length=cast(int, report_document["source_artifact_byte_length"]),
        media_type=cast(str, report_document["source_media_type"]),
    )
    reconstructed_lock = SourceLock((source,))
    if reconstructed_lock.digest() != report_document["source_lock_digest"]:
        raise ValueError("corpus report source lock digest mismatch")
    if reconstructed_lock.digest() != dataset.source_lock_digest:
        raise ValueError("corpus dataset source lock digest mismatch")
    return index.aggregate_digest
