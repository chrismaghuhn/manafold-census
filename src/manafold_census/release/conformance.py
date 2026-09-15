"""Final Census 0.1 release-conformance and reproduction checks."""

from __future__ import annotations

import filecmp
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..capability.input import M3RequirementCorpusV1
from ..digest import domain_digest, measure_file, sha256_bytes
from ..query.api import open_bundle
from ..reports.build import build_census_derived
from ..reports.model import DERIVED_FILES
from .bundle import (
    CensusBundleContentsV1,
    build_census_bundle,
    validate_census_bundle,
)
from .input_lock import (
    CensusInputLockStatusV1,
    CensusInputLockV1,
    CensusInputProvisioningV1,
    load_census_input_lock,
    validate_census_input_lock,
)

CONFORMANCE_SCHEMA = "census.m5-release-conformance.v1"
CONFORMANCE_DIGEST_DOMAIN = CONFORMANCE_SCHEMA
HARD_GATE_NAMES = (
    "CENSUS_AUTHORITATIVE_BYTES_PARITY",
    "REPORT_INDEX_BYTES_PARITY",
    "RELEASE_CANDIDATE_REPRODUCTION",
    "RELEASE_CANDIDATE_AUDITABILITY",
)
EXPERIMENTAL_GATE_NAMES = ("WINDOWS_EXE_BYTE_PARITY",)


class ReleaseConformanceError(ValueError):
    """Raised when an explicit release-conformance input is invalid."""


class ReleaseConformanceBlockedError(FileNotFoundError):
    """Raised when an explicit release-conformance artifact is unavailable."""


def _file_map(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }


def _tree_digest(root: Path, relative_paths: Iterable[str]) -> str:
    entries: list[dict[str, JSONValue]] = []
    for relative_path in sorted(relative_paths):
        measurement = measure_file(root / Path(relative_path))
        entries.append(
            {
                "path": relative_path,
                "sha256": measurement.sha256,
                "byte_length": measurement.byte_length,
            }
        )
    return domain_digest(CONFORMANCE_DIGEST_DOMAIN, cast(JSONValue, entries))


def _compare_files(
    left_root: Path,
    right_root: Path,
    label: str,
    relative_paths: Sequence[str] | None = None,
) -> tuple[int, str]:
    left_files = _file_map(left_root)
    right_files = _file_map(right_root)
    if relative_paths is None:
        left_names = tuple(sorted(left_files))
        right_names = tuple(sorted(right_files))
        if left_names != right_names:
            raise ReleaseConformanceError(f"{label} file sets differ")
        names = left_names
    else:
        names = tuple(sorted(relative_paths))
        for relative_path in names:
            if relative_path not in left_files or relative_path not in right_files:
                raise ReleaseConformanceBlockedError(
                    f"{label} is missing {relative_path}"
                )
    for relative_path in names:
        if not filecmp.cmp(
            left_files[relative_path], right_files[relative_path], shallow=False
        ):
            raise ReleaseConformanceError(f"{label} bytes differ: {relative_path}")
    return len(names), _tree_digest(left_root, names)


def _sha256_json_file(path: Path) -> str:
    document = json.loads(path.read_bytes())
    return sha256_bytes(canonical_json_bytes(document))


@dataclass(frozen=True, slots=True)
class ReleaseCandidateEvidenceV1:
    """Path-free identity summary for one reproduced candidate pair."""

    label: str
    bundle_file_count: int
    bundle_tree_digest: str
    census_release_id: str
    census_manifest_sha256: str
    derived_file_count: int
    derived_tree_digest: str
    report_index_sha256: str
    index_manifest_sha256: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "label",
        "bundle_file_count",
        "bundle_tree_digest",
        "census_release_id",
        "census_manifest_sha256",
        "derived_file_count",
        "derived_tree_digest",
        "report_index_sha256",
        "index_manifest_sha256",
    }

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "label": self.label,
            "bundle_file_count": self.bundle_file_count,
            "bundle_tree_digest": self.bundle_tree_digest,
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "derived_file_count": self.derived_file_count,
            "derived_tree_digest": self.derived_tree_digest,
            "report_index_sha256": self.report_index_sha256,
            "index_manifest_sha256": self.index_manifest_sha256,
        }


