"""Independent M3 shard and corpus-closure validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import canonical_json_bytes
from .manifest import SHARD_NAMES, AnalysisShardDescriptorV1, analysis_shard_for
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
            order_key = sort_key(value)
            if previous_key is not None and order_key <= previous_key:
                raise AnalysisClosureError(f"{path} is not strictly ordered")
            if key in seen_keys and kind == "records":
                raise AnalysisClosureError(
                    f"duplicate output source identity in {path}"
                )
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
    records_directory: str | Path,
    trace_directory: str | Path,
    expected_source_keys: list[tuple[str, str, str, str]]
    | tuple[tuple[str, str, str, str], ...],
) -> tuple[ShardReadResultV1, ShardReadResultV1]:
    records = inspect_record_shards(records_directory)
    traces = inspect_trace_shards(trace_directory)
    actual_keys = tuple(
        card_source_key(cast(CardAnalysisRecordV1, value).source)
        for value in records.values
    )
    validate_identity_set(expected_source_keys, actual_keys)
    actual_key_set = set(actual_keys)
    trace_keys = {
        cast(RequirementTraceEventV1, value).card_source_key for value in traces.values
    }
    if not trace_keys <= actual_key_set:
        raise AnalysisClosureError("trace contains an unknown source identity")
    return records, traces


__all__ = [
    "AnalysisClosureError",
    "ShardReadResultV1",
    "inspect_record_shards",
    "inspect_trace_shards",
    "validate_analysis_closure",
    "validate_identity_set",
]
