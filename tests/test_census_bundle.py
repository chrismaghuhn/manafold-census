from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from test_census_authority_package import _TestAuthorityPackage, _write_test_package

from manafold_census.canonical import canonical_json_bytes
from manafold_census.release.bundle import (
    CensusBundleBuildError,
    build_census_bundle,
    load_census_bundle,
    validate_census_bundle,
)
from manafold_census.release.m4_orchestration import build_real_m4_snapshot
from manafold_census.release.manifest import (
    AUTHORITATIVE_COMPONENT_ROLES,
    BUNDLE_SCHEMA,
    BUNDLE_VERSION,
    COMPONENT_MANIFEST_PATHS,
    COMPONENT_SCHEMAS,
    BundleCompatibilityV1,
    BundleComponentDescriptorV1,
    BundlePopulationV1,
    BundleSchemaCompatibilityV1,
    CensusBundleManifestV1,
    census_release_id_for,
)


def _manifest_fixture() -> CensusBundleManifestV1:
    components = tuple(
        BundleComponentDescriptorV1(
            role,
            COMPONENT_MANIFEST_PATHS[role],
            "a" * 64,
            1,
            COMPONENT_SCHEMAS[role],
            "c" * 64 if role == "m1" else None,
        )
        for role in AUTHORITATIVE_COMPONENT_ROLES
    )
    return CensusBundleManifestV1.create(
        census_release_version=BUNDLE_VERSION,
        source_lock_digest="b" * 64,
        authoritative_components=components,
        population=BundlePopulationV1(5, 5, 5, 5, 5, 0, 0),
        schemas=BundleSchemaCompatibilityV1(
            "census.structural-card.v1",
            "census.card-analysis.v1",
            "census.semantic-requirement.v1",
            "census.semantic-requirement-bundle.v1",
            "census.m4-ontology-manifest.v1",
        ),
        compatibility=BundleCompatibilityV1(1, "census.query.v1", "0.1.0"),
        parent_census_release_id=None,
    )


def _build_m4_and_bundle_inputs(
    tmp_path: Path,
) -> tuple[_TestAuthorityPackage, Path, Path]:
    package = _write_test_package(tmp_path)
    m4_output = tmp_path / "m4"
    build_real_m4_snapshot(
        authority_package_directory=package.root,
        m3_input=package.m3_input,
        lock=package.lock,
        corpus=package.corpus,
        output_directory=m4_output,
    )
    lock_path = tmp_path / "input-lock.json"
    lock_path.write_bytes(canonical_json_bytes(package.lock.to_wire()))
    return package, m4_output, lock_path


def _build_bundle(tmp_path: Path):
    package, m4_output, lock_path = _build_m4_and_bundle_inputs(tmp_path)
    result = build_census_bundle(
        input_lock_path=lock_path,
        source_lock_path=package.m3_input.source_lock_path,
        structural_output_directory=package.m3_input.structural_output_directory,
        analysis_output_directory=package.m3_input.analysis_output_directory,
        authority_package_directory=package.root,
        m4_output_directory=m4_output,
        output_directory=tmp_path / "bundle",
    )
    return package, result


def test_bundle_manifest_release_id_excludes_derived_release_id() -> None:
    manifest = _manifest_fixture()

    assert manifest.schema == BUNDLE_SCHEMA
    assert manifest.census_release_id == census_release_id_for(manifest)
    mutated = replace(manifest, census_release_id="censusrel_" + "f" * 64)
    assert census_release_id_for(mutated) == manifest.census_release_id


def test_bundle_build_is_self_contained_and_validates_nested_authority(
    tmp_path: Path,
) -> None:
    package, result = _build_bundle(tmp_path)

    assert result.manifest.parent_census_release_id is None
    assert result.manifest.census_release_version == BUNDLE_VERSION
    assert result.manifest.census_release_id.startswith("censusrel_")
    contents = load_census_bundle(result.output_dir)
    validate_census_bundle(result.output_dir, package.lock, package.corpus)
    assert contents.manifest == result.manifest
    assert (result.output_dir / "inputs/m4/m4-ontology-manifest.json").is_file()


