import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_structural_check_synthetic_cli_succeeds_offline() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "structural-check",
            "--synthetic",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "synthetic_reproduction=PASS" in result.stdout


def test_structural_build_cli_fails_for_invalid_repository_root(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "structural-build",
            "--repository-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "output"),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "structural-build=FAIL" in result.stderr


def test_structural_check_cli_requires_output_or_synthetic(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "structural-check",
            "--repository-root",
            str(tmp_path),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "structural-check=FAIL" in result.stderr
