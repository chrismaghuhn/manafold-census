from __future__ import annotations

import subprocess
import sys


def test_m6_03_commands_are_visible_in_root_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "manafold_census.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "m6-03-opportunity-build" in result.stdout
    assert "m6-03-opportunity-check" in result.stdout
    assert "m6-03-opportunity-report" in result.stdout
    assert "m6-03-opportunity-reproduce" in result.stdout
    assert "m6-02-inventory-build" in result.stdout
