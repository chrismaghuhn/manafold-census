"""Explicit M5 release maintainer commands."""

from __future__ import annotations

from pathlib import Path

from ..capability.input import FrozenM3InputV1
from ..reports.build import build_census_derived
from .authority_package import validate_authority_package
from .bundle import build_census_bundle
from .conformance import (
    ReleaseConformanceBlockedError,
    ReleaseConformanceError,
    run_release_conformance,
)
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


def build_census_bundle_command(
    input_lock_path: str | Path,
    authority_package_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    m4_output_directory: str | Path,
    output_directory: str | Path,
) -> int:
    """Build the first self-contained Census bundle from explicit inputs."""

    try:
        lock = load_census_input_lock(input_lock_path)
    except FileNotFoundError as error:
        print(f"m5-bundle-build=BLOCKED: {error}")
        return 1
    except (OSError, TypeError, ValueError) as error:
        print(f"m5-bundle-build=FAIL: {error}")
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
        print(f"m5-bundle-build={input_result.status.value}")
        return 1
    if input_result.m3_corpus is None:
        print("m5-bundle-build=FAIL: M5-02 did not return an M3 corpus")
        return 1
    try:
        result = build_census_bundle(
            input_lock_path=input_lock_path,
            source_lock_path=source_lock_path,
            structural_output_directory=structural_output_directory,
            analysis_output_directory=analysis_output_directory,
            authority_package_directory=authority_package_path,
            m4_output_directory=m4_output_directory,
            output_directory=output_directory,
        )
    except FileNotFoundError as error:
        print(f"m5-bundle-build=BLOCKED: {error}")
        return 1
    except OSError as error:
        print(f"m5-bundle-build=BLOCKED: {error}")
        return 1
    except (TypeError, ValueError) as error:
        print(f"m5-bundle-build=FAIL: {error}")
        return 1
    m4_component = next(
        item for item in result.manifest.authoritative_components if item.role == "m4"
    )
    print(f"m4-manifest-sha256={m4_component.sha256}")
    print(f"census-release-id={result.manifest.census_release_id}")
    print(f"census-manifest-sha256={result.census_manifest_sha256}")
    print("bundle-authoritative-components=5")
    print("bundle-reread=PASS")
    print("m5-bundle-build=PASS")
    return 0


def build_census_derived_command(
    bundle_path: str | Path,
    output_directory: str | Path,
) -> int:
    """Build reports and indexes from one explicit frozen Census bundle."""

    try:
        result = build_census_derived(bundle_path, output_directory)
    except FileNotFoundError as error:
        print(f"m5-derived-build=BLOCKED: {error}")
        return 1
    except OSError as error:
        print(f"m5-derived-build=BLOCKED: {error}")
        return 1
    except (TypeError, ValueError) as error:
        print(f"m5-derived-build=FAIL: {error}")
        return 1
    print(f"census-release-id={result.census_release_id}")
    print(f"census-manifest-sha256={result.census_manifest_sha256}")
    print(f"report-descriptor-count={len(result.report_index.report_descriptors)}")
    print(f"index-descriptor-count={len(result.index_manifest.index_descriptors)}")
    print("report-index=PASS")
    print("index-manifest=PASS")
    print("m5-derived-build=PASS")
    return 0


def build_release_conformance_command(
    input_lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    authority_package_path: str | Path,
    m4_output_directory: str | Path,
    output_root: str | Path,
    evidence_path: str | Path,
) -> int:
    """Run the final two-candidate Census 0.1 conformance check."""

    try:
        result = run_release_conformance(
            input_lock_path=input_lock_path,
            source_lock_path=source_lock_path,
            structural_output_directory=structural_output_directory,
            analysis_output_directory=analysis_output_directory,
            authority_package_directory=authority_package_path,
            m4_output_directory=m4_output_directory,
            output_root=output_root,
            evidence_path=evidence_path,
        )
    except (ReleaseConformanceBlockedError, FileNotFoundError) as error:
        print(f"m5-release-conformance=BLOCKED: {error}")
        return 1
    except OSError as error:
        print(f"m5-release-conformance=BLOCKED: {error}")
        return 1
    except (TypeError, ValueError, ReleaseConformanceError) as error:
        print(f"m5-release-conformance=FAIL: {error}")
        return 1
    for name, status in result.hard_gates:
        print(f"{name}={status}")
    for name, status in result.experimental_gates:
        print(f"{name.lower().replace('_', '-')}={status}")
    for candidate in result.candidate_runs:
        print(f"{candidate.label}-bundle-file-count={candidate.bundle_file_count}")
        print(f"{candidate.label}-derived-file-count={candidate.derived_file_count}")
        print(f"{candidate.label}-census-release-id={candidate.census_release_id}")
        print(f"{candidate.label}-bundle-tree-digest={candidate.bundle_tree_digest}")
        print(f"{candidate.label}-derived-tree-digest={candidate.derived_tree_digest}")
    print(f"authoritative-file-count={result.authoritative_file_count}")
    print(f"derived-file-count={result.derived_file_count}")
    print("m5-release-conformance=PASS")
    return 0


__all__ = [
    "build_census_bundle_command",
    "build_census_derived_command",
    "build_release_conformance_command",
    "build_real_m4_snapshot_command",
    "check_census_authority_package_command",
    "check_census_input_lock_command",
]