def test_bundle_rejects_reports_indexes_and_metadata(tmp_path: Path) -> None:
    package, result = _build_bundle(tmp_path)
    (result.output_dir / "reports").mkdir()
    (result.output_dir / "reports/report.json").write_bytes(b"derived")

    with pytest.raises(ValueError, match="file set"):
        validate_census_bundle(result.output_dir, package.lock, package.corpus)


def test_bundle_rejects_missing_nested_file(tmp_path: Path) -> None:
    package, result = _build_bundle(tmp_path)
    (result.output_dir / "inputs/m3/records/0.jsonl").unlink()

    with pytest.raises((FileNotFoundError, ValueError), match="missing|file set"):
        validate_census_bundle(result.output_dir, package.lock, package.corpus)


def test_bundle_rejects_tampered_nested_bytes(tmp_path: Path) -> None:
    package, result = _build_bundle(tmp_path)
    path = result.output_dir / "inputs/m4-authority/authority-manifest.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(ValueError, match="descriptor|canonical|authority"):
        validate_census_bundle(result.output_dir, package.lock, package.corpus)


def test_bundle_rejects_symlinked_expected_file(tmp_path: Path) -> None:
    package, result = _build_bundle(tmp_path)
    target = result.output_dir / "inputs/source-lock.json"
    outside = tmp_path / "outside-source-lock.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(ValueError, match="symlink|junction|containment"):
        validate_census_bundle(result.output_dir, package.lock, package.corpus)


def test_bundle_rejects_symlinked_bundle_root(tmp_path: Path) -> None:
    package, result = _build_bundle(tmp_path)
    alias = tmp_path / "bundle-alias"
    try:
        alias.symlink_to(result.output_dir, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlink creation unavailable: {error}")

    with pytest.raises(ValueError, match="symlink|junction|containment"):
        validate_census_bundle(alias, package.lock, package.corpus)


def test_bundle_rejects_junctioned_directory_on_windows(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows junction test")
    package, result = _build_bundle(tmp_path)
    target = result.output_dir / "inputs/m4-authority"
    outside = tmp_path / "outside-m4-authority"
    shutil.copytree(target, outside)
    shutil.rmtree(target)
    created = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(target), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        pytest.skip(
            f"junction creation unavailable: {created.stderr or created.stdout}"
        )

    with pytest.raises(ValueError, match="symlink|junction|containment"):
        validate_census_bundle(result.output_dir, package.lock, package.corpus)


def test_bundle_never_overwrites_existing_output(tmp_path: Path) -> None:
    package, m4_output, lock_path = _build_m4_and_bundle_inputs(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(CensusBundleBuildError, match="already exists"):
        build_census_bundle(
            input_lock_path=lock_path,
            source_lock_path=package.m3_input.source_lock_path,
            structural_output_directory=package.m3_input.structural_output_directory,
            analysis_output_directory=package.m3_input.analysis_output_directory,
            authority_package_directory=package.root,
            m4_output_directory=m4_output,
            output_directory=output,
        )

    assert sentinel.read_bytes() == b"keep"


def test_bundle_cli_uses_only_explicit_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package, m4_output, lock_path = _build_m4_and_bundle_inputs(tmp_path)
    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-bundle-build",
            "--input-lock",
            str(lock_path),
            "--authority-package",
            str(package.root),
            "--source-lock",
            str(package.m3_input.source_lock_path),
            "--structural-output",
            str(package.m3_input.structural_output_directory),
            "--analysis-output",
            str(package.m3_input.analysis_output_directory),
            "--m4-output",
            str(m4_output),
            "--output",
            str(tmp_path / "cli-bundle"),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "bundle-reread=PASS" in captured
    assert "m5-bundle-build=PASS" in captured
