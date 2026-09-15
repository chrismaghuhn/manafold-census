"""Immutable M5-08 card, name-resolution, and Capability detail values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..canonical import JSONValue
from ..capability.admissibility import SourceRequirementAdmissibilityV1
from ..capability.definition import CapabilityDefinitionV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.review import CapabilityReviewRecordV1
from ..semantic.primitives import _require_int, _require_text
from ..structural.model import StructuralCardRecordV1
from .cards import CardSemanticViewV1, RequirementSummaryV1


def _requirement_link_sort_key(
    item: RequirementCapabilityLinkV1,
) -> tuple[str, str, int, str, str]:
    return (
        item.relation.value,
        item.capability.capability_family_id,
        item.capability.capability_version,
        item.capability.claim_digest,
        item.link_id,
    )


def _supporting_link_sort_key(
    item: RequirementCapabilityLinkV1,
) -> tuple[str, str, str, int, str, str]:
    return (item.requirement_id, *_requirement_link_sort_key(item))


class CardNameResolutionStatusV1(StrEnum):
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class CardIdentityV1:
    oracle_id: str
    source_card_id: str
    source_record_sha256: str
    name: str

    def __post_init__(self) -> None:
        for field in (
            "oracle_id",
            "source_card_id",
            "source_record_sha256",
            "name",
        ):
            _require_text(field, getattr(self, field))

    @classmethod
    def from_record(cls, record: StructuralCardRecordV1) -> CardIdentityV1:
        if not isinstance(record, StructuralCardRecordV1):
            raise TypeError("record must be StructuralCardRecordV1")
        return cls(
            record.oracle_id,
            record.source_card_id,
            record.source_record_sha256,
            record.name,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "oracle_id": self.oracle_id,
            "source_card_id": self.source_card_id,
            "source_record_sha256": self.source_record_sha256,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class CardNameResolutionV1:
    query: str
    lookup_key: str
    status: CardNameResolutionStatusV1
    matches: tuple[CardIdentityV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.query, str) or not isinstance(self.lookup_key, str):
            raise TypeError("query and lookup_key must be strings")
        status = CardNameResolutionStatusV1(self.status)
        matches = tuple(self.matches)
        if any(not isinstance(item, CardIdentityV1) for item in matches):
            raise TypeError("matches must contain CardIdentityV1 values")
        ordered = tuple(sorted(matches, key=lambda item: (item.name, item.oracle_id)))
        if ordered != matches:
            raise ValueError("name resolution matches must be canonically ordered")
        expected = (
            CardNameResolutionStatusV1.UNKNOWN
            if not matches
            else CardNameResolutionStatusV1.RESOLVED
            if len(matches) == 1
            else CardNameResolutionStatusV1.AMBIGUOUS
        )
        if status is not expected:
            raise ValueError("name resolution status does not match its matches")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "matches", matches)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "query": self.query,
            "lookup_key": self.lookup_key,
            "status": self.status.value,
            "matches": [item.to_wire() for item in self.matches],
        }


@dataclass(frozen=True, slots=True)
class MappedSubsetFrequencyV1:
    mapped_requirement_count: int
    denominator: int
    denominator_label: str

    def __post_init__(self) -> None:
        _require_int(
            "mapped_requirement_count",
            self.mapped_requirement_count,
            nonnegative=True,
        )
        _require_int("denominator", self.denominator, nonnegative=True)
        if self.mapped_requirement_count > self.denominator:
            raise ValueError("mapped requirement count exceeds denominator")
        if _require_text("denominator_label", self.denominator_label) != (
            "MAPPED_REQUIREMENTS"
        ):
            raise ValueError("denominator_label must be MAPPED_REQUIREMENTS")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "mapped_requirement_count": self.mapped_requirement_count,
            "denominator": self.denominator,
            "denominator_label": self.denominator_label,
        }


@dataclass(frozen=True, slots=True)
class RequirementDetailViewV1:
    summary: RequirementSummaryV1
    admissibility: SourceRequirementAdmissibilityV1
    mapping_decision: RequirementMappingDecisionV1
    links: tuple[RequirementCapabilityLinkV1, ...]

    @property
    def requirement_id(self) -> str:
        return self.summary.requirement_id

    def __post_init__(self) -> None:
        if not isinstance(self.summary, RequirementSummaryV1):
            raise TypeError("summary must be RequirementSummaryV1")
        if not isinstance(self.admissibility, SourceRequirementAdmissibilityV1):
            raise TypeError("admissibility must be SourceRequirementAdmissibilityV1")
        if not isinstance(self.mapping_decision, RequirementMappingDecisionV1):
            raise TypeError("mapping_decision must be RequirementMappingDecisionV1")
        if self.admissibility.requirement_id != self.requirement_id:
            raise ValueError("admissibility does not match Requirement summary")
        if self.mapping_decision.requirement_id != self.requirement_id:
            raise ValueError("mapping decision does not match Requirement summary")
        links = tuple(self.links)
        if any(not isinstance(item, RequirementCapabilityLinkV1) for item in links):
            raise TypeError("links must contain RequirementCapabilityLinkV1 values")
        if any(item.requirement_id != self.requirement_id for item in links):
            raise ValueError("links do not match Requirement summary")
        if tuple(_requirement_link_sort_key(item) for item in links) != tuple(
            sorted(_requirement_link_sort_key(item) for item in links)
        ):
            raise ValueError("links must use the canonical M4 query order")
        object.__setattr__(self, "links", links)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "summary": self.summary.to_wire(),
            "admissibility": self.admissibility.to_wire(),
            "mapping_decision": self.mapping_decision.to_wire(),
            "links": [item.to_wire() for item in self.links],
        }


@dataclass(frozen=True, slots=True)
class CapabilityDetailViewV1:
    census_release_id: str
    census_manifest_sha256: str
    definition: CapabilityDefinitionV1
    definition_review: CapabilityReviewRecordV1 | None
    links: tuple[RequirementCapabilityLinkV1, ...]
    linked_requirements: tuple[RequirementSummaryV1, ...]
    mapped_cards: tuple[CardIdentityV1, ...]
    mapped_subset_frequency: MappedSubsetFrequencyV1

    def __post_init__(self) -> None:
        _require_text("census_release_id", self.census_release_id)
        _require_text("census_manifest_sha256", self.census_manifest_sha256)
        if not isinstance(self.definition, CapabilityDefinitionV1):
            raise TypeError("definition must be CapabilityDefinitionV1")
        if self.definition_review is not None and not isinstance(
            self.definition_review, CapabilityReviewRecordV1
        ):
            raise TypeError(
                "definition_review must be CapabilityReviewRecordV1 or None"
            )
        if self.definition.review_ref is None and self.definition_review is not None:
            raise ValueError("definition review is present without a review_ref")
        if self.definition.review_ref is not None and (
            self.definition_review is None
            or self.definition_review.record_id != self.definition.review_ref
        ):
            raise ValueError("definition review does not match review_ref")
        links = tuple(self.links)
        if any(not isinstance(item, RequirementCapabilityLinkV1) for item in links):
            raise TypeError("links must contain RequirementCapabilityLinkV1 values")
        if tuple(_supporting_link_sort_key(item) for item in links) != tuple(
            sorted(_supporting_link_sort_key(item) for item in links)
        ):
            raise ValueError("links must use the canonical supporting-link order")
        if len({item.link_id for item in links}) != len(links):
            raise ValueError("links must be unique")
        requirements = tuple(self.linked_requirements)
        if any(not isinstance(item, RequirementSummaryV1) for item in requirements):
            raise TypeError(
                "linked_requirements must contain RequirementSummaryV1 values"
            )
        if tuple(item.requirement_id for item in requirements) != tuple(
            sorted(item.requirement_id for item in requirements)
        ):
            raise ValueError("linked_requirements must be sorted")
        cards = tuple(self.mapped_cards)
        if any(not isinstance(item, CardIdentityV1) for item in cards):
            raise TypeError("mapped_cards must contain CardIdentityV1 values")
        if tuple(item.oracle_id for item in cards) != tuple(
            sorted(item.oracle_id for item in cards)
        ):
            raise ValueError("mapped_cards must be sorted")
        if len({item.oracle_id for item in cards}) != len(cards):
            raise ValueError("mapped_cards must be unique")
        if not isinstance(self.mapped_subset_frequency, MappedSubsetFrequencyV1):
            raise TypeError("mapped_subset_frequency must be typed")
        object.__setattr__(self, "links", links)
        object.__setattr__(self, "linked_requirements", requirements)
        object.__setattr__(self, "mapped_cards", cards)

    @property
    def mapped_requirement_count(self) -> int:
        return self.mapped_subset_frequency.mapped_requirement_count

    @property
    def mapped_subset_denominator(self) -> int:
        return self.mapped_subset_frequency.denominator

    @property
    def mapped_subset_denominator_label(self) -> str:
        return self.mapped_subset_frequency.denominator_label

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "definition": self.definition.to_wire(),
            "definition_review": (
                None
                if self.definition_review is None
                else self.definition_review.to_wire()
            ),
            "links": [item.to_wire() for item in self.links],
            "linked_requirements": [
                item.to_wire() for item in self.linked_requirements
            ],
            "mapped_cards": [item.to_wire() for item in self.mapped_cards],
            "mapped_subset_frequency": self.mapped_subset_frequency.to_wire(),
        }


@dataclass(frozen=True, slots=True)
class CardDetailViewV1:
    structural_record: StructuralCardRecordV1
    semantic_view: CardSemanticViewV1
    requirement_details: tuple[RequirementDetailViewV1, ...]
    capability_details: tuple[CapabilityDetailViewV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.structural_record, StructuralCardRecordV1):
            raise TypeError("structural_record must be StructuralCardRecordV1")
        if not isinstance(self.semantic_view, CardSemanticViewV1):
            raise TypeError("semantic_view must be CardSemanticViewV1")
        if self.structural_record.oracle_id != self.semantic_view.oracle_id:
            raise ValueError("structural record and semantic view do not match")
        requirement_details = tuple(self.requirement_details)
        if any(
            not isinstance(item, RequirementDetailViewV1)
            for item in requirement_details
        ):
            raise TypeError("requirement_details must contain typed values")
        if tuple(item.requirement_id for item in requirement_details) != tuple(
            sorted(item.requirement_id for item in requirement_details)
        ):
            raise ValueError("requirement_details must be sorted")
        details = tuple(self.capability_details)
        if any(not isinstance(item, CapabilityDetailViewV1) for item in details):
            raise TypeError("capability_details must contain typed values")
        if tuple(item.definition.capability_ref for item in details) != tuple(
            sorted(
                (item.definition.capability_ref for item in details),
                key=lambda ref: (
                    ref.capability_family_id,
                    ref.capability_version,
                    ref.claim_digest,
                ),
            )
        ):
            raise ValueError("capability_details must be sorted")
        object.__setattr__(self, "requirement_details", requirement_details)
        object.__setattr__(self, "capability_details", details)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "structural_record": self.structural_record.to_wire(),
            "semantic_view": self.semantic_view.to_wire(),
            "requirement_details": [
                item.to_wire() for item in self.requirement_details
            ],
            "capability_details": [item.to_wire() for item in self.capability_details],
        }


__all__ = [
    "CardDetailViewV1",
    "CardIdentityV1",
    "CardNameResolutionStatusV1",
    "CardNameResolutionV1",
    "CapabilityDetailViewV1",
    "MappedSubsetFrequencyV1",
    "RequirementDetailViewV1",
]
