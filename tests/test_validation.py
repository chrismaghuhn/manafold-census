from dataclasses import replace

import pytest

from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceArtifact, SourceLock
from manafold_census.validation import (
    SchemaValidationError,
    validate_document,
    validate_source_file,
)


def _source(source_id: str, data: bytes = b"fixture") -> SourceArtifact:
    return SourceArtifact(
        source_id=source_id,
        locator=f"fixture://{source_id}.txt",
        sha256=sha256_bytes(data),
        byte_length=len(data),
        media_type="text/plain",
    )


def test_schema_validation_rejects_unknown_properties() -> None:
    document = _source("example-source").to_wire()
    document["unexpected"] = "rejected"

    with pytest.raises(SchemaValidationError, match="additional properties"):
        validate_document(document, "source-artifact.v1.schema.json")


def test_schema_validation_rejects_invalid_sha256() -> None:
    document = _source("example-source").to_wire()
    document["sha256"] = "not-a-sha256"

    with pytest.raises(SchemaValidationError, match="sha256"):
        validate_document(document, "source-artifact.v1.schema.json")


def test_schema_validation_rejects_negative_record_count() -> None:
    document = {
        "schema": "census.dataset-manifest.v1",
        "dataset_id": "example-dataset",
        "dataset_version": "1.0.0",
        "source_lock_digest": "a" * 64,
        "normalization_profile": "identity.v1",
        "record_count": -1,
    }

    with pytest.raises(SchemaValidationError, match="greater than or equal to 0"):
        validate_document(document, "dataset-manifest.v1.schema.json")


def test_schema_validation_rejects_negative_byte_length() -> None:
    document = {
        "schema": "census.artifact-manifest.v1",
        "artifact_id": "example-artifact",
        "artifact_kind": "fixture-output.v1",
        "study_digest": "a" * 64,
        "content_sha256": "b" * 64,
        "byte_length": -1,
    }

    with pytest.raises(SchemaValidationError, match="greater than or equal to 0"):
        validate_document(document, "artifact-manifest.v1.schema.json")


def test_python_validation_rejects_duplicate_source_ids_and_unsorted_locks() -> None:
    first = _source("a-source")
    second = _source("z-source")
    document = {
        "schema": "census.source-lock.v1",
        "artifacts": [second.to_wire(), first.to_wire()],
    }

    with pytest.raises(SchemaValidationError, match="sorted"):
        validate_document(document, "source-lock.v1.schema.json")

    duplicate_document = {
        "schema": "census.source-lock.v1",
        "artifacts": [first.to_wire(), first.to_wire()],
    }
    with pytest.raises(SchemaValidationError, match="duplicate source_id"):
        validate_document(duplicate_document, "source-lock.v1.schema.json")


def test_python_validation_rejects_noncanonical_study_parameter_value() -> None:
    document = {
        "schema": "census.study-spec.v1",
        "study_id": "example-study",
        "dataset_refs": ["example-dataset"],
        "operation": "fixture-identity.v1",
        "parameters": {"ratio": 0.5},
    }

    with pytest.raises(SchemaValidationError):
        validate_document(document, "study-spec.v1.schema.json")


def test_source_file_validation_rejects_digest_mismatch(tmp_path) -> None:
    path = tmp_path / "source.txt"
    path.write_bytes(b"expected")
    artifact = SourceArtifact.from_file(
        "example-source", "fixture://source.txt", path, "text/plain"
    )
    path.write_bytes(b"changed")

    with pytest.raises(ValueError, match="digest mismatch"):
        validate_source_file(artifact, path)


def test_source_file_validation_rejects_byte_length_mismatch(tmp_path) -> None:
    path = tmp_path / "source.txt"
    path.write_bytes(b"expected")
    artifact = SourceArtifact.from_file(
        "example-source", "fixture://source.txt", path, "text/plain"
    )
    wrong_length = replace(artifact, byte_length=artifact.byte_length + 1)

    with pytest.raises(ValueError, match="byte length mismatch"):
        validate_source_file(wrong_length, path)


def test_source_lock_model_digest_matches_wire_digest() -> None:
    lock = SourceLock((_source("example-source"),))
    assert len(lock.digest()) == 64
