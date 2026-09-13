"""Canonical M3 shard descriptors, identity digests, and run manifest."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, sha256_bytes
from .model import CardAnalysisRecordV1, card_source_key

ANALYSIS_MANIFEST_SCHEMA = "census.analysis-manifest.v1"
ANALYSIS_INDEX_DIGEST_DOMAIN = "census.card-analysis-index.v1"
TRACE_INDEX_DIGEST_DOMAIN = "census.analysis-trace-index.v1"
IDENTITY_SET_DIGEST_DOMAIN = "census.card-analysis-identity-set.v1"
SHARD_NAMES = tuple("0123456789abcdef")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SHARD_PATH_PATTERN = re.compile(r"^(records|trace)/([0-9a-f])\.jsonl$")


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_count(field: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def analysis_shard_for(oracle_id: str) -> str:
    if not isinstance(oracle_id, str) or not oracle_id:
        raise ValueError("oracle_id must be non-empty")
    shard = oracle_id[0].lower()
    if shard not in SHARD_NAMES:
        raise ValueError("oracle_id must start with a hexadecimal character")
    return shard


@dataclass(frozen=True, slots=True)
class AnalysisShardDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.relative_path, str):
            raise TypeError("relative_path must be a string")
        match = _SHARD_PATH_PATTERN.fullmatch(self.relative_path)
        if match is None:
            raise ValueError("relative_path must identify a records or trace shard")
        _require_digest("sha256", self.sha256)
        _require_count("byte_length", self.byte_length)
        _require_count("record_count", self.record_count)

    @property
    def kind(self) -> str:
        match = _SHARD_PATH_PATTERN.fullmatch(self.relative_path)
        assert match is not None
        return match.group(1)

    @property
    def shard(self) -> str:
        match = _SHARD_PATH_PATTERN.fullmatch(self.relative_path)
        assert match is not None
        return match.group(2)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "record_count": self.record_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> AnalysisShardDescriptorV1:
        if not isinstance(value, dict):
            raise TypeError("shard descriptor must be an object")
        expected = {"relative_path", "sha256", "byte_length", "record_count"}
        actual = set(value)
        if actual != expected:
            raise ValueError("shard descriptor has missing or unexpected properties")
        return cls(
            relative_path=cast(str, value["relative_path"]),
            sha256=cast(str, value["sha256"]),
            byte_length=cast(int, value["byte_length"]),
            record_count=cast(int, value["record_count"]),
        )


def index_digest_for(
    descriptors: tuple[AnalysisShardDescriptorV1, ...],
    domain: str,
) -> str:
    if len(descriptors) != 16:
        raise ValueError("an index requires exactly 16 shard descriptors")
    if tuple(item.shard for item in descriptors) != SHARD_NAMES:
        raise ValueError("shard descriptors must contain ordered 0-f shards")
    return domain_digest(
        domain,
        cast(JSONValue, [item.to_wire() for item in descriptors]),
    )


def record_identity_set_digest(
    keys: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
) -> str:
    identities = [
        {
            "record_schema": key[0],
            "oracle_id": key[1],
            "source_card_id": key[2],
            "source_record_sha256": key[3],
        }
        for key in keys
    ]
    identities.sort(key=lambda item: (item["record_schema"], item["oracle_id"]))
    return domain_digest(IDENTITY_SET_DIGEST_DOMAIN, cast(JSONValue, identities))


def partition_records(
    records: list[CardAnalysisRecordV1] | tuple[CardAnalysisRecordV1, ...],
    partition_count: int,
) -> tuple[tuple[CardAnalysisRecordV1, ...], ...]:
    if type(partition_count) is not int or partition_count <= 0:
        raise ValueError("partition_count must be positive")
    ordered = sorted(records, key=lambda item: card_source_key(item.source))
    partitions: list[list[CardAnalysisRecordV1]] = [[] for _ in range(partition_count)]
    for ordinal, record in enumerate(ordered):
        partitions[ordinal % partition_count].append(record)
    return tuple(tuple(partition) for partition in partitions)


def merge_partitioned_records(
    partitions: tuple[tuple[CardAnalysisRecordV1, ...], ...]
    | list[tuple[CardAnalysisRecordV1, ...]],
) -> tuple[CardAnalysisRecordV1, ...]:
    flattened = [record for partition in partitions for record in partition]
    keys = [card_source_key(record.source) for record in flattened]
    if len(keys) != len(set(keys)):
        raise ValueError("partition merge contains duplicate source identity")
    return tuple(sorted(flattened, key=lambda item: card_source_key(item.source)))


@dataclass(frozen=True, slots=True)
class AnalysisManifestV1:
    analysis_schema: str
    source_lock_digest: str
    structural_record_schema: str
    structural_index_manifest_sha256: str
    structural_index_aggregate_digest: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    producer_registry_digest: str
    pattern_registry_digest: str
    build_profile: str
    record_count: int
    record_identity_set_digest: str
    record_shards: tuple[AnalysisShardDescriptorV1, ...]
    trace_shards: tuple[AnalysisShardDescriptorV1, ...]
    record_index_digest: str
    trace_index_digest: str

    SCHEMA: ClassVar[str] = ANALYSIS_MANIFEST_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "analysis_schema",
        "source_lock_digest",
        "structural_record_schema",
        "structural_index_manifest_sha256",
        "structural_index_aggregate_digest",
        "m2_requirement_schema",
        "m2_bundle_schema",
        "producer_registry_digest",
        "pattern_registry_digest",
        "build_profile",
        "record_count",
        "record_identity_set_digest",
        "record_shards",
        "trace_shards",
        "record_index_digest",
        "trace_index_digest",
    }

    def __post_init__(self) -> None:
        expected_text = {
            "analysis_schema": ANALYSIS_MANIFEST_SCHEMA.replace(
                "analysis-manifest", "card-analysis"
            ),
            "structural_record_schema": "census.structural-card.v1",
            "m2_requirement_schema": "census.semantic-requirement.v1",
            "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
        }
        for field, expected in expected_text.items():
            value = _require_text(field, getattr(self, field))
            if value != expected:
                raise ValueError(f"{field} must be {expected}")
        for field in (
            "source_lock_digest",
            "structural_index_manifest_sha256",
            "structural_index_aggregate_digest",
            "producer_registry_digest",
            "pattern_registry_digest",
            "record_identity_set_digest",
            "record_index_digest",
            "trace_index_digest",
        ):
            _require_digest(field, getattr(self, field))
        _require_text("build_profile", self.build_profile)
        _require_count("record_count", self.record_count)
        record_shards = tuple(self.record_shards)
        trace_shards = tuple(self.trace_shards)
        if tuple(item.shard for item in record_shards) != SHARD_NAMES:
            raise ValueError("record_shards must contain ordered 0-f shards")
        if tuple(item.kind for item in record_shards) != ("records",) * 16:
            raise ValueError("record_shards must use records paths")
        if tuple(item.shard for item in trace_shards) != SHARD_NAMES:
            raise ValueError("trace_shards must contain ordered 0-f shards")
        if tuple(item.kind for item in trace_shards) != ("trace",) * 16:
            raise ValueError("trace_shards must use trace paths")
        if (
            index_digest_for(record_shards, ANALYSIS_INDEX_DIGEST_DOMAIN)
            != self.record_index_digest
        ):
            raise ValueError("record_index_digest does not match descriptors")
        if (
            index_digest_for(trace_shards, TRACE_INDEX_DIGEST_DOMAIN)
            != self.trace_index_digest
        ):
            raise ValueError("trace_index_digest does not match descriptors")
        object.__setattr__(self, "record_shards", record_shards)
        object.__setattr__(self, "trace_shards", trace_shards)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "analysis_schema": self.analysis_schema,
            "source_lock_digest": self.source_lock_digest,
            "structural_record_schema": self.structural_record_schema,
            "structural_index_manifest_sha256": self.structural_index_manifest_sha256,
            "structural_index_aggregate_digest": self.structural_index_aggregate_digest,
            "m2_requirement_schema": self.m2_requirement_schema,
            "m2_bundle_schema": self.m2_bundle_schema,
            "producer_registry_digest": self.producer_registry_digest,
            "pattern_registry_digest": self.pattern_registry_digest,
            "build_profile": self.build_profile,
            "record_count": self.record_count,
            "record_identity_set_digest": self.record_identity_set_digest,
            "record_shards": [item.to_wire() for item in self.record_shards],
            "trace_shards": [item.to_wire() for item in self.trace_shards],
            "record_index_digest": self.record_index_digest,
            "trace_index_digest": self.trace_index_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> AnalysisManifestV1:
        if not isinstance(value, dict):
            raise TypeError("analysis manifest must be an object")
        if set(value) != cls._WIRE_KEYS:
            raise ValueError("analysis manifest has missing or unexpected properties")
        if value["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        record_shards = value["record_shards"]
        trace_shards = value["trace_shards"]
        if not isinstance(record_shards, list) or not isinstance(trace_shards, list):
            raise TypeError("record_shards and trace_shards must be arrays")
        return cls(
            analysis_schema=cast(str, value["analysis_schema"]),
            source_lock_digest=cast(str, value["source_lock_digest"]),
            structural_record_schema=cast(str, value["structural_record_schema"]),
            structural_index_manifest_sha256=cast(
                str, value["structural_index_manifest_sha256"]
            ),
            structural_index_aggregate_digest=cast(
                str, value["structural_index_aggregate_digest"]
            ),
            m2_requirement_schema=cast(str, value["m2_requirement_schema"]),
            m2_bundle_schema=cast(str, value["m2_bundle_schema"]),
            producer_registry_digest=cast(str, value["producer_registry_digest"]),
            pattern_registry_digest=cast(str, value["pattern_registry_digest"]),
            build_profile=cast(str, value["build_profile"]),
            record_count=cast(int, value["record_count"]),
            record_identity_set_digest=cast(str, value["record_identity_set_digest"]),
            record_shards=tuple(
                AnalysisShardDescriptorV1.from_wire(item) for item in record_shards
            ),
            trace_shards=tuple(
                AnalysisShardDescriptorV1.from_wire(item) for item in trace_shards
            ),
            record_index_digest=cast(str, value["record_index_digest"]),
            trace_index_digest=cast(str, value["trace_index_digest"]),
        )

    def digest(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.to_wire()))


__all__ = [
    "ANALYSIS_INDEX_DIGEST_DOMAIN",
    "ANALYSIS_MANIFEST_SCHEMA",
    "IDENTITY_SET_DIGEST_DOMAIN",
    "SHARD_NAMES",
    "TRACE_INDEX_DIGEST_DOMAIN",
    "AnalysisManifestV1",
    "AnalysisShardDescriptorV1",
    "analysis_shard_for",
    "index_digest_for",
    "merge_partitioned_records",
    "partition_records",
    "record_identity_set_digest",
]
