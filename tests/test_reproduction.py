import re
import subprocess
import sys
from pathlib import Path

from manafold_census.cli import build_fixture, directory_digest


def test_two_independent_fixture_builds_have_byte_parity(tmp_path) -> None:
    build_a = tmp_path / "build-a"
    build_b = tmp_path / "build-b"
    digest_a = build_fixture(build_a)
    digest_b = build_fixture(build_b)

    files_a = sorted(path.relative_to(build_a) for path in build_a.rglob("*"))
    files_b = sorted(path.relative_to(build_b) for path in build_b.rglob("*"))
    assert files_a == files_b
    assert files_a
    for relative_path in files_a:
        assert (build_a / relative_path).read_bytes() == (
            build_b / relative_path
        ).read_bytes()

    assert digest_a == digest_b == directory_digest(build_a)


def test_reproduce_command_reports_equal_run_digests() -> None:
    repository_root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "manafold_census.cli", "reproduce"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    run_a = re.search(r"run_a_digest=([0-9a-f]{64})", result.stdout)
    run_b = re.search(r"run_b_digest=([0-9a-f]{64})", result.stdout)
    assert run_a is not None
    assert run_b is not None
    assert run_a.group(1) == run_b.group(1)
