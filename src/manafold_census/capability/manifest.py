"""Canonical M4 ontology manifests and authoritative file descriptors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from ..semantic.primitives import _require_int, _require_object, _require_text

M4_MANIFEST_SCHEMA = "census.m4-ontology-manifest.v1"
M4_ONTOLOGY_SCHEMA = "census.capability-ontology.v1"
M4_BUILD_PROFILE = "census.m4-reference.v1"
M4_DIMENSION_REGISTRY_VERSION = "1"
M4_MANIFEST_FILENAME = "m4-ontology-manifest.json"
SHARD_NAMES = tuple("0123456789abcdef")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PATH_PATTERN = re.compile(
    r"^(?:capabilities|review-authority|capability-relations|"
    r"requirement-admissibility|evolution)\.jsonl$|"
    r"^(?:links|mapping-decisions)/[0-9a-f]\.jsonl$"
)


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


@dataclass(frozen=True, slots=True)
class M4FileDescriptorV1:
    """Digest and cardinality for one canonical M4 JSONL file."""

    relative_path: str
    sha256: str
    byte_length: int
    record_count: int

    _WIRE_KEYS: ClassVar[set[str]] = {
        "relative_path",
        "sha256",
        "byte_length",
        "record_count",
    }

    def __post_init__(self) -> None:
        relative_path = _require_text("relative_path", self.relative_path)
        if _PATH_PATTERN.fullmatch(relative_path) is None:
            raise ValueError("relative_path is not a permitted M4 artifact path")
        _digest("sha256", self.sha256)
        _require_int("byte_length", self.byte_length, nonnegative=True)
        _require_int("record_count", self.record_count, nonnegative=True)
        object.__setattr__(self, "relative_path", relative_path)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "record_count": self.record_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> M4FileDescriptorV1:
        document = _require_object(value, cls._WIRE_KEYS, "M4 file descriptor")
        result = cls(
            relative_path=cast(str, document["relative_path"]),
            sha256=cast(str, document["sha256"]),
            byte_length=cast(int, document["byte_length"]),
            record_count=cast(int, document["record_count"]),
        )
        if result.to_wire() != document:
            raise ValueError("M4 file descriptor wire is not canonical")
        return result


def _descriptor(value: object, field: str, relative_path: str) -> M4FileDescriptorV1:
    if not isinstance(value, M4FileDescriptorV1):
        raise TypeError(f"{field} must be an M4FileDescriptorV1")
    if value.relative_path != relative_path:
        raise ValueError(f"{field} must identify {relative_path}")
    return value


def _shards(value: object, field: str, prefix: str) -> tuple[M4FileDescriptorV1, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    values = tuple(value)
    if len(values) != len(SHARD_NAMES):
        raise ValueError(f"{field} must contain exactly 16 shard descriptors")
    descriptors = tuple(
        _descriptor(item, f"{field}[{index}]", f"{prefix}/{shard}.jsonl")
        for index, (item, shard) in enumerate(zip(values, SHARD_NAMES, strict=True))
    )
    return descriptors


@dataclass(frozen=True, slots=True)
class M4OntologyManifestV1:
    schema: str
    ontology_schema: str
    build_profile: str
    m3_analysis_manifest_sha256: str
    m3_analysis_schema: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    m4_dimension_registry_version: str
    parent_m4_manifest_sha256: str | None
    requirement_set_digest: str
    capability_file: M4FileDescriptorV1
    review_file: M4FileDescriptorV1
    relation_file: M4FileDescriptorV1
    admissibility_file: M4FileDescriptorV1
    evolution_file: M4FileDescriptorV1
    link_shards: tuple[M4FileDescriptorV1, ...]
    mapping_decision_shards: tuple[M4FileDescriptorV1, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "ontology_schema",
        "build_profile",
        "m3_analysis_manifest_sha256",
        "m3_analysis_schema",
        "m2_requirement_schema",
        "m2_bundle_schema",
        "m4_dimension_registry_version",
        "parent_m4_manifest_sha256",
        "requirement_set_digest",
        "capability_file",
        "review_file",
        "relation_file",
        "admissibility_file",
        "evolution_file",
        "link_shards",
        "mapping_decision_shards",
    }

    def __post_init__(self) -> None:
        if _require_text("schema", self.schema) != M4_MANIFEST_SCHEMA:
            raise ValueError(f"schema must be {M4_MANIFEST_SCHEMA}")
        if _require_text("ontology_schema", self.ontology_schema) != M4_ONTOLOGY_SCHEMA:
            raise ValueError(f"ontology_schema must be {M4_ONTOLOGY_SCHEMA}")
        if _require_text("build_profile", self.build_profile) != M4_BUILD_PROFILE:
            raise ValueError(f"build_profile must be {M4_BUILD_PROFILE}")
        if _require_text("m3_analysis_schema", self.m3_analysis_schema) != (
            "census.card-analysis.v1"
        ):
            raise ValueError("m3_analysis_schema must be census.card-analysis.v1")
        if _require_text("m2_requirement_schema", self.m2_requirement_schema) != (
            "census.semantic-requirement.v1"
        ):
            raise ValueError(
                "m2_requirement_schema must be census.semantic-requirement.v1"
            )
        if _require_text("m2_bundle_schema", self.m2_bundle_schema) != (
            "census.semantic-requirement-bundle.v1"
        ):
            raise ValueError(
                "m2_bundle_schema must be census.semantic-requirement-bundle.v1"
            )
        if (
            _require_text(
                "m4_dimension_registry_version", self.m4_dimension_registry_version
            )
            != M4_DIMENSION_REGISTRY_VERSION
        ):
            raise ValueError(
                f"m4_dimension_registry_version must be {M4_DIMENSION_REGISTRY_VERSION}"
            )
        _digest("m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256)
        if self.parent_m4_manifest_sha256 is not None:
            _digest("parent_m4_manifest_sha256", self.parent_m4_manifest_sha256)
        _digest("requirement_set_digest", self.requirement_set_digest)
        _descriptor(self.capability_file, "capability_file", "capabilities.jsonl")
        _descriptor(self.review_file, "review_file", "review-authority.jsonl")
        _descriptor(
            self.relation_file,
            "relation_file",
            "capability-relations.jsonl",
        )
        _descriptor(
            self.admissibility_file,
            "admissibility_file",
            "requirement-admissibility.jsonl",
        )
        _descriptor(self.evolution_file, "evolution_file", "evolution.jsonl")
        link_shards = _shards(self.link_shards, "link_shards", "links")
        mapping_shards = _shards(
            self.mapping_decision_shards,
            "mapping_decision_shards",
            "mapping-decisions",
        )
        object.__setattr__(self, "link_shards", link_shards)
        object.__setattr__(self, "mapping_decision_shards", mapping_shards)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.schema,
            "ontology_schema": self.ontology_schema,
            "build_profile": self.build_profile,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "m3_analysis_schema": self.m3_analysis_schema,
            "m2_requirement_schema": self.m2_requirement_schema,
            "m2_bundle_schema": self.m2_bundle_schema,
            "m4_dimension_registry_version": self.m4_dimension_registry_version,
            "parent_m4_manifest_sha256": self.parent_m4_manifest_sha256,
            "requirement_set_digest": self.requirement_set_digest,
            "capability_file": self.capability_file.to_wire(),
            "review_file": self.review_file.to_wire(),
            "relation_file": self.relation_file.to_wire(),
            "admissibility_file": self.admissibility_file.to_wire(),
            "evolution_file": self.evolution_file.to_wire(),
            "link_shards": [item.to_wire() for item in self.link_shards],
            "mapping_decision_shards": [
                item.to_wire() for item in self.mapping_decision_shards
            ],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire())

    def digest(self) -> str:
        """Return the raw SHA-256 of the exact canonical manifest bytes."""

        return sha256_bytes(self.canonical_bytes())

    @classmethod
    def from_wire(cls, value: object) -> M4OntologyManifestV1:
        document = _require_object(value, cls._WIRE_KEYS, "M4 ontology manifest")
        raw_links = document["link_shards"]
        raw_mapping = document["mapping_decision_shards"]
        if not isinstance(raw_links, list) or not isinstance(raw_mapping, list):
            raise TypeError("M4 manifest shard fields must be JSON arrays")
        result = cls(
            schema=cast(str, document["schema"]),
            ontology_schema=cast(str, document["ontology_schema"]),
            build_profile=cast(str, document["build_profile"]),
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            m3_analysis_schema=cast(str, document["m3_analysis_schema"]),
            m2_requirement_schema=cast(str, document["m2_requirement_schema"]),
            m2_bundle_schema=cast(str, document["m2_bundle_schema"]),
            m4_dimension_registry_version=cast(
                str, document["m4_dimension_registry_version"]
            ),
            parent_m4_manifest_sha256=cast(
                str | None, document["parent_m4_manifest_sha256"]
            ),
            requirement_set_digest=cast(str, document["requirement_set_digest"]),
            capability_file=M4FileDescriptorV1.from_wire(document["capability_file"]),
            review_file=M4FileDescriptorV1.from_wire(document["review_file"]),
            relation_file=M4FileDescriptorV1.from_wire(document["relation_file"]),
            admissibility_file=M4FileDescriptorV1.from_wire(
                document["admissibility_file"]
            ),
            evolution_file=M4FileDescriptorV1.from_wire(document["evolution_file"]),
            link_shards=tuple(M4FileDescriptorV1.from_wire(item) for item in raw_links),
            mapping_decision_shards=tuple(
                M4FileDescriptorV1.from_wire(item) for item in raw_mapping
            ),
        )
        if result.to_wire() != document:
            raise ValueError("M4 ontology manifest wire is not canonical")
        return result


__all__ = [
    "M4_BUILD_PROFILE",
    "M4_DIMENSION_REGISTRY_VERSION",
    "M4FileDescriptorV1",
    "M4_MANIFEST_FILENAME",
    "M4_MANIFEST_SCHEMA",
    "M4_ONTOLOGY_SCHEMA",
    "M4OntologyManifestV1",
    "SHARD_NAMES",
]
