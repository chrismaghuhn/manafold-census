from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from analysis_fixtures import bundle, structural_record

from manafold_census.analysis.manifest import (
    SHARD_NAMES,
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    analysis_shard_for,
    record_identity_set_digest,
)
from manafold_census.analysis.model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    NegativeReviewAuthorityRefV1,
    card_source_key,
)
from manafold_census.analysis.trace import (
    NegativeAuthorityTraceDispositionV1,
    NegativeAuthorityTraceEventV1,
    RequirementTraceEventV1,
    TraceDispositionV1,
    trace_sort_key,
)
from manafold_census.canonical import canonical_json_bytes
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceLock
from manafold_census.semantic.evidence import SourceRecordRefV1
from manafold_census.structural.index import (
    StructuralShardSummary,
    aggregate_structural_index_digest,
)
from manafold_census.structural.manifest import StructuralCardIndexManifestV1

REPOSITORY_ROOT = Path(__file__).parents[1]
SOURCE_LOCK_PATH = REPOSITORY_ROOT / "source-locks" / "scryfall-oracle-v1.json"
SOURCE_LOCK_DIGEST = SourceLock.from_wire(
    json.loads(SOURCE_LOCK_PATH.read_bytes())
).digest()
ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdeb"
SOURCE_RECORD_SHA256 = "b" * 64


def source_for(
    index: int = 0,
    *,
    source_lock_digest: str = SOURCE_LOCK_DIGEST,
) -> SourceRecordRefV1:
    if type(index) is not int or index < 0 or index > 15:
        raise ValueError("fixture source index must be between 0 and 15")
    suffix = format(index, "x")
    return SourceRecordRefV1(
        record_schema="census.structural-card.v1",
        source_lock_digest=source_lock_digest,
        oracle_id=(
            ORACLE_ID if index == 0 else f"abcdefab-abcd-4abc-8abc-abcdefabcde{suffix}"
        ),
        source_card_id=(
            SOURCE_CARD_ID
            if index == 0
            else f"abcdefab-abcd-4abc-8abc-abcdefabcdf{suffix}"
        ),
        source_record_sha256=(
            SOURCE_RECORD_SHA256 if index == 0 else (suffix * 64)[:64]
        ),
    )


def record_with_proposed_requirement(index: int = 0) -> CardAnalysisRecordV1:
    source = source_for(index)
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=bundle(source),
        no_requirements_basis=None,
    )


def record_with_requirement(index: int = 0) -> CardAnalysisRecordV1:
    return record_with_proposed_requirement(index)


def record_with_other_requirement(index: int = 1) -> CardAnalysisRecordV1:
    return record_with_proposed_requirement(index)


def unresolved_record_without_bundle(index: int = 1) -> CardAnalysisRecordV1:
    return CardAnalysisRecordV1(
        source=source_for(index),
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )


def unresolved_record_with_requirement(index: int = 1) -> CardAnalysisRecordV1:
    source = source_for(index)
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=bundle(source),
        no_requirements_basis=None,
    )


def record_with_wrong_source_lock(index: int = 0) -> CardAnalysisRecordV1:
    source = source_for(index, source_lock_digest="f" * 64)
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=bundle(source),
        no_requirements_basis=None,
    )


def no_requirements_applicable_record(index: int = 2) -> CardAnalysisRecordV1:
    source = source_for(index)
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE,
        bundle=None,
        no_requirements_basis=_negative_authority(),
    )


def _negative_authority() -> NegativeReviewAuthorityRefV1:
    return NegativeReviewAuthorityRefV1(
        authority_id="fixture-negative-authority",
        authority_version="1",
        record_id="nra_" + "a" * 64,
        record_sha256="b" * 64,
        scope_digest="c" * 64,
    )


def trace_for_requirement_outside_bundle(
    record: CardAnalysisRecordV1,
    requirement_id: str,
) -> RequirementTraceEventV1:
    return RequirementTraceEventV1(
        card_source_key=card_source_key(record.source),
        producer_id="fixture-producer",
        producer_version="1",
        pattern_id=None,
        pattern_version=None,
        pattern_digest=None,
        source_field=None,
        face_index=None,
        exact_fragment=None,
        clause_ordinal=None,
        parser_span=None,
        candidate_requirement_id=requirement_id,
        local_candidate_key="outside-bundle",
        disposition=TraceDispositionV1.CANDIDATE_EMITTED,
    )


def _structural_records(
    records: Sequence[CardAnalysisRecordV1],
) -> tuple:
    return tuple(
        sorted(
            (
                structural_record(
                    oracle_id=record.source.oracle_id,
                    source_card_id=record.source.source_card_id,
                    source_record_sha256=record.source.source_record_sha256,
                )
                for record in records
            ),
            key=lambda item: item.oracle_id,
        )
    )


