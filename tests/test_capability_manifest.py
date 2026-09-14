from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest
from test_capability_build import build_synthetic_m4, empty_m3_input

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.manifest import M4OntologyManifestV1
from manafold_census.validation import validate_document


def test_m4_manifest_binds_m3_and_all_authoritative_files(tmp_path: Path) -> None:
    m3_input = empty_m3_input(tmp_path / "m3")
    result = build_synthetic_m4(
        tmp_path / "output",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    assert result.manifest.m3_analysis_manifest_sha256
    assert result.manifest.requirement_set_digest
    assert len(result.manifest.link_shards) == 16
    assert len(result.manifest.mapping_decision_shards) == 16
    assert "report_index_digest" not in result.manifest.to_wire()
    assert (result.output_dir / "capability-relations.jsonl").is_file()
    validate_document(
        result.manifest.to_wire(),
        "capability-ontology-manifest.v1.schema.json",
    )


def test_manifest_digest_is_raw_sha256_of_canonical_manifest_bytes(
    tmp_path: Path,
) -> None:
    result = build_synthetic_m4(
        tmp_path / "output",
        m3_input=empty_m3_input(tmp_path / "m3"),
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    manifest = result.manifest
    raw = canonical_json_bytes(manifest.to_wire())

    assert manifest.digest() == hashlib.sha256(raw).hexdigest()
    assert M4OntologyManifestV1.from_wire(manifest.to_wire()) == manifest


@pytest.mark.parametrize("mutation", ["fixed_path", "duplicate_shard_path"])
def test_manifest_schema_binds_descriptor_paths(
    tmp_path: Path,
    mutation: str,
) -> None:
    result = build_synthetic_m4(
        tmp_path / "output",
        m3_input=empty_m3_input(tmp_path / "m3"),
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    wire = copy.deepcopy(result.manifest.to_wire())
    if mutation == "fixed_path":
        wire["capability_file"]["relative_path"] = "review-authority.jsonl"
    else:
        wire["link_shards"][1]["relative_path"] = "links/0.jsonl"

    with pytest.raises(ValueError):
        validate_document(wire, "capability-ontology-manifest.v1.schema.json")
