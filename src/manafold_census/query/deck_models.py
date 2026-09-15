"""Immutable M5-09 parser and deck-result atoms."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from ..analysis.model import AnalysisOutcomeV1
from ..canonical import JSONValue
from ..capability.model import CapabilityRefV1
from ..semantic.primitives import _require_int, _require_text
from .cards import SemanticStateV1
from .details import CardIdentityV1
from .provenance import MappingTraceV1, RequirementTraceV1

MAX_DECK_QUANTITY = 1_000_000
MAX_SECTION_CARD_COUNT = 1_000_000
DECK_ANALYSIS_SCHEMA = "census.deck-analysis.v1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class DeckInputError(ValueError):
    """Raised when deck bytes cannot be decoded under the strict input contract."""


class DeckSectionV1(StrEnum):
    MAIN = "main"
    SIDEBOARD = "sideboard"


class DeckInvalidReasonV1(StrEnum):
    UNKNOWN_SECTION = "UNKNOWN_SECTION"
    INVALID_SECTION = "INVALID_SECTION"
    ENTRY_BEFORE_SECTION = "ENTRY_BEFORE_SECTION"
    INVALID_ENTRY = "INVALID_ENTRY"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    QUANTITY_LIMIT_EXCEEDED = "QUANTITY_LIMIT_EXCEEDED"
    SECTION_CARD_LIMIT_EXCEEDED = "SECTION_CARD_LIMIT_EXCEEDED"
    BOM_NOT_AT_FILE_START = "BOM_NOT_AT_FILE_START"


def _count(field: str, value: object) -> int:
    return _require_int(field, value, nonnegative=True)


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _enum_counts(
    field: str,
    value: Mapping[str, int],
    enum_type: type[StrEnum],
    denominator: int,
) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    expected = tuple(item.value for item in enum_type)
    if set(value) != set(expected):
        raise ValueError(f"{field} must contain exactly the closed enum values")
    result = MappingProxyType(
        {key: _count(f"{field}.{key}", value[key]) for key in expected}
    )
    if sum(result.values()) != denominator:
        raise ValueError(f"{field} does not match its denominator")
    return result


def _sorted_unique_lines(
    field: str,
    values: tuple[DeckInvalidLineV1, ...]
    | tuple[DeckUnknownNameV1, ...]
    | tuple[DeckAmbiguousNameV1, ...],
) -> (
    tuple[DeckInvalidLineV1, ...]
    | tuple[DeckUnknownNameV1, ...]
    | tuple[DeckAmbiguousNameV1, ...]
):
    if tuple(item.line_number for item in values) != tuple(
        sorted(item.line_number for item in values)
    ):
        raise ValueError(f"{field} must be sorted by line number")
    if len({item.line_number for item in values}) != len(values):
        raise ValueError(f"{field} must contain unique line numbers")
    return values


@dataclass(frozen=True, slots=True)
class DeckParsedEntryV1:
    line_number: int
    section: DeckSectionV1
    quantity: int
    name: str

    def __post_init__(self) -> None:
        section = DeckSectionV1(self.section)
        line_number = _require_int("line_number", self.line_number)
        if line_number < 1:
            raise ValueError("line_number must be positive")
        quantity = _count("quantity", self.quantity)
        if not 1 <= quantity <= MAX_DECK_QUANTITY:
            raise ValueError("quantity is outside the deck line limit")
        name = _require_text("name", self.name)
        object.__setattr__(self, "section", section)
        object.__setattr__(self, "line_number", line_number)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class DeckInvalidLineV1:
    line_number: int
    section: DeckSectionV1 | None
    raw_line: str
    reason: DeckInvalidReasonV1

    def __post_init__(self) -> None:
        line_number = _require_int("line_number", self.line_number)
        if line_number < 1:
            raise ValueError("line_number must be positive")
        section = None if self.section is None else DeckSectionV1(self.section)
        raw_line = _require_text("raw_line", self.raw_line)
        reason = DeckInvalidReasonV1(self.reason)
        object.__setattr__(self, "line_number", line_number)
        object.__setattr__(self, "section", section)
        object.__setattr__(self, "raw_line", raw_line)
        object.__setattr__(self, "reason", reason)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "line_number": self.line_number,
            "section": None if self.section is None else self.section.value,
            "raw_line": self.raw_line,
            "reason": self.reason.value,
        }


@dataclass(frozen=True, slots=True)
class DeckParseResultV1:
    entries: tuple[DeckParsedEntryV1, ...]
    invalid_lines: tuple[DeckInvalidLineV1, ...]

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        invalid_lines = tuple(self.invalid_lines)
        if any(not isinstance(item, DeckParsedEntryV1) for item in entries):
            raise TypeError("entries must contain DeckParsedEntryV1 values")
        if any(not isinstance(item, DeckInvalidLineV1) for item in invalid_lines):
            raise TypeError("invalid_lines must contain DeckInvalidLineV1 values")
        if tuple(item.line_number for item in entries) != tuple(
            sorted(item.line_number for item in entries)
        ) or len({item.line_number for item in entries}) != len(entries):
            raise ValueError("entries must be sorted and unique by line number")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self,
            "invalid_lines",
            cast(
                tuple[DeckInvalidLineV1, ...],
                _sorted_unique_lines("invalid_lines", invalid_lines),
            ),
        )


@dataclass(frozen=True, slots=True)
class DeckUnknownNameV1:
    line_number: int
    section: DeckSectionV1
    quantity: int
    name: str
    lookup_key: str

    def __post_init__(self) -> None:
        line_number = _require_int("line_number", self.line_number)
        if line_number < 1:
            raise ValueError("line_number must be positive")
        object.__setattr__(self, "section", DeckSectionV1(self.section))
        quantity = _count("quantity", self.quantity)
        if not 1 <= quantity <= MAX_DECK_QUANTITY:
            raise ValueError("quantity is outside the deck line limit")
        object.__setattr__(self, "line_number", line_number)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "name", _require_text("name", self.name))
        object.__setattr__(
            self, "lookup_key", _require_text("lookup_key", self.lookup_key)
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "line_number": self.line_number,
            "section": self.section.value,
            "quantity": self.quantity,
            "name": self.name,
            "lookup_key": self.lookup_key,
        }


@dataclass(frozen=True, slots=True)
class DeckAmbiguousNameV1:
    line_number: int
    section: DeckSectionV1
    quantity: int
    name: str
    lookup_key: str
    matches: tuple[CardIdentityV1, ...]

    def __post_init__(self) -> None:
        line_number = _require_int("line_number", self.line_number)
        if line_number < 1:
            raise ValueError("line_number must be positive")
        object.__setattr__(self, "section", DeckSectionV1(self.section))
        quantity = _count("quantity", self.quantity)
        if not 1 <= quantity <= MAX_DECK_QUANTITY:
            raise ValueError("quantity is outside the deck line limit")
        object.__setattr__(self, "line_number", line_number)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "name", _require_text("name", self.name))
        object.__setattr__(
            self, "lookup_key", _require_text("lookup_key", self.lookup_key)
        )
        matches = tuple(self.matches)
        if not matches or any(not isinstance(item, CardIdentityV1) for item in matches):
            raise TypeError("matches must contain CardIdentityV1 values")
        if tuple((item.name, item.oracle_id) for item in matches) != tuple(
            sorted((item.name, item.oracle_id) for item in matches)
        ):
            raise ValueError("ambiguous matches must be canonically ordered")
        if len({item.oracle_id for item in matches}) != len(matches):
            raise ValueError("ambiguous matches must be unique")
        object.__setattr__(self, "matches", matches)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "line_number": self.line_number,
            "section": self.section.value,
            "quantity": self.quantity,
            "name": self.name,
            "lookup_key": self.lookup_key,
            "matches": [item.to_wire() for item in self.matches],
        }


@dataclass(frozen=True, slots=True)
class DeckCardSummaryV1:
    identity: CardIdentityV1
    quantity: int
    analysis_outcome: AnalysisOutcomeV1
    semantic_state: SemanticStateV1

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CardIdentityV1):
            raise TypeError("identity must be CardIdentityV1")
        quantity = _count("quantity", self.quantity)
        if not 1 <= quantity <= MAX_SECTION_CARD_COUNT:
            raise ValueError("quantity must be positive")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(
            self, "analysis_outcome", AnalysisOutcomeV1(self.analysis_outcome)
        )
        object.__setattr__(self, "semantic_state", SemanticStateV1(self.semantic_state))

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "identity": self.identity.to_wire(),
            "quantity": self.quantity,
            "analysis_outcome": self.analysis_outcome.value,
            "semantic_state": self.semantic_state.value,
        }


@dataclass(frozen=True, slots=True)
class DeckCapabilityCountV1:
    capability: CapabilityRefV1
    display_name: str
    unique_mapped_oracle_identity_count: int
    quantity_weighted_mapped_card_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.capability, CapabilityRefV1):
            raise TypeError("capability must be CapabilityRefV1")
        object.__setattr__(
            self, "display_name", _require_text("display_name", self.display_name)
        )
        object.__setattr__(
            self,
            "unique_mapped_oracle_identity_count",
            _count(
                "unique_mapped_oracle_identity_count",
                self.unique_mapped_oracle_identity_count,
            ),
        )
        object.__setattr__(
            self,
            "quantity_weighted_mapped_card_count",
            _count(
                "quantity_weighted_mapped_card_count",
                self.quantity_weighted_mapped_card_count,
            ),
        )
        if self.quantity_weighted_mapped_card_count > MAX_SECTION_CARD_COUNT:
            raise ValueError("quantity-weighted Capability count exceeds section limit")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "capability": self.capability.to_wire(),
            "display_name": self.display_name,
            "unique_mapped_oracle_identity_count": (
                self.unique_mapped_oracle_identity_count
            ),
            "quantity_weighted_mapped_card_count": (
                self.quantity_weighted_mapped_card_count
            ),
        }


@dataclass(frozen=True, slots=True)
class DeckProvenanceTraceV1:
    card: CardIdentityV1
    requirement_traces: tuple[RequirementTraceV1, ...]
    mapping_traces: tuple[MappingTraceV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.card, CardIdentityV1):
            raise TypeError("card must be CardIdentityV1")
        requirements = tuple(self.requirement_traces)
        mappings = tuple(self.mapping_traces)
        if any(not isinstance(item, RequirementTraceV1) for item in requirements):
            raise TypeError("requirement_traces must contain RequirementTraceV1 values")
        if any(not isinstance(item, MappingTraceV1) for item in mappings):
            raise TypeError("mapping_traces must contain MappingTraceV1 values")
        if tuple(item.requirement.requirement_id for item in requirements) != tuple(
            sorted(item.requirement.requirement_id for item in requirements)
        ):
            raise ValueError("requirement_traces must be sorted")
        if tuple(item.link.link_id for item in mappings) != tuple(
            sorted(item.link.link_id for item in mappings)
        ):
            raise ValueError("mapping_traces must be sorted")
        object.__setattr__(self, "requirement_traces", requirements)
        object.__setattr__(self, "mapping_traces", mappings)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "card": self.card.to_wire(),
            "requirement_traces": [item.to_wire() for item in self.requirement_traces],
            "mapping_traces": [item.to_wire() for item in self.mapping_traces],
        }
