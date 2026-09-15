"""M5-12 release-conformance tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_census_bundle import _build_m4_and_bundle_inputs

from manafold_census.canonical import canonical_json_bytes
from manafold_census.cli import main
from manafold_census.release.conformance import (
    ReleaseConformanceError,
    run_release_conformance,
)


def _arguments(tmp_path: Path) -> dict[str, Path]:
    package, m4_output, lock_path = _build_m4_and_bundle_inputs(tmp_path / "fixture")
    return {
        "input_lock_path": lock_path,
        "source_lock_path": package.m3_input.source_lock_path,
        "structural_output_directory": package.m3_input.structural_output_directory,
        "analysis_output_directory": package.m3_input.analysis_output_directory,
        "authority_package_directory": package.root,
        "m4_output_directory": m4_output,
        "output_root": tmp_path / "release-candidates",
        "evidence_path": tmp_path / "release-evidence.json",
    }


def test_release_conformance_rebuilds_two_candidates_and_writes_canonical_evidence(
    tmp_path: Path,
) -> None:
    arguments = _arguments(tmp_path)

    result = run_release_conformance(**arguments)

    assert tuple(run.label for run in result.candidate_runs) == (
        "candidate-a",
        "candidate-b",
    )
    assert result.authoritative_file_count == 98
    assert result.derived_file_count == 108
    assert result.hard_gates == (
        ("CENSUS_AUTHORITATIVE_BYTES_PARITY", "PASS"),
        ("REPORT_INDEX_BYTES_PARITY", "PASS"),
        ("RELEASE_CANDIDATE_REPRODUCTION", "PASS"),
        ("RELEASE_CANDIDATE_AUDITABILITY", "PASS"),
    )
    assert result.experimental_gates == (("WINDOWS_EXE_BYTE_PARITY", "EXPERIMENTAL"),)
    for label in ("bundle-a", "bundle-b", "derived-a", "derived-b"):
        assert (arguments["output_root"] / label).is_dir()

    raw = arguments["evidence_path"].read_bytes()
    document = json.loads(raw)
    assert raw == canonical_json_bytes(document)
    assert str(tmp_path) not in raw.decode("utf-8")
    assert document["hard_gates"]["CENSUS_AUTHORITATIVE_BYTES_PARITY"] == "PASS"
    assert document["experimental_gates"]["WINDOWS_EXE_BYTE_PARITY"] == ("EXPERIMENTAL")


def test_release_conformance_rejects_existing_workspace_without_overwrite(
    tmp_path: Path,
) -> None:
    arguments = _arguments(tmp_path)
    output_root = arguments["output_root"]
    output_root.mkdir()
    sentinel = output_root / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(ReleaseConformanceError, match="output root already exists"):
        run_release_conformance(**arguments)

    assert sentinel.read_bytes() == b"keep"
    assert not arguments["evidence_path"].exists()


def test_release_conformance_failure_does_not_write_evidence(tmp_path: Path) -> None:
    arguments = _arguments(tmp_path)
    arguments["m4_output_directory"] = tmp_path / "missing-m4"

    with pytest.raises((FileNotFoundError, ReleaseConformanceError, ValueError)):
        run_release_conformance(**arguments)

    assert not arguments["evidence_path"].exists()


def test_release_conformance_cli_uses_only_explicit_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = _arguments(tmp_path)
    exit_code = main(
        [
            "m5-release-conformance",
            "--input-lock",
            str(arguments["input_lock_path"]),
            "--source-lock",
            str(arguments["source_lock_path"]),
            "--structural-output",
            str(arguments["structural_output_directory"]),
            "--analysis-output",
            str(arguments["analysis_output_directory"]),
            "--authority-package",
            str(arguments["authority_package_directory"]),
            "--m4-output",
            str(arguments["m4_output_directory"]),
            "--output-root",
            str(arguments["output_root"]),
            "--evidence",
            str(arguments["evidence_path"]),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "CENSUS_AUTHORITATIVE_BYTES_PARITY=PASS" in captured
    assert "REPORT_INDEX_BYTES_PARITY=PASS" in captured
    assert "windows-exe-byte-parity=EXPERIMENTAL" in captured
    assert "m5-release-conformance=PASS" in captured
