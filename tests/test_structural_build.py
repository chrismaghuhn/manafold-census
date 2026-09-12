import gzip
import json
from pathlib import Path

import pytest

import manafold_census.structural.build as structural_build_module
from manafold_census.canonical import canonical_json_bytes
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceArtifact, SourceLock
from manafold_census.source.transfer import cache_path_for
from manafold_census.structural.build import (
    STRUCTURAL_ARTIFACT_ID,
    STRUCTURAL_ARTIFACT_KIND,
    STRUCTURAL_DATASET_ID,
    STRUCTURAL_DATASET_VERSION,
    STRUCTURAL_NORMALIZATION_PROFILE,
    STRUCTURAL_OPERATION,
    STRUCTURAL_STUDY_ID,
    StructuralBuildResult,
    build_pinned_structural,
    build_structural_corpus,
)
from manafold_census.validation import validate_document

ORACLE_ID_0 = "00000000-0000-4000-8000-000000000000"
ORACLE_ID_8 = "88888888-8888-4888-8888-888888888888"
CARD_ID_0 = "00000000-0000-4000-8000-000000000001"
CARD_ID_8 = "88888888-8888-4888-8888-888888888889"


def _records() -> list[dict[str, object]]:
    return [
        {
            "object": "card",
            "oracle_id": ORACLE_ID_8,
            "id": CARD_ID_8,
            "name": "Eight",
            "layout": "normal",
            "oracle_text": "parent text",
            "colors": ["G"],
            "color_identity": ["G"],
            "keywords": [],
        },
        {
            "object": "card",
            "oracle_id": ORACLE_ID_0,
            "id": CARD_ID_0,
            "name": "Zero",
            "layout": "modal_dfc",
            "card_faces": [
                {
                    "name": "Front",
                    "mana_cost": "{G}",
                    "type_line": "Creature",
                    "oracle_text": "front",
                },
                {
                    "name": "Back",
                    "mana_cost": "",
                    "type_line": "Land",
                    "oracle_text": "",
                },
            ],
        },
    ]


def _write_source_and_lock(root: Path) -> tuple[Path, Path, SourceLock]:
    source_path = root / "source.jsonl.gz"
    with gzip.open(source_path, "wb") as stream:
        for record in _records():
            stream.write(
                json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode()
                + b"\n"
            )
    source_bytes = source_path.read_bytes()
    lock = SourceLock(
        (
            SourceArtifact(
                source_id="structural-test-source",
                locator="fixture://structural-test-source.jsonl.gz",
                sha256=sha256_bytes(source_bytes),
                byte_length=len(source_bytes),
                media_type="application/gzip",
            ),
        )
    )
    lock_path = root / "source-locks" / "scryfall-oracle-v1.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))
    return source_path, lock_path, lock


def test_build_writes_exact_structural_output_and_lifecycle_identities(
    tmp_path: Path,
) -> None:
    source_path, lock_path, lock = _write_source_and_lock(tmp_path)
    output = tmp_path / "build"

    result = build_structural_corpus(source_path, lock_path, output)

    assert isinstance(result, StructuralBuildResult)
    assert {path.name for path in output.iterdir()} == {
        "records",
        "structural-index-manifest.json",
        "dataset-manifest.json",
        "study-spec.json",
        "artifact-manifest.json",
        "structural-report.json",
    }
    assert {path.name for path in (output / "records").iterdir()} == {
        f"{shard}.jsonl" for shard in "0123456789abcdef"
    }
    assert result.source_lock == lock
    assert result.dataset.dataset_id == STRUCTURAL_DATASET_ID
    assert result.dataset.dataset_version == STRUCTURAL_DATASET_VERSION
    assert result.dataset.normalization_profile == STRUCTURAL_NORMALIZATION_PROFILE
    assert result.dataset.record_count == 2
    assert result.study.study_id == STRUCTURAL_STUDY_ID
    assert result.study.operation == STRUCTURAL_OPERATION
    assert result.study.to_wire()["parameters"] == {
        "shard_count": 16,
        "source_lock_digest": lock.digest(),
    }
    assert result.artifact.artifact_id == STRUCTURAL_ARTIFACT_ID
    assert result.artifact.artifact_kind == STRUCTURAL_ARTIFACT_KIND
    assert result.report["record_provenance"] == "SOURCE_FACT"
    assert result.report["structural_record_count"] == 2
    assert result.report["cards_with_faces"] == 1
    assert result.report["cards_without_faces"] == 1
    assert result.report["face_count_distribution"] == {"2": 1}


