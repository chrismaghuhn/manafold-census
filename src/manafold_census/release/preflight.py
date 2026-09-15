"""Availability and exact-file-set checks for frozen M1/M3 inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..analysis.manifest import SHARD_NAMES
from .input_lock import (
    CensusInputCheckV1,
    CensusInputLockStatusV1,
    CensusInputProvisioningV1,
)


@dataclass(frozen=True, slots=True)
class CensusInputPreflightResultV1:
    status: CensusInputLockStatusV1
    checks: tuple[CensusInputCheckV1, ...]


def _result(
    status: CensusInputLockStatusV1,
    name: str,
    detail: str,
) -> CensusInputPreflightResultV1:
    return CensusInputPreflightResultV1(
        status=status,
        checks=(CensusInputCheckV1(name, status, detail),),
    )


def _require_file(path: Path, name: str) -> CensusInputPreflightResultV1 | None:
    if not path.is_file():
        return _result(
            CensusInputLockStatusV1.BLOCKED,
            name,
            f"{name} is missing or has the wrong type: {path}",
        )
    return None


def _require_directory(path: Path, name: str) -> CensusInputPreflightResultV1 | None:
    if not path.is_dir():
        return _result(
            CensusInputLockStatusV1.BLOCKED,
            name,
            f"{name} is missing or has the wrong type: {path}",
        )
    return None


def _check_shard_directory(
    path: Path,
    name: str,
) -> CensusInputPreflightResultV1 | None:
    directory_result = _require_directory(path, name)
    if directory_result is not None:
        return directory_result
    expected_names = {f"{shard}.jsonl" for shard in SHARD_NAMES}
    try:
        actual_names = {entry.name for entry in path.iterdir()}
    except OSError as error:
        return _result(
            CensusInputLockStatusV1.BLOCKED,
            name,
            f"{name} cannot be enumerated: {error}",
        )
    missing = sorted(expected_names - actual_names)
    if missing:
        return _result(
            CensusInputLockStatusV1.BLOCKED,
            name,
            f"{name} is missing required shard: {path / missing[0]}",
        )
    unexpected = sorted(actual_names - expected_names)
    if unexpected:
        return _result(
            CensusInputLockStatusV1.FAIL,
            name,
            f"{name} contains unexpected entry: {path / unexpected[0]}",
        )
    for shard in SHARD_NAMES:
        shard_result = _require_file(path / f"{shard}.jsonl", name)
        if shard_result is not None:
            return shard_result
    return None


def preflight_census_input_provisioning(
    provisioning: CensusInputProvisioningV1,
) -> CensusInputPreflightResultV1:
    """Check required M1/M3 paths before invoking frozen M3 validation."""

    if not isinstance(provisioning, CensusInputProvisioningV1):
        raise TypeError("provisioning must be CensusInputProvisioningV1")
    result = _require_file(provisioning.source_lock_path, "source_lock_path")
    if result is not None:
        return result
    for path, name in (
        (provisioning.structural_output_directory, "structural_output_directory"),
        (provisioning.analysis_output_directory, "analysis_output_directory"),
    ):
        result = _require_directory(path, name)
        if result is not None:
            return result
    required_files = (
        (
            "M1 structural manifest",
            provisioning.structural_output_directory / "structural-index-manifest.json",
        ),
        (
            "M3 analysis manifest",
            provisioning.analysis_output_directory / "analysis-manifest.json",
        ),
    )
    for name, path in required_files:
        result = _require_file(path, name)
        if result is not None:
            return result
    for path, name in (
        (provisioning.structural_output_directory / "records", "M1 records directory"),
        (provisioning.analysis_output_directory / "records", "M3 records directory"),
        (provisioning.analysis_output_directory / "trace", "M3 trace directory"),
    ):
        result = _check_shard_directory(path, name)
        if result is not None:
            return result
    checks = tuple(
        CensusInputCheckV1(name, CensusInputLockStatusV1.PASS, "verified")
        for name in (
            "source lock",
            "M1 structural manifest",
            "M3 analysis manifest",
            "M1 records directory",
            "M3 records directory",
            "M3 trace directory",
        )
    )
    return CensusInputPreflightResultV1(
        status=CensusInputLockStatusV1.PASS,
        checks=checks,
    )


__all__ = [
    "CensusInputPreflightResultV1",
    "preflight_census_input_provisioning",
]
