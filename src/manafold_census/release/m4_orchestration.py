"""Explicit M5-04 orchestration for the first real M4 snapshot."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ..canonical import canonical_json_bytes
from ..capability.build import _reread_output, build_reference_m4
from ..capability.definition import CapabilityDefinitionV1
from ..capability.input import FrozenM3InputV1, M3RequirementCorpusV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.manifest import M4OntologyManifestV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.validate import validate_m4_inputs
from .authority_package import AuthorityPackageContentsV1
from .authority_validation import validate_authority_package
from .input_lock import CensusInputLockV1


class M5M4BuildError(ValueError):
    """Raised when the first real M4 snapshot cannot be published."""


@dataclass(frozen=True, slots=True)
class M5M4BuildResultV1:
    output_dir: Path
    manifest: M4OntologyManifestV1
    authority_package_record_set_parity: bool
    definitions: tuple[CapabilityDefinitionV1, ...]
    links: tuple[RequirementCapabilityLinkV1, ...]
    mapping_decisions: tuple[RequirementMappingDecisionV1, ...]


def _wire_set(values: Sequence[Any]) -> tuple[bytes, ...]:
    return tuple(
        sorted(canonical_json_bytes(cast(Any, value).to_wire()) for value in values)
    )


def _assert_record_set_parity(
    authority: AuthorityPackageContentsV1,
    published: Any,
) -> None:
    pairs = (
        ("definitions", authority.capability_definitions, published.definitions),
        ("reviews", authority.reviews, published.reviews),
        ("relations", authority.relations, published.relations),
        ("admissibility", authority.admissibility, published.admissibility),
        ("evolution", authority.evolution, published.evolution),
        ("links", authority.links, published.links),
        ("mapping-decisions", authority.mapping_decisions, published.decisions),
    )
    for name, authority_values, published_values in pairs:
        if _wire_set(authority_values) != _wire_set(published_values):
            raise M5M4BuildError(
                f"authority/publication record-set parity failed: {name}"
            )


def _validate_published_manifest(
    manifest: M4OntologyManifestV1,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
) -> None:
    if manifest.parent_m4_manifest_sha256 is not None:
        raise M5M4BuildError("first real M4 snapshot must have a null parent")
    if (
        manifest.m3_analysis_manifest_sha256 != lock.m3_analysis_manifest_sha256
        or manifest.m3_analysis_manifest_sha256 != corpus.m3_analysis_manifest_sha256
        or manifest.requirement_set_digest != lock.expected_m4_requirement_set_digest
        or manifest.requirement_set_digest != corpus.requirement_set_digest
        or manifest.m3_analysis_schema != lock.m3_analysis_schema
        or manifest.m2_requirement_schema != lock.m2_requirement_schema
        or manifest.m2_bundle_schema != lock.m2_bundle_schema
        or manifest.m4_dimension_registry_version != lock.m4_dimension_registry_version
    ):
        raise M5M4BuildError("published M4 manifest is not bound to the locked input")


def build_real_m4_snapshot(
    *,
    authority_package_directory: str | Path,
    m3_input: FrozenM3InputV1,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
    output_directory: str | Path,
) -> M5M4BuildResultV1:
    """Build and atomically publish the first real M4 snapshot."""

    if not isinstance(m3_input, FrozenM3InputV1):
        raise TypeError("m3_input must be FrozenM3InputV1")
    if not isinstance(lock, CensusInputLockV1):
        raise TypeError("lock must be CensusInputLockV1")
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("corpus must be M3RequirementCorpusV1")
    if (
        m3_input.expected_analysis_manifest_sha256 != lock.m3_analysis_manifest_sha256
        or corpus.m3_analysis_manifest_sha256 != lock.m3_analysis_manifest_sha256
        or corpus.requirement_set_digest != lock.expected_m4_requirement_set_digest
    ):
        raise M5M4BuildError("M5-04 inputs do not match the frozen M5-02 lock")
    authority = validate_authority_package(
        authority_package_directory,
        lock,
        corpus,
    )
    output = Path(output_directory)
    if output.exists():
        raise M5M4BuildError("M4 output directory already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output.name}-",
            dir=str(output.parent),
        ) as temporary:
            staging = Path(temporary) / "publication"
            build_reference_m4(
                m3_input,
                None,
                None,
                authority.capability_definitions,
                authority.reviews,
                authority.relations,
                authority.admissibility,
                authority.links,
                authority.mapping_decisions,
                authority.evolution,
                staging,
            )
            published = _reread_output(staging)
            _validate_published_manifest(published.manifest, lock, corpus)
            validate_m4_inputs(
                corpus,
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
            os.replace(staging, output)
    except M5M4BuildError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise M5M4BuildError(str(error)) from error
    return M5M4BuildResultV1(
        output,
        published.manifest,
        True,
        published.definitions,
        published.links,
        published.decisions,
    )


__all__ = [
    "M5M4BuildError",
    "M5M4BuildResultV1",
    "build_real_m4_snapshot",
]
