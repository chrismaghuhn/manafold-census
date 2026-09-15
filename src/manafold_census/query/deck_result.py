"""Immutable M5-09 section and top-level result values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, cast

from ..analysis.model import AnalysisOutcomeV1
from ..canonical import JSONValue
from ..capability.mapping import MappingDispositionV1
from ..semantic.model import ReviewStatusV1
from ..semantic.primitives import _require_text
from .cards import SemanticStateV1
from .deck_models import (
    DECK_ANALYSIS_SCHEMA,
    DeckAmbiguousNameV1,
    DeckCapabilityCountV1,
    DeckCardSummaryV1,
    DeckInvalidLineV1,
    DeckProvenanceTraceV1,
    DeckSectionV1,
    DeckUnknownNameV1,
    _count,
    _digest,
    _enum_counts,
    _sorted_unique_lines,
)


def _capability_key(item: DeckCapabilityCountV1) -> tuple[str, int, str]:
    ref = item.capability
    return ref.capability_family_id, ref.capability_version, ref.claim_digest


def _card_ids(items: tuple[DeckCardSummaryV1, ...]) -> tuple[str, ...]:
    return tuple(item.identity.oracle_id for item in items)


@dataclass(frozen=True, slots=True)
class DeckSectionAnalysisV1:
    section: DeckSectionV1
    declared_card_count: int
    resolved_card_count: int
    unique_resolved_oracle_identity_count: int
    unknown_names: tuple[DeckUnknownNameV1, ...]
    ambiguous_names: tuple[DeckAmbiguousNameV1, ...]
    invalid_line_count: int
    analysis_outcome_counts: Mapping[str, int]
    analysis_outcome_denominator: int
    analysis_outcome_denominator_label: str
    m2_review_status_counts: Mapping[str, int]
    m2_review_status_denominator: int
    m2_review_status_denominator_label: str
    m4_mapping_disposition_counts: Mapping[str, int]
    m4_mapping_disposition_denominator: int
    m4_mapping_disposition_denominator_label: str
    resolved_cards: tuple[DeckCardSummaryV1, ...]
    established_cards: tuple[DeckCardSummaryV1, ...]
    partially_established_cards: tuple[DeckCardSummaryV1, ...]
    unresolved_cards: tuple[DeckCardSummaryV1, ...]
    explicit_negative_cards: tuple[DeckCardSummaryV1, ...]
    capability_counts: tuple[DeckCapabilityCountV1, ...]
    provenance_traces: tuple[DeckProvenanceTraceV1, ...]

    _DISTRIBUTION_LABEL: ClassVar[str] = "PERSISTED_REQUIREMENTS_ON_RESOLVED_CARDS"

    def __post_init__(self) -> None:
        section = DeckSectionV1(self.section)
        declared = _count("declared_card_count", self.declared_card_count)
        resolved_count = _count("resolved_card_count", self.resolved_card_count)
        unique_count = _count(
            "unique_resolved_oracle_identity_count",
            self.unique_resolved_oracle_identity_count,
        )
        invalid_count = _count("invalid_line_count", self.invalid_line_count)
        if resolved_count > declared:
            raise ValueError("resolved_card_count exceeds declared_card_count")
        object.__setattr__(self, "section", section)
        object.__setattr__(self, "declared_card_count", declared)
        object.__setattr__(self, "resolved_card_count", resolved_count)
        object.__setattr__(self, "unique_resolved_oracle_identity_count", unique_count)
        object.__setattr__(self, "invalid_line_count", invalid_count)

        unknown = tuple(self.unknown_names)
        ambiguous = tuple(self.ambiguous_names)
        if any(not isinstance(item, DeckUnknownNameV1) for item in unknown):
            raise TypeError("unknown_names must contain typed values")
        if any(not isinstance(item, DeckAmbiguousNameV1) for item in ambiguous):
            raise TypeError("ambiguous_names must contain typed values")
        if any(item.section is not section for item in unknown):
            raise ValueError("unknown names do not match section")
        if any(item.section is not section for item in ambiguous):
            raise ValueError("ambiguous names do not match section")
        object.__setattr__(
            self,
            "unknown_names",
            cast(
                tuple[DeckUnknownNameV1, ...],
                _sorted_unique_lines("unknown_names", unknown),
            ),
        )
        object.__setattr__(
            self,
            "ambiguous_names",
            cast(
                tuple[DeckAmbiguousNameV1, ...],
                _sorted_unique_lines("ambiguous_names", ambiguous),
            ),
        )

        resolved = tuple(self.resolved_cards)
        groups = (
            tuple(self.established_cards),
            tuple(self.partially_established_cards),
            tuple(self.unresolved_cards),
            tuple(self.explicit_negative_cards),
        )
        if any(
            not isinstance(item, DeckCardSummaryV1)
            for item in resolved + sum(groups, ())
        ):
            raise TypeError("card partitions must contain DeckCardSummaryV1 values")
        if tuple(item.identity.oracle_id for item in resolved) != tuple(
            sorted(item.identity.oracle_id for item in resolved)
        ):
            raise ValueError("resolved_cards must be sorted")
        resolved_ids = set(_card_ids(resolved))
        if len(resolved_ids) != len(resolved) or len(resolved_ids) != unique_count:
            raise ValueError("resolved_cards do not match unique identity count")
        if sum(item.quantity for item in resolved) != resolved_count:
            raise ValueError("resolved_cards do not match resolved count")
        expected_states = (
            SemanticStateV1.ESTABLISHED,
            SemanticStateV1.PARTIALLY_ESTABLISHED,
            SemanticStateV1.UNRESOLVED_ANALYSIS,
            SemanticStateV1.NO_REQUIREMENTS_APPLICABLE,
        )
        group_ids: set[str] = set()
        for values, expected in zip(groups, expected_states, strict=False):
            if tuple(item.identity.oracle_id for item in values) != tuple(
                sorted(item.identity.oracle_id for item in values)
            ):
                raise ValueError("card partitions must be sorted")
            if any(item.semantic_state is not expected for item in values):
                raise ValueError("card partition has the wrong SemanticState")
            expected_outcome = (
                AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
                if expected is SemanticStateV1.UNRESOLVED_ANALYSIS
                else AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE
                if expected is SemanticStateV1.NO_REQUIREMENTS_APPLICABLE
                else AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
            )
            if any(item.analysis_outcome is not expected_outcome for item in values):
                raise ValueError("card partition has the wrong analysis outcome")
            ids = set(_card_ids(values))
            if group_ids & ids or not ids <= resolved_ids:
                raise ValueError("card partitions overlap or contain unknown cards")
            group_ids.update(ids)
        if group_ids != resolved_ids:
            raise ValueError("card partitions do not cover resolved cards")
        object.__setattr__(self, "resolved_cards", resolved)
        object.__setattr__(self, "established_cards", groups[0])
        object.__setattr__(self, "partially_established_cards", groups[1])
        object.__setattr__(self, "unresolved_cards", groups[2])
        object.__setattr__(self, "explicit_negative_cards", groups[3])

        analysis_denominator = _count(
            "analysis_outcome_denominator", self.analysis_outcome_denominator
        )
        if analysis_denominator != unique_count:
            raise ValueError("analysis denominator does not match unique cards")
        object.__setattr__(
            self,
            "analysis_outcome_counts",
            _enum_counts(
                "analysis_outcome_counts",
                self.analysis_outcome_counts,
                AnalysisOutcomeV1,
                analysis_denominator,
            ),
        )
        if (
            self.analysis_outcome_denominator_label
            != "UNIQUE_RESOLVED_ORACLE_IDENTITIES"
        ):
            raise ValueError("analysis outcome denominator label is invalid")
        object.__setattr__(self, "analysis_outcome_denominator", analysis_denominator)

        m2_denominator = _count(
            "m2_review_status_denominator", self.m2_review_status_denominator
        )
        m4_denominator = _count(
            "m4_mapping_disposition_denominator",
            self.m4_mapping_disposition_denominator,
        )
        if m2_denominator != m4_denominator:
            raise ValueError("M2 and M4 denominators must match")
        for label, value in (
            (
                "m2_review_status_denominator_label",
                self.m2_review_status_denominator_label,
            ),
            (
                "m4_mapping_disposition_denominator_label",
                self.m4_mapping_disposition_denominator_label,
            ),
        ):
            if value != self._DISTRIBUTION_LABEL:
                raise ValueError(f"{label} is invalid")
        object.__setattr__(
            self,
            "m2_review_status_counts",
            _enum_counts(
                "m2_review_status_counts",
                self.m2_review_status_counts,
                ReviewStatusV1,
                m2_denominator,
            ),
        )
        object.__setattr__(
            self,
            "m4_mapping_disposition_counts",
            _enum_counts(
                "m4_mapping_disposition_counts",
                self.m4_mapping_disposition_counts,
                MappingDispositionV1,
                m4_denominator,
            ),
        )
        object.__setattr__(self, "m2_review_status_denominator", m2_denominator)
        object.__setattr__(self, "m4_mapping_disposition_denominator", m4_denominator)

        capabilities = tuple(self.capability_counts)
        if any(not isinstance(item, DeckCapabilityCountV1) for item in capabilities):
            raise TypeError("capability_counts must contain typed values")
        if tuple(_capability_key(item) for item in capabilities) != tuple(
            sorted(_capability_key(item) for item in capabilities)
        ):
            raise ValueError("capability_counts must be sorted")
        if len({_capability_key(item) for item in capabilities}) != len(capabilities):
            raise ValueError("capability_counts must be unique")
        object.__setattr__(self, "capability_counts", capabilities)

        traces = tuple(self.provenance_traces)
        if any(not isinstance(item, DeckProvenanceTraceV1) for item in traces):
            raise TypeError("provenance_traces must contain typed values")
        if tuple(item.card.oracle_id for item in traces) != tuple(
            sorted(item.card.oracle_id for item in traces)
        ):
            raise ValueError("provenance_traces must be sorted")
        if len({item.card.oracle_id for item in traces}) != len(traces):
            raise ValueError("provenance_traces must be unique")
        if {item.card.oracle_id for item in traces} != resolved_ids:
            raise ValueError("provenance traces must cover resolved cards")
        object.__setattr__(self, "provenance_traces", traces)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "section": self.section.value,
            "declared_card_count": self.declared_card_count,
            "resolved_card_count": self.resolved_card_count,
            "unique_resolved_oracle_identity_count": (
                self.unique_resolved_oracle_identity_count
            ),
            "unknown_names": [item.to_wire() for item in self.unknown_names],
            "ambiguous_names": [item.to_wire() for item in self.ambiguous_names],
            "invalid_line_count": self.invalid_line_count,
            "analysis_outcome_counts": dict(self.analysis_outcome_counts),
            "analysis_outcome_denominator": self.analysis_outcome_denominator,
            "analysis_outcome_denominator_label": (
                self.analysis_outcome_denominator_label
            ),
            "m2_review_status_counts": dict(self.m2_review_status_counts),
            "m2_review_status_denominator": self.m2_review_status_denominator,
            "m2_review_status_denominator_label": (
                self.m2_review_status_denominator_label
            ),
            "m4_mapping_disposition_counts": dict(self.m4_mapping_disposition_counts),
            "m4_mapping_disposition_denominator": (
                self.m4_mapping_disposition_denominator
            ),
            "m4_mapping_disposition_denominator_label": (
                self.m4_mapping_disposition_denominator_label
            ),
            "resolved_cards": [item.to_wire() for item in self.resolved_cards],
            "established_cards": [item.to_wire() for item in self.established_cards],
            "partially_established_cards": [
                item.to_wire() for item in self.partially_established_cards
            ],
            "unresolved_cards": [item.to_wire() for item in self.unresolved_cards],
            "explicit_negative_cards": [
                item.to_wire() for item in self.explicit_negative_cards
            ],
            "capability_counts": [item.to_wire() for item in self.capability_counts],
            "provenance_traces": [item.to_wire() for item in self.provenance_traces],
        }


@dataclass(frozen=True, slots=True)
class DeckAnalysisV1:
    deck_input_sha256: str
    census_release_id: str
    census_manifest_sha256: str
    source_lock_digest: str
    m3_analysis_manifest_sha256: str
    m4_manifest_sha256: str
    main: DeckSectionAnalysisV1
    sideboard: DeckSectionAnalysisV1
    invalid_lines: tuple[DeckInvalidLineV1, ...]

    SCHEMA: ClassVar[str] = DECK_ANALYSIS_SCHEMA

    def __post_init__(self) -> None:
        for field in (
            "deck_input_sha256",
            "census_manifest_sha256",
            "source_lock_digest",
            "m3_analysis_manifest_sha256",
            "m4_manifest_sha256",
        ):
            _digest(field, getattr(self, field))
        _require_text("census_release_id", self.census_release_id)
        if not isinstance(self.main, DeckSectionAnalysisV1):
            raise TypeError("main must be DeckSectionAnalysisV1")
        if not isinstance(self.sideboard, DeckSectionAnalysisV1):
            raise TypeError("sideboard must be DeckSectionAnalysisV1")
        if self.main.section is not DeckSectionV1.MAIN:
            raise ValueError("main section has the wrong section value")
        if self.sideboard.section is not DeckSectionV1.SIDEBOARD:
            raise ValueError("sideboard section has the wrong section value")
        invalid_lines = tuple(self.invalid_lines)
        if any(not isinstance(item, DeckInvalidLineV1) for item in invalid_lines):
            raise TypeError("invalid_lines must contain DeckInvalidLineV1 values")
        object.__setattr__(
            self,
            "invalid_lines",
            cast(
                tuple[DeckInvalidLineV1, ...],
                _sorted_unique_lines("invalid_lines", invalid_lines),
            ),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "deck_input_sha256": self.deck_input_sha256,
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "source_lock_digest": self.source_lock_digest,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "m4_manifest_sha256": self.m4_manifest_sha256,
            "main": self.main.to_wire(),
            "sideboard": self.sideboard.to_wire(),
            "invalid_lines": [item.to_wire() for item in self.invalid_lines],
        }
