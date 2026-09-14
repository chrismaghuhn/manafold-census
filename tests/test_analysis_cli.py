from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from manafold_census import cli
from manafold_census.canonical import canonical_json_bytes

REPOSITORY_ROOT = Path(__file__).parents[1]


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "manafold_census.cli", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        tmp_path / "m3",
        tmp_path / "m1",
        tmp_path / "source-lock.json",
    )


def test_bounded_synthetic_m3_cli_build_check_and_report(
    tmp_path: Path,
) -> None:
    output, structural_output, source_lock = _build_paths(tmp_path)
    build = _run_cli(
        "m3-build",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert build.returncode == 0, build.stderr
    assert "m3-build=PASS" in build.stdout
    manifest_path = output / "analysis-manifest.json"
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_bytes())["record_count"] == 5

    check = _run_cli(
        "m3-check",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert check.returncode == 0, check.stderr
    assert "m3-check=PASS" in check.stdout

    report = _run_cli(
        "m3-report",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert report.returncode == 0, report.stderr
    assert "m3-report=PASS" in report.stdout
    assert (output / "report-index.json").is_file()


def test_m3_check_rejects_missing_card_artifact(tmp_path: Path) -> None:
    output, structural_output, source_lock = _build_paths(tmp_path)
    build = _run_cli(
        "m3-build",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert build.returncode == 0, build.stderr
    (output / "records" / "0.jsonl").write_bytes(b"")

    check = _run_cli(
        "m3-check",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert check.returncode != 0
    assert "m3-check=FAIL:" in check.stderr
    assert "identity set mismatch: missing=1 extra=0" in check.stderr


def test_m3_report_rejects_report_index_for_wrong_analysis_manifest(
    tmp_path: Path,
) -> None:
    output, structural_output, source_lock = _build_paths(tmp_path)
    build = _run_cli(
        "m3-build",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert build.returncode == 0, build.stderr
    report = _run_cli(
        "m3-report",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert report.returncode == 0, report.stderr

    report_index_path = output / "report-index.json"
    report_index = json.loads(report_index_path.read_bytes())
    report_index["analysis_manifest_sha256"] = "0" * 64
    report_index_path.write_bytes(canonical_json_bytes(report_index))

    rerun = _run_cli(
        "m3-report",
        "--synthetic",
        "--output",
        str(output),
        "--structural-output",
        str(structural_output),
        "--source-lock",
        str(source_lock),
    )
    assert rerun.returncode != 0
    assert "m3-report=FAIL:" in rerun.stderr
    assert "report-index analysis manifest mismatch" in rerun.stderr


def test_unrelated_cli_commands_retain_their_documentation() -> None:
    assert cli.reproduce.__doc__ == (
        "Run two independent fixture builds and require byte-for-byte parity."
    )
    assert cli.doctor.__doc__ == (
        "Check the supported Python floor without touching external systems."
    )
    assert cli.source_refresh.__doc__ == (
        "Refresh live bytes into the cache and write a reviewable lock proposal."
    )
    assert cli.corpus_build.__doc__ == (
        "Build the pinned source into a fresh generated corpus directory."
    )
    assert cli.structural_check.__doc__ == (
        "Validate pinned structural output or run its offline reproduction."
    )
