"""Single-process deterministic M3 reference-build orchestration."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple, cast

from ..canonical import canonical_json_bytes
from ..semantic.bundle import RequirementBundleV1
from ..semantic.evidence import SourceRecordRefV1
from ..semantic.model import RequirementV1
from ..structural.model import StructuralCardRecordV1
from .authority import (
    NegativeRequirementAuthorityRecordV1,
    load_negative_requirement_authority,
)
from .build_input import (
    load_reference_build_input,
    source_ref_for_record,
)
from .manifest import (
    SHARD_NAMES,
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    analysis_shard_for,
    record_identity_set_digest,
)
from .model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    NegativeReviewAuthorityRefV1,
    card_source_key,
)
from .patterns import PATTERN_REGISTRY_DIGEST_DOMAIN, EffectivePatternRegistryV1
from .producer import (
    CandidateProducerV1,
    ImmutableRegistrySnapshotV1,
    ProducerContextV1,
    ProducerContractError,
    ProducerDescriptorV1,
    ProducerExecutionError,
    ProducerFindingV1,
    ProducerResultStatusV1,
    RelationshipProposalV1,
    execute_producer,
    validate_producer_candidate,
)
from .reconcile import ReconciliationFailure, reconcile
from .registry import PRODUCER_REGISTRY_DIGEST_DOMAIN, ProducerRegistryV1
from .trace import RequirementTraceEventV1, TraceDispositionV1, trace_sort_key
from .validate import validate_analysis_closure

M3_BUILD_PROFILE = "census.m3-reference.v1"


class AnalysisBuildError(RuntimeError):
    """Raised when an authoritative M3 build must fail closed."""


class NegativeAuthorityInputV1(NamedTuple):
    path: str | Path
    reference: NegativeReviewAuthorityRefV1
    source: SourceRecordRefV1


class ReferenceBuildResultV1(NamedTuple):
    output_dir: Path
    source_lock_digest: str
    manifest: AnalysisManifestV1
    records: tuple[CardAnalysisRecordV1, ...]
    traces: tuple[RequirementTraceEventV1, ...]
    identity_set: tuple[tuple[str, str, str, str], ...]

    def record_for(self, source_key: tuple[str, str, str, str]) -> CardAnalysisRecordV1:
        return next(
            record
            for record in self.records
            if card_source_key(record.source) == source_key
        )


def _failure(code: str, detail: str = "") -> AnalysisBuildError:
    return AnalysisBuildError(code if not detail else f"{code}: {detail}")


def _bind_producers(
    registry: ProducerRegistryV1,
    implementations: Sequence[CandidateProducerV1],
) -> tuple[ProducerRegistryV1, tuple[CandidateProducerV1, ...]]:
    if not isinstance(registry, ProducerRegistryV1):
        raise _failure("PRODUCER_ADMISSION", "registry has the wrong type")
    try:
        active = registry.for_authoritative_run()
    except (TypeError, ValueError) as error:
        raise _failure("PRODUCER_ADMISSION", str(error)) from error
    values = tuple(implementations)
    descriptors = [producer.descriptor for producer in values]
    if any(not isinstance(item, ProducerDescriptorV1) for item in descriptors):
        raise _failure("PRODUCER_BINDING", "implementation has no descriptor")
    keys = [(item.producer_id, item.producer_version) for item in descriptors]
    if len(keys) != len(set(keys)):
        raise _failure("PRODUCER_BINDING", "duplicate implementation identity")
    by_key = dict(zip(keys, values, strict=True))
    expected = {
        (item.producer_id, item.producer_version): item for item in active.producers
    }
    if set(by_key) != set(expected):
        raise _failure("PRODUCER_BINDING", "registry and implementation sets differ")
    for key, descriptor in zip(keys, descriptors, strict=True):
        if descriptor != expected[key]:
            raise _failure("PRODUCER_BINDING", f"descriptor mismatch for {key[0]}")
    return active, tuple(
        by_key[(item.producer_id, item.producer_version)] for item in active.producers
    )


def _trace_events(
    record: StructuralCardRecordV1,
    descriptor: ProducerDescriptorV1,
    status: ProducerResultStatusV1,
    candidates: tuple[RequirementV1, ...],
    findings: tuple[ProducerFindingV1, ...],
    retained: set[str],
    disputed: set[str],
) -> list[RequirementTraceEventV1]:
    source_key = (
        card_source_key(candidates[0].source)
        if candidates
        else (
            StructuralCardRecordV1.SCHEMA,
            record.oracle_id,
            record.source_card_id,
            record.source_record_sha256,
        )
    )
    entries: list[tuple[str | None, TraceDispositionV1, ProducerFindingV1 | None]]
    if status is ProducerResultStatusV1.EMITTED:
        entries = [
            (
                candidate.requirement_id,
                TraceDispositionV1.CANDIDATE_RETAINED
                if candidate.requirement_id in retained
                else TraceDispositionV1.DISPUTED_IDENTITY_OMITTED
                if candidate.requirement_id in disputed
                else TraceDispositionV1.CANDIDATE_EMITTED,
                next(
                    (item for item in findings if item.candidate_index == ordinal),
                    None,
                ),
            )
            for ordinal, candidate in enumerate(candidates)
        ]
    else:
        entries = [
            (
                None,
                TraceDispositionV1.PRODUCER_NO_MATCH
                if status is ProducerResultStatusV1.NO_MATCH
                else TraceDispositionV1.PRODUCER_UNSUPPORTED_SHAPE,
                None,
            )
        ]
    return [
        RequirementTraceEventV1(
            source_key,
            descriptor.producer_id,
            descriptor.producer_version,
            None if finding is None else finding.pattern_id,
            None if finding is None else finding.pattern_version,
            None if finding is None else finding.pattern_digest,
            None if finding is None else finding.source_field,
            None if finding is None else finding.face_index,
            None if finding is None else finding.exact_fragment,
            None if finding is None else finding.clause_ordinal,
            None if finding is None else finding.parser_span,
            candidate_id,
            None,
            disposition,
        )
        for candidate_id, disposition, finding in entries
    ]


def _descriptor(
    path: Path, relative_path: str, record_count: int
) -> AnalysisShardDescriptorV1:
    raw = path.read_bytes()
    return AnalysisShardDescriptorV1(
        relative_path, hashlib.sha256(raw).hexdigest(), len(raw), record_count
    )


WireValue = CardAnalysisRecordV1 | RequirementTraceEventV1


def _write_shard(
    path: Path,
    relative_path: str,
    values: list[WireValue],
    key: Callable[[WireValue], tuple[str, ...]],
) -> AnalysisShardDescriptorV1:
    values.sort(key=key)
    path.write_bytes(
        b"".join(canonical_json_bytes(item.to_wire()) + b"\n" for item in values)
    )
    return _descriptor(path, relative_path, len(values))


def _write_shards(
    root: Path,
    records: tuple[CardAnalysisRecordV1, ...],
    traces: tuple[RequirementTraceEventV1, ...],
) -> tuple[
    tuple[AnalysisShardDescriptorV1, ...],
    tuple[AnalysisShardDescriptorV1, ...],
]:
    records_root, trace_root = root / "records", root / "trace"
    records_root.mkdir()
    trace_root.mkdir()
    record_values: dict[str, list[WireValue]] = {s: [] for s in SHARD_NAMES}
    trace_values: dict[str, list[WireValue]] = {s: [] for s in SHARD_NAMES}
    for record in records:
        record_values[analysis_shard_for(record.source.oracle_id)].append(record)
    for event in traces:
        trace_values[analysis_shard_for(event.card_source_key[1])].append(event)
    record_descriptors: list[AnalysisShardDescriptorV1] = []
    trace_descriptors: list[AnalysisShardDescriptorV1] = []
    for shard in SHARD_NAMES:
        record_path = records_root / f"{shard}.jsonl"
        record_descriptors.append(
            _write_shard(
                record_path,
                f"records/{shard}.jsonl",
                record_values[shard],
                lambda value: card_source_key(cast(CardAnalysisRecordV1, value).source),
            )
        )
        trace_path = trace_root / f"{shard}.jsonl"
        trace_descriptors.append(
            _write_shard(
                trace_path,
                f"trace/{shard}.jsonl",
                trace_values[shard],
                lambda value: trace_sort_key(cast(RequirementTraceEventV1, value)),
            )
        )
    return tuple(record_descriptors), tuple(trace_descriptors)


def build_reference_m3(
    structural_index: str | Path,
    producer_registry: ProducerRegistryV1,
    pattern_registry: EffectivePatternRegistryV1,
    output_dir: str | Path,
    negative_authority: object = None,
    *,
    producer_implementations: Sequence[CandidateProducerV1] = (),
    source_lock_path: str | Path | None = None,
) -> ReferenceBuildResultV1:
    """Build and atomically publish one closure-validated M3 artifact."""
    output_path = Path(output_dir)
    if output_path.exists():
        raise _failure("PUBLICATION_FAILURE", "output directory already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        structural = load_reference_build_input(structural_index, source_lock_path)
    except Exception as error:
        raise _failure("INVALID_M1_INPUT", str(error)) from error
    registry, producers = _bind_producers(producer_registry, producer_implementations)
    if not isinstance(pattern_registry, EffectivePatternRegistryV1):
        raise _failure("PATTERN_ADMISSION", "registry has the wrong type")
    try:
        pattern = EffectivePatternRegistryV1.from_wire(pattern_registry.to_wire())
        producer_snapshot = ImmutableRegistrySnapshotV1.from_wire(
            "producer",
            ProducerRegistryV1.SCHEMA,
            PRODUCER_REGISTRY_DIGEST_DOMAIN,
            registry.to_wire(),
        )
        pattern_snapshot = ImmutableRegistrySnapshotV1.from_wire(
            "pattern",
            EffectivePatternRegistryV1.SCHEMA,
            PATTERN_REGISTRY_DIGEST_DOMAIN,
            pattern.to_wire(),
        )
    except (TypeError, ValueError) as error:
        raise _failure("PATTERN_ADMISSION", str(error)) from error
    authority_record: NegativeRequirementAuthorityRecordV1 | None = None
    authority_key: tuple[str, str, str, str] | None = None
    authority_reference: NegativeReviewAuthorityRefV1 | None = None
    if negative_authority is not None:
        if not isinstance(negative_authority, NegativeAuthorityInputV1):
            raise _failure("INVALID_NEGATIVE_AUTHORITY", "input has the wrong type")
        authority_reference = negative_authority.reference
        if (
            negative_authority.source.source_lock_digest
            != structural.source_lock_digest
        ):
            raise _failure("INVALID_NEGATIVE_AUTHORITY", "source lock mismatch")
        authority_key = card_source_key(negative_authority.source)
        m1_keys = {
            card_source_key(source_ref_for_record(item, structural.source_lock_digest))
            for item in structural.records
        }
        if authority_key not in m1_keys:
            raise _failure("INVALID_NEGATIVE_AUTHORITY", "source is not in M1")
        try:
            authority_record = load_negative_requirement_authority(
                negative_authority.path,
                negative_authority.reference,
                negative_authority.source,
            )
        except Exception as error:
            raise _failure("INVALID_NEGATIVE_AUTHORITY", str(error)) from error
    context = ProducerContextV1(
        structural.source_lock_digest,
        RequirementV1.SCHEMA,
        RequirementBundleV1.SCHEMA,
        producer_snapshot,
        pattern_snapshot,
    )
    records: list[CardAnalysisRecordV1] = []
    traces: list[RequirementTraceEventV1] = []
    for item in structural.records:
        source = source_ref_for_record(item, structural.source_lock_digest)
        candidates: list[RequirementV1] = []
        relationships: list[RelationshipProposalV1] = []
        results: list[
            tuple[
                ProducerDescriptorV1,
                ProducerResultStatusV1,
                tuple[RequirementV1, ...],
                tuple[ProducerFindingV1, ...],
            ]
        ] = []
        unresolved = False
        for producer in producers:
            descriptor = producer.descriptor
            try:
                result = execute_producer(producer, item, context)
            except ProducerExecutionError as error:
                raise _failure("PRODUCER_EXCEPTION", descriptor.producer_id) from error
            except ProducerContractError as error:
                raise _failure(
                    "INVALID_PRODUCER_RESULT", descriptor.producer_id
                ) from error
            for candidate in result.candidates:
                try:
                    validate_producer_candidate(
                        candidate, item, structural.source_lock_digest
                    )
                except (TypeError, ValueError) as error:
                    raise _failure(
                        "INVALID_REQUIREMENT", descriptor.producer_id
                    ) from error
            candidates.extend(result.candidates)
            relationships.extend(result.relationship_proposals)
            unresolved |= result.status is ProducerResultStatusV1.UNSUPPORTED_SHAPE
            results.append(
                (descriptor, result.status, result.candidates, result.findings)
            )
        try:
            merged = reconcile(candidates, relationships)
        except ReconciliationFailure as error:
            raise _failure("RECONCILIATION_FAILURE", item.oracle_id) from error
        retained = {candidate.requirement_id for candidate in merged.requirements}
        disputed = {
            candidate.requirement_id for candidate in merged.disputed_candidates
        }
        for descriptor, status, result_candidates, result_findings in results:
            traces.extend(
                _trace_events(
                    item,
                    descriptor,
                    status,
                    result_candidates,
                    result_findings,
                    retained,
                    disputed,
                )
            )
        bundle = None
        if merged.requirements:
            try:
                bundle = RequirementBundleV1(
                    source, merged.requirements, merged.relationships
                )
            except (TypeError, ValueError) as error:
                raise _failure("RECONCILIATION_FAILURE", item.oracle_id) from error
        key = card_source_key(source)
        has_authority = authority_key == key and authority_record is not None
        conflict = has_authority and (
            bool(candidates) or unresolved or merged.outcome_is_unresolved
        )
        if has_authority and not conflict:
            outcome, basis, card_bundle = (
                AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE,
                cast(NegativeReviewAuthorityRefV1, authority_reference),
                None,
            )
        else:
            outcome = (
                AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
                if bundle is not None
                and not (
                    conflict
                    or unresolved
                    or merged.outcome_is_unresolved
                    or not candidates
                )
                else AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
            )
            basis, card_bundle = None, bundle
        try:
            records.append(CardAnalysisRecordV1(source, outcome, card_bundle, basis))
        except (TypeError, ValueError) as error:
            raise _failure("INVALID_ANALYSIS_RECORD", item.oracle_id) from error
    ordered_records = tuple(
        sorted(records, key=lambda item: card_source_key(item.source))
    )
    ordered_traces = tuple(sorted(traces, key=trace_sort_key))
    expected_keys = tuple(card_source_key(item.source) for item in ordered_records)
    manifest: AnalysisManifestV1
    reread_records: tuple[CardAnalysisRecordV1, ...]
    reread_traces: tuple[RequirementTraceEventV1, ...]
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output_path.name}-", dir=str(output_path.parent)
        ) as temp:
            staging = Path(temp)
            record_shards, trace_shards = _write_shards(
                staging, ordered_records, ordered_traces
            )
            manifest = AnalysisManifestV1(
                CardAnalysisRecordV1.SCHEMA,
                structural.source_lock_digest,
                StructuralCardRecordV1.SCHEMA,
                structural.manifest_sha256,
                structural.structural_index_aggregate_digest,
                RequirementV1.SCHEMA,
                RequirementBundleV1.SCHEMA,
                registry.digest(),
                pattern.digest(),
                M3_BUILD_PROFILE,
                len(ordered_records),
                record_identity_set_digest(expected_keys),
                record_shards,
                trace_shards,
            )
            (staging / "analysis-manifest.json").write_bytes(
                canonical_json_bytes(manifest.to_wire())
            )
            record_result, trace_result = validate_analysis_closure(
                structural.root, staging, structural.source_lock_path
            )
            reread_records = tuple(
                cast(CardAnalysisRecordV1, item) for item in record_result.values
            )
            reread_traces = tuple(
                cast(RequirementTraceEventV1, item) for item in trace_result.values
            )
            if (
                tuple(card_source_key(item.source) for item in reread_records)
                != expected_keys
            ):
                raise ValueError("reread identity order changed")
            os.replace(staging, output_path)
    except AnalysisBuildError:
        raise
    except Exception as error:
        raise _failure("PUBLICATION_FAILURE", str(error)) from error
    return ReferenceBuildResultV1(
        output_path,
        structural.source_lock_digest,
        manifest,
        reread_records,
        reread_traces,
        tuple(card_source_key(item.source) for item in reread_records),
    )


__all__ = [
    "AnalysisBuildError",
    "M3_BUILD_PROFILE",
    "NegativeAuthorityInputV1",
    "ReferenceBuildResultV1",
    "build_reference_m3",
]
