"""Normative aggregate manifest for the 16 structural shard files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from .index import (
    SHARD_NAMES,
    StructuralIndexError,
    StructuralIndexSummary,
    StructuralShardSummary,
    aggregate_structural_index_digest,
)

STRUCTURAL_INDEX_MANIFEST_SCHEMA = "census.structural-card-index-manifest.v1"
STRUCTURAL_INDEX_MANIFEST_SCHEMA_PATH = (
    "schemas/structural-card-index-manifest.v1.schema.json"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PATH_PATTERN = re.compile(r"^records/([0-9a-f])\.jsonl$")


class StructuralIndexManifestError(ValueError):
    """Raised when the structural aggregate manifest is invalid."""


def _require_wire_object(
    value: object, expected_keys: set[str], label: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StructuralIndexManifestError(f"{label} must be an object")
    actual_keys = set(value)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(actual_keys - expected_keys)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing properties: {missing}")
        if unexpected:
            details.append(f"unexpected properties: {unexpected}")
        raise StructuralIndexManifestError(f"{label} has {'; '.join(details)}")
    return cast(dict[str, object], value)


@dataclass(frozen=True, slots=True)
class StructuralCardIndexManifestV1:
    """Ordered shard descriptors and their structural aggregate digest."""

    shards: tuple[StructuralShardSummary, ...]
    aggregate_digest: str

    SCHEMA: ClassVar[str] = STRUCTURAL_INDEX_MANIFEST_SCHEMA
    SCHEMA_PATH: ClassVar[str] = STRUCTURAL_INDEX_MANIFEST_SCHEMA_PATH
    _WIRE_KEYS: ClassVar[set[str]] = {"schema", "shards", "aggregate_digest"}

    def __post_init__(self) -> None:
        if tuple(shard.shard for shard in self.shards) != SHARD_NAMES:
            raise StructuralIndexManifestError(
                "manifest must contain all 16 ordered shards"
            )
        if (
            not isinstance(self.aggregate_digest, str)
            or _DIGEST_PATTERN.fullmatch(self.aggregate_digest) is None
        ):
            raise StructuralIndexManifestError(
                "aggregate_digest must be a lowercase SHA-256 digest"
            )
        if aggregate_structural_index_digest(self.shards) != self.aggregate_digest:
            raise StructuralIndexManifestError("aggregate digest mismatch")

    @classmethod
    def from_summary(
        cls, summary: StructuralIndexSummary
    ) -> StructuralCardIndexManifestV1:
        return cls(summary.shards, summary.aggregate_digest)

    @classmethod
    def from_wire(cls, value: object) -> StructuralCardIndexManifestV1:
        document = _require_wire_object(
            value, cls._WIRE_KEYS, "structural index manifest"
        )
        if document["schema"] != cls.SCHEMA:
            raise StructuralIndexManifestError(f"schema must be {cls.SCHEMA}")
        raw_shards = document["shards"]
        if not isinstance(raw_shards, list):
            raise StructuralIndexManifestError("shards must be an array")
        shards: list[StructuralShardSummary] = []
        for raw_shard in raw_shards:
            shard_document = _require_wire_object(
                raw_shard,
                {"relative_path", "sha256", "byte_length", "record_count"},
                "shard descriptor",
            )
            relative_path = shard_document["relative_path"]
            if not isinstance(relative_path, str):
                raise StructuralIndexManifestError("relative_path must be a string")
            match = _PATH_PATTERN.fullmatch(relative_path)
            if match is None:
                raise StructuralIndexManifestError("relative_path is invalid")
            try:
                shards.append(
                    StructuralShardSummary(
                        shard=match.group(1),
                        relative_path=relative_path,
                        sha256=cast(str, shard_document["sha256"]),
                        byte_length=cast(int, shard_document["byte_length"]),
                        record_count=cast(int, shard_document["record_count"]),
                    )
                )
            except StructuralIndexError as error:
                raise StructuralIndexManifestError(str(error)) from error
        return cls(
            shards=tuple(shards),
            aggregate_digest=cast(str, document["aggregate_digest"]),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "shards": [
                {
                    "relative_path": shard.relative_path,
                    "sha256": shard.sha256,
                    "byte_length": shard.byte_length,
                    "record_count": shard.record_count,
                }
                for shard in self.shards
            ],
            "aggregate_digest": self.aggregate_digest,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire())

    def digest(self) -> str:
        """Return the SHA-256 of exact canonical manifest bytes."""

        return sha256_bytes(self.canonical_bytes())
