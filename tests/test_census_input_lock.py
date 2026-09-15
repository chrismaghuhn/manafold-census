from __future__ import annotations

import copy
import importlib
import json
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest
from capability_m3_fixtures import record_with_proposed_requirement, write_synthetic_m3

from manafold_census.analysis.manifest import AnalysisManifestV1
from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.identity import requirement_set_digest_for
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceLock
from manafold_census.structural.manifest import StructuralCardIndexManifestV1
from manafold_census.validation import validate_document


def input_lock_module() -> ModuleType:
    try:
        return importlib.import_module("manafold_census.release.input_lock")
    except ModuleNotFoundError as error:
        pytest.fail(f"input-lock module is missing: {error}")


def build_lock(
    tmp_path: Path,
) -> tuple[object, object, object]:
    module = input_lock_module()
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    source_raw = m3_input.source_lock_path.read_bytes()
    source_lock = SourceLock.from_wire(json.loads(source_raw))
    m1_manifest_path = (
        m3_input.structural_output_directory / "structural-index-manifest.json"
    )
    m1_raw = m1_manifest_path.read_bytes()
    m1_manifest = StructuralCardIndexManifestV1.from_wire(json.loads(m1_raw))
    m3_manifest_path = m3_input.analysis_output_directory / "analysis-manifest.json"
    m3_raw = m3_manifest_path.read_bytes()
    m3_manifest = AnalysisManifestV1.from_wire(json.loads(m3_raw))
    lock = module.CensusInputLockV1(
        source_lock_digest=source_lock.digest(),
        source_lock_file_sha256=sha256_bytes(source_raw),
        m1_structural_manifest_sha256=sha256_bytes(m1_raw),
        m1_structural_aggregate_digest=m1_manifest.aggregate_digest,
        m3_analysis_manifest_sha256=sha256_bytes(m3_raw),
        m3_record_identity_set_digest=m3_manifest.record_identity_set_digest,
        m3_record_index_digest=m3_manifest.record_index_digest,
        m3_trace_index_digest=m3_manifest.trace_index_digest,
        expected_m4_requirement_set_digest=corpus.requirement_set_digest,
        m1_structural_schema="census.structural-card.v1",
        m3_analysis_schema="census.card-analysis.v1",
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        m4_ontology_schema="census.capability-ontology.v1",
        m4_dimension_registry_version="1",
        expected_oracle_identity_count=1,
        expected_structural_record_count=1,
        expected_analysis_record_count=1,
        expected_requirements_produced_card_count=1,
        expected_no_requirements_applicable_count=0,
        expected_unresolved_analysis_count=0,
        expected_requirement_count=len(corpus.requirements),
    )
    provisioning = module.CensusInputProvisioningV1(
        source_lock_path=m3_input.source_lock_path,
        structural_output_directory=m3_input.structural_output_directory,
        analysis_output_directory=m3_input.analysis_output_directory,
    )
    return lock, provisioning, corpus


def test_input_lock_wire_round_trips_with_raw_canonical_digest(
    tmp_path: Path,
) -> None:
    lock, _, _ = build_lock(tmp_path)
    module = input_lock_module()

    wire = lock.to_wire()
    validate_document(wire, "census-input-lock.v1.schema.json")
    round_tripped = module.CensusInputLockV1.from_wire(copy.deepcopy(wire))

    assert round_tripped == lock
    assert lock.digest() == sha256_bytes(canonical_json_bytes(wire))


def test_input_lock_has_no_release_lineage_field(tmp_path: Path) -> None:
    lock, _, _ = build_lock(tmp_path)
    module = input_lock_module()
    wire = lock.to_wire()
    wire["parent_census_release_id"] = "censusrel_" + "a" * 64

    with pytest.raises(ValueError, match="unexpected"):
        module.CensusInputLockV1.from_wire(wire)


def test_input_lock_rejects_boolean_lock_version(tmp_path: Path) -> None:
    lock, _, _ = build_lock(tmp_path)
    module = input_lock_module()
    wire = lock.to_wire()
    wire["lock_version"] = True

    with pytest.raises(ValueError, match="lock_version"):
        module.CensusInputLockV1.from_wire(wire)


