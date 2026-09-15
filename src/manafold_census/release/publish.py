"""Exact input copying and manifest reread for Census bundle publication."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..canonical import canonical_json_bytes
from ..digest import sha256_bytes
from ..validation import validate_document
from .authority_package import AUTHORITY_PACKAGE_FILES
from .manifest import (
    BUNDLE_MANIFEST_FILENAME,
    CensusBundleManifestV1,
)

SHARD_NAMES = tuple("0123456789abcdef")
M1_BUNDLE_FILES = frozenset(
    {"structural-index-manifest.json"}
    | {f"records/{shard}.jsonl" for shard in SHARD_NAMES}
)
M3_BUNDLE_FILES = frozenset(
    {"analysis-manifest.json"}
    | {f"records/{shard}.jsonl" for shard in SHARD_NAMES}
    | {f"trace/{shard}.jsonl" for shard in SHARD_NAMES}
)
AUTHORITY_BUNDLE_FILES = frozenset(
    {"authority-manifest.json", *AUTHORITY_PACKAGE_FILES}
)


def _copy_paths(
    source_root: Path,
    destination_root: Path,
    relative_paths: set[str] | frozenset[str],
) -> None:
    if not source_root.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_root}")
    for relative_path in sorted(relative_paths):
        source = source_root / Path(relative_path)
        if not source.is_file():
            raise FileNotFoundError(f"missing source artifact: {source}")
        destination = destination_root / Path(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def copy_bundle_inputs(
    staging_root: Path,
    *,
    source_lock_path: Path,
    structural_output_directory: Path,
    analysis_output_directory: Path,
    authority_package_directory: Path,
    m4_output_directory: Path,
) -> None:
    """Copy only the fixed authoritative Census bundle input topology."""

    source_destination = staging_root / "inputs/source-lock.json"
    if not source_lock_path.is_file():
        raise FileNotFoundError(f"source lock does not exist: {source_lock_path}")
    source_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_lock_path, source_destination)
    _copy_paths(
        structural_output_directory,
        staging_root / "inputs/m1",
        M1_BUNDLE_FILES,
    )
    _copy_paths(
        analysis_output_directory,
        staging_root / "inputs/m3",
        M3_BUNDLE_FILES,
    )
    _copy_paths(
        authority_package_directory,
        staging_root / "inputs/m4-authority",
        AUTHORITY_BUNDLE_FILES,
    )
    m4_files = {
        path.relative_to(m4_output_directory).as_posix()
        for path in m4_output_directory.rglob("*")
        if path.is_file()
    }
    _copy_paths(m4_output_directory, staging_root / "inputs/m4", m4_files)


def read_bundle_manifest(bundle_root: Path) -> CensusBundleManifestV1:
    """Read and validate one canonical bundle manifest."""

    try:
        raw = (bundle_root / BUNDLE_MANIFEST_FILENAME).read_bytes()
    except FileNotFoundError:
        raise
    except OSError as error:
        raise ValueError("Census bundle manifest cannot be read") from error
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Census bundle manifest cannot be read as JSON") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("Census bundle manifest is not canonical JSON")
    validate_document(document, "census-bundle-manifest.v1.schema.json")
    return CensusBundleManifestV1.from_wire(document)


def file_descriptor_matches(path: Path, sha256: str, byte_length: int) -> bool:
    """Return whether one file has the exact declared raw identity."""

    try:
        raw = path.read_bytes()
    except OSError:
        return False
    return len(raw) == byte_length and sha256_bytes(raw) == sha256


__all__ = [
    "AUTHORITY_BUNDLE_FILES",
    "M1_BUNDLE_FILES",
    "M3_BUNDLE_FILES",
    "copy_bundle_inputs",
    "file_descriptor_matches",
    "read_bundle_manifest",
]
