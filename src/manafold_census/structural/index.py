"""Deterministic 16-way JSONL sharding for structural card records."""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import MAX_INTEGER, JSONValue, canonical_json_bytes
from ..digest import domain_digest
from .extract import iter_structural_records
from .model import StructuralCardRecordV1

SHARD_NAMES = tuple("0123456789abcdef")
STRUCTURAL_INDEX_DIGEST_DOMAIN = "census.structural-card-index.v1"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class StructuralIndexError(ValueError):
    """Raised when structural shard output is invalid or cannot be built."""


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise StructuralIndexError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_count(field: str, value: object) -> int:
    if type(value) is not int:
        raise StructuralIndexError(f"{field} must be an integer")
    if value < 0 or value > MAX_INTEGER:
        raise StructuralIndexError(f"{field} is outside the signed 64-bit range")
    return value


@dataclass(frozen=True, slots=True)
class StructuralShardSummary:
    """Measured byte identity and count for one structural shard."""

    shard: str
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int

    def __post_init__(self) -> None:
        if self.shard not in SHARD_NAMES:
            raise StructuralIndexError(f"invalid shard name: {self.shard}")
        expected_path = f"records/{self.shard}.jsonl"
        if self.relative_path != expected_path:
            raise StructuralIndexError(f"invalid relative path for shard {self.shard}")
        _require_digest("shard sha256", self.sha256)
        _require_count("byte_length", self.byte_length)
        _require_count("record_count", self.record_count)


def aggregate_structural_index_digest(
    shards: tuple[StructuralShardSummary, ...],
) -> str:
    """Digest the ordered 16-shard descriptor list with the M1 domain."""

    if tuple(shard.shard for shard in shards) != SHARD_NAMES:
        raise StructuralIndexError("structural index requires all 16 ordered shards")
    descriptors = [
        {
            "path": shard.relative_path,
            "sha256": shard.sha256,
            "byte_length": shard.byte_length,
            "record_count": shard.record_count,
        }
        for shard in shards
    ]
    return domain_digest(
        STRUCTURAL_INDEX_DIGEST_DOMAIN,
        cast(JSONValue, descriptors),
    )


@dataclass(frozen=True, slots=True)
class StructuralIndexSummary:
    """Measured identity and counts for a complete structural shard set."""

    shards: tuple[StructuralShardSummary, ...]
    record_count: int
    unique_oracle_id_count: int
    duplicate_oracle_id_count: int
    aggregate_digest: str

    def __post_init__(self) -> None:
        if tuple(shard.shard for shard in self.shards) != SHARD_NAMES:
            raise StructuralIndexError(
                "structural index summary requires all 16 ordered shards"
            )
        _require_count("record_count", self.record_count)
        _require_count("unique_oracle_id_count", self.unique_oracle_id_count)
        _require_count("duplicate_oracle_id_count", self.duplicate_oracle_id_count)
        _require_digest("aggregate_digest", self.aggregate_digest)
        if aggregate_structural_index_digest(self.shards) != self.aggregate_digest:
            raise StructuralIndexError("structural aggregate digest mismatch")

    @property
    def total_byte_length(self) -> int:
        return sum(shard.byte_length for shard in self.shards)

    @property
    def shard_record_counts(self) -> dict[str, int]:
        return {shard.shard: shard.record_count for shard in self.shards}


def _summary(
    shards: tuple[StructuralShardSummary, ...], unique_oracle_ids: int
) -> StructuralIndexSummary:
    return StructuralIndexSummary(
        shards=shards,
        record_count=sum(shard.record_count for shard in shards),
        unique_oracle_id_count=unique_oracle_ids,
        duplicate_oracle_id_count=0,
        aggregate_digest=aggregate_structural_index_digest(shards),
    )


