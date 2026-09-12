from dataclasses import FrozenInstanceError

import pytest

from manafold_census.digest import sha256_bytes
from manafold_census.models import (
    ArtifactManifest,
    DatasetManifest,
    SourceArtifact,
    SourceLock,
    StudySpec,
)


def _source(source_id: str, data: bytes = b"fixture") -> SourceArtifact:
    return SourceArtifact(
        source_id=source_id,
        locator=f"fixture://{source_id}.txt",
        sha256=sha256_bytes(data),
        byte_length=len(data),
        media_type="text/plain",
    )


def test_source_artifact_from_file_records_exact_bytes(tmp_path) -> None:
    path = tmp_path / "example.txt"
    path.write_bytes(b"synthetic source\n")

    artifact = SourceArtifact.from_file(
        source_id="example-source",
        locator="fixture://example.txt",
        path=path,
        media_type="text/plain",
    )

    assert artifact.to_wire() == {
        "schema": "census.source-artifact.v1",
        "source_id": "example-source",
        "locator": "fixture://example.txt",
        "sha256": sha256_bytes(b"synthetic source\n"),
        "byte_length": 17,
        "media_type": "text/plain",
    }


def test_source_lock_sorts_artifacts_and_rejects_duplicate_source_ids() -> None:
    first = _source("z-source")
    second = _source("a-source")
    lock = SourceLock(artifacts=(first, second))

    assert [artifact.source_id for artifact in lock.artifacts] == [
        "a-source",
        "z-source",
    ]
    with pytest.raises(ValueError, match="duplicate source_id"):
        SourceLock(artifacts=(first, first))


def test_dataset_manifest_contains_only_reproducible_data_product_fields() -> None:
    lock = SourceLock((_source("example-source"),))
    dataset = DatasetManifest(
        dataset_id="example-dataset",
        dataset_version="1.0.0",
        source_lock_digest=lock.digest(),
        normalization_profile="identity.v1",
        record_count=1,
    )

    assert dataset.to_wire() == {
        "schema": "census.dataset-manifest.v1",
        "dataset_id": "example-dataset",
        "dataset_version": "1.0.0",
        "source_lock_digest": lock.digest(),
        "normalization_profile": "identity.v1",
        "record_count": 1,
    }
    assert len(dataset.digest()) == 64


def test_study_spec_is_frozen_and_round_trips() -> None:
    study = StudySpec(
        study_id="example-study",
        dataset_refs=("example-dataset",),
        operation="fixture-identity.v1",
        parameters={"mode": "identity", "include_source": True},
    )

    with pytest.raises(FrozenInstanceError):
        study.study_id = "changed"  # type: ignore[misc]

    assert StudySpec.from_wire(study.to_wire()) == study
    assert study.to_wire()["schema"] == "census.study-spec.v1"


@pytest.mark.parametrize("parameters", [{"ratio": 0.5}, {"values": {"x"}}])
def test_study_spec_rejects_noncanonical_parameters(parameters: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        StudySpec(
            study_id="example-study",
            dataset_refs=("example-dataset",),
            operation="fixture-identity.v1",
            parameters=parameters,  # type: ignore[arg-type]
        )


def test_artifact_manifest_describes_bytes_and_study_provenance() -> None:
    manifest = ArtifactManifest(
        artifact_id="example-artifact",
        artifact_kind="fixture-output.v1",
        study_digest="a" * 64,
        content_sha256=sha256_bytes(b"{}"),
        byte_length=2,
    )

    assert manifest.to_wire() == {
        "schema": "census.artifact-manifest.v1",
        "artifact_id": "example-artifact",
        "artifact_kind": "fixture-output.v1",
        "study_digest": "a" * 64,
        "content_sha256": sha256_bytes(b"{}"),
        "byte_length": 2,
    }
    assert "authority" not in manifest.to_wire()
