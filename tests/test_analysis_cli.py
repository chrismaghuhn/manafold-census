from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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
    assert (output / "analysis-manifest.json").is_file()

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