def _read_shard(
    path: Path, shard: str, seen_oracle_ids: set[str]
) -> StructuralShardSummary:
    digest = hashlib.sha256()
    byte_length = 0
    record_count = 0
    previous_oracle_id: str | None = None
    try:
        stream = path.open("rb")
    except OSError as error:
        raise StructuralIndexError(f"shard {shard} could not be opened") from error
    with stream:
        while raw_line := stream.readline():
            digest.update(raw_line)
            byte_length += len(raw_line)
            if not raw_line.endswith(b"\n"):
                raise StructuralIndexError(f"shard {shard} is missing final LF")
            try:
                document = json.loads(raw_line)
                record = StructuralCardRecordV1.from_wire(document)
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as error:
                raise StructuralIndexError(
                    f"shard {shard} contains an invalid structural record"
                ) from error
            expected_bytes = canonical_json_bytes(record.to_wire()) + b"\n"
            if raw_line != expected_bytes:
                raise StructuralIndexError(f"shard {shard} contains noncanonical JSONL")
            if record.oracle_id[0] != shard:
                raise StructuralIndexError(
                    f"record {record.oracle_id} is in the wrong shard {shard}"
                )
            if (
                previous_oracle_id is not None
                and record.oracle_id <= previous_oracle_id
            ):
                raise StructuralIndexError(
                    f"shard {shard} records are not strictly ordered"
                )
            if record.oracle_id in seen_oracle_ids:
                raise StructuralIndexError(
                    f"duplicate oracle_id in structural index: {record.oracle_id}"
                )
            seen_oracle_ids.add(record.oracle_id)
            previous_oracle_id = record.oracle_id
            record_count += 1
    return StructuralShardSummary(
        shard=shard,
        relative_path=f"records/{shard}.jsonl",
        sha256=digest.hexdigest(),
        byte_length=byte_length,
        record_count=record_count,
    )


def inspect_structural_index(output_dir: str | Path) -> StructuralIndexSummary:
    """Validate the exact 16-shard set and recompute its measured identity."""

    output_path = Path(output_dir)
    if not output_path.is_dir():
        raise StructuralIndexError("structural index directory does not exist")
    actual_names = {path.name for path in output_path.iterdir()}
    expected_names = {f"{shard}.jsonl" for shard in SHARD_NAMES}
    unexpected = sorted(actual_names - expected_names)
    if unexpected:
        raise StructuralIndexError(f"unexpected shard: {unexpected[0]}")
    missing = sorted(expected_names - actual_names)
    if missing:
        raise StructuralIndexError(f"missing shard: {missing[0]}")
    seen_oracle_ids: set[str] = set()
    shards = tuple(
        _read_shard(output_path / f"{shard}.jsonl", shard, seen_oracle_ids)
        for shard in SHARD_NAMES
    )
    return _summary(shards, len(seen_oracle_ids))


def build_structural_index(
    source_path: str | Path, output_dir: str | Path
) -> StructuralIndexSummary:
    """Build a fresh deterministic 16-shard index from one source stream."""

    output_path = Path(output_dir)
    if output_path.exists() and not output_path.is_dir():
        raise StructuralIndexError("structural index output is not a directory")
    output_path.mkdir(parents=True, exist_ok=True)
    if any(output_path.iterdir()):
        raise StructuralIndexError("structural index output directory must be empty")

    records: list[StructuralCardRecordV1] = []
    seen_oracle_ids: set[str] = set()
    for record in iter_structural_records(source_path):
        if record.oracle_id in seen_oracle_ids:
            raise StructuralIndexError(f"duplicate oracle_id: {record.oracle_id}")
        seen_oracle_ids.add(record.oracle_id)
        records.append(record)
    records.sort(key=lambda record: record.oracle_id)

    with ExitStack() as stack:
        streams = {
            shard: stack.enter_context((output_path / f"{shard}.jsonl").open("wb"))
            for shard in SHARD_NAMES
        }
        for record in records:
            shard = record.oracle_id[0]
            streams[shard].write(canonical_json_bytes(record.to_wire()) + b"\n")
    return inspect_structural_index(output_path)