def test_artifact_binds_exact_structural_manifest_bytes_not_aggregate_digest(
    tmp_path: Path,
) -> None:
    source_path, lock_path, _ = _write_source_and_lock(tmp_path)
    output = tmp_path / "build"

    result = build_structural_corpus(source_path, lock_path, output)
    manifest_bytes = (output / "structural-index-manifest.json").read_bytes()

    assert manifest_bytes == result.index_manifest.canonical_bytes()
    assert result.artifact.content_sha256 == sha256_bytes(manifest_bytes)
    assert result.artifact.byte_length == len(manifest_bytes)
    assert (
        result.artifact.content_sha256
        == result.report["structural_index_manifest_sha256"]
    )
    assert result.artifact.content_sha256 != result.index.aggregate_digest


def test_all_written_documents_validate_against_their_normative_schemas(
    tmp_path: Path,
) -> None:
    source_path, lock_path, _ = _write_source_and_lock(tmp_path)
    output = tmp_path / "build"
    build_structural_corpus(source_path, lock_path, output)

    schema_by_name = {
        "structural-index-manifest.json": (
            "structural-card-index-manifest.v1.schema.json"
        ),
        "dataset-manifest.json": "dataset-manifest.v1.schema.json",
        "study-spec.json": "study-spec.v1.schema.json",
        "artifact-manifest.json": "artifact-manifest.v1.schema.json",
        "structural-report.json": "structural-card-report.v1.schema.json",
    }
    for filename, schema in schema_by_name.items():
        document = json.loads((output / filename).read_bytes())
        validate_document(document, schema)


def test_build_rejects_nonempty_output_and_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    source_path, lock_path, _ = _write_source_and_lock(tmp_path)
    output = tmp_path / "build"
    output.mkdir()
    (output / "unrelated.txt").write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        build_structural_corpus(source_path, lock_path, output)

    clean_output = tmp_path / "clean-build"
    source_path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="source digest mismatch"):
        build_structural_corpus(source_path, lock_path, clean_output)


def test_build_rejects_multi_artifact_source_lock(tmp_path: Path) -> None:
    source_path, lock_path, lock = _write_source_and_lock(tmp_path)
    first = lock.artifacts[0]
    second = SourceArtifact(
        source_id="second-structural-test-source",
        locator="fixture://second-structural-test-source.jsonl.gz",
        sha256=first.sha256,
        byte_length=first.byte_length,
        media_type=first.media_type,
    )
    multi_lock = SourceLock.build((first, second))
    lock_path.write_bytes(canonical_json_bytes(multi_lock.to_wire()))

    with pytest.raises(ValueError, match="exactly one"):
        build_structural_corpus(source_path, lock_path, tmp_path / "multi-build")


def test_pinned_build_rejects_valid_substituted_lock_and_cache(
    tmp_path: Path,
) -> None:
    source_path, lock_path, lock = _write_source_and_lock(tmp_path)
    cache_root = tmp_path / ".cache" / "sources" / "scryfall"
    cache_root.mkdir(parents=True)
    cache_path_for(cache_root, lock.artifacts[0].sha256).write_bytes(
        source_path.read_bytes()
    )

    with pytest.raises(ValueError, match="pinned source lock digest"):
        build_pinned_structural(tmp_path, tmp_path / "substituted-build")


def test_pinned_build_uses_only_the_content_addressed_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path, lock_path, lock = _write_source_and_lock(tmp_path)
    cache_root = tmp_path / ".cache" / "sources" / "scryfall"
    cache_root.mkdir(parents=True)
    cache_path_for(cache_root, lock.artifacts[0].sha256).write_bytes(
        source_path.read_bytes()
    )
    monkeypatch.setattr(
        structural_build_module, "PINNED_SOURCE_LOCK_DIGEST", lock.digest()
    )

    result = build_pinned_structural(tmp_path, tmp_path / "pinned-build")

    assert result.dataset.source_lock_digest == lock.digest()
