import gzip
import json
from copy import deepcopy
from pathlib import Path

import pytest

from manafold_census.canonical import canonical_json_bytes
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceArtifact, SourceLock
from manafold_census.structural.build import build_structural_corpus
from manafold_census.structural.check import (
    validate_pinned_structural_output,
    validate_structural_output,
)

OID_0 = "00000000-0000-4000-8000-000000000000"
OID_0B = "00000000-0000-4000-8000-00000000000b"
OID_8 = "88888888-8888-4888-8888-888888888888"
CID_0 = "00000000-0000-4000-8000-000000000001"
CID_0B = "00000000-0000-4000-8000-00000000000c"
CID_8 = "88888888-8888-4888-8888-888888888889"


def _records() -> list[dict[str, object]]:
    return [
        {
            "object": "card",
            "oracle_id": OID_8,
            "id": CID_8,
            "name": "Eight",
            "layout": "normal",
            "oracle_text": "plain source text",
            "colors": ["G"],
            "color_identity": ["G"],
        },
        {
            "object": "card",
            "oracle_id": OID_0B,
            "id": CID_0B,
            "name": "Zero B",
            "layout": "normal",
        },
        {
            "object": "card",
            "oracle_id": OID_0,
            "id": CID_0,
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
            "all_parts": [
                {
                    "component": "related",
                    "id": CID_8,
                    "name": "Eight",
                    "object": "card",
                    "type_line": "Creature",
                    "uri": "https://example.invalid/eight",
                }
            ],
        },
    ]


def _build_fixture(root: Path) -> tuple[Path, Path, Path]:
    source_path = root / "source.jsonl.gz"
    root.mkdir(parents=True)
    with gzip.open(source_path, "wb") as stream:
        for record in _records():
            stream.write(json.dumps(record, separators=(",", ":")).encode() + b"\n")
    source_bytes = source_path.read_bytes()
    lock = SourceLock(
        (
            SourceArtifact(
                source_id="check-test-source",
                locator="fixture://check-test-source.jsonl.gz",
                sha256=sha256_bytes(source_bytes),
                byte_length=len(source_bytes),
                media_type="application/gzip",
            ),
        )
    )
    lock_path = root / "source-lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))
    output = root / "output"
    build_structural_corpus(source_path, lock_path, output)
    return source_path, lock_path, output


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_bytes())


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.write_bytes(canonical_json_bytes(document))


def _read_shard_documents(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def _write_shard_documents(path: Path, documents: list[dict[str, object]]) -> None:
    path.write_bytes(
        b"".join(canonical_json_bytes(document) + b"\n" for document in documents)
    )


def test_checker_reconstructs_a_complete_output_from_source(tmp_path: Path) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "valid")

    digest = validate_structural_output(output, source_path, lock_path)

    assert isinstance(digest, str)
    assert len(digest) == 64


def test_checker_rejects_missing_and_extra_output_files(tmp_path: Path) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "missing")
    (output / "structural-report.json").unlink()
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "extra")
    (output / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)


def test_checker_rejects_noncanonical_documents_and_jsonl(tmp_path: Path) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "document")
    dataset_path = output / "dataset-manifest.json"
    dataset = _read_json(dataset_path)
    dataset_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="canonical"):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "jsonl")
    shard_path = output / "records" / "0.jsonl"
    document = _read_shard_documents(shard_path)[0]
    shard_path.write_bytes(
        json.dumps(document, separators=(", ", ": ")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="canonical"):
        validate_structural_output(output, source_path, lock_path)


def test_checker_validates_each_structural_record_against_card_schema(
    tmp_path: Path,
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "card-schema")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    documents[0]["unexpected"] = True
    _write_shard_documents(zero_path, documents)

    with pytest.raises(ValueError, match="additional properties"):
        validate_structural_output(output, source_path, lock_path)


def test_checker_rejects_wrong_shard_order_and_duplicate_identity(
    tmp_path: Path,
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "wrong-shard")
    zero_path = output / "records" / "0.jsonl"
    zero_data = zero_path.read_bytes()
    zero_path.write_bytes(b"")
    (output / "records" / "1.jsonl").write_bytes(zero_data)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "order")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    _write_shard_documents(zero_path, list(reversed(documents)))
    with pytest.raises(ValueError, match="order|strictly"):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "duplicate")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    _write_shard_documents(zero_path, documents + [deepcopy(documents[0])])
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)


@pytest.mark.parametrize("field", ["source_record_sha256", "source_card_id", "name"])
def test_checker_rejects_task01_identity_projection_mutations(
    tmp_path: Path, field: str
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / field)
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    if field == "source_record_sha256":
        documents[0][field] = "0" * 64
    elif field == "source_card_id":
        documents[0][field] = "11111111-1111-4111-8111-111111111111"
    else:
        documents[0][field] = "changed"
    _write_shard_documents(zero_path, documents)

    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)


def test_checker_rejects_wrong_retained_field_face_order_and_related_uri(
    tmp_path: Path,
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "field")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    documents[0]["oracle_text"] = "changed"
    _write_shard_documents(zero_path, documents)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "faces")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    documents[0]["faces"] = list(reversed(documents[0]["faces"]))
    _write_shard_documents(zero_path, documents)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "uri")
    zero_path = output / "records" / "0.jsonl"
    documents = _read_shard_documents(zero_path)
    documents[0]["all_parts"][0]["uri"] = "https://example.invalid/changed"
    _write_shard_documents(zero_path, documents)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)


def test_checker_rejects_manifest_artifact_and_report_mutations(
    tmp_path: Path,
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "manifest")
    manifest_path = output / "structural-index-manifest.json"
    manifest = _read_json(manifest_path)
    manifest["aggregate_digest"] = "0" * 64
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "artifact")
    artifact_path = output / "artifact-manifest.json"
    artifact = _read_json(artifact_path)
    artifact["content_sha256"] = "0" * 64
    _write_json(artifact_path, artifact)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "report")
    report_path = output / "structural-report.json"
    report = _read_json(report_path)
    report["structural_record_count"] = 999
    _write_json(report_path, report)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "report-map")
    report_path = output / "structural-report.json"
    report = _read_json(report_path)
    report["top_level_field_presence"]["oracle_text"] = 999
    _write_json(report_path, report)
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)


def test_checker_rejects_source_lock_mismatch_and_pinned_substitution(
    tmp_path: Path,
) -> None:
    source_path, lock_path, output = _build_fixture(tmp_path / "lock")
    lock = _read_json(lock_path)
    lock["artifacts"][0]["locator"] = "fixture://substituted"
    lock_path.write_bytes(canonical_json_bytes(lock))
    with pytest.raises(ValueError):
        validate_structural_output(output, source_path, lock_path)

    source_path, lock_path, output = _build_fixture(tmp_path / "pinned")
    repository_root = tmp_path / "pinned-repository"
    (repository_root / "source-locks").mkdir(parents=True)
    (repository_root / ".cache" / "sources" / "scryfall").mkdir(parents=True)
    pinned_lock = repository_root / "source-locks" / "scryfall-oracle-v1.json"
    pinned_lock.write_bytes(lock_path.read_bytes())
    cache_path = (
        repository_root
        / ".cache"
        / "sources"
        / "scryfall"
        / (json.loads(lock_path.read_bytes())["artifacts"][0]["sha256"] + ".jsonl.gz")
    )
    cache_path.write_bytes(source_path.read_bytes())
    with pytest.raises(ValueError, match="pinned source lock digest"):
        validate_pinned_structural_output(repository_root, output)