@dataclass(frozen=True, slots=True)
class ReleaseConformanceResultV1:
    """Auditable result of two fresh Census 0.1 candidate reproductions."""

    census_release_version: str
    source_lock_digest: str
    candidate_runs: tuple[ReleaseCandidateEvidenceV1, ...]
    authoritative_file_count: int
    derived_file_count: int
    hard_gates: tuple[tuple[str, str], ...]
    experimental_gates: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if len(self.candidate_runs) != 2:
            raise ValueError("release conformance requires exactly two candidates")
        if tuple(name for name, _status in self.hard_gates) != HARD_GATE_NAMES:
            raise ValueError("release conformance hard gates are not canonical")
        if tuple(name for name, _status in self.experimental_gates) != (
            *EXPERIMENTAL_GATE_NAMES,
        ):
            raise ValueError("release conformance experimental gates are not canonical")
        if any(status != "PASS" for _name, status in self.hard_gates):
            raise ValueError("release conformance contains a failed hard gate")
        if any(status != "EXPERIMENTAL" for _name, status in self.experimental_gates):
            raise ValueError("release conformance experimental status changed")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": CONFORMANCE_SCHEMA,
            "census_release_version": self.census_release_version,
            "source_lock_digest": self.source_lock_digest,
            "candidate_runs": [item.to_wire() for item in self.candidate_runs],
            "authoritative_file_count": self.authoritative_file_count,
            "derived_file_count": self.derived_file_count,
            "hard_gates": {name: status for name, status in self.hard_gates},
            "experimental_gates": {
                name: status for name, status in self.experimental_gates
            },
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire())


def _validated_lock_inputs(
    input_lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
) -> tuple[CensusInputLockV1, M3RequirementCorpusV1]:
    lock = load_census_input_lock(input_lock_path)
    result = validate_census_input_lock(
        lock,
        CensusInputProvisioningV1(
            source_lock_path=Path(source_lock_path),
            structural_output_directory=Path(structural_output_directory),
            analysis_output_directory=Path(analysis_output_directory),
        ),
    )
    if result.status is CensusInputLockStatusV1.BLOCKED:
        raise ReleaseConformanceBlockedError(
            f"M5-02 input validation is {result.status.value}"
        )
    if result.status is not CensusInputLockStatusV1.PASS:
        raise ReleaseConformanceError(
            f"M5-02 input validation is {result.status.value}"
        )
    if result.m3_corpus is None:
        raise ReleaseConformanceError("M5-02 validation returned no M3 corpus")
    return lock, result.m3_corpus


def _candidate_evidence(
    label: str,
    bundle: CensusBundleContentsV1,
    derived_directory: Path,
    derived_file_count: int,
    derived_tree_digest: str,
) -> ReleaseCandidateEvidenceV1:
    manifest_path = bundle.root / "census-manifest.json"
    return ReleaseCandidateEvidenceV1(
        label=label,
        bundle_file_count=len(_file_map(bundle.root)),
        bundle_tree_digest=_tree_digest(bundle.root, _file_map(bundle.root)),
        census_release_id=bundle.manifest.census_release_id,
        census_manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
        derived_file_count=derived_file_count,
        derived_tree_digest=derived_tree_digest,
        report_index_sha256=_sha256_json_file(
            derived_directory / "reports/report-index.json"
        ),
        index_manifest_sha256=_sha256_json_file(
            derived_directory / "indexes/index-manifest.json"
        ),
    )


def _write_evidence(path: Path, result: ReleaseConformanceResultV1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result.canonical_bytes())


