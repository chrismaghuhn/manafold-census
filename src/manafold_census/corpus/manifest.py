"""The aggregate manifest for the generated multi-file record index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from .index import (
    SHARD_NAMES,
    IndexSummary,
    ShardSummary,
    aggregate_index_digest,
)

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PATH_PATTERN = re.compile(r"^records/([0-9a-f])\.jsonl$")


class IndexManifestError(ValueError):
    """Raised when an aggregate record-index manifest is invalid."""


@dataclass(frozen=True, slots=True)
class IndexRecordManifest:
    """Reviewable descriptors and identity for the complete 16-file index."""

    shards: tuple[ShardSummary, ...]
    aggregate_digest: str

    SCHEMA = "census.oracle-record-index-manifest.v1"

    def __post_init__(self) -> None:
        if tuple(shard.shard for shard in self.shards) != SHARD_NAMES:
            raise IndexManifestError(
                "index manifest must contain all 16 ordered shards"
            )
        if not isinstance(self.aggregate_digest, str) or not _DIGEST_PATTERN.fullmatch(
            self.aggregate_digest
        ):
            raise IndexManifestError(
                "aggregate_digest must be a lowercase SHA-256 digest"
            )
        if aggregate_index_digest(self.shards) != self.aggregate_digest:
            raise IndexManifestError("index manifest aggregate digest mismatch")

    @classmethod
    def from_summary(cls, summary: IndexSummary) -> IndexRecordManifest:
        return cls(summary.shards, summary.aggregate_digest)

    @classmethod
    def from_wire(cls, value: object) -> IndexRecordManifest:
        if not isinstance(value, dict):
            raise IndexManifestError("index manifest must be an object")
        expected_keys = {"schema", "shards", "aggregate_digest"}
        if set(value) != expected_keys:
            raise IndexManifestError("index manifest has missing or unexpected fields")
        if value["schema"] != cls.SCHEMA:
            raise IndexManifestError(f"schema must be {cls.SCHEMA}")
        raw_shards = value["shards"]
        if not isinstance(raw_shards, list):
            raise IndexManifestError("index manifest shards must be an array")
        shards: list[ShardSummary] = []
        for raw_shard in raw_shards:
            if not isinstance(raw_shard, dict):
                raise IndexManifestError("index manifest shard must be an object")
            shard_keys = {
                "relative_path",
                "sha256",
                "byte_length",
                "record_count",
            }
            if set(raw_shard) != shard_keys:
                raise IndexManifestError(
                    "index manifest shard has missing or unexpected fields"
                )
            relative_path = raw_shard["relative_path"]
            if not isinstance(relative_path, str):
                raise IndexManifestError("index manifest shard path must be a string")
            match = _PATH_PATTERN.fullmatch(relative_path)
            if match is None:
                raise IndexManifestError("index manifest shard path is invalid")
            shards.append(
                ShardSummary(
                    shard=match.group(1),
                    relative_path=relative_path,
                    sha256=cast(str, raw_shard["sha256"]),
                    byte_length=cast(int, raw_shard["byte_length"]),
                    record_count=cast(int, raw_shard["record_count"]),
                )
            )
        return cls(tuple(shards), cast(str, value["aggregate_digest"]))

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
        return sha256_bytes(self.canonical_bytes())
