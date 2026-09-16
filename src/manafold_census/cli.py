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

from .analysis.cli_support import m3_command
from .canonical import JSONValue, canonical_json_bytes
from .capability.commands import (
    build_synthetic_m4_command,
    check_synthetic_m4_command,
    report_synthetic_m4_command,
)
from .corpus.build import (
    build_pinned_corpus,
    load_source_lock,
)
from .corpus.build import (
    run_synthetic_reproduction as run_corpus_synthetic_reproduction,
)
from .corpus.check import validate_corpus_output
from .digest import REPRODUCTION_DOMAIN, domain_digest, measure_file, sha256_bytes
from .explorer.cli import add_explorer_parser, dispatch_explorer_command
from .inventory.cli import add_m6_02_parsers, dispatch_m6_02_command
from .models import ArtifactManifest, DatasetManifest, SourceLock, StudySpec
from .release.cli import add_m5_parsers, dispatch_m5_command
from .resources import project_data_root
from .source.scryfall import discover_oracle_cards, refresh_current_source
from .source.transfer import fetch_pinned_source
from .structural.build import build_pinned_structural
from .structural.build import (
    run_synthetic_reproduction as run_structural_synthetic_reproduction,
)
from .structural.check import validate_pinned_structural_output
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


def source_discover() -> int:
    """Print the current source facts without writing any local state."""

    observation = discover_oracle_cards()
    print(f"bulk_type={observation.bulk_type}")
    print(f"observed_format={observation.advertised_format}")
    print(f"download_field={observation.download_field}")
    print(f"source_id={observation.source_id}")
    print(f"updated_at={observation.updated_at or 'NOT_SUPPLIED'}")
    print(f"source_locator={observation.download_uri}")
    print(
        "compressed_size="
        + (
            str(observation.compressed_size)
            if observation.compressed_size is not None
            else "NOT_SUPPLIED"
        )
    )
    print("source_discovery=PASS")
    return 0


def source_refresh(repository_root: str | Path, proposal_path: str | Path) -> int:
    """Refresh live bytes into the cache and write a reviewable lock proposal."""

    root = Path(repository_root)
    proposal = Path(proposal_path)
    if not proposal.is_absolute():
        proposal = root / proposal
    observation, artifact, lock = refresh_current_source(
        cache_root=root / ".cache" / "sources" / "scryfall",
        proposal_path=proposal,
    )
    print(f"bulk_type={observation.bulk_type}")
    print(f"observed_format={observation.advertised_format}")
    print(f"download_field={observation.download_field}")
    print(f"source_id={observation.source_id}")
    print(f"source_sha256={artifact.sha256}")
    print(f"source_byte_length={artifact.byte_length}")
    print(f"source_media_type={artifact.media_type}")
    print(f"source_lock_digest={lock.digest()}")
    print("source_refresh=PASS")
    return 0


def source_fetch_pinned(repository_root: str | Path) -> int:
    """Fetch and verify the exact source artifact in the committed lock."""

    root = Path(repository_root)
    lock = load_source_lock(root / "source-locks" / "scryfall-oracle-v1.json")
    artifact = fetch_pinned_source(
        lock.artifacts[0], root / ".cache" / "sources" / "scryfall"
    )
    print(f"source_id={artifact.source_id}")
    print(f"source_sha256={artifact.sha256}")
    print(f"source_byte_length={artifact.byte_length}")
    print(f"source_locator={artifact.locator}")
    print("source_fetch_pinned=PASS")
    return 0


def corpus_build(repository_root: str | Path, output_dir: str | Path) -> int:
    """Build the pinned source into a fresh generated corpus directory."""

    result = build_pinned_corpus(repository_root, output_dir)
    print(f"record_count={result.index.record_count}")
    print(f"unique_oracle_id_count={result.index.unique_oracle_id_count}")
    print(f"aggregate_index_digest={result.index.aggregate_digest}")
    print("corpus_build=PASS")
    return 0


def corpus_check(
    repository_root: str | Path,
    output_dir: str | Path | None,
    synthetic: bool,
) -> int:
    """Validate a generated index, or run its fully offline synthetic check."""

    if synthetic:
        digest_a, digest_b = run_corpus_synthetic_reproduction()
        print(f"run_a_digest={digest_a}")
        print(f"run_b_digest={digest_b}")
        print("synthetic_reproduction=PASS")
        return 0
    if output_dir is None:
        raise ValueError("corpus-check requires --output or --synthetic")
    digest = validate_corpus_output(output_dir)
    print(f"aggregate_index_digest={digest}")
    print("corpus_check=PASS")
    return 0


def structural_build(repository_root: str | Path, output_dir: str | Path) -> int:
    """Build the pinned structural census without network acquisition."""

    result = build_pinned_structural(repository_root, output_dir)
    print(f"structural_record_count={result.index.record_count}")
    print(f"unique_oracle_id_count={result.index.unique_oracle_id_count}")
    print(f"aggregate_structural_index_digest={result.index.aggregate_digest}")
    print("structural_build=PASS")
    return 0


def structural_check(
    repository_root: str | Path,
    output_dir: str | Path | None,
    synthetic: bool,
) -> int:
    """Validate pinned structural output or run its offline reproduction."""

    if synthetic:
        digest_a, digest_b = run_structural_synthetic_reproduction()
        print(f"run_a_digest={digest_a}")
        print(f"run_b_digest={digest_b}")
        print("synthetic_reproduction=PASS")
        return 0
    if output_dir is None:
        raise ValueError("structural-check requires --output or --synthetic")
    digest = validate_pinned_structural_output(repository_root, output_dir)
    print(f"aggregate_structural_index_digest={digest}")
    print("structural_check=PASS")
    return 0