def run_release_conformance(
    *,
    input_lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    authority_package_directory: str | Path,
    m4_output_directory: str | Path,
    output_root: str | Path,
    evidence_path: str | Path,
) -> ReleaseConformanceResultV1:
    """Build and compare two fresh release candidates from frozen inputs."""

    output = Path(output_root)
    evidence = Path(evidence_path)
    if output.exists():
        raise ReleaseConformanceError("release-conformance output root already exists")
    if evidence.exists():
        raise ReleaseConformanceError("release-conformance evidence already exists")
    try:
        evidence.resolve().relative_to(output.resolve())
    except ValueError:
        pass
    else:
        raise ReleaseConformanceError("evidence must be outside output root")

    lock, corpus = _validated_lock_inputs(
        input_lock_path,
        source_lock_path,
        structural_output_directory,
        analysis_output_directory,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    bundle_directories = (output / "bundle-a", output / "bundle-b")
    derived_directories = (output / "derived-a", output / "derived-b")
    bundle_results = tuple(
        build_census_bundle(
            input_lock_path=input_lock_path,
            source_lock_path=source_lock_path,
            structural_output_directory=structural_output_directory,
            analysis_output_directory=analysis_output_directory,
            authority_package_directory=authority_package_directory,
            m4_output_directory=m4_output_directory,
            output_directory=directory,
        )
        for directory in bundle_directories
    )
    bundle_contents = tuple(
        validate_census_bundle(directory, lock, corpus)
        for directory in bundle_directories
    )
    derived_results = tuple(
        build_census_derived(bundle_directory, directory)
        for bundle_directory, directory in zip(
            bundle_directories, derived_directories, strict=True
        )
    )
    for directory in derived_directories:
        open_bundle(directory)

    authoritative_count, authoritative_digest = _compare_files(
        bundle_directories[0], bundle_directories[1], "authoritative candidate"
    )
    derived_count, derived_digest = _compare_files(
        derived_directories[0], derived_directories[1], "derived candidate"
    )
    report_index_count, report_index_digest = _compare_files(
        derived_directories[0],
        derived_directories[1],
        "report/index candidate",
        tuple(sorted(DERIVED_FILES)),
    )
    if report_index_count != len(DERIVED_FILES):
        raise ReleaseConformanceError(
            "derived file count is not the frozen ten-file set"
        )
    if bundle_results[0].manifest != bundle_results[1].manifest:
        raise ReleaseConformanceError("bundle candidate manifests differ")
    if derived_results[0].report_index != derived_results[1].report_index:
        raise ReleaseConformanceError("report indexes differ")
    if derived_results[0].index_manifest != derived_results[1].index_manifest:
        raise ReleaseConformanceError("index manifests differ")
    if authoritative_digest != _tree_digest(
        bundle_directories[0], _file_map(bundle_directories[0])
    ):
        raise ReleaseConformanceError("authoritative candidate digest is stale")
    if derived_digest != _tree_digest(
        derived_directories[0], _file_map(derived_directories[0])
    ):
        raise ReleaseConformanceError("derived candidate digest is stale")

    result = ReleaseConformanceResultV1(
        census_release_version=bundle_contents[0].manifest.census_release_version,
        source_lock_digest=lock.source_lock_digest,
        candidate_runs=tuple(
            _candidate_evidence(
                label,
                bundle,
                derived_directory,
                derived_count,
                derived_digest,
            )
            for label, bundle, derived_directory in zip(
                ("candidate-a", "candidate-b"),
                bundle_contents,
                derived_directories,
                strict=True,
            )
        ),
        authoritative_file_count=authoritative_count,
        derived_file_count=derived_count,
        hard_gates=tuple((name, "PASS") for name in HARD_GATE_NAMES),
        experimental_gates=tuple(
            (name, "EXPERIMENTAL") for name in EXPERIMENTAL_GATE_NAMES
        ),
    )
    if report_index_digest != _tree_digest(
        derived_directories[0], tuple(sorted(DERIVED_FILES))
    ):
        raise ReleaseConformanceError("report/index parity digest is stale")
    _write_evidence(evidence, result)
    return result


__all__ = [
    "CONFORMANCE_SCHEMA",
    "EXPERIMENTAL_GATE_NAMES",
    "HARD_GATE_NAMES",
    "ReleaseCandidateEvidenceV1",
    "ReleaseConformanceBlockedError",
    "ReleaseConformanceError",
    "ReleaseConformanceResultV1",
    "run_release_conformance",
]
