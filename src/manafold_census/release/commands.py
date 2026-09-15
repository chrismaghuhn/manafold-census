"""Explicit M5 release maintainer commands."""

from __future__ import annotations

from pathlib import Path

from .input_lock import (
    CensusInputLockStatusV1,
    CensusInputProvisioningV1,
    load_census_input_lock,
    validate_census_input_lock,
)


def check_census_input_lock_command(
    lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
) -> int:
    """Run the explicit maintainer command for one input lock."""

    try:
        lock = load_census_input_lock(lock_path)
    except FileNotFoundError as error:
        print(f"m5-input-lock={CensusInputLockStatusV1.BLOCKED}: {error}")
        return 1
    except (OSError, TypeError, ValueError) as error:
        print(f"m5-input-lock={CensusInputLockStatusV1.FAIL}: {error}")
        return 1

    result = validate_census_input_lock(
        lock,
        CensusInputProvisioningV1(
            source_lock_path=Path(source_lock_path),
            structural_output_directory=Path(structural_output_directory),
            analysis_output_directory=Path(analysis_output_directory),
        ),
    )
    for check in result.checks:
        print(f"{check.name}={check.status.value}: {check.detail}")
    print(f"m5-input-lock={result.status.value}")
    return 0 if result.status is CensusInputLockStatusV1.PASS else 1


__all__ = ["check_census_input_lock_command"]