def test_explicit_provisioning_paths_are_not_part_of_lock_wire(
    tmp_path: Path,
) -> None:
    lock, provisioning, _ = build_lock(tmp_path)
    module = input_lock_module()

    assert isinstance(provisioning.source_lock_path, Path)
    assert "source_lock_path" not in lock.to_wire()
    with pytest.raises(TypeError, match="path"):
        module.CensusInputProvisioningV1(
            source_lock_path="source-lock.json",
            structural_output_directory=provisioning.structural_output_directory,
            analysis_output_directory=provisioning.analysis_output_directory,
        )


def test_valid_frozen_inputs_return_pass_and_m3_corpus(
    tmp_path: Path,
) -> None:
    lock, provisioning, corpus = build_lock(tmp_path)
    module = input_lock_module()

    result = module.validate_census_input_lock(lock, provisioning)

    assert result.status is module.CensusInputLockStatusV1.PASS
    assert result.m3_corpus == corpus
    assert all(
        check.status is module.CensusInputLockStatusV1.PASS for check in result.checks
    )


def test_missing_explicit_artifact_returns_blocked(
    tmp_path: Path,
) -> None:
    lock, provisioning, _ = build_lock(tmp_path)
    module = input_lock_module()
    missing = replace(
        provisioning,
        analysis_output_directory=tmp_path / "missing-analysis",
    )

    result = module.validate_census_input_lock(lock, missing)

    assert result.status is module.CensusInputLockStatusV1.BLOCKED
    assert result.m3_corpus is None
    assert "analysis_output_directory" in result.checks[0].detail


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("source_lock_file_sha256", "source lock file"),
        ("m1_structural_manifest_sha256", "M1 structural manifest"),
        ("m1_structural_aggregate_digest", "M1 structural aggregate"),
        ("m3_analysis_manifest_sha256", "M3 analysis manifest"),
        ("m3_record_identity_set_digest", "M3 identity"),
        ("m3_record_index_digest", "M3 record index"),
        ("m3_trace_index_digest", "M3 trace index"),
        ("expected_m4_requirement_set_digest", "M4 Requirement-set"),
    ],
)
def test_digest_cross_checks_fail_closed(
    tmp_path: Path,
    field: str,
    message: str,
) -> None:
    lock, provisioning, _ = build_lock(tmp_path)
    module = input_lock_module()
    mutated = replace(lock, **{field: "f" * 64})

    result = module.validate_census_input_lock(mutated, provisioning)

    assert result.status is module.CensusInputLockStatusV1.FAIL
    assert result.m3_corpus is None
    assert message in result.checks[-1].detail or message in result.checks[0].detail


def test_lock_loader_requires_canonical_json(tmp_path: Path) -> None:
    lock, _, _ = build_lock(tmp_path)
    module = input_lock_module()
    path = tmp_path / "census-input-lock.json"
    path.write_bytes(b" " + canonical_json_bytes(lock.to_wire()))

    with pytest.raises(ValueError, match="canonical"):
        module.load_census_input_lock(path)


def test_cli_validates_only_explicit_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock, provisioning, _ = build_lock(tmp_path)
    lock_path = tmp_path / "census-input-lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))

    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-input-lock-check",
            "--lock",
            str(lock_path),
            "--source-lock",
            str(provisioning.source_lock_path),
            "--structural-output",
            str(provisioning.structural_output_directory),
            "--analysis-output",
            str(provisioning.analysis_output_directory),
        ]
    )

    assert exit_code == 0
    assert "m5-input-lock=PASS" in capsys.readouterr().out


def test_cli_reports_missing_artifact_as_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock, provisioning, _ = build_lock(tmp_path)
    lock_path = tmp_path / "census-input-lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))

    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-input-lock-check",
            "--lock",
            str(lock_path),
            "--source-lock",
            str(provisioning.source_lock_path),
            "--structural-output",
            str(provisioning.structural_output_directory),
            "--analysis-output",
            str(tmp_path / "missing-analysis"),
        ]
    )

    assert exit_code == 1
    assert "m5-input-lock=BLOCKED" in capsys.readouterr().out


def test_requirement_set_digest_fixture_uses_frozen_m4_domain(
    tmp_path: Path,
) -> None:
    lock, _, corpus = build_lock(tmp_path)

    assert lock.expected_m4_requirement_set_digest == requirement_set_digest_for(
        lock.m3_analysis_manifest_sha256,
        corpus.requirements,
    )


def test_input_lock_counts_use_the_signed_64_bit_range(tmp_path: Path) -> None:
    lock, _, _ = build_lock(tmp_path)

    with pytest.raises(ValueError, match="signed 64-bit"):
        replace(lock, expected_requirement_count=1 << 63)
