"""Census 0.1 bundle validation and atomic publication."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..capability.build import _reread_output
from ..capability.input import M3RequirementCorpusV1
from ..capability.manifest import M4OntologyManifestV1
from ..capability.validate import validate_m4_inputs
from ..digest import sha256_bytes
from ..models import SourceLock
from .authority_validation import validate_authority_package
from .input_lock import (
    CensusInputLockStatusV1,
    CensusInputLockV1,
    CensusInputProvisioningV1,
    load_census_input_lock,
    validate_census_input_lock,
)
from .m4_orchestration import (
    _assert_record_set_parity,
    _validate_published_manifest,
)
from .manifest import (
    AUTHORITATIVE_COMPONENT_ROLES,
    BUNDLE_FORMAT_MAJOR,
    BUNDLE_MANIFEST_FILENAME,
    BUNDLE_VERSION,
    COMPONENT_MANIFEST_PATHS,
    COMPONENT_SCHEMAS,
    MINIMUM_EXPLORER_VERSION,
    QUERY_CONTRACT,
    BundleCompatibilityV1,
    BundleComponentDescriptorV1,
    BundlePopulationV1,
    BundleSchemaCompatibilityV1,
    CensusBundleManifestV1,
)
from .publish import (
    AUTHORITY_BUNDLE_FILES,
    M1_BUNDLE_FILES,
    M3_BUNDLE_FILES,
    copy_bundle_inputs,
    file_descriptor_matches,
    read_bundle_manifest,
)


class CensusBundleBuildError(ValueError):
    """Raised when a Census bundle cannot be validated and published."""


@dataclass(frozen=True, slots=True)
class CensusBundleContentsV1:
    root: Path
    manifest: CensusBundleManifestV1


@dataclass(frozen=True, slots=True)
class CensusBundleBuildResultV1:
    output_dir: Path
    manifest: CensusBundleManifestV1
    census_manifest_sha256: str


def _m4_file_set(root: Path) -> set[str]:
    manifest_path = root / "inputs/m4/m4-ontology-manifest.json"
    document = json.loads(manifest_path.read_bytes())
    manifest = M4OntologyManifestV1.from_wire(document)
    descriptors = (
        manifest.capability_file,
        manifest.review_file,
        manifest.relation_file,
        manifest.admissibility_file,
        manifest.evolution_file,
        *manifest.link_shards,
        *manifest.mapping_decision_shards,
    )
    return {
        "inputs/m4/m4-ontology-manifest.json",
        *(f"inputs/m4/{item.relative_path}" for item in descriptors),
    }


def _expected_bundle_files(root: Path) -> set[str]:
    return {
        BUNDLE_MANIFEST_FILENAME,
        "inputs/source-lock.json",
        *(f"inputs/m1/{item}" for item in M1_BUNDLE_FILES),
        *(f"inputs/m3/{item}" for item in M3_BUNDLE_FILES),
        *(f"inputs/m4-authority/{item}" for item in AUTHORITY_BUNDLE_FILES),
        *_m4_file_set(root),
    }


def load_census_bundle(bundle_dir: str | Path) -> CensusBundleContentsV1:
    """Read the manifest and enforce the self-contained bundle file set."""

    root = Path(bundle_dir)
    manifest = read_bundle_manifest(root)
    _validate_bundle_file_set(root, ())
    return CensusBundleContentsV1(root, manifest)


def _validate_bundle_file_set(root: Path, allowed_extra_files: Collection[str]) -> None:
    for relative_path in allowed_extra_files:
        parsed = PurePosixPath(relative_path)
        if (
            parsed.is_absolute()
            or ".." in parsed.parts
            or parsed.as_posix() != relative_path
        ):
            raise ValueError("allowed derived path is not a safe relative path")
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    expected = _expected_bundle_files(root) | set(allowed_extra_files)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise FileNotFoundError("missing Census bundle artifact: " + missing[0])
    if extra:
        raise ValueError("Census bundle file set mismatch: " + extra[0])


def _component_map(
    manifest: CensusBundleManifestV1,
) -> dict[str, BundleComponentDescriptorV1]:
    return {item.role: item for item in manifest.authoritative_components}


def _validate_components(
    root: Path,
    manifest: CensusBundleManifestV1,
    lock: CensusInputLockV1,
) -> None:
    components = _component_map(manifest)
    if tuple(components) != AUTHORITATIVE_COMPONENT_ROLES:
        raise ValueError("bundle authoritative component roles are not canonical")
    for role, component in components.items():
        if not file_descriptor_matches(
            root / component.manifest_path,
            component.sha256,
            component.byte_length,
        ):
            raise ValueError(f"bundle component descriptor mismatch: {role}")
    if components["source_lock"].sha256 != lock.source_lock_file_sha256:
        raise ValueError("bundle SourceLock descriptor does not match lock")
    if components["m1"].sha256 != lock.m1_structural_manifest_sha256:
        raise ValueError("bundle M1 descriptor does not match lock")
    if components["m1"].aggregate_digest != lock.m1_structural_aggregate_digest:
        raise ValueError("bundle M1 aggregate descriptor does not match lock")
    if components["m3"].sha256 != lock.m3_analysis_manifest_sha256:
        raise ValueError("bundle M3 descriptor does not match lock")


def _expected_population(lock: CensusInputLockV1) -> BundlePopulationV1:
    return BundlePopulationV1(
        lock.expected_oracle_identity_count,
        lock.expected_structural_record_count,
        lock.expected_analysis_record_count,
        lock.expected_requirement_count,
        lock.expected_requirements_produced_card_count,
        lock.expected_no_requirements_applicable_count,
        lock.expected_unresolved_analysis_count,
    )


def _validate_authoritative_contents(
    contents: CensusBundleContentsV1,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
) -> CensusBundleContentsV1:
    """Validate all authoritative bytes beneath an already selected root."""

    manifest = contents.manifest
    if manifest.parent_census_release_id is not None:
        raise ValueError("first Census bundle must have a null parent")
    if manifest.source_lock_digest != lock.source_lock_digest:
        raise ValueError("bundle SourceLock digest does not match lock")
    if manifest.population != _expected_population(lock):
        raise ValueError("bundle population does not match lock")
    _validate_components(contents.root, manifest, lock)

    provisioning = CensusInputProvisioningV1(
        source_lock_path=contents.root / "inputs/source-lock.json",
        structural_output_directory=contents.root / "inputs/m1",
        analysis_output_directory=contents.root / "inputs/m3",
    )
    input_result = validate_census_input_lock(lock, provisioning)
    if input_result.status is not CensusInputLockStatusV1.PASS:
        raise CensusBundleBuildError(
            f"nested M5-02 validation is {input_result.status.value}"
        )
    if input_result.m3_corpus is None:
        raise CensusBundleBuildError("nested M5-02 validation returned no corpus")
    nested_corpus = input_result.m3_corpus
    if nested_corpus != corpus:
        raise ValueError("bundle M3 corpus differs from the selected corpus")

    authority = validate_authority_package(
        contents.root / "inputs/m4-authority",
        lock,
        nested_corpus,
    )
    published = _reread_output(contents.root / "inputs/m4")
    _validate_published_manifest(published.manifest, lock, nested_corpus)
    validate_m4_inputs(
        nested_corpus,
        None,
        None,
        published.definitions,
        published.reviews,
        published.relations,
        published.admissibility,
        published.links,
        published.decisions,
        published.evolution,
    )
    _assert_record_set_parity(authority, published)
    return contents


def validate_census_bundle(
    bundle_dir: str | Path,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
) -> CensusBundleContentsV1:
    """Reread and validate every authoritative component in one bundle."""

    if not isinstance(lock, CensusInputLockV1):
        raise TypeError("lock must be CensusInputLockV1")
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("corpus must be M3RequirementCorpusV1")
    return _validate_authoritative_contents(
        load_census_bundle(bundle_dir), lock, corpus
    )


def validate_census_authoritative_subtree(
    bundle_dir: str | Path,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
    *,
    allowed_extra_files: Collection[str] = (),
) -> CensusBundleContentsV1:
    """Validate authoritative bytes while allowing an exact derived sibling set."""

    if not isinstance(lock, CensusInputLockV1):
        raise TypeError("lock must be CensusInputLockV1")
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("corpus must be M3RequirementCorpusV1")
    root = Path(bundle_dir)
    manifest = read_bundle_manifest(root)
    _validate_bundle_file_set(root, allowed_extra_files)
    contents = CensusBundleContentsV1(root, manifest)
    return _validate_authoritative_contents(contents, lock, corpus)


def _bundle_manifest(
    source_lock_path: Path,
    structural_output_directory: Path,
    analysis_output_directory: Path,
    authority_package_directory: Path,
    m4_output_directory: Path,
    lock: CensusInputLockV1,
) -> CensusBundleManifestV1:
    source_lock = SourceLock.from_wire(json.loads(source_lock_path.read_bytes()))
    if source_lock.digest() != lock.source_lock_digest:
        raise ValueError("source lock does not match the selected lock")
    component_roots = {
        "source_lock": source_lock_path.parent,
        "m1": structural_output_directory,
        "m3": analysis_output_directory,
        "m4_authority": authority_package_directory,
        "m4": m4_output_directory,
    }
    component_paths = {
        "source_lock": source_lock_path.name,
        "m1": "structural-index-manifest.json",
        "m3": "analysis-manifest.json",
        "m4_authority": "authority-manifest.json",
        "m4": "m4-ontology-manifest.json",
    }
    descriptors = []
    for role in AUTHORITATIVE_COMPONENT_ROLES:
        path = component_roots[role] / component_paths[role]
        raw = path.read_bytes()
        descriptors.append(
            BundleComponentDescriptorV1(
                role,
                COMPONENT_MANIFEST_PATHS[role],
                sha256_bytes(raw),
                len(raw),
                COMPONENT_SCHEMAS[role],
                lock.m1_structural_aggregate_digest if role == "m1" else None,
            )
        )
    return CensusBundleManifestV1.create(
        census_release_version=BUNDLE_VERSION,
        source_lock_digest=lock.source_lock_digest,
        authoritative_components=tuple(descriptors),
        population=_expected_population(lock),
        schemas=BundleSchemaCompatibilityV1(
            lock.m1_structural_schema,
            lock.m3_analysis_schema,
            lock.m2_requirement_schema,
            lock.m2_bundle_schema,
            "census.m4-ontology-manifest.v1",
        ),
        compatibility=BundleCompatibilityV1(
            BUNDLE_FORMAT_MAJOR,
            QUERY_CONTRACT,
            MINIMUM_EXPLORER_VERSION,
        ),
        parent_census_release_id=None,
    )


def build_census_bundle(
    *,
    input_lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    authority_package_directory: str | Path,
    m4_output_directory: str | Path,
    output_directory: str | Path,
) -> CensusBundleBuildResultV1:
    """Build, reread, and atomically publish one self-contained bundle."""

    lock = load_census_input_lock(input_lock_path)
    provisioning = CensusInputProvisioningV1(
        source_lock_path=Path(source_lock_path),
        structural_output_directory=Path(structural_output_directory),
        analysis_output_directory=Path(analysis_output_directory),
    )
    input_result = validate_census_input_lock(lock, provisioning)
    if input_result.status is not CensusInputLockStatusV1.PASS:
        raise CensusBundleBuildError(
            f"M5-02 input validation is {input_result.status.value}"
        )
    if input_result.m3_corpus is None:
        raise CensusBundleBuildError("M5-02 input validation returned no corpus")
    authority = validate_authority_package(
        authority_package_directory,
        lock,
        input_result.m3_corpus,
    )
    m4_root = Path(m4_output_directory)
    published = _reread_output(m4_root)
    _validate_published_manifest(published.manifest, lock, input_result.m3_corpus)
    validate_m4_inputs(
        input_result.m3_corpus,
        None,
        None,
        published.definitions,
        published.reviews,
        published.relations,
        published.admissibility,
        published.links,
        published.decisions,
        published.evolution,
    )
    _assert_record_set_parity(authority, published)
    manifest = _bundle_manifest(
        Path(source_lock_path),
        provisioning.structural_output_directory,
        provisioning.analysis_output_directory,
        Path(authority_package_directory),
        m4_root,
        lock,
    )
    output = Path(output_directory)
    if output.exists():
        raise CensusBundleBuildError("Census bundle output directory already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output.name}-",
            dir=str(output.parent),
        ) as temporary:
            staging = Path(temporary) / "bundle"
            staging.mkdir()
            copy_bundle_inputs(
                staging,
                source_lock_path=Path(source_lock_path),
                structural_output_directory=provisioning.structural_output_directory,
                analysis_output_directory=provisioning.analysis_output_directory,
                authority_package_directory=Path(authority_package_directory),
                m4_output_directory=m4_root,
            )
            (staging / BUNDLE_MANIFEST_FILENAME).write_bytes(manifest.canonical_bytes())
            validate_census_bundle(staging, lock, input_result.m3_corpus)
            os.replace(staging, output)
    except CensusBundleBuildError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise CensusBundleBuildError(str(error)) from error
    raw_manifest = (output / BUNDLE_MANIFEST_FILENAME).read_bytes()
    return CensusBundleBuildResultV1(output, manifest, sha256_bytes(raw_manifest))


__all__ = [
    "CensusBundleBuildError",
    "CensusBundleBuildResultV1",
    "CensusBundleContentsV1",
    "build_census_bundle",
    "load_census_bundle",
    "validate_census_authoritative_subtree",
    "validate_census_bundle",
]