def _write_m1(
    root: Path, records: Sequence[CardAnalysisRecordV1]
) -> tuple[Path, StructuralCardIndexManifestV1]:
    structural_root = root / "m1"
    records_root = structural_root / "records"
    records_root.mkdir(parents=True)
    structural = _structural_records(records)
    summaries: list[StructuralShardSummary] = []
    for shard in SHARD_NAMES:
        values = [
            record
            for record in structural
            if analysis_shard_for(record.oracle_id) == shard
        ]
        raw = b"".join(canonical_json_bytes(item.to_wire()) + b"\n" for item in values)
        path = records_root / f"{shard}.jsonl"
        path.write_bytes(raw)
        summaries.append(
            StructuralShardSummary(
                shard=shard,
                relative_path=f"records/{shard}.jsonl",
                sha256=sha256_bytes(raw),
                byte_length=len(raw),
                record_count=len(values),
            )
        )
    manifest = StructuralCardIndexManifestV1(
        tuple(summaries), aggregate_structural_index_digest(tuple(summaries))
    )
    (structural_root / "structural-index-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )
    return structural_root, manifest


def _descriptor(
    path: Path, relative_path: str, record_count: int
) -> AnalysisShardDescriptorV1:
    raw = path.read_bytes()
    return AnalysisShardDescriptorV1(
        relative_path=relative_path,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        record_count=record_count,
    )


def write_synthetic_m3(
    root: Path,
    *,
    records: Sequence[CardAnalysisRecordV1],
    extra_traces: Sequence[RequirementTraceEventV1] = (),
):
    structural_root, structural_manifest = _write_m1(root, records)
    analysis_root = root / "m3"
    records_root = analysis_root / "records"
    trace_root = analysis_root / "trace"
    records_root.mkdir(parents=True)
    trace_root.mkdir()
    traces: list[RequirementTraceEventV1 | NegativeAuthorityTraceEventV1] = list(
        extra_traces
    )
    for record in records:
        if (
            record.outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE
            and record.no_requirements_basis is not None
        ):
            traces.append(
                NegativeAuthorityTraceEventV1(
                    card_source_key=card_source_key(record.source),
                    authority=record.no_requirements_basis,
                    disposition=NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_APPLIED,
                )
            )
    record_values: dict[str, list[CardAnalysisRecordV1]] = {
        shard: [] for shard in SHARD_NAMES
    }
    trace_values: dict[
        str, list[RequirementTraceEventV1 | NegativeAuthorityTraceEventV1]
    ] = {shard: [] for shard in SHARD_NAMES}
    for record in records:
        record_values[analysis_shard_for(record.source.oracle_id)].append(record)
    for trace in traces:
        trace_values[analysis_shard_for(trace.card_source_key[1])].append(trace)
    record_shards: list[AnalysisShardDescriptorV1] = []
    trace_shards: list[AnalysisShardDescriptorV1] = []
    for shard in SHARD_NAMES:
        record_values[shard].sort(key=lambda item: card_source_key(item.source))
        record_path = records_root / f"{shard}.jsonl"
        record_path.write_bytes(
            b"".join(
                canonical_json_bytes(item.to_wire()) + b"\n"
                for item in record_values[shard]
            )
        )
        record_shards.append(
            _descriptor(
                record_path,
                f"records/{shard}.jsonl",
                len(record_values[shard]),
            )
        )
        trace_values[shard].sort(key=trace_sort_key)
        trace_path = trace_root / f"{shard}.jsonl"
        trace_path.write_bytes(
            b"".join(
                canonical_json_bytes(item.to_wire()) + b"\n"
                for item in trace_values[shard]
            )
        )
        trace_shards.append(
            _descriptor(
                trace_path,
                f"trace/{shard}.jsonl",
                len(trace_values[shard]),
            )
        )
    manifest = AnalysisManifestV1(
        analysis_schema="census.card-analysis.v1",
        source_lock_digest=SOURCE_LOCK_DIGEST,
        structural_record_schema="census.structural-card.v1",
        structural_index_manifest_sha256=sha256_bytes(
            (structural_root / "structural-index-manifest.json").read_bytes()
        ),
        structural_index_aggregate_digest=structural_manifest.aggregate_digest,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry_digest="d" * 64,
        pattern_registry_digest="e" * 64,
        build_profile="census.m4-test.v1",
        record_count=len(records),
        record_identity_set_digest=record_identity_set_digest(
            [card_source_key(record.source) for record in records]
        ),
        record_shards=tuple(record_shards),
        trace_shards=tuple(trace_shards),
    )
    manifest_path = analysis_root / "analysis-manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest.to_wire()))
    from manafold_census.capability.input import FrozenM3InputV1

    return FrozenM3InputV1(
        structural_output_directory=structural_root,
        analysis_output_directory=analysis_root,
        source_lock_path=SOURCE_LOCK_PATH,
        expected_analysis_manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
    )
