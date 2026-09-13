"""Independent M3 shard and corpus-closure validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import canonical_json_bytes
from ..digest import sha256_bytes
from ..models import SourceLock
from ..structural.index import (
    SHARD_NAMES as STRUCTURAL_SHARD_NAMES,
)
from ..structural.index import (
    StructuralShardSummary,
    aggregate_structural_index_digest,
)
from ..structural.manifest import StructuralCardIndexManifestV1
from ..structural.model import StructuralCardRecordV1
from ..validation import validate_document
from .manifest import (
    SHARD_NAMES,
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    analysis_shard_for,
)
from .model import CardAnalysisRecordV1, card_source_key
from .trace import RequirementTraceEventV1, trace_sort_key


class AnalysisClosureError(ValueError):
    """Raised when M3 output cannot prove exact source/output closure."""


@dataclass(frozen=True, slots=True)
class ShardReadResultV1:
    descriptors: tuple[AnalysisShardDescriptorV1, ...]
    values: tuple[object, ...]


def validate_identity_set(
    expected: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
    actual: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
) -> None:
    expected_set = set(expected)
    actual_set = set(actual)
    if len(actual) != len(actual_set):
        raise AnalysisClosureError("duplicate output source identity")
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    if missing or extra:
        raise AnalysisClosureError(
            f"identity set mismatch: missing={len(missing)} extra={len(extra)}"
        )


def _expected_shard_paths(directory: Path, kind: str) -> set[str]:
    return {f"{kind}/{shard}.jsonl" for shard in SHARD_NAMES}


def _read_canonical_object(path: Path) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisClosureError(f"{path} is not valid JSON") from error
    if not isinstance(document, dict):
        raise AnalysisClosureError(f"{path} must contain an object")
    if raw != canonical_json_bytes(document):
        raise AnalysisClosureError(f"{path} is not canonical JSON")
    return cast(dict[str, object], document)


def _read_m1_authority(
    structural_output_directory: str | Path,
) -> tuple[StructuralCardIndexManifestV1, tuple[tuple[str, str, str, str], ...], str]:
    root = Path(structural_output_directory)
    manifest_path = root / "structural-index-manifest.json"
    try:
        document = _read_canonical_object(manifest_path)
        validate_document(document, "structural-card-index-manifest.v1.schema.json")
        persisted = StructuralCardIndexManifestV1.from_wire(document)
    except (OSError, TypeError, ValueError) as error:
        raise AnalysisClosureError("structural index manifest is invalid") from error

    records_root = root / "records"
    if not records_root.is_dir():
        raise AnalysisClosureError("M1 structural records directory is missing")
    summaries: list[StructuralShardSummary] = []
    records: list[StructuralCardRecordV1] = []
    seen_oracle_ids: set[str] = set()
    for shard in STRUCTURAL_SHARD_NAMES:
        path = records_root / f"{shard}.jsonl"
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        previous_oracle_id: str | None = None
        count = 0
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise AnalysisClosureError(f"{path} is missing final LF")
            try:
                record = StructuralCardRecordV1.from_wire(json.loads(line))
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as error:
                raise AnalysisClosureError(
                    f"{path} contains an invalid M1 record"
                ) from error
            if line != canonical_json_bytes(record.to_wire()) + b"\n":
                raise AnalysisClosureError(f"{path} contains noncanonical JSONL")
            if analysis_shard_for(record.oracle_id) != shard:
                raise AnalysisClosureError(
                    f"{path} contains a record in the wrong shard"
                )
            if (
                previous_oracle_id is not None
                and record.oracle_id <= previous_oracle_id
            ):
                raise AnalysisClosureError(f"{path} is not strictly ordered")
            if record.oracle_id in seen_oracle_ids:
                raise AnalysisClosureError("duplicate M1 oracle_id")
            seen_oracle_ids.add(record.oracle_id)
            previous_oracle_id = record.oracle_id
            records.append(record)
            count += 1
        summaries.append(
            StructuralShardSummary(
                shard=shard,
                relative_path=f"records/{shard}.jsonl",
                sha256=digest,
                byte_length=len(raw),
                record_count=count,
            )
        )
    actual = StructuralCardIndexManifestV1(
        tuple(summaries),
        aggregate_structural_index_digest(tuple(summaries)),
    )
    if actual != persisted:
        raise AnalysisClosureError("structural index manifest does not match records")
    keys = tuple(
        (
            StructuralCardRecordV1.SCHEMA,
            record.oracle_id,
            record.source_card_id,
            record.source_record_sha256,
        )
        for record in sorted(records, key=lambda item: item.oracle_id)
    )
    return persisted, keys, sha256_bytes(manifest_path.read_bytes())


def _read_source_lock(path: str | Path) -> SourceLock:
    try:
        document = _read_canonical_object(Path(path))
        validate_document(document, "source-lock.v1.schema.json")
        return SourceLock.from_wire(document)
    except (OSError, TypeError, ValueError) as error:
        raise AnalysisClosureError("source lock is invalid") from error


def _read_jsonl_shards(
    directory: str | Path,
    *,
    kind: str,
    parser: Callable[[object], object],
    sort_key: Callable[[object], tuple[str, ...]],
) -> ShardReadResultV1:
    root = Path(directory)
    if not root.is_dir():
        raise AnalysisClosureError(f"{kind} shard directory does not exist")
    actual = {f"{kind}/{path.name}" for path in root.glob("*.jsonl")}
    expected = _expected_shard_paths(root, kind)
    unexpected = actual - expected
    missing = expected - actual
    if unexpected:
        raise AnalysisClosureError(f"unexpected {kind} shard: {sorted(unexpected)[0]}")
    if missing:
        raise AnalysisClosureError(f"missing {kind} shard: {sorted(missing)[0]}")

    descriptors: list[AnalysisShardDescriptorV1] = []
    values: list[object] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for shard in SHARD_NAMES:
        path = root / f"{shard}.jsonl"
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        previous_key = None
        count = 0
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise AnalysisClosureError(f"{path} is missing final LF")
            try:
                document = json.loads(line)
                value = parser(document)
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as error:
                raise AnalysisClosureError(
                    f"{path} contains an invalid record"
                ) from error
            parsed_value = cast(
                CardAnalysisRecordV1 | RequirementTraceEventV1,
                value,
            )
            if line != canonical_json_bytes(parsed_value.to_wire()) + b"\n":
                raise AnalysisClosureError(f"{path} contains noncanonical JSONL")
            if kind == "records":
                record = cast(CardAnalysisRecordV1, value)
                key = card_source_key(record.source)
                if analysis_shard_for(record.source.oracle_id) != shard:
                    raise AnalysisClosureError(
                        f"{path} contains a record in the wrong shard"
                    )
            else:
                trace = cast(RequirementTraceEventV1, value)
                key = trace.card_source_key
                if analysis_shard_for(key[1]) != shard:
                    raise AnalysisClosureError(
                        f"{path} contains a trace in the wrong shard"
                    )
            if key in seen_keys and kind == "records":
                raise AnalysisClosureError(
                    f"duplicate output source identity in {path}"
                )
            order_key = sort_key(value)
            if previous_key is not None and order_key <= previous_key:
                raise AnalysisClosureError(f"{path} is not strictly ordered")
            seen_keys.add(key)
            previous_key = order_key
            values.append(value)
            count += 1
        descriptors.append(
            AnalysisShardDescriptorV1(
                relative_path=f"{kind}/{shard}.jsonl",
                sha256=digest,
                byte_length=len(raw),
                record_count=count,
            )
        )
    return ShardReadResultV1(tuple(descriptors), tuple(values))


def inspect_record_shards(directory: str | Path) -> ShardReadResultV1:
    def record_key(value: object) -> tuple[str, ...]:
        record = cast(CardAnalysisRecordV1, value)
        return card_source_key(record.source)

    return _read_jsonl_shards(
        directory,
        kind="records",
        parser=CardAnalysisRecordV1.from_wire,
        sort_key=record_key,
    )


def inspect_trace_shards(directory: str | Path) -> ShardReadResultV1:
    def trace_key(value: object) -> tuple[str, ...]:
        return trace_sort_key(cast(RequirementTraceEventV1, value))

    return _read_jsonl_shards(
        directory,
        kind="trace",
        parser=RequirementTraceEventV1.from_wire,
        sort_key=trace_key,
    )


def validate_analysis_closure(
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    source_lock_path: str | Path,
) -> tuple[ShardReadResultV1, ShardReadResultV1]:
    structural_manifest, expected_keys, structural_manifest_sha256 = _read_m1_authority(
        structural_output_directory
    )
    source_lock = _read_source_lock(source_lock_path)
    analysis_root = Path(analysis_output_directory)
    try:
        manifest_document = _read_canonical_object(
            analysis_root / "analysis-manifest.json"
        )
        validate_document(manifest_document, "analysis-manifest.v1.schema.json")
        manifest = AnalysisManifestV1.from_wire(manifest_document)
    except (OSError, TypeError, ValueError) as error:
        raise AnalysisClosureError("analysis manifest is invalid") from error

    records = inspect_record_shards(analysis_root / "records")
    traces = inspect_trace_shards(analysis_root / "trace")
    actual_keys = tuple(
        card_source_key(cast(CardAnalysisRecordV1, value).source)
        for value in records.values
    )
    validate_identity_set(expected_keys, actual_keys)
    actual_key_set = set(actual_keys)
    trace_keys = {
        cast(RequirementTraceEventV1, value).card_source_key for value in traces.values
    }
    if not trace_keys <= actual_key_set:
        raise AnalysisClosureError("trace contains an unknown source identity")
    if manifest.source_lock_digest != source_lock.digest():
        raise AnalysisClosureError("analysis source lock digest mismatch")
    if manifest.structural_index_manifest_sha256 != structural_manifest_sha256:
        raise AnalysisClosureError("analysis structural manifest digest mismatch")
    if (
        manifest.structural_index_aggregate_digest
        != structural_manifest.aggregate_digest
    ):
        raise AnalysisClosureError("analysis structural aggregate digest mismatch")
    if manifest.record_count != len(expected_keys):
        raise AnalysisClosureError("analysis manifest record count mismatch")
    from .manifest import record_identity_set_digest

    if manifest.record_identity_set_digest != record_identity_set_digest(expected_keys):
        raise AnalysisClosureError("analysis manifest identity digest mismatch")
    if manifest.record_shards != records.descriptors:
        raise AnalysisClosureError(
            "analysis manifest record shard descriptors mismatch"
        )
    if manifest.trace_shards != traces.descriptors:
        raise AnalysisClosureError("analysis manifest trace shard descriptors mismatch")
    return records, traces


__all__ = [
    "AnalysisClosureError",
    "ShardReadResultV1",
    "inspect_record_shards",
    "inspect_trace_shards",
    "validate_analysis_closure",
    "validate_identity_set",
]
