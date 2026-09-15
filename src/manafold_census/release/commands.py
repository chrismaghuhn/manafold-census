"""Explicit M5 release maintainer commands."""

from __future__ import annotations

from pathlib import Path

from ..capability.input import FrozenM3InputV1
from .authority_package import validate_authority_package
from .input_lock import (
    CensusInputLockStatusV1,
    CensusInputProvisioningV1,
    load_census_input_lock,
    validate_census_input_lock,
)
from .m4_orchestration import build_real_m4_snapshot


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


def build_real_m4_snapshot_command(
    input_lock_path: str | Path,
    authority_package_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    output_directory: str | Path,
) -> int:
    """Build the first real M4 snapshot from explicit M5 inputs."""

    try:
        lock = load_census_input_lock(input_lock_path)
    except FileNotFoundError as error:
        print(f"m5-m4-build=BLOCKED: {error}")
        return 1
    except (OSError, TypeError, ValueError) as error:
        print(f"m5-m4-build=FAIL: {error}")
        return 1

    provisioning = CensusInputProvisioningV1(
        source_lock_path=Path(source_lock_path),
        structural_output_directory=Path(structural_output_directory),
        analysis_output_directory=Path(analysis_output_directory),
    )
    input_result = validate_census_input_lock(lock, provisioning)
    for check in input_result.checks:
        print(f"{check.name}={check.status.value}: {check.detail}")
    if input_result.status is not CensusInputLockStatusV1.PASS:
        print(f"m5-m4-build={input_result.status.value}")
        return 1
    if input_result.m3_corpus is None:
        print("m5-m4-build=FAIL: M5-02 did not return an M3 corpus")
        return 1
    try:
        result = build_real_m4_snapshot(
            authority_package_directory=authority_package_path,
            m3_input=FrozenM3InputV1(
                structural_output_directory=provisioning.structural_output_directory,
                analysis_output_directory=provisioning.analysis_output_directory,
                source_lock_path=provisioning.source_lock_path,
                expected_analysis_manifest_sha256=lock.m3_analysis_manifest_sha256,
            ),
            lock=lock,
            corpus=input_result.m3_corpus,
            output_directory=output_directory,
        )
    except FileNotFoundError as error:
        print(f"m5-m4-build=BLOCKED: {error}")
        return 1
    except OSError as error:
        print(f"m5-m4-build=BLOCKED: {error}")
        return 1
    except (TypeError, ValueError) as error:
        print(f"m5-m4-build=FAIL: {error}")
        return 1
    print("m4-parent=null")
    print(
        "authority-m4-record-set-parity="
        + ("PASS" if result.authority_package_record_set_parity else "FAIL")
    )
    print(f"m4-manifest-sha256={result.manifest.digest()}")
    print("m5-m4-build=PASS")
    return 0


__all__ = [
    "build_real_m4_snapshot_command",
    "check_census_authority_package_command",
    "check_census_input_lock_command",
]
