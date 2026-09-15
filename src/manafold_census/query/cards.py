"""Closed card semantic views and their M3-first state derivation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1, card_source_key
from ..canonical import JSONValue
from ..capability.admissibility import (
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
)
from ..capability.binding import ParameterBindingV1
from ..capability.definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from ..capability.link import LinkRelationV1, RequirementCapabilityLinkV1
from ..capability.mapping import MappingDispositionV1, RequirementMappingDecisionV1
from ..capability.model import CapabilityRefV1
from ..semantic.evidence import SourceRecordRefV1
from ..semantic.identity import wire_digest_for
from ..semantic.kinds import RequirementFamilyV1, RequirementKindV1
from ..semantic.model import RequirementV1, ResolutionStateV1, ReviewStatusV1
from ..semantic.primitives import _require_int, _require_text
from ..structural.model import StructuralCardRecordV1
from .summaries import M2ReviewSummaryV1, M4MappingSummaryV1


class SemanticStateV1(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    PARTIALLY_ESTABLISHED = "PARTIALLY_ESTABLISHED"
    UNRESOLVED_ANALYSIS = "UNRESOLVED_ANALYSIS"
    NO_REQUIREMENTS_APPLICABLE = "NO_REQUIREMENTS_APPLICABLE"


def _tuple_values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class QueryNotFoundV1:
    resource: str
    identifier: str

    SCHEMA: ClassVar[str] = "census.query-not-found.v1"

    def __post_init__(self) -> None:
        _require_text("resource", self.resource)
        _require_text("identifier", self.identifier)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "resource": self.resource,
            "identifier": self.identifier,
        }


@dataclass(frozen=True, slots=True)
class RequirementSummaryV1:
    requirement_id: str
    requirement_wire_digest: str
    source: SourceRecordRefV1
    family: RequirementFamilyV1
    kind: RequirementKindV1
    review_status: ReviewStatusV1
    resolution_state: ResolutionStateV1

    def __post_init__(self) -> None:
        _require_text("requirement_id", self.requirement_id)
        _require_text("requirement_wire_digest", self.requirement_wire_digest)
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        if not isinstance(self.family, RequirementFamilyV1):
            raise TypeError("family must be RequirementFamilyV1")
        if not isinstance(self.kind, RequirementKindV1):
            raise TypeError("kind must be RequirementKindV1")
        if not isinstance(self.review_status, ReviewStatusV1):
            raise TypeError("review_status must be ReviewStatusV1")
        if not isinstance(self.resolution_state, ResolutionStateV1):
            raise TypeError("resolution_state must be ResolutionStateV1")

    @classmethod
    def from_requirement(cls, requirement: RequirementV1) -> RequirementSummaryV1:
        return cls(
            requirement.requirement_id,
            wire_digest_for(requirement),
            requirement.source,
            requirement.family,
            requirement.kind,
            requirement.review.status,
            requirement.resolution.state,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
            "source": self.source.to_wire(),
            "family": self.family.value,
            "kind": self.kind.value,
            "review_status": self.review_status.value,
            "resolution_state": self.resolution_state.value,
        }


@dataclass(frozen=True, slots=True)
class CapabilityMappingSummaryV1:
    requirement_id: str
    link_id: str
    link_claim_digest: str
    capability: CapabilityRefV1
    relation: LinkRelationV1
    parameter_bindings: tuple[ParameterBindingV1, ...]
    lifecycle: CapabilityLifecycleStateV1
    mapping_disposition: MappingDispositionV1

    def __post_init__(self) -> None:
        _require_text("requirement_id", self.requirement_id)
        _require_text("link_id", self.link_id)
        _require_text("link_claim_digest", self.link_claim_digest)
        if not isinstance(self.capability, CapabilityRefV1):
            raise TypeError("capability must be CapabilityRefV1")
        if not isinstance(self.relation, LinkRelationV1):
            raise TypeError("relation must be LinkRelationV1")
        bindings = _tuple_values(self.parameter_bindings, "parameter_bindings")
        if any(not isinstance(item, ParameterBindingV1) for item in bindings):
            raise TypeError("parameter_bindings must contain ParameterBindingV1 values")
        object.__setattr__(self, "parameter_bindings", bindings)
        if not isinstance(self.lifecycle, CapabilityLifecycleStateV1):
            raise TypeError("lifecycle must be CapabilityLifecycleStateV1")
        if not isinstance(self.mapping_disposition, MappingDispositionV1):
            raise TypeError("mapping_disposition must be MappingDispositionV1")

    @classmethod
    def from_link(
        cls,
        link: RequirementCapabilityLinkV1,
        definition: CapabilityDefinitionV1,
        disposition: MappingDispositionV1,
    ) -> CapabilityMappingSummaryV1:
        return cls(
            link.requirement_id,
            link.link_id,
            link.link_claim_digest,
            link.capability,
            link.relation,
            link.parameter_bindings,
            definition.lifecycle,
            disposition,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "requirement_id": self.requirement_id,
            "link_id": self.link_id,
            "link_claim_digest": self.link_claim_digest,
            "capability": self.capability.to_wire(),
            "relation": self.relation.value,
            "parameter_bindings": [item.to_wire() for item in self.parameter_bindings],
            "lifecycle": self.lifecycle.value,
            "mapping_disposition": self.mapping_disposition.value,
        }


@dataclass(frozen=True, slots=True)
class CardProvenanceV1:
    census_release_id: str
    census_manifest_sha256: str
    source: SourceRecordRefV1
    m3_analysis_manifest_sha256: str
    trace_event_count: int

    def __post_init__(self) -> None:
        for field in (
            "census_release_id",
            "census_manifest_sha256",
            "m3_analysis_manifest_sha256",
        ):
            _require_text(field, getattr(self, field))
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        _require_int("trace_event_count", self.trace_event_count, nonnegative=True)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "source": self.source.to_wire(),
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "trace_event_count": self.trace_event_count,
        }


@dataclass(frozen=True, slots=True)
class CardSemanticViewV1:
    oracle_id: str
    analysis_outcome: AnalysisOutcomeV1
    semantic_state: SemanticStateV1
    requirements: tuple[RequirementSummaryV1, ...]
    active_capability_mappings: tuple[CapabilityMappingSummaryV1, ...]
    m2_review_summary: M2ReviewSummaryV1
    m4_mapping_summary: M4MappingSummaryV1
    provenance: CardProvenanceV1

    def __post_init__(self) -> None:
        _require_text("oracle_id", self.oracle_id)
        if not isinstance(self.analysis_outcome, AnalysisOutcomeV1):
            raise TypeError("analysis_outcome must be AnalysisOutcomeV1")
        if not isinstance(self.semantic_state, SemanticStateV1):
            raise TypeError("semantic_state must be SemanticStateV1")
        requirements = cast(
            tuple[RequirementSummaryV1, ...],
            _tuple_values(self.requirements, "requirements"),
        )
        mappings = cast(
            tuple[CapabilityMappingSummaryV1, ...],
            _tuple_values(
                self.active_capability_mappings, "active_capability_mappings"
            ),
        )
        if any(not isinstance(item, RequirementSummaryV1) for item in requirements):
            raise TypeError("requirements must contain RequirementSummaryV1 values")
        if any(not isinstance(item, CapabilityMappingSummaryV1) for item in mappings):
            raise TypeError(
                "active_capability_mappings must contain "
                "CapabilityMappingSummaryV1 values"
            )
        if tuple(item.requirement_id for item in requirements) != tuple(
            sorted(item.requirement_id for item in requirements)
        ):
            raise ValueError("requirements must be sorted by Requirement ID")
        if len({item.requirement_id for item in requirements}) != len(requirements):
            raise ValueError("requirements must be unique")
        mapped_requirement_ids = {item.requirement_id for item in mappings}
        if any(
            item.mapping_disposition is not MappingDispositionV1.MAPPED
            for item in mappings
        ):
            raise ValueError("active mappings must have MAPPED disposition")
        expected_state = semantic_state_for(
            self.analysis_outcome,
            len(requirements),
            len(mapped_requirement_ids),
        )
        if self.semantic_state is not expected_state:
            raise ValueError("semantic_state does not match M3 precedence")
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "active_capability_mappings", mappings)
        if not isinstance(self.m2_review_summary, M2ReviewSummaryV1):
            raise TypeError("m2_review_summary must be M2ReviewSummaryV1")
        if not isinstance(self.m4_mapping_summary, M4MappingSummaryV1):
            raise TypeError("m4_mapping_summary must be M4MappingSummaryV1")
        if not isinstance(self.provenance, CardProvenanceV1):
            raise TypeError("provenance must be CardProvenanceV1")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "oracle_id": self.oracle_id,
            "analysis_outcome": self.analysis_outcome.value,
            "semantic_state": self.semantic_state.value,
            "requirements": [item.to_wire() for item in self.requirements],
            "active_capability_mappings": [
                item.to_wire() for item in self.active_capability_mappings
            ],
            "m2_review_summary": self.m2_review_summary.to_wire(),
            "m4_mapping_summary": self.m4_mapping_summary.to_wire(),
            "provenance": self.provenance.to_wire(),
        }


def semantic_state_for(
    outcome: AnalysisOutcomeV1,
    requirement_count: int,
    mapped_requirement_count: int,
) -> SemanticStateV1:
    """Apply the frozen M3-first SemanticState precedence."""

    if not isinstance(outcome, AnalysisOutcomeV1):
        raise TypeError("outcome must be AnalysisOutcomeV1")
    _require_int("requirement_count", requirement_count, nonnegative=True)
    _require_int("mapped_requirement_count", mapped_requirement_count, nonnegative=True)
    if mapped_requirement_count > requirement_count:
        raise ValueError("mapped_requirement_count cannot exceed requirement_count")
    if outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS:
        return SemanticStateV1.UNRESOLVED_ANALYSIS
    if outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE:
        return SemanticStateV1.NO_REQUIREMENTS_APPLICABLE
    if requirement_count > 0 and mapped_requirement_count == requirement_count:
        return SemanticStateV1.ESTABLISHED
    return SemanticStateV1.PARTIALLY_ESTABLISHED


def _enum_counter(
    enum_type: type[StrEnum], values: Sequence[StrEnum]
) -> dict[str, int]:
    counts = Counter(item.value for item in values)
    return {item.value: counts[item.value] for item in enum_type}


def build_card_semantic_view(
    *,
    structural_record: StructuralCardRecordV1,
    analysis_record: CardAnalysisRecordV1,
    requirements: Sequence[RequirementV1],
    admissibility_by_requirement: Mapping[str, SourceRequirementAdmissibilityV1],
    decisions_by_requirement: Mapping[str, RequirementMappingDecisionV1],
    links_by_id: Mapping[str, RequirementCapabilityLinkV1],
    definitions_by_ref: Mapping[CapabilityRefV1, CapabilityDefinitionV1],
    census_release_id: str,
    census_manifest_sha256: str,
    m3_analysis_manifest_sha256: str,
    trace_event_count: int = 0,
) -> CardSemanticViewV1:
    """Build a view from already validated typed records only."""

    if card_source_key(analysis_record.source) != (
        StructuralCardRecordV1.SCHEMA,
        structural_record.oracle_id,
        structural_record.source_card_id,
        structural_record.source_record_sha256,
    ):
        raise ValueError("M1 and M3 card identities do not match")
    selected = tuple(
        sorted(
            (
                item
                for item in requirements
                if card_source_key(item.source)
                == card_source_key(analysis_record.source)
            ),
            key=lambda item: item.requirement_id,
        )
    )
    expected_ids = (
        ()
        if analysis_record.bundle is None
        else tuple(
            sorted(item.requirement_id for item in analysis_record.bundle.requirements)
        )
    )
    if tuple(item.requirement_id for item in selected) != expected_ids:
        raise ValueError("M3 bundle and Requirement corpus differ")

    requirement_summaries = tuple(
        RequirementSummaryV1.from_requirement(item) for item in selected
    )
    mappings: list[CapabilityMappingSummaryV1] = []
    mapping_dispositions: list[MappingDispositionV1] = []
    admissibility_decisions: list[AdmissibilityDecisionV1] = []
    mapped_requirement_count = 0
    for requirement in selected:
        admissibility = admissibility_by_requirement.get(requirement.requirement_id)
        decision = decisions_by_requirement.get(requirement.requirement_id)
        if admissibility is None or decision is None:
            raise ValueError("Requirement is missing a validated M4 decision")
        admissibility.validate_against_requirement(requirement)
        decision.validate_against_requirement(requirement)
        admissibility_decisions.append(admissibility.decision)
        mapping_dispositions.append(decision.disposition)
        if decision.disposition is not MappingDispositionV1.MAPPED:
            continue
        mapped_requirement_count += 1
        for link_id in decision.active_link_ids:
            link = links_by_id.get(link_id)
            if link is None or link.requirement_id != requirement.requirement_id:
                raise ValueError("mapping decision references an invalid link")
            definition = definitions_by_ref.get(link.capability)
            if definition is None:
                raise ValueError("active link references an unknown Capability")
            mappings.append(
                CapabilityMappingSummaryV1.from_link(
                    link, definition, decision.disposition
                )
            )

    m2_summary = M2ReviewSummaryV1(
        _enum_counter(ReviewStatusV1, [item.review.status for item in selected]),
        _enum_counter(ResolutionStateV1, [item.resolution.state for item in selected]),
    )
    m4_summary = M4MappingSummaryV1(
        _enum_counter(AdmissibilityDecisionV1, admissibility_decisions),
        _enum_counter(MappingDispositionV1, mapping_dispositions),
    )
    return CardSemanticViewV1(
        oracle_id=structural_record.oracle_id,
        analysis_outcome=analysis_record.outcome,
        semantic_state=semantic_state_for(
            analysis_record.outcome,
            len(selected),
            mapped_requirement_count,
        ),
        requirements=requirement_summaries,
        active_capability_mappings=tuple(
            sorted(mappings, key=lambda item: (item.requirement_id, item.link_id))
        ),
        m2_review_summary=m2_summary,
        m4_mapping_summary=m4_summary,
        provenance=CardProvenanceV1(
            census_release_id,
            census_manifest_sha256,
            analysis_record.source,
            m3_analysis_manifest_sha256,
            trace_event_count,
        ),
    )


__all__ = [
    "CapabilityMappingSummaryV1",
    "CardProvenanceV1",
    "CardSemanticViewV1",
    "M2ReviewSummaryV1",
    "M4MappingSummaryV1",
    "QueryNotFoundV1",
    "RequirementSummaryV1",
    "SemanticStateV1",
    "build_card_semantic_view",
    "semantic_state_for",
]
