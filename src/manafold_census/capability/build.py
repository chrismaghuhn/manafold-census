"""Single-process M4 validation, staging, reread, and publication."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ..canonical import canonical_json_bytes
from ..digest import measure_file, sha256_bytes
from ..semantic.model import RequirementV1
from ..validation import validate_document
from .admissibility import SourceRequirementAdmissibilityV1
from .definition import CapabilityDefinitionV1
from .evolution import CapabilityEvolutionV1
from .input import (
    FrozenM3InputV1,
    M3RequirementCorpusV1,
    load_m3_requirement_corpus,
)
from .link import RequirementCapabilityLinkV1
from .manifest import (
    M4_BUILD_PROFILE,
    M4_DIMENSION_REGISTRY_VERSION,
    M4_MANIFEST_FILENAME,
    M4_MANIFEST_SCHEMA,
    M4_ONTOLOGY_SCHEMA,
    SHARD_NAMES,
    M4FileDescriptorV1,
    M4OntologyManifestV1,
)
from .mapping import RequirementMappingDecisionV1
from .relations import (
    CapabilityRelationV1,
    relation_sort_key,
    sort_capability_relations,
)
from .review import CapabilityReviewRecordV1
from .validate import validate_m4_inputs


class CapabilityBuildError(ValueError):
    """Raised when an M4 build cannot produce an authoritative publication."""


@dataclass(frozen=True, slots=True)
class M4BuildResultV1:
    output_dir: Path
    manifest: M4OntologyManifestV1
    requirements: tuple[RequirementV1, ...]
    definitions: tuple[CapabilityDefinitionV1, ...]
    semantic_relations: tuple[CapabilityRelationV1, ...]
    links: tuple[RequirementCapabilityLinkV1, ...]
    mapping_decisions: tuple[RequirementMappingDecisionV1, ...]


@dataclass(frozen=True, slots=True)
class _RereadResult:
    manifest: M4OntologyManifestV1
    definitions: tuple[CapabilityDefinitionV1, ...]
    reviews: tuple[CapabilityReviewRecordV1, ...]
    relations: tuple[CapabilityRelationV1, ...]
    admissibility: tuple[SourceRequirementAdmissibilityV1, ...]
    evolution: tuple[CapabilityEvolutionV1, ...]
    links: tuple[RequirementCapabilityLinkV1, ...]
    decisions: tuple[RequirementMappingDecisionV1, ...]


def _definition_key(value: object) -> tuple[str, str, str]:
    item = cast(CapabilityDefinitionV1, value)
    return (
        item.capability_family_id,
        f"{item.capability_version:020d}",
        item.claim_digest,
    )


def _review_key(value: object) -> tuple[str, str, str]:
    item = cast(CapabilityReviewRecordV1, value)
    subject_wire = item.subject.to_wire()
    return (
        cast(str, subject_wire["type"]),
        canonical_json_bytes(subject_wire).decode(),
        item.record_id,
    )


def _admissibility_key(value: object) -> tuple[str, str]:
    item = cast(SourceRequirementAdmissibilityV1, value)
    return (item.requirement_id, item.record_id)


def _evolution_key(value: object) -> tuple[str, str, str, str]:
    item = cast(CapabilityEvolutionV1, value)
    return (
        item.operation.value,
        canonical_json_bytes([ref.to_wire() for ref in item.from_references]).decode(),
        canonical_json_bytes([ref.to_wire() for ref in item.to_references]).decode(),
        item.event_id,
    )


def _relation_key(value: object) -> tuple[str, bytes, bytes, str]:
    item = cast(CapabilityRelationV1, value)
    return relation_sort_key(item)


def _link_key(value: object) -> tuple[str, str, str, str]:
    item = cast(RequirementCapabilityLinkV1, value)
    return (
        item.requirement_id,
        item.relation.value,
        canonical_json_bytes(item.capability.to_wire()).decode(),
        item.link_id,
    )


def _decision_key(value: object) -> tuple[str, str]:
    item = cast(RequirementMappingDecisionV1, value)
    return (item.requirement_id, item.requirement_id)


def _write_jsonl(
    root: Path,
    relative_path: str,
    values: Sequence[Any],
    sort_key: Callable[[object], Any],
) -> M4FileDescriptorV1:
    ordered = sorted(tuple(values), key=sort_key)
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(
        canonical_json_bytes(cast(Any, value).to_wire()) + b"\n" for value in ordered
    )
    path.write_bytes(raw)
    measurement = measure_file(path)
    return M4FileDescriptorV1(
        relative_path=relative_path,
        sha256=measurement.sha256,
        byte_length=measurement.byte_length,
        record_count=len(ordered),
    )


def _read_jsonl(
    root: Path,
    descriptor: M4FileDescriptorV1,
    parser: Callable[[object], object],
    sort_key: Callable[[object], Any],
) -> tuple[object, ...]:
    path = root / descriptor.relative_path
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(f"missing M4 artifact {descriptor.relative_path}") from error
    measurement = measure_file(path)
    if (
        measurement.sha256 != descriptor.sha256
        or measurement.byte_length != descriptor.byte_length
    ):
        raise ValueError(f"M4 descriptor does not match {descriptor.relative_path}")
    values: list[object] = []
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError(f"{descriptor.relative_path} is missing a final LF")
        try:
            parsed = parser(json.loads(line))
            wire = cast(Any, parsed).to_wire()
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(
                f"{descriptor.relative_path} contains an invalid record"
            ) from error
        if line != canonical_json_bytes(wire) + b"\n":
            raise ValueError(f"{descriptor.relative_path} contains noncanonical JSONL")
        values.append(parsed)
    if len(values) != descriptor.record_count:
        raise ValueError(f"{descriptor.relative_path} record count is stale")
    keys = [sort_key(value) for value in values]
    if keys != sorted(keys):
        raise ValueError(f"{descriptor.relative_path} is not canonically ordered")
    return tuple(values)


def _read_manifest(root: Path) -> M4OntologyManifestV1:
    path = root / M4_MANIFEST_FILENAME
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("M4 manifest cannot be read as JSON") from error
    if not isinstance(document, dict) or raw != canonical_json_bytes(document):
        raise ValueError("M4 manifest is not canonical JSON")
    try:
        validate_document(document, "capability-ontology-manifest.v1.schema.json")
        manifest = M4OntologyManifestV1.from_wire(document)
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(f"M4 manifest is invalid: {error}") from error
    if manifest.digest() != sha256_bytes(raw):
        raise ValueError("M4 manifest digest does not match its bytes")
    return manifest


def _reread_output(root: Path) -> _RereadResult:
    manifest = _read_manifest(root)
    descriptors = (
        manifest.capability_file,
        manifest.review_file,
        manifest.relation_file,
        manifest.admissibility_file,
        manifest.evolution_file,
        *manifest.link_shards,
        *manifest.mapping_decision_shards,
    )
    expected = {M4_MANIFEST_FILENAME} | {
        descriptor.relative_path for descriptor in descriptors
    }
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    if actual != expected:
        raise ValueError(
            "M4 publication file set mismatch: "
            f"missing={len(expected - actual)} extra={len(actual - expected)}"
        )
    definitions = tuple(
        cast(CapabilityDefinitionV1, value)
        for value in _read_jsonl(
            root,
            manifest.capability_file,
            CapabilityDefinitionV1.from_wire,
            _definition_key,
        )
    )
    reviews = tuple(
        cast(CapabilityReviewRecordV1, value)
        for value in _read_jsonl(
            root,
            manifest.review_file,
            CapabilityReviewRecordV1.from_wire,
            _review_key,
        )
    )
    relations = tuple(
        cast(CapabilityRelationV1, value)
        for value in _read_jsonl(
            root,
            manifest.relation_file,
            CapabilityRelationV1.from_wire,
            _relation_key,
        )
    )
    admissibility = tuple(
        cast(SourceRequirementAdmissibilityV1, value)
        for value in _read_jsonl(
            root,
            manifest.admissibility_file,
            SourceRequirementAdmissibilityV1.from_wire,
            _admissibility_key,
        )
    )
    evolution = tuple(
        cast(CapabilityEvolutionV1, value)
        for value in _read_jsonl(
            root,
            manifest.evolution_file,
            CapabilityEvolutionV1.from_wire,
            _evolution_key,
        )
    )
    links: list[RequirementCapabilityLinkV1] = []
    for descriptor in manifest.link_shards:
        links.extend(
            cast(RequirementCapabilityLinkV1, value)
            for value in _read_jsonl(
                root,
                descriptor,
                RequirementCapabilityLinkV1.from_wire,
                _link_key,
            )
        )
    decisions: list[RequirementMappingDecisionV1] = []
    for descriptor in manifest.mapping_decision_shards:
        decisions.extend(
            cast(RequirementMappingDecisionV1, value)
            for value in _read_jsonl(
                root,
                descriptor,
                RequirementMappingDecisionV1.from_wire,
                _decision_key,
            )
        )
    return _RereadResult(
        manifest,
        definitions,
        reviews,
        relations,
        admissibility,
        evolution,
        tuple(links),
        tuple(decisions),
    )


def _wire_set(values: Sequence[Any]) -> tuple[bytes, ...]:
    return tuple(
        sorted(canonical_json_bytes(cast(Any, value).to_wire()) for value in values)
    )


def _write_and_validate(
    staging: Path,
    corpus: M3RequirementCorpusV1,
    parent_sha256: str | None,
    parent_manifest: M4OntologyManifestV1 | None,
    definitions: tuple[CapabilityDefinitionV1, ...],
    reviews: tuple[CapabilityReviewRecordV1, ...],
    relations: tuple[CapabilityRelationV1, ...],
    admissibility: tuple[SourceRequirementAdmissibilityV1, ...],
    evolution: tuple[CapabilityEvolutionV1, ...],
    links: tuple[RequirementCapabilityLinkV1, ...],
    decisions: tuple[RequirementMappingDecisionV1, ...],
) -> M4OntologyManifestV1:
    capability_file = _write_jsonl(
        staging, "capabilities.jsonl", definitions, _definition_key
    )
    review_file = _write_jsonl(staging, "review-authority.jsonl", reviews, _review_key)
    relation_file = _write_jsonl(
        staging, "capability-relations.jsonl", relations, _relation_key
    )
    admissibility_file = _write_jsonl(
        staging, "requirement-admissibility.jsonl", admissibility, _admissibility_key
    )
    evolution_file = _write_jsonl(staging, "evolution.jsonl", evolution, _evolution_key)
    link_shards = tuple(
        _write_jsonl(
            staging,
            f"links/{shard}.jsonl",
            tuple(link for link in links if link.requirement_id[4] == shard),
            _link_key,
        )
        for shard in SHARD_NAMES
    )
    decision_shards = tuple(
        _write_jsonl(
            staging,
            f"mapping-decisions/{shard}.jsonl",
            tuple(
                decision
                for decision in decisions
                if decision.requirement_id[4] == shard
            ),
            _decision_key,
        )
        for shard in SHARD_NAMES
    )
    manifest = M4OntologyManifestV1(
        schema=M4_MANIFEST_SCHEMA,
        ontology_schema=M4_ONTOLOGY_SCHEMA,
        build_profile=M4_BUILD_PROFILE,
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        m3_analysis_schema=corpus.m3_analysis_schema,
        m2_requirement_schema=corpus.m2_requirement_schema,
        m2_bundle_schema=corpus.m2_bundle_schema,
        m4_dimension_registry_version=M4_DIMENSION_REGISTRY_VERSION,
        parent_m4_manifest_sha256=parent_sha256,
        requirement_set_digest=corpus.requirement_set_digest,
        capability_file=capability_file,
        review_file=review_file,
        relation_file=relation_file,
        admissibility_file=admissibility_file,
        evolution_file=evolution_file,
        link_shards=link_shards,
        mapping_decision_shards=decision_shards,
    )
    (staging / M4_MANIFEST_FILENAME).write_bytes(manifest.canonical_bytes())
    reread = _reread_output(staging)
    if reread.manifest != manifest:
        raise ValueError("reread M4 manifest changed")
    for actual, expected in (
        (reread.definitions, definitions),
        (reread.reviews, reviews),
        (reread.relations, relations),
        (reread.admissibility, admissibility),
        (reread.evolution, evolution),
        (reread.links, links),
        (reread.decisions, decisions),
    ):
        if _wire_set(actual) != _wire_set(expected):
            raise ValueError("reread M4 values changed")
    validate_m4_inputs(
        corpus,
        parent_sha256,
        parent_manifest,
        reread.definitions,
        reread.reviews,
        reread.relations,
        reread.admissibility,
        reread.links,
        reread.decisions,
        reread.evolution,
    )
    return manifest


def build_reference_m4(
    m3_input: FrozenM3InputV1,
    parent_m4_manifest_sha256: str | None,
    parent_m4_manifest: M4OntologyManifestV1 | None,
    capability_definitions: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    semantic_relations: Sequence[CapabilityRelationV1],
    admissibility_records: Sequence[SourceRequirementAdmissibilityV1],
    links: Sequence[RequirementCapabilityLinkV1],
    mapping_decisions: Sequence[RequirementMappingDecisionV1],
    evolution_records: Sequence[CapabilityEvolutionV1],
    output_dir: str | Path,
) -> M4BuildResultV1:
    output_path = Path(output_dir)
    if output_path.exists():
        raise CapabilityBuildError(
            "PUBLICATION_FAILURE: output directory already exists"
        )
    try:
        corpus = load_m3_requirement_corpus(m3_input)
    except (OSError, TypeError, ValueError) as error:
        raise CapabilityBuildError(f"INVALID_M3_INPUT: {error}") from error
    try:
        validate_m4_inputs(
            corpus,
            parent_m4_manifest_sha256,
            parent_m4_manifest,
            capability_definitions,
            reviews,
            semantic_relations,
            admissibility_records,
            links,
            mapping_decisions,
            evolution_records,
        )
        definitions = tuple(sorted(capability_definitions, key=_definition_key))
        review_values = tuple(sorted(reviews, key=_review_key))
        relations = sort_capability_relations(semantic_relations)
        admissibility = tuple(sorted(admissibility_records, key=_admissibility_key))
        evolution = tuple(sorted(evolution_records, key=_evolution_key))
        link_values = tuple(sorted(links, key=_link_key))
        decision_values = tuple(sorted(mapping_decisions, key=_decision_key))
    except (TypeError, ValueError) as error:
        raise CapabilityBuildError(f"INVALID_M4_INPUT: {error}") from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output_path.name}-", dir=str(output_path.parent)
        ) as temporary:
            staging = Path(temporary)
            manifest = _write_and_validate(
                staging,
                corpus,
                parent_m4_manifest_sha256,
                parent_m4_manifest,
                definitions,
                review_values,
                relations,
                admissibility,
                evolution,
                link_values,
                decision_values,
            )
            os.replace(staging, output_path)
    except CapabilityBuildError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise CapabilityBuildError(f"PUBLICATION_FAILURE: {error}") from error
    return M4BuildResultV1(
        output_path,
        manifest,
        corpus.requirements,
        definitions,
        relations,
        link_values,
        decision_values,
    )


__all__ = [
    "CapabilityBuildError",
    "M4BuildResultV1",
    "build_reference_m4",
]
