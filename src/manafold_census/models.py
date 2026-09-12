"""Immutable typed models for the initial Census lifecycle contract."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar, cast

from .canonical import JSONValue, canonical_json_bytes
from .digest import (
    ARTIFACT_MANIFEST_DOMAIN,
    DATASET_MANIFEST_DOMAIN,
    SOURCE_LOCK_DOMAIN,
    STUDY_SPEC_DOMAIN,
    domain_digest,
    sha256_file,
)

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/_-]*$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$"
)


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    if any(ord(character) < 0x20 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


def _require_identifier(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _IDENTIFIER_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} is not a stable identifier")
    return text


def _require_digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _require_nonnegative_int(field: str, value: object) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _require_wire_object(value: object, expected_keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("wire value must be an object")
    actual_keys = set(value)
    missing = expected_keys - actual_keys
    unknown = actual_keys - expected_keys
    if missing:
        raise ValueError(f"wire object is missing properties: {sorted(missing)}")
    if unknown:
        raise ValueError(f"wire object has unknown properties: {sorted(unknown)}")
    return cast(dict[str, object], value)


def _require_schema(document: dict[str, object], expected: str) -> None:
    if document["schema"] != expected:
        raise ValueError(f"schema must be {expected}")


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    """Immutable provenance for one exact external byte artifact."""

    source_id: str
    locator: str
    sha256: str
    byte_length: int
    media_type: str

    SCHEMA: ClassVar[str] = "census.source-artifact.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "source_id",
        "locator",
        "sha256",
        "byte_length",
        "media_type",
    }

    def __post_init__(self) -> None:
        _require_identifier("source_id", self.source_id)
        _require_text("locator", self.locator)
        _require_digest("sha256", self.sha256)
        _require_nonnegative_int("byte_length", self.byte_length)
        media_type = _require_text("media_type", self.media_type)
        if _MEDIA_TYPE_PATTERN.fullmatch(media_type) is None:
            raise ValueError("media_type must be a simple type/subtype value")

    @classmethod
    def from_file(
        cls,
        source_id: str,
        locator: str,
        path: str | Path,
        media_type: str,
    ) -> SourceArtifact:
        file_path = Path(path)
        return cls(
            source_id=source_id,
            locator=locator,
            sha256=sha256_file(file_path),
            byte_length=file_path.stat().st_size,
            media_type=media_type,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "source_id": self.source_id,
            "locator": self.locator,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "media_type": self.media_type,
        }

    @classmethod
    def from_wire(cls, value: object) -> SourceArtifact:
        document = _require_wire_object(value, cls._WIRE_KEYS)
        _require_schema(document, cls.SCHEMA)
        return cls(
            source_id=cast(str, document["source_id"]),
            locator=cast(str, document["locator"]),
            sha256=cast(str, document["sha256"]),
            byte_length=cast(int, document["byte_length"]),
            media_type=cast(str, document["media_type"]),
        )


@dataclass(frozen=True, slots=True)
class SourceLock:
    """The deterministically ordered source set required by a dataset."""

    artifacts: tuple[SourceArtifact, ...]

    SCHEMA: ClassVar[str] = "census.source-lock.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {"schema", "artifacts"}

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts, tuple | list):
            raise TypeError("artifacts must be a tuple or list")
        artifacts = tuple(self.artifacts)
        if not artifacts:
            raise ValueError("source lock must contain at least one artifact")
        if any(not isinstance(artifact, SourceArtifact) for artifact in artifacts):
            raise TypeError("source lock artifacts must be SourceArtifact values")
        source_ids = [artifact.source_id for artifact in artifacts]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source_id in source lock")
        object.__setattr__(
            self,
            "artifacts",
            tuple(sorted(artifacts, key=lambda artifact: artifact.source_id)),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "artifacts": [artifact.to_wire() for artifact in self.artifacts],
        }

    def digest(self) -> str:
        return domain_digest(SOURCE_LOCK_DOMAIN, self.to_wire())

    @classmethod
    def from_wire(cls, value: object) -> SourceLock:
        document = _require_wire_object(value, cls._WIRE_KEYS)
        _require_schema(document, cls.SCHEMA)
        raw_artifacts = document["artifacts"]
        if not isinstance(raw_artifacts, list):
            raise TypeError("source lock artifacts must be an array")
        return cls(tuple(SourceArtifact.from_wire(item) for item in raw_artifacts))


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """A reproducible logical data-product identity."""

    dataset_id: str
    dataset_version: str
    source_lock_digest: str
    normalization_profile: str
    record_count: int

    SCHEMA: ClassVar[str] = "census.dataset-manifest.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "dataset_id",
        "dataset_version",
        "source_lock_digest",
        "normalization_profile",
        "record_count",
    }

    def __post_init__(self) -> None:
        _require_identifier("dataset_id", self.dataset_id)
        _require_identifier("dataset_version", self.dataset_version)
        _require_digest("source_lock_digest", self.source_lock_digest)
        _require_identifier("normalization_profile", self.normalization_profile)
        _require_nonnegative_int("record_count", self.record_count)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "source_lock_digest": self.source_lock_digest,
            "normalization_profile": self.normalization_profile,
            "record_count": self.record_count,
        }

    def digest(self) -> str:
        return domain_digest(DATASET_MANIFEST_DOMAIN, self.to_wire())

    @classmethod
    def from_wire(cls, value: object) -> DatasetManifest:
        document = _require_wire_object(value, cls._WIRE_KEYS)
        _require_schema(document, cls.SCHEMA)
        return cls(
            dataset_id=cast(str, document["dataset_id"]),
            dataset_version=cast(str, document["dataset_version"]),
            source_lock_digest=cast(str, document["source_lock_digest"]),
            normalization_profile=cast(str, document["normalization_profile"]),
            record_count=cast(int, document["record_count"]),
        )


@dataclass(frozen=True, slots=True)
class StudySpec:
    """A deterministic operation and parameter set applied to datasets."""

    study_id: str
    dataset_refs: tuple[str, ...]
    operation: str
    parameters: Mapping[str, JSONValue]

    SCHEMA: ClassVar[str] = "census.study-spec.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "study_id",
        "dataset_refs",
        "operation",
        "parameters",
    }

    def __post_init__(self) -> None:
        _require_identifier("study_id", self.study_id)
        if not isinstance(self.dataset_refs, tuple | list):
            raise TypeError("dataset_refs must be a tuple or list")
        refs = tuple(
            _require_identifier("dataset_refs item", reference)
            for reference in self.dataset_refs
        )
        if not refs:
            raise ValueError("study must reference at least one dataset")
        if len(refs) != len(set(refs)):
            raise ValueError("study dataset_refs must be unique")
        object.__setattr__(self, "dataset_refs", refs)
        _require_identifier("operation", self.operation)
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be an object")
        parameter_document = dict(self.parameters)
        canonical_json_bytes(parameter_document)
        object.__setattr__(self, "parameters", MappingProxyType(parameter_document))

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "study_id": self.study_id,
            "dataset_refs": list(self.dataset_refs),
            "operation": self.operation,
            "parameters": dict(self.parameters),
        }

    def digest(self) -> str:
        return domain_digest(STUDY_SPEC_DOMAIN, self.to_wire())

    @classmethod
    def from_wire(cls, value: object) -> StudySpec:
        document = _require_wire_object(value, cls._WIRE_KEYS)
        _require_schema(document, cls.SCHEMA)
        raw_refs = document["dataset_refs"]
        raw_parameters = document["parameters"]
        if not isinstance(raw_refs, list):
            raise TypeError("study dataset_refs must be an array")
        if not isinstance(raw_parameters, dict):
            raise TypeError("study parameters must be an object")
        return cls(
            study_id=cast(str, document["study_id"]),
            dataset_refs=tuple(cast(str, reference) for reference in raw_refs),
            operation=cast(str, document["operation"]),
            parameters=cast(Mapping[str, JSONValue], raw_parameters),
        )


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Provenance and byte identity for one Study-produced output."""

    artifact_id: str
    artifact_kind: str
    study_digest: str
    content_sha256: str
    byte_length: int

    SCHEMA: ClassVar[str] = "census.artifact-manifest.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "artifact_id",
        "artifact_kind",
        "study_digest",
        "content_sha256",
        "byte_length",
    }

    def __post_init__(self) -> None:
        _require_identifier("artifact_id", self.artifact_id)
        _require_identifier("artifact_kind", self.artifact_kind)
        _require_digest("study_digest", self.study_digest)
        _require_digest("content_sha256", self.content_sha256)
        _require_nonnegative_int("byte_length", self.byte_length)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "study_digest": self.study_digest,
            "content_sha256": self.content_sha256,
            "byte_length": self.byte_length,
        }

    def digest(self) -> str:
        return domain_digest(ARTIFACT_MANIFEST_DOMAIN, self.to_wire())

    @classmethod
    def from_wire(cls, value: object) -> ArtifactManifest:
        document = _require_wire_object(value, cls._WIRE_KEYS)
        _require_schema(document, cls.SCHEMA)
        return cls(
            artifact_id=cast(str, document["artifact_id"]),
            artifact_kind=cast(str, document["artifact_kind"]),
            study_digest=cast(str, document["study_digest"]),
            content_sha256=cast(str, document["content_sha256"]),
            byte_length=cast(int, document["byte_length"]),
        )