def m4_command(
    command: str,
    repository_root: str | Path,
    output: str | Path | None,
    synthetic: bool,
) -> int:
    """Run one bounded synthetic-only M4 command."""

    if not synthetic:
        raise ValueError("M4 commands require --synthetic until separately authorized")
    if output is None:
        raise ValueError(f"m4-{command} requires --output or --synthetic")
    root = Path(repository_root)
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    if command == "build":
        build_result = build_synthetic_m4_command(output_path)
        print(f"m4_manifest_sha256={build_result.manifest.digest()}")
    elif command == "check":
        check_result = check_synthetic_m4_command(output_path)
        print(f"m4_manifest_sha256={check_result.manifest.digest()}")
    elif command == "report":
        report_result = report_synthetic_m4_command(output_path)
        print(f"m4_manifest_sha256={report_result.m4_manifest_sha256}")
        print(
            f"report_descriptor_count={len(report_result.report_index.report_descriptors)}"
        )
    else:
        raise ValueError("unsupported M4 command")
    print(f"m4-{command}=PASS")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manafold_census")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="check the local Python baseline")
    subparsers.add_parser("reproduce", help="run the two-build parity check")
    subparsers.add_parser(
        "source-discover", help="inspect current Scryfall bulk metadata"
    )
    refresh_parser = subparsers.add_parser(
        "source-refresh", help="refresh current Scryfall bytes into a proposal"
    )
    refresh_parser.add_argument("--repository-root", default=".")
    refresh_parser.add_argument(
        "--proposal", default="source-locks/scryfall-oracle-v1.proposed.json"
    )
    fetch_parser = subparsers.add_parser(
        "source-fetch-pinned", help="fetch the exact committed source lock"
    )
    fetch_parser.add_argument("--repository-root", default=".")
    build_parser = subparsers.add_parser(
        "corpus-build", help="build the committed pinned source-record index"
    )
    build_parser.add_argument("--repository-root", default=".")
    build_parser.add_argument("--output", default="dist/corpus/scryfall-oracle-v1")
    check_parser = subparsers.add_parser(
        "corpus-check", help="validate a corpus output or its offline fixture"
    )
    check_parser.add_argument("--repository-root", default=".")
    check_parser.add_argument("--output")
    check_parser.add_argument("--synthetic", action="store_true")
    structural_build_parser = subparsers.add_parser(
        "structural-build", help="build the pinned structural census"
    )
    structural_build_parser.add_argument("--repository-root", default=".")
    structural_build_parser.add_argument(
        "--output", default="dist/structural/scryfall-oracle-v1"
    )
    structural_check_parser = subparsers.add_parser(
        "structural-check", help="check pinned structural output or synthetic output"
    )
    structural_check_parser.add_argument("--repository-root", default=".")
    structural_check_parser.add_argument("--output")
    structural_check_parser.add_argument("--synthetic", action="store_true")
    m3_parent = argparse.ArgumentParser(add_help=False)
    for name, default in (
        ("output", "dist/analysis/m3-synthetic"),
        ("structural-output", "dist/analysis/m3-m1"),
        ("source-lock", "dist/analysis/m3-lock.json"),
    ):
        m3_parent.add_argument(f"--{name}", default=default)
    m3_parent.add_argument("--synthetic", action="store_true")
    for command in ("m3-build", "m3-check", "m3-report"):
        subparsers.add_parser(command, parents=[m3_parent])
    m4_parent = argparse.ArgumentParser(add_help=False)
    m4_parent.add_argument("--repository-root", default=".")
    m4_parent.add_argument("--output", default="dist/capability/m4-synthetic")
    m4_parent.add_argument("--synthetic", action="store_true")
    for command in ("m4-build", "m4-check", "m4-report"):
        subparsers.add_parser(command, parents=[m4_parent])
    add_m5_parsers(subparsers)
    add_m6_02_parsers(subparsers)
    add_explorer_parser(subparsers)
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
    try:
        if args.command == "source-discover":
            return source_discover()
        if args.command == "source-refresh":
            return source_refresh(args.repository_root, args.proposal)
        if args.command == "source-fetch-pinned":
            return source_fetch_pinned(args.repository_root)
        if args.command == "corpus-build":
            root = Path(args.repository_root)
            output = Path(args.output)
            if not output.is_absolute():
                output = root / output
            return corpus_build(root, output)
        if args.command == "corpus-check":
            root = Path(args.repository_root)
            check_output: Path | None = (
                Path(args.output) if args.output is not None else None
            )
            if check_output is not None and not check_output.is_absolute():
                check_output = root / check_output
            return corpus_check(root, check_output, args.synthetic)
        if args.command == "structural-build":
            root = Path(args.repository_root)
            output = Path(args.output)
            if not output.is_absolute():
                output = root / output
            return structural_build(root, output)
        if args.command == "structural-check":
            root = Path(args.repository_root)
            structural_check_output: Path | None = (
                Path(args.output) if args.output is not None else None
            )
            if (
                structural_check_output is not None
                and not structural_check_output.is_absolute()
            ):
                structural_check_output = root / structural_check_output
            return structural_check(root, structural_check_output, args.synthetic)
        if args.command in {"m3-build", "m3-check", "m3-report"}:
            return m3_command(args.command[3:], args)
        if args.command in {"m4-build", "m4-check", "m4-report"}:
            return m4_command(
                args.command[3:],
                args.repository_root,
                args.output,
                args.synthetic,
            )
        m5_result = dispatch_m5_command(args)
        if m5_result is not None:
            return m5_result
        m6_02_result = dispatch_m6_02_command(args)
        if m6_02_result is not None:
            return m6_02_result
        explorer_result = dispatch_explorer_command(args)
        if explorer_result is not None:
            return explorer_result
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"{args.command}=FAIL: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
