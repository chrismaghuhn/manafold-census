"""Canonical file writing and reread for the reviewed authority package."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from ..canonical import canonical_json_bytes
from ..capability.admissibility import SourceRequirementAdmissibilityV1
from ..capability.definition import CapabilityDefinitionV1
from ..capability.evolution import CapabilityEvolutionV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.relations import CapabilityRelationV1, relation_sort_key
from ..capability.review import CapabilityReviewRecordV1
from ..digest import sha256_bytes
from ..validation import validate_document
from .authority_package import (
    AUTHORITY_PACKAGE_FILES,
    AuthorityFileDescriptorV1,
    AuthorityPackageContentsV1,
    AuthorityPackageManifestV1,
    AuthorityReviewPolicyV1,
)


def _definition_key(value: object) -> tuple[str, str, str]:
    item = cast(CapabilityDefinitionV1, value)
    return (
        item.capability_family_id,
        f"{item.capability_version:020d}",
        item.claim_digest,
    )


def _review_key(value: object) -> tuple[str, str, str]:
    item = cast(CapabilityReviewRecordV1, value)
    subject = item.subject.to_wire()
    return (
        cast(str, subject["type"]),
        canonical_json_bytes(subject).decode(),
        item.record_id,
    )


def _relation_key(value: object) -> tuple[str, bytes, bytes, str]:
    return relation_sort_key(cast(CapabilityRelationV1, value))


def _admissibility_key(value: object) -> tuple[str, str]:
    item = cast(SourceRequirementAdmissibilityV1, value)
    return item.requirement_id, item.record_id


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
    return item.requirement_id, item.requirement_id


def _evolution_key(value: object) -> tuple[str, str, str, str]:
    item = cast(CapabilityEvolutionV1, value)
    return (
        item.operation.value,
        canonical_json_bytes([ref.to_wire() for ref in item.from_references]).decode(),
        canonical_json_bytes([ref.to_wire() for ref in item.to_references]).decode(),
        item.event_id,
    )


def _write_jsonl(
    root: Path,
    relative_path: str,
    values: Sequence[Any],
    key: Callable[[object], Any],
) -> AuthorityFileDescriptorV1:
    ordered = tuple(sorted(values, key=key))
    raw = b"".join(
        canonical_json_bytes(cast(Any, value).to_wire()) + b"\n" for value in ordered
    )
    (root / relative_path).write_bytes(raw)
    return AuthorityFileDescriptorV1(
        relative_path, sha256_bytes(raw), len(raw), len(ordered)
    )


def write_authority_package(
    package_dir: str | Path,
    *,
    campaign_id: str,
    m3_analysis_manifest_sha256: str,
    m4_requirement_set_digest: str,
    selected_requirement_ids: Sequence[str],
    review_policy: AuthorityReviewPolicyV1,
    capability_definitions: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    relations: Sequence[CapabilityRelationV1],
    admissibility: Sequence[SourceRequirementAdmissibilityV1],
    links: Sequence[RequirementCapabilityLinkV1],
    mapping_decisions: Sequence[RequirementMappingDecisionV1],
    evolution: Sequence[CapabilityEvolutionV1],
) -> AuthorityPackageManifestV1:
    root = Path(package_dir)
    if root.exists() and not root.is_dir():
        raise ValueError("authority package path is not a directory")
    if root.exists() and any(root.iterdir()):
        raise ValueError("authority package output must be fresh")
    root.mkdir(parents=True, exist_ok=True)
    descriptors = (
        _write_jsonl(
            root,
            "capability-definitions.jsonl",
            capability_definitions,
            _definition_key,
        ),
        _write_jsonl(root, "review-authority.jsonl", reviews, _review_key),
        _write_jsonl(root, "capability-relations.jsonl", relations, _relation_key),
        _write_jsonl(
            root,
            "requirement-admissibility.jsonl",
            admissibility,
            _admissibility_key,
        ),
        _write_jsonl(root, "links.jsonl", links, _link_key),
        _write_jsonl(root, "mapping-decisions.jsonl", mapping_decisions, _decision_key),
        _write_jsonl(root, "evolution.jsonl", evolution, _evolution_key),
    )
    manifest = AuthorityPackageManifestV1.create(
        campaign_id=campaign_id,
        m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
        m4_requirement_set_digest=m4_requirement_set_digest,
        selected_requirement_ids=selected_requirement_ids,
        record_file_descriptors=tuple(
            sorted(descriptors, key=lambda item: item.relative_path)
        ),
        review_policy=review_policy,
    )
    (root / "authority-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )
    return manifest


def _read_jsonl(
    root: Path,
    descriptor: AuthorityFileDescriptorV1,
    parser: Callable[[object], Any],
    key: Callable[[object], Any],
) -> tuple[Any, ...]:
    path = root / descriptor.relative_path
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(
            f"missing authority artifact {descriptor.relative_path}"
        ) from error
    if sha256_bytes(raw) != descriptor.sha256 or len(raw) != descriptor.byte_length:
        raise ValueError(
            f"authority descriptor does not match {descriptor.relative_path}"
        )
    values: list[Any] = []
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError(f"{descriptor.relative_path} is missing a final LF")
        try:
            value = parser(json.loads(line))
        except (TypeError, ValueError, UnicodeDecodeError) as error:
            raise ValueError(
                f"{descriptor.relative_path} contains an invalid record"
            ) from error
        if line != canonical_json_bytes(value.to_wire()) + b"\n":
            raise ValueError(f"{descriptor.relative_path} contains noncanonical JSONL")
        values.append(value)
    if len(values) != descriptor.record_count:
        raise ValueError(f"{descriptor.relative_path} record count is stale")
    keys = [key(value) for value in values]
    if keys != sorted(keys):
        raise ValueError(f"{descriptor.relative_path} is not canonically ordered")
    return tuple(values)


def load_authority_package(package_dir: str | Path) -> AuthorityPackageContentsV1:
    root = Path(package_dir)
    try:
        raw = (root / "authority-manifest.json").read_bytes()
    except FileNotFoundError:
        raise
    except OSError as error:
        raise ValueError("authority manifest cannot be read") from error
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("authority manifest cannot be read as JSON") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("authority manifest is not canonical JSON")
    validate_document(document, "census-m4-authority-package.v1.schema.json")
    manifest = AuthorityPackageManifestV1.from_wire(document)
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    expected = {"authority-manifest.json", *AUTHORITY_PACKAGE_FILES}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise FileNotFoundError(
            "missing authority package artifact: " + ", ".join(missing)
        )
    if extra:
        raise ValueError("authority package file set mismatch")
    descriptors = {
        item.relative_path: item for item in manifest.record_file_descriptors
    }
    return AuthorityPackageContentsV1(
        root=root,
        manifest=manifest,
        capability_definitions=cast(
            tuple[CapabilityDefinitionV1, ...],
            _read_jsonl(
                root,
                descriptors["capability-definitions.jsonl"],
                CapabilityDefinitionV1.from_wire,
                _definition_key,
            ),
        ),
        reviews=cast(
            tuple[CapabilityReviewRecordV1, ...],
            _read_jsonl(
                root,
                descriptors["review-authority.jsonl"],
                CapabilityReviewRecordV1.from_wire,
                _review_key,
            ),
        ),
        relations=cast(
            tuple[CapabilityRelationV1, ...],
            _read_jsonl(
                root,
                descriptors["capability-relations.jsonl"],
                CapabilityRelationV1.from_wire,
                _relation_key,
            ),
        ),
        admissibility=cast(
            tuple[SourceRequirementAdmissibilityV1, ...],
            _read_jsonl(
                root,
                descriptors["requirement-admissibility.jsonl"],
                SourceRequirementAdmissibilityV1.from_wire,
                _admissibility_key,
            ),
        ),
        links=cast(
            tuple[RequirementCapabilityLinkV1, ...],
            _read_jsonl(
                root,
                descriptors["links.jsonl"],
                RequirementCapabilityLinkV1.from_wire,
                _link_key,
            ),
        ),
        mapping_decisions=cast(
            tuple[RequirementMappingDecisionV1, ...],
            _read_jsonl(
                root,
                descriptors["mapping-decisions.jsonl"],
                RequirementMappingDecisionV1.from_wire,
                _decision_key,
            ),
        ),
        evolution=cast(
            tuple[CapabilityEvolutionV1, ...],
            _read_jsonl(
                root,
                descriptors["evolution.jsonl"],
                CapabilityEvolutionV1.from_wire,
                _evolution_key,
            ),
        ),
    )


__all__ = ["load_authority_package", "write_authority_package"]
