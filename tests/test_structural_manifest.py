import gzip
import json
from copy import deepcopy
from pathlib import Path

import pytest

from manafold_census.canonical import MAX_INTEGER, canonical_json_bytes
from manafold_census.digest import sha256_bytes
from manafold_census.structural.index import build_structural_index
from manafold_census.structural.manifest import (
    StructuralCardIndexManifestV1,
    StructuralIndexManifestError,
)
from manafold_census.validation import SchemaValidationError, validate_document

ORACLE_ID = "00000000-0000-4000-8000-000000000000"
SOURCE_CARD_ID = "00000000-0000-4000-8000-000000000001"


def _write_source(path: Path) -> None:
    record = {
        "object": "card",
        "oracle_id": ORACLE_ID,
        "id": SOURCE_CARD_ID,
        "name": "Zero",
        "layout": "normal",
    }
    with gzip.open(path, "wb") as stream:
        stream.write(json.dumps(record, separators=(",", ":")).encode() + b"\n")


def _valid_manifest(tmp_path: Path) -> StructuralCardIndexManifestV1:
    source_path = tmp_path / "source.jsonl.gz"
    _write_source(source_path)
    summary = build_structural_index(source_path, tmp_path / "records")
    return StructuralCardIndexManifestV1.from_summary(summary)


def test_manifest_has_exact_wire_shape_and_round_trips(tmp_path: Path) -> None:
    manifest = _valid_manifest(tmp_path)
    wire = manifest.to_wire()

    assert set(wire) == {"schema", "shards", "aggregate_digest"}
    assert wire["schema"] == "census.structural-card-index-manifest.v1"
    assert len(wire["shards"]) == 16
    assert wire["shards"][0]["relative_path"] == "records/0.jsonl"
    assert wire["shards"][-1]["relative_path"] == "records/f.jsonl"
    validate_document(wire, "structural-card-index-manifest.v1.schema.json")
    assert StructuralCardIndexManifestV1.from_wire(wire) == manifest


def test_manifest_bytes_and_digest_are_separate_from_aggregate_digest(
    tmp_path: Path,
) -> None:
    manifest = _valid_manifest(tmp_path)

    assert manifest.canonical_bytes() == canonical_json_bytes(manifest.to_wire())
    assert manifest.digest() == sha256_bytes(manifest.canonical_bytes())
    assert manifest.digest() != manifest.aggregate_digest


def test_manifest_descriptor_keys_and_order_are_frozen(tmp_path: Path) -> None:
    wire = _valid_manifest(tmp_path).to_wire()

    assert [descriptor["relative_path"] for descriptor in wire["shards"]] == [
        f"records/{shard}.jsonl" for shard in "0123456789abcdef"
    ]
    for descriptor in wire["shards"]:
        assert set(descriptor) == {
            "relative_path",
            "sha256",
            "byte_length",
            "record_count",
        }


def test_manifest_rejects_missing_extra_and_reordered_descriptors(
    tmp_path: Path,
) -> None:
    base = _valid_manifest(tmp_path).to_wire()

    missing = deepcopy(base)
    missing["shards"].pop()
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(missing)

    extra = deepcopy(base)
    extra["shards"].append(deepcopy(extra["shards"][0]))
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(extra)

    reordered = deepcopy(base)
    reordered["shards"].reverse()
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(reordered)


def test_manifest_rejects_wrong_path_uppercase_digest_and_unknown_fields(
    tmp_path: Path,
) -> None:
    base = _valid_manifest(tmp_path).to_wire()

    wrong_path = deepcopy(base)
    wrong_path["shards"][0]["relative_path"] = "records/f.jsonl"
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(wrong_path)

    uppercase_digest = deepcopy(base)
    uppercase_digest["shards"][0]["sha256"] = "A" * 64
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(uppercase_digest)

    unknown = deepcopy(base)
    unknown["shards"][0]["unexpected"] = 1
    with pytest.raises(StructuralIndexManifestError):
        StructuralCardIndexManifestV1.from_wire(unknown)


def test_manifest_rejects_wrong_schema_and_aggregate_digest(
    tmp_path: Path,
) -> None:
    base = _valid_manifest(tmp_path).to_wire()

    wrong_schema = deepcopy(base)
    wrong_schema["schema"] = "census.other.v1"
    with pytest.raises(StructuralIndexManifestError, match="schema"):
        StructuralCardIndexManifestV1.from_wire(wrong_schema)

    wrong_digest = deepcopy(base)
    wrong_digest["aggregate_digest"] = "0" * 64
    with pytest.raises(StructuralIndexManifestError, match="aggregate"):
        StructuralCardIndexManifestV1.from_wire(wrong_digest)


@pytest.mark.parametrize("field", ["byte_length", "record_count"])
def test_manifest_rejects_negative_and_int64_overflow(
    tmp_path: Path, field: str
) -> None:
    base = _valid_manifest(tmp_path).to_wire()
    negative = deepcopy(base)
    negative["shards"][0][field] = -1
    with pytest.raises((StructuralIndexManifestError, SchemaValidationError)):
        StructuralCardIndexManifestV1.from_wire(negative)

    overflow = deepcopy(base)
    overflow["shards"][0][field] = MAX_INTEGER + 1
    with pytest.raises((StructuralIndexManifestError, SchemaValidationError)):
        StructuralCardIndexManifestV1.from_wire(overflow)


def test_manifest_schema_rejects_unknown_and_invalid_wire_values(
    tmp_path: Path,
) -> None:
    base = _valid_manifest(tmp_path).to_wire()
    base["unexpected"] = True

    with pytest.raises(SchemaValidationError, match="additional properties"):
        validate_document(base, "structural-card-index-manifest.v1.schema.json")
