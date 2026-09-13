"""Deterministic derived reports downstream of a validated M3 artifact."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Protocol, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import sha256_bytes
from ..semantic.evidence import (
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
)
from ..semantic.kinds import RequirementFamilyV1, RequirementKindV1
from ..semantic.model import (
    DerivationMethodV1,
    ResolutionReasonV1,
    ResolutionStateV1,
    ReviewStatusV1,
)
from ..validation import validate_document
from .manifest import AnalysisManifestV1
from .model import AnalysisOutcomeV1, CardAnalysisRecordV1
from .trace import RequirementTraceEventV1, TraceDispositionV1

REPORT_SCHEMA = "census.analysis-report.v1"
REPORT_INDEX_SCHEMA = "census.analysis-report-index.v1"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"


class ValidatedAnalysisRunV1(Protocol):
    manifest: AnalysisManifestV1
    records: tuple[CardAnalysisRecordV1, ...]
    traces: tuple[RequirementTraceEventV1, ...]


@dataclass(frozen=True, slots=True)
class ReuseSummaryV1:
    distinct_pattern_count: int
    matched_card_count: int
    matched_requirement_count: int
    pattern_count: int
    total_match_count: int
    reused_match_count: int

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "distinct_pattern_count": self.distinct_pattern_count,
            "matched_card_count": self.matched_card_count,
            "matched_requirement_count": self.matched_requirement_count,
            "pattern_count": self.pattern_count,
            "total_match_count": self.total_match_count,
            "reused_match_count": self.reused_match_count,
        }


@dataclass(frozen=True, slots=True)
class ReportDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
        }


@dataclass(frozen=True, slots=True)
class AnalysisReportV1:
    wire: dict[str, JSONValue]
    pattern_counts: tuple[dict[str, JSONValue], ...]
    reuse_summary: ReuseSummaryV1

    def to_wire(self) -> dict[str, JSONValue]:
        return self.wire


@dataclass(frozen=True, slots=True)
class ReportIndexV1:
    analysis_manifest_sha256: str
    report_descriptors: tuple[ReportDescriptorV1, ...]

    SCHEMA: ClassVar[str] = REPORT_INDEX_SCHEMA

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "report_index_schema": self.SCHEMA,
            "analysis_manifest_sha256": self.analysis_manifest_sha256,
            "report_descriptors": [
                descriptor.to_wire() for descriptor in self.report_descriptors
            ],
        }


@dataclass(frozen=True, slots=True)
class ReportBuildResultV1:
    report: AnalysisReportV1
    report_index: ReportIndexV1

    @property
    def analysis_manifest_sha256(self) -> str:
        return self.report_index.analysis_manifest_sha256

    @property
    def report_descriptors(self) -> tuple[ReportDescriptorV1, ...]:
        return self.report_index.report_descriptors

    @property
    def reuse_summary(self) -> ReuseSummaryV1:
        return self.report.reuse_summary

    def to_wire(self) -> dict[str, JSONValue]:
        return self.report_index.to_wire()


def _enum_counts(
    values: Sequence[str], enum_type: type[StrEnum]
) -> dict[str, JSONValue]:
    counter = Counter(values)
    return {member.value: counter[member.value] for member in enum_type}


def _pattern_key(pattern_id: str, pattern_version: str) -> str:
    return f"{pattern_id}@{pattern_version}"


def _requirement_is_face_sourced(requirement: object) -> bool:
    from ..semantic.model import RequirementV1

    if not isinstance(requirement, RequirementV1):
        return False
    return any(
        isinstance(evidence, StructuralFaceEvidenceV1)
        or isinstance(evidence, StructuralFieldEvidenceV1)
        and evidence.face_index is not None
        for evidence in requirement.evidence
    )


def _face_source_counts(requirements: Sequence[object]) -> dict[str, JSONValue]:
    return {
        "PARENT": sum(not _requirement_is_face_sourced(item) for item in requirements),
        "FACE": sum(_requirement_is_face_sourced(item) for item in requirements),
    }


def _multi_face_card_count(records: Sequence[CardAnalysisRecordV1]) -> int:
    return sum(
        record.bundle is not None
        and any(
            _requirement_is_face_sourced(item) for item in record.bundle.requirements
        )
        for record in records
    )


def _largest_unresolved_groups(
    records: Sequence[CardAnalysisRecordV1],
    traces: Sequence[RequirementTraceEventV1],
) -> list[dict[str, JSONValue]]:
    dispositions: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for event in traces:
        dispositions[event.card_source_key].add(event.disposition.value)
    groups: Counter[str] = Counter()
    for record in records:
        key = _unresolved_group_for(record, dispositions)
        if key is not None:
            groups[key] += 1
    return [
        {"group_key": key, "card_count": count}
        for key, count in sorted(groups.items(), key=lambda item: (-item[1], item[0]))
    ]


def _record_source_key(record: CardAnalysisRecordV1) -> tuple[str, str, str, str]:
    return (
        record.source.record_schema,
        record.source.oracle_id,
        record.source.source_card_id,
        record.source.source_record_sha256,
    )


def _unresolved_group_for(
    record: CardAnalysisRecordV1,
    dispositions: dict[tuple[str, str, str, str], set[str]],
) -> str | None:
    if record.outcome is not AnalysisOutcomeV1.UNRESOLVED_ANALYSIS:
        return None
    card_dispositions = dispositions.get(_record_source_key(record), set())
    if "DISPUTED_IDENTITY_OMITTED" in card_dispositions:
        return "DISPUTED_IDENTITY_OMITTED"
    if "PRODUCER_UNSUPPORTED_SHAPE" in card_dispositions:
        return "PRODUCER_UNSUPPORTED_SHAPE"
    if record.bundle is not None:
        return "NEGATIVE_AUTHORITY_CONFLICT"
    if "PRODUCER_NO_MATCH" in card_dispositions:
        return "PRODUCER_NO_MATCH"
    return "UNRESOLVED_ANALYSIS"


def _report_document(
    run: ValidatedAnalysisRunV1,
) -> tuple[dict[str, JSONValue], tuple[dict[str, JSONValue], ...], ReuseSummaryV1]:
    records = tuple(run.records)
    traces = tuple(run.traces)
    outcome_values = [record.outcome.value for record in records]
    requirements = [
        requirement
        for record in records
        if record.bundle is not None
        for requirement in record.bundle.requirements
    ]
    review_counts = _enum_counts(
        [requirement.review.status.value for requirement in requirements],
        ReviewStatusV1,
    )
    resolution_counts = _enum_counts(
        [requirement.resolution.state.value for requirement in requirements],
        ResolutionStateV1,
    )
    reason_counts = _enum_counts(
        [requirement.resolution.reason.value for requirement in requirements],
        ResolutionReasonV1,
    )
    derivation_counts = _enum_counts(
        [
            derivation.method.value
            for requirement in requirements
            for derivation in requirement.provenance.derivations
        ],
        DerivationMethodV1,
    )
    family_counts = _enum_counts(
        [requirement.family.value for requirement in requirements],
        RequirementFamilyV1,
    )
    kind_counts = _enum_counts(
        [requirement.kind.value for requirement in requirements],
        RequirementKindV1,
    )
    producer_stats: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    producer_unresolved: dict[tuple[str, str], set[tuple[str, str, str, str]]] = (
        defaultdict(set)
    )
    pattern_stats: dict[tuple[str, str, str], dict[str, object]] = {}
    trace_dispositions = Counter(event.disposition.value for event in traces)
    matched_cards: set[tuple[str, str, str, str]] = set()
    matched_requirements: set[tuple[tuple[str, str, str, str], str]] = set()
    card_dispositions: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for event in traces:
        card_dispositions[event.card_source_key].add(event.disposition.value)
    card_groups = {
        _record_source_key(record): _unresolved_group_for(record, card_dispositions)
        for record in records
    }
    for event in traces:
        producer_key = (event.producer_id, event.producer_version)
        disposition = event.disposition
        producer_stats[producer_key]["candidate_emitted_count"] += int(
            disposition
            in (
                TraceDispositionV1.CANDIDATE_EMITTED,
                TraceDispositionV1.CANDIDATE_RETAINED,
                TraceDispositionV1.DISPUTED_IDENTITY_OMITTED,
            )
        )
        producer_stats[producer_key]["candidate_retained_count"] += int(
            disposition is TraceDispositionV1.CANDIDATE_RETAINED
        )
        producer_stats[producer_key]["no_match_count"] += int(
            disposition is TraceDispositionV1.PRODUCER_NO_MATCH
        )
        producer_stats[producer_key]["unsupported_shape_count"] += int(
            disposition is TraceDispositionV1.PRODUCER_UNSUPPORTED_SHAPE
        )
        producer_stats[producer_key]["conflict_count"] += int(
            disposition is TraceDispositionV1.DISPUTED_IDENTITY_OMITTED
        )
        group = card_groups.get(event.card_source_key)
        if (
            group == "DISPUTED_IDENTITY_OMITTED"
            and disposition is TraceDispositionV1.DISPUTED_IDENTITY_OMITTED
        ) or (
            group == "PRODUCER_UNSUPPORTED_SHAPE"
            and disposition is TraceDispositionV1.PRODUCER_UNSUPPORTED_SHAPE
        ):
            producer_unresolved[producer_key].add(event.card_source_key)
        if group == "NEGATIVE_AUTHORITY_CONFLICT" and disposition in {
            TraceDispositionV1.CANDIDATE_EMITTED,
            TraceDispositionV1.CANDIDATE_RETAINED,
            TraceDispositionV1.DISPUTED_IDENTITY_OMITTED,
        }:
            producer_unresolved[producer_key].add(event.card_source_key)
            producer_stats[producer_key]["conflict_count"] += 1
        if event.pattern_id is None or event.candidate_requirement_id is None:
            continue
        matched_cards.add(event.card_source_key)
        matched_requirements.add(
            (event.card_source_key, event.candidate_requirement_id)
        )
        pattern_key = (
            event.pattern_id,
            event.pattern_version or "",
            event.pattern_digest or "",
        )
        entry = pattern_stats.setdefault(
            pattern_key,
            {
                "pattern_id": event.pattern_id,
                "pattern_version": event.pattern_version or "",
                "pattern_digest": event.pattern_digest or "",
                "match_count": 0,
                "card_keys": set(),
            },
        )
        entry["match_count"] = cast(int, entry["match_count"]) + 1
        cast(set[tuple[str, str, str, str]], entry["card_keys"]).add(
            event.card_source_key
        )
    producer_contributions = []
    for producer_key in sorted(producer_stats):
        counts = producer_stats[producer_key]
        producer_contributions.append(
            {
                "producer_id": producer_key[0],
                "producer_version": producer_key[1],
                "candidate_emitted_count": counts["candidate_emitted_count"],
                "candidate_retained_count": counts["candidate_retained_count"],
                "no_match_count": counts["no_match_count"],
                "unsupported_shape_count": counts["unsupported_shape_count"],
                "conflict_count": counts["conflict_count"],
                "unresolved_card_count": len(producer_unresolved[producer_key]),
            }
        )
    pattern_counts: list[dict[str, JSONValue]] = []
    single_card_patterns: list[str] = []
    outlier_patterns: list[str] = []
    reused_match_count = 0
    total_match_count = 0
    for pattern_key in sorted(pattern_stats):
        entry = pattern_stats[pattern_key]
        match_count = cast(int, entry["match_count"])
        card_count = len(cast(set[tuple[str, str, str, str]], entry["card_keys"]))
        reused = max(match_count - 1, 0)
        reused_match_count += reused
        total_match_count += match_count
        display_key = _pattern_key(pattern_key[0], pattern_key[1])
        if card_count == 1:
            single_card_patterns.append(display_key)
        if match_count == 1:
            outlier_patterns.append(display_key)
        pattern_counts.append(
            {
                "pattern_id": pattern_key[0],
                "pattern_version": pattern_key[1],
                "pattern_digest": pattern_key[2],
                "match_count": match_count,
                "card_count": card_count,
                "reused_match_count": reused,
            }
        )
    reuse_summary = ReuseSummaryV1(
        distinct_pattern_count=len(pattern_counts),
        matched_card_count=len(matched_cards),
        matched_requirement_count=len(matched_requirements),
        pattern_count=len(pattern_counts),
        total_match_count=total_match_count,
        reused_match_count=reused_match_count,
    )
    report: dict[str, JSONValue] = {
        "schema": REPORT_SCHEMA,
        "analysis_manifest_sha256": run.manifest.digest(),
        "record_count": len(records),
        "trace_event_count": len(traces),
        "cards_by_outcome": _enum_counts(outcome_values, AnalysisOutcomeV1),
        "cards_with_zero_retained_requirements": sum(
            record.bundle is None for record in records
        ),
        "requirements_by_review_status": review_counts,
        "requirements_by_resolution_state": resolution_counts,
        "requirements_by_resolution_reason": reason_counts,
        "requirements_by_derivation": derivation_counts,
        "requirements_by_family": family_counts,
        "requirements_by_kind": kind_counts,
        "producer_contributions": cast(JSONValue, producer_contributions),
        "trace_dispositions": {
            disposition.value: trace_dispositions[disposition.value]
            for disposition in TraceDispositionV1
        },
        "face_source_counts": _face_source_counts(requirements),
        "multi_face_card_count": _multi_face_card_count(records),
        "largest_unresolved_groups": cast(
            JSONValue, _largest_unresolved_groups(records, traces)
        ),
        "distinct_pattern_count": len(pattern_counts),
        "matched_card_count": len(matched_cards),
        "matched_requirement_count": len(matched_requirements),
        "pattern_counts": cast(JSONValue, pattern_counts),
        "single_card_patterns": cast(JSONValue, single_card_patterns),
        "outlier_patterns": cast(JSONValue, outlier_patterns),
        "reuse_summary": reuse_summary.to_wire(),
    }
    return report, tuple(pattern_counts), reuse_summary


def build_reports(
    validated_run: ValidatedAnalysisRunV1,
    output_dir: str | Path,
) -> ReportBuildResultV1:
    """Build canonical reports from a validated manifest, records, and trace."""
    if not isinstance(validated_run.manifest, AnalysisManifestV1):
        raise TypeError("validated_run must contain AnalysisManifestV1")
    output_path = Path(output_dir)
    manifest_path = output_path / "analysis-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("report output root must contain analysis-manifest.json")
    if (output_path / "report-index.json").exists():
        raise ValueError("report-index.json already exists")
    reports_path = output_path / "reports"
    if reports_path.exists() and any(reports_path.iterdir()):
        raise ValueError("reports directory must be empty")
    reports_path.mkdir(parents=True, exist_ok=True)
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    if manifest_sha256 != validated_run.manifest.digest():
        raise ValueError("validated manifest bytes do not match manifest model")
    document, pattern_counts, reuse_summary = _report_document(validated_run)
    validate_document(document, "analysis-report.v1.schema.json")
    report = AnalysisReportV1(document, pattern_counts, reuse_summary)
    report_path = reports_path / "analysis-report.json"
    report_bytes = canonical_json_bytes(report.to_wire())
    report_path.write_bytes(report_bytes)
    descriptor = ReportDescriptorV1(
        "reports/analysis-report.json",
        hashlib.sha256(report_bytes).hexdigest(),
        len(report_bytes),
    )
    report_index = ReportIndexV1(manifest_sha256, (descriptor,))
    validate_document(report_index.to_wire(), "analysis-report.v1.schema.json")
    (output_path / "report-index.json").write_bytes(
        canonical_json_bytes(report_index.to_wire())
    )
    return ReportBuildResultV1(report, report_index)


__all__ = [
    "AnalysisReportV1",
    "ReportBuildResultV1",
    "ReportDescriptorV1",
    "ReportIndexV1",
    "ReuseSummaryV1",
    "build_reports",
]
