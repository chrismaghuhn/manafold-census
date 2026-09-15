from __future__ import annotations

from pathlib import Path

import pytest
from test_census_authority_package import (
    _policy,
    _TestAuthorityPackage,
    _write_test_package,
    _write_variant,
)

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.admissibility import (
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
)
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.release.m4_orchestration import (
    M5M4BuildError,
    build_real_m4_snapshot,
)


def _write_rejected_package(
    package: _TestAuthorityPackage,
    root: Path,
) -> None:
    rejected = tuple(
        SourceRequirementAdmissibilityV1.for_requirement(
            requirement,
            m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
            authority_id=_policy().sra_authority_id,
            authority_version=_policy().sra_authority_version,
            reviewer_id=_policy().sra_reviewer_id,
            decision=AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING,
        )
        for requirement in package.corpus.requirements
    )
    decisions = tuple(
        mapping_decision(
            requirement,
            MappingDispositionV1.UNMAPPED,
            MappingReasonV1.NO_REVIEWED_CAPABILITY,
            m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
        )
        for requirement in package.corpus.requirements
    )
    _write_variant(
        package,
        root,
        capability_definitions=(),
        reviews=(),
        admissibility=rejected,
        links=(),
        mapping_decisions=decisions,
        relations=(),
        evolution=(),
    )


def test_real_m4_snapshot_is_genesis_and_record_set_parity_passes(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    output = tmp_path / "m4"

    result = build_real_m4_snapshot(
        authority_package_directory=package.root,
        m3_input=package.m3_input,
        lock=package.lock,
        corpus=package.corpus,
        output_directory=output,
    )

    assert result.manifest.parent_m4_manifest_sha256 is None
    assert result.authority_package_record_set_parity is True
    assert (output / "m4-ontology-manifest.json").is_file()


def test_real_m4_snapshot_accepts_non_positive_review_result(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    rejected_root = tmp_path / "rejected"
    _write_rejected_package(package, rejected_root)

    result = build_real_m4_snapshot(
        authority_package_directory=rejected_root,
        m3_input=package.m3_input,
        lock=package.lock,
        corpus=package.corpus,
        output_directory=tmp_path / "rejected-m4",
    )

    assert result.manifest.parent_m4_manifest_sha256 is None
    assert result.authority_package_record_set_parity is True
    assert result.definitions == ()
    assert result.links == ()
    assert result.mapping_decisions


def test_real_m4_snapshot_never_overwrites_existing_output(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(M5M4BuildError, match="already exists"):
        build_real_m4_snapshot(
            authority_package_directory=package.root,
            m3_input=package.m3_input,
            lock=package.lock,
            corpus=package.corpus,
            output_directory=output,
        )

    assert sentinel.read_bytes() == b"keep"


def test_real_m4_snapshot_missing_authority_does_not_publish(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    output = tmp_path / "missing-authority-m4"

    with pytest.raises(FileNotFoundError):
        build_real_m4_snapshot(
            authority_package_directory=tmp_path / "missing-authority",
            m3_input=package.m3_input,
            lock=package.lock,
            corpus=package.corpus,
            output_directory=output,
        )

    assert not output.exists()


def test_real_m4_cli_requires_explicit_inputs_and_publishes_genesis(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = _write_test_package(tmp_path)
    lock_path = tmp_path / "input-lock.json"
    lock_path.write_bytes(canonical_json_bytes(package.lock.to_wire()))
    output = tmp_path / "cli-m4"

    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-m4-build",
            "--input-lock",
            str(lock_path),
            "--authority-package",
            str(package.root),
            "--source-lock",
            str(package.m3_input.source_lock_path),
            "--structural-output",
            str(package.m3_input.structural_output_directory),
            "--analysis-output",
            str(package.m3_input.analysis_output_directory),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "m4-parent=null" in captured
    assert "authority-m4-record-set-parity=PASS" in captured
    assert "m5-m4-build=PASS" in captured
