"""Explicit M5 release maintainer commands."""

from __future__ import annotations

from pathlib import Path

from .authority_package import validate_authority_package
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


def check_census_authority_package_command(
    package_path: str | Path,
    lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
) -> int:
    """Validate one real M5-03 authority package from explicit inputs."""

    try:
        lock = load_census_input_lock(lock_path)
    except FileNotFoundError as error:
        print(f"m5-authority=BLOCKED: {error}")
        return 1
    except (OSError, TypeError, ValueError) as error:
        print(f"m5-authority=FAIL: {error}")
        return 1

    input_result = validate_census_input_lock(
        lock,
        CensusInputProvisioningV1(
            source_lock_path=Path(source_lock_path),
            structural_output_directory=Path(structural_output_directory),
            analysis_output_directory=Path(analysis_output_directory),
        ),
    )
    for check in input_result.checks:
        print(f"{check.name}={check.status.value}: {check.detail}")
    if input_result.status is not CensusInputLockStatusV1.PASS:
        print(f"m5-authority={input_result.status.value}")
        return 1
    if input_result.m3_corpus is None:
        print("m5-authority=FAIL: M5-02 did not return an M3 corpus")
        return 1
    try:
        package = validate_authority_package(package_path, lock, input_result.m3_corpus)
    except FileNotFoundError as error:
        print(f"m5-authority=BLOCKED: {error}")
        return 1
    except OSError as error:
        print(f"m5-authority=BLOCKED: {error}")
        return 1
    except (TypeError, ValueError) as error:
        print(f"m5-authority=FAIL: {error}")
        return 1
    print(f"authority-package-digest={package.manifest.authority_package_digest}")
    print(f"authority-sra-count={len(package.admissibility)}")
    print(f"authority-capability-count={len(package.capability_definitions)}")
    print(f"authority-link-count={len(package.links)}")
    print(f"authority-mapping-decision-count={len(package.mapping_decisions)}")
    print("m5-authority=PASS")
    return 0


__all__ = [
    "check_census_authority_package_command",
    "check_census_input_lock_command",
]
