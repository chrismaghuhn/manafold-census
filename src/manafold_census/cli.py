"""Minimal maintainer CLI for the Task 00 deterministic fixture pipeline."""

from __future__ import annotations

import argparse
import filecmp
import json
import platform
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from .canonical import JSONValue, canonical_json_bytes
from .digest import (
    REPRODUCTION_DOMAIN,
    domain_digest,
    measure_file,
    sha256_bytes,
)
from .models import (
    ArtifactManifest,
    DatasetManifest,
    SourceLock,
    StudySpec,
)
from .resources import project_data_root
from .validation import validate_document, validate_source_file


def _read_fixture_spec(filename: str) -> dict[str, object]:
    path = project_data_root() / "fixtures" / "specs" / filename
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"fixture spec must be an object: {filename}")
    return value


def _file_map(directory: Path) -> dict[str, Path]:
    return {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }


def directory_digest(directory: str | Path) -> str:
    """Return a stable digest of relative output names and their file bytes."""

    root = Path(directory)
    entries = [
        {
            "path": relative_path,
            "sha256": (measurement := measure_file(path)).sha256,
            "byte_length": measurement.byte_length,
        }
        for relative_path, path in sorted(_file_map(root).items())
    ]
    return domain_digest(REPRODUCTION_DOMAIN, cast(JSONValue, entries))


def build_fixture(output_dir: str | Path) -> str:
    """Build the synthetic source-to-artifact fixture into a fresh directory."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if any(output_path.iterdir()):
        raise ValueError("fixture output directory must be empty")

    source_path = project_data_root() / "fixtures" / "source" / "example.txt"
    source_lock = SourceLock.from_wire(_read_fixture_spec("example-source-lock.json"))
    source_artifact = source_lock.artifacts[0]
    validate_source_file(source_artifact, source_path)
    dataset = DatasetManifest.from_wire(_read_fixture_spec("example-dataset.json"))
    study = StudySpec.from_wire(_read_fixture_spec("example-study.json"))

    if dataset.source_lock_digest != source_lock.digest():
        raise ValueError("fixture dataset does not reference its source lock")

    artifact_content = canonical_json_bytes(
        {
            "dataset_digest": dataset.digest(),
            "record_count": dataset.record_count,
            "source_lock_digest": source_lock.digest(),
            "study_digest": study.digest(),
        }
    )
    artifact_manifest = ArtifactManifest(
        artifact_id="example-artifact",
        artifact_kind="fixture-output.v1",
        study_digest=study.digest(),
        content_sha256=sha256_bytes(artifact_content),
        byte_length=len(artifact_content),
    )

    documents = {
        "source-artifact.json": source_artifact.to_wire(),
        "source-lock.json": source_lock.to_wire(),
        "dataset-manifest.json": dataset.to_wire(),
        "study-spec.json": study.to_wire(),
        "artifact-manifest.json": artifact_manifest.to_wire(),
    }
    schema_by_filename = {
        "source-artifact.json": "source-artifact.v1.schema.json",
        "source-lock.json": "source-lock.v1.schema.json",
        "dataset-manifest.json": "dataset-manifest.v1.schema.json",
        "study-spec.json": "study-spec.v1.schema.json",
        "artifact-manifest.json": "artifact-manifest.v1.schema.json",
    }
    for filename, document in documents.items():
        validate_document(document, schema_by_filename[filename])
        (output_path / filename).write_bytes(canonical_json_bytes(document))
    (output_path / "artifact-content.json").write_bytes(artifact_content)
    return directory_digest(output_path)


def reproduce() -> tuple[str, str]:
    """Run two independent fixture builds and require byte-for-byte parity."""

    with (
        tempfile.TemporaryDirectory(prefix="census-reproduce-a-") as temp_a,
        tempfile.TemporaryDirectory(prefix="census-reproduce-b-") as temp_b,
    ):
        path_a = Path(temp_a)
        path_b = Path(temp_b)
        digest_a = build_fixture(path_a)
        digest_b = build_fixture(path_b)
        files_a = _file_map(path_a)
        files_b = _file_map(path_b)
        if set(files_a) != set(files_b):
            raise RuntimeError("reproduction byte parity failed: file sets differ")
        for relative_path in sorted(files_a):
            if not filecmp.cmp(
                files_a[relative_path], files_b[relative_path], shallow=False
            ):
                raise RuntimeError("reproduction byte parity failed: " + relative_path)
        if digest_a != digest_b:
            raise RuntimeError("reproduction digest parity failed")
    print(f"run_a_digest={digest_a}")
    print(f"run_b_digest={digest_b}")
    print("reproduction=PASS")
    return digest_a, digest_b


def doctor() -> int:
    """Check the supported Python floor without touching external systems."""

    version = platform.python_version()
    if sys.version_info[:2] < (3, 12):  # noqa: UP036 - doctor checks the runtime floor
        print(f"python_version={version}")
        print("doctor=FAIL: Python 3.12+ is required", file=sys.stderr)
        return 1
    print(f"python_version={version}")
    print("doctor=PASS")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manafold_census")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="check the local Python baseline")
    subparsers.add_parser("reproduce", help="run the two-build parity check")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "reproduce":
        try:
            reproduce()
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            print(f"reproduction=FAIL: {error}", file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
