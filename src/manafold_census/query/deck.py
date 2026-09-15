"""Read-only deck parsing and analysis over the frozen Census query layer."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from ..analysis.model import AnalysisOutcomeV1
from ..capability.mapping import MappingDispositionV1
from ..capability.model import CapabilityRefV1
from ..digest import sha256_bytes
from ..semantic.model import ReviewStatusV1
from .cards import QueryNotFoundV1, SemanticStateV1
from .deck_models import (
    DECK_ANALYSIS_SCHEMA,
    MAX_DECK_QUANTITY,
    MAX_SECTION_CARD_COUNT,
    DeckAmbiguousNameV1,
    DeckCapabilityCountV1,
    DeckCardSummaryV1,
    DeckInputError,
    DeckInvalidLineV1,
    DeckInvalidReasonV1,
    DeckParsedEntryV1,
    DeckParseResultV1,
    DeckProvenanceTraceV1,
    DeckSectionV1,
    DeckUnknownNameV1,
)
from .deck_result import DeckAnalysisV1, DeckSectionAnalysisV1
from .details import (
    CardDetailViewV1,
    CardIdentityV1,
    CardNameResolutionStatusV1,
    CardNameResolutionV1,
)
from .provenance import MappingTraceV1, RequirementTraceV1

if TYPE_CHECKING:
    from .api import QueryMetadataV1


class DeckReader(Protocol):
    def metadata(self) -> QueryMetadataV1: ...

    def resolve_card_name(self, name: str) -> CardNameResolutionV1: ...

    def get_card(self, oracle_id: str) -> CardDetailViewV1 | QueryNotFoundV1: ...

    def trace_requirement(
        self, requirement_id: str
    ) -> RequirementTraceV1 | QueryNotFoundV1: ...

    def trace_mapping(self, link_id: str) -> MappingTraceV1 | QueryNotFoundV1: ...


def _invalid(
    invalid_lines: list[DeckInvalidLineV1],
    line_number: int,
    section: DeckSectionV1 | None,
    raw_line: str,
    reason: DeckInvalidReasonV1,
) -> None:
    invalid_lines.append(DeckInvalidLineV1(line_number, section, raw_line, reason))


def parse_deck_bytes(raw: bytes) -> DeckParseResultV1:
    """Parse strict deck grammar without performing card lookup."""

    if not isinstance(raw, bytes):
        raise TypeError("deck input must be bytes")
    payload = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise DeckInputError("deck input is not strict UTF-8") from error

    entries: list[DeckParsedEntryV1] = []
    invalid_lines: list[DeckInvalidLineV1] = []
    totals = {DeckSectionV1.MAIN: 0, DeckSectionV1.SIDEBOARD: 0}
    current: DeckSectionV1 | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "\ufeff" in line:
            _invalid(
                invalid_lines,
                line_number,
                current,
                line,
                DeckInvalidReasonV1.BOM_NOT_AT_FILE_START,
            )
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        lowered = stripped.casefold()
        if stripped.startswith("["):
            if lowered == "[main]":
                current = DeckSectionV1.MAIN
            elif lowered == "[sideboard]":
                current = DeckSectionV1.SIDEBOARD
            elif stripped.endswith("]"):
                _invalid(
                    invalid_lines,
                    line_number,
                    current,
                    line,
                    DeckInvalidReasonV1.UNKNOWN_SECTION,
                )
                current = None
            else:
                _invalid(
                    invalid_lines,
                    line_number,
                    current,
                    line,
                    DeckInvalidReasonV1.INVALID_SECTION,
                )
                current = None
            continue
        if current is None:
            _invalid(
                invalid_lines,
                line_number,
                None,
                line,
                DeckInvalidReasonV1.ENTRY_BEFORE_SECTION,
            )
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            _invalid(
                invalid_lines,
                line_number,
                current,
                line,
                DeckInvalidReasonV1.INVALID_ENTRY,
            )
            continue
        quantity_text, name = parts
        if re.fullmatch(r"[1-9][0-9]*", quantity_text) is None:
            _invalid(
                invalid_lines,
                line_number,
                current,
                line,
                DeckInvalidReasonV1.INVALID_QUANTITY,
            )
            continue
        quantity = int(quantity_text)
        if quantity > MAX_DECK_QUANTITY:
            _invalid(
                invalid_lines,
                line_number,
                current,
                line,
                DeckInvalidReasonV1.QUANTITY_LIMIT_EXCEEDED,
            )
            continue
        if totals[current] + quantity > MAX_SECTION_CARD_COUNT:
            _invalid(
                invalid_lines,
                line_number,
                current,
                line,
                DeckInvalidReasonV1.SECTION_CARD_LIMIT_EXCEEDED,
            )
            continue
        entries.append(DeckParsedEntryV1(line_number, current, quantity, name))
        totals[current] += quantity
    return DeckParseResultV1(tuple(entries), tuple(invalid_lines))


def _card_detail(reader: DeckReader, oracle_id: str) -> CardDetailViewV1:
    result = reader.get_card(oracle_id)
    if isinstance(result, QueryNotFoundV1):
        raise ValueError("resolved deck card is missing from the query bundle")
    return result


def _trace_for_card(
    reader: DeckReader, detail: CardDetailViewV1
) -> DeckProvenanceTraceV1:
    requirement_traces: list[RequirementTraceV1] = []
    mapping_traces: dict[str, MappingTraceV1] = {}
    for requirement_detail in detail.requirement_details:
        requirement_trace = reader.trace_requirement(requirement_detail.requirement_id)
        if isinstance(requirement_trace, QueryNotFoundV1):
            raise ValueError("deck Requirement trace is missing")
        requirement_traces.append(requirement_trace)
        for link_id in requirement_detail.mapping_decision.active_link_ids:
            mapping_trace = reader.trace_mapping(link_id)
            if isinstance(mapping_trace, QueryNotFoundV1):
                raise ValueError("deck mapping trace is missing")
            mapping_traces[link_id] = mapping_trace
    return DeckProvenanceTraceV1(
        CardIdentityV1.from_record(detail.structural_record),
        tuple(
            sorted(requirement_traces, key=lambda item: item.requirement.requirement_id)
        ),
        tuple(sorted(mapping_traces.values(), key=lambda item: item.link.link_id)),
    )


def _section_analysis(
    section: DeckSectionV1,
    entries: tuple[DeckParsedEntryV1, ...],
    invalid_lines: tuple[DeckInvalidLineV1, ...],
    reader: DeckReader,
) -> DeckSectionAnalysisV1:
    declared = sum(item.quantity for item in entries if item.section is section)
    unknown: list[DeckUnknownNameV1] = []
    ambiguous: list[DeckAmbiguousNameV1] = []
    aggregates: dict[str, tuple[int, CardDetailViewV1]] = {}
    for entry in entries:
        if entry.section is not section:
            continue
        resolution = reader.resolve_card_name(entry.name)
        if resolution.status is CardNameResolutionStatusV1.UNKNOWN:
            unknown.append(
                DeckUnknownNameV1(
                    entry.line_number,
                    section,
                    entry.quantity,
                    entry.name,
                    resolution.lookup_key,
                )
            )
        elif resolution.status is CardNameResolutionStatusV1.AMBIGUOUS:
            ambiguous.append(
                DeckAmbiguousNameV1(
                    entry.line_number,
                    section,
                    entry.quantity,
                    entry.name,
                    resolution.lookup_key,
                    resolution.matches,
                )
            )
        elif resolution.status is CardNameResolutionStatusV1.RESOLVED:
            if len(resolution.matches) != 1:
                raise ValueError("resolved name result must contain one identity")
            identity = resolution.matches[0]
            detail = _card_detail(reader, identity.oracle_id)
            previous = aggregates.get(identity.oracle_id)
            aggregates[identity.oracle_id] = (
                (entry.quantity if previous is None else previous[0] + entry.quantity),
                detail if previous is None else previous[1],
            )
        else:
            raise ValueError("unknown card name resolution status")

    details = tuple(
        sorted(
            aggregates.values(), key=lambda item: item[1].structural_record.oracle_id
        )
    )
    summaries = tuple(
        DeckCardSummaryV1(
            CardIdentityV1.from_record(detail.structural_record),
            quantity,
            detail.semantic_view.analysis_outcome,
            detail.semantic_view.semantic_state,
        )
        for quantity, detail in details
    )
    state_groups: dict[SemanticStateV1, list[DeckCardSummaryV1]] = {
        state: [] for state in SemanticStateV1
    }
    for summary in summaries:
        state_groups[summary.semantic_state].append(summary)

    outcome_counts = Counter(item.analysis_outcome.value for item in summaries)
    m2_values = [
        item.summary.review_status.value
        for _, detail in details
        for item in detail.requirement_details
    ]
    m4_values = [
        item.mapping_decision.disposition.value
        for _, detail in details
        for item in detail.requirement_details
    ]
    requirement_denominator = len(m2_values)

    capability_values: dict[CapabilityRefV1, tuple[str, set[str], int]] = {}
    for quantity, detail in details:
        oracle_id = detail.structural_record.oracle_id
        for capability in detail.capability_details:
            ref = capability.definition.capability_ref
            current = capability_values.get(ref)
            if current is None:
                capability_values[ref] = (
                    capability.definition.display_name,
                    {oracle_id},
                    quantity,
                )
            else:
                current[1].add(oracle_id)
                capability_values[ref] = (current[0], current[1], current[2] + quantity)

    capability_counts = tuple(
        DeckCapabilityCountV1(
            ref,
            values[0],
            len(values[1]),
            values[2],
        )
        for ref, values in sorted(
            capability_values.items(),
            key=lambda item: (
                item[0].capability_family_id,
                item[0].capability_version,
                item[0].claim_digest,
            ),
        )
    )
    traces = tuple(
        sorted(
            (_trace_for_card(reader, detail) for _, detail in details),
            key=lambda item: item.card.oracle_id,
        )
    )
    invalid_count = sum(item.section is section for item in invalid_lines)
    return DeckSectionAnalysisV1(
        section=section,
        declared_card_count=declared,
        resolved_card_count=sum(item.quantity for item in summaries),
        unique_resolved_oracle_identity_count=len(summaries),
        unknown_names=tuple(unknown),
        ambiguous_names=tuple(ambiguous),
        invalid_line_count=invalid_count,
        analysis_outcome_counts={
            item.value: outcome_counts[item.value] for item in AnalysisOutcomeV1
        },
        analysis_outcome_denominator=len(summaries),
        analysis_outcome_denominator_label="UNIQUE_RESOLVED_ORACLE_IDENTITIES",
        m2_review_status_counts={
            item.value: m2_values.count(item.value) for item in ReviewStatusV1
        },
        m2_review_status_denominator=requirement_denominator,
        m2_review_status_denominator_label=DeckSectionAnalysisV1._DISTRIBUTION_LABEL,
        m4_mapping_disposition_counts={
            item.value: m4_values.count(item.value) for item in MappingDispositionV1
        },
        m4_mapping_disposition_denominator=requirement_denominator,
        m4_mapping_disposition_denominator_label=DeckSectionAnalysisV1._DISTRIBUTION_LABEL,
        resolved_cards=summaries,
        established_cards=tuple(state_groups[SemanticStateV1.ESTABLISHED]),
        partially_established_cards=tuple(
            state_groups[SemanticStateV1.PARTIALLY_ESTABLISHED]
        ),
        unresolved_cards=tuple(state_groups[SemanticStateV1.UNRESOLVED_ANALYSIS]),
        explicit_negative_cards=tuple(
            state_groups[SemanticStateV1.NO_REQUIREMENTS_APPLICABLE]
        ),
        capability_counts=capability_counts,
        provenance_traces=traces,
    )


def analyze_deck_bytes(raw: bytes, reader: DeckReader) -> DeckAnalysisV1:
    """Parse and analyze one deck against one already validated Census reader."""

    parsed = parse_deck_bytes(raw)
    metadata = reader.metadata()
    return DeckAnalysisV1(
        deck_input_sha256=sha256_bytes(raw),
        census_release_id=metadata.census_release_id,
        census_manifest_sha256=metadata.census_manifest_sha256,
        source_lock_digest=metadata.source_lock_digest,
        m3_analysis_manifest_sha256=metadata.m3_analysis_manifest_sha256,
        m4_manifest_sha256=metadata.m4_manifest_sha256,
        main=_section_analysis(
            DeckSectionV1.MAIN, parsed.entries, parsed.invalid_lines, reader
        ),
        sideboard=_section_analysis(
            DeckSectionV1.SIDEBOARD, parsed.entries, parsed.invalid_lines, reader
        ),
        invalid_lines=parsed.invalid_lines,
    )


def analyze_deck_file(path: str | Path, reader: DeckReader) -> DeckAnalysisV1:
    """Read exact deck file bytes and analyze them without rewriting the input."""

    return analyze_deck_bytes(Path(path).read_bytes(), reader)


__all__ = [
    "DECK_ANALYSIS_SCHEMA",
    "DeckAmbiguousNameV1",
    "DeckAnalysisV1",
    "DeckCapabilityCountV1",
    "DeckCardSummaryV1",
    "DeckInputError",
    "DeckInvalidLineV1",
    "DeckInvalidReasonV1",
    "DeckParseResultV1",
    "DeckParsedEntryV1",
    "DeckProvenanceTraceV1",
    "DeckSectionAnalysisV1",
    "DeckSectionV1",
    "DeckUnknownNameV1",
    "analyze_deck_bytes",
    "analyze_deck_file",
    "parse_deck_bytes",
]
