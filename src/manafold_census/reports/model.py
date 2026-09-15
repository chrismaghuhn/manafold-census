"""Closed wire models for derived file descriptors and manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..semantic.primitives import _require_int
from .report_contract import _digest, _object, _release_id, _text

CENSUS_REPORT_SCHEMA = "census.census-report.v1"
REPORT_INDEX_SCHEMA = "census.census-report-index.v1"
INDEX_MANIFEST_SCHEMA = "census.census-index-manifest.v1"

REPORT_INDEX_FILENAME = "reports/report-index.json"
REPORT_FILENAME = "reports/census-report.json"
UNRESOLVED_ANALYSIS_FILENAME = "reports/unresolved-analysis.jsonl"
MAPPING_REVIEW_QUEUE_FILENAME = "reports/mapping-review-queue.jsonl"
INDEX_MANIFEST_FILENAME = "indexes/index-manifest.json"
INDEX_DATA_FILES = (
    "indexes/cards-by-name.jsonl",
    "indexes/cards-by-oracle-id.jsonl",
    "indexes/requirements-by-card.jsonl",
    "indexes/links-by-requirement.jsonl",
    "indexes/cards-by-capability.jsonl",
)
REPORT_DATA_FILES = (
    REPORT_FILENAME,
    UNRESOLVED_ANALYSIS_FILENAME,
    MAPPING_REVIEW_QUEUE_FILENAME,
)
DERIVED_FILES = frozenset(
    {
        REPORT_INDEX_FILENAME,
        *REPORT_DATA_FILES,
        INDEX_MANIFEST_FILENAME,
        *INDEX_DATA_FILES,
    }
)
_RELATIVE_PATH = re.compile(r"^(?:reports|indexes)/[a-z0-9-]+\.(?:json|jsonl)$")


@dataclass(frozen=True, slots=True)
class DerivedFileDescriptorV1:
    """Digest, byte length, and row count for one derived file."""

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
        path = _text("relative_path", self.relative_path)
        if _RELATIVE_PATH.fullmatch(path) is None:
            raise ValueError("relative_path is not a permitted derived file")
        _digest("sha256", self.sha256)
        _require_int("byte_length", self.byte_length, nonnegative=True)
        _require_int("record_count", self.record_count, nonnegative=True)
        object.__setattr__(self, "relative_path", path)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "record_count": self.record_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> DerivedFileDescriptorV1:
        document = _object(value, cls._WIRE_KEYS, "derived file descriptor")
        result = cls(
            cast(str, document["relative_path"]),
            cast(str, document["sha256"]),
            cast(int, document["byte_length"]),
            cast(int, document["record_count"]),
        )
        if result.to_wire() != document:
            raise ValueError("derived file descriptor is not canonical")
        return result


def _validate_descriptor_paths(
    descriptors: tuple[DerivedFileDescriptorV1, ...],
    expected: tuple[str, ...],
    field: str,
) -> None:
    if tuple(item.relative_path for item in descriptors) != expected:
        raise ValueError(f"{field} must contain the frozen ordered file set")


@dataclass(frozen=True, slots=True)
class ReportIndexV1:
    census_manifest_sha256: str
    census_release_id: str
    report_descriptors: tuple[DerivedFileDescriptorV1, ...]

    SCHEMA: ClassVar[str] = REPORT_INDEX_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "report_index_schema",
        "census_manifest_sha256",
        "census_release_id",
        "report_descriptors",
    }

    def __post_init__(self) -> None:
        _digest("census_manifest_sha256", self.census_manifest_sha256)
        _release_id("census_release_id", self.census_release_id)
        descriptors = tuple(self.report_descriptors)
        if any(not isinstance(item, DerivedFileDescriptorV1) for item in descriptors):
            raise TypeError("report_descriptors must contain typed values")
        _validate_descriptor_paths(descriptors, REPORT_DATA_FILES, "report_descriptors")
        object.__setattr__(self, "report_descriptors", descriptors)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "report_index_schema": self.SCHEMA,
            "census_manifest_sha256": self.census_manifest_sha256,
            "census_release_id": self.census_release_id,
            "report_descriptors": [item.to_wire() for item in self.report_descriptors],
        }

    @classmethod
    def from_wire(cls, value: object) -> ReportIndexV1:
        document = _object(value, cls._WIRE_KEYS, "report index")
        if document["report_index_schema"] != cls.SCHEMA:
            raise ValueError(f"report_index_schema must be {cls.SCHEMA}")
        raw = document["report_descriptors"]
        if not isinstance(raw, list):
            raise TypeError("report_descriptors must be an array")
        result = cls(
            cast(str, document["census_manifest_sha256"]),
            cast(str, document["census_release_id"]),
            tuple(DerivedFileDescriptorV1.from_wire(item) for item in raw),
        )
        if result.to_wire() != document:
            raise ValueError("report index is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class IndexManifestV1:
    census_manifest_sha256: str
    census_release_id: str
    index_descriptors: tuple[DerivedFileDescriptorV1, ...]

    SCHEMA: ClassVar[str] = INDEX_MANIFEST_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "index_manifest_schema",
        "census_manifest_sha256",
        "census_release_id",
        "index_descriptors",
    }

    def __post_init__(self) -> None:
        _digest("census_manifest_sha256", self.census_manifest_sha256)
        _release_id("census_release_id", self.census_release_id)
        descriptors = tuple(self.index_descriptors)
        if any(not isinstance(item, DerivedFileDescriptorV1) for item in descriptors):
            raise TypeError("index_descriptors must contain typed values")
        _validate_descriptor_paths(descriptors, INDEX_DATA_FILES, "index_descriptors")
        object.__setattr__(self, "index_descriptors", descriptors)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "index_manifest_schema": self.SCHEMA,
            "census_manifest_sha256": self.census_manifest_sha256,
            "census_release_id": self.census_release_id,
            "index_descriptors": [item.to_wire() for item in self.index_descriptors],
        }

    @classmethod
    def from_wire(cls, value: object) -> IndexManifestV1:
        document = _object(value, cls._WIRE_KEYS, "index manifest")
        if document["index_manifest_schema"] != cls.SCHEMA:
            raise ValueError(f"index_manifest_schema must be {cls.SCHEMA}")
        raw = document["index_descriptors"]
        if not isinstance(raw, list):
            raise TypeError("index_descriptors must be an array")
        result = cls(
            cast(str, document["census_manifest_sha256"]),
            cast(str, document["census_release_id"]),
            tuple(DerivedFileDescriptorV1.from_wire(item) for item in raw),
        )
        if result.to_wire() != document:
            raise ValueError("index manifest is not canonical")
        return result


__all__ = [
    "CENSUS_REPORT_SCHEMA",
    "DERIVED_FILES",
    "INDEX_DATA_FILES",
    "INDEX_MANIFEST_FILENAME",
    "INDEX_MANIFEST_SCHEMA",
    "MAPPING_REVIEW_QUEUE_FILENAME",
    "REPORT_DATA_FILES",
    "REPORT_FILENAME",
    "REPORT_INDEX_FILENAME",
    "REPORT_INDEX_SCHEMA",
    "UNRESOLVED_ANALYSIS_FILENAME",
    "DerivedFileDescriptorV1",
    "IndexManifestV1",
    "ReportIndexV1",
]
