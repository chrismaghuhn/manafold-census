"""Streaming source-record validation and deterministic 16-way sharding."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, sha256_bytes

SHARD_NAMES = tuple("0123456789abcdef")
INDEX_DIGEST_DOMAIN = "census.oracle-record-index.v1"
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CorpusIndexError(ValueError):
    """Raised when a source record or generated index is not valid."""


def _normalize_uuid(field: str, value: object) -> str:
    if not isinstance(value, str) or _UUID_PATTERN.fullmatch(value) is None:
        raise CorpusIndexError(f"{field} must be a canonical UUID")
    try:
        return str(UUID(value)).lower()
    except ValueError as error:
        raise CorpusIndexError(f"{field} must be a canonical UUID") from error


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise CorpusIndexError(f"{field} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class RecordIndexEntry:
    """The four source-fact fields retained for one Oracle record."""

    oracle_id: str
    source_card_id: str
    name: str
    source_record_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "oracle_id", _normalize_uuid("oracle_id", self.oracle_id)
        )
        object.__setattr__(
            self,
            "source_card_id",
            _normalize_uuid("source_card_id", self.source_card_id),
        )
        if not isinstance(self.name, str) or not self.name.strip():
            raise CorpusIndexError("name must be a non-empty string")
        _require_digest("source_record_sha256", self.source_record_sha256)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "name": self.name,
            "source_record_sha256": self.source_record_sha256,
        }

    @classmethod
    def from_wire(cls, value: object) -> RecordIndexEntry:
        if not isinstance(value, dict):
            raise CorpusIndexError("index record must be an object")
        expected_keys = {
            "oracle_id",
            "source_card_id",
            "name",
            "source_record_sha256",
        }
        actual_keys = set(value)
        if actual_keys != expected_keys:
            raise CorpusIndexError("index record has missing or unexpected fields")
        return cls(
            oracle_id=cast(str, value["oracle_id"]),
            source_card_id=cast(str, value["source_card_id"]),
            name=cast(str, value["name"]),
            source_record_sha256=cast(str, value["source_record_sha256"]),
        )


@dataclass(frozen=True, slots=True)
class ShardSummary:
    """Measured identity and count for one generated shard."""

    shard: str
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int


@dataclass(frozen=True, slots=True)
class IndexSummary:
    """Measured identity and counts for a complete 16-shard index."""

    shards: tuple[ShardSummary, ...]
    record_count: int
    unique_oracle_id_count: int
    duplicate_oracle_id_count: int
    aggregate_digest: str

    @property
    def total_byte_length(self) -> int:
        return sum(shard.byte_length for shard in self.shards)

    @property
    def shard_record_counts(self) -> dict[str, int]:
        return {shard.shard: shard.record_count for shard in self.shards}


def parse_source_record(raw_line: bytes, line_number: int) -> RecordIndexEntry:
    """Parse one raw decompressed JSONL line and hash its exact bytes."""

    if not raw_line.strip():
        raise CorpusIndexError(f"source record line {line_number} is blank")
    try:
        document = json.loads(raw_line)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CorpusIndexError(
            f"source record line {line_number} is invalid JSON"
        ) from error
    if not isinstance(document, dict):
        raise CorpusIndexError(f"source record line {line_number} must be an object")
    if document.get("object") != "card":
        raise CorpusIndexError(f"source record line {line_number} is not a card object")
    return RecordIndexEntry(
        oracle_id=cast(str, document.get("oracle_id")),
        source_card_id=cast(str, document.get("id")),
        name=cast(str, document.get("name")),
        source_record_sha256=sha256_bytes(raw_line),
    )


def iter_source_records(source_path: str | Path) -> Iterator[RecordIndexEntry]:
    """Yield compact entries while streaming gzip decompression one line at a time."""

    try:
        with gzip.open(source_path, "rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                yield parse_source_record(raw_line, line_number)
    except CorpusIndexError:
        raise
    except (EOFError, OSError) as error:
        raise CorpusIndexError(
            f"source gzip JSONL could not be read: {error}"
        ) from error


def _aggregate_index_digest(shards: tuple[ShardSummary, ...]) -> str:
    if tuple(shard.shard for shard in shards) != SHARD_NAMES:
        raise CorpusIndexError("aggregate index requires exactly 16 ordered shards")
    descriptor = [
        {
            "path": shard.relative_path,
            "sha256": shard.sha256,
            "byte_length": shard.byte_length,
            "record_count": shard.record_count,
        }
        for shard in shards
    ]
    return domain_digest(INDEX_DIGEST_DOMAIN, cast(JSONValue, descriptor))


def _index_summary(
    shards: tuple[ShardSummary, ...], unique_oracle_ids: int
) -> IndexSummary:
    record_count = sum(shard.record_count for shard in shards)
    return IndexSummary(
        shards=shards,
        record_count=record_count,
        unique_oracle_id_count=unique_oracle_ids,
        duplicate_oracle_id_count=0,
        aggregate_digest=_aggregate_index_digest(shards),
    )


def build_record_index(source_path: str | Path, output_dir: str | Path) -> IndexSummary:
    """Build a fresh deterministic index from one pinned gzip JSONL source."""

    entries: list[RecordIndexEntry] = []
    seen_oracle_ids: set[str] = set()
    for entry in iter_source_records(source_path):
        if entry.oracle_id in seen_oracle_ids:
            raise CorpusIndexError(f"duplicate oracle_id: {entry.oracle_id}")
        seen_oracle_ids.add(entry.oracle_id)
        entries.append(entry)
    entries.sort(key=lambda entry: entry.oracle_id)

    output_path = Path(output_dir)
    if output_path.exists() and not output_path.is_dir():
        raise CorpusIndexError("record index output is not a directory")
    output_path.mkdir(parents=True, exist_ok=True)
    if any(output_path.iterdir()):
        raise CorpusIndexError("record index output directory must be empty")

    with ExitStack() as stack:
        streams = {
            shard: stack.enter_context((output_path / f"{shard}.jsonl").open("wb"))
            for shard in SHARD_NAMES
        }
        for entry in entries:
            shard = entry.oracle_id[0]
            streams[shard].write(canonical_json_bytes(entry.to_wire()) + b"\n")
    return inspect_record_index(output_path)


def _read_shard(path: Path, shard: str, seen_oracle_ids: set[str]) -> ShardSummary:
    digest = hashlib.sha256()
    byte_length = 0
    record_count = 0
    previous_oracle_id: str | None = None
    with path.open("rb") as stream:
        while raw_line := stream.readline():
            digest.update(raw_line)
            byte_length += len(raw_line)
            if not raw_line.endswith(b"\n"):
                raise CorpusIndexError(f"shard {shard} record is missing final LF")
            try:
                document = json.loads(raw_line)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise CorpusIndexError(
                    f"shard {shard} contains invalid JSON"
                ) from error
            entry = RecordIndexEntry.from_wire(document)
            expected_bytes = canonical_json_bytes(entry.to_wire()) + b"\n"
            if raw_line != expected_bytes:
                raise CorpusIndexError(f"shard {shard} record is not canonical JSONL")
            if entry.oracle_id[0] != shard:
                raise CorpusIndexError(
                    f"record {entry.oracle_id} is in the wrong shard {shard}"
                )
            if previous_oracle_id is not None and entry.oracle_id <= previous_oracle_id:
                raise CorpusIndexError(
                    f"shard {shard} records are not strictly ordered"
                )
            if entry.oracle_id in seen_oracle_ids:
                raise CorpusIndexError(
                    f"duplicate oracle_id in index: {entry.oracle_id}"
                )
            previous_oracle_id = entry.oracle_id
            seen_oracle_ids.add(entry.oracle_id)
            record_count += 1
    return ShardSummary(
        shard=shard,
        relative_path=f"records/{shard}.jsonl",
        sha256=digest.hexdigest(),
        byte_length=byte_length,
        record_count=record_count,
    )


def inspect_record_index(output_dir: str | Path) -> IndexSummary:
    """Validate the complete generated shard set and return its identities."""

    output_path = Path(output_dir)
    if not output_path.is_dir():
        raise CorpusIndexError("record index directory does not exist")
    actual_names = {path.name for path in output_path.iterdir()}
    expected_names = {f"{shard}.jsonl" for shard in SHARD_NAMES}
    unexpected = sorted(actual_names - expected_names)
    if unexpected:
        raise CorpusIndexError(f"unexpected shard: {unexpected[0]}")
    missing = sorted(expected_names - actual_names)
    if missing:
        raise CorpusIndexError(f"missing shard: {missing[0]}")
    seen_oracle_ids: set[str] = set()
    shards = tuple(
        _read_shard(output_path / f"{shard}.jsonl", shard, seen_oracle_ids)
        for shard in SHARD_NAMES
    )
    return _index_summary(shards, len(seen_oracle_ids))
